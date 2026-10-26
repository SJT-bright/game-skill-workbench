/* Passive QA observer. Never dispatch input, call game code, or change storage. */
(() => {
  'use strict';
  let seq=0, queue=[], movesAt=0, touchCount=0, mouseCount=0, badge;
  const rect = el => {const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,pixelWidth:el.width,pixelHeight:el.height};};
  const environment = () => ({viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,maxTouchPoints:navigator.maxTouchPoints,userAgent:navigator.userAgent,visibility:document.visibilityState,canvases:Array.from(document.querySelectorAll('canvas')).map(rect)});
  const touch = t => ({id:t.identifier,clientX:t.clientX,clientY:t.clientY,screenX:t.screenX,screenY:t.screenY});
  const record = (type,data={}) => {
    if (seq>=12000) return;
    queue.push({seq:++seq,type,at:new Date().toISOString(),elapsedMs:performance.now(),...data,environment:environment()});
    if (!badge && document.body) {
      badge=document.createElement('div');badge.id='mobile-cua-qa-badge';
      badge.style.cssText='position:fixed;right:2px;top:2px;z-index:2147483647;pointer-events:none;padding:2px 4px;font:9px monospace;color:white;background:rgba(18,46,85,.8);';
      document.body.appendChild(badge);
    }
    if (badge) badge.textContent=`QA ${innerWidth}x${innerHeight} DPR${devicePixelRatio} T${touchCount} M${mouseCount}`;
  };
  const flush = () => {
    if (!queue.length) return;
    const batch=queue.splice(0,48);
    fetch('/__mobile_cua_events__',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(batch),keepalive:true}).catch(()=>{queue=batch.concat(queue).slice(0,1000);});
  };
  ['touchstart','touchmove','touchend','touchcancel','pointerdown','pointermove','pointerup','pointercancel','mousedown','mouseup','click'].forEach(type=>{
    window.addEventListener(type,event=>{
      if (type==='pointermove'&&!event.buttons) return;
      if (type.endsWith('move')) {const now=performance.now();if(now-movesAt<40)return;movesAt=now;}
      if(type==='touchstart')touchCount++;if(type==='mousedown')mouseCount++;
      record(type,{isTrusted:event.isTrusted,targetTag:event.target?.tagName,targetId:event.target?.id,pointerType:event.pointerType,pointerId:event.pointerId,buttons:event.buttons,clientX:event.clientX,clientY:event.clientY,screenX:event.screenX,screenY:event.screenY,touches:event.touches?Array.from(event.touches).map(touch):undefined,changedTouches:event.changedTouches?Array.from(event.changedTouches).map(touch):undefined});
    },{capture:true,passive:true});
  });
  window.addEventListener('resize',()=>record('resize'),{passive:true});
  document.addEventListener('visibilitychange',()=>record('visibilitychange'),{passive:true});
  window.addEventListener('error',e=>record('error',{message:e.message,filename:e.filename,line:e.lineno,column:e.colno}),{passive:true});
  window.addEventListener('unhandledrejection',e=>record('unhandledrejection',{message:String(e.reason)}),{passive:true});
  document.addEventListener('DOMContentLoaded',()=>record('ready'),{once:true});
  window.addEventListener('pagehide',flush,{passive:true});
  setInterval(flush,250);record('observer-start');
})();
