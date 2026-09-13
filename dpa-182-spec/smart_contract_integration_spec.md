# DPA-182: Blockchain Audit Trail Smart Contract Integration Spec

## Purpose
Define the integration between the MLOps metrics ETL pipeline and the blockchain audit trail smart contract (to be implemented by Blockchain Integration Lead, DPA-79).

## 1. Event Schema (Agreed)

Per DPA-84#document-metrics-audit-trail-spec §2.1:

```json
{
  "eventType": "sensor_batch_ingest|model_training|model_promotion|prediction_batch",
  "eventId": "<uuid-v4>",
  "timestamp": "<ISO8601 UTC>",
  "actor": "<agent_id>",
  "payloadHash": "<sha256 hex>",
  "prevEventRef": "<uuid-v4|null>",
  "signature": "<secp256k1 hex>"
}
```

### Event Type Details

| eventType | payloadHash source | prevEventRef | Notes |
|-----------|-------------------|--------------|-------|
| `sensor_batch_ingest` | SHA-256 of batched sensor records (merkle root) | Previous event ID | Emitted per farm per window |
| `model_training` | SHA-256 of training dataset commit hash | Previous event ID | Emitted per training run |
| `model_promotion` | SHA-256 of model artifact URI | Previous event ID | Emitted on staging→prod promotion |
| `prediction_batch` | Merkle root of prediction batch | Previous event ID | Batched for gas efficiency |

## 2. Smart Contract Interface

Per DPA-84#document-metrics-audit-trail-spec §2.2:

```solidity
function logSensorBatch(bytes32 hash, uint256 timestamp, bytes32 farmId) external
function logModelTraining(bytes32 configHash, bytes32 datasetHash, bytes memory metrics) external
function logModelPromotion(address modelAddr, bytes32 version) external
function logPredictions(bytes32 merkleRoot, uint256 count) external
function verifySchemaCompliance(bytes32 hash) external view returns (bool)
```

## 3. ETL Integration Points

### 3.1 Audit Events Input
The ETL accepts blockchain audit events via `--audit-events` flag:

```bash
python3 metrics-etl.py \
  --sensor-ingest ingest/sensor_online.json \
  --model-monitor monitor/yield_runs.json \
  --activity-logs logs/labor_hours.json \
  --audit-events blockchain/audit_events.json \
  --dsn "${PG_DSN}"
```

### 3.2 audit_gap_minutes Computation
```python
# In metrics-etl.py, compute gap between latest sensor batch and latest blockchain event
latest_sensor_ts = max(event["timestamp"] for event in sensor_events)
latest_blockchain_ts = max(event["timestamp"] for event in audit_events)
audit_gap_minutes = (latest_sensor_ts - latest_blockchain_ts).total_seconds() / 60
```

### 3.3 Alert Threshold
- `audit_gap_minutes > 15` → alert triggered (configurable via `AUDIT_GAP_ALERT_MINUTES`)

## 4. Gas Cost Estimates

| Operation | Gas (single) | Gas (batched/50) | Weekly ETH (batched) |
|-----------|-------------|-------------------|---------------------|
| sensor_batch_ingest | 65,000 | 120,000 (merkle) | 0.000065 |
| model_training | 80,000 | 80,000 | 0.000020 |
| model_promotion | 70,000 | 70,000 | 0.000020 |
| prediction_batch | 55,000 | 120,000 (merkle) | 0.000160 |
| **Total** | **270,000** | **390,000** | **0.000265** |

**Savings with batching: 94.5%** (vs. 0.0065 ETH/week single writes)

## 5. Integration Checklist

- [ ] Smart contract deployed by Blockchain Lead (DPA-79)
- [ ] Contract address shared with MLOps Lead
- [ ] ETL updated to write to blockchain audit table
- [ ] Grafana panel for audit-gap metric added
- [ ] Alert routing: gap > 15 min → ticket to Blockchain team
- [ ] Shared verification protocol documented
- [ ] First weekly sync completed

## 6. Dependencies

- **DPA-79** (Blockchain Integration Workstream) — smart contract implementation
- **DPA-84** (metrics tracking) — parent issue, ETL pipeline already complete

## 7. Ready for Integration

All MLOps-side artifacts are complete and validated:
- `metrics-dashboard/scripts/metrics-etl.py` — accepts `--audit-events`
- `metrics-dashboard/verification/audit-trail-validator.py` — validates spec §2.1
- `metrics-dashboard/verification/gas-calculator.py` — gas estimates
- `metrics-dashboard/scripts/testdata/spec_compliant_events.json` — test data
- `metrics-dashboard/postgres/metrics_schema.sql` — database schema

**Once DPA-79 completes the smart contract, DPA-182 integration can be completed in 1-2 days.**
