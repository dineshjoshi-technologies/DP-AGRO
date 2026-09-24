variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "dashboard_config" {
  description = "Dashboard configuration JSON"
  type        = string
  default     = "{}"
}

variable "alarm_config" {
  description = "Map of alarm names to their configurations"
  type        = map(object({
    metric_name        = string
    namespace          = string
    statistic          = string
    period             = number
    evaluation_periods = number
    threshold          = number
    comparison_operator = string
    alarm_description  = string
    alarm_actions      = list(string)
    ok_actions         = list(string)
    dimensions         = map(string)
  }))
  default = {}
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}