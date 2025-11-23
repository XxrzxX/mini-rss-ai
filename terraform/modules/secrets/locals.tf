locals {
  # Generate secret name matching backend expectations: chatbot-secrets-{env}
  current_date = formatdate("YYYY-MM-DD", timestamp())
  random_suffix = random_integer.secret_suffix.result
  secret_name = "chatbot-secrets-${var.environment}"
  
  # Environment-specific configurations
  is_production = var.environment == "prod"
  
  # Security configurations based on environment
  recovery_window = var.environment == "prod" ? max(var.recovery_window_in_days, 30) : var.recovery_window_in_days
  rotation_enabled = var.environment == "prod" ? true : var.enable_rotation
  
  # KMS key configuration
  kms_key_id = var.kms_key_id != null ? var.kms_key_id : "alias/aws/secretsmanager"
  
  # Secret structure with configurable keys (matching backend expectations)
  secret_data = {
    "PROJ-DB-NAME"        = var.db_name
    "PROJ-DB-USER"        = var.db_username
    "PROJ-DB-PASSWORD"    = var.db_password
    "PROJ-DB-HOST"        = var.db_host
    "PROJ-DB-PORT"        = tostring(var.db_port)
    "PROJ-S3-BUCKET-NAME" = var.s3_bucket_name
    "ENVIRONMENT"         = var.environment
    "CREATED_DATE"        = local.current_date
  }
  
  # Resource policy for secure access
  resource_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RestrictToEnvironment"
        Effect = "Allow"
        Principal = "*"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Environment" = var.environment
          }
        }
      },
      {
        Sid    = "DenyUnencryptedAccess"
        Effect = "Deny"
        Principal = "*"
        Action = "secretsmanager:*"
        Resource = "*"
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  }
}
