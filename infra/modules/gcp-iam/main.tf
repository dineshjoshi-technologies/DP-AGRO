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

variable "ci_cd_sa_name" {
  description = "Name for the CI/CD service account"
  type        = string
  default     = "ci-cd"
}

variable "workload_sa_name" {
  description = "Name for the workload service account"
  type        = string
  default     = "workload"
}

variable "allowed_github_org" {
  description = "GitHub organization for workload identity"
  type        = string
  default     = ""
}

variable "allowed_github_repos" {
  description = "List of GitHub repositories allowed for workload identity"
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "google_service_account" "ci_cd" {
  account_id   = "${var.environment}-${var.ci_cd_sa_name}"
  display_name = "${var.environment} CI/CD Service Account"
  description  = "Service account for GitHub Actions CI/CD pipelines"
  labels = merge(var.labels, {
    environment = var.environment
    role        = "ci-cd"
  })
}

resource "google_service_account" "workload" {
  account_id   = "${var.environment}-${var.workload_sa_name}"
  display_name = "${var.environment} Workload Service Account"
  description  = "Service account for application workloads"
  labels = merge(var.labels, {
    environment = var.environment
    role        = "workload"
  })
}

resource "google_project_iam_member" "ci_cd_roles" {
  for_each = toset([
    "roles/editor",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/storage.objectAdmin",
    "roles/artifactregistry.writer"
  ])

  project = var.environment
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci_cd.email}"
}

resource "google_project_iam_member" "workload_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudsql.client"
  ])

  project = var.environment
  role    = each.value
  member  = "serviceAccount:${google_service_account.workload.email}"
}

resource "google_service_account_iam_member" "github_oidc" {
  count = var.allowed_github_org != "" ? 1 : 0

  service_account_id = google_service_account.ci_cd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.environment}/locations/global/workloadIdentityPools/github/attribute.repository/${var.allowed_github_org}/*"
}

output "ci_cd_sa_email" {
  description = "Email of the CI/CD service account"
  value       = google_service_account.ci_cd.email
}

output "workload_sa_email" {
  description = "Email of the workload service account"
  value       = google_service_account.workload.email
}

output "ci_cd_sa_name" {
  description = "Name of the CI/CD service account"
  value       = google_service_account.ci_cd.name
}

output "workload_sa_name" {
  description = "Name of the workload service account"
  value       = google_service_account.workload.name
}