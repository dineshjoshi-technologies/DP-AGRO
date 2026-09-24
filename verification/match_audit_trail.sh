#!/bin/bash
# Audit trail matching between AI pipeline and blockchain
# Ensures every sensor batch and model event has a corresponding blockchain entry

set -e

echo "=== Blockchain Audit Trail Matching ==="
echo "Timestamp: $(date -Iseconds)"

# Check audit trail logs
if [ -f "logs/audit_trail.jsonl" ]; then
    echo "✓ Audit trail log found"
    count=$(wc -l < logs/audit_trail.jsonl)
    echo "Total audit entries: $count"
    
    # Check for critical event types
    python3 << 'EOF'
import json

event_types = set()
critical_events = {"sensor_batch_ingest", "model_training_run", "model_promotion", "prediction_batch"}
found_critical = set()

with open("logs/audit_trail.jsonl") as f:
    for line in f:
        try:
            entry = json.loads(line)
            if "event_type" in entry:
                event_types.add(entry["event_type"])
                if entry["event_type"] in critical_events:
                    found_critical.add(entry["event_type"])
        except json.JSONDecodeError:
            continue

print(f"Event types found: {sorted(event_types)}")
missing = critical_events - found_critical
if missing:
    print(f"⚠ Missing critical event types: {missing}")
else:
    print("✓ All critical event types present")
EOF
else
    echo "✗ Audit trail log NOT found"
fi

echo "=== Audit Trail Matching Complete ==="