terraform {
  required_version = ">= 1.5.0"
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

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional, uses AWS managed key if not provided)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "aws_secretsmanager_secret" "secrets" {
  for_each = var.secret_names

  name        = "${var.environment}/${each.key}"
  description = each.value
  kms_key_id  = var.kms_key_id != "" ? var.kms_key_id : null

  tags = merge(var.tags, {
    Name        = "${var.environment}-${each.key}"
    Environment = var.environment
  })
}

resource "aws_secretsmanager_secret_version" "secrets" {
  for_each = var.secret_names

  secret_id = aws_secretsmanager_secret.secrets[each.key].id
  secret_string = jsonencode({
    placeholder = "replace-with-actual-value"
    created_at  = timestamp()
  })
}

output "secret_arns" {
  description = "Map of secret names to their ARNs"
  value       = { for k, v in aws_secretsmanager_secret.secrets : k => v.arn }
}

output "secret_names" {
  description = "Map of secret names to their full names"
  value       = { for k, v in aws_secretsmanager_secret.secrets : k => v.name }
}