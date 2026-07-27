terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

# When var.localstack_endpoint is set, every AWS service call is redirected
# to LocalStack instead of real AWS. When it's empty (the default), this
# behaves like a normal AWS provider block — same code, two targets.
provider "aws" {
  region = var.aws_region

  access_key                 = var.localstack_endpoint != "" ? "test" : null
  secret_key                 = var.localstack_endpoint != "" ? "test" : null
  skip_credentials_validation = var.localstack_endpoint != ""
  skip_metadata_api_check     = var.localstack_endpoint != ""
  skip_requesting_account_id  = var.localstack_endpoint != ""

  dynamic "endpoints" {
    for_each = var.localstack_endpoint != "" ? [1] : []
    content {
      dynamodb = var.localstack_endpoint
      s3       = var.localstack_endpoint
      iam      = var.localstack_endpoint
      sts      = var.localstack_endpoint
    }
  }

  # Path-style addressing is required for S3 against LocalStack.
  s3_use_path_style = var.localstack_endpoint != ""
}
