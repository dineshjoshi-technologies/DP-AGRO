# Shared Verification Protocol

## Purpose
Shared verification scripts for AI model validation and blockchain audit trail matching between MLOps and Blockchain Integration workstreams.

## Location
`/verification/`

## Current Status
- [x] Basic schema registry established
- [x] Edge anomaly detection prototype complete
- [x] MLflow model registry with promotion gates
- [ ] Blockchain audit trail smart contract audited
- [ ] Drift detection dashboards live
- [ ] Incident runbook tested (tabletop)
- [ ] Farmer consent flow UAT complete

## Verification Script Contents
```bash
#!/bin/bash
# Shared verification protocol for cross-initiative validation

# Schema compliance validation
./verify_schema_compliance.sh

# Blockchain audit trail matching
./match_audit_trail.sh

# Model promotion gates validation
./validate_model_promotion.sh
```

## Verification Report Templates
- `/verification/ingest_report.md`
- `/verification/model_validation_report.md`
- `/verification/audit_trail_report.md`

## Integration Requirements

### Blockchain Integration (DPA-79) Verification Needs:
- Sensor batch ingest hashes for audit trail blockchain entries
- Model training run hashes for validation
- Model promotion/demotion event logs
- Prediction batch output merkle roots

### AI-Agriculture Convergence Verification:
- Schema compliance reports for all sensor data
- Edge anomaly detection validation
- MLflow registry state snapshots
- Drift detection dashboard metrics