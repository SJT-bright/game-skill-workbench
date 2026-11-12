'use strict';
// recoverTyped / recoverNumeric of parts/storage-guard.js. The sync read turns numbers into Booleans; the async read
// returns the real value, a Boolean again ('corrupt'), fails, or never answers ('hang').
// 2026-11-12: when no real value can be had the key reads as "no value" and done() carries no error, so the game starts.
var assert=require('assert'),path=require('path');
var install=require(process.env.STORAGE_GUARD || path.join(__dirname,'../parts/storage-guard.js'));
var warn=console.warn; console.warn=function(){};
function runtime(initial,mode){
 var data=Object.assign({},initial),writes=0,completion;
 var storage={getItem:function(k){return k in data?(typeof data[k]==='number'?data[k]!==0:data[k]):false;},setItem:function(k,v){writes++;data[k]=v;}};
 var api={getStorageInfoSync:function(){return {keys:Object.keys(data)};},getStorage:function(o){
  var r={data:mode==='corrupt'?true:data[o.key]};
  if(mode==='hang'){completion=function(){o.success(r);};return;}
  if(mode==='fail'){o.fail({errMsg:'failed'});return;}
  if(mode==='promise')return Promise.resolve(r);
  o.success(r);if(mode==='mixed')return Promise.resolve(r);
 }};
 var cc={sys:{localStorage:storage}};install(cc,api);
 return {cc:cc,api:api,data:data,writes:function(){return writes;},late:function(){if(completion)completion();}};
}
function run(entry,t,specs,ms){return new Promise(function(resolve){install[entry](t.cc,t.api,specs,function(error,results){resolve({error:error,results:results});},ms);});}
function recover(t,specs,ms){return run('recoverNumeric',t,specs,ms);}
(async function(){var checks=[],t,r;
 for(var mode of ['callback','promise','mixed']){
  t=runtime({balance:45,progress:0},mode);
  assert.strictEqual(t.cc.sys.localStorage.getItem('balance'),null,'a Boolean sync read is no value, not a throw');
  r=await recover(t,[{key:'balance',min:0},{key:'progress',min:0}]);
  assert(!r.error);assert.deepStrictEqual(r.results,{balance:'value_recovered',progress:'value_recovered'});
  assert.deepStrictEqual(t.data,{balance:'45',progress:'0'});assert.equal(t.writes(),2);
  assert.strictEqual(t.cc.sys.localStorage.getItem('balance'),'45');checks.push(mode+'_45_and_zero_recovered_as_text');
 }
 var expected={corrupt:'schema_reject_no_value',fail:'async_failed_no_value',hang:'timeout_no_value'};
 for(var mode of ['corrupt','fail','hang']){
  t=runtime({balance:45},mode);var before=JSON.stringify(t.data);
  r=await recover(t,[{key:'balance',min:0}],20);t.late();
  assert(!r.error,'no error: saved data never stops the game');assert.deepStrictEqual(r.results,{balance:expected[mode]});
  assert.equal(JSON.stringify(t.data),before,'the recovery itself resets nothing');assert.equal(t.writes(),0);
  assert.strictEqual(t.cc.sys.localStorage.getItem('balance'),null,'the game sees no value and uses its default');
  t.cc.sys.localStorage.setItem('balance',3);assert.equal(t.data.balance,'3','and can save again');
  checks.push(mode+'_no_value_game_goes_on_late_ignored');
 }
 t=runtime({balance:-5});r=await recover(t,[{key:'balance',min:0}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{balance:'schema_reject_no_value'});assert.equal(t.data.balance,-5);assert.equal(t.writes(),0);checks.push('schema_reject_no_reset_no_error');
 t=runtime({});r=await recover(t,[{key:'balance',min:0}]);assert(!r.error);assert.deepStrictEqual(r.results,{balance:'absent'});
 t.cc.sys.localStorage.setItem('balance',0);assert.equal(t.data.balance,'0');checks.push('confirmed_fresh_initializes');
 // 0/1 flags that are Booleans on both read paths: only a spec that asks for it gets 0 / 1.
 t=runtime({guide:1,blade:0,coins:45},'corrupt');
 r=await recover(t,[{key:'guide',min:0,max:1,acceptBoolean:true},{key:'blade',min:0,acceptBoolean:true},{key:'coins',min:0}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{guide:'boolean_as_number',blade:'boolean_as_number',coins:'schema_reject_no_value'});
 assert.deepStrictEqual(t.data,{guide:'1',blade:'0',coins:45},'a balance is never guessed from a Boolean');checks.push('accept_boolean_only_when_asked');
 // A real Boolean switch keeps its value even when the async read fails.
 t=runtime({music:false,sound:true},'fail');
 r=await run('recoverTyped',t,[{key:'music',type:'boolean'},{key:'sound',type:'boolean'}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{music:'boolean_kept',sound:'boolean_kept'});
 assert.deepStrictEqual(t.data,{music:'false',sound:'true'});assert.strictEqual(t.cc.sys.localStorage.getItem('music'),'false');checks.push('boolean_switch_kept');
 // A write that cannot be read back leaves the key readable on the next try.
 t=runtime({balance:45});var state=t.cc.sys.localStorage.getItem.__tiktokKitStorageState,read=state.read,once=true;
 state.read=function(k){if(typeof t.data[k]==='string'&&once){once=false;throw Error('transient');}return read(k);};
 r=await recover(t,[{key:'balance'}]);assert(!r.error);assert.deepStrictEqual(r.results,{balance:'write_unconfirmed'});
 r=await recover(t,[{key:'balance'}]);assert(!r.error);assert.deepStrictEqual(r.results,{balance:'kept'});
 t.cc.sys.localStorage.setItem('balance',46);assert.equal(t.data.balance,'46');checks.push('retry_after_readback_failure');
 // Time is up while the first key waits: that key and the keys after it are settled from the sync read alone.
 t=runtime({balance:45,label:'ok',music:true,level:7},'hang');t.data.level='7';
 r=await run('recoverTyped',t,[{key:'balance',type:'integer'},{key:'label',type:'string'},{key:'music',type:'boolean'},{key:'level',type:'integer'},{key:'gone',type:'integer'}],20);
 assert(!r.error);assert.deepStrictEqual(r.results,{balance:'timeout_no_value',label:'kept',music:'boolean_kept',level:'kept',gone:'absent'});
 assert.deepStrictEqual(t.data,{balance:45,label:'ok',music:'true',level:'7'});checks.push('timeout_settles_the_rest_from_sync_reads');
 // A readable value outside the schema is left for the game to read as before.
 t=runtime({name:'a much too long text'});r=await run('recoverTyped',t,[{key:'name',type:'string',maxLength:4}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{name:'schema_reject_left_as_is'});assert.strictEqual(t.cc.sys.localStorage.getItem('name'),'a much too long text');assert.equal(t.writes(),0);checks.push('readable_value_outside_schema_left_as_is');
 // A Boolean false for a key the platform does not list is a missing key on several devices: never stored as false.
 t=runtime({});delete t.api.getStorageInfoSync;t.api.getStorage=function(o){o.fail({errMsg:'getStorage:fail internal error'});};
 r=await run('recoverTyped',t,[{key:'music',type:'boolean'},{key:'guide',type:'integer',acceptBoolean:true}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{music:'async_failed_no_value',guide:'async_failed_no_value'});assert.equal(t.writes(),0);checks.push('unlisted_false_is_not_a_stored_boolean');
 // A superseded request must not overwrite a newer recovery or subsequent gameplay value.
 t=runtime({balance:45},'hang');var callbacks=[];
 t.api.getStorage=function(o){callbacks.push(o.success);};
 var old=recover(t,[{key:'balance'}]),latest=recover(t,[{key:'balance'}]);
 callbacks[1]({data:45});assert(!(await latest).error);assert((await old).error,'the superseded batch is told so');
 t.cc.sys.localStorage.setItem('balance',50);callbacks[0]({data:45});assert.equal(t.data.balance,'50');
 checks.push('superseded_recovery_cannot_write_old_balance');
 // The game saved the key while the async read was out: the newer value stays.
 t=runtime({balance:45},'hang');callbacks=[];t.api.getStorage=function(o){callbacks.push(o.success);};
 var pending=recover(t,[{key:'balance'}]);t.cc.sys.localStorage.setItem('balance',60);callbacks[0]({data:45});
 r=await pending;assert(!r.error);assert.deepStrictEqual(r.results,{balance:'newer_write_kept'});assert.equal(t.data.balance,'60');checks.push('newer_game_write_kept');
 // No platform SDK (browser preview) or no guard: nothing to recover, the callback still comes, without an error.
 t=runtime({balance:45});r=await new Promise(function(resolve){install.recoverTyped(t.cc,null,[{key:'balance',type:'integer'}],function(e,x){resolve({error:e,results:x});});});
 assert(!r.error);assert.deepStrictEqual(r.results,{balance:'not_checked_no_sdk'});checks.push('no_sdk_does_not_throw');
 assert.throws(function(){install.recoverTyped(t.cc,t.api,null,function(){});},/schema list and callback/);
 r=await run('recoverTyped',t,[{key:'balance',type:'money'}]);assert(r.error&&/schema required/.test(r.error.message));checks.push('wrong_schema_is_an_error');
 console.warn=warn;
 console.log(JSON.stringify({suite:'storage-recovery',passed:checks.length,checks:checks}));
})().catch(function(e){console.warn=warn;console.error(e);process.exitCode=1;});
