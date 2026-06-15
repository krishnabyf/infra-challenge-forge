resource "aws_kms_key" "terraform_state" {
  description             = "Terraform state encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "payments-terraform-state-${var.tooling_account_id}"
  tags   = { Purpose = "terraform-state" }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform_state.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "payments-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "build_trust" {
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
      values   = ["repo:${var.repository}:ref:refs/heads/main"]
    }
  }
}

data "aws_iam_policy_document" "build" {
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [
      "arn:aws:ecr:${var.aws_region}:${var.tooling_account_id}:repository/payments",
    ]
  }

  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "build_boundary" {
  name   = "payments-build-boundary"
  policy = data.aws_iam_policy_document.build.json
  tags   = { Purpose = "permissions-boundary" }
}

resource "aws_iam_policy" "build" {
  name   = "payments-build"
  policy = data.aws_iam_policy_document.build.json
  tags   = { Purpose = "build" }
}

resource "aws_iam_role" "build" {
  name                 = "payments-build"
  assume_role_policy   = data.aws_iam_policy_document.build_trust.json
  permissions_boundary = aws_iam_policy.build_boundary.arn
  max_session_duration = 3600
  tags                 = { Purpose = "build", Account = "tooling" }
}

resource "aws_iam_role_policy_attachment" "build" {
  role       = aws_iam_role.build.name
  policy_arn = aws_iam_policy.build.arn
}

module "staging_deployment" {
  source = "./modules/deployment-role"
  providers = {
    aws = aws.staging
  }

  account_name       = "staging"
  account_id         = var.staging_account_id
  github_environment = "staging"
  repository         = var.repository
}

module "production_deployment" {
  source = "./modules/deployment-role"
  providers = {
    aws = aws.production
  }

  account_name       = "production"
  account_id         = var.production_account_id
  github_environment = "production"
  repository         = var.repository
}
