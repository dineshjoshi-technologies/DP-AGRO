variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "VPC network name"
  type        = string
  default     = "dj-tech-network"
}

variable "subnets" {
  description = "Map of subnet names to configurations"
  type        = map(object({
    ip_cidr_range      = string
    region             = string
    private_ip_google_access = bool
    secondary_ranges   = list(object({
      range_name    = string
      ip_cidr_range = string
    }))
  }))
  default = {
    "public-us-central1-a" = {
      ip_cidr_range              = "10.0.1.0/24"
      region                     = "us-central1"
      private_ip_google_access   = false
      secondary_ranges           = []
    }
    "private-us-central1-a" = {
      ip_cidr_range              = "10.0.11.0/24"
      region                     = "us-central1"
      private_ip_google_access   = true
      secondary_ranges           = []
    }
  }
}

variable "secondary_ranges" {
  description = "Secondary IP ranges for pods/services"
  type        = map(list(object({
    range_name    = string
    ip_cidr_range = string
  })))
  default = {}
}

variable "secret_names" {
  description = "Map of secret names to their descriptions"
  type        = map(string)
  default     = {
    "database-url"      = "Database connection string"
    "redis-url"         = "Redis connection string"
    "api-keys"          = "External API keys"
    "jwt-secret"        = "JWT signing secret"
    "encryption-key"    = "Data encryption key"
  }
}

variable "log_bucket_name" {
  description = "Cloud Storage bucket for logs"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "dashboard_config" {
  description = "Dashboard configuration JSON"
  type        = string
  default     = "{}"
}

variable "alert_policies" {
  description = "Map of alert policy names to configurations"
  type        = map(any)
  default     = {}
}

variable "notification_channels" {
  description = "List of notification channel IDs"
  type        = list(string)
  default     = []
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

variable "common_tags" {
  description = "Common labels applied to all resources"
  type        = map(string)
  default     = {
    project     = "dj-tech"
    managed-by  = "terraform"
    environment = "staging"
  }
}