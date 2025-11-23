variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database username"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_host" {
  description = "Database host"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name"
  type        = string
}

# Secrets Manager Security Variables
variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "kms_key_id" {
  description = "KMS key ID for secrets encryption"
  type        = string
  default     = null
}

variable "recovery_window_in_days" {
  description = "Recovery window for deleted secrets"
  type        = number
  default     = 30
}

variable "enable_rotation" {
  description = "Enable automatic rotation"
  type        = bool
  default     = false
}

variable "rotation_days" {
  description = "Days between automatic rotations"
  type        = number
  default     = 30
}

