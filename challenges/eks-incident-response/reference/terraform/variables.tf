variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "recovery"
}

variable "name" {
  type    = string
  default = "payments-recovery"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "payments_table_arn" {
  type = string
}

