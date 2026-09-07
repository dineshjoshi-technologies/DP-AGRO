#!/usr/bin/env python3
"""Weekly metrics ETL scheduler for AI-Agriculture Convergence (DPA-84).

Reads input files from configurable paths, runs the ETL, and writes rollups
to Postgres. Designed to be invoked by cron weekly.

Usage:
    python3 weekly-etl.py --config /path/to/config.yaml

Config file format:
    inputs:
      sensor_ingest: "path/to/sensor_online.json"
      model_monitor: "path/to/yield_runs.json"
      activity_logs: "path/to/labor_hours.json"
      audit_events: "path/to/audit_events.json"  # optional
    output:
      dsn: "postgres://metrics:password@localhost:5432/metrics"
    thresholds:
      audit_gap_alert_minutes: 15
      coverage_alert_pct: 80
      rmse_alert_threshold: 0.18

Exit codes: 0 ok, 1 bad config, 2 DB error, 3 alert triggered
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None


def resolve_env_vars(obj):
    """Recursively resolve ${VAR} and ${VAR:-default} in strings."""
    if isinstance(obj, str):
        import re
        def replace_var(match):
            var_expr = match.group(1)
            if ":-" in var_expr:
                var, default = var_expr.split(":-", 1)
                return os.environ.get(var, default)
            return os.environ.get(var_expr, match.group(0))
        return re.sub(r'\$\{([^}]+)\}', replace_var, obj)
    elif isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    return obj


def load_config(path):
    if path.endswith(".json"):
        with open(path) as fp:
            return resolve_env_vars(json.load(fp))
    elif yaml is not None and path.endswith(".yaml"):
        with open(path) as fp:
            return resolve_env_vars(yaml.safe_load(fp))
    else:
        raise ValueError(f"Unsupported config format: {path}")


def run_etl(config):
    import subprocess
    import os

    inputs = config.get("inputs", {})
    output = config.get("output", {})
    thresholds = config.get("thresholds", {})

    # Resolve script path relative to this file's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    etl_script = os.path.join(script_dir, "metrics-etl.py")

    cmd = ["python3", etl_script]
    for key in ["sensor_ingest", "model_monitor", "activity_logs", "audit_events"]:
        input_path = inputs.get(key)
        if input_path:
            # Resolve relative to script dir if not absolute
            if not os.path.isabs(input_path):
                input_path = os.path.join(script_dir, input_path)
            cmd.extend(["--" + key.replace("_", "-"), input_path])

    dsn = output.get("dsn")
    # Skip DSN if missing or unresolved env var (e.g. ${PG_DSN} literal)
    if dsn and not dsn.startswith("${") and "%%(" not in dsn:
        cmd.extend(["--dsn", dsn])
    else:
        cmd.append("--dry-run")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ETL failed: {result.stderr}", file=sys.stderr)
        return result.returncode, None

    try:
        rollups = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"ETL output not JSON: {result.stdout}", file=sys.stderr)
        return 1, None

    # Check alert thresholds
    alerts = []
    for r in rollups:
        key = r.get("metric_key")
        val = r.get("metric_value")
        if key == "audit_gap_minutes" and val > thresholds.get("audit_gap_alert_minutes", 15):
            alerts.append(f"audit_gap_minutes={val} exceeds threshold {thresholds.get('audit_gap_alert_minutes', 15)}")
        if key == "sensor_coverage" and val < thresholds.get("coverage_alert_pct", 80):
            alerts.append(f"sensor_coverage={val}% below threshold {thresholds.get('coverage_alert_pct', 80)}%")
        if key == "yield_rmse" and val > thresholds.get("rmse_alert_threshold", 0.18):
            alerts.append(f"yield_rmse={val} exceeds threshold {thresholds.get('rmse_alert_threshold')}")

    if alerts:
        print("ALERTS:", file=sys.stderr)
        for a in alerts:
            print(f"  - {a}", file=sys.stderr)
        return 3, rollups

    return 0, rollups


def main():
    parser = argparse.ArgumentParser(description="Weekly metrics ETL scheduler (DPA-84)")
    parser.add_argument("--config", required=True, help="Path to config JSON/YAML")
    parser.add_argument("--log", help="Path to append execution log")
    args = parser.parse_args()

    config = load_config(args.config)
    now = datetime.now(timezone.utc).isoformat()

    exit_code, rollups = run_etl(config)

    log_entry = {
        "timestamp": now,
        "exit_code": exit_code,
        "rollups": rollups,
    }

    if args.log:
        with open(args.log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    print(json.dumps(log_entry, indent=2, default=str))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
