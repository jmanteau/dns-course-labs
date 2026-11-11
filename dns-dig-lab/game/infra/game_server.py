"""BIND configuration of the Dig Quest game server, built from the private spec (secret/server.json).

The spec holds the content (and so the answers); this module only renders a self-contained Docker
build folder: {relative path: text}. Two containers run from one Debian image, with host networking
(so BIND sees the real client addresses, which its rate limiting needs): one on port 53, one on alt_port.

Spec keys:
  server     host name of the server inside the game zone, e.g. "ns" for ns.quest.example.org
  game_zone  the game zone, e.g. "quest.example.org"
  address    public IPv4 address of the server (the A record of `server` in the game zone)
  version, hostname, server_id   answers to CH TXT version.bind, hostname.bind, id.server
  alt_port   a second BIND instance listens on this port (alt_zones are served there only)
  zones      [{"name": "axfr.quest.example.org", "transfer": true, "dnssec": false, "delegated": true,
               "records": [{"name": "www", "type": "A", "values": ["192.0.2.1"]}]}]
             transfer: anyone may AXFR it; dnssec: signed by BIND with NSEC (a chain to walk);
             delegated: the game zone gets NS records for it (false: only those who ask the server see it)
  alt_zones  same format, served by the instance on alt_port
"""
import game_zone

CONF_DIR, WORK_DIR = "/etc/quest", "/var/lib/quest"  # in the container: read-only config, writable zones

DOCKERFILE = """FROM debian:trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends bind9 && rm -rf /var/lib/apt/lists/*
COPY quest/ /etc/quest/
COPY start.sh /usr/local/bin/start
ENTRYPOINT ["/bin/sh", "/usr/local/bin/start"]
"""

# zones are copied to a writable directory: BIND signs walk.* there and keeps its keys next to it
START = """set -eu
instance="$1"
mkdir -p /var/lib/quest/"$instance" /run/named
cp /etc/quest/"$instance"/*.zone /var/lib/quest/"$instance"/
chown -R bind:bind /var/lib/quest /run/named
named-checkconf -z /etc/quest/"$instance"/named.conf
exec named -g -u bind -c /etc/quest/"$instance"/named.conf
"""


def server_fqdn(spec):
    return f"{spec['server']}.{spec['game_zone'].rstrip('.')}"


def zone_file(zone, spec, ttl=300):
    """A zone file: SOA and NS pointing to the game server, then the zone's records."""
    name = zone["name"].rstrip(".")
    ns = server_fqdn(spec) + "."
    lines = [
        f"$ORIGIN {name}.",
        f"$TTL {ttl}",
        f"@ IN SOA {ns} hostmaster.{spec['game_zone'].rstrip('.')}. 1 3600 600 86400 {ttl}",
        f"@ IN NS {ns}",
    ]
    for rec in zone.get("records", []):
        for value in rec["values"]:
            value = game_zone.txt_value(value) if rec["type"] == "TXT" else value
            lines.append(f"{rec['name']} {rec.get('ttl', ttl)} IN {rec['type']} {value}")
    return "\n".join(lines) + "\n"


def zone_file_name(zone):
    return zone["name"].rstrip(".") + ".zone"


def named_conf(spec, zones, directory, port, pid):
    """named.conf of one instance: authoritative only, no recursion, rate limited."""
    opts = [
        f'directory "{directory}";',
        f'pid-file "{pid}";',
        f'session-keyfile "{directory}/session.key";',
        f"listen-on port {port} {{ any; }};",
        "listen-on-v6 { none; };",
        "recursion no;",  # never an open resolver
        "allow-query { any; };",
        "allow-transfer { none; };",
        "minimal-any yes;",
        # blunts reflection attacks; a class behind one NAT shares a bucket, and over-limit queries get a
        # truncated answer every other time (slip), so dig retries over TCP and still gets through
        "rate-limit { responses-per-second 20; window 5; };",
        f'version "{spec["version"]}";',
        f'hostname "{spec["hostname"]}";',
        f'server-id "{spec["server_id"]}";',
    ]
    # no rndc channel: two instances share the host network and would both claim 127.0.0.1:953
    out = ["options {"] + [f"    {o}" for o in opts] + ["};", "", "controls { };", ""]
    for zone in zones:
        body = [f"type primary;", f'file "{zone_file_name(zone)}";']
        if zone.get("transfer"):
            body.append("allow-transfer { any; };")
        if zone.get("dnssec"):
            # the default policy signs with NSEC: every name points to the next one
            body += ["dnssec-policy default;", "inline-signing yes;"]
        out += [f'zone "{zone["name"].rstrip(".")}" {{'] + [f"    {b}" for b in body] + ["};", ""]
    return "\n".join(out)


def compose(spec):
    services = [("main", 53)] + ([("alt", spec["alt_port"])] if spec.get("alt_zones") else [])
    out = ["services:"]
    for name, port in services:
        out += [f"  {name}:", "    build: .", "    image: dig-quest-bind", f'    command: ["{name}"]',
                "    network_mode: host", "    restart: unless-stopped", f"    # DNS on port {port}, UDP and TCP"]
    return "\n".join(out) + "\n"


def files(spec):
    """The Docker build folder: Dockerfile, compose.yaml, start script, both configurations and their zones."""
    out = {"Dockerfile": DOCKERFILE, "start.sh": START, "compose.yaml": compose(spec)}
    instances = [("main", spec["zones"], 53)]
    if spec.get("alt_zones"):
        instances.append(("alt", spec["alt_zones"], spec["alt_port"]))
    for name, zones, port in instances:
        out[f"quest/{name}/named.conf"] = named_conf(spec, zones, f"{WORK_DIR}/{name}", port, f"/run/named/{name}.pid")
        for zone in zones:
            out[f"quest/{name}/{zone_file_name(zone)}"] = zone_file(zone, spec)
    return out


def delegations(spec):
    """Sub-zones the game zone must delegate to the server (relative names)."""
    suffix = "." + spec["game_zone"].rstrip(".")
    return [z["name"].rstrip(".")[: -len(suffix)] for z in spec["zones"]
            if z.get("delegated", True) and z["name"].rstrip(".").endswith(suffix)]


if __name__ == "__main__":
    # python infra/game_server.py secret/server.json build/server: write the Docker build folder
    import json
    import os
    import shutil
    import sys

    spec_path, out_dir = sys.argv[1], sys.argv[2]
    with open(spec_path, encoding="utf-8") as fh:
        rendered = files(json.load(fh))
    shutil.rmtree(out_dir, ignore_errors=True)
    for rel, text in rendered.items():
        path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"{len(rendered)} files in {out_dir}")
