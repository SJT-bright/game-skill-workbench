'use strict';
// Each variant breaks one rule in a temporary copy of the guard or of SaveStore; storage-typed-recovery.test.js MUST fail.
var fs=require('fs'),os=require('os'),path=require('path'),child=require('child_process');
var kit=path.join(__dirname,'..'),guard=fs.readFileSync(path.join(kit,'parts/storage-guard.js'),'utf8'),save=fs.readFileSync(path.join(kit,'assets/tiktok-platform/SaveStore.js'),'utf8');
var variants=[
 {name:'cancel_callback_ownership_regressed',file:'guard',before:'state.cancelRecovery = cancel;\n  if (previous) previous();\n  if (!current()) { cancel(); return; }',after:'if (previous) previous();\n  state.cancelRecovery = cancel; state.generation = token;'},
 {name:'boolean_guessed_as_number',file:'guard',before:"if (typeof value !== 'number' && typeof value !== 'string') return null;",after:"if (typeof value !== 'number' && typeof value !== 'string' && typeof value !== 'boolean') return null;"},
 {name:'generic_failure_treated_as_missing_key',file:'guard',before:"if (!error || typeof error !== 'object') return false;",after:"return true;\n  if (!error || typeof error !== 'object') return false;"},
 // the 2026-11-11 behaviour: no usable real value ended the startup with an error
 {name:'no_real_value_ends_with_an_error',file:'guard',before:"state.knownAbsent[key] = true; settle(why + '_no_value');",after:"return finish(Error('Typed storage value unreadable; save preserved: ' + key));"},
 {name:'time_up_ends_with_an_error',file:'guard',before:"if (!hidden && remaining <= 0) { outOfTime = true; if (waiting) waiting(); return; }",after:"if (!hidden && remaining <= 0) return finish(Error('Typed storage recovery timed out; save preserved'));"},
 {name:'unlisted_false_stored_as_a_boolean',file:'guard',before:"if (typeof value === 'boolean' && (value === true || present === true)) {",after:"if (typeof value === 'boolean') {"},
 // the 2026-11-11 SaveStore: an unreadable save could never be saved over
 {name:'unreadable_save_refuses_every_update',file:'save',before:"  if (!this.storage) return this._result(false, 'storage_unavailable');\n  var draft = clone(this.data);",after:"  if (!this.storage || this.status === 'recovered') return this._result(false, 'storage_unavailable');\n  var draft = clone(this.data);"},
 {name:'new_save_without_key_list_refused',file:'save',before:"  if (raw === null || raw === '') {\n    this.data = clone(this.defaults); this.status = 'new'; return this._result(true);",after:"  if (raw === null || raw === '') {\n    this.data = clone(this.defaults); this.status = 'unavailable'; this.storage = null; return this._result(false, 'saved_data_unreadable');"},
 {name:'unreadable_save_not_backed_up',file:'save',before:"this.storage.setItem(this.key + ':corrupt-backup', typeof raw === 'string' ? raw : String(raw));",after:''}
];
var results=variants.map(function(v){var dir=fs.mkdtempSync(path.join(os.tmpdir(),'typed-storage-negative-')),text=v.file==='guard'?guard:save,applied=text.indexOf(v.before)>=0;try{
 fs.writeFileSync(path.join(dir,'storage-guard.js'),v.file==='guard'?text.replace(v.before,v.after):guard);
 fs.writeFileSync(path.join(dir,'SaveStore.js'),v.file==='save'?text.replace(v.before,v.after):save);
 fs.copyFileSync(path.join(kit,'assets/tiktok-platform/PlatformConfig.js'),path.join(dir,'PlatformConfig.js'));
 var run=child.spawnSync(process.execPath,[path.join(__dirname,'storage-typed-recovery.test.js')],{encoding:'utf8',timeout:10000,env:Object.assign({},process.env,{STORAGE_GUARD:path.join(dir,'storage-guard.js'),SAVE_STORE_FILE:path.join(dir,'SaveStore.js')})});
 return {name:v.name,mutation_applied:applied,test_failed_as_expected:applied&&run.status!==0,observed_error:String(run.stderr).slice(0,600)};
 }finally{fs.rmSync(dir,{recursive:true,force:true});}});
console.log(JSON.stringify(results,null,2));if(results.some(function(r){return !r.test_failed_as_expected;}))process.exitCode=1;
