'use strict';
// Executes the storage sections and exported JSAPI methods from both actual host source files.
// This is a host-semantics test, not a rendered game or physical-phone test.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const root = process.env.HOST_SCRIPTS || path.resolve(__dirname, '../..');
function section(s, a, b) { const i=s.indexOf(a), j=s.indexOf(b,i+a.length); assert(i>=0&&j>i, a); return s.slice(i,j); }
function localStore() {
 const value={}; Object.defineProperties(value,{
  length:{get(){return Object.keys(value).length;}},
  key:{value:i=>Object.keys(value)[i]},
  getItem:{value:k=>Object.hasOwn(value,k)?value[k]:null},
  setItem:{value:(k,v)=>{value[k]=String(v);}},
  removeItem:{value:k=>{delete value[k];}}
 }); return value;
}
function host(kind, query, kept) {
 const file=path.join(root, kind===2?'ad_regression/host.js':'runtime_regression/host3x/host.js');
 const text=fs.readFileSync(file,'utf8'), timers=[], logs=[], localStorage=kept||localStore();
 const context={window:{localStorage},localStorage, URLSearchParams,Q:new URLSearchParams(query),F:new Set(), STORE:'RR3:default:',X:{},growthLaunchScene:null,
  log:(...x)=>logs.push(x),hit:(...x)=>logs.push(x),setTimeout:f=>timers.push(f), cb:(o,ok,r)=>{if(ok)o.success&&o.success(r);else o.fail&&o.fail(r);o.complete&&o.complete(r);}};
 vm.createContext(context);
 const body=section(text,'// ---------- storage ----------',kind===2?'// ---------- rewarded ads':'// ---------- touch ----------');
 const api=section(text,kind===2?'getStorageSync: function (k)':'getStorageSync: k => storage.get(k)',kind===2?'onTouchStart: H_.touchstart.on':'onTouchStart: f => touchCbs.Start.push(f)');
 vm.runInContext(body+'\nvar tt={'+api+'};window.__testApi=tt;',context,{filename:file});
 const tt=context.window.__testApi;
 return {tt,localStorage,logs,read(k){let r,failed; const returned=tt.getStorage({key:k,success:v=>{r=v.data;},fail:e=>{failed=e;}});while(timers.length)timers.shift()();if(failed)throw Error(failed.errMsg);assert.equal(returned,undefined,'host remains callback API');return r;}};
}
const cases=[];
function test(name,f){f();cases.push(name);}
for(const k of [2,3]) {
 const seed=encodeURIComponent(JSON.stringify({wallet:45,zero:0,text:'45',truth:true}));
 test('host'+k+' seed before game and typed async independent of sync distortion',()=>{
  const h=host(k,'reset=1&missing=false&syncnumbool=all&async_storage=typed&storage_seed='+seed);
  assert.equal(h.tt.getStorageSync('wallet'),true);assert.equal(h.tt.getStorageSync('zero'),false);
  assert.equal(h.read('wallet'),45);assert.equal(h.read('zero'),0);assert.equal(h.read('truth'),true);
  assert.equal(h.tt.getStorageSync('text'),'45');assert.equal(h.read('text'),'45');
  assert(h.tt.getStorageInfoSync().keys.includes('wallet'));
  h.tt.setStorageSync('wallet','45');
  const restart=host(k,'missing=false&syncnumbool=all&async_storage=typed',h.localStorage);
  assert.equal(restart.tt.getStorageSync('wallet'),'45');assert.equal(restart.read('zero'),0);
 });
 test('host'+k+' original defaults and old numbool diagnostic stay unchanged',()=>{
  const normal=host(k,'storage_seed='+seed);assert.equal(normal.tt.getStorageSync('wallet'),45);assert.equal(normal.read('wallet'),45);
  const all=host(k,'numbool=all&storage_seed='+seed);assert.equal(all.tt.getStorageSync('wallet'),true);assert.equal(all.read('wallet'),true);
  const zeroOne=host(k,'numbool=01&storage_seed='+seed);assert.equal(zeroOne.tt.getStorageSync('wallet'),45);assert.equal(zeroOne.read('zero'),false);
 });
 for(const [m,value] of [['false',false],['true',true],['null',null],['undefined',undefined]]) test('host'+k+' missing '+m+' unaffected',()=>{
  const h=host(k,'async_storage=typed&missing='+m);assert.equal(h.tt.getStorageSync('absent'),value);assert.equal(h.read('absent'),value);
 });
 test('host'+k+' missing throw unaffected',()=>{
  const h=host(k,'async_storage=typed&missing=throw');assert.throws(()=>h.tt.getStorageSync('absent'),/data not found/);assert.throws(()=>h.read('absent'),/data not found/);
 });
 test('host'+k+' invalid fixture rejected',()=>assert.throws(()=>host(k,'storage_seed=%5B45%5D'),/must be a JSON object/));
}
console.log(JSON.stringify({suite:'storage_host_profiles',passed:true,cases,boundary:'actual host storage sections in VM; not game-renderer/device acceptance'},null,2));
