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