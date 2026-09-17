#!/bin/bash
# Smoke test for the Orchestration spike prototype
# Tests: orchestration main, sandbox manager, executor, billing, config

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ORCH_DIR="$PROJECT_ROOT/spike-prototype/orchestration"

echo "=== DJ Tech Orchestration Spike Prototype Smoke Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Orchestration dir: $ORCH_DIR"
echo ""

# Test 1: Check orchestration main exists
echo "Test 1: Checking orchestration main entry point..."
if [[ -f "$ORCH_DIR/main.go" ]]; then
    echo "  ✓ main.go exists"
    if grep -q "sandbox.NewManager" "$ORCH_DIR/main.go" && \
       grep -q "executor.NewExecutor" "$ORCH_DIR/main.go" && \
       grep -q "billing.NewTracker" "$ORCH_DIR/main.go" && \
       grep -q "createHandler" "$ORCH_DIR/main.go"; then
        echo "  ✓ Main has required components (sandbox, executor, billing, HTTP)"
    else
        echo "  ✗ Main missing required components"
        exit 1
    fi
else
    echo "  ✗ main.go not found"
    exit 1
fi

# Test 2: Check orchestration config
echo "Test 2: Checking orchestration configuration..."
if [[ -f "$ORCH_DIR/config/config.go" ]]; then
    echo "  ✓ config.go exists"
    if grep -q "SandboxConfig" "$ORCH_DIR/config/config.go" && \
       grep -q "ExecutorConfig" "$ORCH_DIR/config/config.go" && \
       grep -q "BillingConfig" "$ORCH_DIR/config/config.go" && \
       grep -q "OrchestrationConfig" "$ORCH_DIR/config/config.go"; then
        echo "  ✓ Config has required structures"
    else
        echo "  ✗ Config missing required structures"
        exit 1
    fi
else
    echo "  ✗ config.go not found"
    exit 1
fi

if [[ -f "$ORCH_DIR/config/config.json" ]]; then
    echo "  ✓ config.json exists"
    if command -v jq &> /dev/null; then
        if jq empty "$ORCH_DIR/config/config.json" 2>/dev/null; then
            echo "  ✓ config.json is valid JSON"
            if jq -e '.sandbox and .executor and .billing' "$ORCH_DIR/config/config.json" >/dev/null; then
                echo "  ✓ config.json has required sections"
            else
                echo "  ✗ config.json missing required sections"
                exit 1
            fi
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

# Test 3: Check sandbox manager
echo "Test 3: Checking sandbox manager..."
if [[ -f "$ORCH_DIR/sandbox/manager.go" ]]; then
    echo "  ✓ manager.go exists"
    if grep -q "CreateSandbox" "$ORCH_DIR/sandbox/manager.go" && \
       grep -q "TerminateSandbox" "$ORCH_DIR/sandbox/manager.go" && \
       grep -q "WaitSandbox" "$ORCH_DIR/sandbox/manager.go" && \
       grep -q "CollectResources" "$ORCH_DIR/sandbox/manager.go" && \
       grep -q "containerd" "$ORCH_DIR/sandbox/manager.go" && \
       grep -q "gVisor\|runsc" "$ORCH_DIR/sandbox/manager.go"; then
        echo "  ✓ Sandbox manager has required methods (create, terminate, wait, collect, containerd, gVisor)"
    else
        echo "  ✗ Sandbox manager missing required components"
        exit 1
    fi
else
    echo "  ✗ manager.go not found"
    exit 1
fi

# Test 4: Check executor
echo "Test 4: Checking agent executor..."
if [[ -f "$ORCH_DIR/executor/executor.go" ]]; then
    echo "  ✓ executor.go exists"
    if grep -q "Execute" "$ORCH_DIR/executor/executor.go" && \
       grep -q "handleAgentExecution" "$ORCH_DIR/executor/executor.go" && \
       grep -q "calculateBilling" "$ORCH_DIR/executor/executor.go" && \
       grep -q "ExecuteRequest" "$ORCH_DIR/executor/executor.go" && \
       grep -q "ExecuteResponse" "$ORCH_DIR/executor/executor.go"; then
        echo "  ✓ Executor has required components"
    else
        echo "  ✗ Executor missing required components"
        exit 1
    fi
else
    echo "  ✗ executor.go not found"
    exit 1
fi

# Test 5: Check billing tracker
echo "Test 5: Checking billing tracker..."
if [[ -f "$ORCH_DIR/billing/tracker.go" ]]; then
    echo "  ✓ tracker.go exists"
    if grep -q "Record" "$ORCH_DIR/billing/tracker.go" && \
       grep -q "Stats" "$ORCH_DIR/billing/tracker.go" && \
       grep -q "Webhook" "$ORCH_DIR/billing/tracker.go" && \
       grep -q "BillingInfo" "$ORCH_DIR/billing/tracker.go" && \
       grep -q "BillingRecord" "$ORCH_DIR/billing/tracker.go"; then
        echo "  ✓ Billing tracker has required components (record, stats, webhook, billing info/record)"
    else
        echo "  ✗ Billing tracker missing required components"
        exit 1
    fi
else
    echo "  ✗ tracker.go not found"
    exit 1
fi

# Test 6: Check go.mod
echo "Test 6: Checking Go module..."
if [[ -f "$ORCH_DIR/go.mod" ]]; then
    echo "  ✓ go.mod exists"
    if grep -q "github.com/djtech/orchestration" "$ORCH_DIR/go.mod" && \
       grep -q "github.com/containerd/containerd" "$ORCH_DIR/go.mod" && \
       grep -q "github.com/djtech/llm-router" "$ORCH_DIR/go.mod" && \
       grep -q "github.com/djtech/llm-gateway" "$ORCH_DIR/go.mod" && \
       grep -q "github.com/djtech/job-queue" "$ORCH_DIR/go.mod"; then
        echo "  ✓ go.mod has required dependencies"
    else
        echo "  ✗ go.mod missing required dependencies"
        exit 1
    fi
else
    echo "  ✗ go.mod not found"
    exit 1
fi

# Test 7: Check integration with other components
echo "Test 7: Checking integration with other components..."
if [[ -f "$PROJECT_ROOT/spike-prototype/llm-router/main.go" ]] && \
   [[ -f "$PROJECT_ROOT/spike-prototype/llm-gateway/main.go" ]] && \
   [[ -f "$PROJECT_ROOT/spike-prototype/job-queue/queue/redis_queue.go" ]] && \
   [[ -f "$PROJECT_ROOT/spike-prototype/job-queue/worker/worker.go" ]]; then
    echo "  ✓ All dependent components exist (llm-router, llm-gateway, job-queue)"
else
    echo "  ✗ Some dependent components missing"
    exit 1
fi

# Test 8: Check ADR documents referenced
echo "Test 8: Checking ADR documents..."
if [[ -f "$PROJECT_ROOT/ADR-001-agent-sandboxing-model.md" ]] && \
   [[ -f "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md" ]] && \
   [[ -f "$PROJECT_ROOT/ADR-003-job-queue-state-persistence.md" ]]; then
    echo "  ✓ All ADR documents exist"
else
    echo "  ✗ Some ADR documents missing"
    exit 1
fi

echo ""
echo "=== All smoke tests passed! ==="
echo ""
echo "Next steps for full validation:"
echo "  1. Install dependencies: cd spike-prototype/orchestration && go mod tidy"
echo "  2. Build orchestration: cd spike-prototype/orchestration && go build -o orchestration ."
echo "  3. Start dependencies: Redis, PostgreSQL, containerd with gVisor runtime"
echo "  4. Set environment variables (see config/config.json for list)"
echo "  5. Run orchestration: ./orchestration -config config/config.json"
echo "  6. Test agent execution: curl -X POST http://localhost:8082/v1/agents/execute -H 'Content-Type: application/json' -d '{\"agent_id\":\"test-agent\",\"agent_type\":\"python\",\"code\":\"print(\\\"hello\\\")\"}'"
echo "  7. Check metrics: curl http://localhost:8082/metrics"
echo "  8. Check billing: curl http://localhost:8082/v1/billing/usage"