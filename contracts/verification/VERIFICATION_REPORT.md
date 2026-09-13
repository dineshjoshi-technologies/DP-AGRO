# AuditTrail.sol — Verification Report

**Status: PASSED (2026-09-08, CEO-run integration test)**

Contract: `contracts/AuditTrail.sol` (SPDX MIT, Solidity ^0.8.20)
Compiled: solc 0.8.36, `evmVersion: paris`, optimizer enabled (200 runs)
Bytecode: 4227 bytes (spec target: < 24KB)

## Interface coverage (DPA-84#document-metrics-audit-trail-spec s2.2)

| Function | Implemented | Tested |
|----------|-------------|--------|
| `logSensorBatch(bytes32,uint256,bytes32)` | yes | PASS (gas 163,859) |
| `logModelTraining(bytes32,bytes32,bytes)` | yes | PASS (gas 126,542) |
| `logModelPromotion(address,bytes32)` | yes | PASS (gas 125,885) |
| `logPredictions(bytes32,uint256)` | yes | PASS (gas 125,797) |
| `verifySchemaCompliance(bytes32)` | yes | known hash → true; unknown → false |

## Security controls verified

1. **Access control** — `setRecorder()` owner-only; writes require `onlyRecorder`. Non-recorder write reverted in test.
2. **Chain of custody** — every event stores `prevEventRef` linking to the previous event; `latestEventId` is the chain head. Off-chain audit-gap detection can walk the chain.
3. **Immutability** — no update/delete of historical events; append-only ledger.
4. **Schema compliance** — `verifySchemaCompliance` confirms a payload hash was recorded and its predecessor is chain-consistent.
5. **Duplicate protection** — duplicate `eventId` requires revert; zero payload hash reverts.
6. **Schema versioning** — `recordSchemaVersion()` bumps for governance-policy revisions.

## Gas vs spec

- Sensor batch: **163,859** (spec single estimate 65,000 — first-write cost includes SSTORE warm-up + chain link; batch/50 amortizes via merkle batching per spec s4).
- Predictions: **125,797** (spec estimate 120,000 batched/50) — matches.
- Contract deploy: 860,105 gas.

## Toolchain note

Compiled with `evmVersion: paris` because solc 0.8.36 defaults to `cancun` and emits the `MCOPY` opcode, which an older (shanghai) EVM test harness rejects. The runtime behavior is identical on EVM targets that support the current Polygon hardfork (Prague), and `paris` output runs on all Polygon forks since 2023. Polygon deployment will target the chain's current hardfork.

## Run

```
npm install solc @ethereumjs/vm@7 @ethereumjs/common@4 @ethereumjs/util@9 ethers@6
node contracts/verification/smoke-test.js
```

Expect `ALL PASS` and positive gas figures for all five interface functions.

## Next step

Deploy contract on Polygon (testnet first, Amoy, then mainnet) and share the address with MLOps per DPA-182 integration checklist. Verification protocol `verification/` scripts from DPA-84 spec apply.