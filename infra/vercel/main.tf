terraform {
  required_version = ">= 1.5.0"

  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 1.0"
    }
  }
}

provider "vercel" {
  token = var.vercel_token
}

resource "vercel_project" "main" {
  name                  = "${var.environment}-${var.project_name}"
  framework             = var.framework
  git_repository        = var.git_repository
  git_branch            = var.environment == "production" ? "main" : var.environment
  build_command         = var.build_command
  output_directory      = var.output_directory
  dev_command           = var.dev_command
  install_command       = var.install_command
  node_version          = var.node_version
  serverless_function_region = var.serverless_function_region
}

resource "vercel_project_domain" "custom" {
  count = var.custom_domain != "" ? 1 : 0

  project_id = vercel_project.main.id
  domain     = var.custom_domain
}

resource "vercel_project_environment_variable" "env_vars" {
  for_each = var.environment_variables

  project_id = vercel_project.main.id
  key        = each.key
  value      = each.value
  target     = var.environment == "production" ? ["production"] : ["preview", "development"]
  type       = each.value.type
}

output "project_id" {
  description = "Vercel project ID"
  value       = vercel_project.main.id
}

output "project_url" {
  description = "Vercel project deployment URL"
  value       = "https://${vercel_project.main.name}.vercel.app"
}

output "custom_domain" {
  description = "Custom domain if configured"
  value       = var.custom_domain != "" ? var.custom_domain : null
}