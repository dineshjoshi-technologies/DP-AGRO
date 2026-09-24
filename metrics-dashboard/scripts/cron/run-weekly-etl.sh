#!/usr/bin/env bash
# Weekly ETL runner for DPA-84 metrics tracking
# Invoked by cron: 0 2 * * 1 (every Monday 02:00 UTC)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${METRICS_LOG_DIR:-$(dirname "$SCRIPT_DIR")/logs}"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/weekly-etl-$(date -u +%Y%m%d-%H%M%S).log"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting weekly ETL" >> "$LOG_FILE"

python3 "$SCRIPT_DIR/weekly-etl.py" \
  --config "$SCRIPT_DIR/config/weekly-etl.json" \
  --log "$LOG_FILE" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ETL exited with code $EXIT_CODE" >> "$LOG_FILE"
exit "$EXIT_CODE"
