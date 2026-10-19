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
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver

DEFAULT_SERVER = "8.8.8.8"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class CheckError(Exception):
    """The live lookup needed to grade an answer failed (not the student's fault)."""


def query(name, rtype, server=DEFAULT_SERVER, ecs=None, recurse=True):
    """Send one DNS query and return the response message."""
    options = []
    if ecs:
        net, _, bits = ecs.partition("/")
        options.append(dns.edns.ECSOption(net, int(bits or 24)))
    msg = dns.message.make_query(name, rtype, use_edns=0, options=options)
    if not recurse:
        msg.flags &= ~dns.flags.RD
    try:
        resp = dns.query.udp(msg, server, timeout=3)
        if resp.flags & dns.flags.TC:
            resp = dns.query.tcp(msg, server, timeout=4)
    except Exception as exc:
        raise CheckError(f"lookup of {name} {rtype} via {server} failed: {exc}") from exc
    return resp


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
    return norm_name(text)


# ---- expected values ---------------------------------------------------------


def expected(check):
    """Compute what a correct answer is right now. Returns {'set': {...}} or {'num': n, 'tol': t}."""
    kind = check["kind"]
    return KINDS[kind](check)


def _rrset(check):
    resp = query(check["name"], check["type"], check.get("server", DEFAULT_SERVER), check.get("ecs"))
    values = rdata_values(resp, check["type"])
    if not values:
        raise CheckError(f"no {check['type']} answer for {check['name']}")
    return {"set": values, "match": check.get("match", "exact"), "all": check.get("all", False), "rtype": check["type"]}


def _mx_primary(check):
    resp = query(check["name"], "MX")
    rrs = [r for rrset in resp.answer if rrset.rdtype == dns.rdatatype.MX for r in rrset]
    if not rrs:
        raise CheckError("no MX")
    best = min(r.preference for r in rrs)
    return {"set": {norm_name(r.exchange.to_text()) for r in rrs if r.preference == best}, "rtype": "MX"}


def _rcode(check):
    resp = query(check["name"], check.get("type", "A"))
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


KINDS = {
    "rrset": _rrset,
    "mx_primary": _mx_primary,
    "rcode": _rcode,
    "chain_len": _chain_len,
    "auth_ttl": _auth_ttl,
    "txt_has": _txt_has,
    "txt_count": _txt_count,
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
    if exp.get("match") == "prefix24" and rtype == "A":
        return any(answer.rsplit(".", 1)[0] == v.rsplit(".", 1)[0] for v in values if "." in v)
    return False
