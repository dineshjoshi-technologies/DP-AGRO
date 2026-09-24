# ADR-001: Agent Sandboxing Model

## Status
Accepted

## Context
We need to define the sandboxing architecture for the multi-agent runtime. The system will execute untrusted agent code from customers and must provide strong isolation guarantees while maintaining performance and developer experience.

Key requirements:
- Process isolation between agents
- Resource limits (CPU, memory, disk, network)
- Network egress controls (allowlist/denylist)
- LLM tool-use boundaries
- Fast startup times for serverless-style execution
- Support for long-running agents (hours to days)

## Decision
We will use **gVisor (runsc)** as the primary sandboxing layer with the following architecture:

### Sandbox Layers

1. **gVisor Container Runtime** (Primary isolation)
   - User-space kernel implementing Linux syscall interface
   - No host kernel access — strong isolation boundary
   - Compatible with OCI container images
   - Lower overhead than VMs, stronger isolation than namespaces

2. **Containerd + CRI-O** (Container management)
   - Pull, unpack, and manage container images
   - gVisor runtime handler via runsc
   - Image layer caching for fast cold starts

3. **cgroups v2** (Resource enforcement)
   - CPU quota/period, memory max, pids max
   - Disk I/O limits via blkio
   - Unified hierarchy for cleaner delegation

4. **Network Namespace + eBPF/Cilium** (Network controls)
   - Per-agent network namespace
   - eBPF programs for L4/L7 allowlist enforcement
   - DNS filtering via CoreDNS plugin
   - Default-deny egress; explicit allowlist per agent

5. **Custom LLM Gateway Proxy** (Tool-use boundaries)
   - Intercepts all LLM API calls from sandboxed agents
   - Enforces token budgets, model allowlists, rate limits
   - Redacts PII from prompts/responses
   - Audit logging of all tool invocations

### Agent Execution Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Host Node                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              containerd / CRI-O                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │  Agent A    │  │  Agent B    │  │  Agent C    │  │   │
│  │  │  (gVisor)   │  │  (gVisor)   │  │  (gVisor)   │  │   │
│  │  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │  │   │
│  │  │  │cgroups│  │  │  │cgroups│  │  │  │cgroups│  │  │   │
│  │  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │  │   │
│  │  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │  │   │
│  │  │  │net ns │  │  │  │net ns │  │  │  │net ns │  │  │   │
│  │  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              LLM Gateway Proxy (sidecar)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Resource Limits (Default, Configurable Per-Agent)

| Resource | Default Limit | Configuration |
|----------|---------------|---------------|
| CPU | 1000m (1 core) | `cpu_quota_us` / `cpu_period_us` |
| Memory | 512 MiB | `memory.max` |
| PIDs | 256 | `pids.max` |
| Disk | 1 GiB (ephemeral) | OverlayFS with quota |
| Network egress | Deny all | eBPF allowlist |
| Execution time | 24 hours | Runtime watchdog |

### Image Strategy

- **Base image**: `gcr.io/distroless/cc-debian12` (minimal, no shell)
- **Language runtimes**: Pre-baked layers for Python, Node.js, Go, Rust
- **Customer code**: Mounted as read-only layer at `/workspace`
- **Secrets**: Injected via tmpfs at `/secrets` (no disk persistence)

### Tool-Use Boundary Enforcement

The LLM Gateway Proxy enforces:

1. **Model allowlist**: Only approved models (e.g., `gpt-4o`, `claude-3.5-sonnet`)
2. **Token budgets**: Per-agent, per-request, per-day limits
3. **Tool schemas**: JSON Schema validation on all function calls
4. **PII redaction**: Regex + ML-based detection on prompts/responses
5. **Audit log**: Structured JSONL to CloudWatch/Cloud Logging

### Spike Prototype

A minimal prototype will validate:
- gVisor + containerd integration on target cloud (AWS/GCP)
- Cold start latency < 2s for warm images
- Memory overhead < 50 MiB per sandbox
- eBPF network policy enforcement
- LLM proxy interception and budget enforcement

## Consequences

### Positive
- Strong isolation without VM overhead
- OCI ecosystem compatibility (images, registries, tooling)
- Fine-grained resource control via cgroups v2
- Programmable network policies via eBPF
- Extensible LLM gateway for future tool types

### Negative
- gVisor syscall coverage gaps (some syscalls unimplemented)
- Added complexity vs. plain containers
- eBPF requires kernel 5.10+ (modern distros only)
- LLM proxy adds latency (~10-50ms per request)

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| gVisor syscall gaps break customer code | Medium | High | Test suite with common workloads; fallback to Firecracker VM for incompatible workloads |
| eBPF kernel version incompatibility | Low | Medium | Pin kernel version in AMI; CI test on target kernels |
| LLM proxy becomes bottleneck | Low | High | Horizontal scaling; async buffering; local token counting |

## Alternatives Considered

1. **Firecracker MicroVMs** — Stronger isolation, but higher memory overhead (~100MiB base) and slower cold starts (~150ms vs ~50ms). Chosen for workloads that fail gVisor compatibility.

2. **Plain containers (runc + namespaces)** — Lower overhead, but weaker isolation (shared kernel). Rejected for multi-tenant untrusted code.

3. **WASM/WASI (wasmtime, wasmedge)** — Fast startup, strong capability model. Rejected due to immature ecosystem for general-purpose agent workloads (no native threading, limited syscalls, no GPU).

4. **Kata Containers** — VM-based, similar to Firecracker. More mature but heavier. Considered as gVisor fallback.

## Implementation Plan

1. **Week 1**: gVisor + containerd PoC on single node
2. **Week 2**: cgroups v2 resource limits + network namespace isolation
3. **Week 3**: eBPF network policy enforcement (Cilium)
4. **Week 4**: LLM Gateway Proxy v1 (token budgets, model allowlist)
5. **Week 5**: Integration testing + CI pipeline
6. **Week 6**: Documentation + runbooks

## References

- gVisor Architecture: https://gvisor.dev/docs/architecture/
- cgroups v2: https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
- Cilium eBPF: https://cilium.io/eBPF/
- Firecracker: https://firecracker-microvm.github.io/