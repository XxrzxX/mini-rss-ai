resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnets

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.db_port
    to_port     = var.db_port
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "PostgreSQL access from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-db"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = local.storage_encrypted
  kms_key_id           = local.kms_key_id

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  # ⚠️ BACKUP RETENTION: Current setting may cause data loss on destroy
  # - Dev environment: Only 1 day retention (from terraform.tfvars)
  # - Prod environment: Minimum 30 days (from locals.tf)
  # - Consider increasing dev retention for safety
  backup_retention_period = local.backup_retention
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window

  multi_az               = local.multi_az_enabled
  
  # ⚠️ DELETION PROTECTION: Environment-dependent setting
  # - Prod: Always enabled (safe)
  # - Dev: Currently DISABLED (terraform.tfvars: rds_deletion_protection = false)
  # - This allows accidental deletion in dev environment
  deletion_protection    = local.deletion_protection_enabled
  
  # ⚠️ FINAL SNAPSHOT: Critical for data recovery
  # - Prod: Always creates final snapshot (safe)
  # - Dev: May skip final snapshot if skip_final_snapshot = true
  # - Current dev config doesn't explicitly set this, using default behavior
  skip_final_snapshot    = local.skip_final_snapshot_setting
  final_snapshot_identifier = local.skip_final_snapshot_setting ? null : "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  performance_insights_enabled = local.performance_insights
  monitoring_interval         = local.performance_insights ? 60 : 0

  auto_minor_version_upgrade = false
  apply_immediately         = false

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Environment = var.environment
  }

  lifecycle {
    # ✅ PROTECTION: prevent_destroy protects against accidental terraform destroy
    # However, this can be overridden with -target flag or by removing this block
    prevent_destroy = true
    ignore_changes = [
      final_snapshot_identifier
    ]
  }
}
