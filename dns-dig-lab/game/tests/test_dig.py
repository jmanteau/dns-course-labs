import dns.message
import pytest

import dig
import handler
from test_handler import call, join, session, warmed  # noqa: F401  (fixtures)


def msg(question, *sections, rcode="NOERROR", flags="QR RD RA"):
    """A response; `sections` are ';ANSWER', ';AUTHORITY', ';ADDITIONAL' headers and record lines."""
    text = f"id 7\nopcode QUERY\nrcode {rcode}\nflags {flags}\nedns 0\npayload 1232\n;QUESTION\n{question}\n" + "\n".join(sections)
    return dns.message.from_text(text)


class Table(dict):
    """Fake answers, plus `sent`: every query made."""


@pytest.fixture
def fake(monkeypatch):
    """Answers keyed by (name, type, server); records every query sent."""
    table, sent = Table(), []

    def send(name, rtype, server, recurse=True, dnssec=False, tcp=False, subnet=None, rdclass="IN", nsid=False, cd=False,
             port=53):
        name = str(name).lower()
        sent.append((name, rtype, server, recurse))
        table.opts.append({"rdclass": rdclass, "nsid": nsid, "cd": cd, "port": port})
        if (name, rtype, server) not in table:
            raise dig.Failed(f";; communications error to {server}#53: timed out")
        return table[(name, rtype, server)], "TCP" if tcp else "UDP", 12

    monkeypatch.setattr(dig, "send", send)
    table.sent, table.opts = sent, []
    return table


def test_full_output_looks_like_dig(fake):
    fake[("www.example.com", "A", "8.8.8.8")] = msg(
        "www.example.com. IN A", ";ANSWER",
        "www.example.com. 300 IN CNAME a1422.dscr.akamai.net.", "a1422.dscr.akamai.net. 20 IN A 23.72.250.233")
    res = dig.run({"names": "www.example.com"})
    assert res["command"] == "dig @8.8.8.8 www.example.com A"
    out = res["output"]
    assert ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 7" in out
    assert ";; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1" in out
    assert ";; ANSWER SECTION:" in out and "IN CNAME  a1422.dscr.akamai.net." in out
    assert ";; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)" in out


def test_short_and_options(fake):
    fake[("airbus.com", "MX", "1.1.1.1")] = msg("airbus.com. IN MX", ";ANSWER", "airbus.com. 300 IN MX 4 mx1.myeers.net.")
    res = dig.run({"names": "airbus.com", "type": "mx", "server": "cloudflare", "short": True, "tcp": True})
    assert res == {"command": "dig @1.1.1.1 airbus.com MX +short +tcp", "output": "4 mx1.myeers.net.\n"}


def test_several_names_put_options_first(fake):
    for n in ("a.fr", "b.fr"):
        fake[(n, "TXT", "8.8.8.8")] = msg(f"{n}. IN TXT", ";ANSWER", f'{n}. 60 IN TXT "v=spf1 -all"')
    res = dig.run({"names": "a.fr, b.fr", "type": "TXT", "short": True})
    assert res["command"] == "dig @8.8.8.8 +short a.fr TXT b.fr TXT"
    assert res["output"].count("v=spf1") == 2


def test_ip_is_a_reverse_lookup(fake):
    fake[("8.8.8.8.in-addr.arpa.", "PTR", "8.8.8.8")] = msg(
        "8.8.8.8.in-addr.arpa. IN PTR", ";ANSWER", "8.8.8.8.in-addr.arpa. 60 IN PTR dns.google.")
    res = dig.run({"names": "8.8.8.8", "short": True})
    assert res["command"] == "dig @8.8.8.8 -x 8.8.8.8 +short"
    assert res["output"] == "dns.google.\n"


def test_nodata_shows_the_soa(fake):
    fake[("impots.gouv.fr", "AAAA", "8.8.8.8")] = msg(
        "impots.gouv.fr. IN AAAA", ";AUTHORITY", "impots.gouv.fr. 3600 IN SOA dns0.x. host.x. 1 2 3 4 3600")
    out = dig.run({"names": "impots.gouv.fr", "type": "AAAA"})["output"]
    assert "ANSWER: 0, AUTHORITY: 1" in out and ";; AUTHORITY SECTION:" in out


def test_authoritative_asks_the_zone_ns_without_recursion(fake):
    fake[("example.com", "SOA", "8.8.8.8")] = msg("example.com. IN SOA", ";ANSWER", "example.com. 300 IN SOA ns1.x. h.x. 1 2 3 4 5")
    fake[("example.com.", "NS", "8.8.8.8")] = msg("example.com. IN NS", ";ANSWER", "example.com. 300 IN NS ns1.example.com.")
    fake[("ns1.example.com.", "A", "8.8.8.8")] = msg("ns1.example.com. IN A", ";ANSWER", "ns1.example.com. 300 IN A 192.0.2.53")
    fake[("example.com", "A", "192.0.2.53")] = msg(
        "example.com. IN A", ";ANSWER", "example.com. 300 IN A 192.0.2.1", flags="QR AA")
    res = dig.run({"names": "example.com", "server": "authoritative"})
    assert res["command"] == "dig @ns1.example.com example.com A +norecurse"
    assert ";; flags: qr aa;" in res["output"]
    assert ("example.com", "A", "192.0.2.53", False) in fake.sent


def test_trace_follows_referrals(fake):
    fake[(".", "NS", "8.8.8.8")] = msg(". IN NS", ";ANSWER", ". 518400 IN NS a.root-servers.net.")
    fake[("a.root-servers.net.", "A", "8.8.8.8")] = msg("a.root-servers.net. IN A", ";ANSWER", "a.root-servers.net. 1 IN A 198.41.0.4")
    fake[("example.com", "A", "198.41.0.4")] = msg(
        "example.com. IN A", ";AUTHORITY", "com. 172800 IN NS a.gtld-servers.net.",
        ";ADDITIONAL", "a.gtld-servers.net. 172800 IN A 192.5.6.30", flags="QR")
    fake[("example.com", "A", "192.5.6.30")] = msg(
        "example.com. IN A", ";AUTHORITY", "example.com. 172800 IN NS ns1.example.net.", flags="QR")
    fake[("ns1.example.net.", "A", "8.8.8.8")] = msg("ns1.example.net. IN A", ";ANSWER", "ns1.example.net. 1 IN A 192.0.2.53")
    fake[("example.com", "A", "192.0.2.53")] = msg("example.com. IN A", ";ANSWER", "example.com. 300 IN A 192.0.2.1", flags="QR AA")
    res = dig.run({"names": "example.com", "trace": True})
    assert res["command"] == "dig example.com A +trace"
    out = res["output"]
    assert "from 198.41.0.4#53(a.root-servers.net.)" in out
    assert "from 192.5.6.30#53(a.gtld-servers.net.)" in out
    assert "from 192.0.2.53#53(ns1.example.net.)" in out
    assert out.index("com.  ") < out.index("example.com.                    300")


def test_timeout_is_printed_not_raised(fake):
    out = dig.run({"names": "slow.example"})["output"]
    assert ";; communications error to 8.8.8.8#53: timed out" in out


@pytest.mark.parametrize("body", [
    {"names": ""},
    {"names": "a b c d e f"},
    {"names": "bad name!"},
    {"names": "x.com", "type": "AXFR"},
    {"names": "x.com", "type": "ANY"},
    {"names": "x.com", "server": "10.0.0.1"},
    {"names": "x.com", "server": "127.0.0.1"},
    {"names": "x.com", "server": "169.254.169.254"},
    {"names": "x.com", "server": "ns1.internal"},
    {"names": "x.com", "subnet": "nope"},
    {"names": "a.com b.com", "trace": True},
    {"names": "version.bind", "type": "TXT", "class": "HS"},
    {"names": "version.bind", "type": "A", "class": "CH"},
    {"names": "version.bind", "type": "TXT", "class": "CH", "trace": True},
    {"names": "x.com", "server": "localhost"},
    {"names": "x.com", "type": "AXFR"},
    {"names": "x.com", "port": "8053"},
    {"names": "x.com", "port": "99999"},
    {"names": "x.com", "port": "abc"},
])
def test_bad_requests(body, fake):
    with pytest.raises(dig.DigError):
        dig.run(body)


def test_route_needs_a_player_and_is_rate_limited(session, fake, monkeypatch):  # noqa: F811
    monkeypatch.setattr(handler, "_dig_calls", {})
    assert call("POST", "/dig", {"names": "x.com"})[0] == 401
    assert call("POST", "/dig", {"names": "x.com"}, join("bob"))[0] == 403  # before the warm-up
    tok = warmed("alice")
    assert call("POST", "/dig", {"names": "x.com", "server": "10.0.0.1"}, tok)[0] == 400
    for _ in range(handler.DIG_LIMIT - 1):
        assert call("POST", "/dig", {"names": "x.com"}, tok)[0] == 200
    status, body = call("POST", "/dig", {"names": "x.com"}, tok)
    assert status == 429 and "wait" in body["error"]


def test_chaos_class_to_a_server_name(fake):
    fake[("f.root-servers.net", "A", "8.8.8.8")] = msg("f.root-servers.net. IN A", ";ANSWER", "f.root-servers.net. 60 IN A 192.5.5.241")
    fake[("hostname.bind", "TXT", "192.5.5.241")] = msg(
        "hostname.bind. CH TXT", ";ANSWER", 'hostname.bind. 60 CH TXT "CDG.cf.f.root-servers.org"', flags="QR AA")
    res = dig.run({"names": "hostname.bind", "type": "TXT", "class": "ch", "server": "f.root-servers.net."})
    assert res["command"] == "dig @f.root-servers.net hostname.bind CH TXT"
    assert "CH TXT    \"CDG.cf.f.root-servers.org\"" in res["output"] and ";hostname.bind.                 CH TXT" in res["output"]
    assert ";; SERVER: 192.5.5.241#53(f.root-servers.net) (UDP)" in res["output"]
    assert fake.opts[-1]["rdclass"] == "CH"


def test_server_name_must_resolve_to_a_public_address(fake):
    fake[("ns.evil.example", "A", "8.8.8.8")] = msg("ns.evil.example. IN A", ";ANSWER", "ns.evil.example. 60 IN A 10.1.2.3")
    with pytest.raises(dig.DigError, match="not a public address"):
        dig.run({"names": "x.com", "server": "ns.evil.example"})
    with pytest.raises(dig.DigError, match="cannot find"):
        dig.run({"names": "x.com", "server": "unknown.example"})


def test_nsid_and_ede_are_printed(fake):
    import dns.edns

    resp = msg("dnssec-failed.org. IN A", rcode="SERVFAIL")
    resp.use_edns(0, payload=1232, options=[dns.edns.GenericOption(dns.edns.OptionType.NSID, b"bg-goz-aa"),
                                           dns.edns.EDEOption(9, "No DNSKEY matches DS RRs of dnssec-failed.org")])
    fake[("dnssec-failed.org", "A", "8.8.8.8")] = resp
    res = dig.run({"names": "dnssec-failed.org", "nsid": True, "cd": False})
    assert res["command"] == "dig @8.8.8.8 dnssec-failed.org A +nsid"
    assert '; NSID: 62 67 2d 67 6f 7a 2d 61 61 ("bg-goz-aa")' in res["output"]
    assert "; EDE: 9 (DNSKEY Missing): (No DNSKEY matches DS RRs of dnssec-failed.org)" in res["output"]
    assert fake.opts[-1]["nsid"] is True


def test_cd_is_sent_and_shown(fake):
    fake[("dnssec-failed.org", "A", "8.8.8.8")] = msg("dnssec-failed.org. IN A", ";ANSWER", "dnssec-failed.org. 60 IN A 96.99.227.255")
    res = dig.run({"names": "dnssec-failed.org", "cd": True, "short": True})
    assert res == {"command": "dig @8.8.8.8 dnssec-failed.org A +short +cd", "output": "96.99.227.255\n"}
    assert fake.opts[-1]["cd"] is True


@pytest.fixture
def game(fake, monkeypatch):
    """A game server at 94.23.1.53, reachable by name."""
    monkeypatch.setattr(dig, "GAME_SERVER", "ns.quest.example.org")
    fake[("ns.quest.example.org", "A", "8.8.8.8")] = msg("ns.quest.example.org. IN A", ";ANSWER", "ns.quest.example.org. 60 IN A 94.23.1.53")
    return fake


def test_axfr_and_port_only_toward_the_game_server(game):
    for body in ({"names": "x.com", "type": "AXFR", "server": "8.8.8.8"},
                 {"names": "x.com", "port": 8053, "server": "cloudflare"},
                 {"names": "x.com", "type": "AXFR", "server": "authoritative"},
                 {"names": "a.com b.com", "type": "AXFR", "server": "ns.quest.example.org"},
                 {"names": "version.bind", "type": "TXT", "class": "CH", "port": 8053, "server": "ns.quest.example.org"}):
        with pytest.raises(dig.DigError):
            dig.run(body)


def test_port_is_used_and_shown(game):
    game[("door.quest.example.org", "TXT", "94.23.1.53")] = msg(
        "door.quest.example.org. IN TXT", ";ANSWER", 'door.quest.example.org. 60 IN TXT "hello"', flags="QR AA")
    res = dig.run({"names": "door.quest.example.org", "type": "TXT", "port": "8053", "server": "ns.quest.example.org"})
    assert res["command"] == "dig @ns.quest.example.org -p 8053 door.quest.example.org TXT"
    assert ";; SERVER: 94.23.1.53#8053(ns.quest.example.org) (UDP)" in res["output"]
    assert game.opts[-1]["port"] == 8053


def test_axfr_prints_the_zone(game, monkeypatch):
    import dns.exception

    zone = msg("axfr.quest.example.org. IN AXFR", ";ANSWER",
               "axfr.quest.example.org. 300 IN SOA ns.quest.example.org. h.quest.example.org. 1 3600 600 86400 300",
               "www.axfr.quest.example.org. 300 IN A 192.0.2.10",
               "axfr.quest.example.org. 300 IN SOA ns.quest.example.org. h.quest.example.org. 1 3600 600 86400 300", flags="QR AA")
    calls = []

    def xfr(server, name, port=53, lifetime=None, relativize=True):
        assert relativize is False  # dig prints full names
        calls.append((server, name, port))
        if name == "walk.quest.example.org":
            raise dns.exception.FormError("REFUSED")
        yield zone

    monkeypatch.setattr(dig.dns.query, "xfr", xfr)
    res = dig.run({"names": "axfr.quest.example.org", "type": "AXFR", "server": "ns.quest.example.org"})
    assert res["command"] == "dig @ns.quest.example.org axfr.quest.example.org AXFR"
    assert "IN A      192.0.2.10" in res["output"]
    # from_text merges the two SOA lines; a real transfer keeps one record per set, like dig counts them
    assert ";; XFR size: 2 records (messages 1, bytes" in res["output"]
    assert calls == [("94.23.1.53", "axfr.quest.example.org", 53)]
    out = dig.run({"names": "walk.quest.example.org", "type": "AXFR", "server": "ns.quest.example.org"})["output"]
    assert "; Transfer failed." in out


def test_private_servers_only_in_the_allowed_network(fake, monkeypatch):
    with pytest.raises(dig.DigError, match="not a public address"):
        dig.parse_server("10.53.0.53")
    monkeypatch.setattr(dig, "ALLOW_NET", dig.ipaddress.ip_network("10.53.0.0/24"))
    assert dig.parse_server("10.53.0.53") == ("10.53.0.53", "10.53.0.53")
    with pytest.raises(dig.DigError):
        dig.parse_server("10.0.0.1")
