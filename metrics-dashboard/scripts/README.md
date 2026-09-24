# Weekly ETL Scheduler

Runs the metrics ETL pipeline on a weekly schedule. Designed for cron deployment.

## Setup

1. Configure inputs in `config/weekly-etl.json`
2. Set `PG_DSN` environment variable for Postgres connection
3. Add to cron:

```cron
# Run every Monday at 06:00 UTC
0 6 * * 1 cd /path/to/metrics-dashboard && python3 scripts/weekly-etl.py --config config/weekly-etl.json --log logs/weekly-etl.log
```

## Exit Codes

- 0: Success, no alerts
- 1: Bad config or ETL error
- 2: Database write error
- 3: Alert threshold exceeded (rollups still written)

## Alert Thresholds

Configurable in `config/weekly-etl.json`:

- `audit_gap_alert_minutes`: Alert when blockchain audit gap exceeds this (default: 15 min)
- `coverage_alert_pct`: Alert when sensor coverage falls below this (default: 80%)
- `rmse_alert_threshold`: Alert when yield RMSE exceeds this (default: 0.18 t/ha)
