#!/usr/bin/env python3
import os

import aws_cdk as cdk

from dig_quest_stack import DigQuestStack
import game_server
import game_zone_stack

app = cdk.App()
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=os.environ.get("CDK_DEFAULT_REGION"))
zone_spec, server_spec = game_zone_stack.load_spec(), game_zone_stack.load_spec(game_zone_stack.SERVER_SPEC)
# the dig console allows AXFR and -p only toward the game server
DigQuestStack(app, "DigQuest", game_server=game_server.server_fqdn(server_spec) if server_spec else None, env=env)
if zone_spec:
    game_zone_stack.GameZoneStack(app, "DigQuestZone", spec=zone_spec, server=server_spec, env=env)
app.synth()
