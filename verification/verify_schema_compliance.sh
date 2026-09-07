#!/bin/bash
# Schema compliance verification for sensor data ingestion
# Used by both MLOps and Blockchain Integration for audit trail matching (DPA-84 / DPA-79)
#
# Validates JSON samples against schema/sensor_schema_v1.json.
# v2: aligned with the actual schema registry (timestamp_utc, quality_flag);
#     legacy timestamp/latitude/longitude/readings fields are accepted but optional.

set -e

echo "=== Schema Compliance Verification ==="
echo "Timestamp: $(date -Iseconds)"

SCHEMA_FILE="${SENSOR_SCHEMA:-schema/sensor_schema_v2.json}"

# Check sensor schema registry
if [ -f "$SCHEMA_FILE" ]; then
    echo "✓ Sensor schema registry found: $SCHEMA_FILE"
    python3 -m jsonschema -i data/samples/*.json "$SCHEMA_FILE" \
        && echo "✓ All samples validate against $(basename "$SCHEMA_FILE")" \
        || { echo "✗ Sample validation failed"; exit 1; }
else
    echo "✗ Sensor schema registry NOT found: $SCHEMA_FILE"
    exit 1
fi

# Check required fields (schema-required + legacy optional fields reported separately)
python3 << 'EOF'
import glob
import json

SCHEMA_REQUIRED = ["farm_id", "sensor_id", "timestamp_utc", "measurement", "quality_flag"]
LEGACY_OPTIONAL = ["timestamp", "latitude", "longitude", "readings"]

failures = 0
files = sorted(glob.glob("data/samples/*.json"))
for f in files:
    with open(f) as fp:
        data = json.load(fp)
    missing = [rf for rf in SCHEMA_REQUIRED if rf not in data]
    if missing:
        print(f"✗ {f}: missing required fields {missing}")
        failures += 1
        continue
    legacy_missing = [rf for rf in LEGACY_OPTIONAL if rf not in data]
    note = f" (legacy fields absent: {', '.join(legacy_missing)})" if legacy_missing else ""
    print(f"✓ {f}: all schema-required fields present{note}")

if failures:
    raise SystemExit(1)
print(f"✓ {len(files)} sample file(s) checked")
EOF

echo "=== Schema Verification Complete ==="