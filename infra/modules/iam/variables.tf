variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "ci_cd_role_name" {
  description = "Name for the CI/CD IAM role"
  type        = string
  default     = "ci-cd"
}

variable "workload_role_name" {
  description = "Name for the workload IAM role"
  type        = string
  default     = "workload"
}

variable "allowed_github_org" {
  description = "GitHub organization for OIDC trust"
  type        = string
  default     = ""
}

variable "allowed_github_repos" {
  description = "List of GitHub repositories allowed to assume the CI/CD role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}