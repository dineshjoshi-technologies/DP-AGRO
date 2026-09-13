#!/usr/bin/env python3
"""Tests for edge_anomaly.py — isolation forest anomaly detection (DPA-82)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from edge_anomaly import AnomalyDetector, fit_isolation_forest, FEATURE_ORDER


def make_reading(values):
    return {"measurement": {k: v for k, v in zip(FEATURE_ORDER, values)}}


def test_unfitted_flags_everything():
    d = fit_isolation_forest(n_estimators=10, sample_size=64, seed=42)
    assert d.is_outlier(make_reading([0.3, 0.5, 6.5, 25.0, 70.0, 0.0, 0.0])) is True


def test_fit_accepts_normals():
    d = fit_isolation_forest(n_estimators=20, sample_size=64, seed=42)
    normals = [make_reading([0.28 + (i % 5) * 0.01, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0]) for i in range(100)]
    d.fit(normals, contamination=0.02)
    assert d.fitted is True


def test_normal_readings_not_flagged():
    d = fit_isolation_forest(n_estimators=20, sample_size=64, seed=42)
    normals = [make_reading([0.28 + (i % 5) * 0.01, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0]) for i in range(100)]
    d.fit(normals)
    # A reading near the mean should not be flagged
    normal = make_reading([0.28, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0])
    assert d.is_outlier(normal) is False


def test_extreme_reading_flagged():
    d = fit_isolation_forest(n_estimators=50, sample_size=128, seed=42)
    import random
    rng = random.Random(99)
    normals = [make_reading([rng.uniform(0.25, 0.31), rng.uniform(0.42, 0.48), rng.uniform(6.5, 7.1),
                             rng.uniform(24.0, 28.0), rng.uniform(65.0, 72.0), rng.uniform(0.0, 1.0),
                             rng.uniform(-0.1, 0.1)]) for _ in range(200)]
    d.fit(normals, contamination=0.02)
    # Multi-channel extreme should be flagged
    extreme = make_reading([2.0, 10.0, 11.0, 60.0, 100.0, 100.0, 1.0])
    assert d.is_outlier(extreme) is True


def test_missing_measurement_keys_use_defaults():
    d = fit_isolation_forest(n_estimators=10, sample_size=32, seed=42)
    normals = [make_reading([0.28, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0]) for _ in range(20)]
    d.fit(normals)
    # Reading with missing keys should fall back to defaults and not crash
    partial = {"measurement": {"moisture": 0.28}}
    result = d.is_outlier(partial)
    assert isinstance(result, bool)


def test_update_history():
    d = fit_isolation_forest(n_estimators=10, sample_size=32, seed=42)
    normals = [make_reading([0.28 + i * 0.001, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0]) for i in range(50)]
    d.fit(normals)
    for r in normals[:10]:
        d.update_history(r)
    assert len(d._history) == 60


def test_empty_history_fails_closed():
    d = fit_isolation_forest(n_estimators=10, sample_size=32, seed=42)
    d.fit([])
    # Fails closed: empty history => flags everything
    assert d.is_outlier(make_reading([0.28, 0.45, 6.8, 26.0, 68.0, 0.4, 0.0])) is True


if __name__ == "__main__":
    tests = [
        test_unfitted_flags_everything,
        test_fit_accepts_normals,
        test_normal_readings_not_flagged,
        test_extreme_reading_flagged,
        test_missing_measurement_keys_use_defaults,
        test_update_history,
        test_empty_history_fails_closed,
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
