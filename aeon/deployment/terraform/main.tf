terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# NOTE: this is generic, illustrative Terraform scaffolding. Before applying:
# - Set real values for var.acm_certificate_arn (must be issued/validated first)
# - Review CIDR ranges against your actual account/VPC layout
# - Set real DB credentials via a secrets manager, not plaintext variables
# ---------------------------------------------------------------------------

variable "aws_region" { default = "us-east-1" }
variable "environment" { default = "production" }
variable "db_password" {
  sensitive = true
  description = "Set via TF_VAR_db_password env var or a secrets manager — do not hardcode"
}
variable "acm_certificate_arn" {
  description = "ARN of a validated ACM certificate for the ALB HTTPS listener"
}

# --- VPC ---
resource "aws_vpc" "aeon_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "aeon-${var.environment}-vpc" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.aeon_vpc.id
  cidr_block        = cidrsubnet(aws_vpc.aeon_vpc.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "aeon-private-${count.index}" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.aeon_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.aeon_vpc.cidr_block, 8, count.index + 10)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "aeon-public-${count.index}" }
}

data "aws_availability_zones" "available" { state = "available" }

# --- RDS Aurora Postgres ---
resource "aws_db_subnet_group" "aeon" {
  name       = "aeon-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_rds_cluster" "aeon_postgres" {
  cluster_identifier      = "aeon-${var.environment}"
  engine                  = "aurora-postgresql"
  engine_version          = "15.4"
  database_name           = "aeon"
  master_username         = "aeon_admin"
  master_password         = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.aeon.name
  vpc_security_group_ids  = [aws_security_group.db_sg.id]
  skip_final_snapshot     = false
  final_snapshot_identifier = "aeon-${var.environment}-final-snapshot"
}

resource "aws_rds_cluster_instance" "aeon_postgres_instance" {
  count              = 1
  identifier         = "aeon-${var.environment}-instance-${count.index}"
  cluster_identifier = aws_rds_cluster.aeon_postgres.id
  instance_class     = "db.r6g.large"
  engine             = aws_rds_cluster.aeon_postgres.engine
}

# --- ElastiCache Redis ---
resource "aws_elasticache_subnet_group" "aeon" {
  name       = "aeon-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "aeon_redis" {
  cluster_id           = "aeon-${var.environment}"
  engine               = "redis"
  node_type            = "cache.t3.medium"
  num_cache_nodes      = 1
  subnet_group_name    = aws_elasticache_subnet_group.aeon.name
  security_group_ids   = [aws_security_group.redis_sg.id]
}

# --- S3 for ML model artifacts ---
resource "aws_s3_bucket" "ml_models" {
  bucket = "aeon-${var.environment}-ml-models"
}

resource "aws_s3_bucket_versioning" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id
  versioning_configuration { status = "Enabled" }
}

# --- ECS Fargate ---
resource "aws_ecs_cluster" "aeon" {
  name = "aeon-${var.environment}"
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "aeon-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  container_definitions = jsonencode([{
    name      = "backend"
    image     = "REPLACE_WITH_ECR_IMAGE_URI:latest"
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "DATABASE_URL", value = "postgresql+psycopg2://aeon_admin:${var.db_password}@${aws_rds_cluster.aeon_postgres.endpoint}:5432/aeon" },
      { name = "CELERY_BROKER_URL", value = "redis://${aws_elasticache_cluster.aeon_redis.cache_nodes[0].address}:6379/0" },
    ]
  }])
}

resource "aws_ecs_task_definition" "celery_worker" {
  family                   = "aeon-celery-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  container_definitions = jsonencode([{
    name    = "celery-worker"
    image   = "REPLACE_WITH_ECR_IMAGE_URI:latest"
    command = ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info"]
    environment = [
      { name = "DATABASE_URL", value = "postgresql+psycopg2://aeon_admin:${var.db_password}@${aws_rds_cluster.aeon_postgres.endpoint}:5432/aeon" },
      { name = "CELERY_BROKER_URL", value = "redis://${aws_elasticache_cluster.aeon_redis.cache_nodes[0].address}:6379/0" },
    ]
  }])
}

# --- ALB ---
resource "aws_lb" "aeon" {
  name               = "aeon-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb_sg.id]
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.aeon.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.acm_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "aeon-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.aeon_vpc.id
  target_type = "ip"
  health_check { path = "/health" }
}

# --- Security groups (only 443 + restricted 5432 as required) ---
resource "aws_security_group" "alb_sg" {
  name   = "aeon-alb-sg"
  vpc_id = aws_vpc.aeon_vpc.id
  ingress { from_port = 443, to_port = 443, protocol = "tcp", cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0, to_port = 0, protocol = "-1", cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "db_sg" {
  name   = "aeon-db-sg"
  vpc_id = aws_vpc.aeon_vpc.id
  ingress { from_port = 5432, to_port = 5432, protocol = "tcp", cidr_blocks = [aws_vpc.aeon_vpc.cidr_block] }
}

resource "aws_security_group" "redis_sg" {
  name   = "aeon-redis-sg"
  vpc_id = aws_vpc.aeon_vpc.id
  ingress { from_port = 6379, to_port = 6379, protocol = "tcp", cidr_blocks = [aws_vpc.aeon_vpc.cidr_block] }
}

output "alb_dns_name" { value = aws_lb.aeon.dns_name }
output "rds_endpoint" { value = aws_rds_cluster.aeon_postgres.endpoint }
output "redis_endpoint" { value = aws_elasticache_cluster.aeon_redis.cache_nodes[0].address }
