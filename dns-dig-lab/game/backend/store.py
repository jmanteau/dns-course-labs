"""DynamoDB access. One table, keys PK/SK:

  S#<code> | META              session (status, name, activities, live quiz question)
  S#<code> | P#<nick>          player (tokenHash, score, advScore, solved, hints, wrong)
  S#<code> | FIRST#<qid>#<n>   first-blood winners, written with a conditional put
  S#<code> | QA#<qid>#<nick>   a live-quiz answer (one per player, conditional put); open ones get voters
  S#<code> | WS#<connId>       an open page's WebSocket connection (DynamoDB TTL)
  WS#<connId> | META           which session a connection belongs to, for $disconnect
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


_table = None


def table():
    """One table handle per Lambda container: building a boto3 resource costs tens of ms."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _table


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


def set_activities(code, activities):
    """Which activities run: {"dig": bool, "advanced": bool}. A session without them runs everything."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": "META"},
        UpdateExpression="SET activities = :a",
        ExpressionAttributeValues={":a": activities},
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
            "advScore": 0,
            "solved": {},
            "hints": {},
            "wrong": {},
            "bonus": {},
            "lastSolveAt": 0,
            "lastAdvSolveAt": 0,
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


# each board has its own score and tie-break time: advanced solves never move the main ranking
LAST_SOLVE = {"score": "lastSolveAt", "advScore": "lastAdvSolveAt"}


def record_solve(code, nick, part_key, points, now, field="score"):
    """Idempotent: raises Conflict if the part was already solved. `field` is score or advScore."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
        UpdateExpression="SET solved.#k = :p, #t = :t ADD #f :p",
        ConditionExpression="attribute_not_exists(solved.#k)",
        ExpressionAttributeNames={"#k": part_key, "#f": field, "#t": LAST_SOLVE[field]},
        ExpressionAttributeValues={":p": points, ":t": now},
    )


def claim_first_blood(code, qid, nick, ranks, bonuses, field="score"):
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
            UpdateExpression="SET bonus.#q = :b ADD #f :b",
            ExpressionAttributeNames={"#q": qid, "#f": field},
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


# live quiz --------------------------------------------------------------------


def set_quiz(code, live):
    """The question on screen: {qid, phase, openedAt}, or None when nothing is live."""
    if live is None:
        table().update_item(Key={"PK": f"S#{code}", "SK": "META"}, UpdateExpression="REMOVE quiz")
    else:
        table().update_item(Key={"PK": f"S#{code}", "SK": "META"}, UpdateExpression="SET quiz = :q",
                            ExpressionAttributeValues={":q": live})


def put_quiz_answer(code, qid, nick, item):
    """Raises Conflict if the player already answered this question."""
    _conditional(
        table().put_item,
        Item={"PK": f"S#{code}", "SK": f"QA#{qid}#{nick.lower()}", "nick": nick, **item},
        ConditionExpression="attribute_not_exists(PK)",
    )


def get_quiz_answer(code, qid, nick):
    item = table().get_item(Key={"PK": f"S#{code}", "SK": f"QA#{qid}#{nick.lower()}"}).get("Item")
    return plain(item) if item else None


def list_quiz_answers(code, qid):
    resp = table().query(KeyConditionExpression=Key("PK").eq(f"S#{code}") & Key("SK").begins_with(f"QA#{qid}#"))
    return [plain(i) for i in resp["Items"]]


def add_vote(code, qid, author, voter):
    """Upvote an open answer: a string set, so voting twice counts once. Conflict if the answer is gone."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": f"QA#{qid}#{author.lower()}"},
        UpdateExpression="ADD voters :v",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeValues={":v": {voter.lower()}},
    )


def hide_answer(code, qid, nick):
    """The teacher removes an open answer from the wall."""
    _conditional(
        table().update_item,
        Key={"PK": f"S#{code}", "SK": f"QA#{qid}#{nick.lower()}"},
        UpdateExpression="SET #h = :t",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeNames={"#h": "hidden"},  # a reserved word in DynamoDB expressions
        ExpressionAttributeValues={":t": True},
    )


def add_quiz_score(code, nick, points, at):
    """The quiz has its own score, apart from the missions."""
    table().update_item(
        Key={"PK": f"S#{code}", "SK": f"P#{nick.lower()}"},
        UpdateExpression="SET lastQuizAt = :t ADD quizScore :p",
        ExpressionAttributeValues={":p": points, ":t": at},
    )


# websocket connections ----------------------------------------------------------

WS_TTL = 4 * 3600  # a class is shorter: stale connections expire on their own


def add_connection(code, conn):
    expires = int(time.time()) + WS_TTL
    table().put_item(Item={"PK": f"S#{code}", "SK": f"WS#{conn}", "ttl": expires})
    table().put_item(Item={"PK": f"WS#{conn}", "SK": "META", "code": code, "ttl": expires})


def connection_session(conn):
    item = table().get_item(Key={"PK": f"WS#{conn}", "SK": "META"}).get("Item")
    return item["code"] if item else None


def list_connections(code):
    resp = table().query(KeyConditionExpression=Key("PK").eq(f"S#{code}") & Key("SK").begins_with("WS#"))
    return [i["SK"][3:] for i in resp["Items"]]


def delete_connection(code, conn):
    table().delete_item(Key={"PK": f"S#{code}", "SK": f"WS#{conn}"})
    table().delete_item(Key={"PK": f"WS#{conn}", "SK": "META"})


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
