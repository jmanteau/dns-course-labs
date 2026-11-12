"""Live quiz: the teacher opens one question at a time, every player answers it, then the teacher reveals.

The questions live in secret/quiz.json, apart from the missions (questions.json):

  {"rounds": [{"id": 1, "title": "..."}],
   "questions": [{"id": "r1q01", "round": 1, "type": "mcq", "text": "...", "options": [...], "answer": 1,
                  "explain": "...", "seconds": 30}]}

Types: mcq (one option), multi (tick all that apply, answer is a list), static (short text), open (free text,
not graded, shown with upvotes) and poll (one option, no right answer).

A multi answer earns partial credit: (right ticks - wrong ticks) / number of right options, never below 0.
So 4 of 6 right options plus 1 wrong one score half the points, and ticking every option scores nothing.

A static answer is right if it matches one of its regex `patterns`, or is close to one of its `accept`
phrases. Close means: after lowercasing, removing accents and punctuation, the phrase is inside the answer,
or some run of the answer's words is at least 85% similar to it. So "fully qualified domaine name" or
"Full Qualifided Domain Name" count for "fully qualified domain name", but "domain name" does not.
"""
import difflib
import json
import os
import re
import unicodedata

import checkers

TYPES = ("mcq", "multi", "static", "open", "poll")
GRADED = ("mcq", "multi", "static")
CHOICE = ("mcq", "multi", "poll")
POINTS, SPEED_BONUS, SPEED_WINDOW = 100, 50, 20  # a right answer, plus up to 50 in the first 20 s
OPEN_MAX = 200
DEFAULT_SECONDS = 30
SIMILAR = 0.85  # how close a text answer must be to an accepted phrase

_spec = None


def load(secret_dir):
    global _spec
    if _spec is None:
        path = os.path.join(secret_dir, "quiz.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                _spec = json.load(fh)
        else:
            _spec = {"rounds": [], "questions": []}
    return _spec


def find(spec, qid):
    return next((q for q in spec["questions"] if q["id"] == qid), None)


def public(q, revealed):
    """What players and the board may see: the answer and its explanation only after the reveal."""
    out = {"id": q["id"], "round": q["round"], "type": q["type"], "text": q["text"],
           "seconds": q.get("seconds", DEFAULT_SECONDS)}
    if q["type"] in CHOICE:
        out["options"] = q["options"]
    if revealed:
        if q["type"] in ("mcq", "multi"):
            out["answer"] = q["answer"]
        if q.get("explain"):
            out["explain"] = q["explain"]
    return out


def clean(q, value):
    """The answer as stored: an option index, a sorted list of indexes, or text. ValueError if malformed."""
    n = len(q.get("options", []))
    if q["type"] in ("mcq", "poll"):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < n:
            raise ValueError("pick one option")
        return value
    if q["type"] == "multi":
        if not isinstance(value, list) or not value or not all(isinstance(v, int) and 0 <= v < n for v in value):
            raise ValueError("tick at least one option")
        return sorted(set(value))
    text = str(value or "").strip()
    if not text:
        raise ValueError("write an answer")
    return text[:OPEN_MAX]


def grade(q, value):
    """True or False for graded types, None for open and poll."""
    if q["type"] == "multi":
        return sorted(value) == sorted(q["answer"])
    if q["type"] == "mcq":
        return checkers.grade({"type": "mcq", "answer": q["answer"]}, value)
    if q["type"] == "static":
        by_pattern = bool(q.get("patterns")) and checkers.grade({"type": "static", "patterns": q["patterns"]}, value)
        return by_pattern or any(close_enough(value, phrase) for phrase in q.get("accept", []))
    return None


def credit(q, value):
    """Share of the points an answer earns, from 0 to 1: partial for multi, all or nothing otherwise."""
    if q["type"] == "multi":
        right = set(q["answer"])
        hits, wrong = len(right & set(value)), len(set(value) - right)
        return max(0, hits - wrong) / len(right)
    return 1 if grade(q, value) else 0


def normalise(text):
    """Lowercase, no accents, words separated by single spaces."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def close_enough(answer, phrase):
    """The phrase is in the answer, or some run of the answer's words is at least SIMILAR to it."""
    answer, phrase = normalise(answer), normalise(phrase)
    if not answer or not phrase:
        return False
    if f" {phrase} " in f" {answer} ":
        return True
    words, n = answer.split(), len(phrase.split())
    for size in (n - 1, n, n + 1):
        for start in range(max(1, len(words) - size + 1)):
            window = " ".join(words[start:start + size])
            if window and difflib.SequenceMatcher(None, window, phrase).ratio() >= SIMILAR:
                return True
    return False


def points(credit, opened_at, at):
    """The full points (100 plus the speed bonus) times the credit: True counts as 1, False as 0."""
    if not credit:
        return 0
    elapsed = max(0, at - opened_at)
    return round(credit * (POINTS + SPEED_BONUS * max(0, SPEED_WINDOW - elapsed) / SPEED_WINDOW))


def counts(q, answers):
    """Answers per option (choice types), or per right/wrong (static)."""
    if q["type"] in CHOICE:
        out = [0] * len(q["options"])
        for a in answers:
            for v in a["value"] if isinstance(a["value"], list) else [a["value"]]:
                # answers saved before the question changed type (e.g. text) are left out, never crash
                if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < len(out):
                    out[v] += 1
        return out
    if q["type"] == "static":
        right = sum(1 for a in answers if a.get("correct"))
        return [right, len(answers) - right]
    return []


def check(spec):
    """Problems in a quiz spec, as a list of messages (empty when it is valid)."""
    errors = []
    rounds = {r["id"] for r in spec.get("rounds", [])}
    seen = set()
    for q in spec.get("questions", []):
        qid = q.get("id", "?")
        if qid in seen:
            errors.append(f"{qid}: duplicate id")
        seen.add(qid)
        if q.get("type") not in TYPES:
            errors.append(f"{qid}: unknown type {q.get('type')!r}")
            continue
        if q.get("round") not in rounds:
            errors.append(f"{qid}: unknown round {q.get('round')!r}")
        if not str(q.get("text", "")).strip():
            errors.append(f"{qid}: no text")
        n = len(q.get("options", []))
        if q["type"] in CHOICE and n < 2:
            errors.append(f"{qid}: needs at least 2 options")
        if q["type"] == "mcq" and not (isinstance(q.get("answer"), int) and 0 <= q["answer"] < n):
            errors.append(f"{qid}: answer must be an option index")
        if q["type"] == "multi" and not (isinstance(q.get("answer"), list) and q["answer"]
                                         and all(isinstance(a, int) and 0 <= a < n for a in q["answer"])):
            errors.append(f"{qid}: answer must be a list of option indexes")
        if q["type"] == "static":
            if not q.get("patterns") and not q.get("accept"):
                errors.append(f"{qid}: needs patterns or accept phrases")
            if any(not isinstance(a, str) or not normalise(a) for a in q.get("accept", [])):
                errors.append(f"{qid}: accept phrases must be non-empty text")
            try:
                for p in q.get("patterns", []):
                    re.compile(p)
            except re.error as exc:
                errors.append(f"{qid}: bad patterns ({exc})")
    for r in rounds:
        if not any(q.get("round") == r for q in spec.get("questions", [])):
            errors.append(f"round {r}: no questions")
    return errors


if __name__ == "__main__":
    # python backend/quiz.py check secret/quiz.json
    import sys

    with open(sys.argv[2], encoding="utf-8") as fh:
        spec = json.load(fh)
    problems = check(spec)
    for p in problems:
        print(p)
    by_round = {r["id"]: sum(1 for q in spec["questions"] if q["round"] == r["id"]) for r in spec["rounds"]}
    print(f"{len(spec['questions'])} questions, rounds {by_round}: {'errors' if problems else 'ok'}")
    sys.exit(1 if problems else 0)
