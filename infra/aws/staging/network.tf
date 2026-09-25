data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_caller_identity" "current" {}

locals {
  name = var.project_name
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "staging" {
  cidr_block = "10.40.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
}
resource "aws_internet_gateway" "staging" {
  vpc_id = aws_vpc.staging.id
}
resource "aws_subnet" "public" {
  count = 2
  vpc_id = aws_vpc.staging.id
  cidr_block = cidrsubnet(aws_vpc.staging.cidr_block, 8, count.index)
  availability_zone = local.azs[count.index]
  map_public_ip_on_launch = true
}
resource "aws_subnet" "private" {
  count = 2
  vpc_id = aws_vpc.staging.id
  cidr_block = cidrsubnet(aws_vpc.staging.cidr_block, 8, count.index + 10)
  availability_zone = local.azs[count.index]
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.staging.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.staging.id
  }
}
resource "aws_route_table_association" "public" {
  count = 2
  subnet_id = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_db_subnet_group" "staging" {
  name = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_elasticache_subnet_group" "staging" {
  name = "${local.name}-redis"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "alb" {
  name = "${local.name}-alb"
  vpc_id = aws_vpc.staging.id
  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "app" {
  name = "${local.name}-app"
  vpc_id = aws_vpc.staging.id
  ingress {
    from_port = 8000
    to_port = 8000
    protocol = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "db" {
  name = "${local.name}-db"
  vpc_id = aws_vpc.staging.id
  ingress {
    from_port = 5432
    to_port = 5432
    protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
resource "aws_security_group" "redis" {
  name = "${local.name}-redis"
  vpc_id = aws_vpc.staging.id
  ingress {
    from_port = 6379
    to_port = 6379
    protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
