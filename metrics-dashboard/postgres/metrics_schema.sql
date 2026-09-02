-- Metrics storage schema for AI-Agriculture Convergence (DPA-84)
-- Stores KPI rollups used by the Grafana dashboard:
--   sensor coverage (% farms), yield prediction RMSE, labor hours saved,
--   audit-trail completeness, data quality pass rate.
-- Materialized by scripts/metrics-etl.py from the ingestion pipeline + model monitoring.

CREATE TABLE IF NOT EXISTS kpi_rollups (
    id            BIGSERIAL PRIMARY KEY,
    metric_key     TEXT NOT NULL,          -- e.g. sensor_coverage, yield_rmse, labor_hours_saved
    metric_value   DOUBLE PRECISION NOT NULL,
    unit           TEXT NOT NULL DEFAULT '',
    farm_id        TEXT,                   -- NULL for company-wide rollup
    window_start   TIMESTAMPTZ NOT NULL,   -- aligned to UTC day for daily rollups
    window_end     TIMESTAMPTZ NOT NULL,
    source         TEXT NOT NULL DEFAULT 'ingest_logs',
    quality_flag   INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric_key, farm_id, window_start)
);

CREATE TABLE IF NOT EXISTS farm_sensor_online (
    farm_id        TEXT NOT NULL,
    sensor_id      TEXT NOT NULL,
    last_ingest_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (farm_id, sensor_id)
);

-- Sensor data coverage per farm, computed by metrics-etl.py
CREATE OR REPLACE VIEW coverage_current AS
SELECT
    farm_id,
    COUNT(*)                                                                  AS sensors_expected,
    COUNT(*) FILTER (WHERE last_ingest_at > now() - interval '5 minutes')     AS sensors_online,
    ROUND(100.0 * COUNT(*) FILTER (WHERE last_ingest_at > now() - interval '5 minutes')
        / NULLIF(COUNT(*), 0), 1)                                             AS coverage_pct
FROM farm_sensor_online
GROUP BY farm_id;

-- Alert threshold checks (driven by Grafana alert rules)
CREATE OR REPLACE VIEW kpi_latest AS
SELECT DISTINCT ON (metric_key, COALESCE(farm_id, 'ALL'))
    metric_key,
    COALESCE(farm_id, 'ALL') AS farm_id,
    metric_value,
    unit,
    quality_flag,
    window_start
FROM kpi_rollups
ORDER BY metric_key, COALESCE(farm_id, 'ALL'), window_start DESC;

CREATE INDEX IF NOT EXISTS idx_kpi_rollups_window ON kpi_rollups (metric_key, window_start DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_rollups_farm ON kpi_rollups (farm_id);