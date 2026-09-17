variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
}

variable "subnets" {
  description = "Map of subnet names to configurations"
  type        = map(object({
    ip_cidr_range              = string
    region                     = string
    private_ip_google_access   = bool
    secondary_ranges           = list(object({
      range_name    = string
      ip_cidr_range = string
    }))
  }))
}

variable "secondary_ranges" {
  description = "Secondary IP ranges for pods/services"
  type        = map(list(object({
    range_name    = string
    ip_cidr_range = string
  })))
  default = {}
}

variable "tags" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}