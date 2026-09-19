# AWS Backend Configuration for Staging
bucket         = "dj-tech-staging-terraform-state"
key            = "dj-tech/staging/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "dj-tech-staging-terraform-locks"
encrypt        = true