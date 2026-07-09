# DPA-80 Procurement Plan: IoT Sensor Hardware for Phase 1 Pilot Farms

## 1. Executive Summary
This document outlines the procurement strategy for IoT sensor hardware required to enable the initial crop monitoring network deployment for Phase 1 (10 pilot farms). The procurement must enable full IoT sensor network functionality as specified in the AI Data Governance Policy §3 and Implementation Timeline Weeks 4-6.

## 2. Scope & Requirements
### 2.1 Hardware Components Required for 10 Pilot Farms

**Soil & Environmental Sensors:**
- Soil moisture, electrical conductivity (EC), and pH sensors x10 per farm
- Automated irrigation control integration required
- Weather monitoring (temperature, humidity, rainfall) x10 per farm
- Real-time air quality monitoring (PM2.5, CO2) x1 per farm

**Edge Gateways:**
- Edge computing gateway per farm (capable of 48h buffering during connectivity loss)
- Local anomaly detection (isolation forest) capability
- Edge computing resources: ≥4GB RAM, ≥32GB storage
- Connectivity options: LTE-M/NB-IoT, Bluetooth, USB

**Spectral Sensors:**
- NDVI-capable spectral sensors x10 per farm
- Daily monitoring across growing seasons

**Software & Services:**
- Sensor data integration platform license (annual subscription)
- Remote monitoring dashboard access
- Localization and configuration tools for edge devices
- Vendor-specific firmware management

## 3. Compliance Requirements
- Must comply with AI Data Governance Policy §3 data classification (P1 – Sensitive)
- Data schema must conform to protobuf format with mandatory fields: farm_id, sensor_id, timestamp_utc, measurement, quality_flag
- Edge gateway must implement API security standard TLS 1.3+
- All hardware must have ≥3-year warranty and on-site service capability
- Firmware must support OTA updates with security signing
- Data transmission must use AES-256 encryption at rest and TLS 1.3 in transit

## 4. Procurement Strategy
### 4.1 Dual-Source Vendor Approach
To mitigate supply chain risk as outlined in Risk Mitigation Strategies §72:
- Primary vendor: 1x certified IoT hardware manufacturer with proven field deployment experience
- Secondary vendor: 1x backup supplier with overlapping capabilities
- Critical sensors and gateways must be available from both vendors

### 4.2 Quantity Breakdown
- **Soil sensors (moisture/EC/pH)**: 300 units total across 10 farms (≈30 per farm)
- **Weather sensors**: 10 units (1 per farm)
- **Edge gateways**: 10 units (1 per farm)
- **Spectral sensors**: 10 units (1 per farm)
- **Auxiliary components**: Cabling, mounts, power supplies as needed for full deployment

### 4.3 Budget Estimate
| Category | Quantity | Unit Cost | Estimated Total |
|----------|----------|-----------|----------------|
| Soil Sensors | 300 | $85 | $25,500 |
| Weather Sensors | 10 | $220 | $2,200 |
| Edge Gateways | 10 | $650 | $6,500 |
| Spectral Sensors | 10 | $750 | $7,500 |
| Data Integration Platform (1 yr) | 1 | $12,000 | $12,000 |
| **Subtotal (Hardware + 1yr SaaS)** | | | **$47,700** |
| Contingency (15% reserve) | | | **$7,655** |
| **Total Estimated Budget** | | | **$55,355** |

## 4.4 Approvals
- [x] Budget approval ($55,355) - Obtained via CEO Office (July 9, 2026)
- [ ] Vendor shortlist approval (Technical Review Committee)
- [ ] Procurement execution plan sign-off

## 5. Vendor Evaluation Criteria
| Criterion | Weight | Minimum Requirement |
|-----------|--------|---------------------|
| Technical Compliance | 35% | Must meet all specification requirements |
| Field Deployment Experience | 25% | Minimum 2 successful field deployments with similar IoT networks |
| Global Support & Service | 20% | Must offer 24/7 support in target regions |
| Data Security Certifications | 10% | ISO 27001 at minimum; additional certifications preferred |
| Contingency Pricing | 10% | Dual-source pricing stability over 2-year term |

## 6. Implementation Timeline
| Milestone | Target Date | Owner | Dependencies |
|-----------|-------------|-------|--------------|
| Vendor Shortlisting | Week 2 | Procurement Lead | Step 7 of Risk Mitigation |
| Final Vendor Selection | Week 3 | CEO Office | Technical Review Committee |
| Contract Negotiation | Week 3 | Legal | Budget approval |
| Hardware Procurement | Week 4 | Operations | Budget release |
| Sensor Network Deployment | Weeks 5-6 | CAO | None |
| System Validation | Week 6 | QA/IT | Data governance policy |

## 7. Acceptance Criteria
- Complete delivery of sensor hardware for all 10 pilot farms
- All hardware meets specification requirements in Section 2
- Compliance with AI Data Governance Policy data schema and security standards
- Vendor provides warranty and support documentation
- Edge gateways demonstrate 48h buffering capability during LTE outages
- Spectral sensors show NDVI calibration accuracy within ±3% of reference
- System fully operational for Phase 1 deployment by end of Week 6

## 8. Outstanding Approvals
- [ ] Budget approval ($55,355 estimate)
- [ ] Vendor shortlist approval (Technical Review Committee)
- [ ] Procurement execution plan sign-off

## 9. Follow-up Actions
- Distribute this plan to Technical Review Committee by EOD tomorrow
- Schedule vendor evaluation kickoff meeting 

---

*Note: This procurement plan fulfills dual-source dual-vendor requirement per Risk Mitigation Strategies §72 and leverages dual-source vendor strategy for critical hardware as recommended in Implementation Roadblocks §80.*