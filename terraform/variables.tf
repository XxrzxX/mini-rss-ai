variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "rss-chat"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "beta"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "rss_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Port Configuration Variables
variable "alb_http_port" {
  description = "HTTP port for ALB"
  type        = number
  default     = 80
}

variable "alb_https_port" {
  description = "HTTPS port for ALB"
  type        = number
  default     = 443
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8501
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/"
}

# ECR Security Variables
variable "ecr_image_tag_mutability" {
  description = "ECR image tag mutability (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "IMMUTABLE"
}

variable "ecr_lifecycle_image_count" {
  description = "Number of ECR images to keep"
  type        = number
  default     = 5
}

variable "ecr_enable_encryption" {
  description = "Enable ECR encryption at rest"
  type        = bool
  default     = true
}

# ECS Security Variables
variable "ecs_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 256
}

variable "ecs_memory" {
  description = "ECS task memory"
  type        = number
  default     = 512
}

variable "ecs_desired_count" {
  description = "ECS desired task count"
  type        = number
  default     = 1
}

variable "ecs_log_retention_days" {
  description = "ECS CloudWatch log retention days"
  type        = number
  default     = 30
}

variable "docker_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "ecr_image_uri" {
  description = "Full ECR image URI (overrides auto-generated URI)"
  type        = string
  default     = null
}

# RDS Security Variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS initial storage allocation"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "RDS maximum storage allocation"
  type        = number
  default     = 100
}

variable "rds_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Enable RDS Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "rds_deletion_protection" {
  description = "Enable RDS deletion protection"
  type        = bool
  default     = true
}

variable "rds_backup_window" {
  description = "RDS backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "rds_maintenance_window" {
  description = "RDS maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

# S3 Security Variables
variable "s3_encryption_type" {
  description = "S3 encryption type (AES256 or KMS)"
  type        = string
  default     = "KMS"
}

variable "s3_enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "s3_lifecycle_enabled" {
  description = "Enable S3 lifecycle management"
  type        = bool
  default     = true
}

variable "s3_transition_to_ia_days" {
  description = "Days to transition to IA storage class"
  type        = number
  default     = 30

  validation {
    condition     = var.s3_transition_to_ia_days >= 30
    error_message = "S3 transition to IA must be at least 30 days."
  }
}

variable "s3_transition_to_glacier_days" {
  description = "Days to transition to Glacier storage class"
  type        = number
  default     = 90

  validation {
    condition     = var.s3_transition_to_glacier_days >= 60
    error_message = "Glacier transition must be at least 60 days."
  }
}

variable "s3_expiration_days" {
  description = "Days to expire S3 objects"
  type        = number
  default     = 365

  validation {
    condition     = var.s3_expiration_days > 30
    error_message = "S3 expiration must be greater than transition days (30)."
  }
}

# Secrets Manager Security Variables
variable "secrets_recovery_window_days" {
  description = "Secrets Manager recovery window in days"
  type        = number
  default     = 30
}

variable "secrets_enable_rotation" {
  description = "Enable automatic secrets rotation"
  type        = bool
  default     = false
}

variable "secrets_rotation_days" {
  description = "Days between automatic secret rotations"
  type        = number
  default     = 30
}

# VPC Security Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones_count" {
  description = "Number of availability zones"
  type        = number
  default     = 2
}

variable "vpc_single_nat_gateway" {
  description = "Use single NAT Gateway for all private subnets"
  type        = bool
  default     = true
}

variable "vpc_enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = false
}

variable "vpc_enable_s3_endpoint" {
  description = "Enable S3 VPC Endpoint"
  type        = bool
  default     = false
}

variable "vpc_enable_secrets_endpoint" {
  description = "Enable Secrets Manager VPC Endpoint"
  type        = bool
  default     = false
}
variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "https://yourdomain.com"
}
