locals {
  # Environment-specific configurations
  is_production = var.environment == "prod"
  
  # Security configurations based on environment
  deletion_protection_enabled = var.environment == "prod" ? true : var.deletion_protection
  skip_final_snapshot_setting = var.environment == "prod" ? false : var.skip_final_snapshot
  multi_az_enabled           = var.environment == "prod" ? true : var.multi_az
  performance_insights       = var.environment == "prod" ? true : var.performance_insights_enabled
  
  # Backup retention based on environment
  backup_retention = var.environment == "prod" ? max(var.backup_retention_period, 30) : var.backup_retention_period
  
  # Storage encryption - use null for default AWS managed key
  storage_encrypted = true
  kms_key_id       = var.kms_key_id  # null by default, uses AWS managed key
}
