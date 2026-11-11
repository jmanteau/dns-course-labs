"""Dig Quest: HTTP API -> Lambda -> DynamoDB, static front end on S3 + CloudFront."""
import os
import shutil
import subprocess
import sys

import aws_cdk as cdk
from aws_cdk import (
    Duration, RemovalPolicy, Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(GAME, "build", "lambda")
DECK = os.path.join(GAME, "..", "..", "course", "_site", "dns-advanced-single.html")
DECK_BUILD = os.path.join(GAME, "build", "deck")


def assemble_lambda():
    """Copy backend code, the private answer data and dependencies into one folder."""
    secret = os.path.join(GAME, "secret")
    if not os.path.isfile(os.path.join(secret, "questions.json")):
        sys.exit("game/secret/questions.json is missing: run `git submodule update --init` (private answers repo).")
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.copytree(os.path.join(GAME, "backend"), BUILD, ignore=shutil.ignore_patterns("__pycache__", "requirements.txt"))
    shutil.copytree(secret, os.path.join(BUILD, "secret"), ignore=shutil.ignore_patterns(".git", ".git*"))
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join(GAME, "backend", "requirements.txt"), "-t", BUILD,
         "--platform", "manylinux2014_aarch64", "--only-binary=:all:", "--python-version", "3.12", "--implementation", "cp"],
        check=True,
    )
    return BUILD


def assemble_deck():
    """The advanced theory deck, served next to the game as deck/dns-advanced.html (None if not built)."""
    if not os.path.isfile(DECK):
        print("warning: course/_site/dns-advanced-single.html is missing (run `make single DECK=dns-advanced` in course/):"
              " the game's link to the advanced slides will not work", file=sys.stderr)
        return None
    shutil.rmtree(DECK_BUILD, ignore_errors=True)
    os.makedirs(os.path.join(DECK_BUILD, "deck"))
    shutil.copy(DECK, os.path.join(DECK_BUILD, "deck", "dns-advanced.html"))
    return DECK_BUILD


class DigQuestStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, game_server: str = None, domain: str = None,
                 zone_name: str = None, certificate=None, **kwargs):
        """`domain` (a name in the Route 53 zone `zone_name`) + `certificate` (us-east-1, from CertStack):
        the site also answers on https://<domain>."""
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.TableV2(
            self, "Table",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.RETAIN,
        )

        admin_secret = secretsmanager.Secret(
            self, "AdminToken",
            description="x-admin-token for the Dig Quest teacher API",
            generate_secret_string=secretsmanager.SecretStringGenerator(password_length=32, exclude_punctuation=True),
        )

        fn = lambda_.Function(
            self, "Api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(assemble_lambda()),
            memory_size=1024,  # twice the CPU: faster imports, JSON and cold starts
            timeout=Duration.seconds(29),
            environment={"TABLE": table.table_name, "ADMIN_SECRET_ARN": admin_secret.secret_arn,
                         **({"GAME_SERVER": game_server} if game_server else {})},
        )
        table.grant_read_write_data(fn)
        admin_secret.grant_read(fn)

        bucket = s3.Bucket(
            self, "Site",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        dist = cloudfront.Distribution(
            self, "Cdn",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            **({"domain_names": [domain], "certificate": certificate} if domain else {}),
        )
        origins_allowed = [f"https://{dist.distribution_domain_name}"]
        if domain:
            # the game's own address, kept out of the puzzle zone
            zone = route53.HostedZone.from_lookup(self, "SiteZone", domain_name=zone_name)
            target = route53.RecordTarget.from_alias(targets.CloudFrontTarget(dist))
            route53.ARecord(self, "SiteAlias", zone=zone, record_name=domain, target=target)
            route53.AaaaRecord(self, "SiteAlias6", zone=zone, record_name=domain, target=target)
            origins_allowed.append(f"https://{domain}")
        site_url = origins_allowed[-1]

        api = apigw.HttpApi(
            self, "HttpApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=origins_allowed,
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST],
                allow_headers=["content-type", "x-token", "x-admin-token"],
                max_age=Duration.hours(1),
            ),
            default_integration=integrations.HttpLambdaIntegration("LambdaIntegration", fn),
        )
        stage = api.default_stage.node.default_child
        stage.default_route_settings = apigw.CfnStage.RouteSettingsProperty(throttling_burst_limit=100, throttling_rate_limit=50)

        # WebSocket doorbell: the teacher's actions ring every open page at once (backend/push.py)
        ws_integration = integrations.WebSocketLambdaIntegration("WsIntegration", fn)
        ws_api = apigw.WebSocketApi(
            self, "WsApi",
            connect_route_options=apigw.WebSocketRouteOptions(integration=ws_integration),
            disconnect_route_options=apigw.WebSocketRouteOptions(integration=ws_integration),
            default_route_options=apigw.WebSocketRouteOptions(integration=ws_integration),
        )
        ws_stage = apigw.WebSocketStage(self, "WsStage", web_socket_api=ws_api, stage_name="prod", auto_deploy=True)
        ws_api.grant_manage_connections(fn)
        fn.add_environment("WS_CALLBACK", ws_stage.callback_url)

        deck = assemble_deck()
        s3deploy.BucketDeployment(
            self, "DeploySite",
            destination_bucket=bucket,
            distribution=dist,
            sources=[
                s3deploy.Source.asset(os.path.join(GAME, "frontend")),
                # later sources win: this replaces the local-dev config.js
                s3deploy.Source.data("config.js", cdk.Fn.join("", [
                    "window.QUEST_API = \"", api.api_endpoint, "\";\nwindow.QUEST_WS = \"", ws_stage.url, "\";"])),
            ] + ([s3deploy.Source.asset(deck)] if deck else []),
        )

        cdk.CfnOutput(self, "GameUrl", value=site_url)
        cdk.CfnOutput(self, "BoardUrl", value=f"{site_url}/board.html?session=CODE")
        cdk.CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        cdk.CfnOutput(self, "WsUrl", value=ws_stage.url)
        cdk.CfnOutput(self, "AdminSecretArn", value=admin_secret.secret_arn)
