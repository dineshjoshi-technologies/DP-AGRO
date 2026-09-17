# RFC: Multi-Agent Orchestration Runtime Architecture

**Status:** Draft
**Date:** 2026-09-16
**Author:** DJ Tech Engineering
**Related:** ADR-001 (Sandboxing), ADR-002 (LLM Router), ADR-003 (Job Queue), ADR-004 (Billing)

## Overview

This RFC proposes the architecture for DJ Tech's multi-agent orchestration runtime — a platform for running thousands of AI agents securely, scalably, and cost-effectively. The runtime provides sandboxed execution, intelligent LLM routing, durable job queues, state persistence, and usage-based billing.

## Goals

- **Security:** Strong isolation between agents and from host
- **Scalability:** Support 10,000+ concurrent agents
- **Cost efficiency:** Sub-second cold start; pay-per-use billing
- **Developer experience:** Simple API, rich observability, local dev parity
- **Extensibility:** Pluggable LLM providers, tool ecosystems, custom runtimes

## Non-Goals

- Building our own LLM models
- Replacing Kubernetes (we run on top)
- Supporting bare-metal without container orchestration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CONTROL PLANE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   API        │  │  Agent       │  │  Job         │  │  Billing &     │  │
│  │   Gateway    │──│  Registry    │──│  Queue       │──│  Metering      │  │
│  │   (gRPC/REST)│  │  (etcd)      │  │  (Redis      │  │  (TimescaleDB) │  │
│  └──────────────┘  └──────────────┘  │   Streams)   │  └────────────────┘  │
│         │                            └──────────────┘         │            │
│         ▼                                                          ▼            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATION ENGINE (Go)                           │  │
│  │  • Agent lifecycle (create, start, stop, scale, delete)                │  │
│  │  • Sandbox selection (gVisor/Kata/Native) via ADR-001                  │  │
│  │  • Resource scheduling & quota enforcement                             │  │
│  │  • Health checks, auto-recovery, graceful degradation                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌────────────────┐ ┌───────────────┐ ┌────────────────┐
         │  DATA PLANE    │ │  DATA PLANE   │ │  DATA PLANE    │
         │  (Worker Pool) │ │  (Worker Pool)│ │  (Worker Pool) │
         │                │ │               │ │                │
         │ ┌────────────┐ │ │ ┌────────────┐ │ │ ┌────────────┐ │
         │ │ gVisor Pod │ │ │ │ Kata Pod   │ │ │ │ Native Pod │ │
         │ │ Agent #1   │ │ │ │ Agent #2   │ │ │ │ Infra #1   │ │
         │ └────────────┘ │ │ └────────────┘ │ │ └────────────┘ │
         │ ┌────────────┐ │ │ ┌────────────┐ │ │ ┌────────────┐ │
         │ │ gVisor Pod │ │ │ │ gVisor Pod │ │ │ │ gVisor Pod │ │
         │ │ Agent #3   │ │ │ │ Agent #4   │ │ │ │ Agent #5   │ │
         │ └────────────┘ │ │ └────────────┘ │ │ └────────────┘ │
         └────────────────┘ └───────────────┘ └────────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
         ┌────────────────────────────────────────────────────────────────┐
         │                      SHARED INFRASTRUCTURE                      │
         │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
         │  │  NATS    │ │  Redis   │ │  S3/     │ │  PostgreSQL      │  │
         │  │  JetStream│ │  Cluster │ │  MinIO   │ │  (metadata,      │  │
         │  │  (msg bus)│ │  (state) │ │  (files) │ │   billing)       │  │
         │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
         └────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Sandboxing Model (ADR-001)

Three-tier isolation per [ADR-001](./ADRs/001-sandboxing.md):

| Tier | Runtime | Isolation | Overhead | Use Case |
|------|---------|-----------|----------|----------|
| **L1** | gVisor (runsc) | Syscall interception | 5-15% | Default agent workloads |
| **L2** | Kata Containers | Full VM (own kernel) | ~100MB, 100-200ms | Sensitive data, untrusted code, GPU |
| **L3** | Native (runc) | Namespaces + cgroups | Near-zero | Control plane, trusted infra |

**Selection logic:** Agent manifest declares `securityTier: standard|high|system` → mapped to RuntimeClass at admission.

### 2. LLM Router (ADR-002 — *proposed*)

**Design:** Sidecar proxy pattern (`llm-router` container per pod)

```yaml
# Agent pod with LLM router sidecar
containers:
- name: agent
  image: djtech/agent-runtime:v1
- name: llm-router
  image: djtech/llm-router:v1
  env:
  - name: ROUTER_CONFIG
    value: |
      providers:
        - name: openai
          models: [gpt-4o, gpt-4o-mini, o1-preview]
          priority: 1
          costPer1kTokens: {input: 5.00, output: 15.00}
        - name: anthropic
          models: [claude-3.5-sonnet, claude-3.5-haiku]
          priority: 2
          costPer1kTokens: {input: 3.00, output: 15.00}
        - name: local
          models: [llama-3.1-70b, llama-3.1-8b]
          priority: 3
          costPer1kTokens: {input: 0.00, output: 0.00}
      routing:
        strategy: cost_optimized  # or latency_optimized, quality_optimized
        fallback: true
        cacheTTL: 3600
```

**Features:**
- Automatic failover across providers
- Semantic caching (embedding-based) for repeated prompts
- Cost/latency/quality routing strategies
- Per-agent budget enforcement
- Request/response logging for audit

### 3. Job Queue & State Persistence (ADR-003 — *proposed*)

**Job Queue:** Redis Streams + consumer groups

```redis
# Job structure
XADD jobs:*agent-id* * \
  id "job-uuid" \
  type "llm_inference|tool_execution|workflow_step" \
  payload '{"prompt":"...","tools":[...]}' \
  priority 10 \
  idempotencyKey "client-key" \
  timeoutMs 30000 \
  retryPolicy '{"maxAttempts":3,"backoffMs":1000}'
```

**Exactly-once semantics:**
- Client provides `idempotencyKey` → deduplication at ingest
- Consumer group ack after successful processing + state commit
- Dead letter stream for exhausted retries

**State Persistence:**
- **Ephemeral:** In-memory (per job, TTL 1hr)
- **Durable:** Redis Cluster (agent session state, conversation history)
- **Archival:** S3/MinIO (large outputs, artifacts, logs)
- **Queryable:** PostgreSQL (metadata, billing events, audit log)

### 4. Billing & Metering (ADR-004 — *proposed*)

**Model:** Per-second, per-token, per-tool-call

```go
type UsageEvent struct {
    AgentID       string
    TenantID      string
    Timestamp     time.Time
    EventType     string  // llm_tokens, tool_call, sandbox_seconds, storage_bytes
    Quantity      int64
    UnitCost      float64 // USD * 1e9 (nano-USD)
    Metadata      map[string]string
}
```

**Pipeline:**
1. Sidecars emit usage events → NATS JetStream
2. Billing collector aggregates → TimescaleDB (hypertable by hour)
3. Hourly rollups → invoice generation (Stripe/usage-based)
4. Real-time quota enforcement via Redis counters

---

## API Surface

### Agent Management
```protobuf
service AgentService {
  rpc CreateAgent(CreateAgentRequest) returns (Agent);
  rpc GetAgent(GetAgentRequest) returns (Agent);
  rpc ListAgents(ListAgentsRequest) returns (stream Agent);
  rpc UpdateAgent(UpdateAgentRequest) returns (Agent);
  rpc DeleteAgent(DeleteAgentRequest) returns (Empty);
  rpc StartAgent(StartAgentRequest) returns (Operation);
  rpc StopAgent(StopAgentRequest) returns (Operation);
  rpc GetAgentLogs(GetAgentLogsRequest) returns (stream LogEntry);
}
```

### Job Execution
```protobuf
service JobService {
  rpc SubmitJob(SubmitJobRequest) returns (Job);
  rpc GetJob(GetJobRequest) returns (Job);
  rpc StreamJobEvents(StreamJobEventsRequest) returns (stream JobEvent);
  rpc CancelJob(CancelJobRequest) returns (Empty);
}
```

### Agent Manifest (YAML)
```yaml
apiVersion: djtech.io/v1
kind: Agent
metadata:
  name: "research-assistant"
  tenant: "acme-corp"
spec:
  securityTier: standard  # standard|high|system
  runtime:
    image: "djtech/agent-python:3.11"
    entrypoint: ["python", "-m", "agent_main"]
  resources:
    cpu: "1000m"
    memory: "2Gi"
  llm:
    defaultModel: "gpt-4o-mini"
    maxTokensPerRequest: 8192
    monthlyBudgetUSD: 50.00
  tools:
    - name: "web_search"
      type: "builtin"
    - name: "code_exec"
      type: "sandboxed"
      config:
        language: "python"
        timeoutSeconds: 30
  networking:
    egressAllowlist:
      - "api.github.com"
      - "*.wikipedia.org"
  autoscaling:
    minReplicas: 0
    maxReplicas: 10
    scaleUpDelaySeconds: 30
```

---

## Tech Stack Recommendation

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Orchestration** | Kubernetes + KubeVirt | Mature, multi-cloud, RuntimeClass support |
| **Sandbox (L1)** | gVisor (runsc) | Strong isolation, OCI-compatible, low overhead |
| **Sandbox (L2)** | Kata Containers 3.x | VM isolation, Kubernetes-native, GPU support |
| **Message Bus** | NATS JetStream | High throughput, persistence, consumer groups |
| **State/Queue** | Redis Cluster 7.2+ | Streams, Lua scripting, Redis Functions |
| **Object Storage** | MinIO (S3 API) | S3-compatible, erasure coding, multi-site |
| **Metadata/Relational** | PostgreSQL 16 + TimescaleDB | ACID, JSONB, time-series hypertable |
| **Service Mesh** | Istio (ambient) | mTLS, authz, observability, no sidecar overhead |
| **Policy/Admission** | Kyverno | Native K8s, mutate/validate/generate |
| **Observability** | OpenTelemetry + Grafana + Tempo + Loki | Vendor-neutral, full stack |
| **Control Plane** | Go 1.22+ | Performance, ecosystem, team expertise |
| **Agent Runtime Base** | Distroless + Nix | Minimal attack surface, reproducible builds |

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-3)
- [ ] Kubernetes cluster with gVisor/Kata runtime classes
- [ ] Agent Registry (etcd) + API Gateway (Go/gRPC)
- [ ] ADR-001 implementation: sandbox admission + pod templates
- [ ] Basic job queue (Redis Streams) + worker pool
- [ ] Minimal observability (metrics, logs, traces)

### Phase 2: Core Runtime (Weeks 4-6)
- [ ] LLM Router sidecar (ADR-002)
- [ ] Durable job queue with exactly-once (ADR-003)
- [ ] State persistence (Redis + S3 + PostgreSQL)
- [ ] Agent lifecycle: create, start, stop, scale, logs
- [ ] Network policies + service mesh integration

### Phase 3: Production Hardening (Weeks 7-9)
- [ ] Billing & metering pipeline (ADR-004)
- [ ] Autoscale controller (KEDA + custom scaler)
- [ ] Multi-tenancy: quotas, RBAC, cost attribution
- [ ] Disaster recovery: backup/restore, cross-region
- [ ] Load testing: 10k concurrent agents

### Phase 4: Developer Experience (Weeks 10-12)
- [ ] CLI (`djtech agent create|deploy|logs|exec`)
- [ ] Local dev environment (Kind + gVisor)
- [ ] SDKs: Python, TypeScript, Go
- [ ] Documentation, examples, templates
- [ ] CI/CD integration (GitHub Actions, GitLab)

---

## Open Questions

1. **GPU scheduling:** How to share GPUs across sandboxed agents? (vGPU, MIG, time-slicing)
2. **Wasm support:** Should we add a Wasm/WASI runtime tier for ultra-fast cold starts?
3. **Multi-region:** Active-active vs active-passive for control plane?
4. **Custom runtimes:** Allow users to bring their own base images? Security implications?
5. **Pricing model:** Per-agent-month + usage vs pure usage-based?

---

## Appendix: Threat Model (STRIDE)

| Threat | Mitigation |
|--------|------------|
| **Spoofing** | mTLS everywhere; SPIFFE identities; JWT for API |
| **Tampering** | Signed images (cosign); SBOM; admission validation |
| **Repudiation** | Immutable audit log (append-only); billing events signed |
| **Information Disclosure** | NetworkPolicy deny-all; secrets via Vault/ESO; encryption at rest/in transit |
| **DoS** | Resource quotas; rate limits; priority classes; autoscaling |
| **Elevation of Privilege** | gVisor/Kata isolation; no privileged containers; seccomp; drop caps |

---

## References

- [ADR-001: Agent Sandboxing Model](./ADRs/001-sandboxing.md)
- [gVisor Security Model](https://gvisor.dev/docs/security_model/)
- [Kata Containers Architecture](https://katacontainers.io/architecture/)
- [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)
- [KEDA Autoscaling](https://keda.sh/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)