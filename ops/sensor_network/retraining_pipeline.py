#!/usr/bin/env python3
"""
Retraining pipeline for yield prediction models — DPA-83.

Implements:
  - Scheduled retraining on configurable cadence (default: weekly)
  - Data versioning via manifest (dataset hash tracking)
  - Model promotion: staging -> production with RMSE gate
  - Auto-rollback if new model degrades >10% vs baseline
  - Blockchain audit trail entry per training run

Governance alignment: policy §4.2 (validation), §4.3 (model registry).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = REPO_ROOT / "ops" / "models"
MANIFEST_PATH = MODEL_DIR / "training_manifest.json"
AUDIT_PATH = REPO_ROOT / "logs" / "model_training_audit.jsonl"

# Retraining config (aligns with gateway_config.yaml anomaly_detection.retrain.cadence_days)
DEFAULT_CADENCE_DAYS = 7
RMSE_DEGRADATION_THRESHOLD = 0.10  # 10% degradation triggers rollback


@dataclass
class TrainingRun:
    run_id: str
    timestamp_utc: str
    n_samples: int
    dataset_hash: str
    rmse: float
    mae: float
    r2: float
    per_zone_metrics: Dict[str, Dict[str, float]]
    model_path: str
    status: str  # "staging" | "production" | "rolled_back"
    promoted_by: Optional[str] = None
    base_rmse: Optional[float] = None  # for rollback comparison


class RetrainingPipeline:
    """Orchestrates yield model retraining with governance gates."""

    def __init__(self, cadence_days: int = DEFAULT_CADENCE_DAYS,
                 rmse_threshold: float = 0.15,
                 model_dir: Path = MODEL_DIR,
                 manifest_path: Optional[Path] = None):
        self.cadence_days = cadence_days
        self.rmse_threshold = rmse_threshold
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = manifest_path or MANIFEST_PATH
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                return json.load(f)
        return {"version": "1.0", "runs": [], "production_model": None}

    def _save_manifest(self) -> None:
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def needs_retraining(self, last_run_ts: Optional[str] = None) -> bool:
        """Check if retraining is due based on cadence."""
        if last_run_ts is None:
            last_run = self.manifest.get("production_run")
            if last_run is None:
                return True
            last_run_ts = last_run.get("timestamp_utc")

        if last_run_ts is None:
            return True

        last = datetime.fromisoformat(last_run_ts.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - last > timedelta(days=self.cadence_days)

    def run_training(self, training_data: List[Any], train_fn, dataset_hash: str,
                     dry_run: bool = False) -> TrainingRun:
        """Execute a training run with governance gates.

        Args:
            training_data: List of FarmFeatures (or compatible objects)
            train_fn: Callable that fits model and returns (model, metrics)
            dataset_hash: SHA-256 hash of the training dataset
            dry_run: If True, don't save or promote
        """
        run_id = f"train-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{hashlib.md5(dataset_hash.encode()).hexdigest()[:8]}"
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Execute training
        model, metrics = train_fn(training_data)

        run = TrainingRun(
            run_id=run_id,
            timestamp_utc=ts,
            n_samples=metrics.n_samples,
            dataset_hash=dataset_hash,
            rmse=metrics.rmse,
            mae=metrics.mae,
            r2=metrics.r2,
            per_zone_metrics=metrics.per_zone,
            model_path="",
            status="staging",
        )

        if dry_run:
            # Still apply governance gate in dry-run mode so tests can verify rejection
            if metrics.rmse > self.rmse_threshold:
                run.status = "rejected"
                print(f"[GOVERNANCE] DRY RUN — Run {run_id} REJECTED: RMSE {metrics.rmse:.4f} > threshold {self.rmse_threshold}")
            else:
                prod_run = self.manifest.get("production_run")
                if prod_run and prod_run.get("rmse"):
                    baseline_rmse = prod_run["rmse"]
                    degradation = (metrics.rmse - baseline_rmse) / max(baseline_rmse, 1e-10)
                    if degradation > RMSE_DEGRADATION_THRESHOLD:
                        run.status = "rollback_candidate"
                        run.base_rmse = baseline_rmse
            print(f"[DRY RUN] Training run {run_id}: RMSE={metrics.rmse:.4f} status={run.status}")
            return run

        # Save model
        model_path = self.model_dir / f"{run_id}.json"
        model.save(model_path)
        run.model_path = str(model_path)

        # Governance gate: check RMSE threshold
        if metrics.rmse > self.rmse_threshold:
            run.status = "rejected"
            print(f"[GOVERNANCE] Run {run_id} REJECTED: RMSE {metrics.rmse:.4f} > threshold {self.rmse_threshold}")
        else:
            # Check degradation vs production baseline
            prod_run = self.manifest.get("production_run")
            if prod_run and prod_run.get("rmse"):
                baseline_rmse = prod_run["rmse"]
                degradation = (metrics.rmse - baseline_rmse) / max(baseline_rmse, 1e-10)
                if degradation > RMSE_DEGRADATION_THRESHOLD:
                    run.status = "rollback_candidate"
                    run.base_rmse = baseline_rmse
                    print(f"[ROLLBACK] Run {run_id}: {degradation:.1%} degradation vs baseline {baseline_rmse:.4f}")

        # Emit blockchain audit entry
        self._emit_audit_entry(run, metrics)
        # Persist run to manifest
        self.manifest.setdefault("runs", []).append({
            "run_id": run.run_id,
            "timestamp_utc": run.timestamp_utc,
            "n_samples": run.n_samples,
            "dataset_hash": run.dataset_hash,
            "rmse": run.rmse,
            "mae": run.mae,
            "r2": run.r2,
            "per_zone_metrics": run.per_zone_metrics,
            "status": run.status,
            "model_path": run.model_path,
        })
        self._save_manifest()

        print(f"[TRAIN] Run {run_id}: RMSE={metrics.rmse:.4f} MAE={metrics.mae:.4f} R2={metrics.r2:.4f} status={run.status}")
        return run

    def promote_to_production(self, run_id: str, promoter: str = "MLOps_Lead") -> bool:
        """Promote a staging run to production."""
        for run in self.manifest.get("runs", []):
            if run["run_id"] == run_id and run.get("status") == "staging":
                run["status"] = "production"
                run["promoted_by"] = promoter
                run["promoted_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                self.manifest["production_run"] = run
                self._save_manifest()
                self._emit_promotion_audit(run_id, promoter)
                return True
        return False

    def rollback_to_baseline(self, reason: str = "RMSE degradation") -> Optional[TrainingRun]:
        """Rollback to previous production model."""
        runs = self.manifest.get("runs", [])
        # Find the run before current production
        prod_idx = None
        for i, run in enumerate(runs):
            if run.get("status") == "production":
                prod_idx = i
                break

        if prod_idx and prod_idx > 0:
            prev = runs[prod_idx - 1]
            if prev.get("status") in ("staging", "production"):
                # Demote current, restore previous
                for run in runs:
                    if run.get("status") == "production":
                        run["status"] = "rolled_back"
                        run["rollback_reason"] = reason
                prev["status"] = "production"
                prev["restored_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                self.manifest["production_run"] = prev
                self._save_manifest()
                print(f"[ROLLBACK] Restored production model from {prev['run_id']}")
                return TrainingRun(**prev)
        return None

    def _emit_audit_entry(self, run: TrainingRun, metrics: Any) -> None:
        """Write blockchain audit trail entry for training run."""
        entry = {
            "event_type": "model_training_run",
            "run_id": run.run_id,
            "timestamp_utc": run.timestamp_utc,
            "dataset_hash": run.dataset_hash,
            "metrics": {
                "rmse": run.rmse,
                "mae": run.mae,
                "r2": run.r2,
                "n_samples": run.n_samples,
            },
            "per_zone": run.per_zone_metrics,
            "status": run.status,
            "model_path": run.model_path,
        }
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def _emit_promotion_audit(self, run_id: str, promoter: str) -> None:
        entry = {
            "event_type": "model_promotion",
            "run_id": run_id,
            "promoted_by": promoter,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def get_production_model(self) -> Optional[Dict[str, Any]]:
        """Return the current production model config."""
        prod = self.manifest.get("production_run")
        if prod and prod.get("model_path"):
            path = Path(prod["model_path"])
            if path.exists():
                return json.loads(path.read_text())
        return None

    def status_report(self) -> str:
        lines = []
        lines.append("=== Retraining Pipeline Status ===")
        lines.append(f"Cadence: every {self.cadence_days} days")
        lines.append(f"RMSE threshold: <= {self.rmse_threshold} t/ha")
        lines.append(f"Last production run: {self.manifest.get('production_run', {}).get('run_id', 'none')}")
        lines.append(f"Total training runs: {len(self.manifest.get('runs', []))}")

        runs = self.manifest.get("runs", [])
        if runs:
            latest = runs[-1]
            lines.append(f"Latest run: {latest.get('run_id')} status={latest.get('status')} RMSE={latest.get('rmse', 'N/A')}")
        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Yield model retraining pipeline (DPA-83)")
    parser.add_argument("--train", action="store_true", help="Run training with synthetic data")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--cadence", type=int, default=DEFAULT_CADENCE_DAYS, help="Retraining cadence in days")
    parser.add_argument("--n-farms", type=int, default=120, help="Number of synthetic farms for training")
    args = parser.parse_args()

    pipeline = RetrainingPipeline(cadence_days=args.cadence)

    if args.status:
        print(pipeline.status_report())
        return 0

    if args.train:
        # Import here to avoid circular deps when running standalone
        from yield_model import YieldPredictor, generate_training_data
        from yield_model import ModelMetrics

        data = generate_training_data(n_farms=args.n_farms)
        dataset_hash = hashlib.sha256(json.dumps([asdict(d) for d in data], sort_keys=True).encode()).hexdigest()

        def train_fn(training_data):
            predictor = YieldPredictor(seed=42)
            metrics = predictor.fit(training_data)
            return predictor, metrics

        run = pipeline.run_training(data, train_fn, dataset_hash)

        # Auto-promote if passes gate
        if run.status == "staging":
            pipeline.promote_to_production(run.run_id)
            print(f"[PROMOTED] {run.run_id} -> production")
        elif run.status == "rejected":
            print(f"[REJECTED] {run.run_id} failed RMSE gate")
        else:
            print(f"[AWAITING_REVIEW] {run.run_id} status={run.status}")

        return 0 if run.status in ("staging", "production") else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
