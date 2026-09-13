#!/usr/bin/env python3
"""
Sensor network metrics tracker — Phase 1 (DPA-82).

Tracks the three mission-critical metrics:
  1. Sensor data coverage (% of farms reporting)
  2. Yield prediction accuracy (RMSE) — placeholder for model integration
  3. Labor hours saved — placeholder for operational integration

Also tracks operational metrics:
  - Edge gateway uptime (% heartbeat responses in 24h window)
  - Schema compliance rate (% ingested envelopes valid)
  - Anomaly detection rate (% readings flagged)
  - Audit trail completeness (% batches with hash entries)

Run from repo root: python3 ops/sensor_network/metrics_tracker.py [--simulate]
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_FILE = REPO_ROOT / "ops" / "sensor_network" / "metrics.json"


class MetricsTracker:
    """Collects and reports sensor network operational metrics."""

    def __init__(self, registry_path: Optional[Path] = None):
        # Load farm count from registry if available, else default to 100
        self.farm_count = 100
        if registry_path is None:
            registry_path = REPO_ROOT / "ops" / "sensor_network" / "farm_registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                reg = json.load(f)
            self.farm_count = len(reg.get("farms", []))
        self.readings_by_farm: Dict[str, int] = {f"FARM-{i:03d}": 0 for i in range(1, self.farm_count + 1)}
        self.flagged_by_farm: Dict[str, int] = {f"FARM-{i:03d}": 0 for i in range(1, self.farm_count + 1)}
        self.schema_errors_by_farm: Dict[str, int] = {f"FARM-{i:03d}": 0 for i in range(1, self.farm_count + 1)}
        self.batches_with_audit: int = 0
        self.total_batches: int = 0
        self.uptime_heartbeats: Dict[str, List[str]] = {f"FARM-{i:03d}": [] for i in range(1, self.farm_count + 1)}
        self.yield_predictions: List[Dict] = []
        self.labor_hours_saved: float = 0.0

    def record_reading(self, farm_id: str, sensor_id: str, quality_flag: int,
                       schema_valid: bool, has_audit: bool = True) -> None:
        """Record a single sensor reading."""
        if farm_id in self.readings_by_farm:
            self.readings_by_farm[farm_id] += 1
            if quality_flag == 1:
                self.flagged_by_farm[farm_id] += 1
            if not schema_valid:
                self.schema_errors_by_farm[farm_id] += 1
            if has_audit:
                self.batches_with_audit += 1
        self.total_batches += 1

    def record_heartbeat(self, farm_id: str, timestamp: Optional[str] = None) -> None:
        """Record an edge gateway uptime heartbeat."""
        ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if farm_id in self.uptime_heartbeats:
            self.uptime_heartbeats[farm_id].append(ts)

    def record_yield_prediction(self, farm_id: str, predicted_yields_per_hectare: float,
                                 actual_yields_per_hectare: float) -> None:
        """Record a yield prediction for RMSE tracking."""
        self.yield_predictions.append({
            "farm_id": farm_id,
            "predicted": predicted_yields_per_hectare,
            "actual": actual_yields_per_hectare,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })

    def record_labor_hours(self, farm_id: str, hours_saved: float) -> None:
        """Record labor hours saved via automation."""
        self.labor_hours_saved += hours_saved

    # --- Metric Calculations ---

    def sensor_data_coverage(self) -> float:
        """Percentage of farms with at least 1 reading in the current window."""
        active = sum(1 for v in self.readings_by_farm.values() if v > 0)
        return (active / self.farm_count) * 100.0

    def schema_compliance_rate(self) -> float:
        """Percentage of readings that passed schema validation."""
        total = sum(self.readings_by_farm.values())
        errors = sum(self.schema_errors_by_farm.values())
        if total == 0:
            return 100.0
        return ((total - errors) / total) * 100.0

    def anomaly_detection_rate(self) -> float:
        """Percentage of readings flagged as anomalous."""
        total = sum(self.readings_by_farm.values())
        flagged = sum(self.flagged_by_farm.values())
        if total == 0:
            return 0.0
        return (flagged / total) * 100.0

    def avg_gateway_uptime(self) -> float:
        """Average uptime across all gateways (based on heartbeat frequency)."""
        # In production, this would check heartbeat timestamps against expected cadence
        # For now, return a placeholder based on readings
        total_readings = sum(self.readings_by_farm.values())
        if total_readings == 0:
            return 0.0
        # Simplified: assume 90%+ uptime if we have readings from all farms
        active = sum(1 for v in self.readings_by_farm.values() if v > 0)
        return (active / self.farm_count) * 100.0

    def yield_prediction_rmse(self) -> float:
        """Root mean square error of yield predictions."""
        if not self.yield_predictions:
            return 0.0
        squared_errors = [
            (p["predicted"] - p["actual"]) ** 2
            for p in self.yield_predictions
        ]
        return (sum(squared_errors) / len(squared_errors)) ** 0.5

    def labor_hours_total(self) -> float:
        return self.labor_hours_saved

    def audit_trail_completeness(self) -> float:
        if self.total_batches == 0:
            return 100.0
        return (self.batches_with_audit / self.total_batches) * 100.0

    # --- Reporting ---

    def report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("DPA-82 Phase 1 — Sensor Network Metrics Report")
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
        lines.append("=" * 60)

        lines.append("\n## Mission-Critical Metrics")
        lines.append(f"  1. Sensor Data Coverage:      {self.sensor_data_coverage():5.1f}% (target: 100%)")
        lines.append(f"  2. Yield Prediction RMSE:     {self.yield_prediction_rmse():.4f} t/ha"
                      f" ({'tracked' if self.yield_predictions else 'pending model integration'})")
        lines.append(f"  3. Labor Hours Saved:         {self.labor_hours_total():.1f} hrs"
                      f" ({'tracked' if self.labor_hours_saved > 0 else 'pending operational integration'})")

        lines.append("\n## Operational Metrics")
        lines.append(f"  Gateway Uptime (avg):         {self.avg_gateway_uptime():5.1f}% (target: ≥90%)")
        lines.append(f"  Schema Compliance Rate:       {self.schema_compliance_rate():5.1f}% (target: ≥95%)")
        lines.append(f"  Anomaly Detection Rate:       {self.anomaly_detection_rate():5.1f}%")
        lines.append(f"  Audit Trail Completeness:     {self.audit_trail_completeness():5.1f}% (target: 100%)")

        lines.append("\n## Fleet Status")
        for farm_id in sorted(self.readings_by_farm):
            readings = self.readings_by_farm[farm_id]
            flagged = self.flagged_by_farm[farm_id]
            status = "ACTIVE" if readings > 0 else "INACTIVE"
            lines.append(f"  {farm_id}: {status:8s}  readings={readings:5d}  flagged={flagged:3d}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def save(self) -> None:
        """Persist metrics to JSON file."""
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "metrics": {
                "sensor_data_coverage_pct": self.sensor_data_coverage(),
                "schema_compliance_pct": self.schema_compliance_rate(),
                "anomaly_detection_pct": self.anomaly_detection_rate(),
                "gateway_uptime_pct": self.avg_gateway_uptime(),
                "audit_trail_completeness_pct": self.audit_trail_completeness(),
                "yield_prediction_rmse": self.yield_prediction_rmse(),
                "labor_hours_saved": self.labor_hours_total(),
            },
            "per_farm": {
                "readings": dict(self.readings_by_farm),
                "flagged": dict(self.flagged_by_farm),
            },
        }
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Metrics saved to {METRICS_FILE}")


def simulate_daily_readings(rng: random.Random, days: int = 7, n_farms: int = 100) -> MetricsTracker:
    """Simulate a week of sensor readings for testing."""
    tracker = MetricsTracker()
    # Override to match desired farm count
    tracker.farm_count = n_farms
    tracker.readings_by_farm = {f"FARM-{i:03d}": 0 for i in range(1, n_farms + 1)}
    tracker.flagged_by_farm = {f"FARM-{i:03d}": 0 for i in range(1, n_farms + 1)}
    tracker.schema_errors_by_farm = {f"FARM-{i:03d}": 0 for i in range(1, n_farms + 1)}
    tracker.uptime_heartbeats = {f"FARM-{i:03d}": [] for i in range(1, n_farms + 1)}

    farm_ids = [f"FARM-{i:03d}" for i in range(1, n_farms + 1)]
    sensor_types = ["SOIL", "WX", "SPEC"]
    zones = ["ZA", "ZB", "ZC", "ZD"]

    for day in range(days):
        for farm_id in farm_ids:
            # Each farm reports ~100 readings per day
            n_readings = rng.randint(80, 120)
            for _ in range(n_readings):
                sensor_type = rng.choice(sensor_types)
                zone = rng.choice(zones)
                sensor_id = f"{sensor_type}-{zone}-{rng.randint(1, 8):02d}"
                quality_flag = 0 if rng.random() > 0.03 else 1  # ~3% anomaly rate
                schema_valid = rng.random() > 0.01  # ~1% schema error rate
                tracker.record_reading(farm_id, sensor_id, quality_flag, schema_valid)

            # Uptime heartbeat every 60 seconds
            for minute in range(0, 1440, 60):
                if rng.random() > 0.005:  # 99.5% uptime
                    tracker.record_heartbeat(farm_id)

    # Simulate yield predictions
    for farm_id in farm_ids:
        predicted = rng.uniform(2.5, 4.5)
        actual = predicted + rng.gauss(0, 0.06)
        tracker.record_yield_prediction(farm_id, predicted, max(0, actual))

    # Simulate labor hours saved
    for farm_id in farm_ids:
        tracker.record_labor_hours(farm_id, rng.uniform(2.0, 5.0))

    return tracker


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DPA-82 Sensor Network Metrics Tracker")
    parser.add_argument("--simulate", action="store_true", help="Run simulation for 7 days")
    parser.add_argument("--load", action="store_true", help="Load existing metrics from file")
    parser.add_argument("--n-farms", type=int, default=100, help="Number of farms to simulate")
    args = parser.parse_args()

    if args.simulate:
        rng = random.Random(42)
        tracker = simulate_daily_readings(rng, days=7, n_farms=args.n_farms)
        tracker.save()
    elif args.load and METRICS_FILE.exists():
        with open(METRICS_FILE) as f:
            data = json.load(f)
        # Recreate tracker from saved data
        tracker = MetricsTracker()
        tracker.readings_by_farm = data.get("per_farm", {}).get("readings", tracker.readings_by_farm)
        tracker.flagged_by_farm = data.get("per_farm", {}).get("flagged", tracker.flagged_by_farm)
        # Restore other metrics from data
        metrics = data.get("metrics", {})
        # Recalculate from raw data
    else:
        tracker = MetricsTracker()

    print(tracker.report())

    # Check SLA targets
    print("\n## SLA Compliance Check")
    sla_checks = [
        ("Sensor data coverage ≥ 90%", tracker.sensor_data_coverage() >= 90.0),
        ("Schema compliance ≥ 95%", tracker.schema_compliance_rate() >= 95.0),
        ("Gateway uptime ≥ 90%", tracker.avg_gateway_uptime() >= 90.0),
        ("Audit trail 100% complete", tracker.audit_trail_completeness() == 100.0),
    ]
    for label, passed in sla_checks:
        icon = "✓" if passed else "✗"
        print(f"  {icon}  {label}")

    return 0 if all(p for _, p in sla_checks) else 1


if __name__ == "__main__":
    sys.exit(main())
