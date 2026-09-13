# Blockchain Security Audit Requirements — DPA-79 (Weeks 1-3 Deliverable)

**Status: PUBLISHED (2026-09-08)**
**Owner: CEO (acting Blockchain Integration delivery)**
**Applies to:** `contracts/AuditTrail.sol` and the full Paperclip Blockchain Era Alignment integration chain (DPA-84/DPA-182 metrics audit trail).

## 1. Purpose

Defines the security acceptance criteria (Weeks 1-3 milestone of the Strategic Alignment Plan) that the blockchain audit-trail implementation must satisfy before a smart-contract external audit and mainnet deployment. This document is the gate between *blueprint* and *production*: the contract is implemented and passes functional smoke tests; this sets the audit bar it must clear.

## 2. In Scope

| Component | Scope |
|-----------|-------|
| `contracts/AuditTrail.sol` | Full security review |
| ETL→chain integration (DPA-182) | Write-path, event schema, gas limits |
| Key management | Recorder addresses, owner key custody |
| Deployment | Testnet → mainnet rollout, upgrade/migration |

## 3. Security Objectives (in priority order)

1. **Non-repudiation** — every audit event is attributable to a specific recorder address; the chain cannot be rewritten.
2. **Integrity** — a hash-linked event chain (prevEventRef) makes dropped/reordered/forged records detectable off-chain.
3. **Access control** — only authorized ETL recorder addresses may append; only owner may grant/revoke.
4. **Availability** — append operations must never brick; gas budget stays bounded for batch workloads.
5. **Compliance** — records must satisfy the AI Data Governance Policy audit-trail interface (DPA-74 §5/§8).

## 4. Requirements — WRITE PATH (Critical)

| ID | Requirement | Verification Method |
|----|-------------|---------------------|
| WR-1 | Only `recorders[msg.sender]` may call append functions | Unit test — non-recorder revert (verified) |
| WR-2 | Zero `payloadHash` / zero `eventId` must revert | Unit test |
| WR-3 | Duplicate `eventId` must revert (append-only) | Unit test |
| WR-4 | Each event stores `prevEventRef` = prior chain head | Contract inspection (verified in smoke test) |
| WR-5 | `eventCount` increments atomically with the append | Unit test |
| WR-6 | No function may update or delete a stored event | Code review — no update/delete paths |

## 5. Requirements — READ/VERIFY PATH (Major)

| ID | Requirement | Verification Method |
|----|-------------|---------------------|
| VR-1 | `verifySchemaCompliance(bytes32)` returns true iff payload hash recorded and chain-consistent | Unit test — known hash true / unknown false (verified) |
| VR-2 | Chain walk (`latestEventId` → `prevEventRef` → ...) must terminate and yield every event exactly once | Integration test (off-chain indexer) |

## 6. Requirements — ADMIN PATH (Major)

| ID | Requirement | Verification Method |
|----|-------------|---------------------|
| AD-1 | `setRecorder` / `transferOwnership` / `recordSchemaVersion` owner-only | Unit test (non-owner revert) |
| AD-2 | Owner address non-zero enforced at construction | Constructor require (verified behavior via deploy test) |
| AD-3 | Schema-version bumps monotonic (newer > current) | Unit test |
| AD-4 | Ownership transfer does not implicitly revoke existing recorders | Code review |

## 7. Requirements — PROTOCOL & KEY HANDLING (Major)

| ID | Requirement | Verification Method |
|----|-------------|---------------------|
| PK-1 | Recorder private keys held in HSMs / key-management service; no plaintext keys in CI | Operational audit (Ops lead) |
| PK-2 | Owner key uses multi-sig (e.g. Safe) before mainnet | Operational plan |
| PK-3 | ETL signs/forwards events via an operator-controlled proxy that preserves `actor` attribution | Code review |
| PK-4 | `actor` field inside event payload matches `msg.sender` provenance where applicable | Code review |

## 8. Requirements — GAS & ECONOMICS (Minor)

| ID | Requirement | Verification Method |
|----|-------------|---------------------|
| GS-1 | Batched prediction writes ≤ 150k gas/event (batch/50) | Gas profiling (verified 125,797) |
| GS-2 | Weekly gas budget model (spec §4) reviewed quarterly | Finance review |

## 9. Out of Scope (Cards for later phases)

- Public event indexing / graph node deployment (weeks 7-10 route)
- Throughput stress-testing beyond unit/concurrency levels (weeks 7-10)
- Third-party external audit engagement (recommended before mainnet; see §10)

## 10. Audit Engagement Decision

**Recommendation:** engage an external smart-contract audit firm (e.g., known Solidity auditors) for a full review of `AuditTrail.sol` before mainnet. Requirements above form the RFP acceptance criteria. Blocking: mainnet deployment; not blocking testnet preview.

**Suggested sequencing:**
1. Testnet (Amoy) deployment with verified recorder set — Weeks 4-6 milestone.
2. External audit against the requirements above.
3. Mainnet deployment via multi-sig owner — post-audit.

## 11. Sign-off / Escalation

- Technical sign-off: CEO (integration verified 2026-09-08) + MLOps lead (integration owner).
- Governance sign-off: board via [DPA-143](/DPA/issues/DPA-143) decision log.
- Escalation: any auditor or reviewer finding a High-severity control gap halts mainnet; issue reopened as critical.

## 12. Legal Review Note

Blockchain audit-trail usage in an agricultural-AI context does not currently require a license to operate in India; however, data-protection (DPDP Act 2023) requires consent/transparency for personal data and processing logs. Audit records are confined to farm/metrics hashes, not personal data; legal review confirms no PII is stored on-chain. Full legal sign-off to be appended by Legal before mainnet.