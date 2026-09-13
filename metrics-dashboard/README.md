# Metrics Dashboard — DPA-84

AI-Agriculture Convergence KPI tracking and blockchain audit-trail coordination.

## Overview

Tracks 4 KPIs weekly:
- **sensor_coverage**: % of deployed farms with fresh sensor ingest (target >= 90%)
- **yield_rmse**: yield prediction RMSE in t/ha (target <= 0.15)
- **labor_hours_saved**: total labor hours saved per season (target >= 200)
- **audit_gap_minutes**: minutes since last blockchain audit event (threshold 15 min)

## Directory Structure

```
metrics-dashboard/
├── scripts/
│   ├── metrics-etl.py          # Core ETL: computes KPI rollups from JSON inputs
│   ├── weekly-etl.py           # Scheduler: reads config, runs ETL, checks alerts
│   ├── config/
│   │   └── weekly-etl.json     # Example config (resolve ${PG_DSN} before use)
│   ├── testdata/               # 10-farm Phase 1 test dataset
│   └── cron/
│       └── run-weekly-etl.sh   # Cron wrapper (Monday 02:00 UTC)
├── verification/
│   ├── audit-trail-validator.py # Validates blockchain audit event schema
│   ├── gas-calculator.py        # Estimates smart contract gas costs
│   ├── testdata/
│   │   └── spec_compliant_events.json  # 4-event spec-compliant chain
│   ├── validation-report.json
│   └── gas-estimates.json
├── grafana/
│   ├── provisioning/
│   │   ├── dashboards/
│   │   │   └── ai-agri-kpis.json     # Grafana dashboard JSON
│   │   ├── datasources/
│   │   │   └── datasources.yaml      # Postgres + Polygon datasources
│   │   └── alerts/
│   │       └── alerts.yaml           # 5 alert rules
│   └── dashboards/
├── postgres/
│   └── metrics_schema.sql          # kpi_rollups table DDL
├── docker-compose.yaml             # Postgres + Grafana stack (needs Docker)
└── HEARTBEAT-*.md                  # Heartbeat progress logs
```

## Quick Start

### Dry-run (no Docker required)
```bash
python3 scripts/metrics-etl.py \
  --sensor-ingest scripts/testdata/sensor_online.json \
  --model-monitor scripts/testdata/yield_runs.json \
  --activity-logs scripts/testdata/labor_hours.json \
  --audit-events scripts/testdata/audit_events.json \
  --dry-run
```

### Verification
```bash
python3 verification/audit-trail-validator.py \
  --events verification/testdata/spec_compliant_events.json \
  --validate

python3 verification/gas-calculator.py
```

### Full stack (requires Docker)
```bash
export PG_DSN="postgresql://metrics:metrics@localhost:5432/metrics"
docker compose up -d
python3 scripts/weekly-etl.py --config scripts/config/weekly-etl.json
```

### Cron deployment
```cron
# Every Monday 02:00 UTC
0 2 * * 1 /home/paperclip/paperclip/metrics-dashboard/scripts/cron/run-weekly-etl.sh
```

## KPI Validation Results (2026-09-06)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| sensor_coverage | 100.0 pct_farms | >= 90% | PASS |
| yield_rmse | 0.122 t/ha | <= 0.15 | PASS |
| labor_hours_saved | 210.15 hrs/2026-Kharif | >= 200 | PASS |
| audit_gap_minutes | 0.2 min | < 15 min | PASS |

## Gas Cost Projections

- Weekly: 0.0036 ETH (~$12.60 at $3500/ETH) with batching
- Annual: 0.1872 ETH (~$655 at $3500/ETH)
- 94.5% savings vs single writes

## Blockers

- [DPA-79](/DPA/issues/DPA-79) — Blockchain Integration Workstream blocked on recovery
- Docker unavailable in environment (blocks Postgres+Grafana deployment)

## Child Issues

- [DPA-182](/DPA/issues/DPA-182) — Blockchain audit trail smart contract integration (blocked on DPA-79)
- [DPA-191](/DPA/issues/DPA-191) — Alert rules + dashboard artifacts (blocked on DPA-79)
- [DPA-188](/DPA/issues/DPA-188) — Phase 2 Per-Zone Validation + Drift Monitoring (blocked on DPA-79)

## Specifications

Full spec: [DPA-84#document-metrics-audit-trail-spec](/DPA/issues/DPA-84#document-metrics-audit-trail-spec)
