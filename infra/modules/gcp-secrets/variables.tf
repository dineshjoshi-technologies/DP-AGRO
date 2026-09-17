variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "secret_names" {
  description = "Map of secret names to their descriptions"
  type        = map(string)
  default     = {}
}

variable "replication_policy" {
  description = "Replication policy for secrets"
  type        = string
  default     = "AUTOMATIC"
}

variable "labels" {
  description = "Labels to apply to all secrets"
  type        = map(string)
  default     = {}
}