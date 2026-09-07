#!/bin/bash
# Refresh test data timestamps to current UTC
# Usage: bash refresh-testdata.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/testdata"

python3 << 'PYEOF'
import json, datetime, sys, os

now = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).isoformat()
data_dir = os.environ.get("DATA_DIR", "testdata")
files = ['sensor_online.json', 'yield_runs.json', 'labor_hours.json', 'audit_events.json']
for f in files:
    path = os.path.join(data_dir, f)
    if not os.path.exists(path):
        continue
    with open(path) as fh:
        data = json.load(fh)
    if isinstance(data, list):
        for item in data:
            for key in ['last_ingest_at', 'run_ts', 'timestamp_utc', 'timestamp']:
                if key in item:
                    item[key] = now
    elif isinstance(data, dict):
        for key in ['last_ingest_at', 'run_ts', 'timestamp_utc', 'timestamp']:
            if key in data:
                data[key] = now
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=2)
    print(f'Refreshed {f} to {now}')
print(f'Done. All test data refreshed to {now}')
PYEOF
