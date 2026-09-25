resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "ecs_secret_read" {
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.db_password.arn,
        aws_secretsmanager_secret.api_key.arn,
        aws_secretsmanager_secret.tenant_api_keys.arn
      ]
    }]
  })
}

resource "aws_iam_role" "app" {
  name = "${local.name}-app"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "app" {
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.objects.arn}/*"
      },
      {
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = aws_s3_bucket.objects.arn
      }
    ]
  })
}

resource "aws_ecs_cluster" "staging" {
  name = "${local.name}-staging"
  setting {
    name  = "containerInsights"
    value = "enhanced"
  }
}
resource "aws_ecs_cluster_capacity_providers" "staging" {
  cluster_name = aws_ecs_cluster.staging.name
  capacity_providers = ["FARGATE"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight = 1
  }
}

resource "aws_lb" "staging" {
  name = "${local.name}-stg"
  load_balancer_type = "application"
  subnets = aws_subnet.public[*].id
  security_groups = [aws_security_group.alb.id]
}
resource "aws_lb_target_group" "api" {
  name = "${local.name}-api"
  port = 8000
  protocol = "HTTP"
  target_type = "ip"
  vpc_id = aws_vpc.staging.id
  health_check {
    path = "/ready"
    matcher = "200"
    interval = 30
    timeout = 10
    healthy_threshold = 2
    unhealthy_threshold = 3
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.staging.arn
  port = 443
  protocol = "HTTPS"
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn = var.acm_certificate_arn
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  cpu = var.api_cpu
  memory = var.api_memory
  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn = aws_iam_role.app.arn
  container_definitions = jsonencode([{
    name = "api"
    image = var.container_image
    essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "API_KEY_REQUIRED", value = "true" },
      { name = "DATABASE_HOST", value = aws_db_instance.staging.address },
      { name = "DATABASE_PORT", value = "5432" },
      { name = "DATABASE_NAME", value = "reconciliation" },
      { name = "DATABASE_USER", value = "reconciliation" },
      { name = "JOB_QUEUE", value = "celery" },
      { name = "REDIS_URL", value = "rediss://${aws_elasticache_replication_group.staging.primary_endpoint_address}:6379/0" },
      { name = "RATE_LIMIT_PER_MINUTE", value = "60" },
      { name = "RATE_LIMIT_BACKEND", value = "redis" },
      { name = "OBJECT_STORE", value = "s3" },
      { name = "S3_BUCKET", value = aws_s3_bucket.objects.bucket },
      { name = "S3_PREFIX", value = "reconciliation" },
      { name = "AI_PROVIDER", value = "none" }
    ]
    secrets = [
      { name = "DATABASE_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
      { name = "RECONCILIATION_API_KEY", valueFrom = aws_secretsmanager_secret.api_key.arn },
      { name = "TENANT_API_KEYS", valueFrom = aws_secretsmanager_secret.tenant_api_keys.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group = aws_cloudwatch_log_group.api.name
        awslogs-region = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
    healthCheck = {
      command = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')\""]
      interval = 30
      timeout = 10
      retries = 3
      startPeriod = 30
    }
  }])
}
