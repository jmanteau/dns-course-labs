"""Records of the Dig Quest game zone, built from the private puzzle spec (secret/zone.json).

The spec holds the content (and so the answers); this module only turns it into Route 53
record sets: {"name": fqdn, "type": ..., "ttl": ..., "values": [Route 53 values]}.

Spec keys, all optional except "zone":
  zone      "quest.example.org"
  ttl       default TTL (300)
  records   [{"name": "start", "type": "TXT", "values": ["text", ...]}]  ("@" is the apex;
            TXT values are plain text, or {"strings": [...]} to choose where a long value is split)
  encoded   [{"name": "b64.enc", "encoding": "base64" | "hex" | "bytes", "text": "..."}]
            bytes: every non-ASCII byte written as a Route 53 octal escape (dig prints them in decimal)
  maze      {"name": "maze", "intro": "...", "start": "r0", "rooms": {"r0": {"text": "...", "doors": {"north": "r1"}}}}
            each room is a TXT; each door <door>.<room>.<maze> is a CNAME to the room it leads to
  files     [{"name": "file", "path": "zone/picture.png", "chunk": 240}]
            base64 in chunk-<i>.<name> TXT records, and a meta TXT at <name> (count, size, sha256)
"""
import base64
import hashlib
import os
import re

TXT_MAX = 255  # one TXT character-string


def fqdn(name, zone):
    return f"{zone}." if name == "@" else f"{name}.{zone}."


def quote(text):
    """One TXT character-string, quoted for Route 53 (quotes and backslashes escaped)."""
    if len(text.encode()) > TXT_MAX:
        raise ValueError(f"TXT string over {TXT_MAX} bytes: {text[:40]}…")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def txt_value(value):
    """A TXT record: plain text is split every 255 bytes; {"strings": [...]} keeps the given split."""
    if isinstance(value, dict):
        return " ".join(quote(s) for s in value["strings"])
    data = value.encode()
    if len(data) <= TXT_MAX:
        return quote(value)
    parts, start = [], 0
    while start < len(data):
        end = min(start + TXT_MAX, len(data))
        while end < len(data) and (data[end] & 0xC0) == 0x80:  # never cut a UTF-8 character
            end -= 1
        parts.append(data[start:end].decode())
        start = end
    return " ".join(quote(p) for p in parts)


def octal_bytes(text):
    """Route 53 TXT escapes: printable ASCII as is, every other byte as \\ooo (octal)."""
    out = []
    for b in text.encode():
        if 0x20 <= b < 0x7F and chr(b) not in '"\\':
            out.append(chr(b))
        else:
            out.append(f"\\{b:03o}")
    return '"' + "".join(out) + '"'


def encoded(item):
    text, kind = item["text"], item["encoding"]
    if kind == "base64":
        return quote(base64.b64encode(text.encode()).decode())
    if kind == "hex":
        return quote(text.encode().hex())
    if kind == "bytes":
        return octal_bytes(text)
    raise ValueError(f"unknown encoding {kind}")


def maze_records(maze, zone):
    base = maze["name"]
    out = [("TXT", base, quote(maze["intro"].format(start=f"{maze['start']}.{base}.{zone}")))]
    for room, spec in maze["rooms"].items():
        doors = " ".join(sorted(spec.get("doors", {})))
        text = spec["text"] + (f" Doors: {doors}. Ask TXT <door>.{room}.{base}.{zone}" if doors else "")
        out.append(("TXT", f"{room}.{base}", txt_value(text)))
        for door, target in spec.get("doors", {}).items():
            out.append(("CNAME", f"{door}.{room}.{base}", fqdn(f"{target}.{base}", zone)))
    return out


def file_records(item, base_dir):
    with open(os.path.join(base_dir, item["path"]), "rb") as fh:
        data = fh.read()
    b64 = base64.b64encode(data).decode()
    size = item.get("chunk", 240)
    chunks = [b64[i:i + size] for i in range(0, len(b64), size)]
    name = item["name"]
    out = [("TXT", f"chunk-{i}.{name}", quote(c)) for i, c in enumerate(chunks)]
    meta = [f"chunks={len(chunks)}", f"bytes={len(data)}", f"sha256={hashlib.sha256(data).hexdigest()}",
            f"encoding=base64", f"names=chunk-0.{name} ... chunk-{len(chunks) - 1}.{name}"]
    out.append(("TXT", name, " ".join(quote(m) for m in meta)))
    return out


def build(spec, base_dir="."):
    """All record sets of the zone, one per (name, type), in a stable order."""
    zone, ttl = spec["zone"].rstrip("."), spec.get("ttl", 300)
    raw = []
    for rec in spec.get("records", []):
        for v in rec["values"]:
            raw.append((rec["type"], rec["name"], txt_value(v) if rec["type"] == "TXT" else v, rec.get("ttl", ttl)))
    raw += [("TXT", e["name"], encoded(e), ttl) for e in spec.get("encoded", [])]
    if "maze" in spec:
        raw += [r + (ttl,) for r in maze_records(spec["maze"], zone)]
    for item in spec.get("files", []):
        raw += [r + (ttl,) for r in file_records(item, base_dir)]

    sets = {}
    for rtype, name, value, rttl in raw:
        key = (fqdn(name, zone), rtype)
        entry = sets.setdefault(key, {"name": key[0], "type": rtype, "ttl": rttl, "values": []})
        entry["values"].append(value)
    for (name, rtype), entry in sets.items():
        if rtype == "CNAME" and (len(entry["values"]) > 1 or any(n == name and t != "CNAME" for n, t in sets)):
            raise ValueError(f"{name}: a CNAME must be alone at its name")
    return sorted(sets.values(), key=lambda s: (s["name"], s["type"]))


def bind_value(rtype, value):
    """A Route 53 value written for a BIND zone file: TXT \\ooo escapes are octal there, decimal (\\DDD) in BIND."""
    if rtype != "TXT":
        return value
    return re.sub(r"\\(\\|[0-7]{3})", lambda m: m.group(0) if m.group(1) == "\\" else f"\\{int(m.group(1), 8):03d}", value)


def zone_file(spec, base_dir=".", ns="ns", extra=()):
    """The game zone as a BIND zone file (local simulation: BIND plays Route 53). `extra`: more record lines."""
    zone = spec["zone"].rstrip(".")
    ttl = spec.get("ttl", 300)
    lines = [f"$ORIGIN {zone}.", f"$TTL {ttl}",
             f"@ IN SOA {ns}.{zone}. hostmaster.{zone}. 1 3600 600 86400 {ttl}", f"@ IN NS {ns}.{zone}.", *extra]
    for rs in build(spec, base_dir):
        lines += [f"{rs['name']} {rs['ttl']} IN {rs['type']} {bind_value(rs['type'], v)}" for v in rs["values"]]
    return "\n".join(lines) + "\n"
