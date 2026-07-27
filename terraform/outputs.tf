output "dynamodb_table_name" {
  value = aws_dynamodb_table.users.name
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.users.arn
}

output "s3_bucket_name" {
  value = aws_s3_bucket.avatars.bucket
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.avatars.arn
}

output "app_iam_policy_arn" {
  value = aws_iam_policy.app_permissions.arn
}

output "irsa_role_arn" {
  value       = var.eks_oidc_provider_arn != "" ? aws_iam_role.app_irsa_role[0].arn : null
  description = "Set only if eks_oidc_provider_arn was supplied. Use as the eks.amazonaws.com/role-arn annotation on the K8s ServiceAccount."
}

output "dev_user_access_key_id" {
  value       = aws_iam_access_key.app_dev_user_key.id
  description = "For local/dev testing only (LocalStack, minikube without IRSA). Not for production use."
}

output "dev_user_secret_access_key" {
  value     = aws_iam_access_key.app_dev_user_key.secret
  sensitive = true
}
