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