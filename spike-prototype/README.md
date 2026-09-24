# DJ Tech Agent Orchestration Runtime

This is the spike prototype for the DJ Tech multi-agent orchestration runtime, implementing the architecture defined in ADR-001, ADR-002, and ADR-003.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Service                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Sandbox    │  │  Executor   │  │  Billing    │             │
│  │  Manager    │◀─│             │──│  Tracker    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              External Services                       │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│  │  │ Containerd│  │ LLM      │  │ LLM      │          │       │
│  │  │ + gVisor │  │ Router   │  │ Gateway  │          │       │
│  │  └──────────┘  └──────────┘  └──────────┘          │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │       │
│  │  │ Redis    │  │PostgreSQL│  │ Billing  │          │       │
│  │  │ (Queue)  │  │ (Durable)│  │ Webhook  │          │       │
│  │  └──────────┘  └──────────┘  └──────────┘          │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Sandbox Manager (`orchestration/sandbox/`)
- Manages gVisor sandboxes via containerd
- Creates, monitors, and terminates agent sandboxes
- Enforces resource limits (CPU, memory, disk, network)
- Collects resource usage for billing

### 2. Agent Executor (`orchestration/executor/`)
- Integrates job queue, LLM router, LLM gateway, and sandbox
- Executes agent code in sandboxed environments
- Handles LLM calls through the router/gateway
- Manages checkpoint/resume for long-running agents

### 3. Billing Tracker (`orchestration/billing/`)
- Tracks resource usage (CPU, memory, LLM tokens)
- Calculates costs based on configurable pricing
- Sends billing events to webhook endpoint
- Provides usage statistics and reporting

### 4. LLM Router (`llm-router/`)
- Provider-agnostic LLM routing (OpenAI, Anthropic, Ollama, etc.)
- Intelligent model selection based on cost, quality, latency
- Fallback chains for reliability
- Cost tracking and streaming support

### 5. LLM Gateway (`llm-gateway/`)
- Security proxy for LLM API calls from sandboxes
- Model allowlist, token budgets, rate limiting
- PII detection and redaction
- Audit logging

### 6. Job Queue (`job-queue/`)
- Redis-backed queue with PostgreSQL durability
- Retry logic with exponential backoff
- Scheduling (cron, delayed, recurring)
- Exactly-once semantics via idempotency keys
- Checkpoint/resume for long-running agents

## Quick Start

### Prerequisites
- Docker and Docker Compose
- containerd with gVisor (runsc) runtime
- API keys for LLM providers (OpenAI, Anthropic)

### 1. Build Agent Base Image
```bash
docker build -t djtech/agent-base:latest -f spike-prototype/config/Dockerfile.agent-base .
```

### 2. Set Environment Variables
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### 3. Start the Stack
```bash
cd spike-prototype
docker-compose up -d
```

### 4. Test Agent Execution
```bash
curl -X POST http://localhost:8082/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent-1",
    "agent_type": "python",
    "code": "print(\"Hello from sandbox!\")",
    "timeout": "60s"
  }'
```

### 5. Check Metrics and Billing
```bash
# Orchestration metrics
curl http://localhost:8082/metrics

# Billing usage
curl http://localhost:8082/v1/billing/usage

# LLM Router health
curl http://localhost:8081/health

# LLM Gateway health
curl http://localhost:8080/health
```

## Configuration

All configuration is done via JSON files with environment variable expansion:

- `orchestration/config/config.json` - Main orchestration config
- `llm-router/config/router-config.json` - LLM router config
- `llm-gateway/config.json` - LLM gateway config

Environment variables use `${VAR_NAME:-default}` syntax.

## API Endpoints

### Orchestration Service (port 8082)
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `POST /v1/agents/execute` - Execute an agent
- `GET /v1/billing/usage` - Billing usage stats

### LLM Router (port 8081)
- `GET /health` - Health check
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Chat completions (OpenAI-compatible)

### LLM Gateway (port 8080)
- `GET /health` - Health check
- `GET /metrics` - Gateway metrics
- `POST /v1/chat/completions` - Proxied chat completions

## ADR References

- [ADR-001: Agent Sandboxing Model](ADR-001-agent-sandboxing-model.md)
- [ADR-002: LLM Router and Model Selection](ADR-002-llm-router-model-selection.md)
- [ADR-003: Job Queue and State Persistence](ADR-003-job-queue-state-persistence.md)

## Smoke Tests

Run all smoke tests:
```bash
./spike-prototype/scripts/smoke-test.sh
./spike-prototype/scripts/smoke-test-llm-router.sh
./spike-prototype/scripts/smoke-test-orchestration.sh
```

## Next Steps

1. **Production hardening**: TLS, authentication, rate limiting
2. **Multi-node support**: Distributed sandbox managers, queue sharding
3. **Advanced scheduling**: Priority queues, resource-aware scheduling
4. **Observability**: Distributed tracing, structured logging, alerting
5. **Security**: Enhanced eBPF policies, seccomp profiles, admission control