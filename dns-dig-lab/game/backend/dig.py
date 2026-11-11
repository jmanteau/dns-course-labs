"""The dig console: run a lookup for a player and print it the way dig does.

Only public resolvers or public addresses can be queried (a server hostname must resolve to a
public IP), so the API cannot be used to probe private networks. ANY is not offered; AXFR and a
port other than 53 are allowed only toward the Dig Quest game server (GAME_SERVER).
"""
import ipaddress
import os
import re
import time
from email.utils import formatdate

import dns.edns
import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.reversename
import dns.xfr

# QUEST_RESOLVER replaces 8.8.8.8 (local simulation: a resolver that also knows the local game zone)
RESOLVER = os.environ.get("QUEST_RESOLVER", "8.8.8.8")
RESOLVERS = {"google": RESOLVER, "cloudflare": "1.1.1.1", "quad9": "9.9.9.9", "opendns": "208.67.222.222"}
# DIG_ALLOW_NET: a private network the console may also query (local simulation only, never set in AWS)
ALLOW_NET = ipaddress.ip_network(os.environ["DIG_ALLOW_NET"]) if os.environ.get("DIG_ALLOW_NET") else None
TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "PTR", "CAA", "SRV", "DS", "DNSKEY", "RRSIG",
         "NSEC", "NSEC3PARAM", "HTTPS", "SVCB", "NAPTR", "TLSA", "SSHFP", "CDS", "CDNSKEY", "LOC", "HINFO")
CLASSES = ("IN", "CH")  # CH: servers describing themselves (version.bind, hostname.bind, id.server)
OPTIONS = ("short", "trace", "norecurse", "dnssec", "tcp", "nsid", "cd")
# Extended DNS Errors (RFC 8914), named as dig prints them
EDE_NAMES = {0: "Other", 1: "Unsupported DNSKEY Algorithm", 2: "Unsupported DS Digest Type", 3: "Stale Answer",
             4: "Forged Answer", 5: "DNSSEC Indeterminate", 6: "DNSSEC Bogus", 7: "Signature Expired",
             8: "Signature Not Yet Valid", 9: "DNSKEY Missing", 10: "RRSIGs Missing", 11: "No Zone Key Bit Set",
             12: "NSEC Missing", 13: "Cached Error", 14: "Not Ready", 15: "Blocked", 16: "Censored", 17: "Filtered",
             18: "Prohibited", 19: "Stale NXDOMAIN Answer", 20: "Not Authoritative", 21: "Not Supported",
             22: "No Reachable Authority", 23: "Network Error", 24: "Invalid Data"}
MAX_NAMES, MAX_HOPS, TIMEOUT, DEADLINE = 5, 10, 3, 20
MAX_XFR = 500  # records printed from a zone transfer
GAME_SERVER = os.environ.get("GAME_SERVER")  # the only server AXFR and -p may target
NAME_RE = re.compile(r"^[A-Za-z0-9_*-]+(\.[A-Za-z0-9_-]+)*\.?$|^\.$")
FLAG_ORDER = [("qr", dns.flags.QR), ("aa", dns.flags.AA), ("tc", dns.flags.TC), ("rd", dns.flags.RD),
              ("ra", dns.flags.RA), ("ad", dns.flags.AD), ("cd", dns.flags.CD)]


class DigError(ValueError):
    """The request itself is invalid (shown to the player as is)."""


class Failed(Exception):
    """A lookup did not get an answer: printed in the output, like dig does."""


# ---- input -------------------------------------------------------------------


def parse_names(text):
    names = [n for n in re.split(r"[\s,]+", str(text or "").strip()) if n]
    if not names:
        raise DigError("enter a hostname or an IP address")
    if len(names) > MAX_NAMES:
        raise DigError(f"at most {MAX_NAMES} names at a time")
    for n in names:
        if len(n) > 253 or not (is_ip(n) or NAME_RE.match(n)):
            raise DigError(f"not a valid hostname: {n[:60]}")
    return names


def parse_server(server):
    """Return (ip, label) for a resolver name, a public IP or a server hostname, or (None, 'authoritative')."""
    server = str(server or "google").strip().lower()
    if server in RESOLVERS:
        return RESOLVERS[server], RESOLVERS[server]
    if server == "authoritative":
        return None, "authoritative"
    label = server
    if not is_ip(server):
        if "." not in server.strip(".") or len(server) > 253 or not NAME_RE.match(server):
            raise DigError("server: pick a resolver, or enter a public IP address or a server name")
        try:
            server = resolve_a(server.rstrip("."))
        except Failed:
            raise DigError(f"server: cannot find the address of {label[:60]}")
        label = label.rstrip(".")
    ip = ipaddress.ip_address(server)
    if not ip.is_global and not (ALLOW_NET and ip in ALLOW_NET):
        raise DigError(f"{label} is not a public address" if label == str(ip) else f"{label} ({ip}) is not a public address")
    return str(ip), label


def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False


# ---- one query ---------------------------------------------------------------


def send(name, rtype, server, recurse=True, dnssec=False, tcp=False, subnet=None, rdclass="IN", nsid=False, cd=False,
         port=53):
    """Send one query. Returns (response, transport, milliseconds)."""
    options = []
    if subnet:
        net, _, bits = subnet.partition("/")
        options.append(dns.edns.ECSOption(net, int(bits or 24)))
    if nsid:
        options.append(dns.edns.GenericOption(dns.edns.OptionType.NSID, b""))
    msg = dns.message.make_query(name, rtype, rdclass=dns.rdataclass.from_text(rdclass), use_edns=0, payload=1232,
                                 want_dnssec=dnssec, options=options)
    if not recurse:
        msg.flags &= ~dns.flags.RD
    if cd:
        msg.flags |= dns.flags.CD
    start = time.perf_counter()
    try:
        if tcp:
            resp, transport = dns.query.tcp(msg, server, timeout=TIMEOUT, port=port), "TCP"
        else:
            resp, transport = dns.query.udp(msg, server, timeout=TIMEOUT, port=port), "UDP"
            if resp.flags & dns.flags.TC:
                resp, transport = dns.query.tcp(msg, server, timeout=TIMEOUT, port=port), "TCP"
    except dns.exception.Timeout:
        raise Failed(f";; communications error to {server}#{port}: timed out")
    except (OSError, dns.exception.DNSException) as exc:
        raise Failed(f";; communications error to {server}#{port}: {exc}")
    return resp, transport, round((time.perf_counter() - start) * 1000)


def resolve_a(name, resolver=None):
    resp, _, _ = send(name, "A", resolver or RESOLVER)
    for rrset in resp.answer:
        if rrset.rdtype == dns.rdatatype.A:
            return sorted(r.address for r in rrset)[0]
    raise Failed(f";; no address for {name}")


# ---- formatting --------------------------------------------------------------


def record_lines(rrsets):
    lines = []
    for rrset in rrsets:
        name = rrset.name.to_text()
        rtype = dns.rdatatype.to_text(rrset.rdtype)
        rdclass = dns.rdataclass.to_text(rrset.rdclass)
        for r in rrset:
            lines.append(f"{name:<31} {rrset.ttl:<7} {rdclass} {rtype:<6} {r.to_text()}")
    return lines


def count(rrsets):
    return sum(len(r) for r in rrsets)


def option_lines(resp):
    """The EDNS options of an answer, printed like dig: client subnet, NSID, extended errors."""
    out = []
    for opt in resp.options:
        if isinstance(opt, dns.edns.ECSOption):
            out.append(f"; CLIENT-SUBNET: {opt.address}/{opt.srclen}/{opt.scopelen}")
        elif opt.otype == dns.edns.OptionType.NSID:
            data = opt.to_wire()
            text = data.decode("ascii", "replace") if data.isascii() else ""
            out.append(f"; NSID: {' '.join(f'{b:02x}' for b in data)}" + (f' ("{text}")' if text.isprintable() and text else ""))
        elif isinstance(opt, dns.edns.EDEOption):
            code = int(opt.code)
            out.append(f"; EDE: {code} ({EDE_NAMES.get(code, 'Unknown')})" + (f": ({opt.text})" if opt.text else ""))
    return out


def full_text(resp, server, transport, ms, label=None, port=53):
    """The response printed like dig's default output (from ';; Got answer:' to the footer)."""
    flags = " ".join(f for f, bit in FLAG_ORDER if resp.flags & bit)
    extra = count(resp.additional) + (1 if resp.edns >= 0 else 0)
    out = [
        ";; Got answer:",
        f";; ->>HEADER<<- opcode: QUERY, status: {dns.rcode.to_text(resp.rcode())}, id: {resp.id}",
        f";; flags: {flags}; QUERY: {len(resp.question)}, ANSWER: {count(resp.answer)}, "
        f"AUTHORITY: {count(resp.authority)}, ADDITIONAL: {extra}",
    ]
    if resp.edns >= 0:
        edns_flags = "do" if resp.ednsflags & dns.flags.DO else ""
        out += ["", ";; OPT PSEUDOSECTION:", f"; EDNS: version: {resp.edns}, flags:{edns_flags}; udp: {resp.payload}"]
        out += option_lines(resp)
    out += ["", ";; QUESTION SECTION:"]
    for q in resp.question:
        out.append(f";{q.name.to_text():<30} {dns.rdataclass.to_text(q.rdclass)} {dns.rdatatype.to_text(q.rdtype)}")
    for title, section in (("ANSWER", resp.answer), ("AUTHORITY", resp.authority), ("ADDITIONAL", resp.additional)):
        if section:
            out += ["", f";; {title} SECTION:"] + record_lines(section)
    out += [
        "",
        f";; Query time: {ms} msec",
        f";; SERVER: {server}#{port}({label or server}) ({transport})",
        f";; WHEN: {formatdate(usegmt=True)}",
        f";; MSG SIZE  rcvd: {len(resp.to_wire())}",
    ]
    return out


def short_text(resp):
    return [r.to_text() for rrset in resp.answer for r in rrset]


# ---- lookups -----------------------------------------------------------------


def lookup(name, rtype, server, opts, label=None):
    """One name, one server: dig's default or +short output."""
    port = opts.get("port", 53)
    if rtype == "AXFR":
        return transfer(name, server, port, label, opts.get("short"))
    resp, transport, ms = send(name, rtype, server, recurse=not opts.get("norecurse"), dnssec=opts.get("dnssec"),
                               tcp=opts.get("tcp"), subnet=opts.get("subnet"), rdclass=opts.get("class", "IN"),
                               nsid=opts.get("nsid"), cd=opts.get("cd"), port=port)
    return short_text(resp) if opts.get("short") else full_text(resp, server, transport, ms, label, port)


def transfer(zone, server, port, label, short=False):
    """A zone transfer (AXFR, over TCP), printed like dig: every record, then the XFR size."""
    out, records, messages, size = [], 0, 0, 0
    start = time.perf_counter()
    try:
        for msg in dns.query.xfr(server, zone, port=port, lifetime=10, relativize=False):
            messages, size = messages + 1, size + len(msg.to_wire())
            lines = short_text(msg) if short else record_lines(msg.answer)
            out += lines[:MAX_XFR - records]
            records += len(lines)
            if records > MAX_XFR:
                out.append(f";; stopped: only the first {MAX_XFR} records are shown")
                break
    except (dns.exception.DNSException, OSError):
        return out + ["; Transfer failed."]
    if short:
        return out
    ms = round((time.perf_counter() - start) * 1000)
    return out + ["", f";; Query time: {ms} msec", f";; SERVER: {server}#{port}({label or server}) (TCP)",
                  f";; WHEN: {formatdate(usegmt=True)}", f";; XFR size: {records} records (messages {messages}, bytes {size})"]


def game_server_only(server, label, names, opts):
    """AXFR and -p can reach only the game server: never a tool to transfer or scan other hosts."""
    if not GAME_SERVER:
        raise DigError("AXFR and -p are not available here: use dig in your terminal")
    if label == "authoritative" or opts.get("trace") or len(names) > 1 or server != resolve_a(GAME_SERVER):
        raise DigError(f"AXFR and -p work only toward the game server: Other server… {GAME_SERVER}, one name")


def find_authoritative(name):
    """(ip, ns name) of the first name server of the zone that holds `name`, found via the default resolver."""
    resp, _, _ = send(name, "SOA", RESOLVER)
    zone = None
    for rrset in resp.answer + resp.authority:
        if rrset.rdtype == dns.rdatatype.SOA:
            zone = rrset.name
    if zone is None:
        raise Failed(f";; no zone found for {name}")
    resp, _, _ = send(zone, "NS", RESOLVER)
    ns = sorted(r.target.to_text() for rrset in resp.answer if rrset.rdtype == dns.rdatatype.NS for r in rrset)
    if not ns:
        raise Failed(f";; no NS for {zone}")
    return resolve_a(ns[0]), ns[0]


def trace(name, rtype, resolver, opts, deadline):
    """Walk from the root like dig +trace: print each referral, then the final answer."""
    out = []
    resp, _, ms = send(".", "NS", resolver, dnssec=opts.get("dnssec"))
    out += record_lines(resp.answer) + [f";; Received {len(resp.to_wire())} bytes from {resolver}#53({resolver}) in {ms} ms", ""]
    roots = sorted(r.target.to_text() for rrset in resp.answer for r in rrset)
    if not roots:
        raise Failed(";; no root servers")
    ns_name = roots[0]
    ip = resolve_a(ns_name, resolver)
    for _ in range(MAX_HOPS):
        if time.monotonic() > deadline:
            out.append(";; stopped: time limit")
            break
        resp, _, ms = send(name, rtype, ip, recurse=False, dnssec=opts.get("dnssec"))
        out += record_lines(resp.answer or resp.authority)
        out += [f";; Received {len(resp.to_wire())} bytes from {ip}#53({ns_name}) in {ms} ms", ""]
        referral = [r for r in resp.authority if r.rdtype == dns.rdatatype.NS]
        if resp.answer or resp.rcode() != dns.rcode.NOERROR or not referral:
            break
        names = sorted(r.target.to_text() for rrset in referral for r in rrset)
        glue = {rrset.name.to_text(): rrset[0].address for rrset in resp.additional if rrset.rdtype == dns.rdatatype.A}
        ns_name = next((n for n in names if n in glue), names[0])
        ip = glue.get(ns_name) or resolve_a(ns_name, resolver)
    return out


def command(names, rtype, label, ns_name, opts):
    """The dig command line a student would type for this request."""
    flags = [f"+{k}" for k in OPTIONS if opts.get(k)]
    port = ["-p", str(opts["port"])] if opts.get("port", 53) != 53 else []
    if opts.get("subnet"):
        flags.append(f"+subnet={opts['subnet']}")
    at = []
    if label == "authoritative":
        at = [f"@{ns_name.rstrip('.') if ns_name else '<NS of the zone>'}"]
    elif not opts.get("trace"):
        at = [f"@{label}"]
    cls = [opts["class"]] if opts.get("class", "IN") != "IN" else []
    queries = [["-x", n] if is_ip(n) else [n] + cls + [rtype] for n in names]
    if len(names) == 1:
        return " ".join(["dig"] + at + port + queries[0] + flags)
    return " ".join(["dig"] + at + port + flags + [w for q in queries for w in q])


def run(body):
    """Handle one console request. Returns {'command': str, 'output': str}."""
    names = parse_names(body.get("names"))
    rtype = str(body.get("type") or "A").upper()
    if rtype not in TYPES and rtype != "AXFR":
        raise DigError(f"type {rtype[:12]} is not available here")
    rdclass = str(body.get("class") or "IN").upper()
    if rdclass not in CLASSES:
        raise DigError(f"class {rdclass[:8]} is not available here")
    if rdclass == "CH" and (rtype != "TXT" or body.get("trace") or body.get("server") == "authoritative"):
        raise DigError("class CH: ask a TXT record (version.bind, hostname.bind, id.server) of one server")
    server, label = parse_server(body.get("server"))
    opts = {k: bool(body.get(k)) for k in OPTIONS}
    opts["class"] = rdclass
    try:
        opts["port"] = int(body.get("port") or 53)
    except (TypeError, ValueError):
        raise DigError("port: a number")
    if not 1 <= opts["port"] <= 65535:
        raise DigError("port: 1 to 65535")
    if rtype == "AXFR" or opts["port"] != 53:
        if rdclass != "IN":
            raise DigError("AXFR and -p: class IN only")
        game_server_only(server, label, names, opts)
    subnet = str(body.get("subnet") or "").strip()
    if subnet:
        try:
            ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            raise DigError("subnet: use a prefix like 129.20.0.0/24")
        opts["subnet"] = subnet
    if opts["trace"] and len(names) > 1:
        raise DigError("+trace takes one name at a time")
    if label == "authoritative":
        opts["norecurse"] = True

    deadline = time.monotonic() + DEADLINE
    out, ns_name = [], None
    for name in names:
        qname, qtype = (dns.reversename.from_address(name).to_text(), "PTR") if is_ip(name) else (name, rtype)
        if not opts["short"]:
            out += [f"; <<>> DiG (Dig Quest) <<>> {'-x ' + name if is_ip(name) else name + ' ' + qtype}"]
        try:
            if time.monotonic() > deadline:
                raise Failed(";; stopped: time limit")
            if opts["trace"]:
                out += trace(qname, qtype, server or RESOLVER, opts, deadline)
                continue
            target = server
            if label == "authoritative":
                target, ns_name = find_authoritative(qname)
                if not opts["short"]:
                    out.append(f";; asking {ns_name} ({target}), an authoritative server of the zone")
            out += lookup(qname, qtype, target, opts, label if label != "authoritative" else ns_name)
        except Failed as exc:
            out.append(str(exc))
        if not opts["short"]:
            out.append("")
    return {"command": command(names, rtype, label, ns_name, opts), "output": "\n".join(out).rstrip() + "\n"}
