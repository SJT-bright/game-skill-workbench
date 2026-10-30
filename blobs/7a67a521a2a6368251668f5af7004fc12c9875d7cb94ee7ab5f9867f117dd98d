// Node check of remake-core/assets/ad-simulator.js optional modes (v7.5, D2 1.2) with a stub DOM and fake clock.
// Usage: node test_ad_simulator_modes.cjs [ad-simulator.js] [report.json]. Simulation timing only, not a reward verdict.
const fs=require('fs'),vm=require('vm'),path=require('path');
const file=process.argv[2]||path.join(__dirname,'..','assets','ad-simulator.js'),out=process.argv[3];
const code=fs.readFileSync(file,'utf8');
function el(){const e={style:{},children:[],textContent:'',disabled:false,appendChild(c){this.children.push(c);return c;},replaceChildren(){this.children=[];},
  attachShadow(){const s={innerHTML:'',ids:{},getElementById(id){return s.ids[id]||(s.ids[id]=el());}};return s;},click(){this.onclick&&this.onclick();}};return e;}
function world(search){
  let now=0,timers=[],seq=0;
  const clock={setTimeout(f,ms){const id=++seq;timers.push({id,at:now+(ms||0),f});return id;},clearTimeout(id){timers=timers.filter(t=>t.id!==id);}};
  function advance(ms){const end=now+ms;for(;;){timers.sort((a,b)=>a.at-b.at);const t=timers[0];if(!t||t.at>end)break;timers.shift();now=t.at;t.f();}now=end;}
  const emitted=[];
  const root={location:{hostname:'127.0.0.1',search:search||''},localStorage:{length:0,key(){},getItem(){}},
    cc:{game:{EVENT_HIDE:'game_on_hide',EVENT_SHOW:'game_on_show',emit(n){emitted.push([now,n]);}}}};
  const document={readyState:'complete',body:el(),createElement:()=>el(),querySelector:()=>null,addEventListener(){}};
  const ctx={window:root,document,setTimeout:clock.setTimeout,clearTimeout:clock.clearTimeout,Date:{now:()=>now},Promise,JSON,Object,String,Array,Error,URL:{},Blob:function(){},history:{},decodeURIComponent};
  ctx.window=root;vm.createContext(ctx);vm.runInContext(code.replace(/\}\)\(window\);\s*$/,'})(window);'),ctx);
  return {root,advance,emitted,now:()=>now};
}
async function flush(){for(let i=0;i<5;i++)await Promise.resolve();}
async function play(search,script){
  const w=world(search),tt=w.root.tt,log={closes:[],hides:[],shows:[],showResolvedAt:null};
  tt.onHide(()=>log.hides.push(w.now()));tt.onShow(()=>log.shows.push(w.now()));
  const ad=tt.createRewardedVideoAd({adUnitId:'unit'});ad.onClose(r=>log.closes.push([w.now(),r.isEnded]));
  ad.show().then(()=>{log.showResolvedAt=w.now();});
  await script(w,ad,log);await flush();
  return Object.assign(log,{emitted:w.emitted,record:w.root.__adSimulator.records[0]});
}
(async()=>{
  const rows=[];
  function check(name,ok,detail){rows.push({case:name,passed:!!ok,detail});}
  let r=await play('',async(w)=>{await flush();w.advance(1999);w.root.__adSimulator.finish('completed');await flush();});
  check('default: complete still available at once via finish() and show() resolves immediately',r.showResolvedAt===0&&r.closes.length===1&&r.closes[0][1]===true,r.closes);
  r=await play('?adsim=video60',async(w)=>{await flush();w.advance(59999);await flush();if(r0(w))throw Error("video60 early");w.advance(1);await flush();});
  function r0(w){return w.root.__adSimulator.records[0].outcome;}
  check('video60: no close before 60 s, isEnded true at 60 s',r.closes.length===1&&r.closes[0][0]===60000&&r.closes[0][1]===true,r.closes);
  r=await play('?adsim=video130',async(w)=>{await flush();w.advance(129999);await flush();w.advance(1);await flush();});
  check('video130: isEnded true at 130 s',r.closes.length===1&&r.closes[0][0]===130000&&r.closes[0][1]===true,r.closes);
  r=await play('?adsim=start16',async(w,ad,log)=>{await flush();w.advance(15999);await flush();if(log.showResolvedAt!==null)throw Error("start16 early "+log.showResolvedAt);w.advance(1);await flush();w.advance(2000);w.root.__adSimulator.finish('completed');});
  check('start16: show() resolves at 16 s, then normal playback',r.showResolvedAt===16000&&r.closes.length===1&&r.closes[0][1]===true,{show:r.showResolvedAt,closes:r.closes});
  r=await play('?adsim=start16',async(w,ad)=>{await flush();w.advance(15000);ad.destroy();await flush();w.advance(1000);await flush();w.advance(130000);await flush();});
  check('start16 + game gives up at 15 s: late start resolves, never isEnded true',r.showResolvedAt===16000&&r.closes.every(c=>c[1]===false)&&r.record.lateStartAfterFinish===true,{show:r.showResolvedAt,closes:r.closes});
  r=await play('?adsim=background',async(w)=>{await flush();w.advance(10000);w.root.__adSimulator.finish('completed');await flush();});
  check('background: onHide at 2 s, onShow at 5 s, cc.game EVENT_HIDE/EVENT_SHOW emitted, then complete',
    JSON.stringify(r.hides)==='[2000]'&&JSON.stringify(r.shows)==='[5000]'&&r.emitted.map(e=>e[1]).join()==='game_on_hide,game_on_show'&&r.closes[0][1]===true,{hides:r.hides,shows:r.shows,emitted:r.emitted});
  r=await play('?adsim=video130,background',async(w)=>{await flush();w.advance(3000);w.root.__adSimulator.finish('cancelled');await flush();});
  check('background + cancel while hidden: onShow fired before close, isEnded false',JSON.stringify(r.shows)==='[3000]'&&r.closes[0][1]===false,{shows:r.shows,closes:r.closes});
  let threw=false;try{world('').root.__adSimulator.mode('video60,video130');}catch(e){threw=true;}
  check('video60 and video130 together are refused',threw);
  const ok=rows.every(x=>x.passed);
  if(out)fs.writeFileSync(out,JSON.stringify({file,all_passed:ok,rows,boundary:'stub DOM + fake clock; simulation behaviour only, not a game reward verdict'},null,2));
  rows.forEach(x=>console.log((x.passed?'PASS ':'FAIL ')+x.case));process.exitCode=ok?0:1;
})().catch(e=>{console.error(e);process.exitCode=1;});
