#!/usr/bin/env python3
"""Tests for yield_model.py — gradient boosted yield prediction (DPA-83)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from yield_model import (
    YieldPredictor, FarmFeatures, GBRModel,
    generate_training_data, features_to_vector, FEATURE_ORDER,
    ModelMetrics, _predict_node, _build_tree,
)


def test_generate_training_data():
    data = generate_training_data(n_farms=40, seed=42)
    assert len(data) == 40
    assert all(f.yield_t_per_ha is not None for f in data)
    zones = set(f.zone for f in data)
    assert len(zones) == 4  # 4 zones


def test_features_to_vector():
    f = FarmFeatures(
        farm_id="FARM-001", zone="zone-A", season_week=1,
        soil_moisture_mean=0.28, soil_moisture_std=0.02,
        soil_ph_mean=6.8, soil_ec_mean=0.45,
        temp_mean=26.0, temp_max=35.0, temp_min=18.0,
        humidity_mean=68.0, rainfall_total_mm=50.0,
        ndvi_current=0.65, ndvi_lag7=0.6, ndvi_lag14=0.55,
        ndvi_trend=0.1, growing_degree_days=280.0, soil_water_deficit=0.0,
        yield_t_per_ha=3.2,
    )
    vec = features_to_vector(f)
    assert len(vec) == len(FEATURE_ORDER)
    assert vec[0] == 0.28
    assert vec[-1] == 0.0  # soil_water_deficit is the last feature in FEATURE_ORDER


def test_gbr_model_fit_and_predict():
    rng = __import__("random").Random(42)
    n = 50
    X = [[rng.gauss(0, 1) for _ in range(5)] for _ in range(n)]
    y = [sum(x[:3]) + rng.gauss(0, 0.1) for x in X]

    model = GBRModel(n_estimators=10, max_depth=3, seed=42)
    model.fit(X, y)

    preds = model.predict_batch(X[:5])
    assert len(preds) == 5
    assert all(isinstance(p, float) for p in preds)


def test_yield_predictor_train_and_predict():
    data = generate_training_data(n_farms=80, seed=42)
    predictor = YieldPredictor(seed=42)
    metrics = predictor.fit(data)

    assert metrics.rmse < 0.15, f"RMSE {metrics.rmse} exceeds 0.15 target"
    assert metrics.mae < 0.10, f"MAE {metrics.mae} exceeds 0.10 target"
    assert metrics.r2 > 0.85, f"R² {metrics.r2} below 0.85 target"
    assert metrics.n_samples == 80

    # Test prediction on a sample farm
    sample = data[0]
    pred = predictor.predict(sample.farm_id, sample.zone, sample)
    assert isinstance(pred, float)
    assert pred >= 0.0


def test_yield_predictor_save_load():
    import tempfile
    data = generate_training_data(n_farms=40, seed=42)
    predictor = YieldPredictor(seed=42)
    predictor.fit(data)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name

    saved = predictor.save(path=__import__("pathlib").Path(path))
    assert saved.exists()

    loaded = YieldPredictor.load(saved)
    assert loaded.last_rmse == predictor.last_rmse
    assert len(loaded.zone_models) == len(predictor.zone_models)

    sample = data[0]
    orig_pred = predictor.predict(sample.farm_id, sample.zone, sample)
    load_pred = loaded.predict(sample.farm_id, sample.zone, sample)
    assert abs(orig_pred - load_pred) < 1e-6


def test_zone_models_are_trained():
    data = generate_training_data(n_farms=80, seed=42)
    predictor = YieldPredictor(seed=42)
    predictor.fit(data)

    assert len(predictor.zone_models) >= 3  # At least 3 zones with enough data
    for zone, model in predictor.zone_models.items():
        assert model.base_pred > 0
        assert len(model.trees) > 0


def test_per_zone_metrics():
    data = generate_training_data(n_farms=120, seed=42)
    predictor = YieldPredictor(seed=42)
    metrics = predictor.fit(data)

    assert "zone-A" in metrics.per_zone
    assert "zone-B" in metrics.per_zone
    for zone, zm in metrics.per_zone.items():
        assert "rmse" in zm
        assert "mae" in zm
        assert "r2" in zm
        assert zm["rmse"] >= 0


def test_tree_leaf_node():
    # Single sample should produce a leaf
    X = [[1.0, 2.0]]
    y = [3.0]
    tree = _build_tree(X, y, depth=0, max_depth=3, min_samples=2,
                       rng=__import__("random").Random(42))
    assert tree.value is not None
    assert abs(_predict_node(tree, [1.0, 2.0]) - 3.0) < 1e-6


def test_tree_splits_on_varied_data():
    rng = __import__("random").Random(42)
    X = [[i, i * 2] for i in range(20)]
    y = [i + rng.gauss(0, 0.1) for i in range(20)]
    tree = _build_tree(X, y, depth=0, max_depth=3, min_samples=3, rng=rng)
    # With varied data, the root should have a split
    assert tree.feature_idx is not None
    assert tree.threshold is not None


def test_out_of_sample_generalization():
    """Train on seed=42, validate on seed=99 — must have positive R²."""
    import math, statistics
    train_data = generate_training_data(n_farms=120, seed=42)
    predictor = YieldPredictor(seed=42)
    predictor.fit(train_data)

    test_data = generate_training_data(n_farms=120, seed=99)
    preds, actuals = [], []
    for f in test_data:
        if f.yield_t_per_ha is not None:
            preds.append(predictor.predict(f.farm_id, f.zone, f))
            actuals.append(f.yield_t_per_ha)

    n = len(actuals)
    rmse = math.sqrt(sum((p - a) ** 2 for p, a in zip(preds, actuals)) / n)
    mean_a = statistics.mean(actuals)
    ss_res = sum((p - a) ** 2 for p, a in zip(preds, actuals))
    ss_tot = sum((a - mean_a) ** 2 for a in actuals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0

    assert r2 > 0, f"Out-of-sample R² must be positive, got {r2:.4f}"
    assert rmse <= 0.15, f"Out-of-sample RMSE must be <= 0.15, got {rmse:.4f}"


def test_out_of_sample_per_zone():
    """Out-of-sample R² must be positive for every zone."""
    import math, statistics
    train_data = generate_training_data(n_farms=120, seed=42)
    predictor = YieldPredictor(seed=42)
    predictor.fit(train_data)

    test_data = generate_training_data(n_farms=120, seed=99)
    by_zone = {}
    for f in test_data:
        if f.yield_t_per_ha is not None:
            by_zone.setdefault(f.zone, {"preds": [], "actuals": []})
            by_zone[f.zone]["preds"].append(predictor.predict(f.farm_id, f.zone, f))
            by_zone[f.zone]["actuals"].append(f.yield_t_per_ha)

    for zone, vals in by_zone.items():
        p, a = vals["preds"], vals["actuals"]
        n = len(a)
        rmse = math.sqrt(sum((x - y) ** 2 for x, y in zip(p, a)) / n)
        mean_a = statistics.mean(a)
        ss_res = sum((x - y) ** 2 for x, y in zip(p, a))
        ss_tot = sum((y - mean_a) ** 2 for y in a)
        r2 = 1 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0
        assert r2 > 0, f"{zone} out-of-sample R² must be positive, got {r2:.4f}"
        assert rmse <= 0.15, f"{zone} out-of-sample RMSE must be <= 0.15, got {rmse:.4f}"


if __name__ == "__main__":
    tests = [
        test_generate_training_data,
        test_features_to_vector,
        test_gbr_model_fit_and_predict,
        test_yield_predictor_train_and_predict,
        test_yield_predictor_save_load,
        test_zone_models_are_trained,
        test_per_zone_metrics,
        test_tree_leaf_node,
        test_tree_splits_on_varied_data,
        test_out_of_sample_generalization,
        test_out_of_sample_per_zone,
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
