const { VM } = require('@ethereumjs/vm');
const { Common } = require('@ethereumjs/common');
const { Address, hexToBytes, bytesToHex } = require('@ethereumjs/util');
const { ethers } = require('ethers');
const fs = require('fs');
const abi = require('./AuditTrail.abi.json');
const bytecode = '0x' + fs.readFileSync('./AuditTrail.bin','utf8');

async function main(){
  const common = Common.custom({ chainId: 137, name: 'polygon', networkId: 137, defaultHardfork: 'paris' });
  const vm = await VM.create({ common });
  const runner = Address.fromString('0x1111111111111111111111111111111111111111');
  const recorder = Address.fromString('0x3333333333333333333333333333333333333333');
  const iface = new ethers.Interface(abi);

  const deployData = ethers.concat([bytecode, '0x'+'00'.repeat(12)+'11'.repeat(20)]);
  let res = await vm.evm.runCall({ caller: runner, data: hexToBytes(deployData), gasLimit: BigInt(0xffffff) });
  if (res.exceptionError) throw new Error('deploy failed: '+res.exceptionError.exception);
  const ca = res.createdAddress;
  console.log('deployed at', ca.toString(), 'gas', res.execResult.executionGasUsed.toString());
  const caddr = ca;

  const call = async (from, dataHex) => {
    const r = await vm.evm.runCall({ caller: from, to: caddr, data: hexToBytes(dataHex), gasLimit: BigInt(0xffffff) });
    const e = r.execResult.exceptionError;
    return { ex: e ? e.error : null, gas: r.execResult.executionGasUsed.toString(), ret: bytesToHex(r.execResult.returnValue) };
  };

  // owner logs sensor batch
  let r = await call(runner, iface.encodeFunctionData('logSensorBatch', ['0x'+'ab'.repeat(32), 1n, '0x'+'0f'.repeat(32)]));
  console.log('logSensorBatch owner:', r.ex, 'gas', r.gas);

  // verify known
  r = await call(runner, iface.encodeFunctionData('verifySchemaCompliance', ['0x'+'ab'.repeat(32)]));
  console.log('verify known:', r.ret);
  // verify unknown
  r = await call(runner, iface.encodeFunctionData('verifySchemaCompliance', ['0x'+'ff'.repeat(32)]));
  console.log('verify unknown:', r.ret);

  // non-recorder blocked
  r = await call(recorder, iface.encodeFunctionData('logModelTraining', ['0x'+'cc'.repeat(32), '0x'+'dd'.repeat(32), '0x1234567812345678']));
  console.log('non-recorder (exp revert):', r.ex, 'gas', r.gas);

  // grant recorder
  r = await call(runner, iface.encodeFunctionData('setRecorder', ['0x'+'33'.repeat(20), true]));
  console.log('setRecorder:', r.ex, 'gas', r.gas);

  // recorder logs model training with metrics
  r = await call(recorder, iface.encodeFunctionData('logModelTraining', ['0x'+'cc'.repeat(32), '0x'+'dd'.repeat(32), '0x1234567812345678']));
  console.log('recorder logModelTraining:', r.ex, 'gas', r.gas);

  // predictions
  r = await call(recorder, iface.encodeFunctionData('logPredictions', ['0x'+'0e'.repeat(32), 50n]));
  console.log('logPredictions:', r.ex, 'gas', r.gas);

  // promotion
  r = await call(runner, iface.encodeFunctionData('logModelPromotion', ['0x'+'44'.repeat(20), '0x'+'13'.repeat(32)]));
  console.log('logModelPromotion:', r.ex, 'gas', r.gas);

  // head
  r = await call(runner, iface.encodeFunctionData('head', []));
  console.log('head:', r.ret.length, r.ex);
  console.log('ALL PASS');
}
main().catch(e=>{ console.error('ERR',e); process.exit(1); });
