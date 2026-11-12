import json

import pytest

import handler
import quiz
from test_handler import call, join, session  # noqa: F401  (fixtures)


@pytest.fixture(autouse=True)
def fresh_spec(monkeypatch):
    monkeypatch.setattr(quiz, "_spec", None)


def admin(action, code="CLS1", **body):
    return call("POST", f"/admin/quiz/{code}", {"action": action, **body}, admin="adm")


def board(code="CLS1", **kw):
    return call("GET", "/quiz/board", query={"session": code}, **kw)


def test_open_answer_reveal_close(session):
    alice, bob = join("alice"), join("bob")
    assert call("GET", "/quiz", token=alice)[1]["live"] is None
    assert admin("open", qid="k1")[0] == 200
    live = call("GET", "/quiz", token=alice)[1]["live"]
    assert live["phase"] == "open" and live["question"]["options"] == ["UDP/53", "TCP/80"]
    assert "answer" not in live["question"] and "explain" not in live["question"]
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, alice) == (200, {"saved": True})
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 1}, bob)[0] == 200
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 1}, alice)[0] == 409  # one answer only
    status, b = board()
    assert b["live"]["answered"] == 2 and "counts" not in b["live"]
    assert "answer" not in b["live"]["question"] and "explain" not in b["live"]["question"]
    assert admin("reveal")[0] == 200
    mine = call("GET", "/quiz", token=alice)[1]["live"]
    assert mine["question"]["answer"] == 0 and mine["counts"] == [1, 1]
    assert mine["mine"]["correct"] is True and mine["mine"]["points"] >= 100
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, join("carol"))[0] == 409  # too late
    assert admin("reveal")[0] == 409  # no double scoring
    assert admin("close")[0] == 200 and board()[1]["live"] is None


def test_scores_are_added_at_reveal_on_their_own_board(session):
    alice = join("alice")
    admin("open", qid="k1")
    call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, alice)
    assert call("GET", "/leaderboard", query={"session": "CLS1"})[1]["quiz"] == []  # nothing leaks before the reveal
    admin("reveal")
    lb = call("GET", "/leaderboard", query={"session": "CLS1"})[1]
    assert lb["quiz"][0]["nick"] == "alice" and lb["quiz"][0]["score"] >= 100
    state = call("GET", "/state", token=alice)[1]
    assert state["score"] == 0 and state["advScore"] == 0 and state["quizScore"] >= 100


def test_grading_by_type(session):
    alice = join("alice")
    for qid, value, ok in (("k2", [1, 0], True), ("k3", " 13 ", True)):
        admin("open", qid=qid)
        call("POST", "/quiz/answer", {"qid": qid, "value": value}, alice)
        admin("reveal")
        assert call("GET", "/quiz", token=alice)[1]["live"]["mine"]["correct"] is ok
    admin("open", qid="k5")  # a poll has no right answer
    call("POST", "/quiz/answer", {"qid": "k5", "value": 1}, alice)
    admin("reveal")
    live = call("GET", "/quiz", token=alice)[1]["live"]
    assert live["mine"]["points"] == 0 and live["counts"] == [0, 1] and "answer" not in live["question"]


def test_malformed_answers_are_refused(session):
    alice = join("alice")
    admin("open", qid="k2")
    for bad in (5, [], [7], "x", True):
        assert call("POST", "/quiz/answer", {"qid": "k2", "value": bad}, alice)[0] == 400
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, alice)[0] == 409  # not the live question


def test_speed_bonus():
    assert quiz.points(True, 100, 100) == 150
    assert quiz.points(True, 100, 110) == 125
    assert quiz.points(True, 100, 160) == 100
    assert quiz.points(False, 100, 100) == 0
    assert quiz.points(0.5, 100, 100) == 75 and quiz.points(0.5, 100, 160) == 50


def test_multi_partial_credit():
    q = {"type": "multi", "options": [str(k) for k in range(20)], "answer": [0, 1, 2, 3, 4, 5]}
    assert quiz.credit(q, [0, 1, 2, 3, 4, 5]) == 1
    assert quiz.credit(q, [0, 1, 2, 3, 9]) == 0.5  # 4 right, 1 wrong, out of 6
    assert quiz.credit(q, list(range(20))) == 0  # ticking everything scores nothing
    assert quiz.credit(q, [7, 8]) == 0
    assert quiz.credit({"type": "mcq", "answer": 1}, 1) == 1 and quiz.credit({"type": "mcq", "answer": 1}, 0) == 0


def test_partial_answer_scores_at_reveal(session):
    alice = join("alice")
    admin("open", qid="k2")
    call("POST", "/quiz/answer", {"qid": "k2", "value": [0]}, alice)  # 1 of 2 right options
    admin("reveal")
    mine = call("GET", "/quiz", token=alice)[1]["live"]["mine"]
    assert mine["correct"] is False and 50 <= mine["points"] <= 75
    assert call("GET", "/state", token=alice)[1]["quizScore"] == mine["points"]


def test_open_answers_votes_and_hide(session):
    alice, bob, carol = join("alice"), join("bob"), join("carol")
    admin("open", qid="k4")
    call("POST", "/quiz/answer", {"qid": "k4", "value": "a fully qualified name"}, alice)
    call("POST", "/quiz/answer", {"qid": "k4", "value": "a name ending with a dot"}, bob)
    first = call("GET", "/quiz", token=carol)[1]["live"]
    assert "wall" not in first  # nothing to read or vote on before the reveal
    admin("reveal")
    wall = call("GET", "/quiz", token=carol)[1]["live"]["wall"]
    bob_id = next(w["id"] for w in wall if w["text"].endswith("dot"))
    assert call("POST", "/quiz/vote", {"qid": "k4", "id": bob_id}, carol)[0] == 200
    assert call("POST", "/quiz/vote", {"qid": "k4", "id": bob_id}, carol)[0] == 200  # counted once
    assert call("POST", "/quiz/vote", {"qid": "k4", "id": bob_id}, bob)[0] == 403  # not your own
    projected = board()[1]["live"]["wall"]
    assert projected[0]["text"].endswith("dot") and projected[0]["votes"] == 1
    assert "alice" not in json.dumps(projected) and "bob" not in json.dumps(projected)  # no names on the projector
    assert admin("hide", qid="k4", id=bob_id)[0] == 200
    assert [w["text"] for w in board()[1]["live"]["wall"]] == ["a fully qualified name"]


def test_admin_only(session):
    assert call("POST", "/admin/quiz/CLS1", {"action": "open", "qid": "k1"})[0] == 403
    assert call("POST", "/admin/quiz/CLS1", {"action": "open", "qid": "k1"}, admin="bad")[0] == 403
    assert admin("open", qid="nope")[0] == 404
    assert admin("dance")[0] == 400
    assert "rounds" not in board()[1]  # the question list is for the presenter only
    rounds = board(admin="adm")[1]["rounds"]
    assert [r["id"] for r in rounds] == [1, 2] and rounds[0]["questions"][0]["id"] == "k1"


def test_quiz_needs_an_open_session(session):
    alice = join("alice")
    admin("open", qid="k1")
    call("POST", "/admin/session/CLS1/status", {"status": "closed"}, admin="adm")
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, alice)[0] == 403


def test_check_finds_problems():
    good = {"rounds": [{"id": 1, "title": "R"}], "questions": [
        {"id": "a", "round": 1, "type": "mcq", "text": "t", "options": ["x", "y"], "answer": 1}]}
    assert quiz.check(good) == []
    bad = {"rounds": [{"id": 1, "title": "R"}, {"id": 2, "title": "empty"}], "questions": [
        {"id": "a", "round": 1, "type": "mcq", "text": "t", "options": ["x", "y"], "answer": 2},
        {"id": "a", "round": 1, "type": "multi", "text": "t", "options": ["x", "y"], "answer": []},
        {"id": "b", "round": 9, "type": "static", "text": "t", "patterns": ["("]},
        {"id": "c", "round": 1, "type": "quiz", "text": "t"}]}
    errors = "\n".join(quiz.check(bad))
    for expected in ("a: answer must be an option index", "a: duplicate id", "a: answer must be a list",
                     "b: unknown round", "b: bad patterns", "c: unknown type", "round 2: no questions"):
        assert expected in errors


def test_counts_skip_answers_of_another_type():
    """A question edited from open text to multiple choice must not crash on the old text answers."""
    q = {"type": "multi", "options": ["a", "b", "c"], "answer": [0]}
    answers = [{"value": "free text"}, {"value": [0, 2]}, {"value": True}, {"value": [9]}]
    assert quiz.counts(q, answers) == [1, 0, 1]


def test_text_answers_forgive_typos():
    assert quiz.normalise("  Fully-Qualifié  domaine, NAME. ") == "fully qualifie domaine name"
    phrase = "fully qualified domain name"
    for ok in ("fully qualified domaine name", "Full Qualifided Domain Name", "FULLY-QUALIFIED domain name.",
               "an FQDN is a fully qualified domain name ending with a dot"):
        assert quiz.close_enough(ok, phrase), ok
    for wrong in ("domain name", "Oui", "fully", "qualified", ""):
        assert not quiz.close_enough(wrong, phrase), wrong
    q = {"type": "static", "accept": [phrase, "nom de domaine complet"]}
    assert quiz.grade(q, "nom de domaine complèt") and not quiz.grade(q, "a name")
    assert "accept" not in quiz.public({"id": "x", "round": 1, "text": "t", **q}, revealed=True)


def test_check_needs_patterns_or_accept():
    spec = {"rounds": [{"id": 1, "title": "R"}], "questions": [{"id": "s", "round": 1, "type": "static", "text": "t"}]}
    assert "s: needs patterns or accept phrases" in quiz.check(spec)
    spec["questions"][0]["accept"] = ["  "]
    assert "s: accept phrases must be non-empty text" in quiz.check(spec)
