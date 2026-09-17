variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = []
}

variable "secret_names" {
  description = "Map of secret names to their descriptions"
  type        = map(string)
  default     = {
    "database-url"      = "Database connection string"
    "redis-url"         = "Redis connection string"
    "api-keys"          = "External API keys"
    "jwt-secret"        = "JWT signing secret"
    "encryption-key"    = "Data encryption key"
  }
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional)"
  type        = string
  default     = ""
}

variable "log_group_names" {
  description = "List of log group names to create"
  type        = list(string)
  default     = ["app", "nginx", "audit"]
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "dashboard_config" {
  description = "Dashboard configuration JSON"
  type        = string
  default     = <<-EOT
    {
      "widgets": [
        {
          "type": "metric",
          "properties": {
            "metrics": [
              ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "web-asg"],
              ["AWS/EC2", "NetworkIn", "AutoScalingGroupName", "web-asg"],
              ["AWS/EC2", "NetworkOut", "AutoScalingGroupName", "web-asg"]
            ],
            "period": 300,
            "stat": "Average",
            "region": "us-east-1",
            "title": "EC2 Metrics"
          }
        }
      ]
    }
  EOT
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
  default = {
    "high-cpu" = {
      metric_name        = "CPUUtilization"
      namespace          = "AWS/EC2"
      statistic          = "Average"
      period             = 300
      evaluation_periods = 2
      threshold          = 80
      comparison_operator = "GreaterThanThreshold"
      alarm_description  = "High CPU utilization detected"
      alarm_actions      = []
      ok_actions         = []
      dimensions         = {}
    }
  }
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  type        = string
  default     = ""
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

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {
    Project     = "dj-tech"
    ManagedBy   = "terraform"
    Environment = "staging"
  }
}