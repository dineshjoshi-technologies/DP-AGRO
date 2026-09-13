#!/usr/bin/env python3
"""Tests for edge_runtime.py — edge gateway buffer, quality gate, audit hash (DPA-82)."""
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from edge_runtime import EdgeReading, EdgeBuffer, quality_gate, emit_batch_audit_hash, now_iso
from edge_anomaly import fit_isolation_forest
from ingest_validator import EnvelopeValidator


def make_reading(farm="FARM-001", sensor="SOIL-ZA-001", quality=0):
    return EdgeReading(
        farm_id=farm,
        sensor_id=sensor,
        timestamp_utc="2026-09-06T12:00:00Z",
        measurement={"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8},
        quality_flag=quality,
    )


def test_edge_buffer_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db = Path(tmp.name)
    try:
        buf = EdgeBuffer(db, "test-key-phase1")
        r = make_reading()
        rid = buf.enqueue(r)
        assert rid > 0
        assert buf.pending() == 1
        drained = buf.drain()
        assert len(drained) == 1
        assert drained[0].farm_id == "FARM-001"
        assert buf.pending() == 0
    finally:
        db.unlink(missing_ok=True)


def test_edge_buffer_integrity_check():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db = Path(tmp.name)
    try:
        buf = EdgeBuffer(db, "test-key-integrity")
        r = make_reading()
        buf.enqueue(r)
        # Tamper with the database row
        conn = buf.conn
        conn.execute("UPDATE buffer SET payload = X'FFFFFFFF' WHERE id = 1")
        conn.commit()
        # Should raise on tampered data
        try:
            buf.drain()
            assert False, "Expected integrity check to fail"
        except ValueError:
            pass  # Expected
    finally:
        db.unlink(missing_ok=True)


def test_quality_gate_nominal():
    d = fit_isolation_forest(n_estimators=20, sample_size=64, seed=42)
    v = EnvelopeValidator()
    import random
    rng = random.Random(99)
    normals = [make_reading(farm="FARM-001", sensor="SOIL-ZA-001", quality=0) for _ in range(20)]
    for r in normals:
        r.measurement = {"type": "soil", "moisture": round(rng.uniform(0.25, 0.31), 4),
                         "ec": round(rng.uniform(0.42, 0.48), 4), "ph": round(rng.uniform(6.5, 7.1), 4)}
    d.fit(normals)
    r = make_reading(farm="FARM-001", sensor="SOIL-ZA-001", quality=0)
    r.measurement = {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}
    result = quality_gate(r, d, v)
    assert result == 0  # nominal


def test_quality_gate_rejects_quality_flag_1():
    d = fit_isolation_forest(n_estimators=10, sample_size=32, seed=42)
    v = EnvelopeValidator()
    r = make_reading(quality=1)
    result = quality_gate(r, d, v)
    assert result == 1  # degraded


def test_quality_gate_fails_closed_on_model_error():
    # Unfitted detector on bad input should fail closed
    d = fit_isolation_forest(n_estimators=10, sample_size=32, seed=42)
    v = EnvelopeValidator()
    r = make_reading(quality=0)
    # Detector is unfitted => fails closed
    result = quality_gate(r, d, v)
    assert result == 1


def test_emit_batch_audit_hash():
    batch = [make_reading(sensor=f"SOIL-ZA-{i:02d}") for i in range(1, 6)]
    logs = []
    emit_batch_audit_hash(batch, lambda e: logs.append(e))
    assert len(logs) == 1
    entry = logs[0]
    assert entry["event"] == "audit_batch_hash"
    assert "batch_sha256" in entry
    assert entry["record_count"] == 5
    assert entry["farm_id"] == "FARM-001"


def test_all_farms_have_valid_readings():
    v = EnvelopeValidator()
    d = fit_isolation_forest(n_estimators=20, sample_size=64, seed=42)
    import random
    rng = random.Random(99)
    normals = []
    # Use sensor IDs from the 100-farm registry
    for i in range(1, 21):
        fid = f"FARM-{i:03d}"
        zone_tag = ["ZA", "ZB", "ZC", "ZD"][(i - 1) % 4]
        sid = f"SOIL-{zone_tag}-{i:03d}"
        for _ in range(5):
            r = make_reading(farm=fid, sensor=sid, quality=0)
            r.measurement = {"type": "soil", "moisture": round(rng.uniform(0.25, 0.31), 4),
                             "ec": round(rng.uniform(0.42, 0.48), 4), "ph": round(rng.uniform(6.5, 7.1), 4)}
            normals.append(r)
    d.fit(normals)
    for i in range(1, 21):
        fid = f"FARM-{i:03d}"
        zone_tag = ["ZA", "ZB", "ZC", "ZD"][(i - 1) % 4]
        sid = f"SOIL-{zone_tag}-{i:03d}"
        r = make_reading(farm=fid, sensor=sid, quality=0)
        r.measurement = {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}
        result = quality_gate(r, d, v)
        assert result == 0, f"{fid} should pass quality gate"


if __name__ == "__main__":
    tests = [
        test_edge_buffer_roundtrip,
        test_edge_buffer_integrity_check,
        test_quality_gate_nominal,
        test_quality_gate_rejects_quality_flag_1,
        test_quality_gate_fails_closed_on_model_error,
        test_emit_batch_audit_hash,
        test_all_farms_have_valid_readings,
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
