import dns.message
import pytest

import checkers


def resp(*lines, rcode="NOERROR"):
    text = f"id 1\nopcode QUERY\nrcode {rcode}\nflags QR RD RA\n;QUESTION\nx. IN A\n;ANSWER\n" + "\n".join(lines)
    return dns.message.from_text(text)


@pytest.fixture
def fake(monkeypatch):
    table = {}

    def q(name, rtype, server="8.8.8.8", ecs=None, recurse=True):
        return table[(name.lower(), rtype, server, ecs)]

    monkeypatch.setattr(checkers, "query", q)
    return table


def test_a_follows_cname(fake):
    fake[("www.airbus.com", "A", "8.8.8.8", None)] = resp(
        "www.airbus.com. 38 IN CNAME b4in5fr.x.incapdns.net.", "b4in5fr.x.incapdns.net. 30 IN A 107.154.76.155")
    part = {"type": "live", "check": {"kind": "rrset", "name": "www.airbus.com", "type": "A"}}
    assert checkers.grade(part, " 107.154.76.155 ")
    assert not checkers.grade(part, "1.2.3.4")
    assert not checkers.grade(part, "")


def test_ipv6_normalised(fake):
    fake[("w.org", "AAAA", "8.8.8.8", None)] = resp("w.org. 1 IN AAAA 2a02:ec80:600:ed1a::1")
    part = {"type": "live", "check": {"kind": "rrset", "name": "w.org", "type": "AAAA"}}
    assert checkers.grade(part, "2A02:EC80:600:ED1A:0:0:0:1")


def test_caa_all(fake):
    fake[("b.com", "CAA", "8.8.8.8", None)] = resp('b.com. 1 IN CAA 0 issue "letsencrypt.org"', 'b.com. 1 IN CAA 0 issue "digicert.com"')
    part = {"type": "live", "check": {"kind": "rrset", "name": "b.com", "type": "CAA", "all": True}}
    assert checkers.grade(part, "digicert.com, letsencrypt.org")
    assert not checkers.grade(part, "digicert.com")


def test_prefix24(fake):
    fake[("g.com", "A", "8.8.8.8", "1.0.1.0/24")] = resp("g.com. 1 IN A 142.250.73.142")
    part = {"type": "live", "check": {"kind": "rrset", "name": "g.com", "type": "A", "ecs": "1.0.1.0/24", "match": "prefix24"}}
    assert checkers.grade(part, "142.250.73.1")
    assert not checkers.grade(part, "142.251.73.142")


def test_mx_primary(fake):
    fake[("apple.com", "MX", "8.8.8.8", None)] = resp("apple.com. 1 IN MX 10 mx-in.g.apple.com.", "apple.com. 1 IN MX 20 other.apple.com.")
    part = {"type": "live", "check": {"kind": "mx_primary", "name": "apple.com"}}
    assert checkers.grade(part, "mx-in.g.apple.com")
    assert not checkers.grade(part, "other.apple.com")


def test_rcode_and_chain(fake):
    fake[("gone.com", "A", "8.8.8.8", None)] = resp(rcode="NXDOMAIN")
    assert checkers.grade({"type": "live", "check": {"kind": "rcode", "name": "gone.com"}}, "NXDOMAIN")
    fake[("l.com", "A", "8.8.8.8", None)] = resp("l.com. 1 IN CNAME a.net.", "a.net. 1 IN CNAME b.net.", "b.net. 1 IN A 1.1.1.1", "b.net. 1 IN A 1.1.1.2")
    part = {"type": "live", "check": {"kind": "chain_len", "name": "l.com"}}
    assert checkers.grade(part, "3") and not checkers.grade(part, "4") and not checkers.grade(part, "three")


def test_txt_has(fake):
    fake[("a.com", "TXT", "8.8.8.8", None)] = resp('a.com. 1 IN TXT "slack-domain-verification=zz"')
    fake[("b.com", "TXT", "8.8.8.8", None)] = resp('b.com. 1 IN TXT "v=spf1"')
    part = {"type": "live", "check": {"kind": "txt_has", "domains": ["a.com", "b.com"], "needle": "slack-domain-verification"}}
    assert checkers.grade(part, "A") and checkers.grade(part, "a.com") and not checkers.grade(part, "b.com")


def test_static_and_mcq():
    assert checkers.grade({"type": "static", "patterns": ["imperva|incapsula"]}, "It's Imperva")
    assert not checkers.grade({"type": "static", "patterns": ["imperva"]}, "cloudflare")
    assert checkers.grade({"type": "mcq", "answer": 1}, 1)
    assert not checkers.grade({"type": "mcq", "answer": 1}, "1")


def test_lookup_failure_is_not_a_wrong_answer(monkeypatch):
    def boom(*a, **k):
        raise checkers.CheckError("timeout")

    monkeypatch.setattr(checkers, "query", boom)
    with pytest.raises(checkers.CheckError):
        checkers.grade({"type": "live", "check": {"kind": "rcode", "name": "x"}}, "nxdomain")
