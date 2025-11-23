locals {
  # Common configuration
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    CreatedDate = formatdate("YYYY-MM-DD", timestamp())
  }

  # Port configurations
  backend_port = 8000
  db_port      = 5432

  # Environment-specific settings
  is_production = var.environment == "prod"

  # Resource naming
  name_prefix = "${var.project_name}-${var.environment}"
  secret_name = "chatbot-secrets-${var.environment}"

  # ECR Image URI logic
  # Use provided URI or construct from ECR module output
  ecr_image_uri = var.ecr_image_uri != null ? var.ecr_image_uri : "${module.ecr.repository_url}:${var.docker_image_tag}"
}
