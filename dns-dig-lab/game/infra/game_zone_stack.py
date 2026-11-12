"""Dig Quest game zone: a public Route 53 zone holding the puzzle records of the advanced missions."""
import hashlib
import ipaddress
import json
import os

import aws_cdk as cdk
from aws_cdk import Duration, Stack, aws_route53 as route53
from constructs import Construct

import game_server
import game_zone

SECRET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "secret"))
SPEC = os.path.join(SECRET, "zone.json")
SERVER_SPEC = os.path.join(SECRET, "server.json")


def load_spec(path=SPEC):
    """A private spec (the puzzles by default, or the game server), or None when the secret repo has none."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def server_address(spec):
    """The public IPv4 of the game server, checked: a wrong A record would break missions a21 to a25."""
    try:
        ip = ipaddress.IPv4Address(spec.get("address", ""))
    except ValueError:
        raise SystemExit(f"secret/server.json: set \"address\" to the reserved public IPv4 of the game server "
                         f"(now {spec.get('address')!r})")
    if not ip.is_global:
        raise SystemExit(f"secret/server.json: {ip} is not a public address")
    return str(ip)


class GameZoneStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, spec: dict, server: dict = None, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        name = spec["zone"].rstrip(".")
        zone = route53.PublicHostedZone(self, "Zone", zone_name=name, comment="Dig Quest puzzles (advanced missions)")

        for rs in game_zone.build(spec, SECRET):
            # logical id from the name and type, so editing one record never replaces the others
            rid = "R" + hashlib.sha1(f"{rs['name']}|{rs['type']}".encode()).hexdigest()[:12]
            route53.CfnRecordSet(self, rid, hosted_zone_id=zone.hosted_zone_id, name=rs["name"], type=rs["type"],
                                 ttl=str(rs["ttl"]), resource_records=rs["values"])

        parent = spec.get("parent")
        if parent:
            # the parent zone is in this account: delegate to the new zone's name servers
            parent_zone = route53.HostedZone.from_lookup(self, "Parent", domain_name=parent)
            route53.ZoneDelegationRecord(self, "Delegation", zone=parent_zone, record_name=name,
                                         name_servers=zone.hosted_zone_name_servers, ttl=Duration.hours(1))

        if server:
            # the BIND game server (Docker, outside AWS) and the sub-zones it serves
            ns = game_server.server_fqdn(server)
            route53.ARecord(self, "GameServer", zone=zone, record_name=ns,
                            target=route53.RecordTarget.from_ip_addresses(server_address(server)), ttl=Duration.minutes(5))
            for sub in game_server.delegations(server):
                route53.NsRecord(self, f"Delegate-{sub}", zone=zone, record_name=sub, values=[f"{ns}."],
                                 ttl=Duration.minutes(5))

        cdk.CfnOutput(self, "ZoneName", value=name)
        cdk.CfnOutput(self, "NameServers", value=cdk.Fn.join(" ", zone.hosted_zone_name_servers))
