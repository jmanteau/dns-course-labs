#!/usr/bin/env python3
"""Simulated players for rehearsing the live quiz alone.

    python tools/quiz_bots.py --api http://localhost:8787 --session DEV --bots 20

Each bot joins the session, then answers every question the teacher opens, after a random delay:
right 70% of the time (the answers come from --quiz, secret/quiz.json by default), random otherwise,
a sample sentence for open questions. After a reveal, bots upvote random open answers.
Stop with Ctrl-C. Standard library only.
"""
import argparse
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request

SAMPLES = ["a name with every level up to the root", "it ends with a dot", "globally distributed", "scalable",
           "the primary holds the zone, secondaries copy it", "block a malicious domain", "caches keep old answers",
           "fully qualified domain name", "reliable thanks to caches", "loosely coherent"]


def request(api, method, path, body=None, token=None):
    req = urllib.request.Request(
        api.rstrip("/") + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json", **({"x-token": token} if token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        return {"error": exc.read().decode(), "status": exc.code}


def guess(q, skill, known):
    """An answer to question q: right with probability `skill` when the bot can work it out."""
    right = known.get(q["id"])
    if q["type"] in ("mcq", "poll"):
        return right if right is not None and random.random() < skill else random.randrange(len(q["options"]))
    if q["type"] == "multi":
        if right is not None and random.random() < skill:
            return right
        return sorted(random.sample(range(len(q["options"])), random.randint(1, len(q["options"]))))
    if q["type"] == "static":
        if random.random() >= skill:
            return random.choice(SAMPLES)
        return right if isinstance(right, str) else "13"
    return random.choice(SAMPLES)


def answers_from(path):
    """Right answers by question id, from a quiz spec (empty when the file is not there)."""
    if not path or not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)["questions"]
    known = {q["id"]: q["answer"] for q in spec if "answer" in q}
    known.update({q["id"]: q["accept"][0] for q in spec if q.get("accept")})  # text questions: the first phrase
    return known


def bot(api, session, nick, skill, known, stop):
    joined = request(api, "POST", "/join", {"session": session, "nick": nick})
    if "token" not in joined:
        print(f"{nick}: cannot join: {joined.get('error')}")
        return
    token, answered, voted, known = joined["token"], set(), set(), dict(known)
    while not stop.is_set():
        live = (request(api, "GET", "/quiz", token=token) or {}).get("live")
        if live:
            q = live["question"]
            if live["phase"] == "open" and q["id"] not in answered:
                answered.add(q["id"])
                time.sleep(random.uniform(1, 15))
                request(api, "POST", "/quiz/answer", {"qid": q["id"], "value": guess(q, skill, known)}, token)
            elif live["phase"] == "reveal":
                if "answer" in q:
                    known[q["id"]] = q["answer"]
                if q["id"] not in voted:  # each bot upvotes up to two answers it likes
                    voted.add(q["id"])
                    others = [w for w in live.get("wall", []) if not w.get("mine")]
                    for w in random.sample(others, min(2, len(others))):
                        request(api, "POST", "/quiz/vote", {"qid": q["id"], "id": w["id"]}, token)
        stop.wait(2 + random.random())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--api", default="http://localhost:8787")
    ap.add_argument("--session", default="DEV")
    ap.add_argument("--bots", type=int, default=20)
    ap.add_argument("--skill", type=float, default=0.7)
    ap.add_argument("--quiz", default=os.path.join(os.path.dirname(__file__), "..", "secret", "quiz.json"))
    args = ap.parse_args()
    known = answers_from(args.quiz)
    stop = threading.Event()
    prefix = f"bot{random.randrange(100, 999)}"
    for i in range(args.bots):
        threading.Thread(target=bot, args=(args.api, args.session.upper(), f"{prefix}-{i + 1:02d}", args.skill, known, stop),
                         daemon=True).start()
    print(f"{args.bots} bots ({prefix}-01…) playing in {args.session.upper()} at {args.api}. Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
