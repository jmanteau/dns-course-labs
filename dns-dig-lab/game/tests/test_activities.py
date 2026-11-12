from test_handler import call, join, session, solve_all, warmed  # noqa: F401  (fixtures)


def switch(**body):
    return call("POST", "/admin/session/CLS1/activities", body, admin="adm")


def test_everything_runs_by_default(session):
    tok = join("alice")
    assert call("GET", "/state", token=tok)[1]["activities"] == {"dig": True, "advanced": True}
    assert call("GET", "/leaderboard", query={"session": "CLS1"})[1]["activities"] == {"dig": True, "advanced": True}
    assert call("GET", "/quiz", token=tok)[1]["activities"] == {"dig": True, "advanced": True}


def test_admin_only(session):
    assert call("POST", "/admin/session/CLS1/activities", {"dig": False})[0] == 403
    assert call("POST", "/admin/session/CLS1/activities", {"dig": False}, admin="bad")[0] == 403
    assert switch(dig=False) == (200, {"code": "CLS1", "activities": {"dig": False, "advanced": True}})
    assert switch(advanced=False)[1]["activities"] == {"dig": False, "advanced": False}  # one switch, the other kept


def test_paused_dig_lab_hides_and_blocks_the_missions(session):
    tok = join("alice")
    switch(dig=False)
    body = call("GET", "/state", token=tok)[1]
    assert body["activities"]["dig"] is False
    assert all(q["locked"] == "paused" and not q["title"] and not q["parts"] for q in body["questions"])
    assert "prompt" not in str(body["questions"])
    assert call("POST", "/answer", {"qid": "w1", "part": "a", "value": "ok"}, tok)[0] == 403
    assert call("POST", "/hint", {"qid": "w1", "part": "a"}, tok)[0] == 403
    assert call("POST", "/dig", {"names": "example.com"}, tok)[0] == 403
    switch(dig=True)
    assert call("POST", "/answer", {"qid": "w1", "part": "a", "value": "ok"}, tok)[1]["correct"] is True


def test_paused_advanced_missions_leave_the_main_ones_running(session):
    tok = warmed("alice")
    switch(advanced=False)
    assert call("POST", "/answer", {"qid": "q02", "part": "a", "value": "Imperva"}, tok)[0] == 200
    solve_all(tok)
    status, body = call("POST", "/answer", {"qid": "a01", "part": "a", "value": "deep"}, tok)
    assert status == 403 and "advanced" in body["error"]
    adv = [q for q in call("GET", "/state", token=tok)[1]["questions"] if q["stage"] == "advanced"]
    assert adv and all(q["locked"] == "paused" for q in adv)


def test_the_quiz_runs_whatever_the_switches(session):
    tok = join("alice")
    switch(dig=False, advanced=False)
    call("POST", "/admin/quiz/CLS1", {"action": "open", "qid": "k1"}, admin="adm")
    assert call("POST", "/quiz/answer", {"qid": "k1", "value": 0}, tok) == (200, {"saved": True})
