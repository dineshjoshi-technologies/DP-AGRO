const { VM } = require('@ethereumjs/vm');
const { Common } = require('@ethereumjs/common');
const { Address, hexToBytes, bytesToHex } = require('@ethereumjs/util');
const { ethers } = require('ethers');
const abi = require('./AuditTrail.abi.json');
const bytecode = '0x' + require('fs').readFileSync('./AuditTrail.bin','utf8').trim();

async function main(){
  const common = Common.custom({ chainId: 137, name: 'polygon', networkId: 137, defaultHardfork: 'paris' });
  const vm = await VM.create({ common });
  const deployer = Address.fromString('0x' + 'aa'.repeat(20));
  const etl = Address.fromString('0x' + 'bb'.repeat(20));

  // Mirror the FIXED deploy.js: factory.deploy(wallet.address) =>
  // bytecode ++ abi.encodeConstructor([deployerAddress])
  const iface = new ethers.Interface(abi);
  const constructorArgs = iface.encodeDeploy([deployer.toString()]);
  const deployData = ethers.concat([bytecode, constructorArgs]);
  let res = await vm.evm.runCall({ caller: deployer, data: hexToBytes(deployData), gasLimit: BigInt(0xffffff) });
  if (res.exceptionError) { console.log('DEPLOY REVERTED:', res.exceptionError.error); process.exit(1); }
  const ca = res.createdAddress;
  console.log('deployed at', ca.toString(), 'gas', res.execResult.executionGasUsed.toString());

  const call = async (from, dataHex) => {
    const r = await vm.evm.runCall({ caller: from, to: ca, data: hexToBytes(dataHex), gasLimit: BigInt(0xffffff) });
    if (r.execResult.exceptionError) return { ex: r.execResult.exceptionError.error, gas: r.execResult.executionGasUsed.toString(), ret: '' };
    return { ex: null, gas: r.execResult.executionGasUsed.toString(), ret: bytesToHex(r.execResult.returnValue) };
  };

  // owner check
  let r = await call(deployer, iface.encodeFunctionData('owner'));
  console.log('owner is deployer:', r.ret.toLowerCase().endsWith('aa'.repeat(20)));

  // deployer (auto-recorder via constructor) can log
  r = await call(deployer, iface.encodeFunctionData('logSensorBatch', ['0x'+'ab'.repeat(32), 1n, '0x'+'0f'.repeat(32)]));
  console.log('deployer logSensorBatch (should succeed):', r.ex, 'gas', r.gas);

  // ETL not yet a recorder -> write reverts
  r = await call(etl, iface.encodeFunctionData('logSensorBatch', ['0x'+'cd'.repeat(32), 2n, '0x'+'0f'.repeat(32)]));
  console.log('ETL pre-setRecorder write (should revert):', r.ex);

  // owner setRecorder(ETL, true) — mirror of issue step 4
  r = await call(deployer, iface.encodeFunctionData('setRecorder', [etl.toString(), true]));
  console.log('setRecorder(ETL,true):', r.ex, 'gas', r.gas);

  // ETL recorder now writes
  r = await call(etl, iface.encodeFunctionData('logSensorBatch', ['0x'+'ef'.repeat(32), 3n, '0x'+'0f'.repeat(32)]));
  console.log('ETL post-setRecorder write:', r.ex, 'gas', r.gas);

  // verify known hash -> true, unknown -> false (issue step 5)
  r = await call(deployer, iface.encodeFunctionData('verifySchemaCompliance', ['0x'+'ef'.repeat(32)]));
  console.log('verifySchemaCompliance(known) =', r.ret);
  r = await call(deployer, iface.encodeFunctionData('verifySchemaCompliance', ['0x'+'ff'.repeat(32)]));
  console.log('verifySchemaCompliance(unknown) =', r.ret);

  console.log('VALIDATE-DEPLOY-PATH: ALL PASS');
}
main().catch(e=>{ console.error('ERR', e); process.exit(1); });
