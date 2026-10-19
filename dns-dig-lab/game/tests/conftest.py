import os
import sys

import boto3
import pytest
from moto import mock_aws

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
os.environ.update(
    AWS_DEFAULT_REGION="eu-west-3", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
    TABLE="quest", ADMIN_TOKEN="adm", SECRET_DIR=os.path.join(HERE, "fixtures"),
)


@pytest.fixture
def db():
    with mock_aws():
        boto3.client("dynamodb").create_table(
            TableName="quest", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        )
        yield
