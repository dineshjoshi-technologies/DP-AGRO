# Plan for DJT-11: Stand up secure cloud infrastructure baseline

## Goal

Establish a production-ready, multi-cloud (AWS/GCP/Vercel) infrastructure foundation with infrastructure-as-code, enabling secure deployments, observability, and CI/CD pipelines for DJ Tech's agent platform. This creates the backbone for all subsequent engineering work.

## Context reviewed

- Issue DJT-11 description and acceptance criteria
- Existing empty infra/ directory structure (aws/, gcp/, vercel/, modules/, environments/staging/, environments/production/, .github/workflows/)
- Plan payload indicating blocked on cloud provider credentials (AWS, GCP, Vercel)
- Company mission: secure cloud infrastructure for AI agents
- ADR-001 referencing gVisor + containerd on target cloud (AWS/GCP)
- Parent issue DJT-1 (hiring plan) completed
- Child issues DJT-31 (AWS/GCP infrastructure) and DJT-32 (CI/CD pipelines) blocked on this work

## Constraints and non-goals

**Must hold:**
- Infrastructure-as-code using Terraform (cloud-agnostic where possible)
- Separate staging and production accounts/environments
- Secrets managed via cloud secret stores (AWS Secrets Manager, GCP Secret Manager)
- VPC with public/private subnet separation
- Logging pipeline to centralized observability
- GitHub Actions CI/CD for infrastructure changes
- Domain/SSL via Vercel or cloud provider
- Basic observability stack (logs, metrics, traces)

**Non-goals (deferred):**
- Kubernetes cluster provisioning (EKS/GKE) — separate issue
- Database provisioning (RDS/Cloud SQL) — separate issue
- CDN/WAF configuration — separate issue
- Disaster recovery / backup automation — separate issue
- Cost optimization tooling — separate issue
- Multi-region deployment — separate issue

## Approach

Use Terraform as the single IaC tool across all three providers. Structure follows a modular pattern:
- **modules/** — reusable Terraform modules (VPC, secrets, logging, monitoring)
- **aws/**, **gcp/**, **vercel/** — provider-specific root modules composing shared modules
- **environments/staging/** and **environments/production/** — environment-specific tfvars and backend config
- **.github/workflows/** — CI/CD pipelines for plan/apply per environment

Provider choice rationale:
- **Terraform over Pulumi/CDKTF**: Team familiarity, large provider ecosystem, state management maturity
- **AWS + GCP + Vercel**: Multi-cloud for resilience; Vercel for frontend/edge; AWS/GCP for compute/data
- **Separate accounts per environment**: Security isolation, blast radius limitation

## Work breakdown

### Phase 1: Foundation (no cloud credentials needed — can start immediately)

#### 1.1 Create Terraform module skeleton and shared modules
- **Owner**: Engineer (Infrastructure)
- **Scope**: Create reusable modules in `infra/modules/` for:
  - `vpc/` — VPC, subnets (public/private), NAT gateways, route tables, flow logs
  - `secrets/` — Secret store (AWS Secrets Manager / GCP Secret Manager), IAM policies
  - `logging/` — CloudWatch Log Groups / Cloud Logging sinks, log retention, export to storage
  - `monitoring/` — Basic dashboards, alerts, SLOs (CloudWatch / Cloud Monitoring)
  - `iam/` — Least-privilege roles for CI/CD, workload identity
- **Deliverables**: Module directories with `main.tf`, `variables.tf`, `outputs.tf`, `README.md`
- **Acceptance**: `terraform fmt` and `terraform validate` pass for each module; modules publishable to private registry
- **Blockers**: none

#### 1.2 Create provider root configurations
- **Owner**: Engineer (Infrastructure)
- **Scope**: Create root modules in `infra/aws/`, `infra/gcp/`, `infra/vercel/` that compose shared modules:
  - `infra/aws/main.tf` — providers, backend (S3 + DynamoDB), module invocations
  - `infra/gcp/main.tf` — providers, backend (GCS), module invocations
  - `infra/vercel/main.tf` — provider, project, domain, SSL certs
- **Deliverables**: Root module files, provider version constraints
- **Acceptance**: `terraform init` succeeds (with dummy credentials); plan shows expected resources
- **Blockers**: 1.1

#### 1.3 Create environment configurations
- **Owner**: Engineer (Infrastructure)
- **Scope**: Create `infra/environments/staging/` and `infra/environments/production/` with:
  - `backend.hcl` — backend config per environment
  - `terraform.tfvars` — environment-specific values (CIDR, instance sizes, regions, domain names)
  - `providers.tf` — provider aliases for multi-region if needed
- **Deliverables**: Two environment directories with tfvars
- **Acceptance**: `terraform init -backend-config=backend.hcl` works for both environments
- **Blockers**: 1.2

#### 1.4 Create GitHub Actions CI/CD workflows
- **Owner**: Engineer (Infrastructure)
- **Scope**: Create workflows in `infra/.github/workflows/`:
  - `terraform-plan.yml` — on PR: `terraform fmt`, `validate`, `plan` for changed environments; comment plan on PR
  - `terraform-apply.yml` — on merge to main: `terraform apply` for staging; manual approval for production
  - `drift-detection.yml` — scheduled: detect drift in staging/production
- **Deliverables**: Three workflow YAML files
- **Acceptance**: Workflows pass syntax check; plan workflow runs on test PR
- **Blockers**: 1.3

### Phase 2: Provisioning (requires cloud credentials)

#### 2.1 Provision AWS staging and production accounts
- **Owner**: Engineer (Infrastructure)
- **Scope**: Using AWS credentials, run:
  - Create/setup AWS accounts (or use existing org accounts)
  - Configure Terraform backend (S3 bucket + DynamoDB table for locking)
  - Apply staging environment: VPC, secrets, logging, monitoring
  - Apply production environment: same with production sizing
  - Verify VPC flow logs → CloudWatch → S3 export
- **Deliverables**: Running AWS infrastructure in both environments; backend state stored
- **Acceptance**: `terraform apply` completes without errors; resources visible in AWS console; flow logs flowing
- **Blockers**: 1.4, AWS credentials

#### 2.2 Provision GCP staging and production projects
- **Owner**: Engineer (Infrastructure)
- **Scope**: Using GCP credentials, run:
  - Create/setup GCP projects
  - Configure Terraform backend (GCS bucket)
  - Apply staging environment: VPC, secrets, logging, monitoring
  - Apply production environment: same with production sizing
  - Verify VPC flow logs → Cloud Logging → Cloud Storage export
- **Deliverables**: Running GCP infrastructure in both environments; backend state stored
- **Acceptance**: `terraform apply` completes without errors; resources visible in GCP console; logs flowing
- **Blockers**: 1.4, GCP credentials

#### 2.3 Provision Vercel project and domain/SSL
- **Owner**: Engineer (Infrastructure)
- **Scope**: Using Vercel token, run:
  - Create Vercel project linked to GitHub repo
  - Configure custom domain (djtech.xyz or similar) with automatic SSL
  - Set up preview deployments for PRs
  - Configure environment variables for staging/production
- **Deliverables**: Vercel project with custom domain, SSL, preview deployments
- **Acceptance**: Domain resolves with valid SSL; preview deployments work on test PR
- **Blockers**: 1.4, Vercel token

### Phase 3: Integration & Observability

#### 3.1 Centralized logging pipeline
- **Owner**: Engineer (Infrastructure)
- **Scope**: Connect AWS CloudWatch and GCP Cloud Logging to a central destination:
  - Option A: Export to Loki/Grafana Cloud (preferred for cost)
  - Option B: Export to Elastic/Opensearch
  - Configure log retention, parsing, and basic dashboards
- **Deliverables**: Centralized logs queryable in Grafana; retention policies applied
- **Acceptance**: Logs from both clouds visible in single Grafana instance; sample queries work
- **Blockers**: 2.1, 2.2

#### 3.2 Basic metrics and alerting
- **Owner**: Engineer (Infrastructure)
- **Scope**: 
  - Infrastructure metrics (CPU, memory, disk, network) from both clouds
  - Application metrics endpoints (Prometheus exposition format)
  - Core alerts: high error rate, latency p99, disk pressure, certificate expiry
  - Notification channels: Slack, PagerDuty, email
- **Deliverables**: Grafana dashboards + alert rules + notification channels configured
- **Acceptance**: Alerts fire on synthetic test; dashboards show real data
- **Blockers**: 3.1

#### 3.3 End-to-end validation and documentation
- **Owner**: Engineer (Infrastructure)
- **Scope**:
  - Run full CI/CD pipeline: PR → plan → merge → apply staging
  - Verify drift detection works
  - Document: architecture diagram, runbooks (rotate secrets, scale VPC, failover), credential rotation procedure
  - Create `INFRASTRUCTURE.md` in repo root
- **Deliverables**: Validated pipeline; documentation; runbooks
- **Acceptance**: New engineer can follow docs to spin up staging; pipeline passes
- **Blockers**: 2.1, 2.2, 2.3, 3.1, 3.2

## Acceptance

DJT-11 is complete when:
1. ✅ Terraform modules and root configs exist in `infra/` with passing `fmt`/`validate`
2. ✅ GitHub Actions workflows run successfully (plan on PR, apply on merge with approval)
3. ✅ AWS staging/production: VPC, secrets, logging, monitoring provisioned and verified
4. ✅ GCP staging/production: VPC, secrets, logging, monitoring provisioned and verified
5. ✅ Vercel project with custom domain + SSL + preview deployments working
5. ✅ Centralized logging (Loki/Grafana) receiving logs from both clouds
6. ✅ Basic metrics dashboards and alerts configured with notification channels
7. ✅ Documentation and runbooks complete in repo

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cloud credentials not provided | High | Blocks Phase 2 | Start Phase 1 immediately; escalate for credentials in parallel |
| Terraform state corruption | Low | High | Enable versioning on backend buckets; use DynamoDB/GCS locking |
| Multi-cloud module divergence | Medium | Medium | Shared modules in `infra/modules/`; provider-specific only at root |
| Vercel domain propagation delays | Low | Low | Use subdomain first; apex domain as follow-up |
| Cost overruns in staging | Medium | Low | Set budget alerts; use small instance sizes; auto-shutdown schedules |

## Deferrals

- **Kubernetes clusters (EKS/GKE)** → Separate issue (DJT-33 or new)
- **Managed databases (RDS/Cloud SQL)** → Separate issue
- **Service mesh (Istio/Linkerd)** → Separate issue
- **WAF/CDN (CloudFront/Cloud Armor)** → Separate issue
- **Disaster recovery / cross-region replication** → Separate issue
- **FinOps / cost allocation tags / budgets** → Separate issue
- **Advanced observability (distributed tracing, profiling)** → Separate issue
- **GitOps with ArgoCD/Flux** → Separate issue (current: GitHub Actions native)