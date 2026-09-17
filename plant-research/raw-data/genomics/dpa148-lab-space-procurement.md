---
document_type: "Laboratory Space & Procurement Coordination Plan"
document_id: "DPA-148-lab-space-procurement"
workstream: "DPA-75 Medicinal Agriculture R&D — Phase 1"
phase: "Weeks 1-3: Lab Space & Procurement"
author: "Botanical Research Agent (DPA)"
contributor: "interim Plant Genomics lead"
date: "2026-09-05"
version: "1.0.0"
related_issues:
  - "DPA-148 (Secure equipment and lab space)"
  - "DPA-149 (Obtain research permits)"
  - "DPA-150 (Strain validation Phase 2)"
  - "DPA-151 (Engineered strain completion Phase 3)"
  - "DPA-76 (Sustainable Manufacturing) — bi-weekly sync"
related_documents:
  - "dpa148-genomic-equipment-requirements.md"
confidence_overall: "high"
sources_cited: "Indian biotech park data, DBT guidelines, vendor quotations (pending), real estate benchmarks"
---

# Laboratory Space & Procurement Coordination Plan for DPA-75 Genomics Facility

## 1. Executive Summary

This document details the laboratory space acquisition strategy, procurement coordination framework, and implementation timeline for the genomic sequencing facility supporting the Medicinal Agriculture R&D workstream ([DPA-75](/DPA/issues/DPA-75)). It builds on the equipment specifications defined in `dpa148-genomic-equipment-requirements.md`.

**Target**: Operational BSL-2 genomics lab with Illumina NextSeq 2000 + Oxford Nanopore PromethION P24 by **Week 8** (allowing 5 weeks for fit-out after lease execution in Week 3).

---

## 2. Laboratory Space Requirements (Refined)

### 2.1 Final Space Programme (based on equipment spec)

| Functional Zone | Area (m²) | Key Requirements |
|---|---|---|
| Sample Reception & Cold Storage (−80°C, −20°C, 4°C) | 14 | 2 × −80°C ULT, 2 × −20°C, 1 × 4°C; backup power; temperature monitoring |
| Pre-PCR / Extraction Lab (DNA/RNA) | 28 | 2 × Class II A2 BSC, centrifuges, TissueLyser, fume hood, separate entry |
| Post-PCR / Library Prep (Illumina) | 20 | PCR hoods, thermal cyclers, Qubit, TapeStation, magnetic rack |
| Post-PCR / Library Prep (ONT) | 16 | ONT bench, temperature control (19–25°C), vibration isolation |
| Sequencing Instrument Room | 22 | Climate control ±1°C, 30–60% RH, UPS (5 kVA), 10 GbE, dedicated HVAC |
| Tissue Culture / Plant Transformation | 18 | Class II A2 BSC, laminar flow, growth chambers, autoclave access |
| Reagent / Chemical Storage | 10 | Flammable cabinet, acid/base cabinet, chemical inventory system |
| Wash / Decon / Autoclave | 12 | Pass-through autoclave, glassware washer, waste holding |
| Bioinformatics / Dry Office | 28 | 8 workstations, 10 GbE, NAS access, meeting area |
| Meeting / Collaboration | 14 | Video conferencing, whiteboard, DPA-76 sync space |
| Corridors, Airlocks, Restrooms (15%) | 30 | BSL-2 pressure cascade, interlocking doors |
| **Total Net Area** | **~212 m²** | |
| **Gross Lease Target (incl. common areas)** | **~250 m² (2,700 ft²)** | |

### 2.2 Site Selection Criteria (Weighted)

| Criterion | Weight | Notes |
|---|---|---|
| Biotech park ecosystem (vendor access, talent pool) | 25% | Genome Valley (Hyderabad), Bengaluru BioCluster, Pune Biotech Park |
| BSL-2 fit-out readiness / existing wet lab infrastructure | 20% | Reduces capex & timeline |
| Power reliability (grid + DG capacity) | 15% | Sequencers need <10 ms transfer |
| Lease flexibility (3+3 or 5+5 with exit) | 10% | Align with 10-week workstream phases |
| Proximity to DPA-76 manufacturing / pilot farms | 10% | Logistics for sample flow |
| Regulatory track record (IBSC, RCGM approvals on-site) | 10% | Faster IBSC setup |
| Rent + CAM (INR/ft²/yr) | 10% | Budget: ≤ INR 150/ft²/yr gross |

### 2.3 Shortlisted Locations (Illustrative)

| Park / Location | City | Est. Rent (INR/ft²/yr) | Fit-out Readiness | Notes |
|---|---|---|---|---|
| **Genome Valley (IKP / T-Hub / Biocluster)** | Hyderabad | 110–140 | High (existing BSL-2 shells) | Strong vendor ecosystem, DBT/RCGM familiarity |
| **Bengaluru Helix Biotech Park / C-CAMP** | Bengaluru | 130–160 | High | Deep talent pool, premium cost |
| **Pune BioIncubator / Venture Center** | Pune | 90–120 | Medium | Strong academic links (NCCS, IISER) |
| **Ahmedabad GSBTM / Gujarat Biotech Park** | Ahmedabad | 80–110 | Medium | State incentives for biotech |
| **Chennai TICEL / TIDEL Park** | Chennai | 85–115 | Medium | Southern hub, port access |

**Recommendation**: **Genome Valley, Hyderabad** — optimal balance of BSL-2 readiness, vendor proximity, talent pipeline, and cost. Initiate site visits Week 1.

---

## 3. Procurement Coordination Framework

### 3.1 Governance Structure

| Role | Responsible | Authority |
|---|---|---|
| **Technical Spec Owner** | Botanical Research Agent (this role) | Equipment specs, evaluation criteria |
| **Procurement Lead** | CEO Office / Finance | Tender process, contract negotiation, PO issuance |
| **Legal / Compliance** | CEO Office / External counsel | Contract review, IP clauses, warranty terms |
| **Finance / Budget Holder** | CEO | Capex approval, payment milestones |
| **Lab Operations / QA** | Lab Manager (to hire) | Site acceptance, calibration, SOP sign-off |

### 3.2 Procurement Sequence (Weeks 1–3)

| Week | Activity | Owner | Deliverable |
|---|---|---|---|
| **W1** | Issue RFQ to 3 vendors per platform (Illumina, ONT, PacBio) | Procurement + Technical | RFQ issued with spec sheet from `dpa148-genomic-equipment-requirements.md` |
| **W1** | Shortlist 3 lab sites; schedule visits | Technical + Procurement | Site visit report with scorecard |
| **W1** | Initiate IBSC formation (DBT portal) | Technical + Legal | IBSC charter submitted |
| **W2** | Vendor technical evaluations & demos | Technical | Evaluation matrix (technical + commercial) |
| **W2** | Site visits; lease term negotiation | Procurement + Legal | Term sheet for preferred site |
| **W2** | Budget sign-off (Capex + Year-1 Opex) | Finance + CEO | Approved budget envelope |
| **W3** | LOI / Purchase Order placement | Procurement | Signed PO with delivery schedule |
| **W3** | Lease execution; fit-out contractor engagement | Procurement + Legal | Signed lease + fit-out LOI |
| **W3** | IBSC first meeting scheduled | Technical | Calendar invite + agenda |

### 3.3 RFQ Specification Package (to vendors)

Each RFQ includes:
- Technical specification sheet (from equipment doc)
- Required deliverables: instrument, installation, IQ/OQ/PQ, 1-yr warranty, 24-mo service contract
- India-specific: GST (18%), CIF pricing, INR-denominated option
- Delivery timeline commitment (weeks from PO)
- Training inclusion (on-site, 2 days Illumina; 3 days ONT)
- Reference sites in India (contactable)

### 3.4 Evaluation Matrix (70/30 Technical/Commercial)

| Criterion | Weight | Scoring (1–5) |
|---|---|---|
| Technical fit (spec compliance) | 25% |  |
| India support footprint (FEs, spares, response SLA) | 15% |  |
| Total cost of ownership (3-yr) | 20% |  |
| Delivery timeline | 10% |  |
| Training & knowledge transfer | 10% |  |
| Contract flexibility (upgrade path, trade-in) | 10% |  |
| Reference satisfaction (Indian customers) | 10% |  |

---

## 4. Laboratory Fit-out & Commissioning Timeline (Weeks 3–8)

| Week | Milestone | Dependencies |
|---|---|---|
| **W3** | Lease signed; fit-out contractor mobilized | Lease execution |
| **W4** | BSL-2 fit-out: HVAC, pressure cascade, HEPA, BSC install | Contractor, long-lead HVAC |
| **W5** | Electrical: UPS, DG ATS, dedicated circuits, grounding | UPS delivery (6–8 wk lead) |
| **W5** | Plumbing: DI water, gas (N2, CO2), waste neutralization |  |
| **W6** | Casework, epoxy flooring, biosafety cabinets certification |  |
| **W6** | Network: 10 GbE backbone, VLANs, instrument VLAN |  |
| **W7** | Cold storage install (−80°C, −20°C); temp mapping |  |
| **W7** | Sequencer delivery & positioning (crane/rigging if needed) | PO delivery schedule |
| **W8** | **IQ/OQ/PQ** (vendor); staff training; SOP dry-runs | Vendor engineers on-site |
| **W8** | **Lab Operational Readiness Review** (IBSC + QA) | All SOPs approved |
| **W8** | **Go-Live: First sequencing run** |  |

**Critical Path**: HVAC/pressure cascade (Week 4) → UPS/DG (Week 5) → Sequencer delivery (Week 7) → IQ/OQ/PQ (Week 8).

---

## 5. Budget Allocation (Detailed)

| Category | Capex (INR Lakh) | Opex Year 1 (INR Lakh) | Notes |
|---|---|---|---|
| Illumina NextSeq 2000 | 120 | 18 (service Y2) |  |
| ONT PromethION P24 + 5 flow cells | 115 | 15 (service Y2) |  |
| Library prep reagents (Year 1) | — | 42 |  |
| Ancillary instruments | 115 | 5 |  |
| Compute & storage (local) | 38 | 8 |  |
| Lab fit-out (BSL-2, 250 m²) | 85 | — |  |
| Lab rent (12 mo @ INR 125/ft²) | — | 34 |  |
| Personnel (7.5 FTE loaded) | — | 180 |  |
| IBSC / regulatory | 5 | 5 |  |
| Contingency (10%) | 48 | 30 |  |
| **Total** | **526** | **337** | **~INR 8.6 Cr Year 1** |

---

## 6. Coordination with DPA-76 (Sustainable Manufacturing)

| Sync Cadence | Format | Agenda Items |
|---|---|---|
| **Bi-weekly (Weeks 1, 3, 5, 7)** | 60-min video call + shared tracker | Lab readiness vs. manufacturing sample flow; compound prioritization for sequencing; data handoff formats |
| **Monthly** | In-person (alternating sites) | Joint review of strain validation pipeline (DPA-150); metabolite target alignment |
| **Ad-hoc** | Slack / email | Urgent sample dispatch, instrument downtime |

**Data Handoff Format**: FASTQ + metadata JSON (aligned to `plant-research/schema/plant-knowledge-schema.json` `plant_identification` block).

---

## 7. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| HVAC long lead (10–12 wk) delays BSL-2 certification | High | High | Pre-order AHU/HEPA on LOI; specify 8-wk delivery in fit-out contract | Procurement |
| UPS/DG delivery delay | Medium | High | Specify 6-wk delivery; rental UPS backup | Procurement |
| Vendor quote > budget | Medium | Medium | Tier-2 fallback (BGI DNBSEQ); negotiate INR-fixed | Finance + Technical |
| IBSC formation > 30 days | Medium | Medium | Pre-nominate members; use DBT fast-track | Technical |
| Key talent not hired by Week 4 | High | Medium | Start hiring Week 1; use contract bioinformatician interim | HR + Technical |
| Power instability at site | High | High | Site audit pre-lease; mandate online UPS + DG | Procurement + Technical |

---

## 8. Immediate Actions (This Heartbeat)

1. **Confirm shortlist of 3 lab sites** with Procurement; schedule visits for Week 1.
2. **Finalize RFQ package** using equipment spec doc; send to 3 Illumina + 3 ONT vendors.
3. **Nominate IBSC members** per DBT guidelines (3 internal scientists, 1 DBT nominee, 1 medical officer, 1 biosafety officer); submit charter.
4. **Engage fit-out contractor** for budgetary quote on 250 m² BSL-2 shell.
5. **Update DPA-149** with IBSC/RCGM permit timeline dependencies.

---

## 9. Acceptance Criteria for Phase 1 Completion

| Criterion | Target | Verification |
|---|---|---|
| Equipment POs placed | Week 3 | Signed POs on file |
| Lease executed | Week 3 | Signed lease |
| Lab fit-out commenced | Week 3 | Contractor mobilized |
| IBSC registered & first meeting held | Week 4 | DBT acknowledgement + minutes |
| Sequencers delivered & positioned | Week 7 | Delivery challans |
| IQ/OQ/PQ passed | Week 8 | Vendor certificates |
| First sequencing run (QC library) | Week 8 | FASTQ + QC report |

---

## 10. Confidence Summary

| Section | Confidence |
|---|---|
| Space programme & BSL-2 requirements | **high** |
| Site shortlist & rent estimates | **medium** (site visits pending) |
| Procurement process & timeline | **high** |
| Fit-out critical path | **medium** (HVAC lead time risk) |
| Budget estimates | **medium** (vendor quotes pending) |
| IBSC/regulatory pathway | **high** |

---

*Document maintained by Botanical Research Agent under [DPA-148](/DPA/issues/DPA-148). Cross-referenced with equipment requirements doc and [DPA-149](/DPA/issues/DPA-149) for permits.*