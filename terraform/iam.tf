# ---------------------------------------------------------------------------
# Least-privilege IAM policy: only the specific DynamoDB table + S3 prefix
# actions the app actually performs. No wildcard resources, no admin-y verbs.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "app_permissions" {
  statement {
    sid    = "DynamoDBUserTableAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.users.arn,
    ]
  }

  statement {
    sid    = "S3AvatarObjectAccess"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
    ]
    # tfsec:ignore:aws-iam-no-policy-wildcards -- Object-level S3 access must be scoped to the avatars prefix; the wildcard is limited to avatars/* only.
    resources = [
      "${aws_s3_bucket.avatars.arn}/avatars/*",
    ]
    condition {
      test     = "StringLike"
      variable = "s3:objectkey"
      values   = ["avatars/*"]
    }
  }

  statement {
    sid    = "S3BucketLocation"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
    ]
    resources = [
      aws_s3_bucket.avatars.arn,
    ]
  }
}

resource "aws_iam_policy" "app_permissions" {
  name        = "prima-tech-challenge-app-policy"
  description = "Least-privilege access to the users table and avatars prefix"
  policy      = data.aws_iam_policy_document.app_permissions.json
  tags        = local.common_tags
}

# ---------------------------------------------------------------------------
# IRSA (IAM Roles for Service Accounts): lets the Kubernetes ServiceAccount
# used by the Helm chart assume this role directly via the EKS cluster's
# OIDC provider — no long-lived AWS keys stored in the cluster at all.
#
# This block only creates the trust relationship if an EKS OIDC provider ARN
# is supplied (it's intentionally optional: per the challenge instructions we
# are not standing up a real EKS cluster to test against, but the code is
# complete and ready to point at one).
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "irsa_trust" {
  count = var.eks_oidc_provider_arn != "" ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.eks_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.eks_oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${var.k8s_namespace}:${var.k8s_service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.eks_oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app_irsa_role" {
  count              = var.eks_oidc_provider_arn != "" ? 1 : 0
  name               = "prima-tech-challenge-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust[0].json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "app_irsa_attach" {
  count      = var.eks_oidc_provider_arn != "" ? 1 : 0
  role       = aws_iam_role.app_irsa_role[0].name
  policy_arn = aws_iam_policy.app_permissions.arn
}

data "aws_iam_policy_document" "app_dev_group_mfa" {
  statement {
    sid       = "RequireMFAForGroup"
    effect    = "Deny"
    actions   = ["*"]
    resources = ["*"]

    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["false"]
    }
  }
}

resource "aws_iam_policy" "app_dev_group_mfa" {
  name        = "prima-tech-challenge-dev-group-mfa-policy"
  description = "Require MFA for users in the dev group"
  policy      = data.aws_iam_policy_document.app_dev_group_mfa.json
  tags        = local.common_tags
}

resource "aws_iam_group_policy_attachment" "app_dev_group_mfa_attach" {
  group      = aws_iam_group.app_dev_group.name
  policy_arn = aws_iam_policy.app_dev_group_mfa.arn
}

# For local/dev testing without EKS (e.g. LocalStack or minikube with static
# credentials), a plain IAM user + access key is provisioned instead so the
# Helm chart always has *something* it can authenticate with in Task 4/local
# testing, without requiring a full EKS OIDC setup.
resource "aws_iam_user" "app_dev_user" {
  name = "prima-tech-challenge-dev-user"
  tags = local.common_tags
}

resource "aws_iam_group" "app_dev_group" {
  name = "prima-tech-challenge-dev-group"
}

resource "aws_iam_group_policy_attachment" "app_dev_group_attach" {
  group      = aws_iam_group.app_dev_group.name
  policy_arn = aws_iam_policy.app_permissions.arn
}

resource "aws_iam_user_group_membership" "app_dev_user_groups" {
  user = aws_iam_user.app_dev_user.name

  groups = [
    aws_iam_group.app_dev_group.name,
  ]
}

resource "aws_iam_access_key" "app_dev_user_key" {
  user = aws_iam_user.app_dev_user.name
}
