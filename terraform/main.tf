# ECR Module
module "ecr" {
  source = "./modules/ecr"

  project_name          = var.project_name
  environment           = var.environment
  image_tag_mutability  = var.ecr_image_tag_mutability
  lifecycle_image_count = var.ecr_lifecycle_image_count
  enable_encryption     = var.ecr_enable_encryption
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name             = var.project_name
  environment              = var.environment
  vpc_cidr                 = var.vpc_cidr
  availability_zones_count = var.availability_zones_count
  single_nat_gateway       = var.vpc_single_nat_gateway
  enable_vpc_flow_logs     = var.vpc_enable_flow_logs
  enable_s3_endpoint       = var.vpc_enable_s3_endpoint
  enable_secrets_endpoint  = var.vpc_enable_secrets_endpoint
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name          = var.project_name
  environment           = var.environment
  encryption_type       = var.s3_encryption_type
  enable_versioning     = var.s3_enable_versioning
  lifecycle_enabled     = var.s3_lifecycle_enabled
  transition_to_ia_days = var.s3_transition_to_ia_days
  expiration_days       = var.s3_expiration_days
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  project_name            = var.project_name
  environment             = var.environment
  vpc_id                  = module.vpc.vpc_id
  private_subnets         = module.vpc.private_subnets
  db_username             = var.db_username
  db_password             = var.db_password
  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_allocated_storage
  max_allocated_storage   = var.rds_max_allocated_storage
  backup_retention_period = var.rds_backup_retention_period
  multi_az                = var.rds_multi_az
  deletion_protection     = var.rds_deletion_protection
  backup_window           = var.rds_backup_window
  maintenance_window      = var.rds_maintenance_window
}

# ALB Module
module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnets    = module.vpc.public_subnets
  alb_http_port     = var.alb_http_port
  alb_https_port    = var.alb_https_port
  app_port          = var.app_port
  health_check_path = var.health_check_path
}

# Secrets Manager Module
module "secrets" {
  source = "./modules/secrets"

  project_name            = var.project_name
  environment             = var.environment
  db_name                 = module.rds.db_name
  db_username             = var.db_username
  db_password             = var.db_password
  db_host                 = module.rds.db_endpoint
  db_port                 = local.db_port
  s3_bucket_name          = module.s3.bucket_name
  recovery_window_in_days = var.secrets_recovery_window_days
  enable_rotation         = var.secrets_enable_rotation
  rotation_days           = var.secrets_rotation_days
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnets    = module.vpc.private_subnets
  target_group_arn   = module.alb.target_group_arn
  db_host            = module.rds.db_endpoint
  db_name            = module.rds.db_name
  s3_bucket          = module.s3.bucket_name
  s3_bucket_arn      = module.s3.bucket_arn
  secret_arn         = module.secrets.secret_arn
  secret_name        = local.secret_name
  allowed_origins    = var.allowed_origins
  app_port           = var.app_port
  backend_port       = local.backend_port
  cpu                = var.ecs_cpu
  memory             = var.ecs_memory
  desired_count      = var.ecs_desired_count
  log_retention_days = var.ecs_log_retention_days
  ecr_repository_url = "${module.ecr.repository_url}:latest"
  image_tag          = var.docker_image_tag
  aws_region         = var.aws_region
}
