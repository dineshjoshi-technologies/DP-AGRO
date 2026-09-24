terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

module "vpc" {
  source = "../../modules/gcp-vpc"

  environment           = var.environment
  network_name          = var.network_name
  subnets               = var.subnets
  secondary_ranges      = var.secondary_ranges
  tags                  = var.common_tags
}

module "secrets" {
  source = "../../modules/gcp-secrets"

  environment = var.environment
  secret_names = var.secret_names
  tags        = var.common_tags
}

module "logging" {
  source = "../../modules/gcp-logging"

  environment     = var.environment
  log_bucket_name = var.log_bucket_name
  retention_days  = var.log_retention_days
  tags            = var.common_tags
}

module "monitoring" {
  source = "../../modules/gcp-monitoring"

  environment    = var.environment
  dashboard_config = var.dashboard_config
  alert_policies = var.alert_policies
  notification_channels = var.notification_channels
  tags           = var.common_tags
}

module "iam" {
  source = "../../modules/gcp-iam"

  environment         = var.environment
  ci_cd_sa_name       = var.ci_cd_sa_name
  workload_sa_name    = var.workload_sa_name
  allowed_github_org  = var.allowed_github_org
  allowed_github_repos = var.allowed_github_repos
  tags                = var.common_tags
}

output "network_name" {
  description = "Name of the VPC network"
  value       = module.vpc.network_name
}

output "subnet_names" {
  description = "Names of the subnets"
  value       = module.vpc.subnet_names
}

output "secret_versions" {
  description = "Map of secret names to their versions"
  value       = module.secrets.secret_versions
}

output "log_bucket_name" {
  description = "Name of the log bucket"
  value       = module.logging.log_bucket_name
}

output "ci_cd_sa_email" {
  description = "Email of the CI/CD service account"
  value       = module.iam.ci_cd_sa_email
}

output "workload_sa_email" {
  description = "Email of the workload service account"
  value       = module.iam.workload_sa_email
}