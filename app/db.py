"""
DynamoDB persistence layer.

All boto3/DynamoDB-specific error handling lives here so the API layer
only has to deal with a small set of app-level exceptions.
"""
import logging

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised for any unrecoverable persistence failure."""


class DuplicateUserError(Exception):
    """Raised when attempting to create a user whose email already exists."""


def _client():
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _table():
    return _client().Table(settings.DYNAMODB_TABLE_NAME)


def list_users() -> list[dict]:
    """Scan the users table. A Scan is fine at this scale/spec; a production
    system with high user counts would paginate and likely add a GSI-backed
    query pattern instead (see README 'What I'd extend' section)."""
    try:
        items: list[dict] = []
        table = _table()
        response = table.scan()
        items.extend(response.get("Items", []))

        # Handle pagination in case the table grows beyond 1MB scan pages.
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        return items
    except EndpointConnectionError as exc:
        logger.error("Could not reach DynamoDB endpoint: %s", exc)
        raise DatabaseError("Database is currently unreachable") from exc
    except ClientError as exc:
        logger.error("DynamoDB ClientError on scan: %s", exc)
        raise DatabaseError("Failed to read users from the database") from exc


def create_user(name: str, email: str, avatar_url: str) -> dict:
    """Persist a new user. Uses a conditional write so we never silently
    overwrite an existing user with the same email (email is the natural
    business key here)."""
    item = {"name": name, "email": email, "avatar_url": avatar_url}
    try:
        table = _table()
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(email)",
        )
        return item
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise DuplicateUserError(f"User with email {email} already exists") from exc
        logger.error("DynamoDB ClientError on put_item: %s", exc)
        raise DatabaseError("Failed to save user to the database") from exc
    except EndpointConnectionError as exc:
        logger.error("Could not reach DynamoDB endpoint: %s", exc)
        raise DatabaseError("Database is currently unreachable") from exc
