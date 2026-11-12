'use strict';
var assert=require('assert'),path=require('path');
var install=require(process.env.STORAGE_GUARD || path.join(__dirname,'../parts/storage-guard.js'));
var SaveStore=require(process.env.SAVE_STORE_FILE || path.join(__dirname,'../assets/tiktok-platform/SaveStore.js'));
function runtime(initial, opts){
 opts=opts||{};var data=Object.assign({},initial),writes=[],callbacks=[];
 var storage={getItem:function(k){
  if(!(k in data))return opts.absent===undefined?null:opts.absent;
  if(opts.poisonAll)return true;
  var v=data[k];return typeof v==='number'||v&&typeof v==='object'?true:v;
 },setItem:function(k,v){writes.push({key:k,value:v});data[k]=v;}};
 var api={getStorage:function(o){callbacks.push(o);if(opts.held)return;
  var error=opts.error || (!(o.key in data)?{errMsg:'getStorage:fail data not found'}:null), result={data:data[o.key]};
  if(opts.promise)return error?Promise.reject(error):Promise.resolve(result);
  if(error)o.fail(error);else o.success(result);
 }};
 if(!opts.noMetadata)api.getStorageInfoSync=function(){return {keys:Object.keys(data)};};
 var cc={sys:{localStorage:storage}};install(cc,api);
 return {cc:cc,api:api,data:data,writes:writes,callbacks:callbacks};
}
function recover(t,specs,ms){return new Promise(function(resolve){install.recoverTyped(t.cc,t.api,specs,function(error){resolve(error);},ms);});}
(async function(){var checks=[];
 for(var mode of [false,true]){
  var t=runtime({ratio:0.7,flag:false,options:{coins:45},label:'ok'},{promise:mode});
  assert(!await recover(t,[{key:'ratio',type:'number',min:0,max:1},{key:'flag',type:'boolean'},{key:'options',type:'json_object'},{key:'label',type:'string',maxLength:4}]));
  assert.deepStrictEqual(t.data,{ratio:'0.7',flag:'false',options:'{"coins":45}',label:'ok'});
  assert.equal(t.cc.sys.localStorage.getItem('flag'),'false');checks.push((mode?'promise':'callback')+'_schema_types_preserved');
 }
 for(var mode of [false,true]){
  var t=runtime({}, {noMetadata:true,promise:mode});
  assert.throws(function(){t.cc.sys.localStorage.getItem('wallet');},/unreadable/);
  assert(!await recover(t,[{key:'wallet',type:'integer',min:0}]));
  assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);assert.equal(t.writes.length,0);
  t.cc.sys.localStorage.setItem('wallet',0);assert.equal(t.data.wallet,'0');checks.push((mode?'promise':'callback')+'_explicit_notfound_without_metadata');
 }
 for(var error of [{errMsg:'getStorage:fail network error'},{errMsg:'getStorage:fail no permission'},{errMsg:'not found'},{errMsg:'request resource not found'}]){
  var t=runtime({}, {noMetadata:true,error:error});assert(await recover(t,[{key:'wallet',type:'integer'}]));
  assert.equal(t.writes.length,0);assert.throws(function(){t.cc.sys.localStorage.setItem('wallet',0);},/unreadable/);
 }
 checks.push('non_storage_or_network_errors_not_missing');
 var t=runtime({flag:true});assert(await recover(t,[{key:'flag',type:'integer'}]));assert.strictEqual(t.data.flag,true);assert.equal(t.writes.length,0);checks.push('boolean_never_guessed_numeric');
 var t=runtime({save:'{bad JSON'});assert(await recover(t,[{key:'save',type:'json_object'}]));assert.equal(t.data.save,'{bad JSON');assert.equal(t.writes.length,0);checks.push('invalid_json_preserved');
 var t=runtime({save:{coins:45}});assert(await recover(t,[{key:'save',type:'json_object',validate:function(v){return v.coins<10;}}]));assert.deepStrictEqual(t.data.save,{coins:45});assert.equal(t.writes.length,0);checks.push('project_schema_validation_no_write');
 // Cancellation invokes application code. A nested batch created there is newer than the cancelling batch.
 var t=runtime({wallet:45},{held:true}), outcomes=[];
 install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(error){outcomes.push(['A',!!error]);if(error)install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(e){outcomes.push(['C',!!e]);});});
 install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(e){outcomes.push(['B',!!e]);});
 assert.equal(t.callbacks.length,2);t.callbacks[1].success({data:45});t.cc.sys.localStorage.setItem('wallet',50);t.callbacks[0].success({data:45});
 assert.equal(t.data.wallet,'50');assert.deepStrictEqual(outcomes,[['A',true],['B',true],['C',false]]);checks.push('cancel_callback_reentrancy_latest_batch_owns_writes');
 // Confirmed absence after a prior failed read must unlock legitimate initialization.
 var t=runtime({wallet:45});assert.throws(function(){t.cc.sys.localStorage.getItem('wallet');},/unreadable/);delete t.data.wallet;
 assert(!await recover(t,[{key:'wallet',type:'integer'}]));t.cc.sys.localStorage.setItem('wallet',0);assert.equal(t.data.wallet,'0');checks.push('confirmed_absence_retry_unlocks');
 // Foreground time owns the deadline; background waiting neither erases data nor consumes the budget.
 var t=runtime({wallet:45},{held:true}),listeners={hide:[],show:[]};
 t.api.onHide=function(fn){listeners.hide.push(fn);};t.api.offHide=function(fn){listeners.hide=listeners.hide.filter(function(x){return x!==fn;});};
 t.api.onShow=function(fn){listeners.show.push(fn);};t.api.offShow=function(fn){listeners.show=listeners.show.filter(function(x){return x!==fn;});};
 var ended=false,pending=recover(t,[{key:'wallet',type:'integer'}],30).then(function(e){ended=true;return e;});
 listeners.hide[0]();await new Promise(function(resolve){setTimeout(resolve,60);});assert.equal(ended,false);
 listeners.show[0]();assert(await pending);assert.equal(t.data.wallet,45);assert.equal(listeners.hide.length,0);assert.equal(listeners.show.length,0);
 checks.push('background_does_not_consume_recovery_deadline_and_hooks_cleaned');
 // Genuine Web Storage exposes its own key index even without platform metadata.
 var t=runtime({}, {noMetadata:true});t.cc.sys.localStorage.key=function(i){return Object.keys(t.data)[i] || null;};Object.defineProperty(t.cc.sys.localStorage,'length',{get:function(){return Object.keys(t.data).length;}});
 assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);checks.push('web_storage_own_index_proves_new_key');
 // SaveStore must preserve an existing JSON object while its sync bridge lies, then load after typed normalization.
 var key='demo:123:save:v1',raw={coins:45,platformClaims:{shortcut:true,profile:false},meta:{}};
 var initial={};initial[key]=raw;var t=runtime(initial),before=JSON.stringify(t.data);
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 assert.equal(store.load().ok,false);assert.equal(store.update(function(d){d.coins=0;}).ok,false);assert.equal(JSON.stringify(t.data),before);assert.equal(t.writes.length,0);
 assert(!await recover(t,[{key:key,type:'json_object',validate:function(v){return Number.isSafeInteger(v.coins)&&v.coins>=0;}}]));
 assert.equal(store.load().ok,true);assert.equal(store.get().coins,45);assert.equal(store.isClaimed('shortcut'),true);checks.push('savestore_typed_json_normalization_then_load_retry');
 // 3.x installs against window/global localStorage before the cc namespace exists.
 var t=runtime({enabled:true});var descriptor=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:t.cc.sys.localStorage,writable:true});
 try {assert(!await new Promise(function(resolve){install.recoverTyped(null,t.api,[{key:'enabled',type:'boolean'}],resolve);}));assert.equal(t.data.enabled,'true');}
 finally {if(descriptor)Object.defineProperty(globalThis,'localStorage',descriptor);else delete globalThis.localStorage;}
 checks.push('cocos3_global_storage_without_cc_namespace');
 // Missing metadata plus explicit async not-found can initialize SaveStore without guessing empty data.
 var t=runtime({}, {noMetadata:true}),key='demo:123:save:v1';
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return null;},login:false});
 assert.equal(store.load().ok,false);assert.equal(t.writes.length,0);
 assert(!await recover(t,[{key:key,type:'json_object'}]));assert.equal(store.load().ok,true);assert.equal(store.get().coins,0);
 checks.push('savestore_explicit_notfound_then_fresh_load');
 // Persistent sync corruption is not disguised by a cached success or a guessed reset.
 var initial={};initial[key]=JSON.stringify(raw);var t=runtime(initial,{poisonAll:true}),before=t.data[key];
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 assert.equal(store.load().ok,false);assert(await recover(t,[{key:key,type:'json_object'}]));assert.equal(t.data[key],before);assert.equal(store.load().ok,false);assert.equal(store.update(function(d){d.coins=0;}).ok,false);checks.push('persistently_unreadable_json_not_faked_success');
 // A stale index cannot justify replacing an unambiguously readable existing save.
 var initial={};initial[key]=JSON.stringify(raw);var t=runtime(initial);
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return [];},login:false});
 assert.equal(store.load().ok,true);assert.equal(store.get().coins,45);assert.equal(t.writes.length,0);checks.push('stale_index_cannot_reset_valid_existing_json');
 var t=runtime({}, {noMetadata:true});assert(!await recover(t,[{key:'label',type:'string'}]));
 t.data.label='later SDK text';assert.equal(t.cc.sys.localStorage.getItem('label'),'later SDK text');
 checks.push('confirmed_absence_does_not_mask_later_readable_sdk_write');
 console.log(JSON.stringify({suite:'storage-typed-recovery',passed:checks.length,checks:checks},null,2));
})().catch(function(e){console.error(e);process.exitCode=1;});
