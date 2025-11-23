locals {
  # Environment-specific configurations
  is_production = var.environment == "prod"
  
  # Security configurations based on environment
  versioning_enabled = var.environment == "prod" ? true : var.enable_versioning
  mfa_delete_enabled = var.environment == "prod" ? true : var.mfa_delete
  access_logging_enabled = var.environment == "prod" ? true : var.enable_access_logging
  
  # Lifecycle configurations based on environment
  lifecycle_config = var.lifecycle_enabled ? {
    transition_to_ia_days = var.transition_to_ia_days
    transition_to_glacier_days = var.transition_to_glacier_days
    expiration_days = var.environment == "prod" ? max(var.expiration_days, 2555) : var.expiration_days # 7 years min for prod
  } : null
  
  # Encryption configuration
  kms_key_id = var.kms_key_id != null ? var.kms_key_id : "alias/aws/s3"
  
  # Bucket policy for secure access
  bucket_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureConnections"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-${random_string.suffix.result}",
          "arn:aws:s3:::${var.project_name}-${var.environment}-${random_string.suffix.result}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "RestrictToEnvironment"
        Effect = "Allow"
        Principal = "*"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-${var.environment}-${random_string.suffix.result}/*"
        Condition = {
          StringEquals = {
            "aws:PrincipalTag/Environment" = var.environment
          }
        }
      }
    ]
  }
}
