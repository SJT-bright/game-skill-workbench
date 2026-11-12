// No controller calls stand in for input. state_js reads real instance IDs, not names/counts or a passed flag.
const L=await import(globalThis.CFG.lib);
const P=await import(new URL('phone.mjs',globalThis.CFG.lib).href);
const G=await import(new URL('gates.mjs',globalThis.CFG.lib).href);
const routes=L.A.modal_lifecycle;
await L.suite(async({out,page})=>{
  if(!Array.isArray(routes)||!routes.length)throw Error('modal_lifecycle needs actual route inventory; omit the suite for a game with no modal UI');
  const trace=[];out.evidence.trace=L.evidence('modal-lifecycle-trace.json',trace);
  const ids=new Set();
  for(const r of routes){
    if(!r||!/^[A-Za-z0-9_-]+$/.test(r.id)||ids.has(r.id)||!r.open||!r.close||typeof r.state_js!=='string'||typeof r.async_open!=='boolean'||(r.async_open&&!r.slow_query)||(r.cancel&&!r.async_open))throw Error('invalid modal route: id/open/close/state_js/async_open required; async routes also need slow_query');
    ids.add(r.id);
    const device=r.device||'iphone14';if(!G.DEVICES[device])throw Error('unsupported modal device '+device);
    const scenarios=['normal','burst',...(r.async_open?['slow_burst']:[]),...(r.cancel?['cancel_late']:[])];
    for(const scenario of scenarios){
      const id=r.id+'/'+scenario;if(L.C.selection&&!L.C.selection.includes('@suite')&&!L.C.selection.includes(id))continue;
      const row={id,steps:[]};trace.push(row);
      const write=()=>L.evidence('modal-lifecycle-trace.json',trace);
      const record=async phase=>{
        const s=await P.js(page,r.state_js);
        for(const field of ['views','blockers'])if(!Array.isArray(s?.[field])||s[field].some(x=>typeof x!=='string'||!x)||new Set(s[field]).size!==s[field].length)throw Error(field+' must be the real distinct active instance IDs');
        row.steps.push({phase,state:s,at:Date.now()});write();return s;
      };
      const waitState=async(predicate,label)=>{
        const end=Date.now()+(r.ready_timeout_ms||10000);let s;
        do{s=await P.js(page,r.state_js);if(predicate(s))return s;await L.sleep(60);}while(Date.now()<end);
        throw Error(label+' not reached: '+JSON.stringify(s));
      };
      const tap=async(spec,label)=>{
        const at=await P.point(page,spec);if(!at)throw Error('missing real control '+label);
        await G.probeStart(page,label);
        await page.cdp('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{id:1,x:at.x,y:at.y,radiusX:1,radiusY:1,force:1}]});
        await page.cdp('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        const probe=await page.evaluate(()=>window.__bsProbe?.cur||null);await G.probeStop(page);
        row.steps.push({phase:'input',label,at,probe,time:Date.now()});write();
      };
      const clean=s=>Array.isArray(s?.views)&&Array.isArray(s?.blockers)&&s.views.length===0&&s.blockers.length===0;
      try{
        await G.setViewport(page,device);
        const q=[r.query,scenario==='slow_burst'||scenario==='cancel_late'?r.slow_query:''].filter(Boolean).join('&');
        const boot=await L.boot(page,q,{until:L.A.home});if(!boot.ok||boot.errors.length)throw Error('actual Native home not ready: '+JSON.stringify(boot));
        if(r.prepare){const prepared=await P.steps(page,r.prepare);if(!prepared.ok)throw Error('route preparation failed');}
        await G.installProbe(page);
        if(!clean(await record('before')))throw Error('route starts with an existing view/blocker; fix preparation');
        await tap(r.open,'open');
        if(scenario==='cancel_late'){
          await record('pending');await tap(r.cancel,'cancel-pending');
          // Adapter must observe the actual task completion, not a made-up sleep or a manually written result.
          if(typeof r.settled_js!=='string')throw Error('cancel_late needs settled_js for actual completion/idle');
          const settled=await L.waitFor(page,r.settled_js,r.ready_timeout_ms||10000,60);if(!settled.ok)throw Error('cancelled task did not settle');
          if(!clean(await record('late-completion')))throw Error('cancelled UI revived a view or blocker');
        }else{
          if(scenario!=='normal'){
            await L.sleep(r.burst_gap_ms??180);
            if(scenario==='slow_burst'){
              const pending=await record('before-second-open');
              if(pending.views.length!==0)throw Error('slow async window was not reached; this case is untested, not passed');
            }
            await tap(r.open,'repeat-open');
          }
          await waitState(s=>s?.views?.length>0,'visible modal');
          // settled_js closes the race with a second request still pending. Without it a warm-only check is invalid.
          if(typeof r.settled_js!=='string')throw Error('modal route needs settled_js to observe all relevant requests finished');
          if(!(await L.waitFor(page,r.settled_js,r.ready_timeout_ms||10000,60)).ok)throw Error('modal requests did not settle');
          let s=await record('ready');
          if(!r.allow_multiple&&s.views.length!==1)throw Error('singleton route created '+s.views.length+' live instances');
          const limit=s.views.length;if(limit>8)throw Error('unbounded modal instances');
          for(let i=0;i<limit;i++){
            const previous=s.views.length;await tap(r.close,'close-visible');
            s=await waitState(x=>Array.isArray(x?.views)&&x.views.length===previous-1,'one modal close');await record('closed-one');
          }
          if(!clean(await record('closed-all')))throw Error('orphan blocker remains after closing all views');
        }
        // Same running game, no navigation/reload hiding a blocker leak.
        await tap(r.open,'reopen');await waitState(s=>s?.views?.length===1,'reopened view');
        if(!(await L.waitFor(page,r.settled_js,r.ready_timeout_ms||10000,60)).ok)throw Error('reopen requests did not settle');
        const reopened=await record('reopened');if(reopened.views.length!==1)throw Error('reopen created multiple views');
        await tap(r.close,'close-reopened');await waitState(clean,'final clean state');await record('final');
        out.add(id,true,{trace:out.evidence.trace,scope:'real Native host touch; not physical-device acceptance'});
      }catch(e){row.error=String(e?.message||e);write();out.add(id,false,{error:row.error,trace:out.evidence.trace});}
    }
  }
});
