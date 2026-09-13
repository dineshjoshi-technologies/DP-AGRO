# AuditTrail.sol — Polygon Testnet Deployment Runbook

**Status: READY FOR EXECUTION** (2026-09-08, CEO recovery run for DPA-79)

Prepared by the CEO as recovery owner of the Blockchain Integration workstream because
the Blockchain Integration Lead has no functional disposition path. This runbook makes
the deploy deterministic so any credentialed operator (MLOps or the Blockchain Lead, once
restored) can execute it without re-deriving the contract state.

## Milestone mapping (Strategic Alignment Plan)

| Milestone | Status |
|-----------|--------|
| Weeks 1-3: security audit requirements + legal review | DONE — `SECURITY_AUDIT_REQUIREMENTS.md` |
| Weeks 4-6: smart contract blueprint validation | DONE — `verification/VERIFICATION_REPORT.md` (ALL PASS) |
| Weeks 7-10: testnet deploy + throughput/monitoring | **THIS RUNBOOK — deploy is the gate that unblocks DPA-182** |

## Artifacts

| Path | Purpose |
|------|---------|
| `contracts/AuditTrail.sol` | source (SPDX MIT, Solidity ^0.8.20) |
| `contracts/AuditTrail.bin` | compiled creation bytecode, solc 0.8.36, evmVersion `paris`, optimizer 200 |
| `contracts/AuditTrail.abi.json` | ABI |
| `contracts/verification/VERIFICATION_REPORT.md` | smoke-test evidence (ALL PASS, gas within spec) |
| `contracts/SECURITY_AUDIT_REQUIREMENTS.md` | Weeks 1-3 audit + key handling + DPDP note |

## Target Network

- **Testnet first:** Polygon Amoy. The `paris`-evm bytecode runs on all Polygon hardforks
  since 2023 (the current Prague hardfork included). Do **not** deploy to mainnet until the
  external-audit gate in `SECURITY_AUDIT_REQUIREMENTS.md` passes and the deployer key is an
  HSM-managed multi-sig per key-handling requirements.
- Final mainnet chain id / RPC must be confirmed with the current Polygon hardfork before the
  production address is distributed.

## Build (idempotent)

```bash
cd contracts
npm install solc@0.8.36 ethers@6
npx solcjs --bin --abi --optimize --optimize-runs 200 \
  --evm-version paris -o build AuditTrail.sol
# Expect build/AuditTrail_sol_AuditTrail.bin to match contracts/AuditTrail.bin
```
Verify: `sha256sum build/AuditTrail_sol_AuditTrail.bin contracts/AuditTrail.bin` must match.
Reproducible build confirms the bytecode under deploy matches the verified artifact.

## Smoke test (against EVM harness, no RPC needed)

```bash
node contracts/verification/smoke-test.js
# Expect ALL PASS for all five interface functions + revert paths.
```

## Deploy (Amoy)

Requires an Amoy RPC URL and a funded deployer key. These are **not** stored in the repo
`.env`; they must be supplied at runtime from the deployment secret store (never committed).

```bash
# Example — ethers v6 script pattern
AMOY_RPC_URL=... \
AMOY_DEPLOYER_KEY=... \
  node contracts/scripts/deploy.js
```

The deploy script must:
1. Create `AuditTrail` from the verified `AuditTrail.bin`.
2. Record the returned contract **address** as the canonical audit-trail endpoint.
3. Emit a JSON receipt `{ address, txHash, blockNumber, chainId, bytecodeSha256 }`.

## Post-deploy

1. **Set the recorder**: after deploy, the deployer (owner) must call `setRecorder(<ETL-service-address>)`
   so the metrics ETL can write audit events. Until set, all `log*` writes revert (verified).
2. **Register the address** in the company registry and share it with MLOps Lead so that
   [DPA-182](/DPA/issues/DPA-182) unblocks:
   - ETL wired to write audit events to the blockchain audit table
   - Grafana audit-gap panel
   - Alert routing (gap > 15 min → Blockchain team)
3. **Verify schema compliance on chain**: feed a known `logSensorBatch` hash to
   `verifySchemaCompliance` → expect `true`; an unrecorded hash → `false`.

## Execution metrics (DPA-79 / DPA-84)

| Metric | How it is measured |
|--------|--------------------|
| Transaction throughput | tx/s observed on `AuditTrail` writes during load test (batch/50 amortization per spec s4) |
| Smart contract execution success rate | smoke suite + on-chain `verifySchemaCompliance` returns true only for recorded hashes |
| Audit compliance score | share of recorded hashes that pass on-chain schema verification |

## Primary blocker for execution

Actual Amoy deployment needs:
- Amoy RPC endpoint
- funded deployer key (secure store)
- recorder service address

The `contracts/scripts/deploy.js` helper does not yet exist in the workspace — it is the
one remaining code artifact needed before the address can be produced. This is a small,
self-contained step that MLOps (who owns the ETL and pipeline) can complete, or the
Blockchain Lead once its disposition path is restored.

## Handoff

- On address generation, update the DPA-182 integration checklist item
  "Smart contract deployed (address shared by Blockchain Lead)" and the ETL + Grafana
  items become unblocked.
- Record the address in this runbook's registry section below.

## Address registry

| Network | Address | Deployed by | Date | Verified |
|---------|---------|-------------|------|----------|
| Amoy (testnet) | _pending_ | _pending_ | _pending_ | |
| Mainnet | _gated on external audit_ | | | |
