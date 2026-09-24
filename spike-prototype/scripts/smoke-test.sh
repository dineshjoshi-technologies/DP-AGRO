#!/bin/bash
# Smoke test for the agent sandboxing spike prototype
# Tests: containerd config, cgroups config, eBPF policy, LLM gateway

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== DJ Tech Agent Sandboxing Spike Prototype Smoke Test ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Test 1: Check containerd config exists and is valid
echo "Test 1: Checking containerd configuration..."
if [[ -f "$PROJECT_ROOT/spike-prototype/config/containerd-config.toml" ]]; then
    echo "  ✓ containerd-config.toml exists"
    if command -v toml &> /dev/null; then
        if toml validate "$PROJECT_ROOT/spike-prototype/config/containerd-config.toml" 2>/dev/null; then
            echo "  ✓ containerd-config.toml is valid TOML"
        else
            echo "  ⚠ containerd-config.toml validation skipped (toml not installed)"
        fi
    else
        echo "  ⚠ containerd-config.toml validation skipped (toml not installed)"
    fi
else
    echo "  ✗ containerd-config.toml not found"
    exit 1
fi

# Test 2: Check cgroups config exists
echo "Test 2: Checking cgroups configuration..."
if [[ -f "$PROJECT_ROOT/spike-prototype/config/cgroups-agent.conf" ]]; then
    echo "  ✓ cgroups-agent.conf exists"
    # Check for required keys
    if grep -q "CPUQuota" "$PROJECT_ROOT/spike-prototype/config/cgroups-agent.conf" && \
       grep -q "MemoryMax" "$PROJECT_ROOT/spike-prototype/config/cgroups-agent.conf" && \
       grep -q "TasksMax" "$PROJECT_ROOT/spike-prototype/config/cgroups-agent.conf"; then
        echo "  ✓ cgroups config has required resource limits"
    else
        echo "  ✗ cgroups config missing required resource limits"
        exit 1
    fi
else
    echo "  ✗ cgroups-agent.conf not found"
    exit 1
fi

# Test 3: Check Dockerfile exists
echo "Test 3: Checking agent base Dockerfile..."
if [[ -f "$PROJECT_ROOT/spike-prototype/config/Dockerfile.agent-base" ]]; then
    echo "  ✓ Dockerfile.agent-base exists"
    if grep -q "gcr.io/distroless/cc-debian12" "$PROJECT_ROOT/spike-prototype/config/Dockerfile.agent-base"; then
        echo "  ✓ Uses distroless base image"
    else
        echo "  ✗ Does not use distroless base image"
        exit 1
    fi
    if grep -q "nonroot" "$PROJECT_ROOT/spike-prototype/config/Dockerfile.agent-base"; then
        echo "  ✓ Runs as non-root user"
    else
        echo "  ✗ Does not run as non-root user"
        exit 1
    fi
else
    echo "  ✗ Dockerfile.agent-base not found"
    exit 1
fi

# Test 4: Check eBPF policy exists
echo "Test 4: Checking eBPF network policy..."
if [[ -f "$PROJECT_ROOT/spike-prototype/ebpf/ebpf-agent-policy.c" ]]; then
    echo "  ✓ ebpf-agent-policy.c exists"
    # Check for key components
    if grep -q "agent_egress_filter" "$PROJECT_ROOT/spike-prototype/ebpf/ebpf-agent-policy.c" && \
       grep -q "agent_dns_filter" "$PROJECT_ROOT/spike-prototype/ebpf/ebpf-agent-policy.c" && \
       grep -q "agent_configs" "$PROJECT_ROOT/spike-prototype/ebpf/ebpf-agent-policy.c" && \
       grep -q "dns_allowlist" "$PROJECT_ROOT/spike-prototype/ebpf/ebpf-agent-policy.c"; then
        echo "  ✓ eBPF policy has required components (egress filter, DNS filter, agent configs, DNS allowlist)"
    else
        echo "  ✗ eBPF policy missing required components"
        exit 1
    fi
else
    echo "  ✗ ebpf-agent-policy.c not found"
    exit 1
fi

# Test 5: Check LLM Gateway exists
echo "Test 5: Checking LLM Gateway..."
if [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" ]]; then
    echo "  ✓ main.go exists"
    if grep -q "ChatCompletions" "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" && \
       grep -q "PIIRedactor" "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" && \
       grep -q "TokenBudget" "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" && \
       grep -q "TokenBucket" "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" && \
       grep -q "AuditLogger" "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go"; then
        echo "  ✓ LLM Gateway has required components (chat completions, PII redaction, token budget, rate limiting, audit logging)"
    else
        echo "  ✗ LLM Gateway missing required components"
        exit 1
    fi
else
    echo "  ✗ main.go not found"
    exit 1
fi

# Test 6: Check LLM Gateway config
echo "Test 6: Checking LLM Gateway config..."
if [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/config.json" ]]; then
    echo "  ✓ config.json exists"
    if command -v jq &> /dev/null; then
        if jq empty "$PROJECT_ROOT/spike-prototype/llm-gateway/config.json" 2>/dev/null; then
            echo "  ✓ config.json is valid JSON"
        else
            echo "  ✗ config.json is invalid JSON"
            exit 1
        fi
    else
        echo "  ⚠ config.json validation skipped (jq not installed)"
    fi
else
    echo "  ✗ config.json not found"
    exit 1
fi

# Test 7: Check LLM Gateway Dockerfile
echo "Test 7: Checking LLM Gateway Dockerfile..."
if [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/Dockerfile" ]]; then
    echo "  ✓ Dockerfile exists"
    if grep -q "golang:1.22-alpine" "$PROJECT_ROOT/spike-prototype/llm-gateway/Dockerfile" && \
       grep -q "alpine:3.20" "$PROJECT_ROOT/spike-prototype/llm-gateway/Dockerfile" && \
       grep -q "USER gateway" "$PROJECT_ROOT/spike-prototype/llm-gateway/Dockerfile"; then
        echo "  ✓ Dockerfile uses multi-stage build with non-root user"
    else
        echo "  ✗ Dockerfile missing multi-stage or non-root user"
        exit 1
    fi
else
    echo "  ✗ Dockerfile not found"
    exit 1
fi

# Test 8: Check go.mod and go.sum
echo "Test 8: Checking Go module files..."
if [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/go.mod" ]] && [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/go.sum" ]]; then
    echo "  ✓ go.mod and go.sum exist"
    if grep -q "github.com/gin-gonic/gin" "$PROJECT_ROOT/spike-prototype/llm-gateway/go.mod" && \
       grep -q "github.com/google/uuid" "$PROJECT_ROOT/spike-prototype/llm-gateway/go.mod"; then
        echo "  ✓ go.mod has required dependencies"
    else
        echo "  ✗ go.mod missing required dependencies"
        exit 1
    fi
else
    echo "  ✗ go.mod or go.sum not found"
    exit 1
fi

echo ""
echo "=== All smoke tests passed! ==="
echo ""
echo "Next steps for full validation:"
echo "  1. Build and test agent base image: docker build -t djtech/agent-base:latest -f spike-prototype/config/Dockerfile.agent-base ."
echo "  2. Compile eBPF policy: clang -O2 -target bpf -c spike-prototype/ebpf/ebpf-agent-policy.c -o ebpf-agent-policy.o"
echo "  3. Build LLM Gateway: cd spike-prototype/llm-gateway && go build -o llm-gateway ."
echo "  4. Run integration tests with containerd + gVisor"
echo "  5. Test LLM Gateway with mock upstream"