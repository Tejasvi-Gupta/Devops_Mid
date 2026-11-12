locals {
  name = "${var.project_name}-${var.environment}"
}

resource "aws_vpc" "main" {
  count = var.create_paid_resources ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${local.name}-vpc" }
}

resource "aws_subnet" "public_a" {
  count = var.create_paid_resources ? 1 : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 0)
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public-a" }
}

resource "aws_subnet" "public_b" {
  count = var.create_paid_resources ? 1 : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 1)
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public-b" }
}

resource "aws_subnet" "private_a" {
  count = var.create_paid_resources ? 1 : 0

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, 8)
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "${local.name}-private-a" }
}

resource "aws_subnet" "private_b" {
  count = var.create_paid_resources ? 1 : 0

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, 9)
  availability_zone = "${var.aws_region}b"
  tags              = { Name = "${local.name}-private-b" }
}

resource "aws_internet_gateway" "igw" {
  count  = var.create_paid_resources ? 1 : 0
  vpc_id = aws_vpc.main[0].id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_db_subnet_group" "db" {
  count      = var.create_paid_resources ? 1 : 0
  name       = "${local.name}-db"
  subnet_ids = [aws_subnet.private_a[0].id, aws_subnet.private_b[0].id]
}

resource "aws_security_group" "db" {
  count       = var.create_paid_resources ? 1 : 0
  name        = "${local.name}-db"
  description = "PostgreSQL from API tasks only"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api[0].id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "api" {
  count       = var.create_paid_resources ? 1 : 0
  name        = "${local.name}-api"
  description = "API tasks"
  vpc_id      = aws_vpc.main[0].id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  count = var.create_paid_resources ? 1 : 0

  identifier                 = "${local.name}-pg"
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = var.db_instance_class
  allocated_storage          = 20
  max_allocated_storage      = 100
  db_name                    = "epp"
  username                   = var.db_username
  password                   = var.db_password
  db_subnet_group_name       = aws_db_subnet_group.db[0].name
  vpc_security_group_ids     = [aws_security_group.db[0].id]
  publicly_accessible        = false
  multi_az                   = false
  backup_retention_period    = 7
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${local.name}-final"
  storage_encrypted          = true
  auto_minor_version_upgrade = true
}

resource "aws_ecr_repository" "api" {
  count                = var.create_paid_resources ? 1 : 0
  name                 = "${local.name}-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.create_paid_resources ? 1 : 0
  name              = "/ecs/${local.name}-api"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  count = var.create_paid_resources ? 1 : 0
  name  = local.name
}

resource "aws_iam_role" "ecs_execution" {
  count = var.create_paid_resources ? 1 : 0
  name  = "${local.name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  count      = var.create_paid_resources ? 1 : 0
  role       = aws_iam_role.ecs_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "api" {
  count                    = var.create_paid_resources && var.container_image != "" ? 1 : 0
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution[0].arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = var.container_image
    essential = true
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "COOKIE_SECURE", value = "true" },
      { name = "COOKIE_SAMESITE", value = "none" },
      { name = "CATALOG_PATH", value = "/app/catalog/tools.json" },
    ]
    secrets = [
      {
        name      = "APP_SECRET_KEY"
        valueFrom = aws_secretsmanager_secret.app[0].arn
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api[0].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_secretsmanager_secret" "app" {
  count = var.create_paid_resources ? 1 : 0
  name  = "${local.name}/app-secret-key"
}

resource "aws_secretsmanager_secret_version" "app" {
  count         = var.create_paid_resources ? 1 : 0
  secret_id     = aws_secretsmanager_secret.app[0].id
  secret_string = var.app_secret_key
}

resource "aws_s3_bucket" "frontend" {
  count  = var.create_paid_resources ? 1 : 0
  bucket = var.frontend_bucket_name
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  count                   = var.create_paid_resources ? 1 : 0
  bucket                  = aws_s3_bucket.frontend[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  count                             = var.create_paid_resources ? 1 : 0
  name                              = "${local.name}-frontend-oac"
  description                       = "OAC for SPA bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront distribution and ECS service wiring are intentionally incomplete:
# attach ACM certificates, ALB listeners, and route tables only after domains
# and a reviewed plan exist. Keeping create_paid_resources=false prevents spend.
