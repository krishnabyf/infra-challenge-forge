terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "tls" {}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "staging"
  region = var.aws_region
  assume_role {
    role_arn = "arn:aws:iam::${var.staging_account_id}:role/OrganizationAccountAccessRole"
  }
}

provider "aws" {
  alias  = "production"
  region = var.aws_region
  assume_role {
    role_arn = "arn:aws:iam::${var.production_account_id}:role/OrganizationAccountAccessRole"
  }
}
