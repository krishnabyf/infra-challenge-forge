resource "aws_s3_bucket" "state" {
  bucket = "payments-terraform-state"
  tags   = { Purpose = "terraform-state" }
}

resource "aws_iam_user" "github" {
  name = "github-actions"
}

resource "aws_iam_access_key" "github" {
  user = aws_iam_user.github.name
}

resource "aws_iam_role" "shared_deploy" {
  name                 = "shared-admin-deploy"
  max_session_duration = 43200
  tags = {
    Purpose = "deployment"
    Account = "production"
  }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = aws_iam_user.github.arn }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "deploy" {
  name = "shared-admin-deploy"
  tags = { Purpose = "deployment" }
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

