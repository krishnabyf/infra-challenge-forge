data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

resource "aws_vpc" "platform" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = false
  tags                 = { Name = var.name }
}

resource "aws_subnet" "workload" {
  for_each = toset(local.azs)

  vpc_id                  = aws_vpc.platform.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, index(local.azs, each.value))
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-${each.value}", Tier = "private" }
}

resource "aws_security_group" "control_plane" {
  name   = "${var.name}-control-plane"
  vpc_id = aws_vpc.platform.id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_policy" "payments" {
  name = "${var.name}-payments"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "aws_eks_cluster" "platform" {
  name     = var.name
  role_arn = "arn:aws:iam::111122223333:role/replace-me"

  enabled_cluster_log_types = ["api"]

  vpc_config {
    subnet_ids              = values(aws_subnet.workload)[*].id
    endpoint_private_access = false
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
    security_group_ids      = [aws_security_group.control_plane.id]
  }
}

