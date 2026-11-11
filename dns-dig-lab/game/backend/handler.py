"""Dig Quest API: one Lambda behind an API Gateway HTTP API (payload v2)."""
import base64
import glob
import hashlib
import math
import hmac
import json
import os
import re
import secrets
import time

import checkers
import dig
import push
import quiz
import scoring
import store

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_DIR = os.environ.get("SECRET_DIR", os.path.join(HERE, "secret"))
NICK_RE = re.compile(r"^[A-Za-z0-9_-]{2,16}$")
CODE_RE = re.compile(r"^[A-Z0-9-]{3,24}$")
WRONG_LIMIT, WRONG_WINDOW = 5, 60
DIG_LIMIT, DIG_WINDOW = 20, 60
ADV_SHARE = 0.8  # the advanced missions open once this share of the warm-up and main parts is solved

_questions = None
_dig_calls = {}  # player -> recent console timestamps; per Lambda container, best effort


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def questions():
    global _questions
    if _questions is None:
        with open(os.path.join(SECRET_DIR, "questions.json"), encoding="utf-8") as fh:
            _questions = json.load(fh)["questions"]
    return _questions


def find_part(qid, pid):
    for q in questions():
        if q["id"] == qid:
            for p in q["parts"]:
                if p["id"] == pid:
                    return q, p
    raise HttpError(404, "unknown question or part")


def stage_of(q):
    """warmup (own machine), main (the missions) or advanced (after 80% of the warm-up and main parts)."""
    return q.get("stage", "main")


def stage_keys(*stages):
    return {f"{q['id']}#{p['id']}" for q in questions() if stage_of(q) in stages for p in q["parts"]}


def warmup_done(player):
    """The warm-up (done with dig on the student's own machine) unlocks the missions and the dig console."""
    return set(player["solved"]) >= stage_keys("warmup")


def main_done(player):
    """Every warm-up and main part solved: this unlocks the debrief of the missions."""
    return set(player["solved"]) >= stage_keys("warmup", "main")


def adv_needed():
    """How many warm-up and main parts open the advanced missions (ADV_SHARE of them, rounded up)."""
    return math.ceil(ADV_SHARE * len(stage_keys("warmup", "main")))


def adv_ready(player):
    return len(set(player["solved"]) & stage_keys("warmup", "main")) >= adv_needed()


def stage_open(player, stage):
    if stage == "main":
        return warmup_done(player)
    if stage == "advanced":
        return adv_ready(player)
    return True


def activities(session):
    """The teacher's switches: the dig lab (warm-up, missions, console) and the advanced missions. On by default."""
    a = session.get("activities") or {}
    return {"dig": a.get("dig", True), "advanced": a.get("advanced", True)}


def activity_open(session, stage):
    a = activities(session)
    return a["dig"] and (stage != "advanced" or a["advanced"])


def public_questions(player, session):
    """Questions without answers or checks; hint texts only for hints the player already bought.
    A stage that is not open yet shows only its titles; a paused activity shows nothing but its stage."""
    out = []
    for q in questions():
        stage = stage_of(q)
        if not activity_open(session, stage):
            out.append({"id": q["id"], "title": "", "stage": stage, "locked": "paused", "parts": []})
            continue
        if not stage_open(player, stage):
            out.append({"id": q["id"], "title": q["title"], "stage": stage, "locked": True, "parts": []})
            continue
        parts = []
        for p in q["parts"]:
            key = f"{q['id']}#{p['id']}"
            bought = int(player["hints"].get(key, 0))
            pub = {
                "id": p["id"], "label": p["label"], "points": p["points"], "type": "mcq" if p["type"] == "mcq" else "text",
                "hintsTotal": len(p.get("hints", [])), "hintsBought": bought,
                "hints": p.get("hints", [])[:bought],
                "nextHintCost": scoring.hint_cost(p["points"], bought + 1) if bought < len(p.get("hints", [])) else None,
                "solved": player["solved"].get(key),
            }
            if p["type"] == "mcq":
                pub["options"] = p["options"]
            parts.append(pub)
        out.append({"id": q["id"], "title": q["title"], "stage": stage, "prompt": q["prompt"], "parts": parts})
    return out


# ---- auth -------------------------------------------------------------------


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(headers):
    """Token header format: <SESSION>:<nick>:<secret>. Returns (session_code, player_item)."""
    raw = headers.get("x-token", "")
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise HttpError(401, "missing token")
    code, nick, secret = parts
    player = store.get_player(code, nick) if NICK_RE.match(nick) and CODE_RE.match(code) else None
    if not player or not hmac.compare_digest(player["tokenHash"], hash_token(secret)):
        raise HttpError(401, "invalid token")
    return code, player


_admin_secret = None


def require_admin(headers):
    global _admin_secret
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected and os.environ.get("ADMIN_SECRET_ARN"):
        if _admin_secret is None:  # read once per container: the admin page asks every 1.5 s
            import boto3

            _admin_secret = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["ADMIN_SECRET_ARN"])["SecretString"]
        expected = _admin_secret
    if not expected or not hmac.compare_digest(headers.get("x-admin-token", ""), expected):
        raise HttpError(403, "admin only")


def session_or_404(code):
    if not CODE_RE.match(code or ""):
        raise HttpError(400, "bad session code")
    session = store.get_session(code)
    if not session:
        raise HttpError(404, "unknown session")
    return session


# ---- routes -----------------------------------------------------------------


def join(body, headers, query):
    code = str(body.get("session", "")).strip().upper()
    nick = str(body.get("nick", "")).strip()
    if not NICK_RE.match(nick):
        raise HttpError(400, "nickname: 2-16 letters, digits, - or _")
    session = session_or_404(code)
    if session["status"] != "open":
        raise HttpError(403, "session closed")
    secret = secrets.token_urlsafe(24)
    try:
        store.create_player(code, nick, hash_token(secret))
    except store.Conflict:
        raise HttpError(409, "nickname already taken in this session")
    return {"token": f"{code}:{nick}:{secret}", "nick": nick, "session": code}


def state(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    done = set(player["solved"])
    main, adv = stage_keys("warmup", "main"), stage_keys("advanced")
    return {
        "nick": player["nick"], "session": code, "sessionName": session.get("name", code), "status": session["status"],
        "score": player["score"], "advScore": player.get("advScore", 0), "quizScore": player.get("quizScore", 0),
        "bonus": player["bonus"],
        "solvedCount": len(done & main), "totalParts": len(main),
        "advSolvedCount": len(done & adv), "advTotalParts": len(adv),
        "unlocked": unlocked(player, session), "advUnlocked": adv_unlocked(player, session),
        "warmupDone": warmup_done(player), "mainDone": main_done(player), "activities": activities(session),
        "advOpen": adv_ready(player), "advNeeded": adv_needed(),
        "questions": public_questions(player, session),
    }


def require_stage(player, q, session):
    if not activity_open(session, stage_of(q)):
        raise HttpError(403, "the teacher has paused the advanced missions" if activities(session)["dig"] else "the teacher has paused the dig lab")
    if not stage_open(player, stage_of(q)):
        raise HttpError(403, f"solve {adv_needed()} parts of the missions first" if stage_of(q) == "advanced" else "finish the warm-up first")


def unlocked(player, session):
    """The debrief of the warm-up and main missions."""
    return session["status"] == "closed" or main_done(player)


def adv_unlocked(player, session):
    """The debrief of the advanced missions."""
    return session["status"] == "closed" or (bool(stage_keys("advanced")) and set(player["solved"]) >= stage_keys("advanced"))


def answer(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    if session["status"] != "open":
        raise HttpError(403, "session closed")
    q, part = find_part(str(body.get("qid", "")), str(body.get("part", "")))
    require_stage(player, q, session)
    key = f"{q['id']}#{part['id']}"
    if key in player["solved"]:
        raise HttpError(409, "already solved")
    now = int(time.time())
    wrong = player["wrong"].get(key, {"c": 0, "t": 0})
    recent = wrong["c"] if now - wrong["t"] < WRONG_WINDOW else 0
    if recent >= WRONG_LIMIT:
        raise HttpError(429, f"too many wrong answers, wait {WRONG_WINDOW - (now - wrong['t'])}s")
    try:
        ok = checkers.grade(part, body.get("value"), store.Cache())
    except checkers.CheckError as exc:
        raise HttpError(503, f"live check unavailable, try again ({exc})")
    if not ok:
        store.record_wrong(code, player["nick"], key, recent + 1, now)
        return {"correct": False, "attemptsLeft": WRONG_LIMIT - recent - 1}
    wrong_mcq = wrong["c"] if part["type"] == "mcq" else 0
    points = scoring.part_points(part["points"], int(player["hints"].get(key, 0)), wrong_mcq)
    field = "advScore" if stage_of(q) == "advanced" else "score"
    try:
        store.record_solve(code, player["nick"], key, points, now, field)
    except store.Conflict:
        raise HttpError(409, "already solved")
    result = {"correct": True, "points": points, "firstBlood": None}
    if stage_of(q) != "warmup" and all(f"{q['id']}#{p['id']}" in player["solved"] or f"{q['id']}#{p['id']}" == key for p in q["parts"]):
        won = store.claim_first_blood(code, q["id"], player["nick"], (1, 2, 3), scoring.FIRST_BLOOD, field)
        if won:
            result["firstBlood"] = {"rank": won[0], "bonus": won[1]}
    return result


def hint(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    q, part = find_part(str(body.get("qid", "")), str(body.get("part", "")))
    require_stage(player, q, session)
    key = f"{q['id']}#{part['id']}"
    if key in player["solved"]:
        raise HttpError(409, "already solved")
    bought = int(player["hints"].get(key, 0))
    if bought >= len(part.get("hints", [])):
        raise HttpError(409, "no more hints")
    try:
        store.record_hint(code, player["nick"], key, bought + 1)
    except store.Conflict:
        raise HttpError(409, "hint already revealed, reload")
    return {"n": bought + 1, "text": part["hints"][bought], "cost": scoring.hint_cost(part["points"], bought + 1)}


def leaderboard(body, headers, query):
    code = (query.get("session") or "").upper()
    session = session_or_404(code)
    players = store.list_players(code)
    main, adv = stage_keys("warmup", "main"), stage_keys("advanced")
    rows = sorted(
        ({"nick": p["nick"], "score": p["score"], "solved": len(set(p["solved"]) & main), "lastSolveAt": p["lastSolveAt"]}
         for p in players),
        key=lambda r: (-r["score"], r["lastSolveAt"] or 1 << 60),
    )
    # the advanced board lists only the players who reached it
    adv_rows = sorted(
        ({"nick": p["nick"], "score": p.get("advScore", 0), "solved": len(set(p["solved"]) & adv),
          "lastSolveAt": p.get("lastAdvSolveAt", 0)} for p in players if adv_ready(p)),
        key=lambda r: (-r["score"], r["lastSolveAt"] or 1 << 60),
    )
    # the quiz board: everyone who scored in the live quiz
    quiz_rows = sorted(
        ({"nick": p["nick"], "score": p["quizScore"], "lastSolveAt": p.get("lastQuizAt", 0)}
         for p in players if p.get("quizScore")),
        key=lambda r: (-r["score"], r["lastSolveAt"] or 1 << 60),
    )
    return {
        "session": code, "name": session.get("name", code), "status": session["status"],
        "totalParts": len(main), "players": rows, "firstBloods": store.list_first_bloods(code),
        "advTotalParts": len(adv), "advanced": adv_rows, "quiz": quiz_rows, "activities": activities(session),
    }


def explanations(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    main_open, adv_open = unlocked(player, session), adv_unlocked(player, session)
    if not main_open:
        raise HttpError(403, "solve every part (or wait for the teacher to close the session) to unlock")
    advanced = {q["id"] for q in questions() if stage_of(q) == "advanced"}
    out = {}
    for path in sorted(glob.glob(os.path.join(SECRET_DIR, "explanations", "*.md"))):
        name = os.path.basename(path)[:-3]
        if name in advanced and not adv_open:
            continue
        with open(path, encoding="utf-8") as fh:
            out[name] = fh.read()
    return {"explanations": out}


def dig_console(body, headers, query):
    code, player = authenticate(headers)
    if not activities(session_or_404(code))["dig"]:
        raise HttpError(403, "the teacher has paused the dig lab")
    if not warmup_done(player):
        raise HttpError(403, "the dig console unlocks after the warm-up: use dig in your terminal for now")
    now = time.time()
    key = f"{code}:{player['nick']}"
    recent = [t for t in _dig_calls.get(key, []) if now - t < DIG_WINDOW]
    if len(recent) >= DIG_LIMIT:
        raise HttpError(429, f"slow down: wait {int(DIG_WINDOW - (now - recent[0])) + 1}s")
    _dig_calls[key] = recent + [now]
    try:
        return dig.run(body)
    except dig.DigError as exc:
        raise HttpError(400, str(exc))


# ---- live quiz --------------------------------------------------------------


def now_ms():
    return int(time.time() * 1000)


def live_question(session):
    """(live state, question) of the session, or (None, None) when nothing is on screen."""
    live = session.get("quiz")
    q = quiz.find(quiz.load(SECRET_DIR), live["qid"]) if live else None
    return (live, q) if q else (None, None)


def answer_id(code, qid, nick):
    """Open answers are shown without names: an opaque id stands for the author."""
    return hashlib.sha256(f"{code}#{qid}#{nick.lower()}".encode()).hexdigest()[:12]


def wall(code, q, answers, me=None):
    """Open answers after the reveal: text and votes, most voted first, hidden ones left out."""
    rows = []
    for a in answers:
        if a.get("hidden"):
            continue
        voters = set(a.get("voters", []))
        row = {"id": answer_id(code, q["id"], a["nick"]), "text": a["value"], "votes": len(voters)}
        if me:
            row["mine"] = a["nick"].lower() == me.lower()
            row["votedByMe"] = me.lower() in voters
        rows.append(row)
    return sorted(rows, key=lambda r: -r["votes"])


def results(code, q, answers, me=None):
    """What the reveal shows: counts per option (or right/wrong), and the open answers wall."""
    out = {"answered": len(answers), "counts": quiz.counts(q, answers)}
    if q["type"] == "open":
        out["wall"] = wall(code, q, answers, me)
    return out


def quiz_state(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    live, q = live_question(session)
    # the activities ride along, so a switch reaches students at the quiz's 3 s pace
    out = {"live": None, "now": now_ms(), "quizScore": player.get("quizScore", 0), "activities": activities(session)}
    if not live:
        return out
    revealed = live["phase"] == "reveal"
    mine = store.get_quiz_answer(code, q["id"], player["nick"])
    out["live"] = {"phase": live["phase"], "openedAt": live["openedAt"], "question": quiz.public(q, revealed)}
    if mine:
        out["live"]["mine"] = {"value": mine["value"], **({"correct": mine.get("correct"), "points": mine.get("points", 0)}
                                                         if revealed else {})}
    if revealed:
        out["live"].update(results(code, q, store.list_quiz_answers(code, q["id"]), player["nick"]))
    return out


def quiz_answer(body, headers, query):
    code, player = authenticate(headers)
    session = session_or_404(code)
    if session["status"] != "open":
        raise HttpError(403, "session closed")
    live, q = live_question(session)
    if not live or q["id"] != body.get("qid"):
        raise HttpError(409, "this question is not open")
    if live["phase"] != "open":
        raise HttpError(409, "too late: the answer is already revealed")
    try:
        value = quiz.clean(q, body.get("value"))
    except ValueError as exc:
        raise HttpError(400, str(exc))
    at = now_ms()
    correct = quiz.grade(q, value)
    item = {"value": value, "at": at, "points": quiz.points(correct, live["openedAt"] / 1000, at / 1000)}
    if correct is not None:
        item["correct"] = correct
    try:
        store.put_quiz_answer(code, q["id"], player["nick"], item)
    except store.Conflict:
        raise HttpError(409, "you already answered")
    return {"saved": True}


def quiz_vote(body, headers, query):
    code, player = authenticate(headers)
    live, q = live_question(session_or_404(code))
    if not live or q["id"] != body.get("qid") or live["phase"] != "reveal" or q["type"] != "open":
        raise HttpError(409, "votes open when the answers are revealed")
    author = next((a for a in store.list_quiz_answers(code, q["id"])
                   if answer_id(code, q["id"], a["nick"]) == body.get("id") and not a.get("hidden")), None)
    if not author:
        raise HttpError(404, "unknown answer")
    if author["nick"].lower() == player["nick"].lower():
        raise HttpError(403, "you cannot vote for your own answer")
    store.add_vote(code, q["id"], author["nick"], player["nick"])
    return {"voted": True}


def quiz_board(body, headers, query):
    """The projector view. The question list (with texts) is only for the presenter."""
    code = (query.get("session") or "").upper()
    session = session_or_404(code)
    spec = quiz.load(SECRET_DIR)
    out = {"session": code, "name": session.get("name", code), "now": now_ms(), "live": None}
    try:
        require_admin(headers)
        out["rounds"] = [{"id": r["id"], "title": r["title"],
                          "questions": [{"id": q["id"], "type": q["type"], "text": q["text"]}
                                        for q in spec["questions"] if q["round"] == r["id"]]} for r in spec["rounds"]]
    except HttpError:
        pass
    live, q = live_question(session)
    if live:
        revealed = live["phase"] == "reveal"
        answers = store.list_quiz_answers(code, q["id"])
        out["live"] = {"phase": live["phase"], "openedAt": live["openedAt"], "question": quiz.public(q, revealed),
                       "answered": len(answers)}
        if revealed:
            out["live"].update(results(code, q, answers))
    return out


def admin_quiz(body, headers, query, code):
    require_admin(headers)
    code = code.upper()
    session = session_or_404(code)
    action = body.get("action")
    live, q = live_question(session)
    if action == "open":
        q = quiz.find(quiz.load(SECRET_DIR), str(body.get("qid", "")))
        if not q:
            raise HttpError(404, "unknown quiz question")
        store.set_quiz(code, {"qid": q["id"], "phase": "open", "openedAt": now_ms()})
        push.notify(code, "quiz")
        return {"qid": q["id"], "phase": "open"}
    if action == "reveal":
        if not live or live["phase"] != "open":
            raise HttpError(409, "no open question to reveal")
        store.set_quiz(code, {**live, "phase": "reveal"})
        # points are added now, so the quiz board never shows who is right before the reveal
        for a in store.list_quiz_answers(code, q["id"]):
            if a.get("points"):
                store.add_quiz_score(code, a["nick"], a["points"], a["at"])
        push.notify(code, "quiz")
        return {"qid": q["id"], "phase": "reveal"}
    if action == "close":
        store.set_quiz(code, None)
        push.notify(code, "quiz")
        return {"qid": None}
    if action == "hide":
        if not live:
            raise HttpError(409, "nothing is live")
        author = next((a for a in store.list_quiz_answers(code, q["id"])
                       if answer_id(code, q["id"], a["nick"]) == body.get("id")), None)
        if not author:
            raise HttpError(404, "unknown answer")
        store.hide_answer(code, q["id"], author["nick"])
        push.notify(code, "quiz")
        return {"hidden": body.get("id")}
    raise HttpError(400, "action: open, reveal, close or hide")


def admin_create_session(body, headers, query):
    require_admin(headers)
    code = str(body.get("code") or secrets.token_hex(3)).upper()
    if not CODE_RE.match(code):
        raise HttpError(400, "bad session code")
    try:
        store.create_session(code, str(body.get("name", code))[:60])
    except store.Conflict:
        raise HttpError(409, "session exists")
    return {"code": code}


def admin_activities(body, headers, query, code):
    require_admin(headers)
    session = session_or_404(code.upper())
    current = activities(session)
    new = {k: bool(body[k]) if isinstance(body.get(k), bool) else current[k] for k in ("dig", "advanced")}
    store.set_activities(code.upper(), new)
    push.notify(code.upper(), "activities")
    return {"code": code.upper(), "activities": new}


def admin_close_session(body, headers, query, code):
    require_admin(headers)
    session_or_404(code.upper())
    status = "open" if body.get("status") == "open" else "closed"
    store.set_session_status(code.upper(), status)
    push.notify(code.upper(), "session")
    return {"code": code.upper(), "status": status}


ROUTES = {
    ("POST", "/join"): join,
    ("GET", "/state"): state,
    ("POST", "/answer"): answer,
    ("POST", "/hint"): hint,
    ("GET", "/leaderboard"): leaderboard,
    ("GET", "/explanations"): explanations,
    ("POST", "/dig"): dig_console,
    ("GET", "/quiz"): quiz_state,
    ("POST", "/quiz/answer"): quiz_answer,
    ("POST", "/quiz/vote"): quiz_vote,
    ("GET", "/quiz/board"): quiz_board,
    ("POST", "/admin/session"): admin_create_session,
}
CLOSE_RE = re.compile(r"^/admin/session/([A-Za-z0-9-]+)/status$")
QUIZ_RE = re.compile(r"^/admin/quiz/([A-Za-z0-9-]+)$")
ACTIVITIES_RE = re.compile(r"^/admin/session/([A-Za-z0-9-]+)/activities$")


def respond(status, payload):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(payload),
    }


def ws_event(event):
    """API Gateway WebSocket routes: remember which session each open page follows."""
    ctx = event["requestContext"]
    conn, kind = ctx["connectionId"], ctx.get("eventType")
    if kind == "CONNECT":
        code = ((event.get("queryStringParameters") or {}).get("session") or "").upper()
        if not CODE_RE.match(code) or not store.get_session(code):
            return {"statusCode": 403}
        store.add_connection(code, conn)
    elif kind == "DISCONNECT":
        code = store.connection_session(conn)
        if code:
            store.delete_connection(code, conn)
    return {"statusCode": 200}


def lambda_handler(event, context=None):
    """Every request logs one line, route and time, to find the slow ones in CloudWatch."""
    start = time.perf_counter()
    out = route_event(event)
    ctx = event.get("requestContext", {})
    route = ctx.get("eventType") or f'{ctx.get("http", {}).get("method")} {event.get("rawPath")}'
    print(json.dumps({"route": route, "status": out.get("statusCode"), "ms": round(1000 * (time.perf_counter() - start), 1)}))
    return out


def route_event(event):
    if "connectionId" in event.get("requestContext", {}):
        return ws_event(event)
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    query = event.get("queryStringParameters") or {}
    if method == "OPTIONS":
        # CORS preflight: the $default route sends it here; API Gateway adds the CORS headers,
        # but a browser drops the real request unless the preflight itself succeeds
        return {"statusCode": 204, "headers": {}, "body": ""}
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):  # API Gateway encodes bodies sent without a JSON content type
        raw = base64.b64decode(raw).decode("utf-8", "replace")
    try:
        try:
            body = json.loads(raw)
        except ValueError:
            raise HttpError(400, "invalid JSON")
        if not isinstance(body, dict):
            raise HttpError(400, "JSON object expected")
        match = CLOSE_RE.match(path)
        if method == "POST" and match:
            return respond(200, admin_close_session(body, headers, query, match.group(1)))
        match = ACTIVITIES_RE.match(path)
        if method == "POST" and match:
            return respond(200, admin_activities(body, headers, query, match.group(1)))
        match = QUIZ_RE.match(path)
        if method == "POST" and match:
            return respond(200, admin_quiz(body, headers, query, match.group(1)))
        route = ROUTES.get((method, path))
        if not route:
            raise HttpError(404, "not found")
        return respond(200, route(body, headers, query))
    except HttpError as exc:
        return respond(exc.status, {"error": exc.message})
