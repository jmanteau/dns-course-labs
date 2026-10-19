#!/usr/bin/env python3
import os

import aws_cdk as cdk

from dig_quest_stack import DigQuestStack

app = cdk.App()
DigQuestStack(
    app,
    "DigQuest",
    env=cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=os.environ.get("CDK_DEFAULT_REGION")),
)
app.synth()
