# DPA-285 — Packaging + Solvent Supplier Screening (SC-04..06)

**Status:** PROTOCOL v1 + candidate landscape — screening defined; NO partner asserted as
"qualified" until scored against the written criteria below with verification records
(certificates, licenses, COA, audit). No fabricated vendor claims.
**Date:** 2026-09-15
**Prepared by:** Operations Sustainability Lead (DPA-76 / DPA-285)
**Parent track:** [DPA-235](/DPA/issues/DPA-235) Supply Chain Partner Shortlist and Qualification
(Weeks 1-3). DPA-235 is temporarily run-locked (see [DPA-282](/DPA/issues/DPA-282)); this issue
carries the non-botanical qualification track forward on a clean checkout.
**Sources:** governance/partner-evaluation-framework.md, ops/manufacturing/dpa235-supply-chain-partner-shortlist.md,
MANUFACTURING_SCALING_PLAN.md, DPA-76 Weeks 1-3 scope.

## 1. Purpose

Screen and qualify, to **candidate level**, the three non-botanical critical inputs for the
Phase 1 GMP facility:

- **SC-04** Food-grade packaging — PCH/PET jars, closures, laminated foil, child-resistant
  (CR) options, shipping cartons.
- **SC-05** Food-grade ethanol (extraction solvent).
- **SC-06** Food-grade CO2 (supercritical extraction).

This document defines *how* candidates are identified, verified, and scored; records the
current candidate universe per input; and tracks dual-source coverage and open risks.
Qualification here is candidate-level per the DPA-235 constraint: order volumes and final
packaging specs depend on the GMP facility design (CEO design milestone), so **contractual
qualification is finalized only after volumes are confirmed**.

## 2. Screening Protocol (6 steps)

Every input follows the same gate sequence. A candidate does not advance to the next gate
until the required verification records are collected and attached to the scorecard record.

| Step | Activity | Output | Gate to advance |
|---|---|---|---|
| S1 Target setup | Freeze draft SKU/purity spec per input from GMP design (+ MLOps data-governance alignment where manufacturing data meets monitoring) | Spec sheet with regions + min candidates (SC-04 ≥3 mfrs across ≥2 regions; SC-05 ≥2 excise-licensed; SC-06 ≥2 producers) | Spec draft exists |
| S2 Universe search | Search public registries + trade associations; build candidate list (names, region, category) | Candidate universe list | ≥3 candidates per input identified across target regions before scoring |
| S3 Desk verification | Collect and archive per candidate: certificates, licenses, COA, MSDS, audit reports | Verification record per candidate (file refs) | **No candidate is "qualified" without a complete evidence folder** |
| S4 Scoring | Score each candidate against the scorecard template (Section 4) | Scored shortlist per input | Pass threshold met; scoring record attached |
| S5 Dual-source check | Confirm ≥2 qualified (or risk-accepted w/ CEO sign-off) per critical input | Dual-source matrix updated | Coverage target met |
| S6 Contract onboarding | Volume/RFQ from GMP design; CEO approval; onboarding audit + agreement | Supplier agreement file | CEO approval + volumes confirmed |

S1 and S6 are gated on the **CEO GMP-facility design milestone** (order volumes, final SKU
specs). S2–S5 can and should progress now at candidate level. Interim runs of S2–S3 per input
are suitable for parallel child issues once the candidate universe is populated.

## 3. Regulatory Landscape & Verification Requirements

### SC-04 — Food-grade packaging (jars, closures, foil, CR, cartons)

| Criterion (from DPA-235 written criteria) | Hard requirement | Verification record required |
|---|---|---|
| Food-contact compliance | BIS/IS 9873-equivalent food-contact certification for the SKU material; **FSSAI-registered manufacturer** (FoSCoS) | Certificate + FSSAI 17-digit license no. (verifiable via FoSCoS) |
| Quality systems | ISO 9001 (or equivalent) manufacturing; incoming QC data per lot | Certificate + QC records sample |
| Hygiene | Dust-controlled / clean environment for food-contact packaging | Third-party audit report |
| Regions | ≥3 manufacturers across ≥2 of Karnataka / NCR / W-India | Location + registration records |
| Lead time | ≤4 weeks for standard SKUs | Order history or signed commitment letter |

Notes — *Child-resistant options* are verified per-SKU against the applicable CR compliance
standard for the target market (referenced in DPA-235 criteria; exact CR standard confirmed
per SKU at S1/S3). *BIS standard referenced as IS 9873 or equivalent in the parent criteria;
the exact food-contact material standard applicable per SKU is confirmed during S3 compliance
verification and recorded in the risk register if it diverges.*

### SC-05 — Food-grade ethanol (extraction solvent)

| Criterion (from DPA-235 written criteria) | Hard requirement | Verification record required |
|---|---|---|
| Grade | Food-grade (USP-NF / India food-grade spec) ethanol for extraction | **Lot-level COA commitment** (each batch) |
| Regulatory | **State excise license** in the supplier's territory (Karnataka priority) | Copy of current excise license |
| Supply security | ≥2 licensed suppliers | Dual-source matrix |
| Safety | MSDS + hazard-compliant transport/storage | MSDS + transport docs |

### SC-06 — Food-grade CO2 (supercritical extraction)

| Criterion (from DPA-235 written criteria) | Hard requirement | Verification record required |
|---|---|---|
| Grade | Food-grade CO2 per **IS 3076** | **Lot-level COA** (IS 3076 conformance, purity) |
| Regulatory | Food-grade CO2 producer license | License/permit record |
| Supply security | ≥2 producers (Karnataka / industrial corridor) | Dual-source matrix |
| Safety | MSDS, storage/transport for pressurized gas | MSDS + transport docs |

## 4. Qualification Scorecard Template

Generic per-input scorecard (weights per input as shown). A row is only completed when the
evidence folder exists; score = weighted sum of criteria scores.

- **Scoring scale:** 0 = no evidence / unmet · 1 = partial, at risk · 2 = met, record verified
- **Pass threshold:** weighted score ≥1.6 AND no criterion at 0 on a hard requirement.
- **Qualified status** additionally requires: evidence folder attached to the issue/record,
  dual-source check (S5), and — for contract — CEO approval (S6).

### Packaging (SC-04) scorecard template — weights reflect DPA-235 criteria priority

| Candidate | Region | FSSAI reg (25%) | BIS/IS 9873-equivalent food-contact cert (20%) | ISO 9001 / QC (15%) | Hygiene audit (15%) | Lead time ≤4wk (15%) | Dual-region fit (10%) | **Weighted score** | Status |
|---|---|---|---|---|---|---|---|---|---|

### Ethanol (SC-05) scorecard template

| Candidate | Territory | Food-grade spec (30%) | Lot-level COA commitment (25%) | Excise license (25%) | MSDS/transport (10%) | Supply commitment (10%) | **Weighted score** | Status |
|---|---|---|---|---|---|---|---|---|

### CO2 (SC-06) scorecard template

| Candidate | Territory | IS 3076 food-grade (30%) | Lot-level COA (25%) | Producer license (25%) | MSDS/transport (10%) | Bulk capacity / supply commitment (10%) | **Weighted score** | Status |
|---|---|---|---|---|---|---|---|---|

## 5. Candidate Landscape (status = candidate universe, none qualified)

This is the *identifiable universe* to screen from public registries and associations. Named
entities are intentionally NOT asserted until their verification records are collected and
scored — per DPA-235, unknown/irrelevant entities are not named. "Score not started" is the
honest status for the whole table today.

| # | Input | Target regions | Search universe (registry/association pools) | Min candidates | Current status | Evidence needed to qualify | Owner |
|---|---|---|---|---|---|---|---|
| SC-04 | Packaging (jar/closure/foil/CR/carton) | Karnataka, NCR, W-India | FSSAI FoSCoS-registered packaging manufacturers; BIS-licensed food-contact units; packaging industry association members (PMFAI/AIPMA regional chapters); bulk packaging mills for cartons | ≥3 across ≥2 regions | Candidate universe — S2 not started (registry search pending spec freeze) | FSSAI license, food-contact cert, ISO 9001, hygiene audit, order-history/commitment, CR per SKU | Ops Sustainability Lead |
| SC-05 | Ethanol (extraction) | Karnataka (+1 second territory) | Karnataka state excise licensed distilleries; USP-NF / food-grade ethanol suppliers with excise presence | ≥2 licensed | Candidate universe — S2 not started | Excise license, food-grade spec, lot-level COA commitment, MSDS | Ops Sustainability Lead |
| SC-06 | CO2 (supercritical) | Karnataka / industrial corridor | IS 3076 food-grade CO2 producers; industrial gas producers with FSSAI food-grade line | ≥2 producers | Candidate universe — S2 not started | IS 3076 COA, producer license, MSDS/transport, supply commitment | Ops Sustainability Lead |

Coordination: candidate evidence folders are keyed to the DPA scorecard record; MLOps seeks
alignment where manufacturing (batch/solvent usage) data meets the monitoring stack; on-chain
traceability of verified COA is optional per Blockchain Integration Lead.

## 6. Dual-Source Coverage Matrix (critical inputs)

| Critical input | Primary | Backup | Coverage status | Unblock action / owner |
|---|---|---|---|---|
| Packaging jars/closures/foil | TBD — highest-scored SC-04 candidate | Second-region SC-04 manufacturer | **Not yet covered** — candidates not scored | Run S2–S4 after spec freeze; CEO approves contract at S6 |
| Solvent ethanol | TBD — highest-scored SC-05 supplier | Second excise-licensed supplier | **Not yet covered** | Verify ≥2 excise licenses; any single-license risk accepted only with CEO sign-off |
| Food-grade CO2 | TBD — highest-scored SC-06 producer | Second producer | **Not yet covered** | Verify ≥2 producers; IS 3076 COA per lot |

Dual-source gaps are real and open; they are carried to the DPA-235 shortlist's dual-source
matrix and its risk register.

## 7. Open Risk Register

| Risk | Category | Severity | Owner | Mitigation / next action |
|---|---|---|---|---|
| No candidate verified yet → Week 1-3 "qualification" limited to candidate level | Schedule | Medium | Ops Sustainability Lead | Run S2/S3 as soon as spec draft exists; candidate-level is within contract scope until volumes confirmed |
| Order volumes + final SKU specs pending GMP design (CEO milestone) | Demand | Medium | CEO + Ops Sustainability Lead | Freeze S1 spec; RFP/contract after design confirms; do not over-commit vendor pipeline |
| Karnataka excise-licensed food-grade ethanol pool may be narrow | Supply | Medium | Ops Sustainability Lead | Dual-territory search; escalate single-license deformation to CEO for risk acceptance if unavoidable |
| IS 3076 food-grade CO2 producers limited vs industrial-grade bulk market | Supply | Medium | Ops Sustainability Lead | Verify ≥2 food-grade producers; confirm lot-level IS 3076 COA; extend search to NCR/industrial corridor |
| BIS food-contact standard per SKU (parent criteria cite IS 9873 or equivalent) to be confirmed | Compliance | Low | Ops Sustainability Lead + QA | Confirm applicable standard per SKU at S3; record divergence in scorecard, keep DPA-235 criteria as reference |
| Child-resistant closure compliance per SKU/market | Compliance | Low | Ops Sustainability Lead | Verify CR standard + test records per SKU before final qualification |
| Lead time ≤4 wk not yet evidenced for packaging | Logistics | Medium | Ops Sustainability Lead | Obtain order history/commitment letters during S3; region diversification reduces single-site lead-time risk |
| No purchase commitment without CEO approval (no capital spend) | Governance | High | CEO (approval) | All S6 contract steps gated on CEO approval per DPA constraints |

## 8. Governance & Next Actions

Constraints honored: no supplier asserted qualified without verification records; no
fabricated vendor claims; no purchase commitments or capital spend without CEO approval;
order volumes/final specs await the GMP design milestone (candidate-level qualification now,
contractual qualification after volumes confirmed).

**Next actions:**
1. Ops Sustainability Lead — republish this protocol into per-input child issues (SC-04/SC-05/SC-06
   verification tracks) once the S1 spec draft exists; do not name suppliers until their
   evidence folders are attached.
2. CEO — confirm the GMP-facility design milestone that freezes packaging specs/volumes; this
   unlocks S1 and S6.
3. Roll verified candidates into the [DPA-235](/DPA/issues/DPA-235) shortlist and dual-source
   matrix when the parent run-lock is released per [DPA-282](/DPA/issues/DPA-282).

**Owner:** Operations Sustainability Lead. **Priority:** High (Weeks 1-3 deliverable track).