const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const NATIVE=path.resolve(process.argv[2]),WEB=path.resolve(process.argv[3]);
function loadLedger(bundle,missing,typed=false){
 const values=new Map;let getThrows=false,setThrows=false,writes=0;
 const tt={getStorageSync:k=>{if(getThrows)throw Error('storage unavailable');return values.has(k)?(typed?JSON.parse(values.get(k)):values.get(k)):missing;},setStorageSync:(k,v)=>{if(setThrows)throw Error('quota exceeded');writes++;values.set(k,v);},removeStorageSync:k=>values.delete(k)};
 // Execute the ACTUAL adapter storage module shipped in the old Native ZIP.
 const adapter=fs.readFileSync(path.join(NATIVE,'adapter-min.js'),'utf8');const start=adapter.indexOf('46:[function(e,t,n){')+'46:[function(e,t,n){'.length,end=adapter.indexOf('},{}],47:',start);
 const storageModule={exports:{}};vm.runInNewContext('(function(e,t,n){'+adapter.slice(start,end)+'})(null,module,module.exports)',{tt,module:storageModule});
 const logs=[],ctx={window:{},cc:{_RF:{push(){},pop(){}},sys:{localStorage:storageModule.exports}},console:{warn:(...a)=>logs.push(a)}};
 const source=fs.readFileSync(bundle,'utf8').replace(/,\["Enum","Index"[\s\S]*$/,',[]);');vm.runInNewContext(source,ctx);
 const Ledger=ctx.window.__screwRequire('GrowthLedger').default,ledger=new Ledger;
 return{ledger,values,key:Ledger.KEY,logs,fault(get,set){getThrows=get;setThrows=set;},writes:()=>writes};
}
const newBundle=path.join(NATIVE,'assets/main/index.js');
const checks=[];function test(name,fn){fn();checks.push(name);}
for(const [name,bundle] of [['Native',newBundle],['Web',process.argv[4]]]){
 for(const missing of [null,undefined,''])test(name+' fresh storage '+String(missing),()=>{const t=loadLedger(bundle,missing);assert.equal(t.ledger.snapshot().valid,true);assert.equal(t.ledger.balance('skill'),0);assert.equal(t.writes(),0);assert.equal(t.ledger.consume('skill'),false);});
 for(const typed of [false,true])test(name+' claim/consume/refund/restart typed='+typed,()=>{
  const t=loadLedger(bundle,'',typed),l=t.ledger;
  assert.equal(l.claim('shortcut').ok,true);assert.equal(l.claim('shortcut').reason,'already');assert.equal(l.balance('skill'),1);
  assert.equal(l.consume('skill'),true);assert.equal(l.confirm('skill'),true);assert.equal(l.balance('skill'),0);assert.equal(l.consume('skill'),false);
  assert.equal(l.consume('answer'),true);assert.equal(l.refund('answer'),true);assert.equal(l.balance('answer'),1);
  assert.equal(l.consume('answer'),true);l.owned=null;assert.equal(l.snapshot().valid,true);assert.equal(l.balance('answer'),1,'unapplied pending reservation recovers');
  const record=JSON.parse(t.values.get(t.key));record.v=1;delete record.pending;record.check=l.checksum(record);t.values.set(t.key,JSON.stringify(record));assert.equal(l.snapshot().valid,true,'valid v1 retained');
 });
 for(const raw of ['{','null','{}','0','false','{"v":2}','   '])test(name+' corrupt is preserved '+raw,()=>{const t=loadLedger(bundle,'');t.values.set(t.key,raw);assert.equal(t.ledger.snapshot().valid,false);assert.equal(t.values.get(t.key),raw);assert.equal(t.writes(),0);assert.ok(t.logs.length);});
 test(name+' read error and write failure retained, retry succeeds',()=>{const t=loadLedger(bundle,'');t.fault(true,false);assert.equal(t.ledger.snapshot().valid,false);t.fault(false,true);assert.equal(t.ledger.claim('shortcut').ok,false);t.fault(false,false);assert.equal(t.ledger.claim('shortcut').ok,true);assert.equal(t.ledger.balance('skill'),1);});
 test(name+' tampered checksum remains rejected without overwrite',()=>{const t=loadLedger(bundle,'');t.ledger.claim('shortcut');const r=JSON.parse(t.values.get(t.key));r.skillSpent=-1;const raw=JSON.stringify(r);t.values.set(t.key,raw);assert.equal(t.ledger.snapshot().valid,false);assert.equal(t.values.get(t.key),raw);});
}
console.log(JSON.stringify({tool:'probe_cocos2_reward_storage',passed:true,checks,boundary:'actual exported ledger and adapter in VM, controlled SDK storage; not real ads/device'}));
