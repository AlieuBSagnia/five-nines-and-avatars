import boto3
import pytest
from moto import mock_aws

from app.config import settings


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Ensure boto3 never accidentally touches real AWS during tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", settings.AWS_REGION)


@pytest.fixture
def mocked_aws(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        dynamodb.create_table(
            TableName=settings.DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)

        yield


@pytest.fixture
def client(mocked_aws):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)
