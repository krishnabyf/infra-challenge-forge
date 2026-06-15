data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.repository}:environment:${var.github_environment}",
      ]
    }
  }
}

data "aws_iam_policy_document" "boundary" {
  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:UpdateService",
      "iam:PassRole",
    ]
    resources = [
      "arn:aws:ecs:*:${var.account_id}:service/payments-${var.account_name}/payments",
      "arn:aws:ecs:*:${var.account_id}:task-definition/payments-${var.account_name}:*",
      "arn:aws:iam::${var.account_id}:role/payments-${var.account_name}-task",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecs:RegisterTaskDefinition",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "boundary" {
  name   = "payments-${var.account_name}-deployment-boundary"
  policy = data.aws_iam_policy_document.boundary.json
  tags   = { Purpose = "permissions-boundary" }
}

data "aws_iam_policy_document" "deployment" {
  statement {
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:UpdateService",
    ]
    resources = [
      "arn:aws:ecs:*:${var.account_id}:service/payments-${var.account_name}/payments",
    ]
  }

  statement {
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/payments-${var.account_name}-task"]
  }

  statement {
    actions = [
      "ecr:GetAuthorizationToken",
      "ecs:RegisterTaskDefinition",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "deployment" {
  name   = "payments-${var.account_name}-deployment"
  policy = data.aws_iam_policy_document.deployment.json
  tags   = { Purpose = "deployment" }
}

resource "aws_iam_role" "deployment" {
  name                 = "payments-${var.account_name}-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  permissions_boundary = aws_iam_policy.boundary.arn
  max_session_duration = 3600

  tags = {
    Purpose = "deployment"
    Account = var.account_name
  }
}

resource "aws_iam_role_policy_attachment" "deployment" {
  role       = aws_iam_role.deployment.name
  policy_arn = aws_iam_policy.deployment.arn
}
