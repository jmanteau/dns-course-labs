import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "infra"))
import game_server  # noqa: E402

SPEC = {
    "server": "ns", "game_zone": "quest.example.org", "address": "94.23.1.53",
    "version": "v", "hostname": "h", "server_id": "id1", "alt_port": 8053,
    "zones": [
        {"name": "axfr.quest.example.org", "transfer": True, "records": [{"name": "www", "type": "A", "values": ["192.0.2.1"]}]},
        {"name": "walk.quest.example.org", "dnssec": True, "records": [{"name": "@", "type": "TXT", "values": ['say "hi"']}]},
        {"name": "secret.lab", "delegated": False, "records": []},
    ],
    "alt_zones": [{"name": "door.quest.example.org", "delegated": False, "records": []}],
}


def test_docker_folder():
    files = game_server.files(SPEC)
    assert set(files) == {"Dockerfile", "start.sh", "compose.yaml", "quest/main/named.conf", "quest/alt/named.conf",
                          "quest/main/axfr.quest.example.org.zone", "quest/main/walk.quest.example.org.zone",
                          "quest/main/secret.lab.zone", "quest/alt/door.quest.example.org.zone"}
    assert "FROM debian:trixie-slim" in files["Dockerfile"]
    compose = files["compose.yaml"]
    assert compose.count("network_mode: host") == 2 and '"main"' in compose and '"alt"' in compose


def test_named_conf_is_authoritative_only():
    main, alt = game_server.files(SPEC)["quest/main/named.conf"], game_server.files(SPEC)["quest/alt/named.conf"]
    for conf in (main, alt):
        assert "recursion no;" in conf and "controls { };" in conf and "rate-limit" in conf
        assert 'version "v";' in conf and 'server-id "id1";' in conf
    assert "listen-on port 53 " in main and "listen-on port 8053 " in alt
    axfr = main.split('zone "axfr.quest.example.org"')[1].split("\n};")[0]
    walk = main.split('zone "walk.quest.example.org"')[1].split("\n};")[0]
    assert "allow-transfer { any; };" in axfr and "dnssec-policy" not in axfr
    assert "dnssec-policy default;" in walk and "allow-transfer" not in walk


def test_zone_file():
    text = game_server.files(SPEC)["quest/main/walk.quest.example.org.zone"]
    assert "$ORIGIN walk.quest.example.org." in text
    assert "@ IN NS ns.quest.example.org." in text
    assert '@ 300 IN TXT "say \\"hi\\""' in text


def test_only_public_sub_zones_are_delegated():
    assert game_server.delegations(SPEC) == ["axfr", "walk"]
    assert game_server.server_fqdn(SPEC) == "ns.quest.example.org"


def test_no_alt_instance_without_alt_zones():
    files = game_server.files(dict(SPEC, alt_zones=[]))
    assert not any(p.startswith("quest/alt/") for p in files) and '"alt"' not in files["compose.yaml"]
