import base64
import hashlib
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "infra"))
import game_zone  # noqa: E402

ZONE = "quest.example.org"


def strings(value):
    """The character-strings of a Route 53 TXT value, unescaped."""
    return [re.sub(r'\\(["\\])', r"\1", s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', value)]


def find(sets, name, rtype):
    return next(s for s in sets if s["name"] == f"{name}.{ZONE}." and s["type"] == rtype)


def test_records_are_grouped_by_name_and_type():
    sets = game_zone.build({"zone": ZONE, "records": [
        {"name": "vault", "type": "MX", "values": ["10 gate.quest.example.org.", "20 decoy.quest.example.org."]},
        {"name": "@", "type": "TXT", "values": ['say "hi"']},
    ]})
    assert find(sets, "vault", "MX")["values"] == ["10 gate.quest.example.org.", "20 decoy.quest.example.org."]
    apex = next(s for s in sets if s["name"] == f"{ZONE}.")
    assert apex["values"] == ['"say \\"hi\\""'] and apex["ttl"] == 300


def test_long_txt_is_split_into_255_byte_strings():
    text = "é" * 200  # 400 bytes: the split must not cut a character in two
    (rec,) = game_zone.build({"zone": ZONE, "records": [{"name": "long", "type": "TXT", "values": [text]}]})
    parts = strings(rec["values"][0])
    assert len(parts) == 2 and all(len(p.encode()) <= 255 for p in parts) and "".join(parts) == text


def test_long_txt_with_a_chosen_split():
    (rec,) = game_zone.build({"zone": ZONE, "records": [{"name": "long", "type": "TXT", "values": [{"strings": ["the word is NAME", "SERVER."]}]}]})
    assert rec["values"] == ['"the word is NAME" "SERVER."']
    with pytest.raises(ValueError):
        game_zone.build({"zone": ZONE, "records": [{"name": "x", "type": "TXT", "values": [{"strings": ["a" * 256]}]}]})


def test_encodings():
    sets = game_zone.build({"zone": ZONE, "encoded": [
        {"name": "b64.enc", "encoding": "base64", "text": "anycast"},
        {"name": "hex.enc", "encoding": "hex", "text": "dig"},
        {"name": "bytes.enc", "encoding": "bytes", "text": "🦊 a\"b"},
    ]})
    assert base64.b64decode(strings(find(sets, "b64.enc", "TXT")["values"][0])[0]) == b"anycast"
    assert find(sets, "hex.enc", "TXT")["values"] == ['"646967"']
    # Route 53 reads \ooo as octal: F0 9F A6 8A is the fox emoji
    assert find(sets, "bytes.enc", "TXT")["values"] == ['"\\360\\237\\246\\212 a\\042b"']


def test_maze_rooms_and_doors():
    sets = game_zone.build({"zone": ZONE, "maze": {"name": "maze", "intro": "Enter at {start}.", "start": "r0", "rooms": {
        "r0": {"text": "Room 0.", "doors": {"north": "r1", "east": "r0"}},
        "r1": {"text": "Treasure."},
    }}})
    assert strings(find(sets, "maze", "TXT")["values"][0]) == [f"Enter at r0.maze.{ZONE}."]
    assert strings(find(sets, "r0.maze", "TXT")["values"][0])[0] == f"Room 0. Doors: east north. Ask TXT <door>.r0.maze.{ZONE}"
    assert strings(find(sets, "r1.maze", "TXT")["values"][0]) == ["Treasure."]
    assert find(sets, "north.r0.maze", "CNAME")["values"] == [f"r1.maze.{ZONE}."]
    assert find(sets, "east.r0.maze", "CNAME")["values"] == [f"r0.maze.{ZONE}."]


def test_cname_must_be_alone():
    with pytest.raises(ValueError, match="alone"):
        game_zone.build({"zone": ZONE, "records": [
            {"name": "x", "type": "CNAME", "values": ["a.example."]}, {"name": "x", "type": "TXT", "values": ["t"]}]})


def test_file_chunks_rebuild_the_file(tmp_path):
    data = bytes(range(256)) * 3
    (tmp_path / "f.bin").write_bytes(data)
    sets = game_zone.build({"zone": ZONE, "files": [{"name": "file", "path": "f.bin", "chunk": 200}]}, str(tmp_path))
    meta = strings(find(sets, "file", "TXT")["values"][0])
    count = int(meta[0].split("=")[1])
    b64 = "".join(strings(find(sets, f"chunk-{i}.file", "TXT")["values"][0])[0] for i in range(count))
    assert base64.b64decode(b64) == data
    assert f"sha256={hashlib.sha256(data).hexdigest()}" in meta and count == 6


def test_bind_zone_file_keeps_the_bytes():
    """Route 53 reads \\ooo as octal, BIND as decimal: the simulation zone must hold the same bytes."""
    import dns.zone

    spec = {"zone": ZONE, "records": [{"name": "@", "type": "TXT", "values": ['a \\ "b"']}],
            "encoded": [{"name": "bytes.enc", "encoding": "bytes", "text": "🐙"}]}
    text = game_zone.zone_file(spec, extra=["ns 300 IN A 10.53.0.53"])
    zone = dns.zone.from_text(text, origin=ZONE, relativize=False)
    txt = {n.to_text(): b"".join(r.strings) for n, rds in zone.iterate_rdatasets("TXT") for r in rds}
    assert txt[f"bytes.enc.{ZONE}."] == "🐙".encode()
    assert txt[f"{ZONE}."] == b'a \\ "b"'
    assert zone.get_rdataset(f"ns.{ZONE}.", "A")
