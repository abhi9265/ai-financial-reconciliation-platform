resource "aws_sns_topic" "alerts" {
  name = "${local.name}-staging-alerts"
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name = "${local.name}-staging-alb-5xx"
  alarm_description = "ALB is returning elevated 5xx responses."
  namespace = "AWS/ApplicationELB"
  metric_name = "HTTPCode_ELB_5XX_Count"
  statistic = "Sum"
  period = 300
  evaluation_periods = 2
  threshold = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.staging.arn_suffix
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name = "${local.name}-staging-target-5xx"
  alarm_description = "Application targets are returning elevated 5xx responses."
  namespace = "AWS/ApplicationELB"
  metric_name = "HTTPCode_Target_5XX_Count"
  statistic = "Sum"
  period = 300
  evaluation_periods = 2
  threshold = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.staging.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "target_latency" {
  alarm_name = "${local.name}-staging-target-latency"
  alarm_description = "API target response latency is elevated."
  namespace = "AWS/ApplicationELB"
  metric_name = "TargetResponseTime"
  statistic = "Average"
  period = 300
  evaluation_periods = 3
  threshold = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "notBreaching"
  dimensions = {
    LoadBalancer = aws_lb.staging.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_unhealthy_hosts" {
  alarm_name = "${local.name}-staging-unhealthy-api-hosts"
  alarm_description = "At least one API target is unhealthy."
  namespace = "AWS/ApplicationELB"
  metric_name = "UnHealthyHostCount"
  statistic = "Maximum"
  period = 60
  evaluation_periods = 2
  threshold = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "breaching"
  dimensions = {
    LoadBalancer = aws_lb.staging.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_running_tasks" {
  alarm_name = "${local.name}-staging-api-running-tasks"
  alarm_description = "API ECS service has fewer running tasks than desired."
  namespace = "ECS/ContainerInsights"
  metric_name = "RunningTaskCount"
  statistic = "Minimum"
  period = 300
  evaluation_periods = 2
  threshold = var.api_desired_count
  comparison_operator = "LessThanThreshold"
  treat_missing_data = "breaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.staging.name
    ServiceName = aws_ecs_service.api.name
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "worker_running_tasks" {
  alarm_name = "${local.name}-staging-worker-running-tasks"
  alarm_description = "Worker ECS service has fewer running tasks than desired."
  namespace = "ECS/ContainerInsights"
  metric_name = "RunningTaskCount"
  statistic = "Minimum"
  period = 300
  evaluation_periods = 2
  threshold = var.worker_desired_count
  comparison_operator = "LessThanThreshold"
  treat_missing_data = "breaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.staging.name
    ServiceName = aws_ecs_service.worker.name
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name = "${local.name}-staging-db-cpu"
  alarm_description = "RDS PostgreSQL CPU is elevated."
  namespace = "AWS/RDS"
  metric_name = "CPUUtilization"
  statistic = "Average"
  period = 300
  evaluation_periods = 3
  threshold = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "notBreaching"
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.staging.id
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name = "${local.name}-staging-db-storage"
  alarm_description = "RDS free storage is approaching the configured floor."
  namespace = "AWS/RDS"
  metric_name = "FreeStorageSpace"
  statistic = "Minimum"
  period = 300
  evaluation_periods = 2
  threshold = 2147483648
  comparison_operator = "LessThanOrEqualToThreshold"
  treat_missing_data = "breaching"
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.staging.id
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name = "${local.name}-staging-redis-cpu"
  alarm_description = "ElastiCache Redis CPU is elevated."
  namespace = "AWS/ElastiCache"
  metric_name = "EngineCPUUtilization"
  statistic = "Average"
  period = 300
  evaluation_periods = 3
  threshold = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data = "notBreaching"
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.staging.id
  }
  alarm_actions = [aws_sns_topic.alerts.arn]
}
