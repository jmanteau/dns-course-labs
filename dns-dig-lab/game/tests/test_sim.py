"""End to end against the local simulation (`make sim-test`): the game zone, the game server and a resolver
in containers. The right answers come from the private specs, then go through the real grading and console."""
import json
import os

import pytest

import checkers
import dig

SECRET = os.path.join(os.path.dirname(__file__), "..", "secret")
pytestmark = pytest.mark.sim


def load(name):
    with open(os.path.join(SECRET, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def specs():
    if not os.environ.get("QUEST_RESOLVER"):
        pytest.skip("runs inside the local simulation: make sim-test")
    parts = {f"{q['id']}{p['id']}": p for q in load("questions.json")["questions"] for p in q["parts"]}
    return parts, load("zone.json"), load("server.json")


def record(spec, name, rtype):
    return next(r for r in spec["records"] if r["name"] == name and r["type"] == rtype)


def test_answers_are_graded_against_the_local_dns(specs):
    parts, zone, server = specs
    mx = sorted(v.split() for v in record(zone, "vault", "MX")["values"])
    srv = record(zone, "_quest._tcp.gatekeeper", "SRV")["values"][0].split()
    cases = [("a15a", mx[0][1], mx[1][1]), ("a15b", srv[2], "53"), ("a23a", server["server_id"], server["hostname"]),
             ("a24b", "REFUSED", "NOERROR"), ("a25c", "REFUSED", "NOERROR")]
    for pid, right, wrong in cases:
        assert checkers.grade(parts[pid], right), pid
        assert not checkers.grade(parts[pid], wrong), pid


def test_console_toward_the_game_server(specs):
    _, _, server = specs
    ns = dig.GAME_SERVER
    out = dig.run({"names": "version.bind", "type": "TXT", "class": "CH", "server": ns, "short": True})["output"]
    assert server["version"] in out
    axfr = next(z for z in server["zones"] if z.get("transfer"))
    out = dig.run({"names": axfr["name"], "type": "AXFR", "server": ns})["output"]
    assert all(f"{r['name']}.{axfr['name']}." in out for r in axfr["records"] if r["name"] != "@")
    walk = next(z for z in server["zones"] if z.get("dnssec"))
    assert "Transfer failed" in dig.run({"names": walk["name"], "type": "AXFR", "server": ns})["output"]
    door = server["alt_zones"][0]
    out = dig.run({"names": door["name"], "type": "TXT", "server": ns, "port": server["alt_port"], "short": True})["output"]
    assert door["records"][0]["values"][0] in out
    assert "status: REFUSED" in dig.run({"names": "google.com", "server": ns})["output"]
    with pytest.raises(dig.DigError):
        dig.run({"names": axfr["name"], "type": "AXFR", "server": "cloudflare"})


def test_console_default_resolver_sees_the_game_zone(specs):
    _, zone, _ = specs
    out = dig.run({"names": f"start.{zone['zone']}", "type": "TXT", "short": True})["output"]
    assert record(zone, "start", "TXT")["values"][0] in out
