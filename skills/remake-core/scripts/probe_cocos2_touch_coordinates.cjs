'use strict';
const __cg=(()=>{try{return require(require('path').join(__dirname,'..','..','cocos-game-check','package-check','scripts','check_guard.cjs'))}catch(e){return null}})();// P20: --help / no input never reaches JSON.parse
if(__cg&&require.main===module)__cg.cli({tool:'probe_cocos2_touch_coordinates.cjs',usage:'Usage: python3 audit_upload_startup.py runs this probe; it reads {"files": {name: text}} JSON on stdin (the package\'s cocos2d-js and adapter) and runs the engine\'s own touch converter.'});
// Executes the package's actual legacy Cocos converter, not a reimplementation.
const vm=require('vm'),fs=require('fs');
// Engine converter source: minified release build or the non-minified debug build (MergeShot2048 v82).
const ENGINES=['cocos/cocos2d-js-min.js','cocos/cocos2d-js.js'];
const ID=/^[A-Za-z_$][\w$]*$/;
function converter(engine){
 const head=/getTouchesByEvent\s*:\s*(?=function\b)/.exec(engine);
 if(!head)throw Error('unsupported Cocos touch converter; do not mark input verified');
 const tail=/,\s*registerSystemEvent\s*:\s*function\b/g;tail.lastIndex=head.index;
 const end=tail.exec(engine);
 if(!end)throw Error('unsupported Cocos touch converter; do not mark input verified');
 const fn=engine.slice(head.index+head[0].length,end.index);
 // Closure names the converter reads from its module scope: the sys alias (n in 2.4.15, sys in debug builds)
 // and, from Creator 2.4.5 on, the scratch Vec2 passed as 4th argument of convertToLocationInView (a / _vec2).
 const params=((/^function\b[^(]*\(([^)]*)\)/.exec(fn)||[])[1]||'').split(',').map(s=>s.trim()).filter(Boolean);
 const sys=(/([A-Za-z_$][\w$]*)\.BROWSER_TYPE_FIREFOX\s*===\s*\1\.browserType/.exec(fn)||[])[1];
 if(!sys)throw Error('unsupported Cocos touch converter: no browserType branch');
 const aliases={};aliases[sys]={BROWSER_TYPE_FIREFOX:'firefox',browserType:'native'};
 for(const call of fn.matchAll(/convertToLocationInView\(([^()]*)\)/g)){
  call[1].split(',').slice(3).map(s=>s.trim()).forEach(name=>{if(ID.test(name)&&!params.includes(name)&&!(name in aliases))aliases[name]={x:0,y:0};});
 }
 return{fn,aliases};
}
function requires(source,name){
 const re=new RegExp("require\\(\\s*['\"]\\.?/?"+name.replace(/\.js$/,'').replace(/[.$]/g,'\\$&')+"(?:\\.js)?['\"]\\s*\\)");
 const m=re.exec(source);return m?m.index:-1;
}
function probe(files){
 const candidates=Object.keys(files).filter(n=>/(?:^|\/)cocos\/cocos2d-js(?:-min)?\.js$/.test(n)&&/getTouchesByEvent\s*:\s*function\b/.test(files[n]));
 const engineName=ENGINES.find(n=>candidates.includes(n))||(candidates.length===1?candidates[0]:ENGINES[0]);
 const engine=files[engineName]||'';
 const conv=converter(engine);
 class Touch{constructor(x,y,id){this.x=x;this.y=y;this.id=id;}getLocation(){return{x:this.x,y:this.y};}_setPrevPoint(){}}
 const manager={_glView:{convertToLocationInView(x,y){return{x:x*1,y:y*1};}},_preTouchPoint:{x:0,y:0},getPreTouch(){return{getLocation(){return{x:0,y:0};}};},setPreTouch(){}};
 manager.getTouchesByEvent=vm.runInNewContext('('+conv.fn+')',Object.assign({s:{},o:{},cc:{Touch}},conv.aliases));
 const entry=files['game.js']||'';
 const INSTALL=/require\(\s*['"]\.\/touch-coordinates(?:\.js)?['"]\s*\)\.install\(\s*cc\s*\)/;
 // The TikTok Platform Kit installs the converter fix from main.js (README: only main.js + touch-coordinates.js in
 // build-templates/bytedance); older games did it in game.js. main.js counts only when game.js really loads it.
 const mainLoaded=requires(entry,'main')>=0;
 if(INSTALL.test(entry)||(mainLoaded&&INSTALL.test(files['main.js']||''))){
  const context={module:{exports:{}},Number,Object,Array,Error};vm.runInNewContext(files['touch-coordinates.js']||'',context,{timeout:1000});
  context.module.exports.install({internal:{inputManager:manager}});
 }
 let adapterNormalize=null, adapterDispatch=null;
 const adapter=files['adapter-min.js']||'';
 const adapterStart=adapter.indexOf('function __restoreTouchFields2_4('),adapterEnd=adapter.indexOf('function __restoreTouchListener2_4(',adapterStart);
 if(adapterStart>=0&&adapterEnd>adapterStart){
  // Execute the actual package boundary; reject a familiar name without its real call site.
  if(!adapter.includes('__globalAdapter[e](__restoreTouchListener2_4(e,n,function(e){e.changedTouches&&t.call(n,n.getTouchesByEvent(e,o))}))'))throw Error('unreviewed adapter touch dispatch');
  const scope={Number,Object,Math,__restoreTouchPoints2_4:{},__restoreTouchTrace2_4:[]};
  vm.createContext(scope);vm.runInContext(adapter.slice(adapterStart,adapterEnd),scope,{timeout:1000});
  adapterNormalize=scope.__restoreTouchFields2_4;
 }
 // Legacy Mouse Chef adapters normalize inside the actual four-phase registration.
 // Execute that registration and the shipped helper, not a renamed/synthetic normalizer.
 if(adapter.includes('function __mouseChefTouchFields2_4(')){
  const loaded=requires(entry,'adapter-min'),engineAt=requires(entry,'cocos/cocos2d-js-min');
  if(loaded<0||engineAt<0||loaded>engineAt)throw Error('legacy touch adapter is not loaded before engine');
  const marker='// MouseChef Cocos 2.4.15 documented touch fields v';
  const helperAt=adapter.indexOf(marker),heads=[...adapter.matchAll(/registerSystemEvent\s*:\s*(function\([^)]*\)\{)/g)];
  if(helperAt<0||heads.length!==1)throw Error('unsupported legacy registration');
  const start=heads[0].index+heads[0][0].indexOf('function'),brace=adapter.indexOf('{',start);
  let depth=0,end=-1,quote=null;
  for(let i=brace;i<helperAt;i++){const c=adapter[i];if(quote){if(c==='\\'){i++;continue;}if(c===quote)quote=null;continue;}if(c==='"'||c==="'"){quote=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0){end=i+1;break;}}
  if(end<0)throw Error('unclosed legacy registration');
  const registration=adapter.slice(start,end),canvas=(/getTouchesByEvent\(\w+,(\w+)\)/.exec(registration)||[])[1];
  if(!canvas)throw Error('unsupported legacy canvas binding');
  const callbacks={},phases={onTouchStart:'handleTouchesBegin',onTouchMove:'handleTouchesMove',onTouchEnd:'handleTouchesEnd',onTouchCancel:'handleTouchesCancel'};
  let received=null;
  manager._touchesIntegerDict={};
  for(const handler of Object.values(phases))manager[handler]=touches=>{received=touches};
  const scope={Number,Object,Math,cc:{view:manager._glView},console:{info(){}},__globalAdapter:{}};
  scope[canvas]={};
  for(const phase of Object.keys(phases))scope.__globalAdapter[phase]=fn=>{callbacks[phase]=fn};
  vm.createContext(scope);vm.runInContext(adapter.slice(helperAt),scope,{timeout:1000});
  scope.manager=manager;
  vm.runInContext('('+registration+').call(manager,{})',scope,{timeout:1000});
  if(Object.keys(phases).some(p=>typeof callbacks[p]!=='function'))throw Error('missing legacy touch phase');
  adapterDispatch=event=>{received=null;scope.event=event;scope.dispatch=callbacks.onTouchStart;vm.runInContext('dispatch(event)',scope,{timeout:1000});if(!received)throw Error('legacy adapter did not deliver touches');return received};
 }
 // An SDK touch wrapper module required by game.js before the adapter: Basil's tiktok-input.js, or a module the
 // project declares with a line `// tiktok-touch-adapter: ./name.js` in game.js. Execute the shipped module on an
 // SDK stub and read what a listener registered through it receives. Missing or required after the adapter -> fail.
 if(!adapterNormalize){
  const declared=[...entry.matchAll(/\/\/\s*tiktok-touch-adapter:\s*\.?\/?([\w.\-\/]+?)(?:\.js)?\s*$/gm)].map(m=>m[1]+'.js');
  const adapterAt=['adapter-min','adapter'].map(n=>requires(entry,n)).filter(i=>i>=0).sort((a,b)=>a-b)[0];
  const named=['tiktok-input.js'].filter(n=>requires(entry,n)>=0).concat(declared);
  for(const name of [...new Set(named)]){
   const at=requires(entry,name);
   if(at<0)throw Error('declared touch adapter '+name+' is not required by game.js');
   if(!files[name])throw Error('touch adapter '+name+' is required by game.js but missing from the package');
   if(adapterAt!==undefined&&at>adapterAt)throw Error('touch adapter '+name+' installed after the adapter (too late)');
  }
  if(named.length){
   let listener=null;
   const sdk={onTouchStart(fn){listener=fn;},offTouchStart(){},onTouchMove(){},offTouchMove(){},onTouchEnd(){},offTouchEnd(){},onTouchCancel(){},offTouchCancel(){}};
   const context={TTMinis:{game:sdk},tt:sdk,GameGlobal:{},Proxy,Reflect,WeakMap,Map,Set,Array,Object,Number,Math,isFinite,console:{log(){},warn(){},error(){}}};
   context.globalThis=context;context.window=context;context.GameGlobal=context;vm.createContext(context);
   for(const name of [...new Set(named)].sort((a,b)=>requires(entry,a)-requires(entry,b))){
    const module={exports:{}};context.module=module;context.exports=module.exports;
    vm.runInContext(files[name],context,{timeout:1000,filename:name});
   }
   const api=context.TTMinis&&context.TTMinis.game||context.tt;
   let mapped=null;
   api.onTouchStart(function(e){mapped=e;});
   if(typeof listener!=='function')throw Error('touch adapter did not register with the SDK');
   adapterNormalize=event=>{mapped=null;listener(event);if(!mapped)throw Error('touch adapter discarded a valid event');return mapped;};
  }
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
 // Some Cocos 2.4 packages normalize SDK events in an external facade before adapter registration.
 if(entry.includes("require('./tiktok-touch-bridge')(TTMinis.game)")){
  if(entry.indexOf("require('./tiktok-touch-bridge')")>entry.indexOf("require('adapter-min.js')"))throw Error('touch facade installed after adapter');
  if(!/globalThis\.tt\s*=\s*engineSDK/.test(entry)||!adapter.includes('tt.onTouchStart'))throw Error('touch facade is not connected to the engine SDK namespace');
  let listener=null,mapped=null;
  const sdk={onTouchStart(fn){listener=fn},offTouchStart(){}};
  const context={module:{exports:{}},Proxy,Reflect,WeakMap,Set,Array,Object,Number,isFinite};
  vm.runInNewContext(files['tiktok-touch-bridge.js']||'',context,{timeout:1000});
  const facade=context.module.exports(Object.freeze(sdk));facade.onTouchStart(e=>{mapped=e});
  adapterNormalize=event=>{mapped=null;listener(event);return mapped;};
 }
 const cases=[['sdk_screen_coordinates',{identifier:0,screenX:195,screenY:392},195,392],['client_coordinates',{identifier:0,clientX:20,clientY:30},20,30],['preserve_client_coordinates',{identifier:0,clientX:11,clientY:12,screenX:99,screenY:98},11,12],['zero_coordinates',{identifier:0,screenX:0,screenY:0},0,0]];
 const rows=cases.map(([id,t,x,y])=>{const a=adapterDispatch?adapterDispatch({changedTouches:[t],touches:[t]}):manager.getTouchesByEvent(adapterNormalize?adapterNormalize({changedTouches:[t],touches:[t]},'onTouchStart'):{changedTouches:[t],touches:[t]},{});return{id,expected:{x,y,id:0},passed:a.length===1&&a[0].x===x&&a[0].y===y&&a[0].id===0,observed:a.map(t=>({x:t.x,y:t.y,id:t.id}))};});
 return{schema:'cocos2_touch_coordinates.v1',passed:rows.every(r=>r.passed),rows,boundary:'actual converter with controlled SDK payloads; not renderer/device acceptance'};
}
if(require.main===module){try{const payload=JSON.parse((__cg&&require.main===module?__cg.stdinText('probe_cocos2_touch_coordinates.cjs'):fs.readFileSync(0,'utf8')));const r=probe(payload.files);console.log(JSON.stringify(r));process.exitCode=r.passed?0:1;}catch(e){console.log(JSON.stringify({passed:false,error:e.message}));process.exitCode=1;}}
module.exports={probe};
