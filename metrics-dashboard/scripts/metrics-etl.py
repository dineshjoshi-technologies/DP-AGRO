#!/usr/bin/env python3
"""Metrics ETL for the AI-Agriculture KPI dashboard (DPA-84).

Loads KPI rollups into the metrics Postgres schema (postgres/metrics_schema.sql):

  sensor_coverage   % of deployed farms with fresh sensor ingest (>= 1 sensor online)
  yield_rmse        yield prediction RMSE (t/ha) from model monitoring
  labor_hours_saved labor hours saved per farm per season from farmer activity logs

Inputs (JSON, one object per file or a list):
  --sensor-ingest  [{farm_id, sensor_id, last_ingest_at}]
  --model-monitor  [{farm_id, run_id, rmse}]                  (or {"rmse_t_ha": ...})
  --activity-logs  [{farm_id, season, hours_saved}]

Idempotent: rolls upsert on (metric_key, farm_id, window_start).
Exit codes: 0 ok, 1 bad input, 2 DB error.

Usage:
  python3 metrics-etl.py \
    --sensor-ingest ingest/sensor_online.json \
    --model-monitor monitor/yield_runs.json \
    --activity-logs logs/labor_hours.json \
    [--dsn postgresql://metrics:metrics@localhost:5432/metrics] \
    [--window-end ISO8601] [--dry-run]

Without a DSN the script prints rollups to stdout (used by dashboard smoke tests).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

METRIC_SENSOR_COVERAGE = "sensor_coverage"
METRIC_YIELD_RMSE = "yield_rmse"
METRIC_LABOR_HOURS = "labor_hours_saved"
METRIC_AUDIT_GAP = "audit_gap_minutes"
COVERAGE_FRESH_WINDOW_MINUTES = int(
    os.environ.get("COVERAGE_FRESH_WINDOW_MINUTES", "15")
)
# Default matches Phase 1 deployment: 10 pilot farms (ops/sensor_network/farm_registry.json).
TOTAL_DEPLOYED_FARMS = int(os.environ.get("TOTAL_DEPLOYED_FARMS", "10"))
SOURCE_SENSOR = "iot_ingest"
SOURCE_MODEL = "model_monitoring"
SOURCE_LABOR = "farmer_activity_logs"
SOURCE_AUDIT = "blockchain_audit"
AUDIT_GAP_ALERT_MINUTES = int(os.environ.get("AUDIT_GAP_ALERT_MINUTES", "15"))


def parse_args():
    p = argparse.ArgumentParser(description="KPI rollup ETL (DPA-84)")
    p.add_argument("--sensor-ingest", help="JSON with sensor last-ingest records")
    p.add_argument("--model-monitor", help="JSON with per-run RMSE records")
    p.add_argument("--activity-logs", help="JSON with labor hours saved records")
    p.add_argument("--audit-events", help="JSON with last blockchain audit timestamps [{event_type, timestamp_utc}]")
    p.add_argument("--dsn", help="Postgres DSN; omit to print rollups only")
    p.add_argument("--window-end", help="ISO8601 window end (default: now UTC)")
    p.add_argument("--dry-run", action="store_true", help="print rollups, no DB write")
    return p.parse_args()


def load_json(path):
    with open(path) as fp:
        data = json.load(fp)
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array or {{'records': [...]}}")
    return data


def parse_ts(value):
    if value is None:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def compute_rollups(sensor, model, activity, audit_events, window_end, now):
    rollups = []

    # --- sensor coverage: % of deployed farms with at least one fresh sensor
    farms = {}
    fresh_cutoff = now - timedelta(minutes=COVERAGE_FRESH_WINDOW_MINUTES)
    for rec in sensor:
        farm = rec.get("farm_id")
        if not farm:
            raise ValueError("sensor ingest record missing farm_id")
        farms.setdefault(farm, []).append(parse_ts(rec.get("last_ingest_at")))
    fresh_farms = {
        farm
        for farm, ts_list in farms.items()
        if any(ts and ts > fresh_cutoff for ts in ts_list)
    }
    known_farms = set(farms) | {
        rec.get("farm_id") for rec in model if rec.get("farm_id")
    }
    known_farms.discard(None)
    deployed = TOTAL_DEPLOYED_FARMS or len(known_farms)
    coverage = round(100.0 * len(fresh_farms) / deployed, 1) if deployed else 0.0
    rollups.append(
        {
            "metric_key": METRIC_SENSOR_COVERAGE,
            "metric_value": coverage,
            "unit": "pct_farms",
            "farm_id": None,
            "window_start": window_end - timedelta(days=7),
            "window_end": window_end,
            "source": SOURCE_SENSOR,
        }
    )

    # --- yield RMSE: mean of latest run per farm, plus company-wide mean
    latest_per_farm = {}
    for rec in model:
        farm = rec.get("farm_id")
        rmse = rec.get("rmse", rec.get("rmse_t_ha"))
        if farm is None or rmse is None:
            raise ValueError(f"model monitor record missing farm_id/rmse: {rec}")
        ts = parse_ts(rec.get("run_ts")) or window_end
        if farm not in latest_per_farm or ts > latest_per_farm[farm][0]:
            latest_per_farm[farm] = (ts, float(rmse))
    if latest_per_farm:
        company_rmse = round(
            sum(v for _, v in latest_per_farm.values()) / len(latest_per_farm), 4
        )
        rollups.append(
            {
                "metric_key": METRIC_YIELD_RMSE,
                "metric_value": company_rmse,
                "unit": "t/ha",
                "farm_id": None,
                "window_start": window_end - timedelta(days=7),
                "window_end": window_end,
                "source": SOURCE_MODEL,
            }
        )

    # --- labor hours saved: total hours per season (company-wide rollup)
    total_hours = 0.0
    seasons = set()
    for rec in activity:
        hours = rec.get("hours_saved")
        if hours is None:
            raise ValueError(f"activity log record missing hours_saved: {rec}")
        total_hours += float(hours)
        if rec.get("season"):
            seasons.add(rec["season"])
    rollups.append(
        {
            "metric_key": METRIC_LABOR_HOURS,
            "metric_value": round(total_hours, 2),
            "unit": "hrs/season",
            "farm_id": None,
            "window_start": window_end - timedelta(days=7),
            "window_end": window_end,
            "source": SOURCE_LABOR,
        }
    )
    if seasons:
        rollups[-1]["unit"] = "hrs/" + "+".join(sorted(seasons))

    # --- audit gap: minutes since last blockchain audit event
    if audit_events:
        latest_audit_ts = None
        for rec in audit_events:
            ts = parse_ts(rec.get("timestamp_utc") or rec.get("timestamp"))
            if ts and (latest_audit_ts is None or ts > latest_audit_ts):
                latest_audit_ts = ts
        if latest_audit_ts:
            gap_minutes = round((now - latest_audit_ts).total_seconds() / 60.0, 1)
        else:
            gap_minutes = 0.0
        rollups.append(
            {
                "metric_key": METRIC_AUDIT_GAP,
                "metric_value": gap_minutes,
                "unit": "min",
                "farm_id": None,
                "window_start": window_end - timedelta(days=7),
                "window_end": window_end,
                "source": SOURCE_AUDIT,
            }
        )

    return rollups


def write_rollups(dsn, rollups):
    import psycopg2  # noqa: deferred import so --dry-run works without the driver

    upsert = """
        INSERT INTO kpi_rollups
            (metric_key, metric_value, unit, farm_id, window_start, window_end, source)
        VALUES (%(metric_key)s, %(metric_value)s, %(unit)s, %(farm_id)s,
                %(window_start)s, %(window_end)s, %(source)s)
        ON CONFLICT (metric_key, farm_id, window_start)
        DO UPDATE SET metric_value = EXCLUDED.metric_value,
                      unit = EXCLUDED.unit,
                      window_end = EXCLUDED.window_end,
                      source = EXCLUDED.source
    """
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            for r in rollups:
                cur.execute(upsert, r)
        conn.commit()
    finally:
        conn.close()


def main():
    args = parse_args()
    if not (args.sensor_ingest or args.model_monitor or args.activity_logs or args.audit_events):
        print("error: at least one of --sensor-ingest/--model-monitor/--activity-logs/--audit-events "
              "is required", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    window_end = parse_ts(args.window_end) if args.window_end else now
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=timezone.utc)

    try:
        sensor = load_json(args.sensor_ingest) if args.sensor_ingest else []
        model = load_json(args.model_monitor) if args.model_monitor else []
        activity = load_json(args.activity_logs) if args.activity_logs else []
        audit_events = load_json(args.audit_events) if args.audit_events else []
        rollups = compute_rollups(sensor, model, activity, audit_events, window_end, now)
    except (ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(rollups, indent=2, default=str))

    if args.dry_run or not args.dsn:
        print("(dry-run: rollups not written)", file=sys.stderr)
        return 0

    try:
        write_rollups(args.dsn, rollups)
    except Exception as exc:  # psycopg2 errors and connection failures
        print(f"error: database write failed: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {len(rollups)} rollup(s) to kpi_rollups", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())