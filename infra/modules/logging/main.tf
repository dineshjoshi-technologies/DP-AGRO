terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "log_group_names" {
  description = "List of log group names to create"
  type        = list(string)
  default     = []
}

variable "retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "aws_cloudwatch_log_group" "log_groups" {
  for_each = toset(var.log_group_names)

  name              = "/aws/${var.environment}/${each.value}"
  retention_in_days = var.retention_days
  kms_key_id        = var.kms_key_id != "" ? var.kms_key_id : null

  tags = merge(var.tags, {
    Name        = "${var.environment}-${each.value}"
    Environment = var.environment
  })
}

resource "aws_iam_role" "logging" {
  name = "${var.environment}-logging-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "logs.amazonaws.com"
      }
    }]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-logging-role"
    Environment = var.environment
  })
}

resource "aws_iam_policy" "logging" {
  name = "${var.environment}-logging-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-logging-policy"
    Environment = var.environment
  })
}

resource "aws_iam_role_policy_attachment" "logging" {
  role       = aws_iam_role.logging.name
  policy_arn = aws_iam_policy.logging.arn
}

output "log_group_arns" {
  description = "Map of log group names to their ARNs"
  value       = { for k, v in aws_cloudwatch_log_group.log_groups : k => v.arn }
}

output "log_group_names" {
  description = "Map of log group names to their full names"
  value       = { for k, v in aws_cloudwatch_log_group.log_groups : k => v.name }
}

output "logging_role_arn" {
  description = "ARN of the logging IAM role"
  value       = aws_iam_role.logging.arn
}