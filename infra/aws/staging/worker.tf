resource "aws_ecs_task_definition" "worker" {
  family = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  cpu = var.worker_cpu
  memory = var.worker_memory
  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn = aws_iam_role.app.arn
  container_definitions = jsonencode([{
    name = "worker"
    image = var.container_image
    essential = true
    command = ["celery", "-A", "reconciliation_platform.worker:celery_app", "worker", "--loglevel=INFO"]
    environment = [
      { name = "DATABASE_HOST", value = aws_db_instance.staging.address },
      { name = "DATABASE_PORT", value = "5432" },
      { name = "DATABASE_NAME", value = "reconciliation" },
      { name = "DATABASE_USER", value = "reconciliation" },
      { name = "JOB_QUEUE", value = "celery" },
      { name = "REDIS_URL", value = "rediss://${aws_elasticache_replication_group.staging.primary_endpoint_address}:6379/0" },
      { name = "OBJECT_STORE", value = "s3" },
      { name = "S3_BUCKET", value = aws_s3_bucket.objects.bucket },
      { name = "S3_PREFIX", value = "reconciliation" },
      { name = "AI_PROVIDER", value = "none" }
    ]
    secrets = [
      { name = "DATABASE_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group = aws_cloudwatch_log_group.worker.name
        awslogs-region = var.aws_region
        awslogs-stream-prefix = "worker"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name = "${local.name}-api"
  cluster = aws_ecs_cluster.staging.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count = var.api_desired_count
  launch_type = "FARGATE"
  network_configuration {
    subnets = aws_subnet.public[*].id
    security_groups = [aws_security_group.app.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name = "api"
    container_port = 8000
  }
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent = 200
  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_service" "worker" {
  name = "${local.name}-worker"
  cluster = aws_ecs_cluster.staging.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count = var.worker_desired_count
  launch_type = "FARGATE"
  network_configuration {
    subnets = aws_subnet.public[*].id
    security_groups = [aws_security_group.app.id]
    assign_public_ip = true
  }
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent = 200
}

data "aws_route53_zone" "staging" {
  name = var.staging_domain
  private_zone = false
}

resource "aws_route53_record" "staging" {
  zone_id = data.aws_route53_zone.staging.zone_id
  name = var.staging_domain
  type = "A"
  alias {
    name = aws_lb.staging.dns_name
    zone_id = aws_lb.staging.zone_id
    evaluate_target_health = true
  }
}
