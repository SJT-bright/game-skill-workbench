'use strict';
const assert=require('node:assert/strict');
const {scan,scanFiles}=require('./scan_tiktok_host_refs.cjs');
const rows=[];
function test(name,fn){fn();rows.push({name,passed:true});}
const good=code=>assert.deepEqual(scan(code,'business.js'),[]);
const bad=code=>assert(scan(code,'business.js').length>0,'unsafe access accepted: '+code);
test('unused_direct_property_aliases',()=>{
  good('function f(){var wx=window["wx"];return 1;}');
  good('function f(){const legacy=globalThis.wx;return 1;}');
  good('var unused=window.wx;');
});
test('used_or_escaping_alias_still_rejected',()=>{
  bad('function f(){var wx=window.wx;wx.login();}');
  bad('function f(){var legacy=window.wx;legacy.login();}');
  bad('function f(){var legacy=window.wx;return legacy;}');
  bad('function f(){var legacy=window.wx;run(legacy);}');
});
test('nested_shadow_does_not_make_unused_alias_used',()=>good('function f(){var sdk=window.wx;function g(sdk){sdk.local();}}'));
test('captured_alias_is_used',()=>bad('function f(){var sdk=window.wx;return ()=>sdk.login();}'));
test('eval_or_with_prevents_unused_proof',()=>{
  bad('function f(){var wx=window.wx;eval("wx.login()");}');
  bad('function f(){var sdk=window.wx;with(object){use(value);}}');
});
test('exact_guarded_optional_global_call',()=>{
  good('window.wx&&window.wx.showShareMenu({menus:["shareAppMessage"]});');
  good('globalThis["wx"]&&globalThis["wx"].showToast({title:"x"});');
});
test('bare_wx_presence_check_can_throw',()=>{
  bad('wx&&wx.login();');bad('root.wx&&root.wx.login();');
});
test('unguarded_access_and_wrong_root_are_rejected',()=>{
  bad('window.wx.login();');bad('window.wx&&globalThis.wx.login();');
  bad('window.wx&&window.wx.login(changeHost(),window.wx.getStorageSync("x"));');
  bad('var unused=root.wx;');
});
test('guard_does_not_escape_into_deferred_callback',()=>bad('window.wx&&window.wx.login({success:()=>window.wx.getStorageSync("x")});'));
test('mutations_and_sequences_cannot_reuse_presence_guard',()=>{
  bad('window.wx&&(window.wx=null,window.wx.login());');
  bad('window.wx&&window.wx.login(window.wx=null);');
});
test('wechat_first_candidate_is_still_rejected',()=>bad('var sdk=root.wx||root.tt||root.TTMinis.game;'));
const probe='function(){var t=typeof window==="undefined"?global:window;function present(e){return typeof t[e]==="object";}var n=!(!present("wx")||!wx.getSharedCanvas),r=!(!present("wx")||!wx.getSystemInfoSync&&!wx.getSharedCanvas);cc.ENGINE_VERSION="2.4.4";}';
const modules=Array.from({length:101},(_,i)=>JSON.stringify(String(i))+':['+(i===100?probe:'function(){}')+',{}]').join(',');
const engine='var modules={'+modules+'};/*'+' '.repeat(100001)+'*/';
const files=code=>[{file:'game.js',code:'require("./cocos2d-js-min.js");'},{file:'cocos2d-js-min.js',code}];
test('root_engine_guarded_probes_with_real_entry_link',()=>assert.deepEqual(scanFiles(files(engine)),[]));
test('root_engine_still_reports_appended_unsafe_code',()=>assert(scanFiles(files(engine+'wx.login();')).length>0));
test('engine_name_alone_is_not_a_whitelist',()=>assert(scanFiles(files('wx.login();')).length>0));
test('engine_shape_without_entry_link_is_not_exempt',()=>assert(scanFiles([{file:'game.js',code:'require("./other.js");'},{file:'cocos2d-js-min.js',code:engine}]).length>0));
test('commented_require_does_not_establish_entry_link',()=>assert(scanFiles([{file:'game.js',code:'// require("./cocos2d-js-min.js");'},{file:'cocos2d-js-min.js',code:engine}]).length>0));
test('nonliteral_require_does_not_establish_entry_link',()=>assert(scanFiles([{file:'game.js',code:'require("./"+"cocos2d-js-min.js");'},{file:'cocos2d-js-min.js',code:engine}]).length>0));
console.log(JSON.stringify({passed:true,count:rows.length,cases:rows},null,2));
