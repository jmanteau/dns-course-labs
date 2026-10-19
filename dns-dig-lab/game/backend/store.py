"""DynamoDB access. One table, keys PK/SK:

  S#<code> | META              session (status, name)
  S#<code> | P#<nick>          player (tokenHash, score, solved, hints, wrong)
  S#<code> | FIRST#<qid>#<n>   first-blood winners, written with a conditional put
  CACHE#<key> | V              cached live-check results (DynamoDB TTL)
"""
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


class Conflict(Exception):
    pass


def table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE"])


def plain(value):
    """Convert DynamoDB Decimals to int/float and recurse into containers."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, set)):
        return [plain(v) for v in value]
    return value


def _conditional(fn, **kwargs):
    try:
        return fn(**kwargs)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise Conflict() from exc
        raise


# sessions ---------------------------------------------------------------------


def create_session(code, name):
    _conditional(
        table().put_item,
        Item={"PK": f"S#{code}", "SK": "META", "name": name, "status": "open", "createdAt": int(time.time())},
        ConditionExpression="attribute_not_exists(PK)",
    )


def get_session(code):
    item = table().get_item(Key={"PK": f"S#{code}", "SK": "META"}).get("Item")
    return plain(item) if item else None


def set_session_status(code, status):
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": "META"},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status},
        ConditionExpression="attribute_exists(PK)",
    )


# players ----------------------------------------------------------------------


def create_player(code, nick, token_hash):
    _conditional(
        table().put_item,
        Item={
            "PK": f"S#{code}",
            "SK": f"P#{nick.lower()}",
            "nick": nick,
            "tokenHash": token_hash,
            "score": 0,
            "solved": {},
            "hints": {},
            "wrong": {},
            "bonus": {},
            "lastSolveAt": 0,
            "joinedAt": int(time.time()),
        },
        ConditionExpression="attribute_not_exists(PK)",
    )


def get_player(code, nick):
    item = table().get_item(Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"}).get("Item")
    return plain(item) if item else None


def list_players(code):
    resp = table().query(KeyConditionExpression=Key("PK").eq(f"S#{code}") & Key("SK").begins_with("P#"))
    return [plain(i) for i in resp["Items"]]


def record_hint(code, nick, part_key, n):
    """Mark hint n as revealed for a part (never goes backwards)."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
        UpdateExpression="SET hints.#k = :n",
        ConditionExpression="attribute_not_exists(hints.#k) OR hints.#k < :n",
        ExpressionAttributeNames={"#k": part_key},
        ExpressionAttributeValues={":n": n},
    )


def record_wrong(code, nick, part_key, count, at):
    table().update_item(
        Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
        UpdateExpression="SET wrong.#k = :w",
        ExpressionAttributeNames={"#k": part_key},
        ExpressionAttributeValues={":w": {"c": count, "t": at}},
    )


def record_solve(code, nick, part_key, points, now):
    """Idempotent: raises Conflict if the part was already solved."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
        UpdateExpression="SET solved.#k = :p, lastSolveAt = :t ADD score :p",
        ConditionExpression="attribute_not_exists(solved.#k)",
        ExpressionAttributeNames={"#k": part_key},
        ExpressionAttributeValues={":p": points, ":t": now},
    )


def claim_first_blood(code, qid, nick, ranks, bonuses):
    """Try rank 1, 2, 3 in turn; the conditional put makes the race atomic. Returns (rank, bonus) or None."""
    for rank in ranks:
        try:
            _conditional(
                table().put_item,
                Item={"PK": f"S#{code}", "SK": f"FIRST#{qid}#{rank}", "nick": nick, "at": int(time.time())},
                ConditionExpression="attribute_not_exists(PK)",
            )
        except Conflict:
            continue
        table().update_item(
            Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
            UpdateExpression="SET bonus.#q = :b ADD score :b",
            ExpressionAttributeNames={"#q": qid},
            ExpressionAttributeValues={":b": bonuses[rank]},
        )
        return rank, bonuses[rank]
    return None


def list_first_bloods(code):
    resp = table().query(KeyConditionExpression=Key("PK").eq(f"S#{code}") & Key("SK").begins_with("FIRST#"))
    out = []
    for item in resp["Items"]:
        _, qid, rank = item["SK"].split("#")
        out.append({"qid": qid, "rank": int(rank), "nick": item["nick"], "at": int(item["at"])})
    return out


# cache ------------------------------------------------------------------------


class Cache:
    """(get, put) cache for live-check results; items expire through the DynamoDB TTL attribute."""

    def get(self, key):
        item = table().get_item(Key={"PK": f"CACHE#{key}", "SK": "V"}).get("Item")
        if not item or int(item["ttl"]) < time.time():
            return None
        return plain(item["value"])

    def put(self, key, value, expires_at):
        table().put_item(Item={"PK": f"CACHE#{key}", "SK": "V", "value": value, "ttl": expires_at})
