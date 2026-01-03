# JARVIS Infrastructure Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.dns_name
}

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "https://${module.alb.dns_name}"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "s3_audio_bucket" {
  description = "S3 bucket for audio files"
  value       = module.s3.audio_bucket_name
}

output "dynamodb_sessions_table" {
  description = "DynamoDB sessions table name"
  value       = module.dynamodb.sessions_table_name
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value       = module.cloudwatch.log_group_names
}
