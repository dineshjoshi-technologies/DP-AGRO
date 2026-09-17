#!/usr/bin/env bash
# Full test suite for DPA-84 metrics pipeline
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

echo "=== DPA-84 Metrics Pipeline Tests ==="

# Test 1: ETL dry-run with all inputs
echo "[1/4] ETL dry-run with all inputs..."
OUTPUT=$(python3 "$SCRIPT_DIR/metrics-etl.py" \
  --sensor-ingest "$SCRIPT_DIR/testdata/sensor_online.json" \
  --model-monitor "$SCRIPT_DIR/testdata/yield_runs.json" \
  --activity-logs "$SCRIPT_DIR/testdata/labor_hours.json" \
  --audit-events "$SCRIPT_DIR/testdata/audit_events.json" \
  --dry-run 2>/dev/null) || { fail "ETL dry-run failed"; echo "$OUTPUT"; }
if echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)==4" 2>/dev/null; then
  pass "4 KPIs computed"
else
  fail "Expected 4 KPIs"
fi

# Test 2: ETL with missing audit events (optional input)
echo "[2/4] ETL dry-run without audit events..."
OUTPUT=$(python3 "$SCRIPT_DIR/metrics-etl.py" \
  --sensor-ingest "$SCRIPT_DIR/testdata/sensor_online.json" \
  --model-monitor "$SCRIPT_DIR/testdata/yield_runs.json" \
  --activity-logs "$SCRIPT_DIR/testdata/labor_hours.json" \
  --dry-run 2>/dev/null) || { fail "ETL dry-run failed"; echo "$OUTPUT"; }
if echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)==3" 2>/dev/null; then
  pass "3 KPIs computed (no audit)"
else
  fail "Expected 3 KPIs without audit"
fi

# Test 3: Audit trail validator
echo "[3/4] Audit trail validator..."
if python3 "$SCRIPT_DIR/../verification/audit-trail-validator.py" \
  --events "$SCRIPT_DIR/../verification/testdata/spec_compliant_events.json" \
  --validate > /dev/null 2>&1; then
  pass "4/4 spec-compliant events"
else
  fail "Validator rejected valid events"
fi

# Test 4: Gas calculator
echo "[4/4] Gas cost calculator..."
if python3 "$SCRIPT_DIR/../verification/gas-calculator.py" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['savings']['savings_pct']==94.5" 2>/dev/null; then
  pass "94.5% savings with batching"
else
  fail "Gas calculator output incorrect"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit ${FAIL}
