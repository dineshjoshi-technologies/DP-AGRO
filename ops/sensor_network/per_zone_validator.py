#!/usr/bin/env python3
"""
Per-zone model validation — DPA-83.

Validates yield prediction models independently per agro-climatic zone,
ensuring each zone model meets governance thresholds:
  - RMSE <= 0.15 t/ha per zone
  - MAE <= 0.10 t/ha per zone
  - R² >= 0.85 per zone

Also computes:
  - Zone-specific feature importance (via permutation)
  - Cross-zone transferability analysis
  - Validation report with governance sign-off readiness
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATION_DIR = REPO_ROOT / "ops" / "models" / "validations"


@dataclass
class ZoneValidationResult:
    zone: str
    n_test_samples: int
    rmse: float
    mae: float
    r2: float
    passes_governance: bool
    feature_importance: Dict[str, float]
    errors: List[float]  # per-sample prediction errors
    timestamp_utc: str


class PerZoneValidator:
    """Validates yield models per agro-climatic zone."""

    GOVERNANCE_THRESHOLDS = {
        "rmse": 0.15,
        "mae": 0.10,
        "r2_min": 0.85,
        "min_samples": 30,  # Minimum test samples for stable R² (increased from 20)
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or self.GOVERNANCE_THRESHOLDS
        self.validation_history: List[Dict[str, Any]] = []

    def validate_zone(self, model, zone: str,
                      test_features: List[Any],
                      test_labels: List[float],
                      feature_names: List[str]) -> ZoneValidationResult:
        """Validate a model on test data for a specific zone.

        Args:
            model: Object with .predict(x) method
            zone: Zone identifier (e.g., "zone-A")
            test_features: List of feature vectors (or FarmFeatures objects)
            test_labels: List of actual yield values
            feature_names: Names matching model feature order
        """
        predictions = []
        errors = []

        for feat, actual in zip(test_features, test_labels):
            if hasattr(feat, "to_vector") or hasattr(feat, "__dict__"):
                # FarmFeatures-like object
                if hasattr(feat, "to_vector"):
                    x = feat.to_vector()
                else:
                    from yield_model import features_to_vector
                    x = features_to_vector(feat)
            else:
                x = feat
            # YieldPredictor.predict requires (farm_id, zone, features) — detect and adapt
            if hasattr(model, "zone_models"):
                # Pass the original feature object so YieldPredictor can call .to_vector()
                pred = model.predict(f"test-farm", zone, feat)
            else:
                pred = model.predict(x) if hasattr(model, "predict") else model.predict([x])
            predictions.append(pred)
            errors.append(pred - actual)

        # Compute metrics
        n = len(test_labels)
        if n == 0:
            return ZoneValidationResult(
                zone=zone, n_test_samples=0, rmse=float("inf"), mae=float("inf"),
                r2=0.0, passes_governance=False, feature_importance={},
                errors=[], timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )

        rmse = math.sqrt(sum(e ** 2 for e in errors) / n)
        mae = sum(abs(e) for e in errors) / n
        mean_actual = sum(test_labels) / n
        ss_res = sum(e ** 2 for e in errors)
        ss_tot = sum((a - mean_actual) ** 2 for a in test_labels)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else (1.0 if rmse == 0 else 0.0)

        # Feature importance via permutation (simplified)
        importance = self._compute_feature_importance(model, test_features, test_labels, feature_names)

        passes = (
            rmse <= self.thresholds["rmse"] and
            mae <= self.thresholds["mae"] and
            r2 >= self.thresholds["r2_min"] and
            n >= self.thresholds.get("min_samples", 30)
        )

        result = ZoneValidationResult(
            zone=zone,
            n_test_samples=n,
            rmse=rmse,
            mae=mae,
            r2=r2,
            passes_governance=passes,
            feature_importance=importance,
            errors=errors[:100],  # Cap for storage
            timestamp_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

        self.validation_history.append(asdict(result))
        self._save_validation(result)

        return result

    def _compute_feature_importance(self, model, test_features: List[Any],
                                     test_labels: List[float],
                                     feature_names: List[str]) -> Dict[str, float]:
        """Compute feature importance via permutation correlation."""
        import random
        import copy
        rng = random.Random(42)
        n_samples = len(test_labels)
        if n_samples == 0:
            return {}

        # Compute base predictions using correct zone for each feature
        base_pred = []
        for f in test_features:
            if hasattr(model, "zone_models"):
                # Use the feature's actual zone, not hardcoded "zone-A"
                zone = f.zone if hasattr(f, "zone") else "zone-A"
                base_pred.append(model.predict("test-farm", zone, f))
            else:
                base_pred.append(model.predict(f) if hasattr(model, "predict") else model.predict([f])[0])
        base_mse = sum((p - a) ** 2 for p, a in zip(base_pred, test_labels)) / n_samples

        importance = {}
        n_features = len(feature_names)

        for fi in range(n_features):
            # Deep copy to avoid mutating original test features
            shuffled = [copy.deepcopy(f) for f in test_features]
            # Permute one feature column
            for i, seq in enumerate(shuffled):
                if hasattr(seq, "__dict__"):
                    vec = seq.to_vector()
                    idx = rng.randint(0, n_samples - 1)
                    other_vec = test_features[idx].to_vector()
                    vec[fi] = other_vec[fi]
                    # Reconstruct with permuted value using actual field names
                    shuffled[i] = type(seq)(
                        farm_id=seq.farm_id,
                        zone=seq.zone,
                        season_week=seq.season_week,
                        soil_moisture_mean=vec[0],
                        soil_moisture_std=vec[1],
                        soil_ph_mean=vec[2],
                        soil_ec_mean=vec[3],
                        temp_mean=vec[4],
                        temp_max=vec[5],
                        temp_min=vec[6],
                        humidity_mean=vec[7],
                        rainfall_total_mm=vec[8],
                        ndvi_current=vec[9],
                        ndvi_lag7=vec[10],
                        ndvi_lag14=vec[11],
                        ndvi_trend=vec[12],
                        growing_degree_days=vec[13],
                        soil_water_deficit=vec[14],
                    )
                else:
                    seq = list(seq)
                    idx = rng.randint(0, n_samples - 1)
                    seq[fi] = test_features[idx][fi]
                    shuffled[i] = seq

            # Compute permuted MSE using correct zone
            perm_pred = []
            for x in shuffled:
                if hasattr(model, "zone_models"):
                    zone = x.zone if hasattr(x, "zone") else "zone-A"
                    perm_pred.append(model.predict("test-farm", zone, x))
                else:
                    perm_pred.append(model.predict(x) if hasattr(model, "predict") else model.predict([x])[0])
            perm_mse = sum((p - a) ** 2 for p, a in zip(perm_pred, test_labels)) / n_samples
            importance[feature_names[fi]] = (perm_mse - base_mse) / max(base_mse, 1e-10)

        return importance

    def _save_validation(self, result: ZoneValidationResult) -> None:
        """Save validation report to disk."""
        VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
        path = VALIDATION_DIR / f"validation_{result.zone}_{result.timestamp_utc.replace(':', '-')}.json"
        with open(path, "w") as f:
            json.dump(asdict(result), f, indent=2)

    def validate_all_zones(self, model, zone_data: Dict[str, Tuple[List[Any], List[float], List[str]]]) -> Dict[str, ZoneValidationResult]:
        """Validate model across all zones.

        Args:
            model: Fitted YieldPredictor
            zone_data: {zone: (test_features, test_labels, feature_names)}
        """
        results = {}
        for zone, (features, labels, feature_names) in zone_data.items():
            result = self.validate_zone(model, zone, features, labels, feature_names)
            results[zone] = result
            status = "PASS" if result.passes_governance else "FAIL"
            print(f"  {zone}: RMSE={result.rmse:.4f} MAE={result.mae:.4f} R2={result.r2:.4f} [{status}]")

        return results

    def generate_governance_report(self, zone_results: Dict[str, ZoneValidationResult]) -> str:
        """Generate governance sign-off report."""
        lines = [
            "=" * 60,
            "DPA-83 — Per-Zone Model Validation Report",
            f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
            "=" * 60,
            "",
            "GOVERNANCE THRESHOLDS:",
            f"  RMSE <= {self.thresholds['rmse']} t/ha",
            f"  MAE <= {self.thresholds['mae']} t/ha",
            f"  R²  >= {self.thresholds['r2_min']}",
            "",
            "ZONE RESULTS:",
        ]

        all_pass = True
        for zone, result in sorted(zone_results.items()):
            status = "PASS" if result.passes_governance else "FAIL"
            if not result.passes_governance:
                all_pass = False
            lines.append(f"  {zone}:")
            lines.append(f"    Samples:     {result.n_test_samples}")
            lines.append(f"    RMSE:        {result.rmse:.4f} t/ha")
            lines.append(f"    MAE:         {result.mae:.4f} t/ha")
            lines.append(f"    R²:          {result.r2:.4f}")
            lines.append(f"    Governance:  {status}")

            if result.feature_importance:
                top_feats = sorted(result.feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                lines.append(f"    Top features: {', '.join(f'{k}({v:.3f})' for k, v in top_feats)}")
            lines.append("")

        lines.append("=" * 60)
        lines.append(f"OVERALL: {'READY FOR PRODUCTION' if all_pass else 'REQUIRES REVIEW'}")
        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Per-zone model validation (DPA-83)")
    parser.add_argument("--report", action="store_true", help="Generate governance report")
    args = parser.parse_args()

    if args.report:
        validator = PerZoneValidator()
        print("No validation data found. Run training first.")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
