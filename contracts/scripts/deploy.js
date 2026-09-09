const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');
const abi = require(path.join(__dirname, '..', 'AuditTrail.abi.json'));
const bytecode = '0x' + fs.readFileSync(path.join(__dirname, '..', 'AuditTrail.bin'), 'utf8').trim();

// Usage:
//   AMOY_RPC_URL=... AMOY_DEPLOYER_KEY=... node contracts/scripts/deploy.js
//
// Reads deployer + RPC from env ONLY (never committed). Emits a JSON receipt on stdout:
//   { address, txHash, blockNumber, chainId, deployedBy, bytecodeSha256, timestamp }
//
// Note: build/deploy artifacts are verified against the repo-pinned AuditTrail.bin in
// the runbook. All values below come from the compiled artifact at build time.

async function main() {
  const rpcUrl = process.env.AMOY_RPC_URL || process.env.RPC_URL;
  const deployerKey = process.env.AMOY_DEPLOYER_KEY || process.env.DEPLOYER_KEY;
  if (!rpcUrl) throw new Error('AMOY_RPC_URL is required (Polygon Amoy testnet)');
  if (!deployerKey) throw new Error('AMOY_DEPLOYER_KEY is required — supply from secret store, never commit');

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(deployerKey, provider);
  const chainId = (await provider.getNetwork()).chainId;
  const balance = await provider.getBalance(wallet.address);
  const minGas = ethers.parseEther('0.05');
  if (balance < minGas) {
    throw new Error(`Deployer ${wallet.address} has ${ethers.formatEther(balance)} MATIC — need >= ${ethers.formatEther(minGas)} for Amoy deploy`);
  }

  const factory = new ethers.ContractFactory(abi, bytecode, wallet);
  const contract = await factory.deploy();
  const receipt = await contract.deploymentTransaction().wait();

  const { createHash } = await import('node:crypto');
  const bytecodeSha256 = createHash('sha256').update(bytecode.slice(2), 'hex').digest('hex');

  const out = {
    address: await contract.getAddress(),
    txHash: receipt.hash,
    blockNumber: receipt.blockNumber,
    chainId: chainId.toString(),
    deployedBy: wallet.address,
    bytecodeSha256,
    timestamp: new Date().toISOString(),
  };
  console.log(JSON.stringify(out, null, 2));
}

main().catch((err) => {
  console.error('DEPLOY FAILED:', err.message);
  process.exit(1);
});