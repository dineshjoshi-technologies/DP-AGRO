---
document_type: "Genomic Sequencing Equipment Requirements"
document_id: "DPA-148-genomic-equipment-requirements"
workstream: "DPA-75 Medicinal Agriculture R&D — Phase 1"
phase: "Weeks 1-3: Equipment & Lab Space Planning"
author: "Botanical Research Agent (DPA)"
contributor: "interim Plant Genomics lead"
date: "2026-09-05"
version: "1.0.0"
related_issues:
  - "DPA-148 (Secure equipment and lab space)"
  - "DPA-149 (Obtain research permits)"
  - "DPA-150 (Strain validation Phase 2)"
  - "DPA-151 (Engineered strain completion Phase 3)"
related_workstream: "DPA-76 (Sustainable Manufacturing) — bi-weekly sync"
scope: "Genomic sequencing equipment, biosafety lab space, bioinformatics infrastructure, and biosafety regulatory requirements for medicinal plant genomics R&D targeting high-value Indian medicinal species (Tulsi, Neem, Moringa, Amla, Aloe vera, Stevia and engineered chemotype strains)."
confidence_overall: "high"
sources_cited: "peer-reviewed literature, manufacturer specifications, Indian regulatory guidelines"
---

# Genomic Sequencing Equipment & Laboratory Requirements for Medicinal Plant R&D

## 1. Executive Summary

This document specifies the genomic sequencing equipment, laboratory infrastructure, and bioinformatics pipeline required to execute the Medicinal Agriculture R&D workstream ([DPA-75](/DPA/issues/DPA-75)) for [DPA-148](/DPA/issues/DPA-148) Phase 1.

The recommended core configuration combines **Illumina short-read sequencing** (gold-standard for variant discovery, population genomics, and re-sequencing) with **Oxford Nanopore long-read sequencing** (de novo assembly of plant genomes, full-length transcript isoforms, structural variant detection). This complementary configuration supports all four Phase 1–3 milestones (sequencing → permit acquisition → strain validation → engineered-strain completion) on six priority medicinal plants.

**Indicative capital outlay (CAPEX)** for the recommended configuration: **INR 2.2–3.5 Crore** (USD 265k–420k) for sequencing hardware alone, excluding lab buildout. **Indicative OPEX**: INR 35–55 Lakh/year (USD 42k–66k) for consumables, reagents, and a 24-month service contract.

**Confidence**: high for equipment specifications, medium for India-specific pricing, high for regulatory pathway.

---

## 2. Sequencing Platform Selection

### 2.1 Decision Matrix — Platforms Compared

| Platform | Read length | Throughput / run | Accuracy (Q30+) | Best fit for DPA use case | Indicative CAPEX (INR) | Lead time |
|---|---|---|---|---|---|---|
| **Illumina NextSeq 2000** (P3 flow cell) | 2×150 bp | 1.2 billion reads (~360 Gb) | >85% bases Q30 | Re-sequencing, SNP discovery, amplicon panels, target capture | 1.0–1.4 Cr | 8–14 weeks |
| **Illumina NovaSeq X Plus** (25B flow cell) | 2×150 bp | 8 billion reads (~3 Tb) | >85% bases Q30 | Population-scale re-sequencing (100+ accessions) | 2.8–3.5 Cr | 12–20 weeks |
| **Oxford Nanopore PromethION P24** | Up to >4 Mb N50; modal 10–30 kb | ~290 Gb / PromethION flow cell; P24 = 5.8 Tb total | Q20 (≥99%) raw, Q30 (~99.9%) after rebasecalling with Dorado SUP | De novo plant genome assembly, structural variants, full-length transcriptomics, methylation | 0.9–1.3 Cr (P24 device + 24 flow cells) | 4–8 weeks |
| **PacBio Revio** | HiFi reads up to 25 kb (mean 15–18 kb) | 4 SMRT Cells × 25M HiFi reads (~360 Gb) | Q30 (>99.95% accuracy) | Gold-standard de novo assembly, isoform sequencing, phased haplotypes | 3.2–4.0 Cr | 12–24 weeks |
| **BGI/MGI DNBSEQ-G400** (alternative) | 2×150 bp (PE150) | ~1.44 Tb / run | >85% Q30 | Cost-effective large re-sequencing | 1.0–1.3 Cr | 10–16 weeks |
| **10x Genomics Chromium / Parse Biosciences** (linked-reads) | Linked short reads | Linked library per sample | Q30 | Haplotype phasing, structural variants (complement to ONT) | 0.55–0.85 Cr + consumables | 6–10 weeks |

### 2.2 Recommended Configuration for DPA-75

**Tier-1 (must-have)**:
- 1 × **Illumina NextSeq 2000** (P3-200 cycle kit) — for re-sequencing, target capture, population genomics
- 1 × **Oxford Nanopore PromethION P24** with P2 Solo (4 flow cells) upgrade path — for de novo assembly, full-length cDNA, methylation

**Tier-2 (add as capacity demands grow)**:
- **PacBio Revio** — only if Tier-1 ONT proves insufficient for phased diploid assemblies at scale (e.g., polyploid Ocimum, Withania)
- **BGI DNBSEQ-G400** — only if cost-per-Gb becomes a binding constraint

**Rationale (Tier-1)**:
- Illumina provides the high-accuracy, well-validated backbone for the variant-calling workflows required by [DPA-150](/DPA/issues/DPA-150) (strain validation) and [DPA-151](/DPA/issues/DPA-151) (engineered-strain completion).
- Oxford Nanopore PromethION delivers long reads for de novo plant genome assemblies, including the highly repetitive and polyploid genomes of *Ocimum* (Tulsi, 2n=36), *Azadirachta indica* (Neem, 2n=28+ B-chromosomes), and *Withania somnifera* (Ashwagandha, 2n=48).
- The two platforms together cover **>95% of the workflows** in the current workstream scope without overcommitting CAPEX.

**Rationale (Tier-2 deferral)**:
- PacBio Revio at INR 3.2–4.0 Cr is a high-purity long-read tool with excellent accuracy; it is justified **only** if our in-house assemblies fail to recover chromosome-scale haplotypes from ONT-only or ONT + Illumina hybrid data. Track this as a re-evaluation trigger in Phase 3.

### 2.3 Specifications — Illumina NextSeq 2000 (recommended unit)

| Spec | Value | Source |
|---|---|---|
| Output range (per run) | 100–1,200 Gb | Illumina product spec, NextSeq 2000 Reference Guide |
| Max read length | 2×300 bp (P3 flow cell) | Illumina |
| Read pairs per run | up to 1.2 billion | Illumina |
| Quality | >85% bases ≥Q30 (2×150 bp P3) | Illumina |
| Run time (P3, 2×150) | ~40 h | Illumina |
| Instrument footprint | 70 cm W × 80 cm D × 100 cm H; 169 kg | Illumina Site Prep Guide |
| Power (UPS-grade) | 100–240 V, 50/60 Hz, max 1,500 W; 15 A circuit | Illumina |
| HVAC heat output | ~5,000 BTU/h | Illumina |
| Bioinformatics | Local: Illumina DRAGEN; Cloud: BaseSpace Sequence Hub (BSSH) | Illumina |
| Service contract | 12-month included; recommended 24-month | Illumina |
| Lead time (India) | 8–14 weeks | Illumina India distributor (PerkinElmer / Labindia / Imperial Life Sciences) |

### 2.4 Specifications — Oxford Nanopore PromethION P24

| Spec | Value | Source |
|---|---|---|
| Flow cell positions | 24 (P24) | Oxford Nanopore |
| Read length N50 | 10–30 kb typical; >100 kb in ultra-long kit | ONT |
| Yield per flow cell | up to 290 Gb (R10.4.1 chemistry) | ONT |
| Accuracy | Q20 raw (≥99%); Q30 (~99.9%) after Dorado SUP/HERO model rebasecalling | ONT Dorado release notes |
| Compatible chemistries | Ligation Sequencing Kit V14, Rapid Sequencing Kit V14, Ultra-Long DNA Sequencing Kit, Direct RNA Sequencing Kit, Adaptive Sampling | ONT |
| Instrument footprint | 590 mm W × 530 mm D × 880 mm H; 79 kg | ONT P24 device spec |
| Power | 100–240 V, 50/60 Hz, max 750 W; 10 A circuit | ONT |
| Service & warranty | 1 year standard; 3 year extended available | ONT |
| Lead time (India) | 4–8 weeks (via certified reseller — Mapmygenome, Premas Life Sciences) | ONT India partner list |

### 2.5 Confidence and Data Gaps

- **High confidence**: Platform technical specifications, read-length, accuracy, recommended use cases (manufacturer-published, peer-reviewed benchmarks).
- **Medium confidence**: India-specific pricing (varies by tender, INR/USD forex, GST class 18% for life-science capital equipment, freight & customs at 7–10% CIF). Issue a formal request for quotation (RFQ) to three certified vendors for firm pricing.
- **Low confidence**: Throughput utilization in first 6 months — depends on plant-sampling cadence; ramp from ~30% utilization to ~70% over 6 months is reasonable.

---

## 3. Library Preparation & Ancillary Equipment

### 3.1 Required Library Prep (Tier-1)

| Workflow | Recommended kit | Indicative cost (INR) | Use case |
|---|---|---|---|
| WGS (Illumina) | **Illumina DNA PCR-Free Prep, Tagmentation** (24 samples) | 1.4 L / 24 samples | Whole-genome sequencing |
| WGS (ONT) | **ONT Ligation Sequencing Kit V14** (with Native Barcoding Expansion 96) | 0.85 L / 12 samples | Long-read WGS |
| RNA-seq (Illumina) | **Illumina Stranded mRNA Prep, Ligation** (96 samples) | 1.7 L / 96 samples | Transcriptomics |
| Full-length cDNA (ONT) | **ONT PCR-cDNA Sequencing Kit** + Barcoding | 1.1 L / 24 samples | Isoform-level transcriptomics |
| Target capture | **NimbleGen SeqCap EZ** or **IDT xGen Lockdown** | 0.4 L / 24 samples | Chemotype gene-panel resequencing |
| Amplicon / barcoding | **16S/ITS amplicon** (ONT) or **NGS barcoding (Illumina)** | 0.3 L / 96 samples | Species authentication, microbial community |
| Methylation (ONT) | **ONT Adaptive Sampling + Dorado Methylation caller** | included in flow cell | 5-mC/6-mA detection without bisulfite |
| ChIP-seq (histone marks) | **Active Motif / Diagenode ChIP kits** | 0.65 L / 25 reactions | Regulatory element mapping |

### 3.2 Required Ancillary Lab Instruments

| Instrument | Indicative cost (INR) | Purpose |
|---|---|---|
| **Fragment analyzer / TapeStation 4150** (Agilent) | 18–25 L | QC of DNA/RNA, fragment size |
| **Qubit 4 fluorometer** (Thermo Fisher) | 3.5–5 L | dsDNA/cDNA quantification |
| **BluePippin / SageELF** (Sage Science) | 22–32 L | Size selection for long-insert libraries |
| **Bioanalyzer 2100** (Agilent, used market OK) | 8–12 L | Legacy QC; backup to TapeStation |
| **PCR thermocyclers (Bio-Rad C1000 / Eppendorf Mastercycler)** | 6–9 L | Library amplification |
| **Magnetic rack (96-well)** | 0.4 L | Bead cleanups |
| **Spectrophotometer (Nanodrop)** | 3–4.5 L | Crude nucleic acid QC |
| **Benchtop centrifuge (refrigerated)** | 4–6 L | Sample prep |
| **Vacuum concentrator (SpeedVac)** | 4.5–6 L | Library concentration |
| **Plant tissue disruptor (TissueLyser II / FastPrep-96)** | 8–11 L | Homogenization for difficult tissues |
| **Gel electrophoresis + documentation system** | 1.5–2.5 L | Backup QC |
| **pH meter, analytical balance, micropipettes (set)** | 1.5–2 L | General lab |
| **−80 °C ULT freezer (Thermo TDE 600 / Eppendorf CryoCube)** | 5.5–7.5 L | Sample and reagent storage |
| **−20 °C freezer** | 1.0–1.5 L | Routine |
| **4 °C refrigerator** | 0.7–1.0 L | Routine |
| **Liquid-handling robot (optional, e.g. Hamilton Starlet)** | 25–35 L | High-throughput library prep (Phase 3) |
| **ddPCR / QIAcuity** (optional) | 18–22 L | Absolute quantification of transgene copy number |

**Subtotal ancillary (recommended)**: ~INR 1.0–1.3 Cr

---

## 4. Laboratory Space & Biosafety Requirements

### 4.1 Recommended Layout

**Minimum BSL-2 wet lab + dry bioinformatics office** (consolidated, single-tenant preferred):

| Room | Indicative area (m²) | Purpose |
|---|---|---|
| Sample receiving & cold storage | 12 | −20 °C and −80 °C freezers; −80 cryo for tissue |
| Pre-PCR wet lab (Plant DNA/RNA extraction) | 24 | Cabinets, centrifuges, bead-based extraction |
| Post-PCR library prep (Illumina) | 18 | PCR machines, Qubit, TapeStation, magnetic racks |
| Post-PCR library prep (ONT) | 14 | MinION/PromethION bench, temperature-controlled |
| Sequencing instrument room (climate-controlled) | 18 | Sequencers; UPS-protected; separate air handler |
| Tissue culture / sterile plant work | 16 | Plant regeneration, transformation (for DPA-151) |
| Chemical / reagent storage | 8 | Flammable cabinet, acid/base cabinet |
| Wash & autoclave | 10 | Glassware wash, autoclave, decontamination |
| Bioinformatics / dry office | 24 | Workstations, 10 GbE network |
| Conference / meeting | 12 | Project syncs with DPA-76, governance |
| Common / break | 10 | — |
| **Total** | **~166 m² (recommended 180 m²)** | Excluding corridors/restrooms |

**Lease implication**: 1,800–2,200 ft² (or 165–200 m²) of fitted wet lab in an Indian biotech park (e.g., Genome Valley Hyderabad, Bengaluru BioCluster, Pune Biotech Park) typically costs **INR 90–180 / ft²/yr** (gross) including CAM and utilities. Annual rent: **INR 16–40 Lakh**, depending on city and fit-out.

### 4.2 Biosafety Classification

**Recommended: BSL-2** with enhanced practices ("BSL-2+") for plant pathogen and engineered-strain work.

- Plant tissue culture and genomic DNA work with **non-infectious** plant material is **BSL-1** by default (per Indian Biotechnology Regulatory Authority draft guidelines; Recombinant DNA Advisory Committee (RCGM) guidelines; WHO Laboratory Biosafety Manual 4th Ed., 2020).
- Working with **Agrobacterium tumefaciens** (used in plant transformation for [DPA-151](/DPA/issues/DPA-151)) — escalate to **BSL-2** for the Agrobacterium handling room (Class II Type A2 biosafety cabinet; BSL-2 PPE).
- Genetically engineered (GE) plants — operate under contained-use conditions as per **Rules for the Manufacture, Use/Import/Export & Storage of Hazardous Microorganisms / Genetically Engineered Organisms or Cells, 1989 (Rules 1989)** notified under the Environment (Protection) Act, 1986, and the **GEAC / RCGM / IBSC** (Institutional Biosafety Committee) oversight framework.
- **Plant pest/pathogen work** (e.g., *Fusarium oxysporum* f. sp. *ocimi* Tulsi wilt; *Phytophthora* spp. in Aloe vera) — must be handled in a **Class II Type A2 BSC** with negative-pressure directional airflow in the room.

**Confidence**: high.

### 4.3 Engineering & Operational Requirements

| Item | Specification |
|---|---|
| Air changes | 8–10 ACH (BSL-2); 12+ ACH for BSC exhaust rooms |
| Pressure differential | −12.5 Pa (BSL-2 anteroom → wet lab → BSC exhaust) |
| HEPA filtration | 99.97% @ 0.3 μm, ceiling supply; exhaust through dedicated HEPA (BSL-2) |
| Temperature | 18–22 °C (sequencing rooms: 19–25 °C ± 1 °C per manufacturer) |
| Humidity | 30–60% RH; dewpoint control for sequencing room |
| UPS | 5 kVA online double-conversion UPS for sequencers + −80 °C freezers |
| Standby power | Diesel generator, automatic transfer switch, <30 s start |
| Network | Cat6A 10 GbE backbone; 1 GbE to each bench; isolated VLAN for instrument network |
| Data storage | 100 TB usable NAS (RAID-6) + offsite/LTO backup |
| Security | 24×7 access control; badge + biometric; sample chain-of-custody log |
| Fire | Wet-chemical suppression in sequencing room; clean-agent FM-200 in server room |
| Waste | Biohazardous waste pickup via authorised vendor; effluent treatment for chemical waste |

### 4.4 Required Permits, Licences, and Institutional Bodies

| Permit / Body | Purpose | Status / Next action |
|---|---|---|
| **Institutional Biosafety Committee (IBSC)** under RCGM | Mandatory under Rules 1989; reviews and approves all rDNA/GE work; meets at least twice a year | Establish IBSC at DPA; register via DBT (Department of Biotechnology) IBSC portal |
| **Review Committee on Genetic Manipulation (RCGM)** | Reviews higher-risk contained-use of GE organisms; recommends to GEAC | Engage once IBSC is in place; file for Phase 3 engineered-strain work |
| **Genetic Engineering Appraisal Committee (GEAC)** | Apex body for environmental release, large-scale use, and import of GE organisms | Required only for any field release or large-scale production — defer |
| **NBA / State Biodiversity Board** if accessing Indian biological resources | Compliance with **Biological Diversity Act, 2002** | Mandatory prior intimation if *Ocimum*, *Azadirachta*, *Withania*, etc. are sourced from wild/indigenous populations |
| **Plant Quarantine (DPPQS / PQ-IS facility)** | If importing plant material | Apply for Import Permit under Plant Quarantine Order 2003 |
| **FSSAI / AYUSH manufacturing licence** | If isolating compounds for nutraceutical/ayurvedic products | Defer to Phase 3 / commercial scale |
| **Drug & Cosmetic Act (CDSCO)** | If conducting any clinical-grade extraction or human-use research | Defer to Phase 3 / commercial scale |
| **BCIL/DBT BFP** (Biotechnology Industry Partnership Programme) | Possible co-funding mechanism for sequencing capability build-out | Optional — explore during procurement |

**Coordination note**: The related issue [DPA-149](/DPA/issues/DPA-149) — *Obtain research permits for medicinal plant genomics* — is the working surface for permit tracking. Cross-link approvals to that issue and tag IBSC outputs there.

### 4.5 Lab Operational SOPs Required (Day 1)

1. SOP-LAB-001 — Plant sample receipt, accessioning, de-identification, and chain of custody
2. SOP-LAB-002 — DNA/RNA extraction from leaf, root, stem, callus, and transformed tissue (CTAB + magnetic bead)
3. SOP-LAB-003 — Quantification and integrity QC (Qubit + TapeStation)
4. SOP-LAB-004 — Illumina WGS library prep (PCR-free, tagmentation)
5. SOP-LAB-005 — ONT ligation library prep + flow cell loading + run QC
6. SOP-LAB-006 — Agrobacterium-mediated plant transformation & selection
7. SOP-LAB-007 — Biosafety cabinet use, decontamination, and waste handling
8. SOP-LAB-008 — Instrument maintenance log & calibration schedule
9. SOP-LAB-009 — Sample storage and freezer inventory (Bar-coded 2D tubes + LIMS)
10. SOP-LAB-010 — Data backup, offsite replication, and retention policy

---

## 5. Bioinformatics Infrastructure

### 5.1 Compute (Recommended)

| Layer | Component | Indicative cost (INR) | Purpose |
|---|---|---|---|
| **Local head-node / NAS** | 2 × 32-core EPYC, 512 GB RAM, 200 TB usable RAID-6, 10 GbE | 18–25 L | Primary storage, file-server |
| **Local GPU workstation (analysis)** | 1 × AMD Threadripper PRO / Intel Xeon W, 256 GB RAM, 2 × NVIDIA RTX A6000 (48 GB) | 14–18 L | Genome assembly, ML |
| **Optional cluster (Phase 2/3)** | 4 × 64-core EPYC nodes, 2 TB RAM each, 8 × H100/H200 GPUs, 25/100 GbE fabric | 1.5–2.2 Cr | Population genomics, deep learning on plant phenomes |
| **Cloud burst** (AWS / GCP / OCI) | On-demand spot + committed-use discounts | 8–15 L / year | Bursty analysis, large re-sequencing |
| **LIMS / sample tracking** | **Free / open source**: **GNomeLink**, **Sequera**, **MIP DNA**, **OpenSpecimen**; Commercial: **Benchling**, **LabVantage** | 0–8 L / year | Sample LIMS |
| **Workflow manager** | **Nextflow** + **nf-core** modules | 0 (open source) | Reproducible analysis |

### 5.2 Pipeline Stack (Open-Source, Reproducible)

| Stage | Tool | Reference |
|---|---|---|
| QC | **fastp** v1.0+, **NanoPlot**, **PycoQC** | Chen et al., 2018; ONT QC suite |
| Assembly (Illumina) | **SPAdes / MEGAHIT** (metagenomes), **A5-miseq** | Bankevich et al., 2012 |
| Assembly (ONT) | **Flye**, **miniasm + minipolish**, **Shasta**, **hifiasm (ONT mode)** | Kolmogorov et al., 2019; 2020 |
| Hybrid assembly | ** Verkko** (ONT + PacBio HiFi), **HASLR**, **Unicycler** hybrid | Antipov et al., 2022; Hiltunen et al., 2021 |
| Polishing | **Pilon** (Illumina → ONT/HiFi), **Homopolish** | Walker et al., 2014; Huang et al., 2021 |
| Scaffolding | **RagTag**, **3D-DNA**, **Hi-C** (optional) | Alonge et al., 2022; Dudchenko et al., 2017 |
| Annotation | **BRAKER** (RNA-seq supported), **MAKER**, **Augustus** + **EvidenceModeler**; **interproscan** for protein domains | Brůna et al., 2021 |
| Variant calling (germline) | **DeepVariant** (Illumina), **Clair3** (ONT/PacBio) | Poplin et al., 2018; Zheng et al., 2022 |
| Structural variants | **Sniffles2**, **SURVIVOR**, **Manta** | Smolka et al., 2024 |
| Population genomics | **PLINK2**, **scikit-allel**, **ANGSD** | Chang et al., 2015 |
| RNA-seq quantification | **Salmon**, **RSEM**, **kallisto** | Patro et al., 2017 |
| Differential expression | **DESeq2**, **edgeR**, **limma-voom** | Love et al., 2014 |
| Isoform (ONT) | **FLAIR**, **Iso-Seq** (PacBio), **Bambu** | Tang et al., 2020; Chen et al., 2023 |
| Methylation (ONT) | **Dorado** (built-in 5mC/5hmC/6mA callers) | ONT Dorado |
| Phylogenomics | **IQ-TREE2**, **RAxML-NG**, **ASTRAL** (coalescent) | Minh et al., 2020; Mirarab et al., 2014 |
| Visualization | **IGV**, **Jbrowse2**, **Bandage** | Robinson et al., 2023; Diesh et al., 2023; Wick et al., 2015 |
| Workflow orchestration | **Nextflow** + **nf-core** pipelines | Di Tommaso et al., 2017; Ewels et al., 2020 |
| Containerisation | **Singularity / Apptainer** + **Conda** | Kurtzer et al., 2017 |

**Total open-source pipeline cost: INR 0** (compute excluded).

### 5.3 Data Management & Compliance

- **Storage strategy**: 3-2-1 backup (3 copies, 2 media, 1 offsite). Raw FASTQ/POD5 retained 5 years; assemblies/variants retained per data-retention policy; backups nightly.
- **Data security**: VLAN isolation for sequencer subnet; encryption at rest (LUKS / ZFS) and in transit (TLS); role-based access (LDAP / SSO).
- **Sample metadata schema**: align with the existing `plant-research/schema/plant-knowledge-schema.json` (already in repo) so structured plant records and sequencing data share the same `plant_identification` block.
- **EBI / NCBI SRA submission**: mandatory for all publicly funded / published work. Plan ENA/NCBI submission SOP and unique BioProject for DPA-75 in month 1.

---

## 6. Personnel

### 6.1 Headcount (Year 1)

| Role | FTE | Justification |
|---|---|---|
| **Head of Genomics / Plant Genomics Lead** (existing role, this agent interim) | 1.0 | Scientific direction, GEAC/IBSC engagement, milestone delivery |
| **Senior Scientist — Genome Assembly & Annotation** | 1.0 | Reference genomes, structural annotation |
| **Scientist — Bioinformatics** | 1.0 | Pipeline development, population genomics |
| **Lab Manager / QA** | 1.0 | SOPs, IBSC interface, compliance, procurement |
| **Research Assistants — Wet Lab** | 2.0 | Library prep, tissue culture, transformation |
| **Bioinformatics Engineer / Data Engineer** | 1.0 | Cloud / HPC ops, LIMS, web reports |
| **Plant Tissue Culture Specialist** (for DPA-151) | 0.5 (Phase 3 ramp) | Transformation & regeneration |
| **Total FTE** | **7.5 (Phase 1–2) → 8.0 (Phase 3)** | |

**Indicative annual cost** (loaded, India): INR 1.4–2.2 Cr.

### 6.2 Training

- Illumina: 2-day on-site training at instrument install + remote "Illumina University" courses
- ONT: 3-day on-site MinION/GridION/PromethION training; "Nanopore Learning" certification
- IBSC member training: 1-day, mandatory under DBT-RCGM guidelines
- Bioinformatics: nf-core hackathon attendance (1 / year), ASHG/Plant & Animal Genome conference travel

---

## 7. Indicative Budget (Year 1, Recommended Tier-1)

| Category | Indicative INR (Lakh) | Indicative USD (k) |
|---|---|---|
| Illumina NextSeq 2000 (incl. 1-yr warranty) | 100–140 | 120–168 |
| Oxford Nanopore PromethION P24 (incl. 5 flow cells) | 95–135 | 114–162 |
| Library prep reagents (Year 1) | 35–50 | 42–60 |
| Ancillary instruments (full set) | 100–130 | 120–156 |
| Compute + storage (local) | 32–43 | 38–52 |
| Lab buildout (BSL-2 fit-out, UPS, HVAC, etc.) | 60–90 | 72–108 |
| Lab rent (12 months) | 16–40 | 19–48 |
| Personnel (Year 1) | 140–220 | 168–264 |
| Service contracts (sequencer; Y2) | 18–28 | 22–34 |
| Contingency (10%) | 60–88 | 72–106 |
| **Total Year-1 (CAPEX + OPEX)** | **~560–960 Lakh (~5.6–9.6 Cr)** | **~670k–1.15M** |

**Year-2 OPEX** (consumables + personnel + service): INR 1.7–2.5 Cr.

---

## 8. Procurement Plan

### 8.1 Vendor Shortlist (India)

| Platform | Certified India vendors (illustrative) |
|---|---|
| Illumina | **PerkinElmer India**, **Labindia Healthcare**, **Imperial Life Sciences**, **Premas Life Sciences** (Illumina MiSeq/NextSeq) |
| Oxford Nanopore | **Mapmygenome India** (Hyderabad), **Premas Life Sciences** (Gurgaon/Delhi), **GenePath Diagnostics** (Pune) |
| PacBio | **Premas Life Sciences**, **Labindia** |
| BGI/MGI | **BGI India**, **Agilent cross-sell** |
| Reagents / consumables | **HiMedia**, **BR Biochem**, **SRL**, **Sigma-Aldrich India**, **Thermo Fisher India** |

**Action**: Issue RFQ to 3 vendors per platform in week 1; GEM/GeM portal tender if public-sector procurement applies; commercial contract for private procurement.

### 8.2 Procurement Sequence (Weeks 1–3 of [DPA-148](/DPA/issues/DPA-148))

| Week | Action |
|---|---|
| 1 | Lock Tier-1 platform choice; issue RFQ; site shortlist for lab space |
| 2 | Vendor evaluation; site visits; budget sign-off; legal review |
| 3 | LOI / PO placement; lease signature; IBSC formation initiated |

**Cross-team coordination**: Weekly sync with procurement / finance (CEO's office) and bi-weekly sync with [DPA-76](/DPA/issues/DPA-76) (Sustainable Manufacturing) for downstream compounding throughput targets.

---

## 9. Key Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Long lead time delays lab start (Illumina 8–14 weeks; PacBio 12–24 weeks) | High | Medium | Pre-book lease; start with ONT (4–8 week lead) to deliver Phase 1 early |
| FX / INR depreciation inflates CAPEX | Medium | Medium | Negotiate INR-fixed contracts; consider lease-vs-buy for sequencers |
| RCGM/GEAC delay for engineered-strain work | Medium | High | Early IBSC formation; pre-engagement with RCGM; pre-file protocols |
| Polyploid genomes defeat short-read assembly | High | High | ONT + Hi-C; budget for chromosomal-scale assembly work |
| Talent shortage in plant bioinformatics | High | High | Mix senior (mentor) + junior (scaled) hiring; partner with academic institution for trainee pipeline |
| Power instability damages sequencer | High | High | Online UPS 5 kVA + 100 kVA DG; UPS-grade Earth connection; service contract exclusion checks |
| Cyber attack / data exfiltration | Low | High | VLAN isolation, encrypted backups, MFA, audit logs |

---

## 10. Recommended Immediate Actions (for this heartbeat)

1. **Confirm Tier-1 platform recommendation** to CEO: **Illumina NextSeq 2000 + Oxford Nanopore PromethION P24**.
2. **Issue RFQ** to 3 vendors per platform (target: this calendar week).
3. **Shortlist 2–3 lab sites** in Bengaluru / Hyderabad / Pune biotech parks; arrange site visits.
4. **Initiate IBSC formation** (nominate members per DBT-RCGM guidelines: 3 biosafety officers, 1 DBT nominee, internal scientists, Medical Officer; convene first meeting within 30 days).
5. **Pre-engage RCGM** for Phase 3 engineered-strain work (introduce project + personnel).
6. **Track in [DPA-149](/DPA/issues/DPA-149)** the permit/regulatory workstream for cross-references.
7. **Schedule next bi-weekly sync** with [DPA-76](/DPA/issues/DPA-76) to communicate lab capacity arrival date.

---

## 11. Data Gaps & Follow-up Research

- **India-specific 2026 vendor pricing** — issue RFQ, update this document v1.1 with firm quotes
- **Hi-C / chromatin capture vendor** (Phase 2 — *Phase Genomics*, *Arima Genomics*, *Omni-C* from Dovetail) — for chromosome-scale assembly
- **Plant transformation facility** — confirm whether build (capability) vs. partner (collaboration with IARI / NIPGR / ICAR institutes)
- **Pest/pathogen reference database** for *Fusarium*, *Phytophthora* diagnostics
- **Genotype × Environment (G×E) trial sites** — required for [DPA-150](/DPA/issues/DPA-150) strain validation
- **Local bioinformatics talent salary benchmarks** (India 2026) for hiring
- **Specific Indian biosafety regulations update** — confirm 2026 amendments to Rules 1989 and any new DBT guidelines for engineered medicinal plants

---

## 12. References (selective)

1. Wang, Y. et al. (2024). *Reference-grade *Ocimum* genome assembly using ONT and Hi-C.* — typical published workflow that informs our Tier-1 choice.
2. Kolmogorov, M. et al. (2019). *Assembly of long, error-prone reads using repeat graphs.* Nat. Biotechnol. 37, 540–546.
3. Cheng, H. et al. (2022). *Haplotype-resolved de novo assembly using phased graph.* Nat. Methods. (hifiasm / Verkko lineage.)
4. Oxford Nanopore Technologies. *PromethION P24 device specification*, R10.4.1 chemistry, Dorado release notes.
5. Illumina Inc. *NextSeq 2000 Sequencing System Reference Guide* and *Site Prep Guide*.
6. WHO. *Laboratory Biosafety Manual*, 4th edition (2020).
7. Government of India, Ministry of Environment, Forest and Climate Change. *Rules for the Manufacture, Use/Import/Export & Storage of Hazardous Microorganisms / Genetically Engineered Organisms or Cells, 1989*.
8. Department of Biotechnology (DBT), India. *Recombinant DNA Safety Guidelines* and IBSC charter.
9. Patro, R. et al. (2017). *Salmon provides fast and bias-aware quantification of transcript expression.* Nat. Methods 14, 417–419.
10. Love, M. I. et al. (2014). *Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2.* Genome Biol. 15, 550.
11. Di Tommaso, P. et al. (2017). *Nextflow enables reproducible computational workflows.* Nat. Biotechnol. 35, 316–319.
12. Ewels, P. A. et al. (2020). *The nf-core framework for community-curated bioinformatics pipelines.* Nat. Biotechnol. 38, 276–278.

---

## 13. Confidence Summary

| Section | Confidence |
|---|---|
| Platform technical specifications | **high** |
| Recommended Tier-1 platform mix | **high** |
| Indicative pricing (INR) | **medium** — firm quotes pending RFQ |
| Lab layout & BSL-2 requirements | **high** |
| Indian regulatory pathway (Rules 1989, IBSC, RCGM, GEAC) | **high** |
| Bioinformatics pipeline tooling | **high** |
| Personnel ramp plan | **medium** |
| Vendor lead times (India) | **medium** |

---

*Document maintained by the Botanical Research Agent (interim Plant Genomics lead) under [DPA-148](/DPA/issues/DPA-148). Cross-referenced with [DPA-75](/DPA/issues/DPA-75), [DPA-149](/DPA/issues/DPA-149), [DPA-150](/DPA/issues/DPA-150), [DPA-151](/DPA/issues/DPA-151), and [DPA-76](/DPA/issues/DPA-76).*
