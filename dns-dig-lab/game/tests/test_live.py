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


def test_dig_console_reaches_real_dns():
    import dig

    assert "status: NOERROR" in dig.run({"names": "example.com"})["output"]
    assert "root-servers.net" in dig.run({"names": "example.com", "trace": True})["output"]


# ---- the game zone (advanced missions a15-a20): is what the spec describes really published? ----

ZONE_SPEC = os.path.join(os.path.dirname(__file__), "..", "secret", "zone.json")


def zone_sets():
    if not os.path.isfile(ZONE_SPEC):
        return []
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "infra"))
    import game_zone

    with open(ZONE_SPEC, encoding="utf-8") as fh:
        return game_zone.build(json.load(fh), os.path.dirname(ZONE_SPEC))


def r53_txt(value):
    """The strings of a Route 53 TXT value as bytes (Route 53 reads \\ooo escapes as octal)."""
    import re

    out = []
    for s in re.findall(r'"((?:[^"\\]|\\.)*)"', value):
        out.append(re.sub(rb"\\([0-7]{3})|\\(.)", lambda m: bytes([int(m.group(1), 8)]) if m.group(1) else m.group(2),
                          s.encode()))
    return tuple(out)


@pytest.mark.parametrize("rs", zone_sets(), ids=lambda rs: f"{rs['type']} {rs['name']}")
def test_game_zone_is_published(rs):
    import dns.rdata
    import dns.rdataclass
    import dns.rdatatype

    resp = checkers.query(rs["name"], rs["type"])
    rtype = dns.rdatatype.from_text(rs["type"])
    got = [r for rrset in resp.answer if rrset.rdtype == rtype and rrset.name.to_text() == rs["name"] for r in rrset]
    if rs["type"] == "TXT":
        assert sorted(tuple(r.strings) for r in got) == sorted(r53_txt(v) for v in rs["values"])
    else:
        want = {dns.rdata.from_text(dns.rdataclass.IN, rtype, v) for v in rs["values"]}
        assert set(got) == want


def test_existing_name_blocks_the_wildcard():
    """Mission a17 says fox.wild (an A record only) gets NODATA for TXT, not the wildcard's text."""
    spec = zone_sets()
    if not spec:
        pytest.skip("no game zone spec")
    zone = next(rs["name"] for rs in spec if rs["name"].startswith("*.wild.")).removeprefix("*.wild.")
    resp = checkers.query(f"fox.wild.{zone}", "TXT")
    assert resp.rcode() == 0 and not resp.answer
    assert checkers.query(f"zebra.wild.{zone}", "TXT").answer


# ---- the game server (missions a21-a25): does the BIND instance serve what the spec describes? ----

SERVER_SPEC = os.path.join(os.path.dirname(__file__), "..", "secret", "server.json")


@pytest.fixture(scope="module")
def server():
    if not os.path.isfile(SERVER_SPEC):
        pytest.skip("no game server spec")
    with open(SERVER_SPEC, encoding="utf-8") as fh:
        spec = json.load(fh)
    return spec, checkers.server_ip(f"{spec['server']}.{spec['game_zone']}")


def txt_of(resp):
    return {b"".join(r.strings).decode() for rrset in resp.answer for r in rrset if hasattr(r, "strings")}


def test_game_server_names_itself(server):
    spec, ip = server
    for name, key in (("version.bind", "version"), ("hostname.bind", "hostname"), ("id.server", "server_id")):
        assert txt_of(checkers.query(name, "TXT", ip, recurse=False, rdclass="CH")) == {spec[key]}


def test_game_server_zones(server):
    import dns.query
    import dns.rcode
    import dns.zone

    spec, ip = server
    for zone in spec["zones"]:
        name = zone["name"]
        if zone.get("transfer"):
            got = dns.zone.from_xfr(dns.query.xfr(ip, name, lifetime=10))
            want = {(r["name"], r["type"]) for r in zone["records"]}
            have = {(n.to_text(), dns.rdatatype.to_text(rds.rdtype)) for n, node in got.nodes.items() for rds in node.rdatasets}
            assert want <= have
        if zone.get("dnssec"):  # walk the chain: every name of the spec, in order, and back to the start
            owners, current = [], name + "."
            for _ in range(50):
                (rr,) = [r for rrset in checkers.query(current, "NSEC", ip, recurse=False).answer for r in rrset]
                owners.append(current)
                current = rr.next.to_text()
                if current == name + ".":
                    break
            want = {name + "."} | {f"{r['name']}.{name}." for r in zone["records"] if r["name"] != "@"}
            assert set(owners) == want
        apex_txt = [v for r in zone["records"] if r["name"] == "@" and r["type"] == "TXT" for v in r["values"]]
        if apex_txt:
            assert txt_of(checkers.query(name, "TXT", ip, recurse=False)) == set(apex_txt)
    assert checkers.query("google.com", "A", ip).rcode() == dns.rcode.REFUSED  # never an open resolver


def test_game_server_alt_port(server):
    import dns.message
    import dns.query

    spec, ip = server
    for zone in spec.get("alt_zones", []):
        want = {v for r in zone["records"] if r["name"] == "@" and r["type"] == "TXT" for v in r["values"]}
        resp = dns.query.udp(dns.message.make_query(zone["name"], "TXT"), ip, port=spec["alt_port"], timeout=3)
        assert txt_of(resp) == want


# ---- the advanced missions keep their commands behind hints ----


def test_advanced_hints_ladder():
    """No dig command in an advanced mission's text or labels (a03's faulty commands are its puzzle);
    every part has 3 hints, concept, ingredients, command, and a command appears only in the third."""
    import re

    with open(SECRET, encoding="utf-8") as fh:
        questions = [q for q in json.load(fh)["questions"] if q.get("stage") == "advanced"]
    command = re.compile(r"`[^`]*\bdig\b[^`]*`")
    for q in questions:
        if q["id"] != "a03":
            assert not command.search(q["prompt"]), q["id"]
        for p in q["parts"]:
            where = f"{q['id']}{p['id']}"
            if q["id"] != "a03":
                assert not command.search(p["label"]), where
            assert len(p["hints"]) == 3, where
            assert not any(command.search(h) for h in p["hints"][:2]), where
