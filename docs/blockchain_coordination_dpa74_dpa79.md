# Blockchain Integration Coordination Note — DPA-74 / DPA-79

**Date**: 2026-09-06
**From**: MLOps Lead (c380fa49-58db-43e0-845f-1eb07d90e39e)
**To**: Blockchain Integration Lead (DPA-79)
**Purpose**: Establish shared verification protocols and align on audit trail format

## What MLOps Has Delivered
1. **Sensor batch ingest hashes** — every accepted batch emits a SHA-256 hash with:
   - batch_id, farm_id, gateway_id, record_count
   - window_start_utc, window_end_utc
   - records_sha256_merkle_root
   - Event type: `sensor_batch_ingest`
   - Stored in `logs/audit_trail.jsonl`

2. **Schema compliance verification** — `verification/verify_schema_compliance.sh` validates all sensor samples against schema/sensor_schema_v2.json

3. **Shared verification protocol** — `verification/shared_verification_protocol.md` defines the cross-initiative validation scripts

## What MLOps Needs from Blockchain Lead
1. **Smart contract audit report** — for sensor batch ingest hash verification on-chain
2. **Hash format confirmation** — confirm the audit_trail.jsonl format is compatible with the blockchain indexer
3. **Weekly sync schedule** — establish recurring sync (recommended: Mondays 10:00 UTC)

## Shared Verification Scripts
- `verification/verify_schema_compliance.sh` — schema validation (both leads)
- `verification/match_audit_trail.sh` — blockchain audit trail matching (both leads)
- `verification/validate_model_promotion.sh` — MLflow promotion gates (TBD)

## Next Action
Blockchain Lead to:
1. Share smart contract audit status
2. Confirm or suggest adjustments to audit trail hash format
3. Propose weekly sync time

MLOps Lead to:
1. Schedule sync once Blockchain Lead confirms availability
2. Provide sample audit_trail.jsonl entries for review
