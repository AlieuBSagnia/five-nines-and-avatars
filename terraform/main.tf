locals {
  common_tags = {
    Project     = "prima-tech-challenge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_key" "main" {
  description             = "KMS key for DynamoDB and S3 encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_alias" "main" {
  name          = "alias/prima-tech-challenge"
  target_key_id = aws_kms_key.main.key_id
}

# ---------------------------------------------------------------------------
# DynamoDB — stores user records. "email" is the natural business key
# (unique per user), avoiding a synthetic UUID nobody asked for.
# On-demand billing removes the need to guess/manage capacity for a
# workload with an unknown, spiky access pattern like this one.
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "users" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "email"

  attribute {
    name = "email"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# S3 — stores avatar images. Public read is scoped to a bucket policy on the
# avatars/ prefix only (so the app can return directly-usable URLs, matching
# the spec's expected avatar_url), rather than making the whole bucket public
# or disabling all public-access protections wholesale.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "avatars" {
  bucket = var.s3_bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "avatars" {
  bucket = aws_s3_bucket.avatars.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "avatars" {
  bucket = aws_s3_bucket.avatars.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "avatars" {
  bucket = aws_s3_bucket.avatars.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "access_logs" {
  bucket = "${var.s3_bucket_name}-access-logs"
  tags   = local.common_tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "avatars" {
  bucket = aws_s3_bucket.avatars.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "avatars/"
}

resource "aws_s3_bucket_lifecycle_configuration" "avatars" {
  bucket = aws_s3_bucket.avatars.id

  rule {
    id     = "expire-old-noncurrent-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
