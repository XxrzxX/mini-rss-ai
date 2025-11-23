# Backend Task Definition (Internal Only)
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-${var.environment}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = var.ecr_repository_url
      
      portMappings = [
        {
          containerPort = var.backend_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "REGION_NAME"
          value = var.aws_region
        },
        {
          name  = "SECRET_NAME"
          value = var.secret_name
        },
        {
          name  = "HOST"
          value = "0.0.0.0"
        },
        {
          name  = "PORT"
          value = tostring(var.backend_port)
        },
        {
          name  = "BEDROCK_MODEL_ID"
          value = "amazon.nova-lite-v1:0"
        },
        {
          name  = "DB_NAME_KEY"
          value = "PROJ-DB-NAME"
        },
        {
          name  = "DB_USER_KEY"
          value = "PROJ-DB-USER"
        },
        {
          name  = "DB_PASSWORD_KEY"
          value = "PROJ-DB-PASSWORD"
        },
        {
          name  = "DB_HOST_KEY"
          value = "PROJ-DB-HOST"
        },
        {
          name  = "DB_PORT_KEY"
          value = "PROJ-DB-PORT"
        },
        {
          name  = "S3_BUCKET_KEY"
          value = "PROJ-S3-BUCKET-NAME"
        }
      ]

      command = ["python", "backend/backend.py"]

      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:${var.backend_port}/health || exit 1"]
        interval = 30
        timeout = 5
        retries = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}-${var.environment}-backend"
  retention_in_days = var.log_retention_days
}

# Backend Service (Internal Only - No Load Balancer)
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-${var.environment}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnets
    security_groups = [aws_security_group.ecs.id]
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }
}

# Service Discovery for Backend
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.project_name}-${var.environment}.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "backend" {
  name = "backend"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}
