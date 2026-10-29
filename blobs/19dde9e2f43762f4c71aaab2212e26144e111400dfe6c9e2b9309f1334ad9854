'use strict';
var assert = require('assert');
var RewardedService = require('./RewardedService');
var Mission = require('./TikTokMissionService');
var config = require('./PlatformConfig');
var results = [];
var watchdog = setTimeout(function () { console.error('Unsettled test promise: timeout recovery missing'); process.exitCode = 1; }, 1500);
async function test(name, run) { await run(); results.push({name:name,status:'passed'}); }
function fakeAd(mode) {
  var h = {}, ad = {
    onClose: function (fn) {h.close=fn;}, onError:function(fn){h.error=fn;},
    offClose:function(fn){if(h.close===fn)h.close=null;},offError:function(fn){if(h.error===fn)h.error=null;},
    show:function(){
      if(mode==='throw')throw new Error('show');
      if(mode==='reject')return Promise.reject({errorCode:1003});
      if(mode==='pending')return new Promise(function(){});
      return Promise.resolve();
    }, close:function(x){if(h.close)h.close(x);},error:function(x){if(h.error)h.error(x);}
  };
  return ad;
}
function ads(mode) {
  var time=0, list=[];
  var sdk={canIUse:function(){return true;},createRewardedVideoAd:function(opts){
    assert(config.rewardedPlacements.some(function(p){return p.id===opts.adUnitId;}));
    var ad=fakeAd(mode);list.push(ad);return ad;
  }};
  var options={getSDK:function(){return sdk;},now:function(){return time;},autoPoll:false,requestTimeoutMs:10,playbackTimeoutMs:20};
  return {service:new RewardedService(options),second:function(){return new RewardedService(options);},list:list,advance:function(n){time+=n;}};
}
function mission(method) {
  var time=0,calls=0,api={canIUse:function(){return true;}};
  ['addShortcut','getShortcutMissionReward','startEntranceMission','getEntranceMissionReward'].forEach(function(k){api[k]=function(opts){calls++;return method(k,opts);};});
  return {service:new Mission({getSDK:function(){return api;},now:function(){return time;},timeoutMs:200,autoPoll:false}),
    advance:function(n){time+=n;},calls:function(){return calls;}};
}
(async function(){
  await test('all_15_placement_keys_present_three_public_ids_and_removed_card_disabled',async function(){
    assert.equal(Object.keys(config.placementMap).length,15);
    assert.equal(new Set(Object.keys(config.placementMap).map(config.getAdUnitId).filter(Boolean)).size,3);
    assert.equal(config.getAdUnitId('fortune_card'),'');
  });
  await test('web_sdk_missing_never_rewards',async function(){
    var s=new RewardedService({getSDK:function(){return null;},autoPoll:false});
    assert.equal((await s.request({placementKey:'revive'})).status,'unsupported');
    var m=new Mission({getSDK:function(){return null;},autoPoll:false});
    assert.equal((await m.query('shortcut')).eligible,false);
    assert.equal((await m.navigate('profile')).status,'unsupported');
  });
  await test('show_resolve_does_not_reward_only_ended_true_new_instance_per_request',async function(){
    var f=ads(), p=f.service.request({placementKey:'revive'}), settled=false;
    p.then(function(){settled=true;});await Promise.resolve();await Promise.resolve();assert(!settled);
    f.list[0].close({isEnded:true});assert.equal((await p).rewarded,true);
    var p2=f.service.request({placementKey:'revive'});assert.equal(f.list.length,2);
    f.list[1].close({isEnded:true});assert.equal((await p2).rewarded,true);
  });
  await test('undefined_false_and_truthy_non_boolean_close_never_reward',async function(){
    for(var x of [undefined,{isEnded:false},{isEnded:1},{isEnded:'true'}]){
      var f=ads(),p=f.service.request({placementKey:'revive'});f.list[0].close(x);
      assert.equal((await p).rewarded,false);
    }
  });
  await test('error_throw_reject_never_reward_and_release',async function(){
    for(var mode of ['throw','reject','normal']){
      var f=ads(mode),p=f.service.request({placementKey:'revive'});
      if(mode==='normal')f.list[0].error({errorCode:1004});
      assert.equal((await p).status,'error');assert(!f.service.isNativeBusy());
    }
  });
  await test('cross_instance_busy_prevents_callback_overwrite',async function(){
    var f=ads(),g=f.second(),p=f.service.request({placementKey:'revive'});
    assert.equal((await g.request({placementKey:'daily_double'})).status,'busy');
    f.list[0].close({isEnded:true});assert.equal((await p).rewarded,true);assert.equal(f.list.length,1);
  });
  await test('duplicate_close_error_only_one_outcome',async function(){
    var f=ads(),p=f.service.request({placementKey:'revive'}),count=0;p.then(function(r){if(r.rewarded)count++;});
    f.list[0].close({isEnded:true});f.list[0].close({isEnded:true});f.list[0].error({});await p;
    assert.equal(count,1);
  });
  await test('request_timeout_independent_tick_and_native_quarantine_until_terminal',async function(){
    var f=ads('pending'),p=f.service.request({placementKey:'revive'});f.advance(11);f.service.tick();
    assert.equal((await p).status,'timeout');assert(f.service.isNativeBusy());
    assert.equal((await f.second().request({placementKey:'revive'})).status,'busy');
    f.list[0].close({isEnded:true});assert(!f.service.isNativeBusy());
    var retry=f.service.request({placementKey:'revive'});f.list[1].close({isEnded:true});assert((await retry).rewarded);
  });
  await test('playback_timeout_does_not_reward_late_ended',async function(){
    var f=ads(),p=f.service.request({placementKey:'revive'});await Promise.resolve();f.advance(21);f.service.tick();
    assert.equal((await p).status,'timeout');f.list[0].close({isEnded:true});assert(!f.service.isNativeBusy());
  });
  await test('cancel_and_dispose_leave_native_lock_then_late_close_cannot_reward',async function(){
    for(var dispose of [false,true]){
      var f=ads(),p=f.service.request({placementKey:'revive',ownerId:'old'});
      if(dispose)f.service.dispose();else f.service.cancelOwner('old');
      assert.equal((await p).rewarded,false);assert(f.service.isNativeBusy());
      f.list[0].close({isEnded:true});assert(!f.service.isNativeBusy());
    }
  });
  await test('run_identity_blocks_late_success',async function(){
    var f=ads(),alive=true,p=f.service.request({placementKey:'revive',isCurrent:function(){return alive;}});
    alive=false;f.list[0].close({isEnded:true});assert.equal((await p).status,'stale');
  });
  await test('mission_callback_promise_and_both_strict_boolean',async function(){
    for(var mode of ['callback','promise','both']) for(var eligible of [true,false]){
      var f=mission(function(k,o){if(mode!=='promise')o.success({canReceiveReward:eligible});o.complete();return mode!=='callback'?Promise.resolve({canReceiveReward:eligible}):undefined;});
      assert.equal((await f.service.query('shortcut')).eligible,eligible);
      assert.equal((await f.service.query('profile')).eligible,eligible);
    }
  });
  await test('navigation_success_never_eligible',async function(){
    var f=mission(function(k,o){o.success({canReceiveReward:true});return Promise.resolve({canReceiveReward:true});});
    assert.equal((await f.service.navigate('shortcut')).eligible,false);
    assert.equal((await f.service.navigate('profile')).status,'success');
  });
  await test('complete_before_same_turn_promise_does_not_steal_valid_eligibility',async function(){
    var f=mission(function(k,o){o.complete();return Promise.resolve({canReceiveReward:true});});
    assert.equal((await f.service.query('shortcut')).eligible,true);
  });
  await test('empty_promise_complete_only_and_non_boolean_bounded_invalid',async function(){
    for(var mode of ['empty','complete','truthy']){
      var f=mission(function(k,o){if(mode==='complete'){o.complete();return;}return Promise.resolve(mode==='truthy'?{canReceiveReward:1}:undefined);});
      var p=f.service.query('profile');await Promise.resolve();f.advance(101);f.service.tick();
      assert.equal((await p).status,'invalid');
    }
  });
  await test('mission_reject_throw_fail_no_reward',async function(){
    for(var mode of ['reject','throw','fail']){
      var f=mission(function(k,o){if(mode==='throw')throw new Error();if(mode==='reject')return Promise.reject({errorCode:7});o.fail({errorCode:8});});
      assert.equal((await f.service.query('shortcut')).status,'error');
    }
  });
  await test('SDK_and_timer_withheld_tick_recovers_then_manual_retry_eligible',async function(){
    var held=true,f=mission(function(){return held?new Promise(function(){}):Promise.resolve({canReceiveReward:true});});
    var p=f.service.query('shortcut');f.advance(201);f.service.tick();assert.equal((await p).status,'timeout');
    held=false;assert.equal((await f.service.query('shortcut')).eligible,true);
  });
  await test('same_query_clicks_coalesce_resume_invalidates_A_and_B_can_succeed',async function(){
    var pending=[],f=mission(function(k,o){pending.push(o);});
    var a=f.service.query('shortcut');assert.strictEqual(a,f.service.query('shortcut'));assert.equal(f.calls(),1);
    f.service.onResume();assert.equal((await a).eligible,false);
    var b=f.service.query('shortcut');pending[0].success({canReceiveReward:true});pending[1].success({canReceiveReward:true});
    assert.equal((await b).eligible,true);assert.equal(f.calls(),2);
  });
  await test('mission_owner_invalid_never_eligible',async function(){
    var cb,active=true,f=mission(function(k,o){cb=o;});
    var p=f.service.query('profile',{isCurrent:function(){return active;}});active=false;cb.success({canReceiveReward:true});
    assert.equal((await p).status,'stale');
  });
  await test('method_and_canIUse_checked_individually',async function(){
    var m=new Mission({autoPoll:false,getSDK:function(){return {canIUse:function(){return false;},addShortcut:function(){throw Error('must not call');}};}});
    assert.equal((await m.navigate('shortcut')).status,'unsupported');assert.equal((await m.query('profile')).status,'unsupported');
  });
  clearTimeout(watchdog);
  console.log(JSON.stringify({schema:'snakevsblock.platform_component_tests.v1',scope:'Node SDK substitutes; no real TikTok IAA or Cocos UI evidence',passed:results.length,results:results},null,2));
})().catch(function(e){clearTimeout(watchdog);console.error(e);process.exitCode=1;});
