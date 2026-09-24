terraform {
  required_version = ">= 1.5.0"
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

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.environment}-infrastructure"
  dashboard_body = var.dashboard_config

  tags = merge(var.tags, {
    Name        = "${var.environment}-infrastructure-dashboard"
    Environment = var.environment
  })
}

resource "aws_cloudwatch_metric_alarm" "alarms" {
  for_each = var.alarm_config

  alarm_name          = "${var.environment}-${each.key}"
  alarm_description   = each.value.alarm_description
  metric_name         = each.value.metric_name
  namespace           = each.value.namespace
  statistic           = each.value.statistic
  period              = each.value.period
  evaluation_periods  = each.value.evaluation_periods
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison_operator
  dimensions          = each.value.dimensions

  alarm_actions  = var.sns_topic_arn != "" ? [var.sns_topic_arn] : each.value.alarm_actions
  ok_actions     = each.value.ok_actions
  insufficient_data_actions = []

  tags = merge(var.tags, {
    Name        = "${var.environment}-${each.key}"
    Environment = var.environment
  })
}

resource "aws_sns_topic" "alerts" {
  count = var.sns_topic_arn == "" ? 1 : 0

  name = "${var.environment}-alerts"

  tags = merge(var.tags, {
    Name        = "${var.environment}-alerts-topic"
    Environment = var.environment
  })
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.arn
}

output "alarm_arns" {
  description = "Map of alarm names to their ARNs"
  value       = { for k, v in aws_cloudwatch_metric_alarm.alarms : k => v.arn }
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = var.sns_topic_arn != "" ? var.sns_topic_arn : aws_sns_topic.alerts[0].arn
}