#!/usr/bin/env python3
"""Tests for ingest_validator.py — schema + registry validation (DPA-82)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ops", "sensor_network"))

from ingest_validator import EnvelopeValidator, IngestPipeline


def make_soil_env(farm="FARM-001", sensor="SOIL-ZA-001", quality=0):
    return {
        "farm_id": farm,
        "sensor_id": sensor,
        "timestamp_utc": "2026-09-06T12:00:00Z",
        "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8},
        "quality_flag": quality,
    }


def test_valid_soil_envelope():
    v = EnvelopeValidator()
    assert v.validate_envelope(make_soil_env()) is True


def test_valid_weather_envelope():
    v = EnvelopeValidator()
    env = {
        "farm_id": "FARM-001",
        "sensor_id": "WX-ZA-001",
        "timestamp_utc": "2026-09-06T12:00:00Z",
        "measurement": {"type": "weather", "temperature_c": 26.0, "humidity": 68.0, "rainfall_mm": 0.0},
        "quality_flag": 0,
    }
    assert v.validate_envelope(env) is True


def test_valid_spectral_envelope():
    v = EnvelopeValidator()
    env = {
        "farm_id": "FARM-001",
        "sensor_id": "SPEC-ZA-001",
        "timestamp_utc": "2026-09-06T12:00:00Z",
        "measurement": {"type": "spectral", "ndvi": 0.65, "source": "edge"},
        "quality_flag": 0,
    }
    assert v.validate_envelope(env) is True


def test_invalid_farm_id():
    v = EnvelopeValidator()
    env = make_soil_env(farm="FARM-999")
    assert v.validate_envelope(env) is False


def test_invalid_sensor_id():
    v = EnvelopeValidator()
    env = make_soil_env(sensor="FAKE-ZA-001")
    assert v.validate_envelope(env) is False


def test_quality_flag_1_rejected_by_validator():
    v = EnvelopeValidator()
    env = make_soil_env(quality=1)
    # Schema allows quality_flag=1; validator passes schema but pipeline rejects
    assert v.validate_envelope(env) is True


def test_missing_required_field():
    v = EnvelopeValidator()
    env = {"farm_id": "FARM-001", "sensor_id": "SOIL-ZA-001"}
    assert v.validate_envelope(env) is False


def test_schema_error_message():
    v = EnvelopeValidator()
    env = {"farm_id": "FARM-001"}
    err = v.schema_error(env)
    assert err is not None
    assert "sensor_id" in err or "timestamp_utc" in err or "measurement" in err


def test_ingest_pipeline_accepts_valid_batch():
    pipe = IngestPipeline()
    # Use sensor IDs from the 100-farm registry (each farm has unique IDs)
    batch = [
        {"farm_id": "FARM-001", "sensor_id": "SOIL-ZA-001", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-002", "sensor_id": "SOIL-ZB-002", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-003", "sensor_id": "SOIL-ZC-003", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-004", "sensor_id": "SOIL-ZD-004", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-005", "sensor_id": "SOIL-ZA-005", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-006", "sensor_id": "SOIL-ZB-006", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-007", "sensor_id": "SOIL-ZC-007", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-008", "sensor_id": "SOIL-ZD-008", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-009", "sensor_id": "SOIL-ZA-009", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
        {"farm_id": "FARM-010", "sensor_id": "SOIL-ZB-010", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
    ]
    accepted, rejected = pipe.ingest(batch)
    assert len(accepted) == 10
    assert len(rejected) == 0


def test_ingest_pipeline_accepts_mid_registry_farm():
    """FARM-050 is in zone-B with sensor SOIL-ZB-050."""
    pipe = IngestPipeline()
    batch = [
        {"farm_id": "FARM-050", "sensor_id": "SOIL-ZB-050", "timestamp_utc": "2026-09-06T12:00:00Z",
         "measurement": {"type": "soil", "moisture": 0.28, "ec": 0.45, "ph": 6.8}, "quality_flag": 0},
    ]
    accepted, rejected = pipe.ingest(batch)
    assert len(accepted) == 1
    assert len(rejected) == 0


def test_ingest_pipeline_rejects_quality_flag_1():
    pipe = IngestPipeline()
    batch = [make_soil_env(quality=0), make_soil_env(quality=1)]
    accepted, rejected = pipe.ingest(batch)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert "quality_flag=1" in rejected[0]


def test_ingest_pipeline_rejects_unknown_farm():
    pipe = IngestPipeline()
    batch = [make_soil_env(farm="FARM-XXX")]
    accepted, rejected = pipe.ingest(batch)
    assert len(accepted) == 0
    assert len(rejected) == 1


def test_all_100_farms_registered():
    v = EnvelopeValidator()
    expected = {f"FARM-{i:03d}" for i in range(1, 101)}
    assert expected.issubset(v.farm_ids)
    assert len(v.farm_ids) == 100


def test_all_100_farm_sensor_ids_valid():
    """Verify every farm has at least one valid soil sensor."""
    v = EnvelopeValidator()
    for i in range(1, 101):
        fid = f"FARM-{i:03d}"
        assert fid in v.farm_ids, f"{fid} not in registry"
        sensors = v.sensor_ids.get(fid, set())
        assert len(sensors) > 0, f"{fid} has no sensors"


if __name__ == "__main__":
    tests = [
        test_valid_soil_envelope,
        test_valid_weather_envelope,
        test_valid_spectral_envelope,
        test_invalid_farm_id,
        test_invalid_sensor_id,
        test_quality_flag_1_rejected_by_validator,
        test_missing_required_field,
        test_schema_error_message,
        test_ingest_pipeline_accepts_valid_batch,
        test_ingest_pipeline_accepts_mid_registry_farm,
        test_ingest_pipeline_rejects_quality_flag_1,
        test_ingest_pipeline_rejects_unknown_farm,
        test_all_100_farms_registered,
        test_all_100_farm_sensor_ids_valid,
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
