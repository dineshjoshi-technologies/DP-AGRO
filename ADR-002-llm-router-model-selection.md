# ADR-002: LLM Router and Model Selection

## Status
Accepted

## Context
We need to design the LLM routing layer for the multi-agent runtime. The system must support multiple LLM providers, intelligent model selection based on task requirements, fallback chains for reliability, cost optimization, and streaming support. This is a critical component that sits between agents and LLM providers.

Key requirements:
- Provider abstraction (OpenAI, Anthropic, local models, etc.)
- Model selection logic based on task type, cost, latency, quality
- Fallback chains for reliability
- Cost tracking and optimization
- Streaming support for real-time responses
- Token budget enforcement per agent
- Request/response transformation for provider compatibility

## Decision
We will implement a **provider-agnostic LLM router** with the following architecture:

### Router Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLM Router                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Request    │  │  Model      │  │  Provider   │            │
│  │  Normalizer │──▶│  Selector   │──▶│  Adapter    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│        │                │                │                     │
│        ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Schema     │  │  Cost/      │  │  Fallback   │            │
│  │  Translator │  │  Latency    │  │  Manager    │            │
│  │             │  │  Tracker    │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **Request Normalizer**
   - Converts incoming requests to canonical internal format
   - Handles OpenAI, Anthropic, and custom schemas
   - Validates required fields, applies defaults

2. **Model Selector**
   - Scores models based on: task type, quality requirements, cost, latency
   - Supports routing rules (e.g., "use cheapest for summarization", "use best for code")
   - Considers agent token budgets and rate limits

3. **Provider Adapters**
   - One adapter per provider (OpenAI, Anthropic, Ollama, etc.)
   - Handles auth, request/response translation, streaming
   - Implements provider-specific quirks and features

4. **Cost/Latency Tracker**
   - Tracks per-request and aggregate costs
   - Maintains latency percentiles per model
   - Feeds data back to Model Selector for optimization

5. **Fallback Manager**
   - Configurable fallback chains per model/task
   - Automatic retry with exponential backoff
   - Circuit breaker for failing providers

6. **Schema Translator**
   - Bidirectional translation between canonical format and provider formats
   - Handles tool/function calling schema differences
   - Streaming chunk normalization

### Model Selection Algorithm

```
score(model) = w_quality * quality_score(task, model)
             + w_cost    * (1 - normalized_cost(model))
             + w_latency * (1 - normalized_latency(model))
             + w_budget  * budget_fit(agent, model)
```

Weights configurable per agent/project. Default: quality=0.5, cost=0.3, latency=0.1, budget=0.1.

### Provider Support Matrix

| Provider | Models | Streaming | Tools | Vision | Auth |
|----------|--------|-----------|-------|--------|------|
| OpenAI | GPT-4o, GPT-4o-mini, GPT-3.5 | ✓ | ✓ | ✓ | API Key |
| Anthropic | Claude 3.5 Sonnet, Haiku, Opus | ✓ | ✓ | ✓ | API Key |
| Ollama | Llama 3, Mistral, CodeLlama | ✓ | ✗ | ✗ | Local |
| vLLM | Any HF model | ✓ | ✓ | ✓ | API Key |
| Bedrock | Claude, Titan, Llama | ✓ | ✓ | ✓ | AWS IAM |

### Configuration

```yaml
router:
  default_model: "gpt-4o-mini"
  selection:
    weights:
      quality: 0.5
      cost: 0.3
      latency: 0.1
      budget: 0.1
  fallbacks:
    gpt-4o: ["claude-3.5-sonnet", "gpt-4o-mini"]
    claude-3.5-sonnet: ["gpt-4o", "gpt-4o-mini"]
    default: ["gpt-4o-mini"]
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"
      base_url: "https://api.openai.com/v1"
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      base_url: "https://api.anthropic.com/v1"
    ollama:
      base_url: "http://localhost:11434/v1"
```

### Cost Model

| Model | Input $/1M | Output $/1M | Quality Tier | Latency Tier |
|-------|------------|-------------|--------------|--------------|
| GPT-4o | $5.00 | $15.00 | Premium | Medium |
| GPT-4o-mini | $0.15 | $0.60 | High | Fast |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Premium | Medium |
| Claude 3.5 Haiku | $0.25 | $1.25 | High | Fast |
| Llama 3 70B (self-hosted) | $0.00* | $0.00* | High | Slow |

*Excludes infrastructure costs

### Streaming Implementation

- Server-Sent Events (SSE) for all providers
- Unified chunk format: `{ delta: string, finish_reason?: string, usage?: Usage }`
- Backpressure handling via buffered channels
- Automatic fallback on stream failure (retry from last checkpoint)

### Token Budget Integration

- Integrates with LLM Gateway (ADR-001) for per-agent budgets
- Pre-flight check: estimates tokens, rejects if over budget
- Post-flight: records actual usage, updates remaining budget

## Consequences

### Positive
- Single interface for all LLM providers
- Intelligent cost/quality optimization
- Resilient with automatic fallbacks
- Extensible for new providers
- Streaming support out of the box

### Negative
- Added latency (~10-20ms) for routing logic
- Complexity in schema translation
- Need to maintain provider adapters

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Provider API changes break adapter | Medium | High | Version pinning, integration tests, adapter interface contracts |
| Cost tracking inaccurate | Low | Medium | Per-request verification, periodic reconciliation |
| Fallback loops | Low | High | Circuit breakers, max retry limits, dead letter queue |

## Alternatives Considered

1. **Direct provider calls** — Simpler but no fallback, no cost optimization, vendor lock-in
2. **LiteLLM proxy** — Good proxy but less control over selection logic, added dependency
3. **LangChain/LlamaIndex router** — Heavy framework, overkill for routing only

## Implementation Plan

1. **Week 1**: Core router + Request Normalizer + OpenAI adapter
2. **Week 2**: Anthropic adapter + Schema Translator + Streaming
3. **Week 3**: Model Selector with scoring + Cost/Latency Tracker
4. **Week 4**: Fallback Manager + Circuit Breaker + Ollama adapter
5. **Week 5**: Configuration system + Integration tests
6. **Week 6**: Documentation + Benchmarks + Load testing

## References

- OpenAI API: https://platform.openai.com/docs/api-reference
- Anthropic API: https://docs.anthropic.com/claude/reference
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- LiteLLM: https://github.com/BerriAI/litellm