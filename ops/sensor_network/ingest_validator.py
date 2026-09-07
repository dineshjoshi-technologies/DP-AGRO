#!/usr/bin/env python3
"""
Cloud ingest validator + quality gate — Phase 1 crop sensor network (DPA-82).

Enforces governance policy §3.1 at the ingest boundary:
  - JSON Schema validation against schema/sensor_message_v1.json (mandatory
    fields: farm_id, sensor_id, timestamp_utc, measurement, quality_flag)
  - registry checks: farm_id/sensor_id must exist in farm_registry.json
  - quality gate: reject quality_flag != 0; reject >3σ from rolling 7-day median
  - audit entries: every accepted batch appends a SHA-256 batch hash to
    logs/audit_trail.jsonl for blockchain matching (policy §5, §6 access:
    Blockchain Lead R(audit))

Shared by the ingest service and verification/verify_schema_compliance.sh.
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = REPO_ROOT / "schema" / "sensor_message_v1.json"
DEFAULT_REGISTRY = REPO_ROOT / "ops" / "sensor_network" / "farm_registry.json"
DEFAULT_AUDIT = Path(os.environ.get("AUDIT_LOG", REPO_ROOT / "logs" / "audit_trail.jsonl"))

QUALITY_FLAG_NOMINAL = 0
SIGMA_GATE = 3.0       # policy §3.1: reject >3σ from rolling 7-day median
BASELINE_DAYS = 7


class EnvelopeValidator:
    """Schema + registry validation shared by edge runtime and cloud ingest."""

    def __init__(self, schema_path: Path = DEFAULT_SCHEMA, registry_path: Path = DEFAULT_REGISTRY,
                 check_registry: bool = True):
        with open(schema_path) as f:
            self.schema = json.load(f)
        self.validator = jsonschema.Draft7Validator(self.schema, format_checker=jsonschema.FormatChecker())
        self.farm_ids: set = set()
        self.sensor_ids: Dict[str, set] = {}
        if check_registry and registry_path.exists():
            with open(registry_path) as f:
                reg = json.load(f)
            for farm in reg.get("farms", []):
                fid = farm["farm_id"]
                self.farm_ids.add(fid)
                sensors = farm.get("sensors", {})
                for s in sensors.values():
                    self.sensor_ids.setdefault(fid, set()).update(s.get("sensor_ids", []))
        self.check_registry = check_registry

    def validate_envelope(self, env: Dict[str, Any], farm_id: Optional[str] = None,
                          sensor_id: Optional[str] = None) -> bool:
        """True when the envelope is schema-valid AND registry-consistent.

        farm_id/sensor_id overrides let the edge runtime validate against its own
        farm context before the registry is fully replicated to the device.
        """
        if not self.validator.is_valid(env):
            return False
        fid = farm_id if farm_id is not None else env["farm_id"]
        sid = sensor_id if sensor_id is not None else env["sensor_id"]
        if self.check_registry:
            if fid not in self.farm_ids:
                return False
            if sid not in self.sensor_ids.get(fid, set()):
                return False
        return True

    def schema_error(self, env: Dict[str, Any]) -> Optional[str]:
        err = next(self.validator.iter_errors(env), None)
        return f"{list(err.absolute_path)}: {err.message}" if err else None


class RollingBaseline:
    """Rolling 7-day median baseline per (farm_id, sensor_id, channel)."""

    def __init__(self):
        self._series: Dict[Tuple[str, str, str], List[Tuple[datetime, float]]] = {}

    def _key(self, env: Dict[str, Any], channel: str) -> Tuple[str, str, str]:
        return (env["farm_id"], env["sensor_id"], channel)

    def add(self, env: Dict[str, Any], channels: Dict[str, float], ts: datetime) -> None:
        for ch, v in channels.items():
            self._series.setdefault(self._key(env, ch), []).append((ts, v))
            if len(self._series[self._key(env, ch)]) > 4032:  # 7d of 15-min readings
                self._series[self._key(env, ch)] = self._series[self._key(env, ch)][-4032:]

    def median_sigma(self, env: Dict[str, Any], channel: str,
                     now: datetime) -> Tuple[Optional[float], Optional[float]]:
        cutoff = now - timedelta(days=BASELINE_DAYS)
        vals = [v for t, v in self._series.get(self._key(env, channel), []) if t >= cutoff]
        if len(vals) < 8:
            return None, None
        med = statistics.median(vals)
        var = statistics.median([abs(v - med) for v in vals]) * 1.4826  # MAD -> sigma est.
        return med, (math_sqrt(var) if False else var) if False else (var ** 0.5)


def math_sqrt(x: float) -> float:
    return x ** 0.5


class IngestPipeline:
    """Cloud ingest boundary: validate -> registry check -> quality gates -> audit."""

    def __init__(self, validator: Optional[EnvelopeValidator] = None,
                 audit_log: Path = DEFAULT_AUDIT):
        self.validator = validator or EnvelopeValidator()
        self.baseline = RollingBaseline()
        self.audit_log = audit_log
        self.stats: Dict[str, int] = {"received": 0, "accepted": 0, "rejected": 0}

    def ingest(self, envelopes: Iterable[Dict[str, Any]],
               now: Optional[datetime] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process a batch; returns (accepted, rejection_reasons)."""
        now = now or datetime.now(timezone.utc)
        accepted: List[Dict[str, Any]] = []
        rejections: List[str] = []
        for env in envelopes:
            self.stats["received"] += 1
            reason = self._check(env, now)
            if reason:
                self.stats["rejected"] += 1
                rejections.append(reason)
                continue
            self.stats["accepted"] += 1
            self._update_baseline(env, now)
            accepted.append(env)
        if accepted:
            self._audit_batch(accepted)
        return accepted, rejections

    def _check(self, env: Dict[str, Any], now: datetime) -> Optional[str]:
        # Strip edge-internal fields (anomaly_score, buffered) before schema validation
        clean = {k: v for k, v in env.items()
                 if k in ("farm_id", "sensor_id", "timestamp_utc", "measurement", "quality_flag")}
        if not self.validator.validate_envelope(clean):
            err = self.validator.schema_error(clean)
            return f"schema/registry: {err or 'registry mismatch'}"
        if env["quality_flag"] != QUALITY_FLAG_NOMINAL:
            return f"quality_flag={env['quality_flag']} (policy §3.1: reject != 0)"
        for ch, v in self._channels(env).items():
            med, sigma = self.baseline.median_sigma(env, ch, now)
            if med is not None and abs(v - med) > SIGMA_GATE * sigma:
                return f"{ch}={v} >3σ from rolling 7-day median ({med:.3f})"
        return None

    @staticmethod
    def _channels(env: Dict[str, Any]) -> Dict[str, float]:
        m = env.get("measurement", {})
        return {k: float(v) for k, v in m.items()
                if k not in ("type", "source", "unit") and isinstance(v, (int, float))}

    def _update_baseline(self, env: Dict[str, Any], now: datetime) -> None:
        ts = datetime.fromisoformat(env["timestamp_utc"].replace("Z", "+00:00"))
        self.baseline.add(env, self._channels(env), ts)

    def _audit_batch(self, accepted: List[Dict[str, Any]]) -> None:
        """Append the batch hash entry consumed by verification/match_audit_trail.sh
        (event_type: sensor_batch_ingest — one of the four critical event types)."""
        records = sorted(accepted, key=lambda e: e["timestamp_utc"])
        record_hashes = [hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
                         for r in records]
        body = {
            "event_type": "sensor_batch_ingest",
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "farm_id": records[0]["farm_id"],
            "record_count": len(records),
            "window_start_utc": records[0]["timestamp_utc"],
            "window_end_utc": records[-1]["timestamp_utc"],
            "records_sha256_merkle_root": hashlib.sha256("".join(record_hashes).encode()).hexdigest(),
        }
        body["batch_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a") as f:
            f.write(json.dumps(body, sort_keys=True) + "\n")


def load_envelopes(paths: Iterable[str]) -> List[Dict[str, Any]]:
    out = []
    for p in paths:
        with open(p) as f:
            out.append(json.load(f))
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Validate sensor envelope JSON files against policy §3.1")
    ap.add_argument("files", nargs="+", help="JSON envelope files")
    ap.add_argument("--audit", action="store_true", help="append batch audit entry")
    args = ap.parse_args()
    pipe = IngestPipeline(audit_log=DEFAULT_AUDIT if args.audit else Path(os.devnull))
    accepted, rejected = pipe.ingest(load_envelopes(args.files))
    print(f"accepted={len(accepted)} rejected={len(rejected)}")
    for r in rejected:
        print(f"  REJECT: {r}")
    sys.exit(1 if rejected else 0)