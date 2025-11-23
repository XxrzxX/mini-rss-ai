output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecr.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name"
  value       = module.ecr.repository_name
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID"
  value       = module.alb.zone_id
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_endpoint
}

output "s3_bucket" {
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_frontend_service_name" {
  description = "ECS frontend service name"
  value       = module.ecs.frontend_service_name
}

output "ecs_backend_service_name" {
  description = "ECS backend service name"
  value       = module.ecs.backend_service_name
}

output "frontend_log_group" {
  description = "Frontend CloudWatch log group"
  value       = module.ecs.frontend_log_group
}

output "backend_log_group" {
  description = "Backend CloudWatch log group"
  value       = module.ecs.backend_log_group
}

# GitHub Secrets Reference
output "github_secrets_needed" {
  description = "GitHub secrets needed for CI/CD"
  value = {
    AWS_REGION           = var.aws_region
    ECR_REPOSITORY       = module.ecr.repository_name
    ECS_CLUSTER          = module.ecs.cluster_name
    ECS_BACKEND_SERVICE  = module.ecs.backend_service_name
    ECS_FRONTEND_SERVICE = module.ecs.frontend_service_name
    S3_BUCKET            = module.s3.bucket_name
  }
}
