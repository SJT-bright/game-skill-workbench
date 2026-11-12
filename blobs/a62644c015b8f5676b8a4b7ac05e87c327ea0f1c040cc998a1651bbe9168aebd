'use strict';
var fs=require('fs'),os=require('os'),path=require('path'),child=require('child_process');
var kit=path.join(__dirname,'..'),guard=fs.readFileSync(path.join(kit,'parts/storage-guard.js'),'utf8'),save=fs.readFileSync(path.join(kit,'assets/tiktok-platform/SaveStore.js'),'utf8');
var variants=[
 {name:'cancel_callback_ownership_regressed',file:'guard',before:'state.cancelRecovery = cancel;\n  if (previous) previous();\n  if (!current()) { cancel(); return; }',after:'if (previous) previous();\n  state.cancelRecovery = cancel; state.generation = token;'},
 {name:'unavailable_save_reset_to_defaults',file:'save',before:"this.data = clone(this.defaults); this.status = 'unavailable'; return this._result(false,error);",after:"this.data = clone(this.defaults); this.status = 'recovered'; this._write(this.data); return this._result(true);"},
 {name:'boolean_guessed_as_number',file:'guard',before:"if (typeof value !== 'number' && typeof value !== 'string') return null;",after:"if (typeof value !== 'number' && typeof value !== 'string' && typeof value !== 'boolean') return null;"},
 {name:'generic_failure_treated_as_missing_key',file:'guard',before:"if (!error || typeof error !== 'object') return false;",after:"return true;\n  if (!error || typeof error !== 'object') return false;"}
];
var results=variants.map(function(v){var dir=fs.mkdtempSync(path.join(os.tmpdir(),'typed-storage-negative-')),text=v.file==='guard'?guard:save,applied=text.indexOf(v.before)>=0;try{
 fs.writeFileSync(path.join(dir,'storage-guard.js'),v.file==='guard'?text.replace(v.before,v.after):guard);
 fs.writeFileSync(path.join(dir,'SaveStore.js'),v.file==='save'?text.replace(v.before,v.after):save);
 fs.copyFileSync(path.join(kit,'assets/tiktok-platform/PlatformConfig.js'),path.join(dir,'PlatformConfig.js'));
 var run=child.spawnSync(process.execPath,[path.join(__dirname,'storage-typed-recovery.test.js')],{encoding:'utf8',timeout:10000,env:Object.assign({},process.env,{STORAGE_GUARD:path.join(dir,'storage-guard.js'),SAVE_STORE_FILE:path.join(dir,'SaveStore.js')})});
 return {name:v.name,mutation_applied:applied,test_failed_as_expected:applied&&run.status!==0,observed_error:String(run.stderr).slice(0,600)};
 }finally{fs.rmSync(dir,{recursive:true,force:true});}});
console.log(JSON.stringify(results,null,2));if(results.some(function(r){return !r.test_failed_as_expected;}))process.exitCode=1;
