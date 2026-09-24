#!/bin/bash
# Smoke test for the LLM Router spike prototype

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ROUTER_DIR="$PROJECT_ROOT/spike-prototype/llm-router"

echo "=== DJ Tech LLM Router Spike Prototype Smoke Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Router dir: $ROUTER_DIR"
echo ""

# Test 1: Check ADR document exists
echo "Test 1: Checking ADR-002 document..."
if [[ -f "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md" ]]; then
    echo "  ✓ ADR-002 document exists"
    if grep -qi "provider abstraction" "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md" && \
       grep -qi "model selection" "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md" && \
       grep -qi "fallback" "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md" && \
       grep -qi "cost optimization" "$PROJECT_ROOT/ADR-002-llm-router-model-selection.md"; then
        echo "  ✓ ADR-002 covers required topics"
    else
        echo "  ✗ ADR-002 missing required topics"
        exit 1
    fi
else
    echo "  ✗ ADR-002 document not found"
    exit 1
fi

# Test 2: Check router config
echo "Test 2: Checking router configuration..."
if [[ -f "$ROUTER_DIR/config/router-config.json" ]]; then
    echo "  ✓ router-config.json exists"
    if command -v jq &> /dev/null; then
        if jq empty "$ROUTER_DIR/config/router-config.json" 2>/dev/null; then
            echo "  ✓ router-config.json is valid JSON"
            # Check required fields
            if jq -e '.default_model and .selection and .fallbacks and .providers and .models' "$ROUTER_DIR/config/router-config.json" >/dev/null; then
                echo "  ✓ router-config.json has required structure"
            else
                echo "  ✗ router-config.json missing required fields"
                exit 1
            fi
        else
            echo "  ✗ router-config.json is invalid JSON"
            exit 1
        fi
    else
        echo "  ⚠ router-config.json validation skipped (jq not installed)"
    fi
else
    echo "  ✗ router-config.json not found"
    exit 1
fi

# Test 3: Check router core
echo "Test 3: Checking router core implementation..."
if [[ -f "$ROUTER_DIR/router/router.go" ]]; then
    echo "  ✓ router.go exists"
    if grep -q "RouteRequest" "$ROUTER_DIR/router/router.go" && \
       grep -q "RouteRequestStream" "$ROUTER_DIR/router/router.go" && \
       grep -q "Provider interface" "$ROUTER_DIR/router/router.go" && \
       grep -q "HTTPHandler" "$ROUTER_DIR/router/router.go"; then
        echo "  ✓ Router has required methods"
    else
        echo "  ✗ Router missing required methods"
        exit 1
    fi
else
    echo "  ✗ router.go not found"
    exit 1
fi

# Test 4: Check model selector
echo "Test 4: Checking model selector..."
if [[ -f "$ROUTER_DIR/selector/selector.go" ]]; then
    echo "  ✓ selector.go exists"
    if grep -q "SelectModel" "$ROUTER_DIR/selector/selector.go" && \
       grep -q "calculateScore" "$ROUTER_DIR/selector/selector.go" && \
       grep -q "SelectionWeights" "$ROUTER_DIR/selector/selector.go"; then
        echo "  ✓ Selector has required components"
    else
        echo "  ✗ Selector missing required components"
        exit 1
    fi
else
    echo "  ✗ selector.go not found"
    exit 1
fi

# Test 5: Check cost tracker
echo "Test 5: Checking cost tracker..."
if [[ -f "$ROUTER_DIR/router/cost_tracker.go" ]]; then
    echo "  ✓ cost_tracker.go exists"
    if grep -q "Record" "$ROUTER_DIR/router/cost_tracker.go" && \
       grep -q "GetStats" "$ROUTER_DIR/router/cost_tracker.go" && \
       grep -q "CostStats" "$ROUTER_DIR/router/cost_tracker.go"; then
        echo "  ✓ Cost tracker has required components"
    else
        echo "  ✗ Cost tracker missing required components"
        exit 1
    fi
else
    echo "  ✗ cost_tracker.go not found"
    exit 1
fi

# Test 6: Check OpenAI adapter
echo "Test 6: Checking OpenAI adapter..."
if [[ -f "$ROUTER_DIR/adapters/openai.go" ]]; then
    echo "  ✓ openai.go exists"
    if grep -q "ChatCompletion" "$ROUTER_DIR/adapters/openai.go" && \
       grep -q "ChatCompletionStream" "$ROUTER_DIR/adapters/openai.go" && \
       grep -q "toOpenAIRequest" "$ROUTER_DIR/adapters/openai.go" && \
       grep -q "parseStream" "$ROUTER_DIR/adapters/openai.go"; then
        echo "  ✓ OpenAI adapter has required components"
    else
        echo "  ✗ OpenAI adapter missing required components"
        exit 1
    fi
else
    echo "  ✗ openai.go not found"
    exit 1
fi

# Test 7: Check Anthropic adapter
echo "Test 7: Checking Anthropic adapter..."
if [[ -f "$ROUTER_DIR/adapters/anthropic.go" ]]; then
    echo "  ✓ anthropic.go exists"
    if grep -q "toAnthropicRequest" "$ROUTER_DIR/adapters/anthropic.go" && \
       grep -q "fromAnthropicResponse" "$ROUTER_DIR/adapters/anthropic.go" && \
       grep -q "parseStream" "$ROUTER_DIR/adapters/anthropic.go"; then
        echo "  ✓ Anthropic adapter has required components"
    else
        echo "  ✗ Anthropic adapter missing required components"
        exit 1
    fi
else
    echo "  ✗ anthropic.go not found"
    exit 1
fi

# Test 8: Check Ollama adapter
echo "Test 8: Checking Ollama adapter..."
if [[ -f "$ROUTER_DIR/adapters/ollama.go" ]]; then
    echo "  ✓ ollama.go exists"
    if grep -q "ChatCompletion" "$ROUTER_DIR/adapters/ollama.go" && \
       grep -q "ChatCompletionStream" "$ROUTER_DIR/adapters/ollama.go"; then
        echo "  ✓ Ollama adapter has required components"
    else
        echo "  ✗ Ollama adapter missing required components"
        exit 1
    fi
else
    echo "  ✗ ollama.go not found"
    exit 1
fi

# Test 9: Check provider factory
echo "Test 9: Checking provider factory..."
if [[ -f "$ROUTER_DIR/adapters/factory.go" ]]; then
    echo "  ✓ factory.go exists"
    if grep -q "CreateProvider" "$ROUTER_DIR/adapters/factory.go" && \
       grep -q "openai" "$ROUTER_DIR/adapters/factory.go" && \
       grep -q "anthropic" "$ROUTER_DIR/adapters/factory.go" && \
       grep -q "ollama" "$ROUTER_DIR/adapters/factory.go"; then
        echo "  ✓ Factory supports required providers"
    else
        echo "  ✗ Factory missing provider support"
        exit 1
    fi
else
    echo "  ✗ factory.go not found"
    exit 1
fi

# Test 10: Check main entry point
echo "Test 10: Checking main entry point..."
if [[ -f "$ROUTER_DIR/main.go" ]]; then
    echo "  ✓ main.go exists"
    if grep -q "NewRouter" "$ROUTER_DIR/main.go" && \
       grep -q "HTTPHandler" "$ROUTER_DIR/main.go" && \
       grep -q "ListenAndServe" "$ROUTER_DIR/main.go"; then
        echo "  ✓ Main has required components"
    else
        echo "  ✗ Main missing required components"
        exit 1
    fi
else
    echo "  ✗ main.go not found"
    exit 1
fi

# Test 11: Check go.mod
echo "Test 11: Checking Go module..."
if [[ -f "$ROUTER_DIR/go.mod" ]]; then
    echo "  ✓ go.mod exists"
    if grep -q "github.com/djtech/llm-router" "$ROUTER_DIR/go.mod" && \
       grep -q "github.com/google/uuid" "$ROUTER_DIR/go.mod"; then
        echo "  ✓ go.mod has required dependencies"
    else
        echo "  ✗ go.mod missing required dependencies"
        exit 1
    fi
else
    echo "  ✗ go.mod not found"
    exit 1
fi

# Test 12: Check unit tests
echo "Test 12: Checking unit tests..."
if [[ -f "$ROUTER_DIR/router/router_test.go" ]]; then
    echo "  ✓ router_test.go exists"
    if grep -q "TestRouterConfigDefaults" "$ROUTER_DIR/router/router_test.go" && \
       grep -q "TestModelSelector" "$ROUTER_DIR/router/router_test.go" && \
       grep -q "TestCostTracker" "$ROUTER_DIR/router/router_test.go"; then
        echo "  ✓ Unit tests cover core components"
    else
        echo "  ✗ Unit tests missing core coverage"
        exit 1
    fi
else
    echo "  ✗ router_test.go not found"
    exit 1
fi

echo ""
echo "=== All smoke tests passed! ==="
echo ""
echo "Next steps for full validation:"
echo "  1. Build router: cd spike-prototype/llm-router && go build -o llm-router ."
echo "  2. Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY"
echo "  3. Run router: ./llm-router -config config/router-config.json"
echo "  4. Test with curl: curl -X POST http://localhost:8081/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo "  5. Run unit tests: go test -v ./..."
echo "  6. Test fallback behavior by simulating provider failures"
echo "  7. Benchmark routing latency and cost tracking accuracy"