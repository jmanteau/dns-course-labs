"""Local simulation of the whole DNS side of Dig Quest, in containers, before anything is deployed.

From the same private specs as the real deployment (secret/zone.json, secret/server.json) it renders a
compose project on one bridge network:
  resolver  10.53.0.2   recursive BIND: the Internet through 8.8.8.8, the game zone through `zone`
  zone      10.53.0.10  the game zone, served by BIND instead of Route 53
  main/alt  10.53.0.53  the game server, ports 53 and 8053 (alt shares main's network, like on the host)
  runner    10.53.0.100 the game code: pytest, or dev_server.py on http://localhost:8787
Tests run inside `runner`: on macOS the host cannot reach the bridge addresses.
"""
import game_server
import game_zone

SUBNET = "10.53.0.0/24"
RESOLVER, ZONE, SERVER, RUNNER = "10.53.0.2", "10.53.0.10", "10.53.0.53", "10.53.0.100"

RUNNER_DOCKERFILE = """FROM python:3.13-slim
RUN pip install --no-cache-dir dnspython "moto[server]" pytest boto3
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /repo/dns-dig-lab/game
"""


def zone_conf(name):
    """The game zone's server: authoritative only, like Route 53 (no rate limit)."""
    return f"""options {{
    directory "/var/lib/quest/zone";
    pid-file "/run/named/zone.pid";
    listen-on {{ any; }};
    listen-on-v6 {{ none; }};
    recursion no;
    allow-query {{ any; }};
    allow-transfer {{ none; }};
}};

controls {{ }};

zone "{name}" {{
    type primary;
    file "{name}.zone";
}};
"""


def resolver_conf(name):
    """A recursive resolver that sees the Internet through 8.8.8.8 and the game zone through `zone`."""
    return f"""options {{
    directory "/var/lib/quest/resolver";
    pid-file "/run/named/resolver.pid";
    listen-on {{ any; }};
    listen-on-v6 {{ none; }};
    recursion yes;
    allow-query {{ {SUBNET}; }};
    allow-recursion {{ {SUBNET}; }};
    forwarders {{ 8.8.8.8; 1.1.1.1; }};
    forward only;
    dnssec-validation auto;
    // the real parent has no DS (nor delegation) for the local game zone
    validate-except {{ "{name}"; }};
}};

controls {{ }};

// iterative from the local zone server: it follows the delegations to the game server itself
zone "{name}" {{
    type static-stub;
    server-addresses {{ {ZONE}; }};
    forwarders {{ }};  // not through 8.8.8.8, which knows nothing of the local zone
}};
"""


def compose(alt, game_server_name):
    bind = lambda svc, ip: [f"  {svc}:", "    build: .", "    image: dig-quest-bind", f'    command: ["{svc}"]',
                            "    networks:", f"      sim: {{ipv4_address: {ip}}}"]
    out = ["name: dig-quest-sim", "services:"]
    out += bind("resolver", RESOLVER) + ["    depends_on: [zone, main]"]
    out += bind("zone", ZONE)
    out += bind("main", SERVER)
    if alt:
        out += ["  alt:", "    image: dig-quest-bind", '    command: ["alt"]', "    network_mode: service:main",
                "    depends_on: [main]"]
    out += [
        "  runner:",
        "    build: {context: ., dockerfile: Dockerfile.runner}",
        "    image: dig-quest-runner",
        "    profiles: [runner]",
        "    networks:",
        f"      sim: {{ipv4_address: {RUNNER}}}",
        "    dns: [" + RESOLVER + "]",
        "    environment:",
        f"      QUEST_RESOLVER: {RESOLVER}",
        f"      DIG_ALLOW_NET: {SUBNET}",
        "      HOST: 0.0.0.0",
        f"      GAME_SERVER: {game_server_name}",
        "    ports: [\"127.0.0.1:8787:8787\"]",
        "    volumes:",
        "      - ../..:/repo/dns-dig-lab/game:ro",
        "      - ../../../../course/_site:/repo/course/_site:ro",
        "    depends_on: [resolver" + (", alt" if alt else "") + "]",
        "networks:",
        "  sim:",
        "    ipam:",
        f"      config: [{{subnet: {SUBNET}}}]",
    ]
    return "\n".join(out) + "\n"


def files(zone_spec, server_spec, base_dir):
    """The compose folder: the game server's files, the zone and resolver configurations, the runner image."""
    out = {k: v for k, v in game_server.files(server_spec).items() if k != "compose.yaml"}
    name = zone_spec["zone"].rstrip(".")
    ns = server_spec["server"]
    extra = [f"{ns} 300 IN A {SERVER}"] + [f"{sub} 300 IN NS {ns}.{name}." for sub in game_server.delegations(server_spec)]
    # the zone's own NS is a stand-in for Route 53's servers: `zone` answers for it
    out["quest/zone/named.conf"] = zone_conf(name)
    out[f"quest/zone/{name}.zone"] = game_zone.zone_file(zone_spec, base_dir, ns="r53", extra=[f"r53 300 IN A {ZONE}"] + extra)
    # start.sh copies *.zone: the resolver has none, but an empty folder would make cp fail
    out["quest/resolver/named.conf"] = resolver_conf(name)
    out["quest/resolver/empty.zone"] = ""
    out["Dockerfile.runner"] = RUNNER_DOCKERFILE
    out["compose.yaml"] = compose(bool(server_spec.get("alt_zones")), game_server.server_fqdn(server_spec))
    return out


if __name__ == "__main__":
    # python infra/sim.py secret build/sim: write the compose folder
    import json
    import os
    import shutil
    import sys

    secret, out_dir = sys.argv[1], sys.argv[2]
    specs = []
    for f in ("zone.json", "server.json"):
        with open(os.path.join(secret, f), encoding="utf-8") as fh:
            specs.append(json.load(fh))
    rendered = files(*specs, secret)
    shutil.rmtree(out_dir, ignore_errors=True)
    for rel, text in rendered.items():
        path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"{len(rendered)} files in {out_dir}")
