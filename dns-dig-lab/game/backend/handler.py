"""Dig Quest API: one Lambda behind an API Gateway HTTP API (payload v2)."""
import glob
import hashlib
import hmac
import json
import os
import re
import secrets
import time

import checkers
import dig
import scoring
import store

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_DIR = os.environ.get("SECRET_DIR", os.path.join(HERE, "secret"))
NICK_RE = re.compile(r"^[A-Za-z0-9_-]{2,16}$")
CODE_RE = re.compile(r"^[A-Z0-9-]{3,24}$")
WRONG_LIMIT, WRONG_WINDOW = 5, 60
DIG_LIMIT, DIG_WINDOW = 20, 60

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
    """warmup (own machine), main (the missions) or advanced (after every main mission)."""
    return q.get("stage", "main")


def stage_keys(*stages):
    return {f"{q['id']}#{p['id']}" for q in questions() if stage_of(q) in stages for p in q["parts"]}


def warmup_done(player):
    """The warm-up (done with dig on the student's own machine) unlocks the missions and the dig console."""
    return set(player["solved"]) >= stage_keys("warmup")


def main_done(player):
    """Every warm-up and main part solved: this unlocks the advanced missions."""
    return set(player["solved"]) >= stage_keys("warmup", "main")


def stage_open(player, stage):
    if stage == "main":
        return warmup_done(player)
    if stage == "advanced":
        return main_done(player)
    return True


def public_questions(player):
    """Questions without answers or checks; hint texts only for hints the player already bought.
    A stage that is not open yet shows only its titles."""
    out = []
    for q in questions():
        stage = stage_of(q)
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


def require_admin(headers):
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected and os.environ.get("ADMIN_SECRET_ARN"):
        import boto3

        expected = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["ADMIN_SECRET_ARN"])["SecretString"]
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
        "score": player["score"], "advScore": player.get("advScore", 0), "bonus": player["bonus"],
        "solvedCount": len(done & main), "totalParts": len(main),
        "advSolvedCount": len(done & adv), "advTotalParts": len(adv),
        "unlocked": unlocked(player, session), "advUnlocked": adv_unlocked(player, session),
        "warmupDone": warmup_done(player), "mainDone": main_done(player),
        "questions": public_questions(player),
    }


def require_stage(player, q):
    if not stage_open(player, stage_of(q)):
        raise HttpError(403, "finish every main mission first" if stage_of(q) == "advanced" else "finish the warm-up first")


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
    require_stage(player, q)
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
    session_or_404(code)
    q, part = find_part(str(body.get("qid", "")), str(body.get("part", "")))
    require_stage(player, q)
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
          "lastSolveAt": p.get("lastAdvSolveAt", 0)} for p in players if set(p["solved"]) >= main),
        key=lambda r: (-r["score"], r["lastSolveAt"] or 1 << 60),
    )
    return {
        "session": code, "name": session.get("name", code), "status": session["status"],
        "totalParts": len(main), "players": rows, "firstBloods": store.list_first_bloods(code),
        "advTotalParts": len(adv), "advanced": adv_rows,
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


def admin_close_session(body, headers, query, code):
    require_admin(headers)
    session_or_404(code.upper())
    status = "open" if body.get("status") == "open" else "closed"
    store.set_session_status(code.upper(), status)
    return {"code": code.upper(), "status": status}


ROUTES = {
    ("POST", "/join"): join,
    ("GET", "/state"): state,
    ("POST", "/answer"): answer,
    ("POST", "/hint"): hint,
    ("GET", "/leaderboard"): leaderboard,
    ("GET", "/explanations"): explanations,
    ("POST", "/dig"): dig_console,
    ("POST", "/admin/session"): admin_create_session,
}
CLOSE_RE = re.compile(r"^/admin/session/([A-Za-z0-9-]+)/status$")


def respond(status, payload):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(payload),
    }


def lambda_handler(event, context=None):
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    query = event.get("queryStringParameters") or {}
    try:
        try:
            body = json.loads(event.get("body") or "{}")
        except ValueError:
            raise HttpError(400, "invalid JSON")
        if not isinstance(body, dict):
            raise HttpError(400, "JSON object expected")
        match = CLOSE_RE.match(path)
        if method == "POST" and match:
            return respond(200, admin_close_session(body, headers, query, match.group(1)))
        route = ROUTES.get((method, path))
        if not route:
            raise HttpError(404, "not found")
        return respond(200, route(body, headers, query))
    except HttpError as exc:
        return respond(exc.status, {"error": exc.message})
