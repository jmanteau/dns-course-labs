#!/usr/bin/env python3
import os
import sys

import aws_cdk as cdk

from cert_stack import CertStack
from dig_quest_stack import DigQuestStack
import game_server
import game_zone_stack

app = cdk.App()
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=os.environ.get("CDK_DEFAULT_REGION"))
zone_spec, server_spec = game_zone_stack.load_spec(), game_zone_stack.load_spec(game_zone_stack.SERVER_SPEC)
if server_spec:
    try:
        game_zone_stack.server_address(server_spec)
    except SystemExit as exc:
        # deploy the rest anyway: the game server's records come with the first deploy after the address is set
        print(f"warning: no game server records: {exc}", file=sys.stderr)
        server_spec = None
# the game's own address (cdk.json context: siteDomain in the Route 53 zone siteZone), apart from the puzzle zone;
# CloudFront needs its certificate in us-east-1
domain, site_zone = app.node.try_get_context("siteDomain"), app.node.try_get_context("siteZone")
cert = (CertStack(app, "DigQuestSiteCert", domain=domain, zone_name=site_zone, cross_region_references=True,
                  env=cdk.Environment(account=env.account, region="us-east-1")).certificate if domain else None)
# the dig console allows AXFR and -p only toward the game server
DigQuestStack(app, "DigQuest", game_server=game_server.server_fqdn(server_spec) if server_spec else None,
              domain=domain, zone_name=site_zone, certificate=cert, cross_region_references=bool(domain), env=env)
if zone_spec:
    game_zone_stack.GameZoneStack(app, "DigQuestZone", spec=zone_spec, server=server_spec, env=env)
app.synth()
