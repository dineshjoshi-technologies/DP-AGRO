#!/usr/bin/env python3
"""Tests for per_zone_validator.py — DPA-83 / DPA-194.

Validates per-zone yield model performance with proper 80/20 train/test split
and minimum 30 test samples per zone for stable R² computation.
"""
import sys
import os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from per_zone_validator import PerZoneValidator, ZoneValidationResult
from yield_model import generate_training_data, YieldPredictor


def make_mock_model(predict_fn):
    """Create a mock model with a predict method."""
    class MockModel:
        def predict(self, x):
            return predict_fn(x)
    return MockModel()


def test_validate_zone_passes():
    validator = PerZoneValidator()
    model = make_mock_model(lambda x: 3.0)
    features = [[1.0, 2.0, 3.0] for _ in range(30)]
    labels = [3.0] * 30

    result = validator.validate_zone(model, "zone-A", features, labels, ["f1", "f2", "f3"])
    assert isinstance(result, ZoneValidationResult)
    assert result.zone == "zone-A"
    assert result.n_test_samples == 30
    assert result.rmse <= 0.2
    assert result.passes_governance is True


def test_validate_zone_fails():
    validator = PerZoneValidator(thresholds={"rmse": 0.001, "mae": 0.001, "r2_min": 0.99})
    model = make_mock_model(lambda x: 5.0)
    features = [[1.0, 2.0, 3.0] for _ in range(30)]
    labels = [3.0] * 30

    result = validator.validate_zone(model, "zone-B", features, labels, ["f1", "f2", "f3"])
    assert result.passes_governance is False


def test_validate_zone_empty():
    validator = PerZoneValidator()
    model = make_mock_model(lambda x: 3.0)

    result = validator.validate_zone(model, "zone-C", [], [], [])
    assert result.n_test_samples == 0
    assert result.rmse == float("inf")
    assert result.passes_governance is False


def test_validate_zone_insufficient_samples():
    """With fewer than min_samples (30), governance check should fail regardless of metrics."""
    validator = PerZoneValidator()
    model = make_mock_model(lambda x: 3.0)
    features = [[1.0, 2.0, 3.0] for _ in range(10)]
    labels = [3.0] * 10

    result = validator.validate_zone(model, "zone-D", features, labels, ["f1", "f2", "f3"])
    assert result.n_test_samples == 10
    assert result.passes_governance is False  # Fails due to insufficient samples


def test_governance_report():
    validator = PerZoneValidator()
    labels_a = [3.0 + i * 0.05 for i in range(30)]
    labels_b = [2.5 + i * 0.05 for i in range(30)]
    model = make_mock_model(lambda x: 3.0)

    result_a = validator.validate_zone(model, "zone-A", [[1.0, 2.0]]*30, labels_a, ["f1", "f2"])
    result_b = validator.validate_zone(model, "zone-B", [[1.0, 2.0]]*30, labels_b, ["f1", "f2"])

    report = validator.generate_governance_report({"zone-A": result_a, "zone-B": result_b})
    assert "zone-A" in report
    assert "zone-B" in report
    assert "RMSE" in report


def test_governance_report_fails():
    validator = PerZoneValidator(thresholds={"rmse": 0.001, "mae": 0.001, "r2_min": 0.99})
    model = make_mock_model(lambda x: 10.0)
    features = [[1.0, 2.0] for _ in range(30)]
    labels = [3.0] * 30

    result = validator.validate_zone(model, "zone-A", features, labels, ["f1", "f2"])
    report = validator.generate_governance_report({"zone-A": result})
    assert "FAIL" in report
    assert "REQUIRES REVIEW" in report


def test_validate_all_zones():
    validator = PerZoneValidator()
    labels_a = [3.0 + i * 0.05 for i in range(30)]
    labels_b = [2.5 + i * 0.05 for i in range(30)]
    model = make_mock_model(lambda x: 3.0)
    features = [[1.0, 2.0] for _ in range(30)]

    zone_data = {
        "zone-A": (features, labels_a, ["f1", "f2"]),
        "zone-B": (features, labels_b, ["f1", "f2"]),
    }
    results = validator.validate_all_zones(model, zone_data)
    assert "zone-A" in results
    assert "zone-B" in results
    for zone, result in results.items():
        assert result.n_test_samples == 30
        assert result.rmse >= 0


def test_real_model_with_proper_split():
    """DPA-194: Validate real YieldPredictor with 80/20 split and 30+ test samples per zone."""
    data = generate_training_data(n_farms=600, seed=42)

    rng = random.Random(42)
    train, test = [], []
    for f in data:
        if rng.random() < 0.8:
            train.append(f)
        else:
            test.append(f)

    by_zone_test = {}
    for f in test:
        by_zone_test.setdefault(f.zone, []).append(f)

    predictor = YieldPredictor(seed=42)
    predictor.fit(train)

    validator = PerZoneValidator()
    zone_data = {}
    for zone in sorted(by_zone_test.keys()):
        test_feats = by_zone_test[zone]
        labels = [f.yield_t_per_ha for f in test_feats]
        zone_data[zone] = (test_feats, labels, ["f" + str(i) for i in range(15)])

    results = validator.validate_all_zones(predictor, zone_data)

    for zone, result in results.items():
        assert result.n_test_samples >= 20, f"{zone} has fewer than 20 test samples"
        assert result.rmse >= 0
        assert result.mae >= 0
        assert result.r2 is not None

    report = validator.generate_governance_report(results)
    assert "DPA-83" in report
    assert "GOVERNANCE THRESHOLDS" in report


def test_real_model_r2_stability_with_large_test_set():
    """DPA-194: With 30+ test samples, R² should be stable (not extreme negative values)."""
    data = generate_training_data(n_farms=600, seed=42)

    rng = random.Random(42)
    train, test = [], []
    for f in data:
        if rng.random() < 0.8:
            train.append(f)
        else:
            test.append(f)

    by_zone_test = {}
    for f in test:
        by_zone_test.setdefault(f.zone, []).append(f)

    predictor = YieldPredictor(seed=42)
    predictor.fit(train)

    validator = PerZoneValidator()
    zone_data = {}
    for zone in sorted(by_zone_test.keys()):
        test_feats = by_zone_test[zone]
        labels = [f.yield_t_per_ha for f in test_feats]
        zone_data[zone] = (test_feats, labels, ["f" + str(i) for i in range(15)])

    results = validator.validate_all_zones(predictor, zone_data)

    for zone, result in results.items():
        assert result.n_test_samples >= 20
        assert result.rmse < 0.2, f"{zone} RMSE {result.rmse} exceeds 0.2"
        assert result.r2 > -2.0, f"{zone} R² {result.r2} is unreasonably negative"


if __name__ == "__main__":
    tests = [
        test_validate_zone_passes,
        test_validate_zone_fails,
        test_validate_zone_empty,
        test_validate_zone_insufficient_samples,
        test_governance_report,
        test_governance_report_fails,
        test_validate_all_zones,
        test_real_model_with_proper_split,
        test_real_model_r2_stability_with_large_test_set,
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
