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
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(GAME, "build", "lambda")


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


class DigQuestStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
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
            memory_size=512,
            timeout=Duration.seconds(29),
            environment={"TABLE": table.table_name, "ADMIN_SECRET_ARN": admin_secret.secret_arn},
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
        )
        site_url = f"https://{dist.distribution_domain_name}"

        api = apigw.HttpApi(
            self, "HttpApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=[site_url],
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST],
                allow_headers=["content-type", "x-token", "x-admin-token"],
                max_age=Duration.hours(1),
            ),
            default_integration=integrations.HttpLambdaIntegration("LambdaIntegration", fn),
        )
        stage = api.default_stage.node.default_child
        stage.default_route_settings = apigw.CfnStage.RouteSettingsProperty(throttling_burst_limit=100, throttling_rate_limit=50)

        s3deploy.BucketDeployment(
            self, "DeploySite",
            destination_bucket=bucket,
            distribution=dist,
            sources=[
                s3deploy.Source.asset(os.path.join(GAME, "frontend")),
                # later sources win: this replaces the local-dev config.js
                s3deploy.Source.data("config.js", cdk.Fn.join("", ["window.QUEST_API = \"", api.api_endpoint, "\";"])),
            ],
        )

        cdk.CfnOutput(self, "GameUrl", value=site_url)
        cdk.CfnOutput(self, "BoardUrl", value=f"{site_url}/board.html?session=CODE")
        cdk.CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        cdk.CfnOutput(self, "AdminSecretArn", value=admin_secret.secret_arn)
