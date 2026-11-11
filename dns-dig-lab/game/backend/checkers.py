"""Answer checkers for Dig Quest.

Data questions are graded against a live DNS lookup (`expected()`), so they never go
stale. Conceptual questions use static regexes or multiple choice.
"""
import hashlib
import ipaddress
import json
import os
import re
import time

import dns.edns
import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.resolver

DEFAULT_SERVER = os.environ.get("QUEST_RESOLVER", "8.8.8.8")  # local simulation: its own resolver
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class CheckError(Exception):
    """The live lookup needed to grade an answer failed (not the student's fault)."""


def query(name, rtype, server=DEFAULT_SERVER, ecs=None, recurse=True, rdclass="IN", cd=False):
    """Send one DNS query and return the response message. `server` may be an IP or a hostname."""
    options = []
    if ecs:
        net, _, bits = ecs.partition("/")
        options.append(dns.edns.ECSOption(net, int(bits or 24)))
    msg = dns.message.make_query(name, rtype, rdclass=dns.rdataclass.from_text(rdclass), use_edns=0, options=options)
    if not recurse:
        msg.flags &= ~dns.flags.RD
    if cd:
        msg.flags |= dns.flags.CD
    server = server_ip(server)
    for attempt in (1, 2):  # small servers drop the odd UDP packet: one retry
        try:
            resp = dns.query.udp(msg, server, timeout=3)
            if resp.flags & dns.flags.TC:
                resp = dns.query.tcp(msg, server, timeout=4)
            return resp
        except dns.exception.Timeout as exc:
            if attempt == 2:
                raise CheckError(f"lookup of {name} {rtype} via {server} failed: {exc}") from exc
        except Exception as exc:
            raise CheckError(f"lookup of {name} {rtype} via {server} failed: {exc}") from exc


def server_ip(server):
    """An IP address as is; a hostname resolved through the default resolver."""
    try:
        return str(ipaddress.ip_address(server))
    except ValueError:
        addrs = sorted(rdata_values(query(server, "A"), "A"))
        if not addrs:
            raise CheckError(f"no address for server {server}")
        return addrs[0]


def rdata_values(resp, rtype):
    """Normalised values of the answer-section records of the given type."""
    want = dns.rdatatype.from_text(rtype)
    out = set()
    for rrset in resp.answer:
        if rrset.rdtype == want:
            out.update(norm_rdata(rtype, r) for r in rrset)
    return out


def norm_rdata(rtype, rdata):
    if rtype == "CAA":
        return rdata.value.decode().lower()
    if rtype == "MX":
        return norm_name(rdata.exchange.to_text())
    if rtype in ("NS", "PTR", "CNAME"):
        return norm_name(rdata.to_text())
    if rtype == "NSEC":
        return norm_name(rdata.next.to_text())
    if rtype in ("A", "AAAA"):
        return str(ipaddress.ip_address(rdata.address))
    return rdata.to_text().strip('"').lower()


def norm_name(text):
    return text.strip().strip('"').lower().rstrip(".")


def norm_answer(rtype, text):
    """Normalise what the student typed, like norm_rdata does for DNS data."""
    text = text.strip()
    if rtype in ("A", "AAAA"):
        try:
            return str(ipaddress.ip_address(text))
        except ValueError:
            return text.lower()
    if rtype == "DATE":
        return norm_date(text)
    return norm_name(text)


def norm_date(text):
    """2026-08-23, 20260823 or 23/08/2026 -> 2026-08-23 (anything else is returned lowercased)."""
    m = re.fullmatch(r"(\d{4})-?(\d{2})-?(\d{2})", text)
    if m:
        return "-".join(m.groups())
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return text.lower()


# ---- expected values ---------------------------------------------------------


def expected(check):
    """Compute what a correct answer is right now. Returns {'set': {...}} or {'num': n, 'tol': t}."""
    kind = check["kind"]
    return KINDS[kind](check)


def _rrset(check):
    """The records of a name. `field` keeps one word of each record (e.g. 2 = the port of an SRV)."""
    resp = query(check["name"], check["type"], check.get("server", DEFAULT_SERVER), check.get("ecs"), cd=check.get("cd", False))
    values = rdata_values(resp, check["type"])
    if not values:
        raise CheckError(f"no {check['type']} answer for {check['name']}")
    rtype = check["type"]
    if "field" in check:
        values, rtype = {norm_name(v.split()[check["field"]]) for v in values}, "FIELD"
    return {"set": values, "match": check.get("match", "exact"), "all": check.get("all", False), "rtype": rtype}


def _mx_primary(check):
    resp = query(check["name"], "MX")
    rrs = [r for rrset in resp.answer if rrset.rdtype == dns.rdatatype.MX for r in rrset]
    if not rrs:
        raise CheckError("no MX")
    best = min(r.preference for r in rrs)
    return {"set": {norm_name(r.exchange.to_text()) for r in rrs if r.preference == best}, "rtype": "MX"}


def _rcode(check):
    resp = query(check["name"], check.get("type", "A"), check.get("server", DEFAULT_SERVER), cd=check.get("cd", False))
    return {"set": {dns.rcode.to_text(resp.rcode()).lower()}, "rtype": "RCODE"}


def _chain_len(check):
    """Number of distinct owner names in the answer chain (CNAMEs + final address records)."""
    resp = query(check["name"], check.get("type", "A"))
    names = {norm_name(rrset.name.to_text()) for rrset in resp.answer}
    if not names:
        raise CheckError("empty chain")
    return {"num": len(names), "tol": 0}


def _auth_ttl(check):
    """TTL returned by an authoritative server of the zone (not the decreasing cached TTL)."""
    zone, rtype = check["name"], check.get("type", "NS")
    ns = sorted(rdata_values(query(zone, "NS"), "NS"))
    if not ns:
        raise CheckError("no NS")
    addr = sorted(rdata_values(query(ns[0], "A"), "A"))
    if not addr:
        raise CheckError("no address for authoritative server")
    resp = query(zone, rtype, server=addr[0], recurse=False)
    ttls = {rrset.ttl for rrset in resp.answer if rrset.rdtype == dns.rdatatype.from_text(rtype)}
    if not ttls:
        raise CheckError("authoritative server returned no answer")
    return {"num": max(ttls), "tol": 0}


def _txt_has(check):
    """Which of the listed domains publish a TXT record containing the needle."""
    needle = check["needle"].lower()
    hits = set()
    for domain in check["domains"]:
        resp = query(domain, "TXT")
        if any(needle in v for v in rdata_values(resp, "TXT")):
            hits.add(domain.lower())
            hits.add(domain.lower().split(".")[0])
    return {"set": hits, "rtype": "TXT-HAS"}


def _txt_count(check):
    """Count the domains of a file whose TXT records contain the needle."""
    needle = check["needle"].lower()
    path = os.path.join(DATA_DIR, check.get("file", "list100.txt"))
    with open(path, encoding="utf-8") as fh:
        domains = [line.strip() for line in fh if line.strip()]
    count = 0
    for domain in domains:
        try:
            resp = query(domain, "TXT")
        except CheckError:
            continue
        if any(needle in v for v in rdata_values(resp, "TXT")):
            count += 1
    return {"num": count, "tol": check.get("tolerance", 1)}


def _chaos_txt(check):
    """What a server says about itself (CH TXT version.bind, hostname.bind, id.server)."""
    resp = query(check["name"], "TXT", check["server"], recurse=False, rdclass="CH")
    values = {r.to_text().strip('"').lower() for rrset in resp.answer for r in rrset}
    if not values:
        raise CheckError(f"no CH TXT {check['name']} from {check['server']}")
    return {"set": values, "match": check.get("match", "exact"), "rtype": "TXT"}


SOA_TEXT = {"mname": lambda r: norm_name(r.mname.to_text()), "rname": lambda r: rname_to_email(r.rname),
            "serial_date": lambda r: norm_date(str(r.serial)[:8])}
SOA_NUM = {"serial": lambda r: r.serial, "refresh": lambda r: r.refresh, "retry": lambda r: r.retry,
           "expire": lambda r: r.expire, "expire_days": lambda r: r.expire // 86400, "minimum": lambda r: r.minimum}


def rname_to_email(rname):
    """The SOA mailbox as an e-mail address: the first label is the local part."""
    return f"{rname.labels[0].decode()}@{dns.name.Name(rname.labels[1:]).to_text().rstrip('.')}".lower()


def _soa_field(check):
    resp = query(check["name"], "SOA")
    rrs = [r for rrset in resp.answer if rrset.rdtype == dns.rdatatype.SOA for r in rrset]
    if not rrs:
        raise CheckError(f"no SOA for {check['name']}")
    field = check["field"]
    if field in SOA_NUM:
        return {"num": SOA_NUM[field](rrs[0]), "tol": check.get("tolerance", 0)}
    return {"set": {SOA_TEXT[field](rrs[0])}, "rtype": "DATE" if field == "serial_date" else "NAME"}


def _ede_code(check):
    """The Extended DNS Error code a resolver adds to its answer. Some anycast instances leave it out: retry."""
    for _ in range(3):
        resp = query(check["name"], check.get("type", "A"), check.get("server", DEFAULT_SERVER))
        codes = [int(o.code) for o in resp.options if isinstance(o, dns.edns.EDEOption)]
        if codes:
            return {"num": codes[0], "tol": 0}
    raise CheckError(f"no EDE for {check['name']}")


def _txt_tag(check):
    """The value of one tag (`p` in v=DMARC1; p=reject) in the TXT records of a name."""
    tag = check["tag"].lower()
    values = set()
    for txt in rdata_values(query(check["name"], "TXT"), "TXT"):
        for item in re.split(r"\s*;\s*", txt.replace('" "', "")):
            key, _, value = item.partition("=")
            if key.strip() == tag and value.strip():
                values.add(value.strip())
    if not values:
        raise CheckError(f"no {tag}= in the TXT of {check['name']}")
    return {"set": values, "rtype": "TAG"}


def _null_mx(check):
    """Which of the listed domains publish a null MX (MX 0 .): they accept no mail."""
    hits = set()
    for domain in check["domains"]:
        resp = query(domain, "MX")
        if any(r.preference == 0 and r.exchange == dns.name.root for rrset in resp.answer
               if rrset.rdtype == dns.rdatatype.MX for r in rrset):
            hits.update({domain.lower(), domain.lower().split(".")[0]})
    return {"set": hits, "rtype": "NAME"}


def _txt_contains(check):
    """'yes' if a TXT record of the name (asked through `server`) contains the needle, else 'no'."""
    resp = query(check["name"], "TXT", check.get("server", DEFAULT_SERVER))
    found = any(check["needle"].lower() in v for v in rdata_values(resp, "TXT"))
    return {"set": {"yes" if found else "no"}, "rtype": "YESNO"}


KINDS = {
    "rrset": _rrset,
    "mx_primary": _mx_primary,
    "rcode": _rcode,
    "chain_len": _chain_len,
    "auth_ttl": _auth_ttl,
    "txt_has": _txt_has,
    "txt_count": _txt_count,
    "chaos_txt": _chaos_txt,
    "soa_field": _soa_field,
    "ede_code": _ede_code,
    "txt_tag": _txt_tag,
    "null_mx": _null_mx,
    "txt_contains": _txt_contains,
}


def cached_expected(check, cache=None, ttl=600):
    """expected() with an optional (get, put) cache so heavy checks run once per 10 minutes."""
    if cache is None:
        return expected(check)
    key = hashlib.sha1(json.dumps(check, sort_keys=True).encode()).hexdigest()
    hit = cache.get(key)
    if hit is not None:
        return _from_json(hit)
    value = expected(check)
    cache.put(key, _to_json(value), int(time.time()) + ttl)
    return value


def _to_json(value):
    return {k: sorted(v) if isinstance(v, set) else v for k, v in value.items()}


def _from_json(value):
    return {k: set(v) if k == "set" else v for k, v in value.items()}


# ---- grading -----------------------------------------------------------------


def grade(part, value, cache=None):
    """Return True if `value` is a correct answer for `part`."""
    kind = part["type"]
    if kind == "mcq":
        return isinstance(value, int) and value == part["answer"]
    text = str(value).strip()
    if not text or len(text) > 500:
        return False
    if kind == "static":
        return any(re.search(p, text, re.IGNORECASE) for p in part["patterns"])
    exp = cached_expected(part["check"], cache)
    if "num" in exp:
        m = re.fullmatch(r"\s*(\d+)\s*", text)
        return bool(m) and abs(int(m.group(1)) - exp["num"]) <= exp.get("tol", 0)
    return _grade_set(exp, text)


def _grade_set(exp, text):
    rtype = exp.get("rtype", "")
    values = exp["set"]
    if exp.get("all"):
        given = {norm_answer(rtype, v) for v in re.split(r"[,\s;]+", text) if v}
        return given == values
    answer = norm_answer(rtype, text)
    if answer in values:
        return True
    if exp.get("match") == "version":
        # the upstream version is enough: 9.20.26 for "9.20.26-1~deb13u1-debian"
        return any(re.fullmatch(r"\d+\.\d+\.\d+", answer) and v.startswith(answer)
                   and not v[len(answer):len(answer) + 1].isdigit() for v in values)
    if exp.get("match") == "prefix24" and rtype == "A":
        return any(answer.rsplit(".", 1)[0] == v.rsplit(".", 1)[0] for v in values if "." in v)
    return False
