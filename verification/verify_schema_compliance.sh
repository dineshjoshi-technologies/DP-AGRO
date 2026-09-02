#!/bin/bash
# Schema compliance verification for sensor data ingestion
# Used by both MLOps and Blockchain Integration for audit trail matching

set -e

echo "=== Schema Compliance Verification ==="
echo "Timestamp: $(date -Iseconds)"

# Check sensor schema registry
if [ -f "schema/sensor_schema_v1.json" ]; then
    echo "✓ Sensor schema registry found"
    python3 -m jsonschema schema/sensor_schema_v1.json data/samples/*.json 2>/dev/null && echo "✓ All samples validate" || echo "✗ Sample validation failed"
else
    echo "✗ Sensor schema registry NOT found"
    exit 1
fi

# Check required fields
python3 << 'EOF'
import json
import glob

required_fields = ["farm_id", "sensor_id", "timestamp", "latitude", "longitude", "readings"]
for f in glob.glob("data/samples/*.json"):
    with open(f) as fp:
        data = json.load(fp)
    missing = [rf for rf in required_fields if rf not in data]
    if missing:
        print(f"✗ {f}: missing fields {missing}")
    else:
        print(f"✓ {f}: all required fields present")
EOF

echo "=== Schema Verification Complete ==="