locals {
  # Environment-specific configurations
  is_production = var.environment == "prod"
  
  # Security configurations based on environment
  flow_logs_enabled = var.environment == "prod" ? true : var.enable_vpc_flow_logs
  multi_nat_gateway = var.environment == "prod" ? false : var.single_nat_gateway
  s3_endpoint_enabled = var.environment == "prod" ? true : var.enable_s3_endpoint
  secrets_endpoint_enabled = var.environment == "prod" ? true : var.enable_secrets_endpoint
  
  # Calculate subnet CIDRs dynamically
  public_subnet_cidrs = [
    for i in range(var.availability_zones_count) : 
    cidrsubnet(var.vpc_cidr, 8, i + 1)
  ]
  
  private_subnet_cidrs = [
    for i in range(var.availability_zones_count) : 
    cidrsubnet(var.vpc_cidr, 8, i + 10)
  ]
  
  # NAT Gateway configuration
  nat_gateway_count = var.enable_nat_gateway ? (local.multi_nat_gateway ? 1 : var.availability_zones_count) : 0
  
  # IAM Policy for VPC Flow Logs
  flow_log_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  }
  
  # Assume Role Policy for VPC Flow Logs
  flow_log_assume_role_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  }
}
