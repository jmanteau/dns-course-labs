import json

import pytest

import checkers
import handler


def call(method, path, body=None, token=None, admin=None, query=None):
    headers = {}
    if token:
        headers["X-Token"] = token
    if admin:
        headers["X-Admin-Token"] = admin
    event = {
        "requestContext": {"http": {"method": method}}, "rawPath": path, "headers": headers,
        "queryStringParameters": query, "body": json.dumps(body) if body is not None else None,
    }
    out = handler.lambda_handler(event)
    return out["statusCode"], json.loads(out["body"])


@pytest.fixture(autouse=True)
def live(monkeypatch):
    """Grade live parts against a fixed set instead of the network."""
    monkeypatch.setattr(checkers, "cached_expected", lambda check, cache=None, ttl=600: {"set": {"1.2.3.4"}, "rtype": "A"})


@pytest.fixture
def session(db):
    assert call("POST", "/admin/session", {"code": "cls1", "name": "Class 1"}, admin="adm")[0] == 200
    return "CLS1"


def join(nick, code="CLS1"):
    status, body = call("POST", "/join", {"session": code, "nick": nick})
    assert status == 200, body
    return body["token"]


def solve_all(tok):
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, tok)[0] == 200
    assert call("POST", "/answer", {"qid": "q01", "part": "b", "value": 1}, tok)[0] == 200
    return call("POST", "/answer", {"qid": "q02", "part": "a", "value": "Imperva"}, tok)


def test_admin_required(db):
    assert call("POST", "/admin/session", {"code": "x1"})[0] == 403
    assert call("POST", "/admin/session", {"code": "x1"}, admin="bad")[0] == 403


def test_join_rules(session):
    join("alice")
    assert call("POST", "/join", {"session": "CLS1", "nick": "ALICE"})[0] == 409
    assert call("POST", "/join", {"session": "CLS1", "nick": "a"})[0] == 400
    assert call("POST", "/join", {"session": "NOPE", "nick": "bob"})[0] == 404


def test_state_never_leaks_answers(session):
    tok = join("alice")
    status, body = call("GET", "/state", token=tok)
    assert status == 200
    dumped = json.dumps(body)
    for secret in ('"answer"', "patterns", "imperva", '"check"'):
        assert secret not in dumped
    assert body["totalParts"] == 3 and body["unlocked"] is False


def test_bad_token(session):
    tok = join("alice")
    assert call("GET", "/state", token=tok[:-3] + "xxx")[0] == 401
    assert call("GET", "/state")[0] == 401


def test_scoring_with_hint_and_first_blood(session):
    alice, bob = join("alice"), join("bob")
    status, body = call("POST", "/hint", {"qid": "q01", "part": "a"}, alice)
    assert (status, body["n"], body["cost"]) == (200, 1, 25)
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, alice)[1]["points"] == 75
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, alice)[0] == 409
    call("POST", "/answer", {"qid": "q01", "part": "b", "value": 1}, alice)
    # alice completes q01 first, bob second
    call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, bob)
    status, body = call("POST", "/answer", {"qid": "q01", "part": "b", "value": 1}, bob)
    assert body["firstBlood"] == {"rank": 2, "bonus": 25}
    board = call("GET", "/leaderboard", query={"session": "cls1"})[1]
    assert [p["nick"] for p in board["players"]] == ["alice", "bob"] or board["players"][0]["score"] >= board["players"][1]["score"]
    assert {(f["nick"], f["rank"]) for f in board["firstBloods"]} == {("alice", 1), ("bob", 2)}
    assert board["players"][0]["score"] == 75 + 100 + 50


def test_wrong_mcq_penalty_and_rate_limit(session):
    tok = join("alice")
    assert call("POST", "/answer", {"qid": "q01", "part": "b", "value": 0}, tok)[1]["correct"] is False
    assert call("POST", "/answer", {"qid": "q01", "part": "b", "value": 1}, tok)[1]["points"] == 75
    for _ in range(5):
        assert call("POST", "/answer", {"qid": "q02", "part": "a", "value": "nope"}, tok)[0] == 200
    assert call("POST", "/answer", {"qid": "q02", "part": "a", "value": "Imperva"}, tok)[0] == 429


def test_explanations_unlock_after_full_solve(session):
    tok = join("alice")
    assert call("GET", "/explanations", token=tok)[0] == 403
    status, body = solve_all(tok)
    assert status == 200
    status, body = call("GET", "/explanations", token=tok)
    assert status == 200 and body["explanations"]["q01"].startswith("# one")


def test_explanations_unlock_when_session_closed(session):
    tok = join("alice")
    assert call("POST", "/admin/session/cls1/status", {}, admin="adm")[0] == 200
    assert call("GET", "/explanations", token=tok)[0] == 200
    assert call("POST", "/answer", {"qid": "q02", "part": "a", "value": "imperva"}, tok)[0] == 403
    assert call("POST", "/join", {"session": "CLS1", "nick": "late"})[0] == 403


def test_live_check_failure_is_503(session, monkeypatch):
    def boom(*a, **k):
        raise checkers.CheckError("timeout")

    monkeypatch.setattr(checkers, "cached_expected", boom)
    tok = join("alice")
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, tok)[0] == 503
