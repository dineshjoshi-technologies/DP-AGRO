#!/usr/bin/env python3
"""
Edge gateway runtime — Phase 1 crop sensor network (DPA-82).

Implements governance policy v1.0 section 3.3 on every gateway:
  - 48h offline buffering with at-rest encryption (section 2, P1):
    AES-256-CBC encrypt-then-MAC (HMAC-SHA256) via openssl; production builds
    use AES-256-GCM per gateway_config.yaml, this reference runtime uses an
    equivalent encrypt-then-MAC construction so the property (confidentiality
    + integrity) is testable without vendor firmware.
  - local anomaly detection: isolation forest, flag -> quality_flag=1 (fail-closed
    on model error)
  - SHA-256 batch hashing (canonical JSON) emitted per flushed batch for the
    blockchain audit trail (section 5)

Sensor ingestion is abstracted behind a source callable so the same runtime runs
against BLE/serial device feeds on the gateway or the deterministic simulator in
tests. Envelopes validate against schema/sensor_message_v1.json before buffering.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ops" / "sensor_network"))

from edge_anomaly import AnomalyDetector  # noqa: E402
from ingest_validator import EnvelopeValidator  # noqa: E402

DEFAULT_DB = Path(os.environ.get("EDGE_DB", REPO_ROOT / "ops" / "sensor_network" / "edge_buffer.db"))
DEFAULT_LOG = Path(os.environ.get("EDGE_LOG", REPO_ROOT / "ops" / "sensor_network" / "edge_runtime.jsonl"))
DEFAULT_KEY = os.environ.get("EDGE_AES_KEY", "phase1-dev-key-change-me")  # dev-only default; prod key via KMS
BUFFER_HOURS = 48  # policy §3.3


@dataclass
class EdgeReading:
    farm_id: str
    sensor_id: str
    timestamp_utc: str
    measurement: Dict[str, Any]
    quality_flag: int  # 0 nominal, 1 degraded (flagged locally)
    anomaly_score: Optional[float] = None
    buffered: bool = False


# --- at-rest crypto: AES-256-CBC encrypt-then-MAC(HMAC-SHA256) -----------------

def _derive(key_material: str, salt: str) -> tuple[bytes, bytes]:
    """PBKDF2-HMAC-SHA256 (10k iters) -> (32-byte AES key, 32-byte HMAC key)."""
    out = subprocess.run(
        ["openssl", "kdf", "-keylen", "64", "-kdfopt", "digest:SHA256",
         "-kdfopt", f"pass:{key_material}", "-kdfopt",
         f"hexsalt:{hashlib.sha256(salt.encode()).hexdigest()[:32]}", "-kdfopt",
         "iter:10000", "PBKDF2"],
        capture_output=True, check=True,
    ).stdout
    return out[:32], out[32:64]


def _aes_cbc(key: bytes, iv: bytes, data: bytes, decrypt: bool = False) -> bytes:
    args = ["openssl", "enc", "-aes-256-cbc", "-K", key.hex(), "-iv", iv.hex()]
    if decrypt:
        args.insert(2, "-d")
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout


def _pad(data: bytes) -> bytes:
    n = 16 - (len(data) % 16)
    return data + bytes([n]) * n


def _unpad(data: bytes) -> bytes:
    n = data[-1]
    if not 1 <= n <= 16 or data[-n:] != bytes([n]) * n:
        raise ValueError("bad padding")
    return data[:-n]


class EdgeBuffer:
    """48h durable buffer, encrypted at rest (policy §2 P1, §3.3)."""

    def __init__(self, db_path: Path, key_material: str):
        self.db_path = db_path
        self.enc_key, self.mac_key = _derive(key_material, db_path.name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS buffer ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " ts TEXT NOT NULL,"        # reading timestamp (pruning window basis)
            " iv BLOB NOT NULL,"
            " mac BLOB NOT NULL,"
            " payload BLOB NOT NULL)"   # ciphertext
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_buffer_ts ON buffer(ts)")
        self.conn.commit()

    def _seal(self, plaintext: bytes) -> tuple[bytes, bytes, bytes]:
        iv = os.urandom(16)
        ct = _aes_cbc(self.enc_key, iv, _pad(plaintext))
        mac = hmac_mod.new(self.mac_key, iv + ct, hashlib.sha256).digest()
        return iv, mac, ct

    def _open(self, iv: bytes, mac: bytes, ct: bytes) -> bytes:
        if not hmac_mod.compare_digest(mac, hmac_mod.new(self.mac_key, iv + ct, hashlib.sha256).digest()):
            raise ValueError("integrity check failed")
        return _unpad(_aes_cbc(self.enc_key, iv, ct, decrypt=True))

    def enqueue(self, reading: EdgeReading) -> int:
        plaintext = json.dumps(reading.__dict__, sort_keys=True).encode()
        iv, mac, ct = self._seal(plaintext)
        cur = self.conn.execute(
            "INSERT INTO buffer (ts, iv, mac, payload) VALUES (?,?,?,?)",
            (reading.timestamp_utc, iv, mac, ct),
        )
        self.conn.commit()
        self._prune()
        return cur.lastrowid

    def requeue(self, readings: List[EdgeReading]) -> None:
        for r in readings:
            self.enqueue(r)

    def _prune(self) -> None:
        """Drop rows older than the 48h window (overflow: drop_oldest_with_audit_note)."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=BUFFER_HOURS)).isoformat()
        cur = self.conn.execute("DELETE FROM buffer WHERE ts < ?", (cutoff,))
        if cur.rowcount:
            log_entry({"event": "buffer_overflow_prune", "dropped": cur.rowcount,
                       "policy": "drop_oldest_with_audit_note"})
        self.conn.commit()

    def pending(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM buffer").fetchone()[0]

    def drain(self) -> List[EdgeReading]:
        rows = self.conn.execute("SELECT id, iv, mac, payload FROM buffer ORDER BY id ASC").fetchall()
        out = []
        for _rid, iv, mac, ct in rows:
            d = json.loads(self._open(iv, mac, ct))
            out.append(EdgeReading(**d))
        self.conn.execute("DELETE FROM buffer")
        self.conn.commit()
        return out


def log_entry(entry: Dict[str, Any]) -> None:
    log_path = Path(os.environ.get("EDGE_LOG", DEFAULT_LOG))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps({"ts": now_iso(), **entry}, sort_keys=True) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# --- core loop ----------------------------------------------------------------


def start_loop(
    source: Callable[[], Iterable[EdgeReading]],
    conn: Callable[[List[EdgeReading]], bool],
    detector: AnomalyDetector,
    validator: EnvelopeValidator,
    max_batches: int,
    log: Callable[[Dict[str, Any]], None],
    buffer: Optional[EdgeBuffer] = None,
) -> int:
    """Buffer readings, flush batches when the uplink allows, emit audit hashes.

    Returns the number of records still pending (buffered) at loop end.
    """
    buffer = buffer or EdgeBuffer(DEFAULT_DB, DEFAULT_KEY)
    batches = 0
    online = True
    for reading in source():
        reading.quality_flag = quality_gate(reading, detector, validator)
        buffer.enqueue(reading)
        if online and buffer.pending() > 0:
            batch = buffer.drain()
            if conn(batch):
                batches += 1
                emit_batch_audit_hash(batch, log)
                log({"event": "batch_flushed", "records": len(batch),
                     "pending": buffer.pending()})
            else:
                online = False  # outage: subsequent readings buffer up to 48h
                buffer.requeue(batch)
        if batches >= max_batches:
            break
    return buffer.pending()


def quality_gate(reading: EdgeReading, detector: AnomalyDetector, validator: EnvelopeValidator) -> int:
    """0 = nominal, 1 = degraded. Fails closed on model/validation errors (§3.1)."""
    try:
        # Strip dataclass-only fields before schema validation (v1 schema has
        # additionalProperties: false, so anomaly_score/buffered would reject).
        envelope = {
            k: v for k, v in reading.__dict__.items()
            if k in ("farm_id", "sensor_id", "timestamp_utc", "measurement", "quality_flag")
        }
        if not validator.validate_envelope(envelope):
            return 1
        if detector.is_outlier(reading):
            return 1
        return 0
    except Exception as e:
        log_entry({"event": "quality_gate_error", "error": str(e), "sensor_id": reading.sensor_id})
        return 1


def emit_batch_audit_hash(batch: List[EdgeReading], log: Callable[[Dict[str, Any]], None]) -> None:
    """SHA-256 batch hash per policy §5 over canonical JSON of:
    batch_id, farm_id, gateway_id, record_count, window_start_utc, window_end_utc,
    records_sha256_merkle_root. The cloud ingest relay records this hash as the
    immutable blockchain audit entry for the batch."""
    records = sorted((r.__dict__ for r in batch), key=lambda d: d["timestamp_utc"])
    record_hashes = [hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
                     for r in records]
    merkle = hashlib.sha256("".join(record_hashes).encode()).hexdigest()
    body = {
        "batch_id": f"{records[0]['farm_id']}-{now_iso()}",
        "farm_id": records[0]["farm_id"],
        "gateway_id": f"GW-{records[0]['farm_id']}",
        "record_count": len(records),
        "window_start_utc": records[0]["timestamp_utc"],
        "window_end_utc": records[-1]["timestamp_utc"],
        "records_sha256_merkle_root": merkle,
    }
    batch_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    log({"event": "audit_batch_hash", "batch_sha256": batch_hash, **body})


if __name__ == "__main__":
    print("edge_runtime is exercised via tests/test_edge_pipeline.py (simulated device feeds)")
    sys.exit(0)