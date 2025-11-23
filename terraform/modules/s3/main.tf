resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-${var.environment}-${random_string.suffix.result}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-bucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  
  versioning_configuration {
    # ⚠️ VERSIONING: Environment-dependent setting
    # - Prod: Always enabled (safe)
    # - Dev: Currently DISABLED (terraform.tfvars: s3_enable_versioning = false)
    # - Without versioning, object overwrites are permanent
    status     = local.versioning_enabled ? "Enabled" : "Suspended"
    mfa_delete = local.mfa_delete_enabled ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.encryption_type == "KMS" ? "aws:kms" : "AES256"
      kms_master_key_id = var.encryption_type == "KMS" ? local.kms_key_id : null
    }
    bucket_key_enabled = var.encryption_type == "KMS" ? true : null
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Commented out due to S3 Block Public Access conflicts
# resource "aws_s3_bucket_policy" "main" {
#   bucket = aws_s3_bucket.main.id
#   policy = jsonencode(local.bucket_policy)
# }

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count  = var.lifecycle_enabled ? 1 : 0
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "lifecycle_rule"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = local.lifecycle_config.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = local.lifecycle_config.transition_to_glacier_days
      storage_class = "GLACIER"
    }

    # ⚠️ OBJECT EXPIRATION: Automatic deletion after specified days
    # - Dev: 90 days (terraform.tfvars: s3_expiration_days = 90)
    # - Prod: Minimum 7 years (2555 days) enforced by locals.tf
    # - Objects will be PERMANENTLY DELETED after this period
    # - Consider if this is appropriate for your data retention needs
    expiration {
      days = local.lifecycle_config.expiration_days
    }

    # ⚠️ VERSION EXPIRATION: Non-current versions deleted after 30 days
    # - This affects versioned objects and cannot be recovered
    # - Consider increasing this value for better data protection
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  name   = "intelligent-tiering"

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 125
  }
}

resource "aws_s3_bucket_logging" "main" {
  count  = local.access_logging_enabled ? 1 : 0
  bucket = aws_s3_bucket.main.id

  target_bucket = aws_s3_bucket.access_logs[0].id
  target_prefix = "access-logs/"
}

resource "aws_s3_bucket" "access_logs" {
  count  = local.access_logging_enabled ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-access-logs-${random_string.suffix.result}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-access-logs"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  count  = local.access_logging_enabled ? 1 : 0
  bucket = aws_s3_bucket.access_logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
