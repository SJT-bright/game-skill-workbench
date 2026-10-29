'use strict';
// Mutate in-memory only: the production candidates on disk are never patched.
var child = require('child_process');
var path = require('path');
var variants = [
  {name:'missing_mission_promise_success',file:'TikTokMissionService.js',
    before:'returned.then(success, fail)',after:'returned.then(function () {}, fail)'},
  {name:'missing_independent_mission_deadline',file:'TikTokMissionService.js',
    before:"else if (self.now() >= r.deadline) r.settle('timeout');",after:'else if (false) r.settle(\'timeout\');'},
  {name:'resume_does_not_invalidate_old_query',file:'TikTokMissionService.js',
    before:'TikTokMissionService.prototype.onResume = function () { this.cancel(); };',
    after:'TikTokMissionService.prototype.onResume = function () {};'},
  {name:'undefined_ad_close_grants_reward',file:'RewardedService.js',
    before:"res && res.isEnded === true ? 'completed' : 'cancelled'",
    after:"!res || res.isEnded === true ? 'completed' : 'cancelled'"}
];
var results=variants.map(function(v){
  var target=path.join(__dirname,v.file), test=path.join(__dirname,'platform-components.test.js');
  var script="var fs=require('fs'),Module=require('module');var old=Module._extensions['.js'];"+
    "Module._extensions['.js']=function(m,f){if(f==="+JSON.stringify(target)+") {var s=fs.readFileSync(f,'utf8');"+
    "if(s.indexOf("+JSON.stringify(v.before)+")<0)throw Error('mutation_not_applied');"+
    "return m._compile(s.replace("+JSON.stringify(v.before)+","+JSON.stringify(v.after)+"),f);}return old(m,f);};require("+JSON.stringify(test)+");";
  var r=child.spawnSync(process.execPath,['-e',script],{encoding:'utf8',timeout:5000});
  var failed=r.status!==0 && !String(r.stderr).includes('mutation_not_applied');
  return {name:v.name,expected_failure_observed:failed,exit_code:r.status,
    diagnostic:String(r.stderr).split('\n').slice(0,4).join('\n')};
});
console.log(JSON.stringify({schema:'snakevsblock.platform_component_negative_controls.v1',
  scope:'Same Node SDK-substitute check as current candidate; source mutated in memory only',results:results},null,2));
if(results.some(function(r){return !r.expected_failure_observed;}))process.exitCode=1;
