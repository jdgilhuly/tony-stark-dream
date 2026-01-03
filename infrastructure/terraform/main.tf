# JARVIS Infrastructure - Main Configuration
# AWS ECS/EKS deployment with supporting services

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for remote state storage
  # backend "s3" {
  #   bucket         = "jarvis-terraform-state"
  #   key            = "infrastructure/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "jarvis-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "JARVIS"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  name_prefix = "jarvis-${var.environment}"

  azs = slice(data.aws_availability_zones.available.names, 0, 3)

  common_tags = {
    Project     = "JARVIS"
    Environment = var.environment
  }
}

# VPC
module "vpc" {
  source = "./modules/vpc"

  name_prefix         = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = local.azs

  enable_nat_gateway = var.environment == "production"
  single_nat_gateway = var.environment != "production"

  tags = local.common_tags
}

# Security Groups
module "security_groups" {
  source = "./modules/security-groups"

  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  vpc_cidr    = var.vpc_cidr

  tags = local.common_tags
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  name_prefix          = local.name_prefix
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  security_group_id    = module.security_groups.rds_security_group_id

  instance_class       = var.rds_instance_class
  allocated_storage    = var.rds_allocated_storage
  database_name        = "jarvis"
  master_username      = var.db_master_username

  multi_az             = var.environment == "production"
  skip_final_snapshot  = var.environment != "production"

  tags = local.common_tags
}

# ElastiCache Redis
module "elasticache" {
  source = "./modules/elasticache"

  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.security_groups.redis_security_group_id

  node_type          = var.redis_node_type
  num_cache_nodes    = var.environment == "production" ? 2 : 1

  tags = local.common_tags
}

# DynamoDB Tables
module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix = local.name_prefix

  billing_mode = var.environment == "production" ? "PROVISIONED" : "PAY_PER_REQUEST"

  tags = local.common_tags
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix
  account_id  = data.aws_caller_identity.current.account_id

  tags = local.common_tags
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"

  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids

  security_groups = {
    api_gateway          = module.security_groups.api_gateway_security_group_id
    conversation_service = module.security_groups.conversation_service_security_group_id
  }

  alb_security_group_id = module.security_groups.alb_security_group_id

  # Service configurations
  api_gateway_config = {
    cpu    = var.environment == "production" ? 512 : 256
    memory = var.environment == "production" ? 1024 : 512
    count  = var.environment == "production" ? 2 : 1
  }

  conversation_service_config = {
    cpu    = var.environment == "production" ? 1024 : 512
    memory = var.environment == "production" ? 2048 : 1024
    count  = var.environment == "production" ? 2 : 1
  }

  # Environment variables
  environment_variables = {
    DATABASE_URL     = module.rds.connection_string
    REDIS_URL        = module.elasticache.connection_string
    AWS_REGION       = var.aws_region
    ENVIRONMENT      = var.environment
  }

  # Secrets
  secrets = {
    JWT_SECRET = var.jwt_secret
  }

  tags = local.common_tags
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"

  name_prefix       = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.security_groups.alb_security_group_id

  certificate_arn = var.certificate_arn

  target_groups = {
    api_gateway = {
      port        = 3000
      health_path = "/health"
    }
  }

  tags = local.common_tags
}

# CloudWatch Log Groups
module "cloudwatch" {
  source = "./modules/cloudwatch"

  name_prefix       = local.name_prefix
  retention_in_days = var.environment == "production" ? 30 : 7

  services = [
    "api-gateway",
    "conversation-service",
    "voice-processing",
    "briefing-service"
  ]

  tags = local.common_tags
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  name_prefix = local.name_prefix

  s3_bucket_arns = [
    module.s3.audio_bucket_arn,
    module.s3.logs_bucket_arn
  ]

  dynamodb_table_arns = module.dynamodb.table_arns

  bedrock_models = [
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-haiku-20240307-v1:0"
  ]

  tags = local.common_tags
}
