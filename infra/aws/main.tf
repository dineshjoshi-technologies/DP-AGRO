terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "../../modules/vpc"

  environment           = var.environment
  cidr_block            = var.vpc_cidr_block
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  availability_zones    = var.availability_zones
  tags                  = var.common_tags
}

module "secrets" {
  source = "../../modules/secrets"

  environment = var.environment
  secret_names = var.secret_names
  kms_key_id  = var.kms_key_id
  tags        = var.common_tags
}

module "logging" {
  source = "../../modules/logging"

  environment     = var.environment
  log_group_names = var.log_group_names
  retention_days  = var.log_retention_days
  kms_key_id      = var.kms_key_id
  tags            = var.common_tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  environment    = var.environment
  dashboard_config = var.dashboard_config
  alarm_config   = var.alarm_config
  sns_topic_arn  = var.sns_topic_arn
  tags           = var.common_tags
}

module "iam" {
  source = "../../modules/iam"

  environment         = var.environment
  ci_cd_role_name     = var.ci_cd_role_name
  workload_role_name  = var.workload_role_name
  allowed_github_org  = var.allowed_github_org
  allowed_github_repos = var.allowed_github_repos
  tags                = var.common_tags
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "secret_arns" {
  description = "Map of secret names to their ARNs"
  value       = module.secrets.secret_arns
}

output "log_group_arns" {
  description = "Map of log group names to their ARNs"
  value       = module.logging.log_group_arns
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = module.monitoring.dashboard_arn
}

output "ci_cd_role_arn" {
  description = "ARN of the CI/CD IAM role"
  value       = module.iam.ci_cd_role_arn
}

output "workload_role_arn" {
  description = "ARN of the workload IAM role"
  value       = module.iam.workload_role_arn
}