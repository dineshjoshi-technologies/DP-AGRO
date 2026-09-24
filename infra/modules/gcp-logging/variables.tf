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