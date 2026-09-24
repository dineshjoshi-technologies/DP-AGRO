#!/usr/bin/env node
/*
 * Blockchain audit recorder for the metrics ETL (DPA-182).
 *
 * Consumes the same --audit-events input as metrics-etl.py and writes sensor
 * batch hashes to the AuditTrail smart contract (DPA-79) audit table:
 *
 *   [{event_type, timestamp_utc, batch_hash, farm_id}]
 *
 * Encodes each `sensor_batch_ingest` event as `logSensorBatch(bytes32 hash,
 * uint256 timestamp, bytes32 farmId)` using the ABI pinned in
 * contracts/AuditTrail.abi.json, signs with the recorder key, and submits the
 * transaction. Designed to be dropped into the ETL cron after the contract
 * address + recorder role are provisioned by the deploy runbook.
 *
 * Env (never committed):
 *   AUDIT_CONTRACT_ADDRESS  deployed AuditTrail address (from deploy receipt)
 *   AUDIT_RPC_URL           chain RPC (testnet first: Amoy)
 *   AUDIT_RECORDER_KEY      ECDSA key granted recorder role via setRecorder()
 *
 * Usage:
 *   node blockchain-recorder.js --audit-events audit_events.json
 *   node blockchain-recorder.js --audit-events audit_events.json --dry-run  # calldata only
 *   node blockchain-recorder.js --audit-events audit_events.json --status   # on-chain state
 *
 * Exit codes: 0 ok, 1 bad input/env, 2 chain error.
 */

const fs = require('fs');

let ethers;
try {
  ethers = require('ethers');
} catch {
  ethers = require(`${__dirname}/../../contracts/node_modules/ethers`);
}

const ABI_PATH = `${__dirname}/../../contracts/AuditTrail.abi.json`;
const SENSOR_EVENT = 'sensor_batch_ingest';
const BATCH_MAX = 50;

function loadEvents(path) {
  let data = JSON.parse(fs.readFileSync(path, 'utf8'));
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.records)) return data.records;
  throw new Error(`${path}: expected a JSON array or {"records": [...]}`);
}

function toBytes32(value, field) {
  if (value === undefined || value === null) throw new Error(`${field}: missing`);
  let hex = String(value).replace(/^0x/, '');
  if (hex.length !== 64) {
    hex = ethers.keccak256(ethers.toUtf8Bytes(String(value))).slice(2);
  }
  return '0x' + hex;
}

function toUnixSeconds(ts) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) throw new Error(`timestamp_utc: invalid (${ts})`);
  return Math.floor(d.getTime() / 1000);
}

function prepare(events) {
  const out = [];
  for (const e of events) {
    const eventType = e.event_type || e.eventType;
    if (eventType !== SENSOR_EVENT) continue;
    const hash = toBytes32(e.batch_hash || e.payloadHash || e.payload_hash, 'batch_hash');
    const timestamp = toUnixSeconds(e.timestamp_utc || e.timestamp);
    const farmId = toBytes32(e.farm_id || e.farmId || '0x0', 'farm_id');
    out.push({ event_type: eventType, timestamp_utc: e.timestamp_utc || e.timestamp, hash, timestamp, farmId });
  }
  return out;
}

async function main() {
  const args = require('node:util').parseArgs({
    options: {
      'audit-events': { type: 'string', required: true },
      'dry-run': { type: 'boolean', default: false },
      status: { type: 'boolean', default: false },
    },
  }).values;

  const events = loadEvents(args['audit-events']);
  const abi = JSON.parse(fs.readFileSync(ABI_PATH, 'utf8'));
  const prepared = prepare(events);

  if (prepared.length === 0) {
    console.error(`error: no ${SENSOR_EVENT} events found in input`);
    return 1;
  }

  const address = process.env.AUDIT_CONTRACT_ADDRESS;
  const rpc = process.env.AUDIT_RPC_URL;
  const recorderKey = process.env.AUDIT_RECORDER_KEY;
  const iface = new ethers.Interface(abi);

  const calldata = prepared.slice(0, BATCH_MAX).map((p) => ({
    ...p,
    calldataHex: iface.encodeFunctionData('logSensorBatch', [p.hash, p.timestamp, p.farmId]),
  }));

  if (args['dry-run']) {
    console.log(JSON.stringify({ mode: 'dry-run', contract_abi: abi[0] ? 'AuditTrail' : null, count: calldata.length, events: calldata }, null, 2));
    return 0;
  }

  if (!address || !rpc) {
    console.error(
      'error: AUDIT_CONTRACT_ADDRESS and AUDIT_RPC_URL are required outside --dry-run'
    );
    return 1;
  }
  const provider = new ethers.JsonRpcProvider(rpc);
  const contract = new ethers.Contract(address, abi, provider);

  try {
    if (args['status']) {
      const [eventCount, head, schemaVersion] = await Promise.all([
        contract.eventCount(),
        contract.head(),
        contract.schemaVersion(),
      ]);
      console.log(
        JSON.stringify(
          { mode: 'status', contract: address, eventCount: Number(eventCount), head, schemaVersion: Number(schemaVersion) },
          null,
          2
        )
      );
      return 0;
    }

    if (!recorderKey) {
      console.error('error: AUDIT_RECORDER_KEY is required to submit audit transactions');
      return 1;
    }
    const wallet = new ethers.Wallet(recorderKey, provider);
    const signerContract = contract.connect(wallet);

    const receipts = [];
    for (const p of prepared.slice(0, BATCH_MAX)) {
      await signerContract.logSensorBatch.staticCall(p.hash, p.timestamp, p.farmId);
      const tx = await signerContract.logSensorBatch(p.hash, p.timestamp, p.farmId);
      receipts.push({ hash: p.hash, timestamp: p.timestamp, farmId: p.farmId, txHash: tx.hash });
    }
    console.log(JSON.stringify({ mode: 'audit', contract: address, submitted: receipts.length, receipts }, null, 2));
    return 0;
  } catch (err) {
    console.error(`error: chain operation failed: ${err.message}`);
    return 2;
  }
}

try {
  main().then((code) => { process.exitCode = code; });
} catch (err) {
  console.error(`error: ${err.message}`);
  process.exitCode = 1;
}