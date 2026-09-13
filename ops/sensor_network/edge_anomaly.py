#!/usr/bin/env python3
"""
Isolation-forest anomaly detection for edge gateways — Phase 1 (DPA-82).

Implements the isolation forest described in governance policy §3.3 and
gateway_config.yaml (n_estimators=100, contamination=0.02, rolling 7-day window).
Pure stdlib implementation suitable for gateway-class hardware (≥4GB RAM per
DPA-80 §2.1 edge gateway spec); no numpy/scipy dependency at the edge.

Model: each tree recursively partitions the feature subspace with random
features/thresholds; path length to isolation estimates anomaly density.
Shorter average path length ⇒ higher anomaly score.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence

# Feature vector order per gateway_config.yaml anomaly_detection.feature_order
FEATURE_ORDER = ["moisture", "ec", "ph", "temperature_c", "humidity", "rainfall_mm", "ndvi_delta"]

FEATURE_MEANS = {
    "moisture": 0.28, "ec": 0.45, "ph": 6.8, "temperature_c": 26.0,
    "humidity": 68.0, "rainfall_mm": 0.4, "ndvi_delta": 0.0,
}


def _features(reading: Any) -> List[float]:
    m = reading.measurement if hasattr(reading, "measurement") else reading.get("measurement", {})
    out = []
    for name in FEATURE_ORDER:
        v = m.get(name)
        if v is None:
            v = FEATURE_MEANS[name]  # neutral value keeps vector aligned
        out.append(float(v))
    return out


class _Node:
    __slots__ = ("feature", "threshold", "left", "right", "size")

    def __init__(self, feature: Optional[int] = None, threshold: Optional[float] = None,
                 left: Optional["_Node"] = None, right: Optional["_Node"] = None,
                 size: int = 0):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.size = size


class _Tree:
    def __init__(self, subsample: Sequence[List[float]], height_limit: int, rng: random.Random):
        self.root = self._build(subsample, 0, height_limit, rng)

    def _build(self, pts: Sequence[List[float]], depth: int, limit: int, rng: random.Random) -> _Node:
        if depth >= limit or len(pts) <= 1:
            return _Node(size=len(pts))
        lo = [min(p[i] for p in pts) for i in range(len(pts[0]))]
        hi = [max(p[i] for p in pts) for i in range(len(pts[0]))]
        candidates = [i for i in range(len(lo)) if lo[i] < hi[i]]
        if not candidates:
            return _Node(size=len(pts))
        f = rng.choice(candidates)
        split = rng.uniform(lo[f], hi[f])
        left = [p for p in pts if p[f] < split]
        right = [p for p in pts if p[f] >= split]
        if not left or not right:
            return _Node(size=len(pts))
        return _Node(f, split, self._build(left, depth + 1, limit, rng),
                     self._build(right, depth + 1, limit, rng), len(pts))

    def path_length(self, x: List[float]) -> float:
        node, depth = self.root, 0
        while node.feature is not None:
            node = node.left if x[node.feature] < node.threshold else node.right
            depth += 1
        return depth + _c(node.size)


def _c(n: int) -> float:
    if n <= 1:
        return 0.0
    return 2.0 * (math.log(n - 1) + 0.5772156649) - 2.0 * (n - 1) / n


def fit_isolation_forest(n_estimators: int = 100, sample_size: int = 256,
                         seed: int = 42) -> "AnomalyDetector":
    """Create an unfitted detector; call .fit(history) before scoring."""
    return AnomalyDetector(n_estimators=n_estimators, sample_size=sample_size, seed=seed)


class AnomalyDetector:
    """Isolation forest scoring rolling history; score ≥ threshold ⇒ outlier."""

    def __init__(self, n_estimators: int = 100, sample_size: int = 256,
                 contamination: float = 0.02, seed: int = 42):
        self.n_estimators = n_estimators
        self.sample_size = sample_size
        self.contamination = contamination
        self.rng = random.Random(seed)
        self.trees: List[_Tree] = []
        self._history: List[List[float]] = []
        self.threshold: Optional[float] = None
        self.fitted = False

    def fit(self, history: Sequence[Any], contamination: Optional[float] = None) -> None:
        """Fit on recent readings (rolling 7-day window upstream).
        Uses standard isolation forest anomaly score: s(x,n) = 2^(-E[h(x)]/c(n)).
        Higher score => more anomalous.
        """
        contam = self.contamination if contamination is None else contamination
        pts = [_features(r) for r in history] or [_features({})]
        self._history = list(pts)
        limit = math.ceil(math.log2(max(len(pts), 2)))
        self.trees = [
            _Tree(self.rng.sample(pts, min(self.sample_size, len(pts))), limit, self.rng)
            for _ in range(self.n_estimators)
        ]
        n_trees = len(self.trees) or 1
        scores = sorted([2.0 ** (-sum(t.path_length(p) for t in self.trees) / n_trees / _c(max(len(pts), 2)))
                         for p in pts], reverse=True)
        cutoff = max(0, min(len(scores) - 1, int(math.ceil(len(scores) * contam)) - 1))
        self.threshold = scores[cutoff] if scores else 0.5
        self.fitted = True

    def _score_points(self, pts: List[List[float]]) -> List[float]:
        n = len(self.trees) or 1
        return [2.0 ** (-sum(t.path_length(p) for t in self.trees) / n / _c(max(len(self._history), 2)))
                for p in pts]

    def score(self, reading: Any) -> float:
        x = _features(reading)
        n = len(self.trees) or 1
        return 2.0 ** (-sum(t.path_length(x) for t in self.trees) / n / _c(max(len(self._history), 2)))

    def is_outlier(self, reading: Any) -> bool:
        """True when anomalous. Fails closed: an unfitted detector flags everything."""
        if not self.fitted:
            return True
        return self.score(reading) >= self.threshold

    def update_history(self, reading: Any) -> None:
        """Append to rolling window; refit is triggered upstream per retrain.cadence_days."""
        self._history.append(_features(reading))
        if len(self._history) > 10000:
            self._history = self._history[-10000:]