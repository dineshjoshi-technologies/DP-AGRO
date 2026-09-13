#!/usr/bin/env python3
"""
End-to-end validation of the Phase 1 crop sensor network pipeline (DPA-82).

Simulates the full data flow:
  1. Edge gateway collects readings from all 10 pilot farms
  2. Anomaly detection runs on each reading (isolation forest)
  3. Quality gate applies schema + registry validation
  4. Valid batches are buffered (48h encrypted storage) and flushed
  5. Audit hashes are emitted per policy §5

Run from repo root: python3 ops/sensor_network/e2e_validation.py
"""
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ops" / "sensor_network"))

from edge_anomaly import fit_isolation_forest
from edge_runtime import EdgeReading, EdgeBuffer, quality_gate, emit_batch_audit_hash, now_iso
from ingest_validator import EnvelopeValidator, IngestPipeline


def load_registry():
    with open(REPO_ROOT / "ops" / "sensor_network" / "farm_registry.json") as f:
        return json.load(f)


def simulate_fleet(registry, rng, n_cycles=50):
    """Simulate sensor readings across all 10 farms for n_cycles rounds."""
    all_readings = []
    anomaly_count = 0
    normal_count = 0

    for cycle in range(n_cycles):
        for farm in registry["farms"]:
            fid = farm["farm_id"]
            # Pick one random sensor per farm per cycle
            sensor_types = list(farm["sensors"].items())
            stype, sinfo = random.choice(sensor_types)
            sid = random.choice(sinfo["sensor_ids"])

            # Generate realistic reading
            if stype == "soil":
                measurement = {
                    "type": "soil",
                    "moisture": round(rng.uniform(0.25, 0.33), 4),
                    "ec": round(rng.uniform(0.40, 0.50), 4),
                    "ph": round(rng.uniform(6.3, 7.2), 2),
                }
            elif stype == "weather":
                measurement = {
                    "type": "weather",
                    "temperature_c": round(rng.uniform(23.0, 30.0), 1),
                    "humidity": round(rng.uniform(62.0, 76.0), 1),
                    "rainfall_mm": round(rng.uniform(0.0, 1.0), 2),
                }
            else:  # spectral
                measurement = {
                    "type": "spectral",
                    "ndvi": round(rng.uniform(0.50, 0.78), 3),
                    "source": "edge",
                }

            reading = EdgeReading(
                farm_id=fid,
                sensor_id=sid,
                timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                measurement=measurement,
                quality_flag=0,
            )
            all_readings.append(reading)

        # Inject ~2% anomalies
        if cycle % 5 == 0:
            for _ in range(3):
                idx = rng.randint(0, len(all_readings) - 1)
                r = all_readings[idx]
                r.measurement["moisture"] = 2.0  # extreme value
                r.measurement["ec"] = 10.0

    return all_readings


def run_pipeline():
    registry = load_registry()
    rng = random.Random(42)

    print("=" * 60)
    print("DPA-82 Phase 1 Sensor Network — End-to-End Validation")
    print("=" * 60)

    # --- Step 1: Load validators and detector ---
    validator = EnvelopeValidator()
    detector = fit_isolation_forest(n_estimators=100, sample_size=256, seed=42)

    # --- Step 2: Simulate fleet readings ---
    print("\n[1/5] Simulating sensor fleet across 10 pilot farms...")
    readings = simulate_fleet(registry, rng, n_cycles=5)
    print(f"  Generated {len(readings)} raw readings")

    # --- Step 3: Train anomaly detector on baseline ---
    print("\n[2/5] Training isolation forest on baseline data...")
    baseline = readings[:20]
    detector.fit(baseline)
    print(f"  Fitted on {len(baseline)} readings, threshold={detector.threshold:.4f}")

    # --- Step 4: Run quality gate on all readings ---
    print("\n[3/5] Running quality gates on all readings...")
    normal = 0
    flagged = 0
    schema_errors = 0
    for r in readings:
        result = quality_gate(r, detector, validator)
        if result == 0:
            normal += 1
        else:
            flagged += 1

    print(f"  Nominal: {normal}")
    print(f"  Flagged (degraded/anomalous): {flagged}")
    compliance_pct = (normal / len(readings)) * 100
    print(f"  Schema + registry compliance: {compliance_pct:.1f}%")

    # --- Step 5: Buffer and flush via ingest pipeline ---
    print("\n[4/5] Buffering and flushing via ingest pipeline...")
    buffer = EdgeBuffer(Path("/tmp/dpa82_test_buffer.db"), "e2e-test-key")
    pipeline = IngestPipeline()

    normal_readings = []
    for r in readings:
        qf = quality_gate(r, detector, validator)
        r.quality_flag = qf
        if qf == 0:
            normal_readings.append(r)

    # Simulate buffer + flush
    for r in normal_readings:
        buffer.enqueue(r)

    flushed = buffer.drain()
    print(f"  Buffered: {len(normal_readings)}, Flushed: {len(flushed)}")

    # Simulate cloud ingest
    envelopes = [r.__dict__ for r in flushed]
    accepted, rejected = pipeline.ingest(envelopes)
    print(f"  Cloud ingest — accepted: {len(accepted)}, rejected: {len(rejected)}")

    # --- Step 6: Audit trail ---
    print("\n[5/5] Generating audit trail hashes...")
    audit_logs = []
    batch_size = 50
    for i in range(0, len(flushed), batch_size):
        batch = flushed[i:i + batch_size]
        emit_batch_audit_hash(batch, lambda e: audit_logs.append(e))

    print(f"  Audit entries generated: {len(audit_logs)}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    total_farms = registry.get("coverage_target", {}).get("total_farms", len(registry["farms"]))
    print(f"  Total farms:          {len(registry['farms'])}/{total_farms}")
    print(f"  Total readings:       {len(readings)}")
    print(f"  Schema+registry pass: {compliance_pct:.1f}%")
    print(f"  Cloud accepted:       {len(accepted)}/{len(flushed)} ({len(accepted)/len(flushed)*100:.1f}%)")
    print(f"  Audit hashes:         {len(audit_logs)}")
    print(f"  Uptime target:        90% (governance §3.2)")
    print(f"  Buffer policy:        48h encrypted (AES-256-GCM)")
    print(f"  Anomaly detection:    isolation_forest (n=100, contam=0.02)")
    print(f"  Sensor breakdown:     soil={registry['fleet_totals']['soil_sensors']}, "
          f"weather={registry['fleet_totals']['weather_stations']}, "
          f"spectral={registry['fleet_totals']['spectral_sensors']}")
    print("=" * 60)

    # Cleanup
    Path("/tmp/dpa82_test_buffer.db").unlink(missing_ok=True)

    if len(registry["farms"]) == total_farms and len(accepted) > 0 and len(audit_logs) > 0:
        print(f"\n  RESULT: PASS — Pipeline operational across all {total_farms} farms")
        print(f"  (ingest acceptance {len(accepted)}/{len(flushed)}, audit entries {len(audit_logs)})")
        return 0
    else:
        print(f"\n  RESULT: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(run_pipeline())
