#!/usr/bin/env python3

"""
CDK Application for running ConsoleMe on ECS
"""

import os

import boto3
import yaml
from aws_cdk import core as cdk

from consoleme_ecs_cdk.service.consoleme_ecs_service_stack import (
    ConsolemeEcsServiceStack,
)
from consoleme_ecs_cdk.service.consoleme_spoke_accounts_stack import (
    ConsolemeSpokeAccountsStack,
)
from consoleme_ecs_cdk.service.constants import BASE_NAME, SPOKE_BASE_NAME

config_yaml = yaml.load(open("config.yaml"), Loader=yaml.FullLoader)

spoke_accounts = config_yaml.get("spoke_accounts", [])

main_environment = cdk.Environment(
    account=boto3.client("sts").get_caller_identity().get("Account"),
    region=os.getenv("AWS_REGION"),
)

app = cdk.App()

for spoke_account_id in spoke_accounts:
    spoke_environment = cdk.Environment(
        account=spoke_account_id, region=os.getenv("AWS_REGION")
    )
    spoke_stack = ConsolemeSpokeAccountsStack(
        app, SPOKE_BASE_NAME, env=spoke_environment
    )  # Spoke account stack

consoleme_ecs_service_stack = ConsolemeEcsServiceStack(
    app, BASE_NAME, env=main_environment
)  # ConsoleMe account

app.synth()
