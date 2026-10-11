/* Exercise measured-response decisions without commanding any hardware. */
const assert=require('node:assert/strict');
const {assess,Check,stuckZero}=require('../dashboard/static/load-cell-check.js');
const baseline=Array.from({length:15},(_,i)=>179200+(i%3-1)*20);
const released=baseline.slice();
for(const direction of [1,-1]) {
  const result=assess(baseline,baseline.map(v=>v+direction*3000),released);
  assert.equal(result.status,'RESPONSE / RETURNED');
  assert.equal(Math.sign(result.change),direction);
}
assert.equal(assess(baseline,baseline,released).status,'NO RESPONSE DETECTED');
assert.equal(assess(baseline,[1000000,...baseline],released).status,'NO RESPONSE DETECTED');
assert.equal(assess(baseline,baseline.map(v=>v+3000),baseline.map(v=>v+2000)).status,'RESPONSE / NOT RETURNED');
assert.equal(assess(Array(15).fill(0),Array(15).fill(0),Array(15).fill(0)).status,'STUCK AT ZERO');
assert.equal(assess([1],baseline,released).status,'INSUFFICIENT DATA');
assert.equal(assess([0,1000,-1000,0,1000,-1000,0,1000,-1000],Array(15).fill(1000),Array(15).fill(0)).status,'NO RESPONSE DETECTED');
const zero=Array.from({length:31},(_,i)=>({time_ms:i*200,load_raw:0}));
assert.equal(stuckZero(zero),true);
assert.equal(stuckZero(zero.slice(0,10)),false);
assert.equal(stuckZero([...zero,{time_ms:6200,load_raw:1}]),false);
const check=new Check();check.start(0,{seq:1,time_ms:100});
for(let i=1;i<60;i++) {
  const now=i*200;
  check.update(now,{seq:i+1,time_ms:100+now,load_raw:now<3000||now>=9000?179200:176200},true);
}
check.update(12000,{seq:61,time_ms:12100,load_raw:179200},true);
assert.equal(check.result.status,'RESPONSE / RETURNED');
check.start(0,{seq:1,time_ms:100});
check.update(100,{seq:2,time_ms:200,load_raw:0},false);
assert.equal(check.result.status,'CHECK INTERRUPTED');
check.start(0,{seq:100,time_ms:20000});
check.update(200,{seq:101,time_ms:100,load_raw:179200},true);
assert.equal(check.result.status,'CHECK INTERRUPTED');
check.start(0,{seq:1,time_ms:100});
for(let i=0;i<20;i++)check.update(i*200,{seq:1,time_ms:100,load_raw:179200},true);
assert.equal(check.groups.flat().length,0);
check.reset();assert.equal(check.result,null);assert.equal(check.running,false);
console.log('Load-cell diagnostics: response, noise, stuck-zero, interruption and reset checks passed.');
