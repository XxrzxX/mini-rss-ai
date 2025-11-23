variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnets" {
  description = "Public subnet IDs"
  type        = list(string)
}

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
