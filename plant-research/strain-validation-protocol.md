---
document_key: strain-validation-protocol
issue_id: "DPA-150"
version: "1.0.0"
last_updated: "2026-09-05"
owner: Botanical Research Agent (DPA)

# Strain Validation Protocol — Top 3 Engineered Compounds
# DPA-75 Phase 2: Weeks 4-6

## Executive Summary

Based on botanical profiles in `plant-research/raw-data/`, three engineered compound targets have been selected for strain validation. These compounds were chosen using the following criteria:

1. Well-characterized biosynthetic pathway with identified candidate genes
2. High commercial/therapeutic value with established market demand
3. Pharmacopoeial or analytical standardization methods available
4. Pathway amenable to heterologous expression or metabolic engineering
5. Confidence level (chemistry + cultivation) = "high" in botanical profile

---

## Target Compounds

### Priority 1: Azadirachtin A
- **Source**: Neem (*Azadirachta indica* A. Juss., Meliaceae)
- **CAS**: 11141-17-6
- **Current concentration**: 0.2–0.6% in seeds; 0.04–0.08% in leaves (varies by cultivar)
- **Pharmacopoeial standard**: ≥1500 ppm (technical grade); ≥3000 ppm (pharmaceutical)
- **Confidence**: High

**Candidate genes for engineering**:
- TPS (terpene synthase) family — limonoid backbone biosynthesis
- CYP71 family oxidases — azadirachtin-specific oxidation steps
- References: Neem botanical profile (`neem-botanical.yaml`), lines 313–318

**Pathway status**: 
- Limonoid biosynthetic pathway partially characterized
- Key bottleneck: oxidative modifications (CYP71 family) not fully elucidated
- Engineering approach: yeast/plant hairy root heterologous expression of TPS + CYP71 gene cluster

**Standardization marker**: Azadirachtin A quantification by HPLC-UV (pharmacopoeial method)

---

### Priority 2: Eugenol
- **Source**: Tulsi (*Ocimum tenuiflorum* L., Lamiaceae)
- **CAS**: 97-53-0
- **Current concentration**: 40–70% of leaf essential oil
- **Pharmacopoeial standard**: ≥70% eugenol in essential oil (IP, API)
- **Confidence**: High

**Candidate genes for engineering**:
- EGS (eugenol synthase) — direct conversion of coniferyl acetate to eugenol
- PAL (phenylalanine ammonia-lyase) — entry point of phenylpropanoid pathway
- C4H (cinnamate 4-hydroxylase) — early pathway steps
- References: Tulsi botanical profile (`tulsi-botanical.yaml`), lines 261–266

**Pathway status**:
- Eugenol synthase (EGS) is a NADPH-dependent reductase; pathway well-characterized in *Ocimum* spp.
- Engineering approach: microbial (yeast *Saccharomyces cerevisiae*) or *Nicotiana benthamiana* transient expression
- Clear advantage: shorter pathway than azadirachtin; higher engineering feasibility

**Standardization marker**: Eugenol quantification by GC-FID/TCD (pharmacopoeial method)

---

### Priority 3: Rebaudioside M (Reb M)
- **Source**: Stevia (*Stevia rebaudiana* Bertoni, Asteraceae)
- **CAS**: Not standard (isomer mixture)
- **Current concentration**: Trace in native plant; 1–5% in selected cultivars or via enzymatic conversion
- **Pharmacopoeial standard**: ≥5% Reb M for premium extracts; ≥95% Reb A for standard
- **Confidence**: High

**Candidate genes for engineering**:
- CYP716A family — oxidation of steviol to steviol oxide intermediates
- UGT (UDP-glucosyltransferase) genes — glycosylation of C-13 and C-19 hydroxyl groups
- Glucosidase genes — for Reb M enrichment pathway (interconversion from Reb A)
- References: Stevia botanical profile (`stevia-botanical.yaml`), lines 267–273

**Pathway status**:
- Steviol glycoside pathway well-characterized; CYP716A and UGT85A family identified
- Reb M is the most commercially valuable glycoside (least bitter aftertaste, 350× sucrose)
- Engineering approach: yeast platform with multi-gene UGT overexpression; enzymatic conversion from Reb A
- Known data gap: Reb M enrichment via enzymatic conversion not yet standardized at commercial scale (flagged in profile)

**Standardization marker**: Reb M quantification by HPLC-ELSD or LC-MS/MS

---

## Validation Framework

### Phase 1: Genomic Variant Selection

For each target compound, compile candidate gene variants from botanical profiles and literature:

| Compound | Gene Family | Source | Priority | Notes |
|---|---|---|---|---|
| Azadirachtin A | TPS (terpene synthase) | Neem leaf/seed | High | Full-length TPS variants from var. indica |
| Azadirachtin A | CYP71 family oxidases | Neem seed | High | CYP71AV1 validated in *Artemisia annua* (CYP71AV1 for artemisinin); analogous activity expected |
| Eugenol | EGS (eugenol synthase) | Tulsi leaf | High | Multiple isoforms; select EGS1 (constitutive expression) |
| Eugenol | PAL, C4H | Tulsi leaf | Medium | Early pathway genes; co-expression with EGS |
| Reb M | CYP716A (CYP716A53v2) | Stevia leaf | High | Known to convert steviol → 13-OXG steviol |
| Reb M | UGT85A family | Stevia leaf | High | UGT85C2, UGT76E1 for glycosylation steps |

### Phase 2: Strain Construction Strategy

**Azadirachtin A**:
- Preferred host: *Saccharomyces cerevisiae* (better for terpene precursors) or *Nicotiana benthamiana* (transient)
- Strategy: Co-express TPS + CYP71AV1 variant + native P450 reductase
- Milestone: GC-MS detection of azadirachtin or precursors

**Eugenol**:
- Preferred host: *E. coli* (for PAL-C4H-4CL-EGS module) or yeast
- Strategy: Modular pathway assembly (PAL → C4H → 4CL → EGS)
- Milestone: GC detection of eugenol at ≥0.1% of culture headspace

**Reb M**:
- Preferred host: Yeast (*S. cerevisiae*)
- Strategy: Express CYP716A53v2 + UGT85C2 + UGT76E1; add glucosidase for interconversion
- Milestone: HPLC-ELSD detection of Reb M ≥0.1% of total steviol glycosides

### Phase 3: Analytical Validation

| Compound | Detection Method | Equipment | Standard |
|---|---|---|---|
| Azadirachtin A | HPLC-UV (218 nm) | Agilent 1200 series or equivalent | IP 2022 monograph; ≥1500 ppm |
| Eugenol | GC-FID | Shimadzu GC-2010 or equivalent | IP, API; ≥70% in oil |
| Reb M | HPLC-ELSD or LC-MS/MS | Agilent 1290 + ELSD/6470 | USP Stevia glycosides; ≥5% Reb M |

### Phase 4: Toxicity Screening

Initial cytotoxicity screen for all engineered strains:
- Method: MTT assay on L-929 mouse fibroblast cell line (per pharmacopoeial requirements)
- Endpoints: IC50 determination; compare to wild-type plant extract baseline
- Compounds: Azadirachtin A, Eugenol, Reb M — all have established safety profiles from botanical profiles

### Phase 5: IP Generation

- Document all novel gene combinations and expression vectors
- Sequence-function relationships for each gene variant
- Optimize transformation protocols; generate IP portfolio

---

## Coordination with DPA-76

**DPA-76 (Sustainable Manufacturing)**: Process parameters will depend on validated compound yields from engineered strains. Key parameters to share once validated:

1. **Azadirachtin A** — extraction method: supercritical CO₂ preferred for premium grade; cold press for technical grade; storage stability data needed
2. **Eugenol** — steam distillation yield parameters; oil composition (eugenol %) informs downstream formulation
3. **Reb M** — aqueous vs ethanolic extraction; purification (activated carbon, ion exchange) informs process scale-up

**Coordination request**: DPA-76 team to provide:
- Target batch sizes and throughput requirements
- Preferred extraction/isolation methods for each compound class
- Quality specifications beyond pharmacopoeial minimums

---

## Data Gaps & Research Needs

1. **Azadirachtin A**: Full limonoid biosynthetic pathway not complete; TPS-CYP71 interface poorly characterized. *Action*: literature survey of heterologous expression in yeast (pending; assign to Plant Genomics specialist)
2. **Reb M**: Enzymatic conversion pathway (Reb A → Reb M) not commercially standardized. *Action*: Review patent literature on Reb M biosynthesis (pending)
3. **Eugenol**: EGS gene family in *O. tenuiflorum* has multiple isoforms; functional characterization needed to select optimal variant. *Action*: Expression analysis across 3 *Ocimum* varieties

---

## Deliverables Summary

| Deliverable | File | Status |
|---|---|---|
| Strain validation protocol | `strain-validation-protocol.md` | Complete (this document) |
| Top 3 engineered compounds rationale | Inline above | Complete |
| Coordination comment to DPA-76 | Issue comment | Pending |
| Genomic variant inventory | See Phase 1 table | Complete |
| Draft validation report | `strain-validation-draft.md` | In progress |
| Child issues for Phase 3-4 work | DPA-151, DPA-152, DPA-153 | Pending |

---

## References

- Neem botanical profile: `plant-research/raw-data/neem-botanical.yaml`
- Tulsi botanical profile: `plant-research/raw-data/tulsi-botanical.yaml`
- Stevia botanical profile: `plant-research/raw-data/stevia-botanical.yaml`
- Azadirachtin A: CAS 11141-17-6; Indian Pharmacopoeia 2022
- Eugenol: CAS 97-53-0; IP/API; WHO Monographs Vol. 1
- Reb M: Not CAS-assigned; USP Stevia glycosides monograph
