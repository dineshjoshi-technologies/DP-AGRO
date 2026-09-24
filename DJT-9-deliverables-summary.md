# DJT-9: Design Core AI Agent Orchestration Architecture - Deliverables Summary

**Issue:** DJT-9 Design core AI agent orchestration architecture  
**Status:** Complete  
**Date:** 2026-09-16  

---

## Deliverables Completed

### 1. RFC (Request for Comments)
**File:** `/home/paperclip/paperclip/docs/rfc-orchestration.md`

Comprehensive architecture document covering:
- Multi-agent orchestration runtime architecture (control plane + data plane)
- Three-tier sandboxing model (gVisor, Kata, Native)
- LLM Router sidecar pattern
- Job queue with Redis Streams + exactly-once semantics
- State persistence (Redis hot, S3 warm, PostgreSQL/TimescaleDB cold)
- Billing & metering pipeline (NATS → TimescaleDB → Stripe)
- API surface (gRPC/REST for agent management, job execution)
- Agent manifest specification (YAML)
- Tech stack recommendation table (12 layers)
- 4-phase implementation plan (12 weeks)
- Open questions (GPU, Wasm, multi-region, custom runtimes, pricing)
- Threat model (STRIDE)

---

### 2. Architecture Decision Records (ADRs)

#### ADR-001: Agent Sandboxing Model
**Files:** 
- `/home/paperclip/paperclip/ADR-001-agent-sandboxing-model.md` (original)
- `/home/paperclip/paperclip/docs/ADRs/001-sandboxing.md` (docs version)

**Decision:** gVisor (runsc) as primary sandbox, Kata Containers for VM isolation, native for trusted components
- Three isolation layers with clear use cases
- Resource limits via cgroups v2
- Network policy via eBPF/Cilium (default-deny)
- LLM Gateway Proxy for tool-use boundaries
- RuntimeClass definitions for Kubernetes
- Kyverno admission control

#### ADR-002: LLM Router and Model Selection
**File:** `/home/paperclip/paperclip/ADR-002-llm-router-model-selection.md`

**Decision:** Provider-agnostic LLM router with intelligent model selection
- Request Normalizer → Model Selector → Provider Adapter pipeline
- Fallback Manager with circuit breakers
- Cost/Latency Tracker feeding back to selection
- Schema Translator for provider compatibility
- Weighted scoring algorithm (quality=0.5, cost=0.3, latency=0.1, budget=0.1)
- Provider support matrix (OpenAI, Anthropic, Ollama, vLLM, Bedrock)
- Streaming via SSE with unified chunk format

#### ADR-003: Job Queue and State Persistence
**Files:**
- `/home/paperclip/paperclip/ADR-003-job-queue-state-persistence.md` (original)
- `/home/paperclip/paperclip/docs/ADRs/003-job-queue-state-persistence.md` (docs version)

**Decision:** Redis Streams + PostgreSQL/TimescaleDB + S3/MinIO
- Redis Streams for hot queue with consumer groups
- Exactly-once via idempotency keys + atomic claim + state commit
- Three-tier state persistence (Redis hot, S3 warm, PostgreSQL cold)
- Lua scripts for atomic operations
- Retry policies with exponential backoff + jitter
- Cron + delayed job scheduling
- Worker protocol with heartbeats

---

### 3. Tech Stack Recommendation
**Included in:** RFC (`/home/paperclip/paperclip/docs/rfc-orchestration.md`)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Orchestration | Kubernetes + KubeVirt | Mature, multi-cloud, RuntimeClass support |
| Sandbox (L1) | gVisor (runsc) | Strong isolation, OCI-compatible, low overhead |
| Sandbox (L2) | Kata Containers 3.x | VM isolation, Kubernetes-native, GPU support |
| Message Bus | NATS JetStream | High throughput, persistence, consumer groups |
| State/Queue | Redis Cluster 7.2+ | Streams, Lua scripting, Redis Functions |
| Object Storage | MinIO (S3 API) | S3-compatible, erasure coding, multi-site |
| Metadata/Relational | PostgreSQL 16 + TimescaleDB | ACID, JSONB, time-series hypertable |
| Service Mesh | Istio (ambient) | mTLS, authz, observability, no sidecar overhead |
| Policy/Admission | Kyverno | Native K8s, mutate/validate/generate |
| Observability | OpenTelemetry + Grafana + Tempo + Loki | Vendor-neutral, full stack |
| Control Plane | Go 1.22+ | Performance, ecosystem, team expertise |
| Agent Runtime Base | Distroless + Nix | Minimal attack surface, reproducible builds |

---

### 4. Spike Prototype - Primary Runtime
**Directory:** `/home/paperclip/paperclip/spike-prototype/`

#### Components Built:

| Component | Path | Description |
|-----------|------|-------------|
| **LLM Router** | `llm-router/` | Go service with OpenAI, Anthropic, Ollama adapters; model selector with weighted scoring; HTTP handler (OpenAI-compatible) |
| **Job Queue** | `job-queue/` | Redis-backed queue with sorted sets; Lua scripts for atomic claim/fail/complete; worker pool with concurrency control; heartbeat mechanism |
| **Scheduler** | `job-queue/scheduler/` | Cron jobs (robfig/cron); delayed job promotion from sorted sets; one-time scheduling |
| **LLM Gateway** | `llm-gateway/` | Token budgets (daily per-agent); rate limiting (token bucket); PII redaction (regex); audit logging (JSONL); model allowlist |
| **eBPF Network Policy** | `ebpf/ebpf-agent-policy.c` | Per-agent egress allowlist; DNS filtering; connection tracking; ring buffer audit events; TC classifier programs |
| **Configuration** | `config/` | cgroups v2 limits; containerd config with gVisor; Distroless agent base Dockerfile |

#### Key Implementation Details:

**LLM Router:**
- `router/router.go` - Core routing logic, HTTP handlers, model selection
- `adapters/openai.go`, `anthropic.go`, `ollama.go` - Provider implementations
- `selector/selector.go` - Weighted scoring model selection
- `main.go` - Server entry point with config loading

**Job Queue:**
- `queue/job.go` - Job struct, statuses, retry policy, next retry calculation
- `queue/redis_queue.go` - Redis implementation with Lua scripts for atomic operations; MockQueue for testing
- `worker/worker.go` - Worker pool with concurrency, heartbeat loop, handler registration
- `scheduler/scheduler.go` - Cron scheduler + delayed job mover

**LLM Gateway:**
- `main.go` - Gin HTTP server with middleware for auth, rate limit, budget, PII, audit
- `config.json` - Runtime configuration (models, budgets, rate limits, PII patterns, upstreams)

**eBPF:**
- `ebpf-agent-policy.c` - Two TC classifiers (egress + DNS); agent config map; DNS allowlist; connection tracking; per-agent stats; ring buffer audit events

---

## Verification Checklist

| Deliverable | Status | Location |
|-------------|--------|----------|
| RFC | ✅ Complete | `docs/rfc-orchestration.md` |
| ADR-001 (Sandboxing) | ✅ Complete | `ADR-001-agent-sandboxing-model.md`, `docs/ADRs/001-sandboxing.md` |
| ADR-002 (LLM Router) | ✅ Complete | `ADR-002-llm-router-model-selection.md` |
| ADR-003 (Job Queue) | ✅ Complete | `ADR-003-job-queue-state-persistence.md`, `docs/ADRs/003-job-queue-state-persistence.md` |
| Tech Stack Recommendation | ✅ Complete | In RFC Section "Tech Stack Recommendation" |
| Spike: LLM Router | ✅ Complete | `spike-prototype/llm-router/` |
| Spike: Job Queue + Scheduler | ✅ Complete | `spike-prototype/job-queue/` |
| Spike: LLM Gateway | ✅ Complete | `spike-prototype/llm-gateway/` |
| Spike: eBPF Network Policy | ✅ Complete | `spike-prototype/ebpf/` |
| Spike: Configuration | ✅ Complete | `spike-prototype/config/` |

---

## Next Steps (Post-DJT-9)

Based on the RFC implementation phases:

1. **Phase 1 (Weeks 1-3):** Kubernetes cluster with gVisor/Kata RuntimeClasses; Agent Registry + API Gateway; Sandbox admission; Basic job queue + worker pool; Observability foundation
2. **Phase 2 (Weeks 4-6):** LLM Router sidecar deployment; Durable job queue with exactly-once; State persistence (Redis + S3 + PostgreSQL); Agent lifecycle management; Network policies + Istio
3. **Phase 3 (Weeks 7-9):** Billing & metering pipeline (ADR-004); Autoscale controller (KEDA); Multi-tenancy (quotas, RBAC, cost attribution); Disaster recovery; Load testing (10k agents)
4. **Phase 4 (Weeks 10-12):** CLI (`djtech`); Local dev (Kind + gVisor); SDKs (Python, TypeScript, Go); Documentation, examples, CI/CD integration

---

## Architecture Diagram (from RFC)

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