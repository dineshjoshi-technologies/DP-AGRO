# ADR-003: Job Queue and State Persistence

## Status
Accepted

## Context
We need to design the job queue architecture for the multi-agent runtime. The system must provide durable execution, retries with exponential backoff, scheduling capabilities, state serialization, and exactly-once semantics for agent executions. This is the backbone that coordinates all agent work.

Key requirements:
- Durable job persistence (survive restarts/crashes)
- Retry logic with configurable policies (exponential backoff, max attempts)
- Scheduling (cron-like, delayed execution, recurring)
- State serialization for long-running agents (checkpoint/resume)
- Exactly-once execution semantics
- Horizontal scalability
- Observability (metrics, tracing, debugging)
- Dead letter queue for failed jobs

## Decision
We will implement a **Redis-backed job queue with PostgreSQL for durability** using the following architecture:

### Queue Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Job Queue System                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   API       │  │  Scheduler  │  │  Workers    │            │
│  │   Gateway   │  │  (cron,     │  │  (pool)     │            │
│  │             │  │   delayed)  │  │             │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                │                   │
│         ▼                ▼                ▼                   │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              Redis (Hot Queue)                      │     │
│  │  • Pending jobs (sorted set by priority/timestamp)  │     │
│  │  • Processing jobs (hash with TTL)                  │     │
│  │  • Delayed jobs (sorted set by execute_at)          │     │
│  │  • Dead letter queue (list)                         │     │
│  └────────────────────────┬────────────────────────────┘     │
│                           │                                   │
│         ┌─────────────────┼─────────────────┐                │
│         ▼                 ▼                 ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ PostgreSQL  │  │  Redis      │  │  Metrics/   │          │
│  │ (Durable    │  │  Streams    │  │  Tracing    │          │
│  │  Log)       │  │  (Events)   │  │             │          │
│  │             │  │             │  │             │          │
│  │ • Job       │  │ • Job       │  │ • Prometheus│          │
│  │   records   │  │   events    │  │ • OpenTelemetry     │
│  │ • State     │  │ • Worker    │  │ • Structured        │
│  │   snapshots │  │   heartbeats│  │   logging           │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Job Definition**
   ```go
   type Job struct {
       ID          string            `json:"id"`
       Type        string            `json:"type"`        // agent-execution, llm-call, etc.
       Payload     json.RawMessage   `json:"payload"`
       Priority    int               `json:"priority"`    // higher = more urgent
       Status      JobStatus         `json:"status"`
       CreatedAt   time.Time         `json:"created_at"`
       UpdatedAt   time.Time         `json:"updated_at"`
       ScheduledAt *time.Time        `json:"scheduled_at,omitempty"`
       StartedAt   *time.Time        `json:"started_at,omitempty"`
       CompletedAt *time.Time        `json:"completed_at,omitempty"`
       Attempts    int               `json:"attempts"`
       MaxAttempts int               `json:"max_attempts"`
       Timeout     time.Duration     `json:"timeout"`
       RetryPolicy RetryPolicy       `json:"retry_policy"`
       IdempotencyKey string         `json:"idempotency_key,omitempty"`
       Result      *JobResult        `json:"result,omitempty"`
       Error       string            `json:"error,omitempty"`
       Metadata    map[string]string `json:"metadata,omitempty"`
   }
   ```

2. **Retry Policy**
   ```go
   type RetryPolicy struct {
       MaxAttempts     int           `json:"max_attempts"`
       BaseDelay       time.Duration `json:"base_delay"`       // e.g., 1s
       MaxDelay        time.Duration `json:"max_delay"`        // e.g., 5m
       Multiplier      float64       `json:"multiplier"`       // e.g., 2.0 (exponential)
       Jitter          float64       `json:"jitter"`           // 0.0-1.0
       RetryableErrors []string      `json:"retryable_errors"` // error codes to retry
   }
   ```

3. **Job Statuses**
   - `pending` — queued, waiting for worker
   - `scheduled` — waiting for scheduled time
   - `processing` — worker has claimed job
   - `completed` — finished successfully
   - `failed` — exceeded max attempts
   - `dead_letter` — moved to DLQ after all retries exhausted
   - `cancelled` — manually cancelled

4. **Exactly-Once Semantics**
   - Idempotency keys on job submission
   - Redis SETNX for job claiming (atomic claim)
   - PostgreSQL unique constraint on idempotency_key
   - Worker heartbeats to detect stale claims
   - Optimistic locking with version field for updates

### Redis Data Structures

| Key Pattern | Type | Purpose |
|-------------|------|---------|
| `queue:pending` | Sorted Set | Jobs ready to process (score = priority + timestamp) |
| `queue:delayed` | Sorted Set | Jobs waiting for scheduled time (score = execute_at) |
| `queue:processing:{job_id}` | Hash | Active job data with TTL (heartbeat) |
| `queue:dead_letter` | List | Failed jobs after all retries |
| `queue:worker:{worker_id}` | Hash | Worker registration + heartbeat |
| `queue:locks:{job_id}` | String | Distributed lock for job claiming |

### PostgreSQL Schema

```sql
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(255) UNIQUE,
    type            VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    priority        INT DEFAULT 0,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_at    TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    attempts        INT DEFAULT 0,
    max_attempts    INT DEFAULT 3,
    timeout_seconds INT DEFAULT 300,
    retry_policy    JSONB,
    result          JSONB,
    error           TEXT,
    metadata        JSONB,
    version         INT DEFAULT 1  -- optimistic locking
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_scheduled ON jobs(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_jobs_idempotency ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE job_events (
    id          BIGSERIAL PRIMARY KEY,
    job_id      UUID NOT NULL REFERENCES jobs(id),
    event_type  VARCHAR(50) NOT NULL,  -- created, claimed, heartbeat, completed, failed, retried
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_events_job_id ON job_events(job_id);
```

### Worker Protocol

1. **Registration**: Worker registers in Redis with TTL (heartbeat)
2. **Claiming**: 
   - Lua script atomically pops from `queue:pending` and writes to `queue:processing`
   - Sets TTL on processing job (e.g., 5 min)
   - Returns job data to worker
3. **Heartbeat**: Worker updates TTL on processing job every 30s
4. **Completion**: Worker writes result, moves job to completed in PostgreSQL, removes from Redis
5. **Failure**: Worker increments attempts, re-queues with backoff or moves to DLQ

### Scheduling

- **Cron jobs**: Separate scheduler process evaluates cron expressions, enqueues jobs
- **Delayed jobs**: Added to `queue:delayed` with execute_at score; background mover promotes to pending
- **Recurring**: Cron scheduler creates new job instances per schedule

### State Serialization (Checkpoint/Resume)

For long-running agents:
- Agent periodically calls `Checkpoint(state)` API
- State serialized to JSON, stored in PostgreSQL `job_state` table
- On resume, job payload includes `resume_from_checkpoint: true` and `checkpoint_id`
- Worker restores state before continuing

```sql
CREATE TABLE job_checkpoints (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID NOT NULL REFERENCES jobs(id),
    state       JSONB NOT NULL,
    step        INT NOT NULL,          -- logical step number
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Configuration

```yaml
queue:
  redis:
    addr: "localhost:6379"
    pool_size: 50
    password: "${REDIS_PASSWORD}"
  postgres:
    dsn: "postgres://user:pass@localhost:5432/queue?sslmode=require"
    max_conns: 20
  worker:
    concurrency: 10
    heartbeat_interval: 30s
    job_ttl: 5m
    claim_timeout: 30s
  retry:
    default_max_attempts: 3
    default_base_delay: 1s
    default_max_delay: 5m
    default_multiplier: 2.0
    default_jitter: 0.1
  scheduler:
    enabled: true
    cron_poll_interval: 10s
    delayed_poll_interval: 5s
  dead_letter:
    max_size: 10000
    retention_days: 30
```

## Consequences

### Positive
- Redis provides high-throughput, low-latency queue operations
- PostgreSQL provides durability and queryability
- Exactly-once via idempotency keys and atomic claims
- Horizontal scaling via worker pools
- Rich observability via events table
- Flexible retry policies per job
- Checkpoint/resume for long-running agents

### Negative
- Two data stores to operate (Redis + PostgreSQL)
- Added complexity vs single-store solutions
- Clock synchronization required for delayed jobs
- Lua scripts for atomic operations add complexity

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Redis data loss on restart | Low | Medium | AOF persistence, replica promotion |
| Job stuck in processing | Medium | High | TTL + heartbeat monitor re-claims stale jobs |
| Duplicate execution | Low | High | Idempotency keys + atomic claim + version check |
| Queue backlog | Medium | Medium | Priority queue, autoscaling workers, backpressure |

## Alternatives Considered

1. **Redis only** — Simpler but no durable queryability, risk of data loss
2. **PostgreSQL only** (SKIP LOCKED) — Durable but lower throughput, no native delayed queue
3. **RabbitMQ** — Good features but operational overhead, less flexible scheduling
4. **Temporal/Cadence** — Full workflow engine, overkill for job queue
5. **BullMQ (Node.js)** — Good but language-specific, we need Go

## Implementation Plan

1. **Week 1**: Core queue (Redis + PostgreSQL), job CRUD, basic worker
2. **Week 2**: Retry logic, exponential backoff, dead letter queue
3. **Week 3**: Scheduling (cron, delayed), worker pool management
4. **Week 4**: State serialization/checkpoint, exactly-once semantics
5. **Week 5**: Metrics, tracing, admin API, integration tests
6. **Week 6**: Load testing, chaos testing, documentation

## References

- Redis Sorted Sets: https://redis.io/docs/data-types/sorted-sets/
- PostgreSQL SKIP LOCKED: https://www.postgresql.org/docs/current/explicit-locking.html
- BullMQ: https://docs.bullmq.io/
- Temporal: https://temporal.io/