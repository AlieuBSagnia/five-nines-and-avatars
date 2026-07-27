"""
Centralised configuration, loaded from environment variables.

Keeping all env-var access in one place makes it trivial to see what the
app depends on, and to override everything in tests / Helm / docker-compose
without touching business logic.
"""
import os


class Settings:
    # AWS / Localstack
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ENDPOINT_URL: str | None = os.getenv("AWS_ENDPOINT_URL")  # e.g. http://localstack:4566
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "test")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

    # DynamoDB
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "prima-tech-challenge-users")

    # S3
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "prima-tech-challenge")
    S3_PUBLIC_BASE_URL: str | None = os.getenv("S3_PUBLIC_BASE_URL")  # override for path-style/localstack URLs

    # App
    MAX_AVATAR_SIZE_BYTES: int = int(os.getenv("MAX_AVATAR_SIZE_BYTES", str(5 * 1024 * 1024)))  # 5MB
    ALLOWED_AVATAR_CONTENT_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
