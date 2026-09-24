# AI Data Governance Policy \-- AI-Agriculture Convergence

## 1. Purpose & Scope
This policy governs all AI initiatives under the AI-Agriculture Convergence program, including:
- Crop monitoring models (NDVI, soil moisture, pest detection)
- Yield prediction models (RMSE target ≤ 0.15 t/ha)
- Sensor network management (IoT soil, weather, spectral sensors)
- Model training, validation, and deployment pipelines

Applies to all data flowing through the AI pipeline: raw sensor feeds, derived features, model artifacts, predictions, and audit logs.

--- 

## 2. Data Classification
| Tier | Description | Examples | Retention | Encryption |
|------|-------------|----------|-----------|------------|
| **P0 – Restricted** | Farmer PII, land records, financials | Farmer KYC, land titles, yield contracts | 7 years + legal hold | AES-256 at rest, TLS 1.3 in transit |
| **P1 – Sensitive** | Raw sensor data, model weights | IoT telemetry, trained model binaries, SHAP values | 5 years | AES-256 at rest, TLS 1.3 in transit |
| **P2 – Internal** | Aggregated metrics, dashboards | Farm-level yield forecasts, regional RMSE reports | 3 years | AES-256 at rest |
| **P3 – Public** | Published research, open datasets | Anonymized benchmark datasets, methodology papers | Indefinite | Optional |

--- 

## 3. Sensor Data Governance (Phase 1)
### 3.1 Collection Standards
- **Frequency**: Soil moisture/EC/pH — 15-min intervals; Weather — 5-min; Spectral (NDVI) — daily via satellite + hourly via edge
- **Schema**: Protobuf with mandatory fields: `farm_id`, `sensor_id`, `timestamp_utc`, `measurement`, `quality_flag`
- **Quality gates**: Reject readings with `quality_flag != 0` or >3σ from rolling 7-day median

### 3.2 Coverage Targets
- **Phase 1 (Weeks 4-6)**: ≥ 10 pilot farms, ≥ 90% sensor uptime, ≥ 95% schema compliance
- **Phase 2 (Weeks 7-10)**: ≥ 100 farms, ≥ 95% uptime, ≥ 98% schema compliance

### 3.3 Edge Processing
- Edge gateway buffers 48h during connectivity loss
- Local anomaly detection (isolation forest) flags outliers before cloud ingest
- Hash of each batch recorded to blockchain audit trail (see §6)

--- 

## 4. Model Training & Validation Data
### 4.1 Training Data Requirements
- Minimum 3 growing seasons of historical yield + weather + soil data per agro-climatic zone
- Stratified split: 70/15/15 (train/val/test) by farm, not by sample
- Data versioning via DVC; each training run pins dataset commit hash

### 4.2 Validation Protocol
| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| **Yield RMSE** | ≤ 0.15 t/ha | Test set, per-crop, per-zone |
| **MAE** | ≤ 0.10 t/ha | Test set |
| **R²** | ≥ 0.85 | Test set |
| **Prediction latency** | ≤ 200 ms/farm | P99, batch inference |
| **Drift detection** | PSI < 0.1 | Weekly on live features |

### 4.3 Model Registry
- All models registered in MLflow with: git commit, dataset hash, hyperparams, metrics, `governance_tier` tag
- Promotion: `staging` → `production` requires 2 approvals (MLOps Lead + Domain Expert)
- Rollback: automatic if RMSE degrades >10% vs baseline over 7-day window

--- 

## 5. Blockchain Audit Trail Integration
Per coordination with Blockchain Integration lead (DPA-79):
- **Immutable log entries** for:
  1. Sensor batch ingest (hash + timestamp + farm_id)
  2. Model training run (config hash + dataset hash + metrics)
  3. Model promotion/demotion events
  4. Prediction batch outputs (merkle root of predictions)
- **Smart contract** validates: schema compliance, uptime SLA, metric thresholds
- **Verification protocol**: Weekly sync with Blockchain lead; shared verification scripts in `/verification`

--- 

## 6. Access Control & Roles
| Role | P0 | P1 | P2 | P3 | Actions |
|------|----|----|----|----|---------|
| MLOps Lead | R/W | R/W | R/W | R/W | Policy admin, model promotion, incident response |
| Data Engineers | — | R/W | R/W | R | Pipeline ops, schema evolution |
| Domain Agronomists | — | R | R/W | R | Feature review, validation labeling |
| Blockchain Lead | — | R (audit) | R | R | Audit trail verification |
| Farmers (data subjects) | R (own) | — | — | R | Access own data via portal |

--- 

## 7. Incident Response
- **P0 breach**: Notify within 4h, contain within 24h, board report within 72h
- **Model drift alert**: Auto-rollback + retrain trigger within 1h
- **Sensor network outage**: Failover to satellite-only mode; log gap in audit trail

--- 

## 8. Metrics & Reporting (Tracked Weekly)
| Metric | Target | Source |
|--------|--------|--------|
| Sensor data coverage (% farms) | ≥ 90% (Phase 1), ≥ 95% (Phase 2) | IoT platform |
| Yield prediction RMSE | ≤ 0.15 t/ha | Model monitoring |
| Labor hours saved | ≥ 20 hrs/farm/season | Farmer surveys + telemetry |
| Audit trail completeness | 100% critical events | Blockchain explorer |
| Data quality pass rate | ≥ 98% | Ingestion pipeline |

--- 

## 9. Compliance & Retention
- **GDPR/PDPA**: Farmer consent for P0 data; right to deletion (exempt: audit trail hashes)
- **India DPDP Act 2023**: Data localization for P0/P1; DPIA for new model deployments
- **Audit**: Quarterly internal; annual external (ISO 27001 aligned)

--- 

## 10. Review Cycle
- **Policy**: Bi-annual review (MLOps Lead + Legal + Blockchain Lead)
- **Operational**: Monthly metrics review with CEO
- **Technical**: Sprint retro includes governance debt items

--- 

## Appendix A: Verification Checklist (Pre-Production)
- [ ] Sensor schema registry deployed
- [ ] Edge anomaly detection validated on test farm
- [ ] MLflow model registry with promotion gates
- [ ] Blockchain audit trail smart contract audited
- [ ] Drift detection dashboards live
- [ ] Incident runbook tested (tabletop)
- [ ] Farmer consent flow UAT complete

--- 

*Policy Version: 1.0 | Author: MLOps Lead | Status: FINAL — Approved for Implementation*