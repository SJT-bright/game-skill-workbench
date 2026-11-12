'use strict';
var assert=require('assert'),path=require('path');
var install=require(process.env.STORAGE_GUARD || path.join(__dirname,'../parts/storage-guard.js'));
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
async function recover(t,specs,ms){return await new Promise(function(resolve){install.recoverNumeric(t.cc,t.api,specs,function(error){resolve(error);},ms);});}
(async function(){var checks=[];
 for(var mode of ['callback','promise','mixed']){
  var t=runtime({balance:45,progress:0},mode);
  assert.throws(function(){t.cc.sys.localStorage.getItem('balance');},/unreadable/);
  assert(!await recover(t,[{key:'balance',min:0},{key:'progress',min:0}]));
  assert.deepStrictEqual(t.data,{balance:'45',progress:'0'});assert.equal(t.writes(),2);checks.push(mode+'_45_and_zero_preserved');
 }
 for(var mode of ['corrupt','fail','hang']){
  var t=runtime({balance:45},mode);var before=JSON.stringify(t.data);
  assert(await recover(t,[{key:'balance',min:0}],20));t.late();
  assert.equal(JSON.stringify(t.data),before);assert.equal(t.writes(),0);
  assert.throws(function(){t.cc.sys.localStorage.setItem('balance',0);},/unreadable/);checks.push(mode+'_preserved_and_late_ignored');
 }
 var t=runtime({balance:-5});assert(await recover(t,[{key:'balance',min:0}]));assert.equal(t.data.balance,-5);assert.equal(t.writes(),0);checks.push('schema_reject_no_reset');
 var t=runtime({});assert(!await recover(t,[{key:'balance',min:0}]));t.cc.sys.localStorage.setItem('balance',0);assert.equal(t.data.balance,'0');checks.push('confirmed_fresh_initializes');
 // A successful write followed by one transient read failure must unlock on Retry.
 var t=runtime({balance:45});var read=t.cc.sys.localStorage.getItem.__tiktokKitStorageState.read;
 var state=t.cc.sys.localStorage.getItem.__tiktokKitStorageState, once=true;
 state.read=function(k){if(typeof t.data[k]==='string'&&once){once=false;throw Error('transient');}return read(k);};
 assert(await recover(t,[{key:'balance'}]));assert(!await recover(t,[{key:'balance'}]));
 t.cc.sys.localStorage.setItem('balance',46);assert.equal(t.data.balance,'46');checks.push('retry_after_readback_failure_unlocks');
 // A superseded request must not overwrite a newer recovery or subsequent gameplay value.
 var t=runtime({balance:45},'hang');var callbacks=[];
 t.api.getStorage=function(o){callbacks.push(o.success);};
 var old=recover(t,[{key:'balance'}]);var latest=recover(t,[{key:'balance'}]);
 callbacks[1]({data:45});assert(!await latest);assert(await old);
 t.cc.sys.localStorage.setItem('balance',50);callbacks[0]({data:45});assert.equal(t.data.balance,'50');
 checks.push('superseded_recovery_cannot_write_old_balance');
 console.log(JSON.stringify({suite:'storage-recovery',passed:checks.length,checks:checks}));
})().catch(function(e){console.error(e);process.exitCode=1;});
