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


def warmed(nick, code="CLS1"):
    """A player who has cleared the warm-up, so the missions are open."""
    tok = join(nick, code)
    assert call("POST", "/answer", {"qid": "w1", "part": "a", "value": "ok"}, tok)[1]["correct"] is True
    return tok


def solve_all(tok):
    call("POST", "/answer", {"qid": "w1", "part": "a", "value": "ok"}, tok)
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
    assert body["totalParts"] == 4 and body["unlocked"] is False


def test_bad_token(session):
    tok = join("alice")
    assert call("GET", "/state", token=tok[:-3] + "xxx")[0] == 401
    assert call("GET", "/state")[0] == 401


def test_scoring_with_hint_and_first_blood(session):
    alice, bob = warmed("alice"), warmed("bob")
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
    assert board["players"][0]["score"] == 20 + 75 + 100 + 50


def test_wrong_mcq_penalty_and_rate_limit(session):
    tok = warmed("alice")
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
    tok = warmed("alice")
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, tok)[0] == 503


def test_missions_locked_until_warmup(session):
    tok = join("alice")
    body = call("GET", "/state", token=tok)[1]
    assert body["warmupDone"] is False
    main = [q for q in body["questions"] if q["stage"] == "main"]
    assert all(q["locked"] and q["parts"] == [] and "prompt" not in q for q in main)
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, tok)[0] == 403
    assert call("POST", "/hint", {"qid": "q01", "part": "a"}, tok)[0] == 403
    assert call("POST", "/hint", {"qid": "w1", "part": "a"}, tok)[0] == 200
    status, body = call("POST", "/answer", {"qid": "w1", "part": "a", "value": "ok"}, tok)
    assert status == 200 and body["firstBlood"] is None  # no speed bonus on the warm-up
    body = call("GET", "/state", token=tok)[1]
    assert body["warmupDone"] is True and not any(q.get("locked") for q in body["questions"] if q["stage"] != "advanced")
    assert call("POST", "/answer", {"qid": "q01", "part": "a", "value": "1.2.3.4"}, tok)[0] == 200


# ---- advanced stage ----------------------------------------------------------


def test_advanced_locked_until_every_main_mission(session):
    tok = warmed("alice")
    body = call("GET", "/state", token=tok)[1]
    adv = [q for q in body["questions"] if q["stage"] == "advanced"]
    assert body["mainDone"] is False and adv and all(q["locked"] and "prompt" not in q for q in adv)
    assert call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, tok)[0] == 403
    assert call("POST", "/hint", {"qid": "a01", "part": "a"}, tok)[0] == 403
    solve_all(tok)
    body = call("GET", "/state", token=tok)[1]
    assert body["mainDone"] is True and not any(q.get("locked") for q in body["questions"])
    assert (body["totalParts"], body["advTotalParts"], body["advSolvedCount"]) == (4, 1, 0)


def test_advanced_points_go_to_their_own_board(session):
    alice, bob = join("alice"), join("bob")
    solve_all(alice)
    solve_all(bob)
    main_before = call("GET", "/leaderboard", query={"session": "cls1"})[1]["players"]
    status, body = call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, bob)
    assert status == 200 and body["points"] == 200 and body["firstBlood"] == {"rank": 1, "bonus": 50}
    board = call("GET", "/leaderboard", query={"session": "cls1"})[1]
    assert board["players"] == main_before  # main scores and tie-breaks unchanged
    assert [(r["nick"], r["score"], r["solved"]) for r in board["advanced"]] == [("bob", 250, 1), ("alice", 0, 0)]
    assert board["advTotalParts"] == 1 and board["totalParts"] == 4
    state = call("GET", "/state", token=bob)[1]
    assert state["advScore"] == 250 and state["solvedCount"] == 4 and state["advSolvedCount"] == 1


def test_advanced_board_only_lists_players_who_reached_it(session):
    warmed("carol")
    assert call("GET", "/leaderboard", query={"session": "cls1"})[1]["advanced"] == []


def test_advanced_explanations_unlock_separately(session):
    tok = join("alice")
    solve_all(tok)
    body = call("GET", "/explanations", token=tok)[1]["explanations"]
    assert "q01" in body and "a01" not in body
    assert call("GET", "/state", token=tok)[1]["advUnlocked"] is False
    call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, tok)
    assert "a01" in call("GET", "/explanations", token=tok)[1]["explanations"]
    assert call("GET", "/state", token=tok)[1]["advUnlocked"] is True


def test_closing_the_session_unlocks_every_explanation(session):
    tok = join("alice")
    call("POST", "/admin/session/cls1/status", {}, admin="adm")
    assert {"q01", "a01"} <= set(call("GET", "/explanations", token=tok)[1]["explanations"])


def test_cors_preflight_succeeds(db):
    """Browsers drop the real request unless the OPTIONS preflight gets a 2xx."""
    event = {"requestContext": {"http": {"method": "OPTIONS"}}, "rawPath": "/join", "headers": {}}
    assert handler.lambda_handler(event)["statusCode"] == 204


def test_base64_bodies_are_decoded(session):
    import base64

    body = base64.b64encode(json.dumps({"session": "CLS1", "nick": "dora"}).encode()).decode()
    event = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/join", "headers": {},
             "body": body, "isBase64Encoded": True}
    out = handler.lambda_handler(event)
    assert out["statusCode"] == 200 and json.loads(out["body"])["nick"] == "dora"


def test_advanced_opens_before_every_main_mission(session, monkeypatch):
    """The advanced stage needs ADV_SHARE of the warm-up and main parts, not all of them."""
    monkeypatch.setattr(handler, "ADV_SHARE", 0.5)  # 2 of the fixture's 4 parts
    tok = warmed("alice")
    assert call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, tok)[0] == 403
    call("POST", "/answer", {"qid": "q02", "part": "a", "value": "Imperva"}, tok)
    state = call("GET", "/state", token=tok)[1]
    assert state["advOpen"] is True and state["mainDone"] is False and state["advNeeded"] == 2
    assert call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, tok)[1]["correct"] is True
    assert [r["nick"] for r in call("GET", "/leaderboard", query={"session": "CLS1"})[1]["advanced"]] == ["alice"]
