"""Before a class, run `pytest -m live` to check every live question is still answerable."""
import json
import os

import pytest

import checkers

SECRET = os.path.join(os.path.dirname(__file__), "..", "secret", "questions.json")
pytestmark = pytest.mark.live


def live_parts():
    with open(SECRET, encoding="utf-8") as fh:
        data = json.load(fh)
    return [(f"{q['id']}{p['id']}", p) for q in data["questions"] for p in q["parts"] if p["type"] == "live"]


@pytest.mark.parametrize("pid,part", live_parts(), ids=lambda v: v if isinstance(v, str) else "")
def test_expected_answer_exists(pid, part):
    exp = checkers.expected(part["check"])
    assert exp.get("set") or exp.get("num") is not None, exp
    print(pid, exp)
