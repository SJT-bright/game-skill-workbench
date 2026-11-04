// Node check of remake-core/assets/ad-simulator.js optional modes (v7.5, D2 1.2) with a stub DOM and fake clock.
// Usage: node test_ad_simulator_modes.cjs [ad-simulator.js] [report.json]. Simulation timing only, not a reward verdict.
const fs=require('fs'),vm=require('vm'),path=require('path');
const file=process.argv[2]||path.join(__dirname,'..','assets','ad-simulator.js'),out=process.argv[3];
const code=fs.readFileSync(file,'utf8');
const RewardedService = require('../assets/platform-kit/assets/tiktok-platform/RewardedService.js');
function el(){const e={style:{},children:[],textContent:'',disabled:false,appendChild(c){this.children.push(c);return c;},replaceChildren(){this.children=[];},
  attachShadow(){const s={innerHTML:'',ids:{},getElementById(id){return s.ids[id]||(s.ids[id]=el());}};this.shadowRoot=s;return s;},click(){if(!this.disabled && this.onclick)this.onclick();}};return e;}
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
  function control(prefix) {
    const shadow = document.body.children[0].shadowRoot;
    const box = shadow.getElementById('box');
    const actions = box.children.find(c => c.id === 'actions');
    const b = actions && actions.children.find(c => c.textContent.startsWith(prefix));
    if (!b) throw Error('Missing simulated ad control: ' + prefix);
    return b;
  }
  return {root,advance,emitted,control,now:()=>now};
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
const timeout = setTimeout(() => { console.error('FAIL simulated request did not settle'); process.exit(1); }, 5000);
(async()=>{
  const rows=[];
  function check(name,ok,detail){rows.push({case:name,passed:!!ok,detail});}
  let r=await play('',async(w,ad,log)=>{
    await flush();
    const collect = w.control('模拟看完');
    if (!collect.textContent.includes('5 秒') || !collect.disabled) throw Error('default countdown missing');
    w.advance(4999); collect.click(); await flush();
    if (log.closes.length || !collect.disabled) throw Error('early manual completion');
    w.advance(1); await flush();
    if (log.closes.length || collect.disabled) throw Error('elapsed timer must only unlock the button');
    collect.click(); collect.click(); await flush();
  });
  check('manual: five seconds only enables the button; two taps complete once',r.showResolvedAt===0 && JSON.stringify(r.closes)==='[[5000,true]]',r.closes);
  r=await play('',async(w)=>{w.control('中途关闭').click();w.advance(6000);});
  check('manual: cancel at once during the countdown never completes',JSON.stringify(r.closes)==='[[0,false]]',r.closes);
  r=await play('?adsim=video60',async(w)=>{
    w.control('一直等待').click();w.advance(70000);await flush();
    if (w.root.__adSimulator.finish('completed')) throw Error('waiting mode accepted completion');
    w.root.__adSimulator.finish('cancelled');
  });
  check('waiting suppresses even an automatic long-video completion',JSON.stringify(r.closes)==='[[70000,false]]',r.closes);
  r=await play('?adsim=video60',async(w)=>{await flush();w.advance(59999);await flush();if(r0(w))throw Error("video60 early");w.advance(1);await flush();});
  function r0(w){return w.root.__adSimulator.records[0].outcome;}
  check('video60: no close before 60 s, isEnded true at 60 s',r.closes.length===1&&r.closes[0][0]===60000&&r.closes[0][1]===true,r.closes);
  r=await play('?adsim=video130',async(w)=>{await flush();w.advance(129999);await flush();w.advance(1);await flush();});
  check('video130: isEnded true at 130 s',r.closes.length===1&&r.closes[0][0]===130000&&r.closes[0][1]===true,r.closes);
  r=await play('?adsim=start16',async(w,ad,log)=>{await flush();w.advance(15999);await flush();if(log.showResolvedAt!==null)throw Error("start16 early "+log.showResolvedAt);w.advance(1);await flush();w.advance(2000);w.root.__adSimulator.finish('completed');});
  check('start16: show() resolves at 16 s, then normal playback',r.showResolvedAt===16000&&r.closes.length===1&&r.closes[0][1]===true,{show:r.showResolvedAt,closes:r.closes});
  for (const retire of ['timeout', 'exit']) {
    const w = world(retire === 'timeout' ? '?adsim=start16' : '?adsim=video130');
    const sim = w.root.__adSimulator;
    const service = new RewardedService({getSDK: () => w.root.tt, now: w.now, autoPoll: false});
    try {
      const first = service.request({placementKey: 'hint'});
      await flush();
      if (retire === 'timeout') {
        w.advance(15000); service.tick();
      } else {
        w.advance(30000); service.tick();
        if (!service.exitAvailable()) throw Error('exit unavailable');
        service.exit();
      }
      const ended = await first;
      sim.mode('normal');
      const next = service.request({placementKey:'hint'});
      await flush();
      if (sim.records.length !== 2) throw Error('retired request blocked the immediate retry');
      w.advance(5000); await flush();
      w.control('模拟看完').click();
      const reward = await next;
      w.advance(130000); await flush();
      const old = sim.records[0];
      check('real service: ' + retire + ' unbinds old session, same placement can immediately complete once',
        ended.status === (retire === 'timeout' ? 'timeout' : 'cancelled') && !ended.rewarded &&
        old.outcome === 'detached' && (retire !== 'timeout' || old.lateStartAfterFinish === true) &&
        reward.rewarded && sim.records[1].outcome === 'completed', {ended,reward,old});
    } finally {
      service.dispose();
    }
  }
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
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(() => clearTimeout(timeout));
