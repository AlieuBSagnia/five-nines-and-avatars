"""S3 persistence layer for avatar images."""
import logging
import uuid

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised for any unrecoverable object-storage failure."""


def _client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _public_url(key: str) -> str:
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def upload_avatar(file_bytes: bytes, content_type: str, original_filename: str) -> str:
    """Upload an avatar image and return its public URL.

    The object key is a random UUID (not the user-supplied filename) to
    avoid path traversal / key collision / overwrite issues from untrusted
    input.
    """
    extension = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    key = f"avatars/{uuid.uuid4()}.{extension}"

    try:
        _client().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return _public_url(key)
    except EndpointConnectionError as exc:
        logger.error("Could not reach S3 endpoint: %s", exc)
        raise StorageError("Object storage is currently unreachable") from exc
    except ClientError as exc:
        logger.error("S3 ClientError on put_object: %s", exc)
        raise StorageError("Failed to upload avatar") from exc
