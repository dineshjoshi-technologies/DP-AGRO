# DJ Tech Infrastructure Documentation

## Overview

This document describes the infrastructure-as-code setup for DJ Tech's multi-cloud platform (AWS, GCP, Vercel). All infrastructure is managed via Terraform with separate staging and production environments.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DJ Tech Platform                         │
├──────────────────┬──────────────────┬──────────────────────────┤
│       AWS        │       GCP        │        Vercel            │
│  ┌────────────┐  │  ┌────────────┐  │  ┌────────────────────┐  │
│  │   VPC      │  │  │   VPC      │  │  │  Next.js Project   │  │
│  │  (Public/  │  │  │  (Public/  │  │  │  Custom Domain     │  │
│  │   Private) │  │  │   Private) │  │  │  Preview Deploys   │  │
│  ├────────────┤  │  ├────────────┤  │  ├────────────────────┤  │
│  │ Secrets    │  │  │ Secrets    │  │  │  Environment       │  │
│  │ Manager    │  │  │ Manager    │  │  │  Variables         │  │
│  ├────────────┤  │  ├────────────┤  │  └────────────────────┘  │
│  │ CloudWatch │  │  │ Cloud      │  │                          │
│  │ Logs       │  │  │ Logging    │  │                          │
│  ├────────────┤  │  ├────────────┤  │                          │
│  │ CloudWatch │  │  │ Cloud      │  │                          │
│  │ Monitoring │  │  │ Monitoring │  │                          │
│  └────────────┘  │  └────────────┘  │                          │
└──────────────────┴──────────────────┴──────────────────────────┘
```

## Directory Structure

```
infra/
├── modules/                    # Reusable Terraform modules
│   ├── vpc/                   # AWS VPC with public/private subnets, NAT, flow logs
│   ├── gcp-vpc/               # GCP VPC with subnets, firewall, NAT
│   ├── secrets/               # AWS Secrets Manager
│   ├── gcp-secrets/           # GCP Secret Manager
│   ├── logging/               # AWS CloudWatch Log Groups
│   ├── gcp-logging/           # GCP Cloud Logging + Storage sink
│   ├── monitoring/            # AWS CloudWatch dashboards/alarms
│   ├── gcp-monitoring/        # GCP Cloud Monitoring dashboards/alerts
│   ├── iam/                   # AWS IAM roles for CI/CD and workloads
│   └── gcp-iam/               # GCP Service Accounts for CI/CD and workloads
├── aws/                       # AWS root module
├── gcp/                       # GCP root module
├── vercel/                    # Vercel root module
├── environments/
│   ├── staging/
│   │   ├── aws.tfvars         # AWS staging variables
│   │   ├── gcp.tfvars         # GCP staging variables
│   │   ├── vercel.tfvars      # Vercel staging variables
│   │   ├── backend.hcl        # AWS backend config (S3 + DynamoDB)
│   │   └── gcp-backend.hcl    # GCP backend config (GCS)
│   └── production/
│       ├── aws.tfvars
│       ├── gcp.tfvars
│       ├── vercel.tfvars
│       ├── backend.hcl
│       └── gcp-backend.hcl
└── .github/workflows/
    ├── terraform-plan.yml     # PR validation: fmt, validate, plan
    ├── terraform-apply.yml    # Merge to main: apply staging, manual prod
    └── drift-detection.yml    # Daily drift detection with issue creation
```

## Prerequisites

### Required Secrets (GitHub Repository Settings → Secrets → Actions)

#### AWS
- `AWS_ROLE_ARN` - IAM role for GitHub Actions to assume (OIDC)
- `AWS_TERRAFORM_STATE_BUCKET` - S3 bucket for Terraform state
- `AWS_TERRAFORM_LOCKS_TABLE` - DynamoDB table for state locking

#### GCP
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload Identity Pool provider
- `GCP_SERVICE_ACCOUNT` - Service account email for GitHub Actions
- `GCP_TERRAFORM_STATE_BUCKET` - GCS bucket for Terraform state

#### Vercel
- `VERCEL_TOKEN` - Vercel access token

### Cloud Provider Setup

#### AWS
1. Create S3 bucket for Terraform state: `dj-tech-staging-terraform-state`, `dj-tech-production-terraform-state`
2. Enable versioning on buckets
3. Create DynamoDB tables for locking: `dj-tech-staging-terraform-locks`, `dj-tech-production-terraform-locks` (partition key: `LockID`)
4. Create IAM role for GitHub Actions with OIDC trust to `token.actions.githubusercontent.com`
5. Attach policies for: EC2, VPC, SecretsManager, CloudWatch, S3, DynamoDB, IAM

#### GCP
1. Create GCP projects: `dj-tech-staging`, `dj-tech-production`
2. Create GCS buckets for Terraform state
3. Enable APIs: Compute Engine, Secret Manager, Cloud Logging, Cloud Monitoring, IAM, Artifact Registry
4. Create Workload Identity Pool and Provider for GitHub Actions
5. Create service account for GitHub Actions with roles: Editor, Secret Manager Secret Accessor, Logging Log Writer, Monitoring Metric Writer, Storage Object Admin, Artifact Registry Writer

#### Vercel
1. Create Vercel account/organization
2. Generate access token with project read/write permissions
3. Configure custom domain `djtech.xyz` (production) and `staging.djtech.xyz` (staging)

## Usage

### Initialize and Validate (Local Development)

```bash
# AWS Staging
cd infra/aws
terraform init -backend-config=../environments/staging/backend.hcl
terraform plan -var-file=../environments/staging/aws.tfvars

# GCP Staging
cd infra/gcp
terraform init -backend-config=../environments/staging/gcp-backend.hcl
terraform plan -var-file=../environments/staging/gcp.tfvars

# Vercel Staging
cd infra/vercel
terraform init
terraform plan -var-file=../environments/staging/vercel.tfvars
```

### CI/CD Pipeline

The GitHub Actions workflows handle all infrastructure changes:

1. **Pull Request** → `terraform-plan.yml` runs:
   - `terraform fmt -check -recursive`
   - `terraform validate` for each provider
   - `terraform plan` for changed environments (staging only on PR)
   - Comments plan summary on PR

2. **Merge to main** → `terraform-apply.yml` runs:
   - Auto-applies to staging environment
   - Requires manual workflow dispatch for production

3. **Daily (6 AM UTC)** → `drift-detection.yml` runs:
   - Checks for drift in staging and production
   - Creates GitHub issues if drift detected

### Manual Apply

```bash
# Via GitHub Actions UI: Actions → Terraform Apply → Run workflow
# Select environment (staging/production) and provider (aws/gcp/vercel/all)
```

## Environment Details

### Staging
- **AWS**: us-east-1, CIDR 10.0.0.0/16, 30-day log retention
- **GCP**: us-central1, project `dj-tech-staging`, 30-day log retention
- **Vercel**: Preview deployments on `staging` branch, domain `staging.djtech.xyz`

### Production
- **AWS**: us-east-1, CIDR 10.1.0.0/16, 90-day log retention
- **GCP**: us-central1, project `dj-tech-production`, 90-day log retention
- **Vercel**: Production deployments on `main` branch, domain `djtech.xyz`

## Runbooks

### Rotate Secrets

```bash
# AWS
aws secretsmanager put-secret-value \
  --secret-id staging/database-url \
  --secret-string "new-connection-string"

# GCP
echo -n "new-connection-string" | gcloud secrets versions add staging-database-url --data-file=-
```

### Scale VPC (Add Subnets)

1. Update `public_subnet_cidrs` and `private_subnet_cidrs` in tfvars
2. Update `availability_zones` if adding new AZs
3. Run `terraform plan` and `terraform apply`

### Credential Rotation

1. Generate new credentials in cloud console
2. Update GitHub repository secrets
3. Re-run CI/CD pipeline to verify

### Emergency Rollback

```bash
# Find previous state version
aws s3api list-object-versions --bucket dj-tech-staging-terraform-state --prefix dj-tech/staging/

# Restore previous state
aws s3api copy-object \
  --bucket dj-tech-staging-terraform-state \
  --copy-source dj-tech-staging-terraform-state/dj-tech/staging/terraform.tfstate?versionId=<version-id> \
  --key dj-tech/staging/terraform.tfstate

# Run terraform apply to reconcile
```

## Troubleshooting

### Terraform State Lock
```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

### Drift Detected
1. Review the GitHub issue created by drift-detection workflow
2. Run `terraform plan` locally to see differences
3. Either apply the drift correction or update Terraform to match reality

### Module Validation Errors
```bash
# Validate all modules
for dir in infra/modules/*/; do
  cd "$dir"
  terraform fmt -check
  terraform validate
  cd -
done
```

## Cost Estimates (Monthly, USD)

| Component | Staging | Production |
|-----------|---------|------------|
| AWS VPC (NAT Gateways) | ~$45 | ~$45 |
| AWS Secrets Manager | ~$5 | ~$5 |
| AWS CloudWatch Logs | ~$10 | ~$30 |
| AWS CloudWatch Alarms | ~$5 | ~$10 |
| GCP VPC (NAT) | ~$45 | ~$45 |
| GCP Secret Manager | ~$5 | ~$5 |
| GCP Cloud Logging | ~$10 | ~$30 |
| GCP Cloud Monitoring | ~$5 | ~$10 |
| Vercel Pro | $20 | $20 |
| **Total** | **~$150** | **~$200** |

## Security

- All secrets stored in cloud secret managers (never in Terraform state)
- VPC flow logs enabled for network monitoring
- Least-privilege IAM roles for CI/CD and workloads
- OIDC-based GitHub Actions authentication (no long-lived keys)
- Encrypted Terraform state at rest (S3/GCS encryption)
- State locking prevents concurrent modifications

## Contacts

- Platform Team: platform-team@djtech.xyz
- On-call: Check PagerDuty schedule
- Documentation updates: This file in `infra/INFRASTRUCTURE.md`

---

*Last updated: 2026-09-17*
*Infrastructure version: 1.0.0*