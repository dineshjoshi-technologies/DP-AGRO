---
document_key: dpa153-toxicity-screening-report
issue_id: "DPA-153"
version: "1.0.0"
last_updated: "2026-09-05"
owner: Botanical Research Agent (DPA)
---

# Phase 4 Toxicity Screening Report — Engineered Strains
## Initial Cytotoxicity Screening via MTT Assay on L-929 Fibroblast Cells
### DPA-153 — Engineered Strain Variants: Azadirachtin A, Eugenol, Reb M

## Executive Summary

This report outlines the initial cytotoxicity screening protocol and existing safety data for three engineered strain variants targeting:
1. **Azadirachtin A** (from Neem, *Azadirachta indica*)
2. **Eugenol** (from Tulsi, *Ocimum tenuiflorum*) 
3. **Rebaudioside M (Reb M)** (from Stevia, *Stevia rebaudiana*)

Based on established safety profiles from botanical profiles, the MTT assay on L-929 mouse fibroblast cells will determine IC50 values and compare against wild-type plant extract baselines. Toxicity profiles will inform IP generation and safety assessment for downstream manufacturing processes.

## 1. Compound Profiles and Existing Safety Data

### 1.1 Azadirachtin A (Neem-derived)
**Source**: Neem botanical profile (`neem-botanical.yaml`)

#### Key Safety Data:
- **Acute Oral LD50 (Rat)**: >5000 mg/kg (low acute toxicity) - WHO Monographs (1999); FAO azadirachtin monograph
- **Chronic Exposure (90-day rat study)**: No significant toxicity observed (NOAEL: 100 mg/kg/day)
- **Environmental Persistence**: Soil half-life 3-44 days (moderate); bioaccumulation: low
- **Bee Toxicity**: Low (LD50 >200 μg/bee)
- **Aquatic Toxicity**: LC50 (Daphnia): >100 mg/L
- **Confidence Level**: High

*Note: Comprehensive toxicity profile for azadirachtin metabolites data gap flagged (confidence: low)*

### 1.2 Eugenol (Tulsi-derived)
**Source**: Tulsi botanical profile (`tulsi-botanical.yaml`)

#### Bioactivity and Mechanism:
- **Primary Compound**: Eugenol (CAS: 97-53-0)
- **Typical Concentration**: 40-70% of leaf essential oil
- **Mechanism**: TRPV1 agonist; anti-inflammatory, analgesic, antimicrobial via membrane disruption
- **Therapeutic Applications**: Anti-inflammatory, analgesic, antifungal, insecticidal
- **Evidence Level**: High (multiple RCTs, clinical studies)
- **Confidence Level**: High

*Data Gap*: Specific cytotoxicity/IC50 data not yet compiled in botanical profile. Literature indicates eugenol has cytotoxic effects at higher concentrations but requires experimental determination via MTT assay for IC50 on L-929 cells.

### 1.3 Rebaudioside M (Reb M) (Stevia-derived)
**Source**: Stevia botanical profile (`stevia-botanical.yaml`)

#### Bioactivity and Mechanism:
- **Primary Compound**: Rebaudioside M (Reb M) - CAS not standard (isomer mixture)
- **Typical Concentration**: Trace in native plant; 1-5% in selected cultivars or via enzymatic conversion
- **Sweetness**: 350x sucrose; least bitter aftertaste among steviol glycosides
- **Mechanism**: Non-caloric sweetener; activates sweet taste receptor (T1R2/T1R3); no caloric contribution
- **Therapeutic Potential**: Non-nutritive sweetener; potential antihyperglycemic
- **Evidence Level**: High (regulatory safety assessment)
- **Confidence Level**: High

*Data Gap*: Specific cytotoxicity/IC50 data not yet compiled in botanical profile. Steviol glycosides generally recognized as safe (GRAS) but strain-specific variants require MTT assay validation.

## 2. Toxicity Screening Protocol

### 2.1 MTT Assay Methodology (per Pharmacopoeial Requirements)
- **Cell Line**: L-929 mouse fibroblast cells (ATCC CCL-1)
- **Assay Principle**: Reduction of yellow MTT (3-(4,5-dimethylthiazol-2-yl)-2,5-diphenyltetrazolium bromide) to purple formazan by mitochondrial dehydrogenases in viable cells
- **Measurement**: Spectrophotometric quantification at 570 nm (reference 630-650 nm)
- **Controls**: 
  - Negative: Cell culture medium only
  - Positive: Known cytotoxic compound (e.g., doxorubicin)
  - Wild-type Baseline: Extracts from non-engineered source plants
- **Concentration Range**: Serial dilutions (typically 0.1-1000 μg/mL) to determine IC50
- **Exposure Duration**: 24-48 hours (standard for cytotoxicity screening)
- **Replicates**: Triplicate wells per concentration, minimum 3 independent experiments

### 2.2 Endpoint Determination
- **Primary Endpoint**: IC50 (half-maximal inhibitory concentration) - concentration causing 50% cell viability reduction
- **Secondary Endpoints**: 
  - CC50 (cytotoxic concentration) if applicable
  - Selectivity Index (SI) = CC50/IC50 for compounds with dual activity
  - Comparison to wild-type plant extract baseline IC50 values
  - Dose-response curve analysis (Hill slope, R²)

### 2.3 Wild-Type Plant Extract Baselines
Baseline cytotoxicity values to be determined for:
- **Neem Extract**: Standardized azadirachtin A-containing extract
- **Tulsi Extract**: Eugenol-rich essential oil or leaf extract  
- **Stevia Extract**: Rebaudioside-rich extract (standard Reb A or enriched Reb M)

These baselines will establish whether engineered strains alter cytotoxicity profiles compared to natural sources.

## 3. Expected Outcomes and Safety Recommendations

### 3.1 Predicted Cytotoxicity Ranges (Based on Literature)
| Compound | Expected IC50 Range (L-929) | Rationale |
|----------|-----------------------------|-----------|
| Azadirachtin A | 50-200 μg/mL | Moderate cytotoxicity reported in some cancer cell lines; low acute toxicity in mammals |
| Eugenol | 200-500 μg/mL | Cytotoxic at higher concentrations; antimicrobial properties suggest cell membrane effects |
| Reb M | >1000 μg/mL | Steviol glycosides generally show low cytotoxicity; high safety margin in food applications |

*Note: These are literature-based estimates only. Actual IC50 values must be determined experimentally via MTT assay.*

### 3.2 Safety Assessment Framework
Results will be evaluated against:
- **Pharmacopoeial Limits**: Compare to established safety thresholds in IP/USP/JP
- **Genotoxic Potential**: Flag compounds requiring Ames test or micronucleus assay if IC50 < 50 μg/mL
- **Therapeutic Index**: Calculate ratio between cytotoxic concentration and effective dose for intended application
- **Environmental Safety**: Assess metabolites and degradation products for ecotoxicity

### 3.3 IP Generation Opportunities
- Novel engineered strains demonstrating improved safety profiles (higher IC50, lower toxicity) vs. wild-type
- Stable expression constructs reducing cytotoxic metabolites or byproducts
- Purification protocols yielding extracts with enhanced selectivity indices
- Formulation strategies mitigating any identified cytotoxicity concerns

## 4. Data Gaps and Follow-up Requirements

### 4.1 Immediate Data Gaps (Requires Experimental Work)
- **Actual IC50 Values**: Must be determined via MTT assay for all three engineered strains
- **Wild-type Baselines**: Cytotoxicity profiles of source plant extracts needed for comparison
- **Dose-response Curves**: Full concentration-response relationships for accurate IC50 calculation
- **Time-dependence**: Whether cytotoxicity is time-dependent or cumulative

### 4.2 Botanical Profile Data Gaps (Documentation)
- Eugenol-specific cytotoxicity/IC50 data missing from tulsi-botanical.yaml
- Reb M-specific cytotoxicity/IC50 data missing from stevia-botanical.yaml  
- Comprehensive metabolite toxicity profiles needed for all three compounds

## 5. Recommendations for Laboratory Execution

### 5.1 Sample Preparation
- **Engineered Strain Extracts**: Standardized to equivalent compound concentrations (e.g., ug/mL of target compound)
- **Wild-type Controls**: Matched for compound concentration to enable direct comparison
- **Vehicle Controls**: Appropriate solvent (DMSO <0.5%, ethanol <1%) 
- **Sterility**: All samples filtered (0.22 μm) to prevent microbial contamination

### 5.2 Quality Control
- **Compound Verification**: HPLC/LC-MS confirmation of target compound identity and purity
- **Cell Line Authentication**: Regular STR profiling of L-929 cells
- **Assay Validation**: Z'-factor >0.5 for assay robustness
- **Interference Testing**: Ensure compounds do not directly reduce MTT (absorbance controls)

### 5.3 Safety Monitoring
- **Biosafety Level**: BSL-2 appropriate for L-929 cell work
- **Waste Disposal**: Chemical waste segregated per institutional guidelines
- **Documentation**: Complete raw data retention for audit trail (plate reader outputs, dilutions, cell counts)

## 6. References

1. WHO. (1999). WHO Monographs on Selected Medicinal Plants, Vol. 1. Neem (Azadirachta indica A. Juss.).
2. FAO. (1995). Azadirachtin: A Natural Product for Pest Control. FAO Plant Production and Protection Paper.
3. Prakash, P. & Suri, S. (2005). Therapeutic uses of Ocimum sanctum Linn (Tulsi) with a note on eugenol and its pharmacological actions: a short review. Indian J Physiol Pharmacol, 49(2):125-135.
4. Singh, S. & Majumdar, D.K. (1997). Anti-inflammatory effect of eugenol, a component of clove oil, in rats. J Pharm Pharmacol, 49(4):357-363.
5. Geuns, J.M.C. (2003). Stevioside. Phytochemistry, 64(5):913-921.
6. Yeo, J. & Shah, S.V. (2012). Antioxidant activities of stevia leaf water extract (Stevia rebaudiana Bertoni) and its major sweetener, stevioside. J Med Food, 15(6):547-552.
7. ISO 10993-5:2009. Biological evaluation of medical devices — Part 5: Tests for in vitro cytotoxicity.
8. USP <63> — Platelet, leukocyte, and erythrocyte counts.
9. Indian Pharmacopoeia Commission. (2022). Indian Pharmacopoeia, 9th Edition.

## 7. Confidence Levels and Source Attribution

**Confidence Legend**:
- **High**: Multiple peer-reviewed studies, pharmacopoeial standards, or regulatory assessments
- **Medium**: Single studies, preliminary data, or conflicting reports requiring verification
- **Low**: Anecdotal, traditional knowledge, or significant data gaps requiring follow-up

**Data Sources Cited**:
- neem-botanical.yaml (DPA-75 Botanical Research, 2026-09-05)
- tulsi-botanical.yaml (DPA-75 Botanical Research, 2026-09-05) 
- stevia-botanical.yaml (DPA-75 Botanical Research, 2026-09-05)
- strain-validation-protocol.md (DPA-150, 2026-09-05)
- WHO Monographs (1999)
- FAO Azadirachtin Monograph (1995)
- Various peer-reviewed literature as cited

## 8. Next Actions and Handoff

### 8.1 Immediate Next Steps (Lab Execution Required)
1. Prepare engineered strain extracts matching target compound concentrations
2. Establish wild-type plant extract baselines for comparison
3. Execute MTT assay on L-929 fibroblast cells per protocol above
4. Determine IC50 values with dose-response curves
5. Compare engineered vs. wild-type cytotoxicity profiles
6. Assess selectivity indices and therapeutic indices where applicable

### 8.2 Handoff to Downstream Processes
Upon completion of cytotoxicity screening:
- **To Data Structuring & AI Training Agent**: Raw IC50 data and dose-response curves for knowledge graph integration
- **To Therapeutic & Market Research Agent**: Toxicity profiles for safety assessment and indication filtering  
- **To CEO**: IP generation opportunities and safety clearance for scale-up decisions
- **To DPA-76 (Sustainable Manufacturing)**: Process parameter adjustments based on cytotoxicity findings

### 8.3 Deliverables Summary
- [x] Toxicity screening protocol with botanical context
- [ ] Experimental IC50 data (requires lab execution)
- [ ] Comparative analysis: engineered strains vs. wild-type baselines  
- [ ] Toxicity profiles for IP and safety assessment
- [ ] Safety recommendations and follow-up testing requirements
- [ ] Data gaps identified for future characterization

---
*Report generated by Botanical Research Agent (DPA) as part of DPA-153 Phase 4 Toxicity Screening — Engineered Strains*
*Actual cytotoxicity screening data to be generated via laboratory execution of MTT assay protocol*