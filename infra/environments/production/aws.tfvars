environment = "production"

aws_region = "us-east-1"

vpc_cidr_block = "10.1.0.0/16"

public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]

private_subnet_cidrs = ["10.1.11.0/24", "10.1.12.0/24"]

availability_zones = ["us-east-1a", "us-east-1b"]

secret_names = {
  "database-url"      = "Database connection string"
  "redis-url"         = "Redis connection string"
  "api-keys"          = "External API keys"
  "jwt-secret"        = "JWT signing secret"
  "encryption-key"    = "Data encryption key"
}

kms_key_id = ""

log_group_names = ["app", "nginx", "audit"]

log_retention_days = 90

dashboard_config = <<-EOT
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

alarm_config = {
  "high-cpu" = {
    metric_name        = "CPUUtilization"
    namespace          = "AWS/EC2"
    statistic          = "Average"
    period             = 300
    evaluation_periods = 2
    threshold          = 70
    comparison_operator = "GreaterThanThreshold"
    alarm_description  = "High CPU utilization detected"
    alarm_actions      = []
    ok_actions         = []
    dimensions         = {}
  }
}

sns_topic_arn = ""

ci_cd_role_name = "ci-cd"

workload_role_name = "workload"

allowed_github_org = ""

allowed_github_repos = []

common_tags = {
  Project     = "dj-tech"
  ManagedBy   = "terraform"
  Environment = "production"
  Owner       = "platform-team"
}