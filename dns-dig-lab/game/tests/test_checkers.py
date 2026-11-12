import dns.edns
import dns.message
import pytest

import checkers


def resp(*lines, rcode="NOERROR", edns=False):
    head = "edns 0\n" if edns else ""
    text = f"id 1\nopcode QUERY\nrcode {rcode}\nflags QR RD RA\n{head};QUESTION\nx. IN A\n;ANSWER\n" + "\n".join(lines)
    return dns.message.from_text(text)


@pytest.fixture
def fake(monkeypatch):
    table = {}

    def q(name, rtype, server="8.8.8.8", ecs=None, recurse=True, rdclass="IN", cd=False):
        key = (name.lower(), rtype, server, ecs)
        return table[key + (rdclass, cd) if rdclass != "IN" or cd else key]

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


# ---- advanced kinds ----------------------------------------------------------


def test_chaos_version_accepts_the_upstream_version(fake):
    fake[("version.bind", "TXT", "ns.example", None, "CH", False)] = resp('version.bind. 0 CH TXT "9.20.26-1~deb13u1-Debian"')
    part = {"type": "live", "check": {"kind": "chaos_txt", "name": "version.bind", "server": "ns.example", "match": "version"}}
    assert checkers.grade(part, "9.20.26-1~deb13u1-Debian")
    assert checkers.grade(part, "9.20.26")
    assert not checkers.grade(part, "9.20.2")
    assert not checkers.grade(part, "9")
    assert not checkers.grade(part, "9.18.1")


def test_soa_fields(fake):
    fake[("afnic.fr", "SOA", "8.8.8.8", None)] = resp(
        "afnic.fr. 1 IN SOA dnsmaster.nic.fr. hostmaster.nic.fr. 2026110701 7200 1800 2419200 5400")
    def part(field):
        return {"type": "live", "check": {"kind": "soa_field", "name": "afnic.fr", "field": field}}
    assert checkers.grade(part("rname"), "hostmaster@nic.fr")
    assert not checkers.grade(part("rname"), "hostmaster.nic.fr")
    assert checkers.grade(part("mname"), "dnsmaster.nic.fr.")
    for date in ("2026-11-07", "20261107", "7/11/2026", "07/11/2026"):
        assert checkers.grade(part("serial_date"), date), date
    assert not checkers.grade(part("serial_date"), "2026-07-11")
    assert checkers.grade(part("expire_days"), "28")
    assert checkers.grade(part("minimum"), "5400")


def test_rcode_and_rrset_with_cd(fake):
    fake[("bad.org", "A", "8.8.8.8", None)] = resp(rcode="SERVFAIL")
    fake[("bad.org", "A", "8.8.8.8", None, "IN", True)] = resp("bad.org. 1 IN A 96.99.227.255")
    assert checkers.grade({"type": "live", "check": {"kind": "rcode", "name": "bad.org"}}, "SERVFAIL")
    assert checkers.grade({"type": "live", "check": {"kind": "rrset", "name": "bad.org", "type": "A", "cd": True}}, "96.99.227.255")


def test_ede_code(fake):
    msg = resp(rcode="SERVFAIL", edns=True)
    msg.use_edns(0, options=[dns.edns.EDEOption(9, "No DNSKEY matches DS RRs")])
    fake[("bad.org", "A", "8.8.8.8", None)] = msg
    part = {"type": "live", "check": {"kind": "ede_code", "name": "bad.org"}}
    assert checkers.grade(part, "9") and not checkers.grade(part, "6")


def test_field_picks_one_word(fake):
    fake[("afnic.fr", "DS", "8.8.8.8", None)] = resp("afnic.fr. 1 IN DS 30098 13 2 dea3df8f5147ef21a6bc35f497be6369dad5c988ca6895317d1fe1fdfd24db1d")
    fake[("_imaps._tcp.gmail.com", "SRV", "8.8.8.8", None)] = resp("_imaps._tcp.gmail.com. 1 IN SRV 5 0 993 imap.gmail.com.")
    assert checkers.grade({"type": "live", "check": {"kind": "rrset", "name": "afnic.fr", "type": "DS", "field": 0}}, "30098")
    assert checkers.grade({"type": "live", "check": {"kind": "rrset", "name": "_imaps._tcp.gmail.com", "type": "SRV", "field": 2}}, "993")


def test_nsec_next_name(fake):
    fake[("_dmarc.isc.org", "NSEC", "8.8.8.8", None)] = resp("_dmarc.isc.org. 1 IN NSEC abc._domainkey.isc.org. TXT RRSIG NSEC")
    part = {"type": "live", "check": {"kind": "rrset", "name": "_dmarc.isc.org", "type": "NSEC"}}
    assert checkers.grade(part, "ABC._domainkey.isc.org.")


def test_txt_tag_follows_the_cname(fake):
    fake[("_dmarc.airbus.com", "TXT", "8.8.8.8", None)] = resp(
        "_dmarc.airbus.com. 1 IN CNAME reject.dmarc.airbus.com.", 'reject.dmarc.airbus.com. 1 IN TXT "v=DMARC1;p=reject;fo=1;"')
    part = {"type": "live", "check": {"kind": "txt_tag", "name": "_dmarc.airbus.com", "tag": "p"}}
    assert checkers.grade(part, "reject") and not checkers.grade(part, "none")


def test_null_mx(fake):
    fake[("example.com", "MX", "8.8.8.8", None)] = resp("example.com. 1 IN MX 0 .")
    fake[("iana.org", "MX", "8.8.8.8", None)] = resp("iana.org. 1 IN MX 10 mx.icann.org.")
    part = {"type": "live", "check": {"kind": "null_mx", "domains": ["example.com", "iana.org"]}}
    assert checkers.grade(part, "example.com") and not checkers.grade(part, "iana.org")


def test_txt_contains_yes_no(fake):
    fake[("o-o.myaddr.l.google.com", "TXT", "1.1.1.1", None)] = resp('o-o.myaddr.l.google.com. 1 IN TXT "2400:cb00::1"')
    part = {"type": "live", "check": {"kind": "txt_contains", "name": "o-o.myaddr.l.google.com", "server": "1.1.1.1", "needle": "edns0-client-subnet"}}
    assert checkers.grade(part, "No") and not checkers.grade(part, "yes")
