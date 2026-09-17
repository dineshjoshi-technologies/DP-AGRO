# DPA-234 — Energy Audit: Baseline Data Collection (Planning Baseline)

**Status:** DRAFT planning baseline — NO measured facility data exists yet
**Date:** 2026-09-15
**Prepared by:** Operations Sustainability Lead (DPA-76 / DPA-234)
**Data source:** None (facility in design) — ALL figures below are labelled
planning estimates to be replaced by measured data, never filed or published as
measured baseline.

## Context

The Phase 1 GMP facility is still in design ($10M approved 2026-07-04,
BR-2026-07-0015; GMP facility design Q3 2026 per implementation-plan.md).
No utility bills, equipment nameplates, production logs, or waste manifests
exist yet. Per DPA measurement discipline, the energy-audit baseline **cannot
be claimed as measured** until the facility is commissioned and metered.

The existing `energy-audit-baseline` issue document (methodology) covers the
data framework: equipment inventory, kWh/kg baseline, waste valorization,
Scope 1/2/3 carbon, and payback-ranked opportunities. This file records the
planning placeholder and the data-request path.

## Planning placeholders (labelled, NOT measured)

| Item | Planning value | Status |
|---|---|---|
| Facility size | 25,000 sq ft GMP | Design spec (scope doc) |
| Utility data (12 mo electricity/gas) | n/a | Not available — facility not commissioned |
| Equipment nameplate (dryers, CO2 extractors, centrifuges, milling, packaging, HVAC ISO 7, lighting, water, compressed air) | n/a | Pending design/commissioning |
| Baseline energy per unit (kWh/kg) | **Not computed** | No production output data |
| Waste-to-value ratio baseline | **Not computed** | No waste manifests |
| Scope 1/2/3 carbon baseline | **Not computed** | No activity data |

## What unblocks a real baseline

1. Facility commissioning + 30–90 days of metered operation (electricity, gas,
   production output, waste).
2. Sub-metering plan on major equipment specified in the design phase (VFDs,
   drying, CO2 extraction) so per-unit baselines are measurable at build time.
3. Waste manifests and logistics data once operations begin.

## Reduction opportunities (planning-level; paybacks TBD with real loads)

Standard herbal-extraction opportunities to be screened once loads exist:
- VFDs on motors (dryers, pumps)
- Heat recovery from extraction / drying
- Insulation upgrades
- LED lighting retrofits
- Compressed-air leak reduction
- Process integration (pinch analysis)
- Solar PV (Indian grid factor 0.82 tCO2/MWh for Scope 2)

## Design-phase sub-metering requirement (so the baseline is measurable at commissioning)

Phase 1 GMP design (owner: CEO/design team) must embed, at-design so the
baseline is measurable from first operation:

1. **Sub-metering on major energy consumers**: CO2 extraction skids, dryers,
   HVAC (ISO 7), compressed air, milling/pulverizing, packaging line, lighting,
   and water heating/recovery. Specify pulse-output energy meters (EN/IEC
   62053-21) feeding the DPA metrics stack.
2. **Production-output metering**: batch/weight record per line (kg output)
   per metering interval, so kWh/kg is computable per product family.
3. **Waste metering**: weighbridge/in-line waste and byproduct weights per line
   (feeds waste-to-value ratio).
4. **Interval resolution**: 15-min logging, 30-day retention onboard, monthly
   rollup to the metrics dashboard.
5. **Scope 2 enabler**: main utility tie-in measurement (kWh, kVA, PF) at the
   service entrance, plus space for on-site solar PV generation metering later.

Adding sub-metering at design is far cheaper than retrofit. This requirement
should be attached to the GMP design RFP.

**Next action (owner: Operations Sustainability Lead → CEO):** propose this
sub-metering clause to be embedded in the Phase 1 GMP design scope, so the
audit baseline and Phase 1 optimization reporting are measurable at
commissioning (coordinated with CEO milestone review).