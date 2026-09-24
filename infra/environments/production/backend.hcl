# AWS Backend Configuration for Production
bucket         = "dj-tech-production-terraform-state"
key            = "dj-tech/production/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "dj-tech-production-terraform-locks"
encrypt        = true