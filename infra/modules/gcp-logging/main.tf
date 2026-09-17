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

variable "log_bucket_name" {
  description = "Cloud Storage bucket for logs"
  type        = string
}

variable "retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "google_storage_bucket" "logs" {
  count = var.log_bucket_name != "" ? 1 : 0

  name          = var.log_bucket_name
  location      = "US"
  force_destroy = false
  versioning {
    enabled = true
  }
  lifecycle_rule {
    action = "Delete"
    condition {
      age = var.retention_days
    }
  }
  labels = merge(var.labels, {
    environment = var.environment
    purpose     = "log-storage"
  })
}

resource "google_logging_bucket" "logs" {
  name         = "${var.environment}-logs"
  location     = "global"
  retention_days = var.retention_days
  labels = merge(var.labels, {
    environment = var.environment
    purpose     = "log-bucket"
  })
}

resource "google_logging_sink" "to_storage" {
  count = var.log_bucket_name != "" ? 1 : 0

  name        = "${var.environment}-sink-to-storage"
  destination = "storage.googleapis.com/${google_storage_bucket.logs[0].name}"
  filter      = "logName:projects/${var.environment}"
  unique_writer_identity = true
  labels = var.labels
}

resource "google_logging_sink" "to_logging_bucket" {
  name        = "${var.environment}-sink-to-logging-bucket"
  destination = "logging.googleapis.com/projects/${var.environment}/locations/global/buckets/${google_logging_bucket.logs.name}"
  filter      = "logName:projects/${var.environment}"
  unique_writer_identity = true
  labels = var.labels
}

resource "google_logging_metric" "error_rate" {
  name   = "${var.environment}-error-rate"
  filter = 'severity>=ERROR'
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
  labels = var.labels
}

output "log_bucket_name" {
  description = "Name of the log storage bucket"
  value       = var.log_bucket_name != "" ? google_storage_bucket.logs[0].name : null
}

output "logging_bucket_name" {
  description = "Name of the logging bucket"
  value       = google_logging_bucket.logs.name
}

output "error_rate_metric" {
  description = "Error rate metric name"
  value       = google_logging_metric.error_rate.name
}