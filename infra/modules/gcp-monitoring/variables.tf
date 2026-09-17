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