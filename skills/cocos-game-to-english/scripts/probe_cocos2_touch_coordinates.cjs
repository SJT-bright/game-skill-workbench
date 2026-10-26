'use strict';
// Executes the package's actual legacy Cocos converter, not a reimplementation.
const vm=require('vm'),fs=require('fs');
function probe(files){
 const engine=files['cocos/cocos2d-js-min.js']||'';
 const start=engine.indexOf('getTouchesByEvent:function(');
 const end=engine.indexOf(',registerSystemEvent:function',start);
 if(start<0||end<0)throw Error('unsupported Cocos touch converter; do not mark input verified');
 const fn=engine.slice(start+'getTouchesByEvent:'.length,end);
 class Touch{constructor(x,y,id){this.x=x;this.y=y;this.id=id;}getLocation(){return{x:this.x,y:this.y};}_setPrevPoint(){}}
 const manager={_glView:{convertToLocationInView(x,y){return{x:x*1,y:y*1};}},_preTouchPoint:{x:0,y:0},getPreTouch(){return{getLocation(){return{x:0,y:0};}};},setPreTouch(){}};
 manager.getTouchesByEvent=vm.runInNewContext('('+fn+')',{n:{BROWSER_TYPE_FIREFOX:'firefox',browserType:'native'},s:{},o:{},cc:{Touch}});
 const entry=files['game.js']||'';
 if(entry.includes("require('./touch-coordinates').install(cc)")){
  const context={module:{exports:{}},Number,Object,Array,Error};vm.runInNewContext(files['touch-coordinates.js']||'',context,{timeout:1000});
  context.module.exports.install({internal:{inputManager:manager}});
 }
 let adapterNormalize=null;
 const adapter=files['adapter-min.js']||'';
 const adapterStart=adapter.indexOf('function __restoreTouchFields2_4('),adapterEnd=adapter.indexOf('function __restoreTouchListener2_4(',adapterStart);
 if(adapterStart>=0&&adapterEnd>adapterStart){
  // Execute the actual package boundary; reject a familiar name without its real call site.
  if(!adapter.includes('__globalAdapter[e](__restoreTouchListener2_4(e,n,function(e){e.changedTouches&&t.call(n,n.getTouchesByEvent(e,o))}))'))throw Error('unreviewed adapter touch dispatch');
  const scope={Number,Object,Math,__restoreTouchPoints2_4:{},__restoreTouchTrace2_4:[]};
  vm.createContext(scope);vm.runInContext(adapter.slice(adapterStart,adapterEnd),scope,{timeout:1000});
  adapterNormalize=scope.__restoreTouchFields2_4;
 }
 // Some packages normalize at game.js before the actual adapter captures SDK methods.
 // Execute that shipped prefix rather than assuming converter-only inputs.
 if(!adapterNormalize && entry.includes('TTMinis.game') && entry.includes('root.tt = compat')){
  const capture={};const sdk={};
  for(const phase of ['Start','Move','End','Cancel'])sdk['onTouch'+phase]=function(fn){capture[phase]=fn;};
  const scope={TTMinis:{game:sdk},Object,Array,Number,isFinite};vm.createContext(scope);
  const firstRequire=entry.search(/require\s*\(/);
  if(firstRequire<0)throw Error('Native SDK prefix has no actual adapter entry');
  vm.runInContext(entry.slice(0,firstRequire),scope,{timeout:1000});
  if(!scope.tt||typeof scope.tt.onTouchStart!=='function')throw Error('Native SDK prefix did not install touch listener');
  adapterNormalize=function(event){let result=null;scope.tt.onTouchStart(function(value){result=value;});capture.Start(event);if(!result)throw Error('Native SDK touch prefix discarded valid event');return result;};
 }
 const cases=[['sdk_screen_coordinates',{identifier:0,screenX:195,screenY:392},195,392],['client_coordinates',{identifier:0,clientX:20,clientY:30},20,30],['preserve_client_coordinates',{identifier:0,clientX:11,clientY:12,screenX:99,screenY:98},11,12],['zero_coordinates',{identifier:0,screenX:0,screenY:0},0,0]];
 const rows=cases.map(([id,t,x,y])=>{const a=manager.getTouchesByEvent(adapterNormalize?adapterNormalize({changedTouches:[t],touches:[t]},'onTouchStart'):{changedTouches:[t],touches:[t]},{});return{id,passed:a.length===1&&a[0].x===x&&a[0].y===y&&a[0].id===0,observed:a.map(t=>({x:t.x,y:t.y,id:t.id}))};});
 return{schema:'cocos2_touch_coordinates.v1',passed:rows.every(r=>r.passed),rows,boundary:'actual converter with controlled SDK payloads; not renderer/device acceptance'};
}
if(require.main===module){try{const payload=JSON.parse(fs.readFileSync(0,'utf8'));const r=probe(payload.files);console.log(JSON.stringify(r));process.exitCode=r.passed?0:1;}catch(e){console.log(JSON.stringify({passed:false,error:e.message}));process.exitCode=1;}}
module.exports={probe};
