output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
output "staging_url" {
  value = "https://${var.staging_domain}"
}
output "alb_dns_name" {
  value = aws_lb.staging.dns_name
}
output "database_endpoint" {
  value = aws_db_instance.staging.address
  sensitive = true
}
output "redis_endpoint" {
  value = aws_elasticache_replication_group.staging.primary_endpoint_address
  sensitive = true
}
output "s3_bucket" {
  value = aws_s3_bucket.objects.bucket
}
output "api_secret_name" {
  value = aws_secretsmanager_secret.api_key.name
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
