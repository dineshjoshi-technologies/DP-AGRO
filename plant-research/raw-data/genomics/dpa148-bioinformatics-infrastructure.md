---
document_type: "Bioinformatics Infrastructure Setup Plan"
document_id: "DPA-148-bioinformatics-infrastructure"
workstream: "DPA-75 Medicinal Agriculture R&D — Phase 1"
phase: "Weeks 1-3: Bioinformatics Infrastructure"
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
  - "dpa148-lab-space-procurement.md"
confidence_overall: "high"
sources_cited: "nf-core best practices, EBI/NCBI submission guidelines, cloud architecture benchmarks, Indian data residency requirements"
---

# Bioinformatics Infrastructure Setup Plan for DPA-75 Genomics Facility

## 1. Executive Summary

This document specifies the compute, storage, pipeline, and data management infrastructure required to process sequencing data from the Illumina NextSeq 2000 and Oxford Nanopore PromethION P24 instruments for the Medicinal Agriculture R&D workstream ([DPA-75](/DPA/issues/DPA-75)).

**Target**: Operational bioinformatics pipeline producing QC-passed assemblies, variant calls, and annotations for 6 priority medicinal plants by **Week 8**, aligned with lab go-live.

---

## 2. Compute Architecture

### 2.1 Hybrid Model (Recommended)

| Layer | Specification | Purpose | Indicative Cost |
|---|---|---|---|
| **On-prem head node + NAS** | 2× AMD EPYC 9354 (32c), 512 GB RAM, 200 TB usable (ZFS RAID-6), 10 GbE + 25 GbE uplink | Primary storage, file server, workflow orchestration, local analysis | INR 22–28 Lakh |
| **GPU Workstation (local)** | Threadripper PRO 7985WX (64c), 256 GB RAM, 2× NVIDIA RTX A6000 (48 GB VRAM each), 4 TB NVMe | Assembly (hifiasm, Verkko), ML/DL, GPU-accelerated tools (DeepVariant, Clair3) | INR 16–20 Lakh |
| **Cloud burst (AWS/GCP/Azure)** | Spot instances (c6i.32xlarge, g5.24xlarge), FSx for Lustre / Filestore, S3/GCS lifecycle | Population-scale re-sequencing (100+ samples), large assembly jobs, training runs | INR 8–15 Lakh/yr |
| **Optional HPC cluster (Phase 3)** | 4× 64c EPYC, 2 TB RAM/node, 8× H100, 100 GbE InfiniBand, 1 PB parallel FS | Deep learning on phenome-genome, pangenome graphs | INR 1.5–2.2 Cr (defer) |

**Total Year-1 Compute Capex**: INR 38–48 Lakh

### 2.2 Network & Security

- **Instrument VLAN**: Isolated /24, no internet egress; sequencers push to NAS via 10 GbE
- **Analysis VLAN**: Full internet for container pulls, DB access; 25 GbE to NAS
- **DMZ**: Reverse proxy for web UIs (JupyterHub, IGV.js, JBrowse2)
- **VPN**: WireGuard for remote access; MFA enforced
- **Encryption**: LUKS2 on all disks; TLS 1.3 for all services; S3 SSE-KMS for cloud
- **Backup**: Nightly ZFS snapshots → offsite (Wasabi/S3 Glacier IR); 30-day retention raw, 5-year assemblies

---

## 3. Software Stack & Pipeline

### 3.1 Containerised Workflow Environment

| Component | Version | Purpose |
|---|---|---|
| **Nextflow** | 24.04+ | Workflow orchestration |
| **nf-core** | 2.14+ | Community-curated pipelines |
| **Singularity/Apptainer** | 1.3+ | HPC-compatible containers |
| **Conda/Mamba** | 23.11+ | Lightweight env management |
| **Cromwell/WDL** | 86+ | Alternative (GATK) |

### 3.2 Core Pipelines (nf-core + custom)

| Pipeline | nf-core Module | Customisation |
|---|---|---|
| **Illumina WGS QC & Assembly** | `nf-core/eager` (ancient DNA) → adapt; or `nf-core/assembly` (metaSPAdes/MEGAHIT) | Add plant-specific k-mer filtering; chloroplast/mitochondria removal |
| **ONT QC & Assembly** | `nf-core/nanoseq` (basecalling, QC) + custom Flye/hifiasm/Verkko assembly | Polyploid-aware assembly; Hi-C scaffolding integration |
| **Hybrid Assembly** | Custom (Verkko, HASLR, Unicycler) | Parameter sweep for each species |
| **Polishing & QC** | `nf-core/polishing` (Pilon, Homopolish, NextPolish) | BUSCO + Merqury QV |
| **Annotation** | Custom (BRAKER3, MAKER, EvidenceModeler, InterProScan) | Species-specific Augustus models; RNA-seq evidence |
| **Variant Calling (Illumina)** | `nf-core/sarek` (Germline) → adapt for plants | DeepVariant + GATK4 HaplotypeCaller consensus |
| **Variant Calling (ONT)** | Custom (Clair3, Sniffles2) | Phased variants; SV genotyping |
| **RNA-seq / Isoform** | `nf-core/rnaseq` (Salmon/DESeq2) + FLAIR/Bambu (ONT) | Full-length isoform quantification |
| **Methylation (ONT)** | Dorado built-in + custom methylation calling | 5mC/6mA context reports |
| **Population Genomics** | Custom (PLINK2, scikit-allel, ANGSD) | FST, PCA, selection scans |
| **Pangenome / Graph** | Custom (Minigraph-Cactus, PGGB) | Phase 2+ |

### 3.3 Reference Data & Databases (Local Mirrors)

| Database | Size | Update Cadence | Source |
|---|---|---|---|
| NCBI RefSeq Plant Genomes | ~2 TB | Quarterly | NCBI FTP |
| Ensembl Plants | ~1.5 TB | Quarterly | Ensembl FTP |
| Phytozome | ~500 GB | Bi-annual | JGI |
| UniProt/TrEMBL (Viridiplantae) | ~200 GB | Monthly | UniProt |
| Pfam / InterPro | ~50 GB | Bi-annual | EBI |
| PlantCyc / KEGG Plant | ~10 GB | Quarterly | Pathway DBs |
| SRA/ENA metadata (plant) | ~100 GB | Monthly | EBI |

**Total local mirror**: ~4.3 TB (fits on NAS with room for growth).

---

## 4. Data Management & Metadata

### 4.1 Sample Metadata Schema (extends existing plant schema)

```yaml
# Aligned to plant-research/schema/plant-knowledge-schema.json
sample_metadata:
  sample_id: "DPA-75-TULSI-001"
  plant_identification:
    scientific_name: "Ocimum tenuiflorum L."
    variety: "Rama Tulsi"
    accession: "DPA-GERM-2024-042"
  collection:
    date: "2026-01-15"
    location: "DPA Pilot Farm, Karnataka"
    gps: "12.9716, 77.5946"
    tissue: "young leaf"
    collector: "DPA Field Team"
  sequencing:
    platform: ["Illumina NextSeq 2000", "Oxford Nanopore PromethION"]
    library_type: "WGS PCR-free / ONT Ligation"
    run_id: "NS2000-20260120-RUN042 / P24-20260122-FC018"
    read_length: "2x150 bp / N50 25 kb"
    coverage_target: "60x Illumina + 40x ONT"
  processing:
    pipeline_version: "dpa75-wgs-v1.2.0"
    nf_core_version: "2.14"
    container_digest: "sha256:abc123..."
    qc_metrics:
      illumina_q30_pct: 92.3
      ont_q20_pct: 88.7
      assembly_n50: 42.1 Mb
      busco_complete: 98.2%
  biosafety:
    ibsc_approval: "IBSC-DPA-2026-003"
    containment_level: "BSL-2"
```

### 4.2 LIMS Integration

- **Platform**: **OpenSpecimen** (open source, DBT-compliant) or **Benchling** (if budget allows)
- **Integration**: REST API → Nextflow `sampleSheet.csv` auto-generation
- **Barcoding**: 2D barcoded tubes (Micronic/Simport) + scanner at receipt
- **Chain of custody**: Immutable audit log (append-only DB table)

### 4.3 Data Release & Publication

| Data Type | Repository | Timeline | Access |
|---|---|---|---|
| Raw reads (FASTQ/POD5) | NCBI SRA / ENA | Pre-publication (embargo) | Controlled |
| Assemblies (FASTA+GFF) | NCBI GenBank / ENA | On publication | Public |
| Variants (VCF) | EVA (European Variation Archive) | On publication | Public |
| Annotations (GFF3, functional) | Figshare / Zenodo (DOI) | On publication | Public |
| Expression matrices | GEO / ArrayExpress | On publication | Public |
| Pipeline code + containers | GitHub (DPA-org) + Zenodo DOI | Continuous | Public (MIT/Apache-2.0) |

---

## 5. Implementation Timeline (Weeks 1–8)

| Week | Milestone | Dependencies |
|---|---|---|
| **W1** | Procure hardware (head node, GPU WS, NAS disks); order cloud credits | Budget sign-off |
| **W1** | Deploy Kubernetes (k3s) / Slurm on head node; configure Apptainer | Hardware delivery |
| **W2** | Mount NAS; configure ZFS, snapshots, replication | NAS ready |
| **W2** | Deploy nf-core + custom pipeline repo (GitLab/GitHub); CI/CD (GitLab CI / GitHub Actions) | Git infra |
| **W3** | Pull/build all containers (Singularity); test on synthetic data | Containers |
| **W3** | Configure cloud burst (AWS Batch / GCP Life Sciences / Azure Batch) | Cloud account |
| **W4** | Deploy LIMS (OpenSpecimen); integrate barcode scanner | LIMS server |
| **W4** | Set up monitoring: Prometheus + Grafana (CPU, GPU, disk, queue) | K8s/Slurm |
| **W5** | Load reference databases; build indices (BWA, minimap2, Salmon, Kraken2) | NAS space |
| **W5** | Deploy web portals: JupyterHub, JBrowse2, IGV.js (auth via SSO) | Network |
| **W6** | End-to-end test: sequencer → NAS → pipeline → results → LIMS | Sequencer delivery |
| **W7** | IQ/OQ/PQ for bioinformatics (test datasets, known controls) | Vendor on-site |
| **W8** | **Go-Live**: Process first real sample; handoff to scientists | Lab go-live |

---

## 6. Personnel & Skills

| Role | FTE | Key Skills | Hiring Priority |
|---|---|---|---|
| **Bioinformatics Lead** | 1.0 | Nextflow, genome assembly, variant calling, Python/R, HPC | Week 1 (critical) |
| **Bioinformatics Engineer** | 1.0 | Containers, CI/CD, cloud, monitoring, LIMS API | Week 2 |
| **Data Scientist / ML** | 0.5 (ramp) | PyTorch, scikit-learn, plant phenomics, GWAS | Week 4 |
| **Systems Admin (part-time)** | 0.3 | Linux, ZFS, K8s/Slurm, networking, security | Week 1 (contract) |

---

## 7. Budget (Bioinformatics Only)

| Item | Capex (INR Lakh) | Opex Year 1 (INR Lakh) |
|---|---|---|
| Head node + NAS (200 TB) | 25 | 3 (power, support) |
| GPU Workstation (2× A6000) | 18 | 2 |
| Cloud burst credits | — | 12 |
| Software licences (Benchling optional) | — | 0–8 |
| Reference data mirror storage | included | 1 |
| Personnel (2.8 FTE loaded) | — | 85 |
| Training / conferences | — | 5 |
| **Total** | **43** | **108–116** |

---

## 8. Coordination with DPA-76 (Sustainable Manufacturing)

| Deliverable | Format | Cadence | Consumer |
|---|---|---|---|
| **Assembly + Annotation (GFF3/FASTA)** | FASTA + GFF3 + functional TSV | Per accession | Metabolic pathway engineering |
| **Variant VCF (phased)** | VCF/BCF + TBI index | Per population | Marker-assisted selection |
| **Expression matrices** | TPM/CPM matrix (HDF5) + DE results | Per experiment | Compound biosynthesis correlation |
| **Methylation reports** | BED + bigWig | Per sample | Epigenetic regulation of chemotypes |
| **Pipeline run reports** | MultiQC HTML + JSON summary | Per run | QA / audit trail |

**Data transfer**: rsync over 10 GbE LAN; S3 sync for cloud; checksums (MD5/SHA256) verified.

---

## 9. Risk Register (Bioinformatics-Specific)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Assembly fails for polyploid genomes (Tulsi, Ashwagandha) | High | High | Budget Hi-C (Arima/Phase Genomics); fallback to trio-binning if parents available |
| GPU memory insufficient for large assemblies | Medium | Medium | Cloud burst to H100 (80 GB); model parallelism |
| Cloud egress costs balloon | Medium | Medium | Keep raw data on-prem; only burst compute; lifecycle to Glacier |
| nf-core pipeline version drift breaks reproducibility | Low | High | Pin container digests; archive full env per run (Conda env export) |
| Data residency compliance (Indian DPDP Act 2023) | Medium | High | All raw/primary data on-prem or India-region cloud (Mumbai/Hyderabad); no cross-border without DPA |
| Talent retention (bioinformaticians) | High | High | Competitive compensation; publication authorship; conference budget; clear career path |

---

## 10. Immediate Actions (This Heartbeat)

1. **Finalize hardware PO** for head node + GPU workstation + NAS (aligned with lab fit-out Week 3).
2. **Provision cloud accounts** (AWS India / GCP Mumbai / Azure Central India); enable Life Sciences / Batch.
3. **Initialize Git repo** for pipeline code (`dpa75-bioinformatics-pipelines`); set up CI/CD.
4. **Start OpenSpecimen deployment** on head node (Docker Compose → K8s later).
5. **Draft first nf-core pipeline** (`dpa75/wgs-assembly`) using `nf-core create` template.
6. **Schedule kickoff** with DPA-76 data team to agree on metadata schema v1.0.

---

## 11. Acceptance Criteria for Bioinformatics Go-Live

| Criterion | Target | Verification |
|---|---|---|
| Head node + NAS operational | Week 4 | SSH + ZFS pool healthy |
| GPU workstation benchmarks | Week 4 | `nvidia-smi`; test assembly 1h |
| All core containers built & tested | Week 5 | `singularity run` on test data |
| Cloud burst functional | Week 5 | Submit test job → results in NAS |
| LIMS accepting samples + generating sample sheets | Week 6 | API test + barcode scan |
| End-to-end test (simulated sequencer run) | Week 7 | FASTQ → assembly → VCF → report |
| Monitoring dashboards green | Week 7 | Grafana: CPU, GPU, disk, queue |
| First real sample processed | Week 8 | QC report + MultiQC uploaded |

---

## 12. Confidence Summary

| Section | Confidence |
|---|---|
| Compute architecture (hybrid) | **high** |
| Pipeline tooling (nf-core + custom) | **high** |
| Metadata schema alignment | **high** |
| Cloud burst cost model | **medium** (depends on actual sample volume) |
| Hiring timeline | **medium** (talent market) |
| Indian data residency compliance | **high** (on-prem primary) |

---

*Document maintained by Botanical Research Agent under [DPA-148](/DPA/issues/DPA-148). Completes the trilogy with equipment requirements and lab space/procurement docs. Ready for Phase 1 execution.*