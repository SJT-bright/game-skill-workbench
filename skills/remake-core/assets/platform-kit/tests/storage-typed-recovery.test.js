'use strict';
// Typed recovery (parts/storage-guard.js recoverTyped) together with SaveStore, on a bridge whose sync read turns
// numbers and objects into `true`. 2026-11-12: nothing here may stop the game: a key without a usable real value
// reads as "no value", done() carries no error, and SaveStore can always save again.
var assert=require('assert'),path=require('path');
var install=require(process.env.STORAGE_GUARD || path.join(__dirname,'../parts/storage-guard.js'));
var SaveStore=require(process.env.SAVE_STORE_FILE || path.join(__dirname,'../assets/tiktok-platform/SaveStore.js'));
var warn=console.warn; console.warn=function(){};
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
function recover(t,specs,ms){return new Promise(function(resolve){install.recoverTyped(t.cc,t.api,specs,function(error,results){resolve({error:error,results:results});},ms);});}
(async function(){var checks=[],r;
 for(var mode of [false,true]){
  var t=runtime({ratio:0.7,flag:false,options:{coins:45},label:'ok'},{promise:mode});
  r=await recover(t,[{key:'ratio',type:'number',min:0,max:1},{key:'flag',type:'boolean'},{key:'options',type:'json_object'},{key:'label',type:'string',maxLength:4}]);
  assert(!r.error);assert.deepStrictEqual(r.results,{ratio:'value_recovered',flag:'value_recovered',options:'value_recovered',label:'kept'});
  assert.deepStrictEqual(t.data,{ratio:'0.7',flag:'false',options:'{"coins":45}',label:'ok'});
  assert.equal(t.cc.sys.localStorage.getItem('flag'),'false');checks.push((mode?'promise':'callback')+'_schema_types_preserved');
 }
 for(var mode of [false,true]){
  var t=runtime({}, {noMetadata:true,promise:mode});
  assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null,'no key list: a new player still starts');
  r=await recover(t,[{key:'wallet',type:'integer',min:0}]);assert(!r.error);assert.deepStrictEqual(r.results,{wallet:'absent'});
  assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);assert.equal(t.writes.length,0);
  t.cc.sys.localStorage.setItem('wallet',0);assert.equal(t.data.wallet,'0');checks.push((mode?'promise':'callback')+'_explicit_notfound_without_metadata');
 }
 // Any other failure is not proof of a missing key (the label says so), and it does not stop the game either.
 for(var error of [{errMsg:'getStorage:fail network error'},{errMsg:'getStorage:fail no permission'},{errMsg:'not found'},{errMsg:'request resource not found'}]){
  var t=runtime({}, {noMetadata:true,error:error});r=await recover(t,[{key:'wallet',type:'integer'}]);
  assert(!r.error,'no error for '+error.errMsg);assert.deepStrictEqual(r.results,{wallet:'async_failed_no_value'});
  assert.equal(t.writes.length,0);assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);
  t.cc.sys.localStorage.setItem('wallet',0);assert.equal(t.data.wallet,'0','the game can save');
 }
 checks.push('other_failures_are_not_absence_and_do_not_stop_the_game');
 var t=runtime({flag:true});r=await recover(t,[{key:'flag',type:'integer'}]);assert(!r.error);assert.deepStrictEqual(r.results,{flag:'schema_reject_no_value'});
 assert.strictEqual(t.data.flag,true);assert.equal(t.writes.length,0);assert.strictEqual(t.cc.sys.localStorage.getItem('flag'),null);checks.push('boolean_never_guessed_numeric');
 var t=runtime({}, {noMetadata:true,absent:false,error:{errMsg:'getStorage:fail internal error'}});
 r=await recover(t,[{key:'music',type:'boolean'},{key:'guide',type:'integer',acceptBoolean:true}]);
 assert(!r.error);assert.deepStrictEqual(r.results,{music:'async_failed_no_value',guide:'async_failed_no_value'});assert.equal(t.writes.length,0);checks.push('unlisted_false_is_a_missing_key_not_a_stored_boolean');
 var t=runtime({save:'{bad JSON'});r=await recover(t,[{key:'save',type:'json_object'}]);assert(!r.error);assert.deepStrictEqual(r.results,{save:'schema_reject_left_as_is'});
 assert.equal(t.data.save,'{bad JSON');assert.equal(t.writes.length,0);assert.equal(t.cc.sys.localStorage.getItem('save'),'{bad JSON');checks.push('invalid_json_left_for_the_game_to_read');
 var t=runtime({save:{coins:45}});r=await recover(t,[{key:'save',type:'json_object',validate:function(v){return v.coins<10;}}]);assert(!r.error);assert.deepStrictEqual(r.results,{save:'schema_reject_no_value'});
 assert.deepStrictEqual(t.data.save,{coins:45});assert.equal(t.writes.length,0);checks.push('project_schema_validation_no_write');
 // Cancellation invokes application code. A nested batch created there is newer than the cancelling batch.
 var t=runtime({wallet:45},{held:true}), outcomes=[];
 install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(error){outcomes.push(['A',!!error&&error.code]);if(error)install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(e){outcomes.push(['C',!!e]);});});
 install.recoverTyped(t.cc,t.api,[{key:'wallet',type:'integer'}],function(e){outcomes.push(['B',!!e&&e.code]);});
 assert.equal(t.callbacks.length,2);t.callbacks[1].success({data:45});t.cc.sys.localStorage.setItem('wallet',50);t.callbacks[0].success({data:45});
 assert.equal(t.data.wallet,'50');assert.deepStrictEqual(outcomes,[['A','TIKTOK_STORAGE_SUPERSEDED'],['B','TIKTOK_STORAGE_SUPERSEDED'],['C',false]]);checks.push('cancel_callback_reentrancy_latest_batch_owns_writes');
 // A key that read as no value, then turns out to be missing: the game initializes it.
 var t=runtime({wallet:45});assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);delete t.data.wallet;
 r=await recover(t,[{key:'wallet',type:'integer'}]);assert(!r.error);assert.deepStrictEqual(r.results,{wallet:'absent'});
 t.cc.sys.localStorage.setItem('wallet',0);assert.equal(t.data.wallet,'0');checks.push('confirmed_absence_then_initialize');
 // Foreground time owns the deadline; background waiting neither erases data nor consumes the budget.
 var t=runtime({wallet:45},{held:true}),listeners={hide:[],show:[]};
 t.api.onHide=function(fn){listeners.hide.push(fn);};t.api.offHide=function(fn){listeners.hide=listeners.hide.filter(function(x){return x!==fn;});};
 t.api.onShow=function(fn){listeners.show.push(fn);};t.api.offShow=function(fn){listeners.show=listeners.show.filter(function(x){return x!==fn;});};
 var ended=false,pending=recover(t,[{key:'wallet',type:'integer'}],30).then(function(e){ended=true;return e;});
 listeners.hide[0]();await new Promise(function(resolve){setTimeout(resolve,60);});assert.equal(ended,false);
 listeners.show[0]();r=await pending;assert(!r.error,'time up is not an error');assert.deepStrictEqual(r.results,{wallet:'timeout_no_value'});
 assert.equal(t.data.wallet,45);assert.equal(listeners.hide.length,0);assert.equal(listeners.show.length,0);
 checks.push('background_does_not_consume_recovery_deadline_and_hooks_cleaned');
 // Genuine Web Storage exposes its own key index even without platform metadata.
 var t=runtime({}, {noMetadata:true});t.cc.sys.localStorage.key=function(i){return Object.keys(t.data)[i] || null;};Object.defineProperty(t.cc.sys.localStorage,'length',{get:function(){return Object.keys(t.data).length;}});
 assert.strictEqual(t.cc.sys.localStorage.getItem('wallet'),null);checks.push('web_storage_own_index_proves_new_key');
 // SaveStore: typed recovery BEFORE the first load keeps a save the sync bridge cannot hand back.
 var key='demo:123:save:v1',raw={coins:45,platformClaims:{shortcut:true,profile:false},meta:{}};
 var initial={};initial[key]=raw;var t=runtime(initial);
 r=await recover(t,[{key:key,type:'json_object',validate:function(v){return Number.isSafeInteger(v.coins)&&v.coins>=0;}}]);assert(!r.error);
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 var loaded=store.load();assert.equal(loaded.ok,true);assert.equal(loaded.status,'loaded');assert.equal(store.get().coins,45);assert.equal(store.isClaimed('shortcut'),true);checks.push('savestore_typed_json_normalization_before_load');
 // SaveStore without typed recovery: the unreadable save is backed up, the game starts from defaults and CAN SAVE.
 var initial={};initial[key]=raw;var t=runtime(initial);
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 var first=store.load();assert.equal(first.ok,true);assert.equal(first.status,'recovered');assert.equal(t.data[key+':corrupt-backup'],'true');
 assert.equal(store.isClaimed('shortcut'),true,'one-time rewards are not paid twice');
 assert.equal(store.update(function(d){d.coins+=7;}).ok,true);assert.equal(store.get().coins,7);
 var again=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 assert.equal(again.load().status,'loaded');assert.equal(again.get().coins,7);checks.push('savestore_unreadable_existing_save_is_backed_up_and_saves_again');
 // 3.x installs against window/global localStorage before the cc namespace exists.
 var t=runtime({enabled:true});var descriptor=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:t.cc.sys.localStorage,writable:true});
 try {assert(!await new Promise(function(resolve){install.recoverTyped(null,t.api,[{key:'enabled',type:'boolean'}],resolve);}));assert.equal(t.data.enabled,'true');}
 finally {if(descriptor)Object.defineProperty(globalThis,'localStorage',descriptor);else delete globalThis.localStorage;}
 checks.push('cocos3_global_storage_without_cc_namespace');
 // No key list and no save: SaveStore starts a new save and the first update writes it.
 var t=runtime({}, {noMetadata:true}),key='demo:123:save:v1';
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return null;},login:false});
 var fresh=store.load();assert.equal(fresh.ok,true);assert.equal(fresh.status,'new');assert.equal(t.writes.length,0);
 assert.equal(store.update(function(d){d.coins+=7;}).ok,true);assert.equal(JSON.parse(t.data[key]).coins,7);
 checks.push('savestore_new_player_without_key_list_can_save');
 // A storage whose every sync read lies is reported as a failed save, never as a success.
 var initial={};initial[key]=JSON.stringify(raw);var t=runtime(initial,{poisonAll:true});
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return Object.keys(t.data);},login:false});
 assert.equal(store.load().ok,false);r=await recover(t,[{key:key,type:'json_object'}]);assert(!r.error);
 assert.equal(store.update(function(d){d.coins=1;}).ok,false);assert.equal(store.get().coins,0);checks.push('persistently_lying_reads_never_reported_as_saved');
 // A stale index cannot justify replacing an unambiguously readable existing save.
 var initial={};initial[key]=JSON.stringify(raw);var t=runtime(initial);
 var store=new SaveStore({coins:0},{storage:t.cc.sys.localStorage,key:key,storageKeys:function(){return [];},login:false});
 assert.equal(store.load().ok,true);assert.equal(store.get().coins,45);assert.equal(t.writes.length,0);checks.push('stale_index_cannot_reset_valid_existing_json');
 var t=runtime({}, {noMetadata:true});r=await recover(t,[{key:'label',type:'string'}]);assert(!r.error);
 t.data.label='later SDK text';assert.equal(t.cc.sys.localStorage.getItem('label'),'later SDK text');
 checks.push('confirmed_absence_does_not_mask_later_readable_sdk_write');
 console.warn=warn;
 console.log(JSON.stringify({suite:'storage-typed-recovery',passed:checks.length,checks:checks},null,2));
})().catch(function(e){console.warn=warn;console.error(e);process.exitCode=1;});
