variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

# S3 Security Variables
variable "enable_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "S3 encryption type (AES256 or KMS)"
  type        = string
  default     = "KMS"
}

variable "kms_key_id" {
  description = "KMS key ID for S3 encryption"
  type        = string
  default     = null
}

variable "lifecycle_enabled" {
  description = "Enable lifecycle management"
  type        = bool
  default     = true
}

variable "transition_to_ia_days" {
  description = "Days to transition to IA storage class"
  type        = number
  default     = 30
}

variable "transition_to_glacier_days" {
  description = "Days to transition to Glacier"
  type        = number
  default     = 90
}

variable "expiration_days" {
  description = "Days to expire objects"
  type        = number
  default     = 365
}

variable "enable_access_logging" {
  description = "Enable S3 access logging"
  type        = bool
  default     = false
}

variable "mfa_delete" {
  description = "Enable MFA delete"
  type        = bool
  default     = false
}
