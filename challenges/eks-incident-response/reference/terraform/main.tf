data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
  subnets = {
    for index, az in local.azs : az => {
      private_cidr = cidrsubnet(var.vpc_cidr, 4, index)
      public_cidr  = cidrsubnet(var.vpc_cidr, 4, index + 8)
    }
  }
}

resource "aws_vpc" "platform" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}

resource "aws_internet_gateway" "platform" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_subnet" "private" {
  for_each = local.subnets

  vpc_id                  = aws_vpc.platform.id
  availability_zone       = each.key
  cidr_block              = each.value.private_cidr
  map_public_ip_on_launch = false
  tags = {
    Name                              = "${var.name}-private-${each.key}"
    Tier                              = "private"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_subnet" "public" {
  for_each = local.subnets

  vpc_id                  = aws_vpc.platform.id
  availability_zone       = each.key
  cidr_block              = each.value.public_cidr
  map_public_ip_on_launch = true
  tags = {
    Name                     = "${var.name}-public-${each.key}"
    Tier                     = "public"
    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_eip" "nat" {
  for_each = local.subnets
  domain   = "vpc"
}

resource "aws_nat_gateway" "az" {
  for_each = local.subnets

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id
  depends_on    = [aws_internet_gateway.platform]
}

resource "aws_route_table" "private" {
  for_each = local.subnets
  vpc_id   = aws_vpc.platform.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.az[each.key].id
  }
}

resource "aws_route_table_association" "private" {
  for_each       = local.subnets
  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_security_group" "control_plane" {
  name   = "${var.name}-control-plane"
  vpc_id = aws_vpc.platform.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

resource "aws_kms_key" "eks" {
  description             = "EKS secrets envelope encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

data "aws_iam_policy_document" "payments" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [var.payments_table_arn]
  }

  statement {
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.eks.arn]
  }
}

resource "aws_iam_policy" "payments" {
  name   = "${var.name}-payments"
  policy = data.aws_iam_policy_document.payments.json
}

resource "aws_eks_cluster" "platform" {
  name     = var.name
  role_arn = "arn:aws:iam::111122223333:role/replace-with-cluster-role"

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler",
  ]

  vpc_config {
    subnet_ids              = values(aws_subnet.private)[*].id
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = [aws_security_group.control_plane.id]
  }

  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = aws_kms_key.eks.arn
    }
  }
}

