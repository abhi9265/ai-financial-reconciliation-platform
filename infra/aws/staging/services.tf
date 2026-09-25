resource "random_password" "db" {
  length = 32
  special = true
}
resource "random_password" "api" {
  length = 48
  special = true
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${local.name}/staging/database-password"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}
resource "aws_secretsmanager_secret" "api_key" {
  name = "${local.name}/staging/api-key"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id = aws_secretsmanager_secret.api_key.id
  secret_string = random_password.api.result
}
resource "aws_secretsmanager_secret" "tenant_api_keys" {
  name = "${local.name}/staging/tenant-api-keys"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "tenant_api_keys" {
  secret_id = aws_secretsmanager_secret.tenant_api_keys.id
  secret_string = "staging:${random_password.api.result}"
}

resource "aws_db_instance" "staging" {
  identifier = "${local.name}-staging"
  engine = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class
  allocated_storage = 20
  max_allocated_storage = 50
  storage_type = "gp3"
  db_name = "reconciliation"
  username = "reconciliation"
  password = random_password.db.result
  port = 5432
  db_subnet_group_name = aws_db_subnet_group.staging.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible = false
  backup_retention_period = 7
  deletion_protection = false
  skip_final_snapshot = true
  multi_az = false
  apply_immediately = true
}

resource "aws_elasticache_replication_group" "staging" {
  replication_group_id = "${local.name}-staging"
  description = "Redis broker for staging"
  node_type = var.redis_node_type
  num_cache_clusters = 1
  engine = "redis"
  engine_version = "7.1"
  port = 6379
  subnet_group_name = aws_elasticache_subnet_group.staging.name
  security_group_ids = [aws_security_group.redis.id]
  automatic_failover_enabled = false
  multi_az_enabled = false
  transit_encryption_enabled = true
}

resource "aws_s3_bucket" "objects" {
  bucket = "${local.name}-staging-${data.aws_caller_identity.current.account_id}"
}
resource "aws_s3_bucket_public_access_block" "objects" {
  bucket = aws_s3_bucket.objects.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_versioning" "objects" {
  bucket = aws_s3_bucket.objects.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_ecr_repository" "app" {
  name = local.name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name = "/ecs/${local.name}/api"
  retention_in_days = 14
}
resource "aws_cloudwatch_log_group" "worker" {
  name = "/ecs/${local.name}/worker"
  retention_in_days = 14
}
