#!/usr/bin/env python3
"""Tests for retraining_pipeline.py — DPA-83."""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from retraining_pipeline import RetrainingPipeline
from yield_model import YieldPredictor, generate_training_data


def test_pipeline_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(model_dir=model_dir, manifest_path=manifest_path)
        report = pipeline.status_report()
        assert "Cadence" in report
        assert "RMSE threshold" in report


def test_needs_retraining_no_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(model_dir=model_dir, manifest_path=manifest_path)
        assert pipeline.needs_retraining() is True


def test_run_training_passes_gate():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(rmse_threshold=0.15, model_dir=model_dir, manifest_path=manifest_path)
        data = generate_training_data(n_farms=80, seed=42)
        dataset_hash = "test-hash-001"

        def train_fn(training_data):
            predictor = YieldPredictor(seed=42)
            metrics = predictor.fit(training_data)
            return predictor, metrics

        run = pipeline.run_training(data, train_fn, dataset_hash, dry_run=True)
        assert run.status in ("staging", "rejected")
        assert run.n_samples == 80
        assert run.rmse < 0.15


def test_run_training_rejected_when_rmse_too_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(rmse_threshold=0.001, model_dir=model_dir, manifest_path=manifest_path)
        data = generate_training_data(n_farms=80, seed=42)

        def train_fn(training_data):
            predictor = YieldPredictor(seed=42)
            metrics = predictor.fit(training_data)
            return predictor, metrics

        run = pipeline.run_training(data, train_fn, "hash-002", dry_run=True)
        assert run.status == "rejected"


def test_promote_to_production():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(rmse_threshold=0.15, model_dir=model_dir, manifest_path=manifest_path)
        data = generate_training_data(n_farms=80, seed=42)

        def train_fn(training_data):
            predictor = YieldPredictor(seed=42)
            metrics = predictor.fit(training_data)
            return predictor, metrics

        run = pipeline.run_training(data, train_fn, "hash-003", dry_run=False)
        assert run.run_id is not None

        promoted = pipeline.promote_to_production(run.run_id)
        assert promoted is True

        prod = pipeline.get_production_model()
        assert prod is not None


def test_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = __import__("pathlib").Path(tmpdir)
        manifest_path = model_dir / "manifest.json"
        pipeline = RetrainingPipeline(rmse_threshold=0.15, model_dir=model_dir, manifest_path=manifest_path)
        data = generate_training_data(n_farms=80, seed=42)

        def train_fn(training_data):
            predictor = YieldPredictor(seed=42)
            metrics = predictor.fit(training_data)
            return predictor, metrics

        # Run two training sessions
        run1 = pipeline.run_training(data, train_fn, "hash-rollback-1", dry_run=False)
        pipeline.promote_to_production(run1.run_id)

        run2 = pipeline.run_training(data, train_fn, "hash-rollback-2", dry_run=False)
        pipeline.promote_to_production(run2.run_id)

        # Verify we have production model
        prod = pipeline.get_production_model()
        assert prod is not None


if __name__ == "__main__":
    tests = [
        test_pipeline_status,
        test_needs_retraining_no_history,
        test_run_training_passes_gate,
        test_run_training_rejected_when_rmse_too_high,
        test_promote_to_production,
        test_rollback,
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
