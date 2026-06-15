variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "repository" {
  type    = string
  default = "krishnabyf/infra-challenge-forge"
}

variable "tooling_account_id" {
  type = string
}

variable "staging_account_id" {
  type = string
}

variable "production_account_id" {
  type = string
}

