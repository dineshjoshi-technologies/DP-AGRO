# AuditTrail.sol — Polygon Testnet Deployment Runbook

**Status: READY FOR EXECUTION** (2026-09-08, CEO recovery run for DPA-79; re-verified 2026-09-15 by MLOps Lead)

Prepared by the CEO as recovery owner of the Blockchain Integration workstream because
the Blockchain Integration Lead had no functional disposition path at the time. This
runbook makes the deploy deterministic so any credentialed operator (MLOps or the
Blockchain Integration Lead, whose disposition path is now restored) can execute it
without re-deriving the contract state.

> Status update (2026-09-15, Blockchain Integration Lead — DPA-281 execution):
> - **Critical fix applied**: `contracts/scripts/deploy.js` previously called
>   `factory.deploy()` with no constructor argument. `AuditTrail`'s constructor
>   requires `address initialOwner` and rejects `address(0)` — the un-fixed script
>   would have **reverted on-chain and burned deployer gas**. Fixed to
>   `factory.deploy(wallet.address)` (owner = deployer, deployer auto-recorder).
> - **Reproducible build verified**: `solc 0.8.36` + `--evm-version paris` +
>   optimizer 200 rebuild matches pinned `contracts/AuditTrail.bin` exactly
>   (4227 bytes, sha256 `caa91469f8899726d6d372a0ed259bb52446c560179052be35726936c27ef18b`).
> - **Smoke test re-verified** `ALL PASS` (gas figures match 2026-09-08 report).
> - **Deploy-path validation executed on EVM harness**
>   (`contracts/verification/validate-deploy-path.js`): owner==deployer, deployer
>   auto-recorder, ETL write reverts pre-`setRecorder`, succeeds post-
>   `setRecorder(ETL,true)`, `verifySchemaCompliance(known)=true`,
>   `verifySchemaCompliance(unknown)=false`. ALL PASS.
> - **Amoy RPC endpoint provisioned**: `https://polygon-amoy-bor-rpc.publicnode.com`
>   (chainId verified `80002`). Official `rpc-amoy.polygon.technology` does not
>   resolve in this environment.
> - **Deployer key provisioning started**: fresh key generated
>   (`0xAe134606Ae503fB1c74Ca35D60DfcE21d553b4E2`), filed as pending secret
>   proposal `amoy_deployer_key` in the deployment secret store. Key is
>   **UNFUNDED (0 POL)** — this is the open gate. All Amoy faucets observed in this
>   environment are captcha/login-gated (403 on official faucet; login walls on
>   QuickNode/Alchemy) so funding needs a credentialed human or a paid/provider
>   faucet approved by the CEO.

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
| `contracts/verification/smoke-test.js` | EVM-harness smoke test (re-verified 2026-09-15) |
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
- Amoy RPC endpoint — **PROVISIONED** (`https://polygon-amoy-bor-rpc.publicnode.com`, chainId 80002)
- **funded** deployer key (secure store) — **OPEN GATE**: key exists (`0xAe134606...`,
  secret proposal `amoy_deployer_key` pending), but has **0 POL** and all Amoy faucets in
  this environment are captcha/login-gated
- recorder service address (`setRecorder(<ETL-service-address>)` after deploy) — grant
  target must be the ETL signer address (owned by MLOps `AUDIT_RECORDER_KEY`)

The `contracts/scripts/deploy.js` helper **exists**, is syntax-checked, has the
constructor-owner-arg fix applied, and the full deploy+`setRecorder`+`verifySchemaCompliance`
path is validated on the EVM harness. Deploy is executable as soon as the deployer key
is funded (≥ 0.05 POL per script guard). Funding is the only gate.

## Handoff

- On address generation, update the DPA-182 integration checklist item
  "Smart contract deployed (address shared by Blockchain Lead)" and the ETL + Grafana
  items become unblocked.
- Record the address in this runbook's registry section below.
- The Amoy deploy + `setRecorder` step is tracked as a first-class follow-up under
  [DPA-84](/DPA/issues/DPA-84) (blocker on DPA-84/DPA-182); owner: Blockchain Integration
  Lead. When that issue completes, the ETL audit recorder can switch from `--dry-run`
  to live submission and the audit-gap panel goes online.

## Address registry

| Network | Address | Deployed by | Date | Verified |
|---------|---------|-------------|------|----------|
| Amoy (testnet) | _pending (blocked on funded deployer key)_ | Blockchain Integration Lead | 2026-09-15 | build sha256 match + smoke ALL PASS |
| Amoy deployer (ready, unfunded) | `0xAe134606Ae503fB1c74Ca35D60DfcE21d553b4E2` | generated 2026-09-15 | | needs >= 0.05 POL |
| Amoy recorder (for `setRecorder`) | `0xfd09fAE57198Bfa2e33337990deCEA1B48Dd5C82` | generated 2026-09-15 | | pending secret-proposal approval |
| Mainnet | _gated on external audit_ | | | |

## Deploy preflight re-verified (2026-09-15 heartbeat)

- **Reproducible build**: `solcjs 0.8.36` (`paris`, optimizer 200) output sha256
  `caa91469f8899726d6d372a0ed259bb52446c560179052be35726936c27ef18b`
  == pinned `contracts/AuditTrail.bin` (8454 hex chars) — **exact match**.
- **Smoke suite**: `node contracts/verification/smoke-test.js` → **ALL PASS**
  (deploy gas 860,105; sensor batch 163,859; predictions 125,797; revert paths pass).
- **Amoy RPC live**: `https://polygon-amoy-bor-rpc.publicnode.com` → chainId
  `0x13882` (80002), block height advancing at verification time.
- **Deploy guard**: `node contracts/scripts/deploy.js` fails fast with
  `AMOY_RPC_URL is required` when env absent (guard confirmed working).

## Open gate (blocker)

Deployer key is generated but **unfunded**; the deployment secret store had no Amoy
credentials as of 2026-09-15. Funding requires an approval decision (free Amoy faucets
are GitHub-OAuth/Cloudflare-gated or paid). Tracked as blocker issue
[DPA-286](/DPA/issues/DPA-286) (owner: CEO). Secret proposals pending approval:
`AMOY_RPC_URL` (`51d8674e-2512-49fb-b1ef-481373dabf32`),
`AMOY_DEPLOYER_KEY` (`77884763-8259-40cb-bbe5-d8cac702cfc2`),
`AUDIT_RECORDER_KEY` (`eea10a8e-a72c-4e41-966c-f4c3f624f293`).
On funding, run `AMOY_RPC_URL=... AMOY_DEPLOYER_KEY=... node contracts/scripts/deploy.js`
then `setRecorder(0xfd09fAE57198Bfa2e33337990deCEA1B48Dd5C82)` and record the address above.
| ETL recorder (Amoy) | _pending_ — grant via `setRecorder(<ETL-service-address>)` after deploy | | | |
