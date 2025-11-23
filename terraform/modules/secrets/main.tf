resource "random_integer" "secret_suffix" {
  min = 100
  max = 999
}

resource "aws_secretsmanager_secret" "app" {
  name                    = local.secret_name
  description             = "Application secrets for ${var.project_name} ${var.environment} environment"
  kms_key_id             = local.kms_key_id
  
  # ⚠️ RECOVERY WINDOW: Time before secret is permanently deleted
  # - Current dev setting: Only 7 days (terraform.tfvars: secrets_recovery_window_days = 7)
  # - After this period, deleted secrets cannot be recovered
  # - Minimum is 7 days, maximum is 30 days
  # - Consider using 30 days for production environments
  recovery_window_in_days = local.recovery_window
  
  policy = jsonencode(local.resource_policy)

  tags = {
    Name        = local.secret_name
    Environment = var.environment
    CreatedDate = local.current_date
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = jsonencode(local.secret_data)

  lifecycle {
    ignore_changes = [
      secret_string
    ]
  }
}

resource "aws_secretsmanager_secret_rotation" "app" {
  count           = local.rotation_enabled ? 1 : 0
  secret_id       = aws_secretsmanager_secret.app.id
  rotation_lambda_arn = aws_lambda_function.rotation[0].arn

  rotation_rules {
    automatically_after_days = var.rotation_days
  }

  depends_on = [aws_lambda_permission.rotation]
}

# Lambda function for rotation (simplified - would need full implementation)
resource "aws_lambda_function" "rotation" {
  count         = local.rotation_enabled ? 1 : 0
  filename      = "rotation.zip"
  function_name = "${var.project_name}-${var.environment}-secret-rotation"
  role          = aws_iam_role.rotation[0].arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role" "rotation" {
  count = local.rotation_enabled ? 1 : 0
  name  = "${var.project_name}-${var.environment}-rotation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "rotation" {
  count         = local.rotation_enabled ? 1 : 0
  statement_id  = "AllowSecretsManagerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rotation[0].function_name
  principal     = "secretsmanager.amazonaws.com"
}
