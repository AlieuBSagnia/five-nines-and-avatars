variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "localstack_endpoint" {
  description = "If set (e.g. http://localhost:4566), all AWS calls are redirected to LocalStack. Leave empty to target real AWS."
  type        = string
  default     = "http://localhost:4566"
}

variable "environment" {
  description = "Deployment environment name, used for tagging and naming."
  type        = string
  default     = "dev"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table storing users."
  type        = string
  default     = "prima-tech-challenge-users"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket storing avatar images. Must be globally unique on real AWS."
  type        = string
  default     = "prima-tech-challenge"
}

variable "eks_oidc_provider_arn" {
  description = "ARN of the EKS cluster's OIDC provider, used to trust the ServiceAccount via IRSA. Leave empty to skip creating the IRSA trust relationship (e.g. when no EKS cluster exists yet)."
  type        = string
  default     = ""
}

variable "eks_oidc_provider_url" {
  description = "The OIDC issuer URL of the EKS cluster (without the https:// prefix), e.g. oidc.eks.us-east-1.amazonaws.com/id/XXXXX. Required if eks_oidc_provider_arn is set."
  type        = string
  default     = ""
}

variable "k8s_namespace" {
  description = "Kubernetes namespace the ServiceAccount lives in."
  type        = string
  default     = "prima-tech-challenge"
}

variable "k8s_service_account_name" {
  description = "Name of the Kubernetes ServiceAccount allowed to assume the IAM role via IRSA."
  type        = string
  default     = "prima-api"
}
