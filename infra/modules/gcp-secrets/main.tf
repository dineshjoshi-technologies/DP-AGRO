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
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "secret_names" {
  description = "Map of secret names to their descriptions"
  type        = map(string)
  default     = {}
}

variable "replication_policy" {
  description = "Replication policy for secrets"
  type        = string
  default     = "AUTOMATIC"
}

variable "labels" {
  description = "Labels to apply to all secrets"
  type        = map(string)
  default     = {}
}

resource "google_secret_manager_secret" "secrets" {
  for_each = var.secret_names

  secret_id = "${var.environment}-${each.key}"
  replication {
    automatic = var.replication_policy == "AUTOMATIC"
    user_managed = var.replication_policy == "USER_MANAGED" ? {
      replicas = [{ location = "us-central1" }]
    } : null
  }
  labels = merge(var.labels, {
    environment = var.environment
    managed-by  = "terraform"
  })
}

resource "google_secret_manager_secret_version" "secrets" {
  for_each = var.secret_names

  secret = google_secret_manager_secret.secrets[each.key].id
  secret_data = base64encode(jsonencode({
    placeholder = "replace-with-actual-value"
    created_at  = timestamp()
  }))
}

output "secret_ids" {
  description = "Map of secret names to their IDs"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.id }
}

output "secret_names" {
  description = "Map of secret names to their full names"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}

output "secret_versions" {
  description = "Map of secret names to their versions"
  value       = { for k, v in google_secret_manager_secret_version.secrets : k => v.id }
}