#!/usr/bin/env python3
"""Audit trail validator for AI-Agriculture blockchain integration (DPA-84).

Validates blockchain audit events against the schema defined in
DPA-84#document-metrics-audit-trail-spec §2.1.

Usage:
    python3 audit-trail-validator.py --events testdata/audit_events.json --schema spec §2.1
    python3 audit-trail-validator.py --events events.json --validate --report report.json

Exit codes:
    0 - All events valid
    1 - Validation errors found
    2 - Bad input
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone


VALID_EVENT_TYPES = {
    "sensor_batch_ingest",
    "model_training",
    "model_promotion",
    "prediction_batch",
    "model_training_run",  # legacy format alias
}


def normalize_event(event):
    """Normalize event to spec format (§2.1), handling legacy keys."""
    normalized = {}
    # eventType: spec key or legacy event_type
    normalized["eventType"] = event.get("eventType", event.get("event_type", "unknown"))
    # eventId: generate from batch_hash/run_id if missing
    normalized["eventId"] = event.get("eventId", hashlib.sha256(
        json.dumps(event, sort_keys=True).encode()
    ).hexdigest()[:36])
    # timestamp: spec key or legacy timestamp_utc
    normalized["timestamp"] = event.get("timestamp", event.get("timestamp_utc", ""))
    # actor: default to "unknown" if missing
    normalized["actor"] = event.get("actor", "unknown")
    # payloadHash: spec key or legacy batch_hash
    normalized["payloadHash"] = event.get("payloadHash", event.get("batch_hash", ""))
    # Copy optional fields through
    for key in ["prevEventRef", "signature"]:
        if key in event:
            normalized[key] = event[key]
    return normalized


def validate_event(event, index):
    """Validate a single audit event against the spec schema."""
    errors = []

    required_fields = ["eventType", "eventId", "timestamp", "actor", "payloadHash"]
    for field in required_fields:
        if field not in event:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    # Validate eventType
    if event["eventType"] not in VALID_EVENT_TYPES:
        errors.append(
            f"Invalid eventType '{event['eventType']}' at index {index}. "
            f"Expected one of: {sorted(VALID_EVENT_TYPES)}"
        )

    # Validate eventId is UUID-like
    if len(event["eventId"]) != 36 or event["eventId"].count("-") != 4:
        errors.append(f"Invalid eventId format at index {index}: {event['eventId']}")

    # Validate timestamp is ISO8601
    try:
        ts = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            errors.append(f"Timestamp at index {index} lacks timezone info")
    except (ValueError, TypeError):
        errors.append(f"Invalid timestamp at index {index}: {event['timestamp']}")

    # Validate payloadHash is sha256 (64 hex chars)
    if not isinstance(event["payloadHash"], str) or len(event["payloadHash"]) != 64:
        errors.append(f"Invalid payloadHash format at index {index}")
    elif not all(c in "0123456789abcdefABCDEF" for c in event["payloadHash"]):
        errors.append(f"payloadHash contains non-hex characters at index {index}")

    # Optional: validate prevEventRef format if present and not null
    if "prevEventRef" in event and event["prevEventRef"] is not None:
        if len(event["prevEventRef"]) != 36:
            errors.append(f"Invalid prevEventRef format at index {index}")

    # Optional: validate signature format if present
    if "signature" in event:
        sig = event["signature"]
        if not isinstance(sig, str) or len(sig) not in (130, 132):
            errors.append(f"Invalid signature format at index {index}")

    return errors


def validate_chain_integrity(events):
    """Validate the merkle chain linkage (prevEventRef ordering)."""
    errors = []
    event_ids = {e["eventId"] for e in events}

    for i, event in enumerate(events):
        if "prevEventRef" in event:
            prev_id = event["prevEventRef"]
            if prev_id not in event_ids:
                # First event may not have a prevEventRef (genesis)
                if i > 0:
                    errors.append(
                        f"Event {event['eventId']} references unknown prevEventRef {prev_id}"
                    )

    return errors


def compute_diagnostics(events):
    """Compute aggregate diagnostics for the event batch."""
    if not events:
        return {"total_events": 0, "event_type_counts": {}, "time_range": None}

    type_counts = {}
    timestamps = []
    for e in events:
        t = e.get("eventType", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        if "timestamp" in e:
            try:
                ts = datetime.fromisoformat(str(e["timestamp"]).replace("Z", "+00:00"))
                timestamps.append(ts)
            except (ValueError, TypeError):
                pass

    time_range = None
    if timestamps:
        time_range = {
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
            "span_minutes": (max(timestamps) - min(timestamps)).total_seconds() / 60,
        }

    return {
        "total_events": len(events),
        "event_type_counts": type_counts,
        "time_range": time_range,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audit trail validator (DPA-84, spec §2.1)"
    )
    parser.add_argument("--events", required=True, help="JSON file with audit events")
    parser.add_argument(
        "--validate", action="store_true", help="Run validation and report errors"
    )
    parser.add_argument("--report", help="Write validation report to file")
    args = parser.parse_args()

    # Load events
    try:
        with open(args.events) as fp:
            data = json.load(fp)
        if isinstance(data, dict) and "records" in data:
            events = data["records"]
        elif isinstance(data, list):
            events = data
        else:
            print(f"Error: {args.events} must contain a JSON array or {{'records': [...]}}", file=sys.stderr)
            sys.exit(2)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading events: {e}", file=sys.stderr)
        sys.exit(2)

    # Validate
    all_errors = []
    normalized_events = [normalize_event(e) for e in events]
    for i, event in enumerate(normalized_events):
        errors = validate_event(event, i)
        all_errors.extend(errors)

    chain_errors = validate_chain_integrity(normalized_events)
    all_errors.extend(chain_errors)

    # Diagnostics
    diagnostics = compute_diagnostics(events)

    # Report
    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "valid": len(all_errors) == 0,
        "error_count": len(all_errors),
        "errors": all_errors[:100],  # Cap at 100 errors
        "diagnostics": diagnostics,
    }

    if args.report:
        with open(args.report, "w") as fp:
            json.dump(report, fp, indent=2)
        print(f"Report written to {args.report}")

    print(json.dumps(report, indent=2))

    if all_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
