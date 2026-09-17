# ADR-003: Job Queue and State Persistence

**Status:** Accepted
**Date:** 2026-09-16
**Author:** DJ Tech Engineering
**Related:** RFC: Multi-Agent Orchestration Runtime Architecture, ADR-001 (Sandboxing), ADR-002 (LLM Router), ADR-004 (Billing)

## Context

The multi-agent runtime requires a durable job queue for executing agent workloads (LLM inference, tool execution, workflow steps) with exactly-once semantics, retries, scheduling, and state persistence across agent restarts and failures.

## Decision

We will use **Redis Streams** as the primary job queue, with **Redis Cluster** for state persistence, **S3/MinIO** for large object storage, and **PostgreSQL/TimescaleDB** for queryable metadata and billing events.

### Job Queue: Redis Streams

```
┌─────────────────────────────────────────────────────────────────┐
│                      REDIS STREAMS TOPOLOGY                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PRODUCERS                    CONSUMERS                          │
│  ┌─────────┐                  ┌─────────────────────┐           │
│  │ API GW  │──XADD jobs:*────▶│ Consumer Group:       │           │
│  │ Agent   │   (per agent)    │  "agent-workers"      │           │
│  │ SDK     │                  │  ├─ Worker 1          │           │
│  └─────────┘                  │  ├─ Worker 2          │           │
│                               │  └─ Worker N          │           │
│                               └──────────┬────────────┘           │
│                                          │                        │
│                                          ▼                        │
│                               ┌─────────────────────┐           │
│                               │ XACK after success  │           │
│                               │ + state commit      │           │
│                               └─────────────────────┘           │
│                                                                  │
│  DEAD LETTER: jobs:dlq:* (exhausted retries)                    │
│  SCHEDULED: jobs:scheduled:* (sorted set by executeAt)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Job Message Format

```redis
XADD jobs:{agent-id} * \
  id "job-uuid-v4" \
  type "llm_inference|tool_execution|workflow_step|agent_lifecycle" \
  payload '{"prompt":"...","tools":[...],"context":{...}}' \
  priority "10" \                    # 1-100, higher = more urgent
  idempotencyKey "client-provided-key" \
  timeoutMs "30000" \
  retryPolicy '{"maxAttempts":3,"backoffMs":1000,"backoffMultiplier":2}' \
  scheduledAt "2026-09-16T10:30:00Z" \  # optional, for delayed execution
  correlationId "workflow-uuid" \       # for tracing multi-step workflows
  parentJobId "parent-job-uuid" \       # for job hierarchies
  metadata '{"tenant":"acme","billingCode":"research"}'
```

### Exactly-Once Semantics

1. **Client-side deduplication:** Client provides `idempotencyKey` → API Gateway checks Redis `SETNX idempotency:{key} "job-id" EX 86400` before enqueueing
2. **Consumer-group processing:** Workers claim jobs via `XREADGROUP GROUP agent-workers worker-1 COUNT 1 STREAMS jobs:agent-123 >`
3. **Processing + State Commit:** Worker processes job, writes result to state store, then `XACK jobs:agent-123 agent-workers job-id`
4. **Failure handling:** Unacked jobs redelivered after `BLOCK` timeout; max retries per `retryPolicy`; exhausted → `XADD jobs:dlq:agent-123 * ...`

### Retry & Backoff

```go
type RetryPolicy struct {
    MaxAttempts      int     `json:"maxAttempts"`       // default: 3
    BaseBackoffMs    int     `json:"baseBackoffMs"`     // default: 1000
    MaxBackoffMs     int     `json:"maxBackoffMs"`      // default: 60000
    BackoffMultiplier float64 `json:"backoffMultiplier"` // default: 2.0
    RetryableErrors  []string `json:"retryableErrors"`  // e.g., ["timeout", "rate_limit", "unavailable"]
}
```

**Implementation:** Lua script atomically checks attempt count, calculates next backoff, re-enqueues with incremented attempt header.

### Scheduling (Delayed/Cron Jobs)

- **One-time:** `scheduledAt` timestamp → sorted set `jobs:scheduled:{agent-id}` with score = unix ms
- **Cron:** Separate scheduler service evaluates cron expressions, enqueues to stream at scheduled time
- **Scheduler:** Lightweight Go service scanning sorted sets every 10s, moving due jobs to streams

---

## State Persistence

### Three-Tier Storage

| Tier | Technology | Data Type | TTL | Use Case |
|------|------------|-----------|-----|----------|
| **Hot** | Redis Cluster | Session state, conversation history, intermediate results | 1-24 hrs | Active agent sessions, recent job results |
| **Warm** | S3/MinIO | Large outputs, artifacts, logs, checkpoints | 30-90 days | LLM responses >10KB, file outputs, debug bundles |
| **Cold** | PostgreSQL + TimescaleDB | Metadata, billing events, audit logs, job summaries | Years | Queryable history, billing, compliance, analytics |

### Hot State (Redis)

```redis
# Agent session state
HSET agent:state:{agent-id} \
  status "running" \
  currentJob "job-uuid" \
  context '{"messages":[...],"tools":[...]}' \
  updatedAt "2026-09-16T10:30:00Z"
EXPIRE agent:state:{agent-id} 86400

# Job result (for polling/streaming)
SET job:result:{job-id} '{"status":"completed","output":{...},"usage":{...}}' EX 3600

# Conversation history (trimmed)
LPUSH agent:history:{agent-id} '{"role":"user","content":"..."}'
LTRIM agent:history:{agent-id} 0 99  # keep last 100
```

### Warm State (S3/MinIO)

```
s3://djtech-agents/
  ├─ {tenant-id}/
  │   ├─ {agent-id}/
  │   │   ├─ jobs/
  │   │   │   ├─ {job-id}/
  │   │   │   │   ├─ input.json
  │   │   │   │   ├─ output.json
  │   │   │   │   ├─ logs.txt
  │   │   │   │   └─ artifacts/
  │   │   ├─ checkpoints/
  │   │   │   └─ {checkpoint-id}.msgpack
  │   │   └─ exports/
  │   │       └─ conversation-{date}.jsonl
```

- Presigned URLs for agent read/write (TTL 1hr)
- Multipart upload for large artifacts
- Lifecycle policy: IA after 30d, Glacier after 90d

### Cold State (PostgreSQL + TimescaleDB)

```sql
-- Job metadata (TimescaleDB hypertable)
CREATE TABLE job_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL,
    tenant_id       UUID NOT NULL,
    job_type        VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL,  -- pending, running, completed, failed, cancelled
    priority        INT DEFAULT 10,
    idempotency_key VARCHAR(128) UNIQUE,
    correlation_id  UUID,
    parent_job_id   UUID,
    scheduled_at    TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     BIGINT,
    input_tokens    BIGINT,
    output_tokens   BIGINT,
    tool_calls      INT,
    error_message   TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('job_events', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_job_events_agent ON job_events (agent_id, created_at DESC);
CREATE INDEX idx_job_events_tenant ON job_events (tenant_id, created_at DESC);
CREATE INDEX idx_job_events_correlation ON job_events (correlation_id);
CREATE INDEX idx_job_events_status ON job_events (status) WHERE status IN ('pending','running');

-- Billing events (TimescaleDB hypertable)
CREATE TABLE billing_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    agent_id        UUID,
    job_id          UUID,
    event_type      VARCHAR(64) NOT NULL,  -- llm_tokens, tool_call, sandbox_seconds, storage_bytes
    quantity        BIGINT NOT NULL,
    unit_cost_nanos BIGINT NOT NULL,       -- USD * 1e9
    metadata        JSONB,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('billing_events', 'timestamp', chunk_time_interval => INTERVAL '1 hour');
```

---

## Implementation

### Worker Pool Architecture

```go
// Internal worker (runs in agent sandbox or sidecar)
type Worker struct {
    agentID       string
    redisClient   *redis.ClusterClient
    stateStore    StateStore
    objectStore   ObjectStore
    metrics       *prometheus.CounterVec
}

func (w *Worker) Run(ctx context.Context) error {
    for {
        // Claim job from consumer group
        streams, err := w.redisClient.XReadGroup(ctx, &redis.XReadGroupArgs{
            Group:    "agent-workers",
            Consumer: w.workerID,
            Streams:  []string{"jobs:" + w.agentID, ">"},
            Count:    1,
            Block:    5 * time.Second,
        }).Result()
        if err == redis.Nil { continue }
        if err != nil { return err }

        for _, stream := range streams {
            for _, msg := range stream.Messages {
                job := w.parseJob(msg.Values)
                result := w.processJob(ctx, job)
                
                // Atomic: commit state + ack job
                if err := w.commitAndAck(ctx, job, result); err != nil {
                    w.handleFailure(ctx, job, err)
                }
            }
        }
    }
}
```

### State Store Interface

```go
type StateStore interface {
    // Hot state (Redis)
    GetSession(ctx context.Context, agentID string) (*SessionState, error)
    SetSession(ctx context.Context, agentID string, state *SessionState, ttl time.Duration) error
    AppendHistory(ctx context.Context, agentID string, entry HistoryEntry, maxLen int) error
    GetJobResult(ctx context.Context, jobID string) (*JobResult, error)
    SetJobResult(ctx context.Context, jobID string, result *JobResult, ttl time.Duration) error

    // Warm state (S3)
    PutObject(ctx context.Context, key string, data io.Reader, size int64) (string, error) // returns presigned URL
    GetObject(ctx context.Context, key string) (io.ReadCloser, error)
    DeleteObject(ctx context.Context, key string) error

    // Cold state (PostgreSQL)
    RecordJobEvent(ctx context.Context, event *JobEvent) error
    RecordBillingEvent(ctx context.Context, event *BillingEvent) error
    QueryJobHistory(ctx context.Context, filter JobHistoryFilter) ([]*JobEvent, error)
}
```

### Idempotency Middleware (API Gateway)

```go
func IdempotencyMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        key := r.Header.Get("Idempotency-Key")
        if key == "" {
            next.ServeHTTP(w, r)
            return
        }

        // Check if already processed
        existing, err := redis.SetNX(ctx, "idempotency:"+key, "processing", 24*time.Hour).Result()
        if err != nil { http.Error(w, "internal error", 500); return }
        if !existing {
            // Return cached response
            cached, _ := redis.Get(ctx, "idempotency:response:"+key).Result()
            if cached != "" {
                w.Header().Set("X-Idempotency-Replay", "true")
                w.Write([]byte(cached))
                return
            }
            // Another request is processing - wait or return 409
            http.Error(w, "duplicate request in progress", 409)
            return
        }

        // Capture response
        rec := newResponseRecorder(w)
        next.ServeHTTP(rec, r)

        // Store response for replay
        redis.Set(ctx, "idempotency:response:"+key, rec.body.String(), 24*time.Hour)
        redis.Set(ctx, "idempotency:"+key, "done", 24*time.Hour)
    })
}
```

---

## Consequences

### Positive

- **Exactly-once:** Idempotency keys + consumer group ack + state commit atomicity
- **Durability:** Redis Streams persisted to AOF + RDB; replication across cluster
- **Scalability:** Consumer groups partition work across workers; horizontal scaling
- **Observability:** Built-in stream lag metrics (`XINFO GROUPS`), job latency histograms
- **Flexibility:** Priority, scheduling, retries, dead-letter all native to Streams
- **Cost-effective:** Single Redis Cluster handles queue + hot state + caching

### Negative

- **Redis dependency:** Single point of failure for queue (mitigated: cluster mode, multi-AZ)
- **Memory pressure:** Hot state in Redis requires sizing; eviction policy critical
- **Operational complexity:** Consumer group lag monitoring, stream trimming, AOF tuning
- **Large payloads:** Must offload to S3; adds latency for big outputs

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Redis OOM | `maxmemory-policy allkeys-lru`; separate cluster for queue vs state; monitoring alerts |
| Stream growth | `XTRIM MAXLEN ~ 10000` per stream; automated cleanup job for completed jobs >24h |
| Consumer group stall | Heartbeat metric `consumer.lag`; auto-rebalance on worker failure |
| Idempotency key collision | UUID v7 (timestamp + random); 128-bit space; 24h TTL |
| S3 latency | Presigned URLs; multipart for >5MB; CloudFront for frequent reads |
| Clock skew (scheduling) | NTP on all nodes; scheduler uses Redis time (not local) |

---

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Kafka / Redpanda | Overkill for per-agent queues; operational burden; no native consumer group ack + state commit atomicity |
| RabbitMQ | Less durable stream semantics; no built-in replay; heavier |
| SQS + DynamoDB | Vendor lock-in; no exactly-once without FIFO + deduplication table; cost at scale |
| Temporal / Cadence | Excellent for workflows, heavy for simple job queue; separate cluster |
| Custom DB queue | Redis Streams is purpose-built; reinventing = bugs |

---

## Related ADRs

- ADR-001: Agent Sandboxing Model (worker isolation)
- ADR-002: LLM Router Architecture (job type: llm_inference)
- ADR-004: Billing and Metering (consumes job_events, billing_events)

## References

- [Redis Streams Documentation](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis Consumer Groups](https://redis.io/docs/latest/develop/data-types/streams/consumer-groups/)
- [TimescaleDB Hypertables](https://docs.timescale.com/timescaledb/latest/how-to-guides/hypertables/)
- [MinIO Presigned URLs](https://min.io/docs/minio/linux/developers/go/presigned-url-operations.html)