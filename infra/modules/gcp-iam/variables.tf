variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "ci_cd_sa_name" {
  description = "Name for the CI/CD service account"
  type        = string
  default     = "ci-cd"
}

variable "workload_sa_name" {
  description = "Name for the workload service account"
  type        = string
  default     = "workload"
}

variable "allowed_github_org" {
  description = "GitHub organization for workload identity"
  type        = string
  default     = ""
}

variable "allowed_github_repos" {
  description = "List of GitHub repositories allowed for workload identity"
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}