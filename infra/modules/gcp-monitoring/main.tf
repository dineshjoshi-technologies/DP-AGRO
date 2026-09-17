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

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "google_monitoring_dashboard" "main" {
  dashboard_json = var.dashboard_config
  labels = merge(var.labels, {
    environment = var.environment
  })
}

resource "google_monitoring_alert_policy" "policies" {
  for_each = var.alert_policies

  display_name = "${var.environment}-${each.key}"
  combiner     = each.value.combiner != "" ? each.value.combiner : "OR"
  conditions {
    dynamic "condition" {
      for_each = each.value.conditions
      content {
        display_name = condition.value.display_name
        condition_threshold {
          filter          = condition.value.filter
          comparison      = condition.value.comparison
          threshold_value = condition.value.threshold_value
          duration        = condition.value.duration != "" ? condition.value.duration : "60s"
          aggregations {
            alignment_period     = condition.value.alignment_period != "" ? condition.value.alignment_period : "60s"
            per_series_aligner   = condition.value.per_series_aligner != "" ? condition.value.per_series_aligner : "ALIGN_RATE"
            cross_series_reducer = condition.value.cross_series_reducer != "" ? condition.value.cross_series_reducer : "REDUCE_MEAN"
            group_by_fields      = condition.value.group_by_fields
          }
        }
      }
    }
  }
  notification_channels = var.notification_channels
  labels = merge(var.labels, {
    environment = var.environment
  })
}

resource "google_monitoring_notification_channel" "default" {
  count = length(var.notification_channels) == 0 ? 1 : 0

  display_name = "${var.environment}-default-channel"
  type         = "email"
  labels = {
    email_address = "alerts@djtech.xyz"
  }
  labels = merge(var.labels, {
    environment = var.environment
  })
}

output "dashboard_name" {
  description = "Name of the monitoring dashboard"
  value       = google_monitoring_dashboard.main.name
}

output "alert_policy_names" {
  description = "Names of the alert policies"
  value       = { for k, v in google_monitoring_alert_policy.policies : k => v.name }
}

output "notification_channel_ids" {
  description = "IDs of the notification channels"
  value       = var.notification_channels != [] ? var.notification_channels : [google_monitoring_notification_channel.default[0].id]
}