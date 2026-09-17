# DPA-182 Integration Checklist

## Pre-Integration (Complete)
- [x] Audit event schema defined (spec_compliant_events.json)
- [x] ETL accepts --audit-events flag
- [x] audit_gap_minutes KPI computes correctly
- [x] Gas cost estimates documented
- [x] Smart contract integration spec written
- [x] Test suite: 4/4 passing

## Post-DPA-79 Completion
- [ ] Smart contract deployed (address shared by Blockchain Lead)
- [ ] ETL wired to write audit events to blockchain audit table
- [ ] Grafana panel for audit-gap metric added
- [ ] Alert routing: gap > 15 min → ticket to Blockchain team
- [ ] First weekly sync completed with Blockchain Lead
- [ ] Shared verification protocol executed
- [ ] Production ETL run against live Postgres

## Files
- `smart_contract_integration_spec.md` - Full integration spec
- `metrics-dashboard/scripts/metrics-etl.py` - ETL with audit support
- `metrics-dashboard/verification/audit-trail-validator.py` - Validator
- `metrics-dashboard/verification/gas-calculator.py` - Gas estimator
- `metrics-dashboard/postgres/metrics_schema.sql` - DB schema
