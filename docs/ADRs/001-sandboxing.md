# ADR-001: Agent Sandboxing Model

**Status:** Accepted
**Date:** 2026-09-16
**Author:** DJ Tech Engineering

## Context

The multi-agent runtime requires a sandboxing model to safely execute untrusted agent code, enforce resource limits, and isolate agents from each other and the host system. This ADR documents the decision for the sandboxing architecture.

## Decision

We will use **gVisor (runsc)** as the primary sandboxing layer, with **Kata Containers** as a fallback for workloads requiring full VM isolation. The sandboxing model consists of three layers:

### Layer 1: Process-Level Isolation (Default)
- **Technology:** gVisor (runsc) with `runsc` runtime
- **Isolation:** Syscall interception, no host kernel access
- **Use case:** Most agent workloads (LLM inference, tool execution, data processing)
- **Resource limits:** CPU shares, memory limits, pids limit via cgroups v2

### Layer 2: VM-Level Isolation (High-Security Workloads)
- **Technology:** Kata Containers (QEMU + virtio-fs)
- **Isolation:** Full VM with dedicated kernel
- **Use case:** Agents handling sensitive data, untrusted third-party code, regulatory compliance
- **Resource limits:** Dedicated vCPU, memory balloon, block device limits

### Layer 3: Host-Native (Trusted System Components)
- **Technology:** Native container runtime (crun/runc)
- **Isolation:** Standard Linux namespaces + cgroups
- **Use case:** Control plane components, infrastructure agents, monitoring
- **Resource limits:** Standard cgroups v2 limits

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Runtime Host                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  gVisor Pod  │  │  Kata Pod    │  │  Native Pod        │  │
│  │  (Layer 1)   │  │  (Layer 2)   │  │  (Layer 3)         │  │
│  ├──────────────┤  ├──────────────┤  ├────────────────────┤  │
│  │ Agent A      │  │ Agent B      │  │ Control Plane      │  │
│  │ Agent C      │  │ (sensitive)  │  │ Infra Agents       │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
│         │                │                   │                │
│         ▼                ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Kubernetes / Nomad Cluster               │   │
│  │  • RuntimeClass: gvisor, kata, native                 │   │
│  │  • ResourceQuota per agent tenant                     │   │
│  │  • NetworkPolicy: deny-all by default                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Security Model

### Isolation Boundaries

| Boundary | Layer 1 (gVisor) | Layer 2 (Kata) | Layer 3 (Native) |
|----------|------------------|----------------|------------------|
| Kernel access | Intercepted (Sentry) | Own kernel | Host kernel |
| Filesystem | Virtual FS (gofer) | Virtio-fs + 9p | Host mounts |
| Network | Sandboxed netstack | VM network ns | Host network ns |
| Devices | Emulated / passthrough | Virtio devices | Direct (with rules) |
| Ptrace | Blocked | Blocked | Allowed (same pod) |

### Resource Limits (Per Agent)

```yaml
# Default resource profile for Layer 1 agents
resources:
  limits:
    cpu: "2000m"        # 2 vCPU equivalent
    memory: "4Gi"
    ephemeral-storage: "10Gi"
    pids: 1024
  requests:
    cpu: "100m"
    memory: "512Mi"
```

### Network Policy

- **Default:** Deny all ingress/egress
- **Allowlist:** Explicit `NetworkPolicy` per agent for required dependencies
- **Service mesh:** Istio sidecar for mTLS and observability (Layer 1/2 only)
- **Egress gateway:** Controlled internet access via egress gateway with allowlist

### Inter-Agent Communication

- **Primary:** gRPC over mTLS via service mesh (Istio)
- **Message bus:** NATS JetStream with per-agent subjects and JWT auth
- **Shared state:** Redis Cluster with ACL per agent tenant
- **File exchange:** S3-compatible object store with presigned URLs
- **Prohibited:** Direct filesystem access, shared memory, Unix domain sockets across sandboxes

## Implementation

### RuntimeClass Definitions

```yaml
# gVisor RuntimeClass
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc

---
# Kata RuntimeClass
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata
handler: kata

---
# Native RuntimeClass
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: native
handler: runc
```

### Agent Pod Template

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: agent-{agent-id}
  labels:
    agent-id: "{agent-id}"
    sandbox-layer: "gvisor"  # or kata, native
spec:
  runtimeClassName: gvisor
  securityContext:
    runAsNonRoot: true
    runAsUser: 10000
    fsGroup: 10000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: agent
    image: djtech/agent-runtime:{version}
    resources:
      limits:
        cpu: "2000m"
        memory: "4Gi"
      requests:
        cpu: "100m"
        memory: "512Mi"
    env:
    - name: AGENT_ID
      value: "{agent-id}"
    - name: SANDBOX_LAYER
      value: "gvisor"
    volumeMounts:
    - name: agent-workspace
      mountPath: /workspace
  volumes:
  - name: agent-workspace
    emptyDir:
      sizeLimit: 10Gi
```

### Admission Control

- **Kyverno policy:** Mutate pods to inject correct `runtimeClassName` based on agent security tier
- **Validation:** Reject pods without valid sandbox layer label
- **Defaults:** Layer 1 (gVisor) for all new agents unless explicitly upgraded

## Consequences

### Positive

- **Strong isolation:** gVisor blocks ~100% of host kernel exploits; Kata provides hardware-level isolation
- **Performance:** gVisor adds ~5-15% overhead vs native; acceptable for most agent workloads
- **Compatibility:** OCI-compatible; works with standard Kubernetes tooling
- **Graduated security:** Three tiers allow cost/performance tradeoffs per agent

### Negative

- **gVisor limitations:** No GPU passthrough (use Kata for GPU workloads); some syscalls unsupported
- **Kata overhead:** ~100-200ms cold start; higher memory footprint (~100MB base)
- **Complexity:** Three runtime classes require node configuration and runtime installation
- **Debugging:** Limited ptrace/kernel debugging in sandboxed layers

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| gVisor syscall gaps break agents | Comprehensive CI testing; fallback to Kata for incompatible workloads |
| Kata cold start latency | Pre-warmed VM pool; firecracker microVM for faster start |
| Resource exhaustion | Per-agent ResourceQuota; cluster autoscaler with sandbox-aware scheduling |
| Supply chain compromise | Signed container images; SBOM verification; runtime admission checks |

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Firecracker microVMs (direct) | Higher operational complexity; Kata provides same with Kubernetes integration |
| Wasm/WASI (wasmtime) | Immature ecosystem for general-purpose agent workloads; limited syscall support |
| Kata only (no gVisor) | Unnecessary overhead for trusted/low-risk agents; 10x memory cost |
| Native only (namespaces) | Insufficient isolation for multi-tenant untrusted code execution |
| gVisor only (no Kata) | No path for GPU workloads or regulatory-required VM isolation |

## Related ADRs

- ADR-002: LLM Router Architecture (pending)
- ADR-003: Job Queue and State Persistence (pending)
- ADR-004: Billing and Metering (pending)

## References

- [gVisor Architecture](https://gvisor.dev/docs/architecture/)
- [Kata Containers Documentation](https://katacontainers.io/documentation/)
- [Kubernetes RuntimeClass](https://kubernetes.io/docs/concepts/containers/runtime-class/)
- [Kyverno Policy Engine](https://kyverno.io/)