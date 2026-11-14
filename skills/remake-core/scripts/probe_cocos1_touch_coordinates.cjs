'use strict';
// Executes the shipped 1.9.3 adapter event module and engine converter, for all four phases.
const fs=require('fs'),vm=require('vm');
function probe(files){
 const engineName=['cocos2d-js-min.js','cocos2d-js.js'].find(n=>/cc\.ENGINE_VERSION\s*=\s*['"]1\.9\.3['"]/.test(files[n]||''));
 if(!engineName)throw Error('Creator 1.9.3 engine missing');
 const entry=files['game.js']||'',adapter=files['adapter-min.js']||'';
 const at=(s,n)=>{const a=s.indexOf("require('./"+n+"')"),b=s.indexOf("require('./"+n+".js')");return a<0?b:b<0?a:Math.min(a,b);};
 if(at(entry,'sdk-namespace')<0||at(entry,'adapter-min')<at(entry,'sdk-namespace')||at(adapter,'libs/weapp-adapter/index')<0)throw Error('SDK namespace must load before actual Creator adapter');
 const code=files[engineName],head=code.indexOf('getTouchesByEvent:function'),end=code.indexOf(',registerSystemEvent:',head);
 if(head<0||end<0)throw Error('unrecognized actual 1.9 converter');
 const converter=code.slice(head+'getTouchesByEvent:'.length,end);
 const alias=(/([\w$]+)\.BROWSER_TYPE_FIREFOX/.exec(converter)||[])[1];
 if(!alias)throw Error('engine sys closure missing');
 const callbacks={},sdk={createCanvas(){},createImage(){},getSystemInfoSync(){},getFileSystemManager(){}};
 for(const phase of ['Start','Move','End','Cancel'])sdk['onTouch'+phase]=fn=>callbacks[phase]=fn;
 let received=null;
 const context={TTMinis:{game:sdk},window:{canvas:{}},document:{dispatchEvent(e){received=e;}},console,Object,Array,Number,Math};
 context.globalThis=context;context.GameGlobal=context;
 vm.createContext(context);
 context.module={exports:{}};vm.runInContext(files['sdk-namespace.js']||'',context,{timeout:1000});
 if(context.wx!==sdk)throw Error('namespace bridge must select the actual SDK');
 context.require=n=>{if(n==='../util/index.js')return {noop(){}};throw Error('unreviewed touch module dependency '+n);};
 context.module={exports:{}};context.exports=context.module.exports;
 vm.runInContext(files['libs/weapp-adapter/EventIniter/TouchEvent.js']||'',context,{timeout:1000});
 class Touch{constructor(x,y,id){this.x=x;this.y=y;this.id=id;}getLocation(){return {x:this.x,y:this.y};}_setPrevPoint(){}}
 context.cc={Touch};context[alias]={BROWSER_TYPE_FIREFOX:'firefox',browserType:'native'};
 const fn=vm.runInContext('('+converter+')',context,{timeout:1000});
 const manager={_glView:{convertToLocationInView(x,y){return {x,y};}},_preTouchPoint:{x:0,y:0},getPreTouch(){return {getLocation(){return {x:0,y:0};}};},setPreTouch(){}};
 const rows=[];
 for(const [phase,type]of [['Start','touchstart'],['Move','touchmove'],['End','touchend'],['Cancel','touchcancel']]){
  for(const [x,y]of [[19,31],[194,516],[371,802]]){
   received=null;
   if(typeof callbacks[phase]!=='function')throw Error('missing SDK '+phase+' callback');
   const point={identifier:7,screenX:x,screenY:y,force:1};
   callbacks[phase]({touches:phase==='End'||phase==='Cancel'?[]:[point],changedTouches:[point],timeStamp:123});
   if(!received||received.type!==type)throw Error('actual DOM event not dispatched');
   const touches=fn.call(manager,received,{}),observed=touches.map(t=>t.getLocation());
   rows.push({phase,expected:{x,y},observed,passed:observed.length===1&&observed[0].x===x&&observed[0].y===y});
  }
 }
 return {schema:'cocos1_touch_coordinates.v1',engine:'1.9.3',passed:rows.every(r=>r.passed),rows};
}
if(require.main===module){try{const r=probe(JSON.parse(fs.readFileSync(0,'utf8')).files);console.log(JSON.stringify(r));process.exitCode=r.passed?0:1;}catch(e){console.log(JSON.stringify({schema:'cocos1_touch_coordinates.v1',passed:false,error:String(e)}));process.exitCode=1;}}
module.exports={probe};
