#!/usr/bin/env python3
"""
Drift monitoring for yield prediction models — DPA-83.

Implements:
  - Population Stability Index (PSI) for feature distribution drift (policy §4.2: PSI < 0.1)
  - Concept drift detection via performance tracking
  - Per-zone drift reports
  - Automated alerting when thresholds exceeded

Governance alignment: policy §4.2 (drift detection: PSI < 0.1 weekly),
§7 (model drift alert: auto-rollback + retrain trigger within 1h).
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
DRIFT_LOG = REPO_ROOT / "logs" / "drift_monitor.jsonl"
DRIFT_REPORTS = REPO_ROOT / "ops" / "models" / "drift_reports"


# ---------------------------------------------------------------------------
# PSI computation
# ---------------------------------------------------------------------------

@dataclass
class FeatureBin:
    feature_name: str
    bin_edges: List[float]
    ref_counts: List[int]
    curr_counts: List[int]


def _compute_psi(ref_dist: List[float], curr_dist: List[float],
                  bins: int = 10, min_bin_count: int = 5) -> Tuple[float, List[FeatureBin]]:
    """Compute Population Stability Index between reference and current distributions.

    PSI = sum((curr_pct - ref_pct) * ln(curr_pct / ref_pct))
    Interpretation:
      < 0.1:  No significant change
      0.1-0.2: Moderate change
      > 0.2:  Significant change (drift detected)

    Args:
        ref_dist: Reference distribution values.
        curr_dist: Current distribution values.
        bins: Number of bins for histogram.
        min_bin_count: Minimum expected count per bin to avoid extreme PSI
            from empty bins with small samples. Bins below this threshold
            use a smoothed estimate.
    """
    if not ref_dist or not curr_dist:
        return 0.0, []

    all_vals = ref_dist + curr_dist
    min_v, max_v = min(all_vals), max(all_vals)
    if max_v == min_v:
        return 0.0, []

    edge_step = (max_v - min_v) / bins
    edges = [min_v + i * edge_step for i in range(bins + 1)]

    def _hist(vals: List[float]) -> List[int]:
        h = [0] * bins
        for v in vals:
            idx = min(int((v - min_v) / edge_step), bins - 1)
            h[idx] += 1
        return h

    ref_h = _hist(ref_dist)
    curr_h = _hist(curr_dist)

    n_ref = len(ref_dist) or 1
    n_curr = len(curr_dist) or 1

    # Smooth bins with counts below min_bin_count to avoid extreme PSI
    expected_ref = n_ref / bins
    expected_curr = n_curr / bins
    smoothed_ref = []
    smoothed_curr = []
    for i in range(bins):
        r = ref_h[i]
        c = curr_h[i]
        if r < min_bin_count:
            r = max(r, expected_ref * 0.5)
        if c < min_bin_count:
            c = max(c, expected_curr * 0.5)
        smoothed_ref.append(r)
        smoothed_curr.append(c)

    psi = 0.0
    bins_info = []

    for i in range(bins):
        ref_pct = smoothed_ref[i] / n_ref
        curr_pct = smoothed_curr[i] / n_curr
        # Avoid log(0)
        if ref_pct < 1e-10:
            ref_pct = 1e-10
        if curr_pct < 1e-10:
            curr_pct = 1e-10
        psi += (curr_pct - ref_pct) * math.log(curr_pct / ref_pct)
        bins_info.append((edges[i], edges[i + 1], ref_h[i], curr_h[i]))

    return psi, bins_info


def compute_psi_per_feature(ref_features: List[Dict[str, float]],
                            curr_features: List[Dict[str, float]],
                            n_bins: int = 10) -> Tuple[Dict[str, float], List]:
    """Compute PSI for each feature dimension.

    Returns:
        (psi_dict, bins_info) where psi_dict maps feature name -> PSI value
        and bins_info is the binning detail from the last feature computed.
    """
    if not ref_features or not curr_features:
        return {}, []

    feature_names = ref_features[0].keys()
    result = {}
    bins_info: List = []

    for fname in feature_names:
        ref_vals = [f[fname] for f in ref_features]
        curr_vals = [f[fname] for f in curr_features]
        psi, bins_info = _compute_psi(ref_vals, curr_vals, bins=n_bins)
        result[fname] = psi

    return result, bins_info


# ---------------------------------------------------------------------------
# Drift monitor
# ---------------------------------------------------------------------------

@dataclass
class DriftAlert:
    alert_type: str  # "feature_drift" | "concept_drift" | "performance_degradation"
    zone: str
    severity: str  # "low" | "medium" | "high"
    psi: float
    threshold: float
    message: str
    timestamp_utc: str


class DriftMonitor:
    """Monitors data drift and concept drift for yield prediction models."""

    PSI_THRESHOLD_MODERATE = 0.1
    PSI_THRESHOLD_SIGNIFICANT = 0.2
    PERFORMACE_DEGRADATION_PCT = 0.10  # 10%
    MIN_SAMPLES_FOR_PSI = 20  # Minimum samples for reliable PSI computation

    def __init__(self, psi_threshold: float = PSI_THRESHOLD_MODERATE,
                 calibration_factor: float = 1.0):
        self.psi_threshold = psi_threshold
        self.calibration_factor = calibration_factor
        self.reference_distributions: Dict[str, List[Dict[str, float]]] = {}
        self.alerts: List[DriftAlert] = []
        self.history: List[Dict[str, Any]] = []

    def set_reference(self, zone: str, features: List[Dict[str, float]]) -> None:
        """Set the reference distribution for a zone (from training data)."""
        self.reference_distributions[zone] = features

    def check_drift(self, zone: str, current_features: List[Dict[str, float]],
                    current_rmse: Optional[float] = None,
                    baseline_rmse: Optional[float] = None) -> Dict[str, Any]:
        """Check for drift in the given zone. Returns drift report."""
        report = {
            "zone": zone,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "psi_per_feature": {},
            "overall_psi": 0.0,
            "alerts": [],
            "drift_detected": False,
        }

        n_curr = len(current_features)
        if n_curr < self.MIN_SAMPLES_FOR_PSI:
            report["warning"] = (
                f"Insufficient samples ({n_curr}) for reliable PSI computation "
                f"(minimum: {self.MIN_SAMPLES_FOR_PSI}). Results may be unstable."
            )

        ref = self.reference_distributions.get(zone)
        if not ref:
            report["warning"] = f"No reference distribution for zone {zone}"
            # Still check RMSE degradation even without reference distribution
            if current_rmse is not None and baseline_rmse is not None:
                degradation = (current_rmse - baseline_rmse) / max(baseline_rmse, 1e-10)
                if degradation > self.PERFORMACE_DEGRADATION_PCT:
                    alert = DriftAlert(
                        alert_type="performance_degradation", zone=zone, severity="high",
                        psi=degradation, threshold=self.PERFORMACE_DEGRADATION_PCT,
                        message=f"RMSE degraded {degradation:.1%} (now {current_rmse:.4f} vs baseline {baseline_rmse:.4f})",
                        timestamp_utc=report["timestamp_utc"],
                    )
                    report["alerts"].append(asdict(alert))
                    report["drift_detected"] = True
            self.history.append(report)
            self._log_drift_report(report)
            return report

        psi_per_feature, _ = compute_psi_per_feature(ref, current_features)
        report["psi_per_feature"] = psi_per_feature

        # Apply zone-specific calibration factor
        calibrated_psi = {}
        for fname, psi in psi_per_feature.items():
            calibrated_psi[fname] = psi / max(self.calibration_factor, 0.1)
        report["psi_per_feature_calibrated"] = calibrated_psi

        # Overall PSI = mean of per-feature PSIs (calibrated)
        psi_values = list(calibrated_psi.values())
        report["overall_psi"] = sum(psi_values) / len(psi_values) if psi_values else 0.0
        report["overall_psi_raw"] = report["overall_psi"] * self.calibration_factor

        # Effective threshold adjusted by calibration
        effective_threshold = self.psi_threshold * self.calibration_factor

        # Per-feature alerts
        for fname, psi in calibrated_psi.items():
            if psi >= effective_threshold * 2:
                alert = DriftAlert(
                    alert_type="feature_drift", zone=zone, severity="high",
                    psi=psi, threshold=effective_threshold * 2,
                    message=f"Critical drift in {fname} (calibrated PSI={psi:.4f})",
                    timestamp_utc=report["timestamp_utc"],
                )
                report["alerts"].append(asdict(alert))
                report["drift_detected"] = True
            elif psi >= effective_threshold:
                alert = DriftAlert(
                    alert_type="feature_drift", zone=zone, severity="medium",
                    psi=psi, threshold=effective_threshold,
                    message=f"Moderate drift in {fname} (calibrated PSI={psi:.4f})",
                    timestamp_utc=report["timestamp_utc"],
                )
                report["alerts"].append(asdict(alert))
                report["drift_detected"] = True

        # Concept drift check (RMSE degradation)
        if current_rmse is not None and baseline_rmse is not None:
            degradation = (current_rmse - baseline_rmse) / max(baseline_rmse, 1e-10)
            if degradation > self.PERFORMACE_DEGRADATION_PCT:
                alert = DriftAlert(
                    alert_type="performance_degradation", zone=zone, severity="high",
                    psi=degradation, threshold=self.PERFORMACE_DEGRADATION_PCT,
                    message=f"RMSE degraded {degradation:.1%} (now {current_rmse:.4f} vs baseline {baseline_rmse:.4f})",
                    timestamp_utc=report["timestamp_utc"],
                )
                report["alerts"].append(asdict(alert))
                report["drift_detected"] = True

        # Log to drift history
        self.history.append(report)
        self._log_drift_report(report)

        return report

    def _log_drift_report(self, report: Dict[str, Any]) -> None:
        """Append drift report to audit log."""
        DRIFT_LOG.parent.mkdir(parents=True, exist_ok=True)
        DRIFT_REPORTS.mkdir(parents=True, exist_ok=True)

        # Save individual report
        report_path = DRIFT_REPORTS / f"drift_{report['zone']}_{report['timestamp_utc'].replace(':', '-')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Append to JSONL log
        with open(DRIFT_LOG, "a") as f:
            f.write(json.dumps({
                "zone": report["zone"],
                "timestamp": report["timestamp_utc"],
                "overall_psi": report["overall_psi"],
                "drift_detected": report["drift_detected"],
                "n_alerts": len(report["alerts"]),
            }, sort_keys=True) + "\n")

    def get_recommendation(self, report: Dict[str, Any]) -> str:
        """Return action recommendation based on drift report."""
        if not report.get("drift_detected"):
            return "NO_ACTION: No significant drift detected."

        high_alerts = [a for a in report.get("alerts", []) if a.get("severity") == "high"]
        if high_alerts:
            return "RETRAIN: Significant drift detected. Trigger retraining pipeline immediately."

        return "MONITOR: Moderate drift detected. Increase monitoring frequency."

    def status_summary(self) -> str:
        lines = ["=== Drift Monitor Status ==="]
        if not self.history:
            # Load from persistent log file
            self._load_history()
        if not self.history:
            lines.append("No drift reports yet.")
            return "\n".join(lines)

        latest = self.history[-1]
        ts = latest.get('timestamp_utc') or latest.get('timestamp', 'unknown')
        lines.append(f"Latest report: {ts}")
        lines.append(f"Overall PSI: {latest.get('overall_psi', 0):.4f}")
        lines.append(f"Drift detected: {latest.get('drift_detected', False)}")
        lines.append(f"Alerts: {len(latest.get('alerts', []))}")
        lines.append(f"Recommendation: {self.get_recommendation(latest)}")
        return "\n".join(lines)

    def _load_history(self) -> None:
        """Load drift history from the persistent JSONL log file."""
        if not DRIFT_LOG.exists():
            return
        with open(DRIFT_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.history.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue


# ---------------------------------------------------------------------------
# Main / CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Drift monitor (DPA-83)")
    parser.add_argument("--check", action="store_true", help="Run drift check on current data")
    parser.add_argument("--status", action="store_true", help="Show drift history")
    parser.add_argument("--zone", type=str, default=None, help="Specific zone to check")
    args = parser.parse_args()

    monitor = DriftMonitor()

    if args.status:
        print(monitor.status_summary())
        return 0

    if args.check:
        # Synthetic check — in production this loads live feature streams
        print("Drift check requires reference distributions. Use --status to view history.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
