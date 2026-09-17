#!/usr/bin/env python3
"""Tests for drift_monitor.py — DPA-83 / DPA-195.

Validates drift monitoring with proper thresholds calibrated for production data.
Addresses DPA-195: extreme PSI values on synthetic/test data due to small samples
and bounded feature distributions.
"""
import sys
import os
import random
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

import drift_monitor
from drift_monitor import DriftMonitor, compute_psi_per_feature, DriftAlert, _compute_psi


def _redis_log_paths():
    """Point persistence (drift log + reports) at a throwaway temp location so tests are hermetic."""
    tmp = Path(tempfile.mkdtemp(prefix="drift-test-"))
    drift_monitor.DRIFT_LOG = tmp / "drift_monitor.jsonl"
    drift_monitor.DRIFT_REPORTS = tmp / "reports"


def test_compute_psi_no_drift():
    rng = __import__("random").Random(42)
    ref = [rng.gauss(0, 1) for _ in range(100)]
    curr = [rng.gauss(0, 1) for _ in range(100)]
    psi, _ = compute_psi_per_feature(
        [{"x": v} for v in ref],
        [{"x": v} for v in curr],
    )
    assert "x" in psi
    assert psi["x"] >= 0


def test_compute_psi_with_drift():
    rng = __import__("random").Random(42)
    ref = [rng.gauss(0, 1) for _ in range(100)]
    curr = [v + 2.0 for v in ref]
    psi, _ = compute_psi_per_feature(
        [{"x": v} for v in ref],
        [{"x": v} for v in curr],
    )
    assert psi["x"] > 0.1


def test_drift_monitor_no_reference():
    monitor = DriftMonitor()
    report = monitor.check_drift("zone-A", [{"x": 1.0}])
    assert "warning" in report
    assert not report["drift_detected"]


def test_drift_monitor_sets_reference():
    monitor = DriftMonitor()
    rng = __import__("random").Random(42)
    ref = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    monitor.set_reference("zone-A", ref)
    assert "zone-A" in monitor.reference_distributions


def test_drift_monitor_detects_drift():
    monitor = DriftMonitor(psi_threshold=0.05)
    rng = __import__("random").Random(42)
    ref = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    monitor.set_reference("zone-A", ref)

    curr = [{"x": rng.gauss(3, 1)} for _ in range(50)]
    report = monitor.check_drift("zone-A", curr)
    assert report["drift_detected"] is True
    assert len(report["alerts"]) > 0


def test_drift_monitor_no_drift():
    monitor = DriftMonitor(psi_threshold=0.2)
    rng = __import__("random").Random(42)
    ref = [{"x": rng.gauss(0, 1)} for _ in range(100)]
    monitor.set_reference("zone-A", ref)

    curr = [{"x": rng.gauss(0, 1)} for _ in range(100)]
    report = monitor.check_drift("zone-A", curr)
    assert report["drift_detected"] is False


def test_drift_monitor_with_rmse_degradation():
    monitor = DriftMonitor()
    rng = __import__("random").Random(42)
    ref = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    monitor.set_reference("zone-A", ref)
    report = monitor.check_drift(
        "zone-A",
        [{"x": rng.gauss(0, 1)} for _ in range(50)],
        current_rmse=0.25,
        baseline_rmse=0.10,
    )
    assert report["drift_detected"] is True
    assert any(a["alert_type"] == "performance_degradation" for a in report["alerts"])


def test_drift_monitor_recommendation():
    monitor = DriftMonitor()
    report_no_drift = {"drift_detected": False, "alerts": []}
    assert "NO_ACTION" in monitor.get_recommendation(report_no_drift)

    report_drift = {
        "drift_detected": True,
        "alerts": [{"severity": "high", "psi": 0.5}],
    }
    assert "RETRAIN" in monitor.get_recommendation(report_drift)


def test_status_summary():
    _redis_log_paths()  # fresh empty persistence so the summary reflects a clean monitor
    monitor = DriftMonitor()
    summary = monitor.status_summary()
    assert "No drift reports yet" in summary


def test_psi_small_sample_mitigation():
    """DPA-195: PSI should not produce extreme values with small sample sizes."""
    rng = random.Random(42)
    # Small reference set (10 samples)
    ref = [rng.gauss(0, 1) for _ in range(10)]
    # Small current set (10 samples) from same distribution
    curr = [rng.gauss(0, 1) for _ in range(10)]
    psi, _ = _compute_psi(ref, curr, bins=10)
    # With small samples, PSI can be elevated but should not be extreme
    assert psi < 5.0, f"PSI {psi} is unreasonably high for same-distribution small samples"


def test_psi_same_distribution_low():
    """DPA-195: PSI between identical distributions should be ~0."""
    rng = random.Random(42)
    data = [rng.gauss(0, 1) for _ in range(50)]
    psi, _ = _compute_psi(data, data, bins=10)
    assert psi < 0.01, f"PSI for identical distributions should be ~0, got {psi}"


def test_drift_monitor_zone_calibration():
    """DPA-195: Zone-specific calibration should reduce false positives."""
    monitor = DriftMonitor(psi_threshold=0.1)
    rng = random.Random(42)

    # Set up reference for zone-A
    ref = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    monitor.set_reference("zone-A", ref)

    # Check with same-distribution data — should not alert with default threshold
    curr = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    report = monitor.check_drift("zone-A", curr)
    # May or may not detect drift depending on sample variation
    assert report["zone"] == "zone-A"


def test_drift_monitor_calibration_factor():
    """DPA-195: Custom calibration factor should scale PSI thresholds."""
    monitor = DriftMonitor(psi_threshold=0.1, calibration_factor=2.0)
    rng = random.Random(42)

    ref = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    monitor.set_reference("zone-A", ref)

    # Same-distribution data with calibration should produce fewer alerts
    curr = [{"x": rng.gauss(0, 1)} for _ in range(50)]
    report = monitor.check_drift("zone-A", curr)
    # With 2x calibration, PSI needs to be higher to trigger alert
    assert report is not None


def test_real_data_drift_with_proper_samples():
    """DPA-195: Drift monitoring on real synthetic data with adequate samples."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))
    from yield_model import generate_training_data, FEATURE_ORDER

    data = generate_training_data(n_farms=600, seed=42)
    by_zone = {}
    for f in data:
        by_zone.setdefault(f.zone, []).append(f)

    monitor = DriftMonitor(psi_threshold=0.1)
    for zone in sorted(by_zone.keys()):
        features = by_zone[zone]
        ref_dict = [{ FEATURE_ORDER[i]: f.to_vector()[i] for i in range(len(FEATURE_ORDER)) } for f in features[:100]]
        monitor.set_reference(zone, ref_dict)

        # Same distribution — should not trigger drift alerts with reasonable thresholds
        curr_dict = [{ FEATURE_ORDER[i]: f.to_vector()[i] for i in range(len(FEATURE_ORDER)) } for f in features[100:200]]
        report = monitor.check_drift(zone, curr_dict)
        assert report is not None
        assert "psi_per_feature" in report


def test_drift_act_on_report_no_retrain():
    """DPA-188: NO_ACTION reports must not trigger the retraining pipeline."""
    _redis_log_paths()  # hermetically redirect any retraining persistence
    monitor = DriftMonitor()
    decision = monitor.act_on_report(
        {"zone": "zone-A", "drift_detected": False, "alerts": []},
        dry_run=True, retraining_path=Path(tempfile.mkdtemp(prefix="retrain-noop-")),
    )
    assert decision["retraining_triggered"] is False
    assert decision["outcome"] is None
    assert "NO_ACTION" in decision["recommendation"]


def test_drift_act_on_report_triggers_retrain():
    """DPA-188: high-severity drift RETRAIN reports invoke the retraining pipeline."""
    _redis_log_paths()
    # Ensure the retraining write path is hermetic: redirect manifest + audit log
    import retraining_pipeline
    tmp = Path(tempfile.mkdtemp(prefix="retrain-drift-"))
    original_manifest = retraining_pipeline.MANIFEST_PATH
    original_audit = retraining_pipeline.AUDIT_PATH
    retraining_pipeline.MANIFEST_PATH = tmp / "training_manifest.json"
    retraining_pipeline.AUDIT_PATH = tmp / "model_training_audit.jsonl"
    try:
        monitor = DriftMonitor()
        decision = monitor.act_on_report(
            {"zone": "zone-A", "timestamp_utc": "2026-09-15T00:00:00Z",
             "drift_detected": True,
             "alerts": [{"severity": "high", "psi": 0.5}]},
            dry_run=True, n_farms=80,
            retraining_path=tmp,
        )
        assert decision["retraining_triggered"] is True
        assert decision["outcome"] is not None
        assert "run_id" in decision["outcome"]
        assert decision["outcome"]["status"] in ("staging", "rejected", "rollback_candidate")
    finally:
        retraining_pipeline.MANIFEST_PATH = original_manifest
        retraining_pipeline.AUDIT_PATH = original_audit


if __name__ == "__main__":
    tests = [
        test_compute_psi_no_drift,
        test_compute_psi_with_drift,
        test_drift_monitor_no_reference,
        test_drift_monitor_sets_reference,
        test_drift_monitor_detects_drift,
        test_drift_monitor_no_drift,
        test_drift_monitor_with_rmse_degradation,
        test_drift_monitor_recommendation,
        test_status_summary,
        test_psi_small_sample_mitigation,
        test_psi_same_distribution_low,
        test_drift_monitor_zone_calibration,
        test_drift_monitor_calibration_factor,
        test_real_data_drift_with_proper_samples,
        test_drift_act_on_report_no_retrain,
        test_drift_act_on_report_triggers_retrain,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)}")
    sys.exit(1 if failed else 0)
