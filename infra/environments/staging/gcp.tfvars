environment = "staging"

gcp_project_id = "dj-tech-staging"

gcp_region = "us-central1"

network_name = "dj-tech-network-staging"

subnets = {
  "public-us-central1-a" = {
    ip_cidr_range              = "10.0.1.0/24"
    region                     = "us-central1"
    private_ip_google_access   = false
    secondary_ranges           = []
  }
  "private-us-central1-a" = {
    ip_cidr_range              = "10.0.11.0/24"
    region                     = "us-central1"
    private_ip_google_access   = true
    secondary_ranges           = []
  }
  "public-us-central1-b" = {
    ip_cidr_range              = "10.0.2.0/24"
    region                     = "us-central1"
    private_ip_google_access   = false
    secondary_ranges           = []
  }
  "private-us-central1-b" = {
    ip_cidr_range              = "10.0.12.0/24"
    region                     = "us-central1"
    private_ip_google_access   = true
    secondary_ranges           = []
  }
}

secondary_ranges = {}

secret_names = {
  "database-url"      = "Database connection string"
  "redis-url"         = "Redis connection string"
  "api-keys"          = "External API keys"
  "jwt-secret"        = "JWT signing secret"
  "encryption-key"    = "Data encryption key"
}

log_bucket_name = "dj-tech-staging-logs"

log_retention_days = 30

dashboard_config = "{}"

alert_policies = {}

notification_channels = []

ci_cd_sa_name = "ci-cd"

workload_sa_name = "workload"

allowed_github_org = ""

allowed_github_repos = []

common_tags = {
  project     = "dj-tech"
  managed-by  = "terraform"
  environment = "staging"
  owner       = "platform-team"
}