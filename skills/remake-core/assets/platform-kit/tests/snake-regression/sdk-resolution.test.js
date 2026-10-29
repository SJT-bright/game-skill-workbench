'use strict';
var assert = require('assert');
var fs = require('fs');
var path = require('path');
var vm = require('vm');
var config = require('./PlatformConfig');
function load(file, namespaces, oldSelector) {
  var source=fs.readFileSync(path.join(__dirname,file),'utf8');
  if(oldSelector) source=source.replace(/function (rootSDK|sdk)\(method\) \{[\s\S]*?\n\}/,
    "function $1(method) { return typeof TTMinis !== 'undefined' && TTMinis.game ? TTMinis.game : null; }");
  var context=Object.assign({module:{exports:{}},require:function(){return config;},Promise:Promise,Date:Date,
    setInterval:setInterval,clearInterval:clearInterval},namespaces);
  vm.runInNewContext(source,context,{filename:file});return context.module.exports;
}
function supported() {
  var calls=[],onClose;
  var api={calls:calls,canIUse:function(method){assert.strictEqual(this,api);return true;},
    createRewardedVideoAd:function(){assert.strictEqual(this,api);calls.push('ad');return {
      onClose:function(fn){onClose=fn;},onError:function(){},offClose:function(){},offError:function(){},
      show:function(){onClose({isEnded:true});return Promise.resolve();}
    };}};
  ['addShortcut','getShortcutMissionReward','startEntranceMission','getEntranceMissionReward'].forEach(function(method){
    api[method]=function(o){assert.strictEqual(this,api);calls.push(method);o.success({canReceiveReward:true});};
  });
  return api;
}
async function verify(namespaces, expected, oldSelector) {
  var Ads=load('RewardedService.js',namespaces,oldSelector);
  var Mission=load('TikTokMissionService.js',namespaces,oldSelector);
  var a=new Ads({autoPoll:false}),m=new Mission({autoPoll:false});
  assert.equal((await a.request({placementKey:'revive'})).rewarded,expected);
  for(var kind of ['shortcut','profile']) {
    assert.equal((await m.navigate(kind)).status,expected?'success':'unsupported');
    assert.equal((await m.query(kind)).eligible,expected);
  }
}
(async function(){
  var results=[];
  for(var prefix of ['TTMinis','tt','wx']) {
    var namespace={};namespace[prefix]=prefix==='TTMinis'?{game:supported()}:supported();
    await verify(namespace,true,false);results.push({case:prefix+'_only_receiver_preserved',status:'passed'});
  }
  for(var prior of [{}, {unrelated:function(){}}, {canIUse:function(){return false;},createRewardedVideoAd:function(){throw Error('wrong SDK');},addShortcut:function(){throw Error('wrong SDK');},getShortcutMissionReward:function(){},startEntranceMission:function(){},getEntranceMissionReward:function(){}}]) {
    await verify({TTMinis:{game:prior},tt:supported()},true,false);
  }
  results.push({case:'first_empty_missing_or_canIUse_false_falls_through',status:'passed'});
  // Different requested methods may live under different compatible prefixes.
  var adOnly=supported();['addShortcut','getShortcutMissionReward','startEntranceMission','getEntranceMissionReward'].forEach(function(k){delete adOnly[k];});
  await verify({TTMinis:{game:adOnly},tt:supported()},true,false);
  results.push({case:'per_method_selection',status:'passed'});
  await verify({TTMinis:{game:{}},tt:{},wx:{getSystemInfoSync:function(){return{};},postMessage:function(){}}},false,false);
  results.push({case:'web_compatibility_shim_unsupported_zero_reward',status:'passed'});
  var injected=supported(), seen=[];
  var Ads=load('RewardedService.js',{}),Mission=load('TikTokMissionService.js',{});
  var getSDK=function(method){seen.push(method);return injected;};
  assert.equal((await new Ads({autoPoll:false,getSDK:getSDK}).request({placementKey:'revive'})).rewarded,true);
  assert.equal((await new Mission({autoPoll:false,getSDK:getSDK}).query('profile')).eligible,true);
  assert.deepEqual(seen,['createRewardedVideoAd','getEntranceMissionReward']);
  results.push({case:'getSDK_injection_preserved_with_requested_method',status:'passed'});
  var detected=false;
  try{await verify({TTMinis:{game:{}},tt:supported()},true,true);}catch(e){detected=e instanceof assert.AssertionError;}
  assert(detected,'Old TTMinis-only selector must fail the same compatibility assertion');
  results.push({case:'old_selector_negative_control_fails_same_assertion',status:'passed'});
  console.log(JSON.stringify({schema:'snakevsblock.sdk_resolution.v1',scope:'Minimal Node namespace substitutes; not actual TikTok Runtime',passed:results.length,results:results},null,2));
})().catch(function(e){console.error(e);process.exitCode=1;});
