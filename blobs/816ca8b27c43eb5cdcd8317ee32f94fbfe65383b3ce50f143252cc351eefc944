// Run only through the official ego-browser nodejs runtime. No game-state writes.
const CFG = __PREVIEW_MOUSE_CONFIG__;
const fs = await import('node:fs/promises');
const task = await taskSpace(CFG.space_name);
const page = task.page('p1');
let result = {schema:'preview_mouse_observation.v1',passed:false,browser_route:'ego_taskspace',input_transport:'ego_page_mouse',space_id:task.spaceId,url:CFG.url};
let failure;
try {
 await page.cdp('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{const log=window.__previewRealMouse={down:0,up:0,move:0,touchStart:0,touchEnd:0,lastTarget:null};const add=EventTarget.prototype.addEventListener;for(const [t,k] of [['mousedown','down'],['mouseup','up'],['mousemove','move']])add.call(window,t,e=>{if(e.isTrusted){log[k]++;log.lastTarget=e.target?.tagName}},{capture:true,passive:true});for(const [t,k] of [['touchstart','touchStart'],['touchend','touchEnd']])add.call(window,t,e=>log[k]++,{capture:true,passive:true});})();`});
 await page.goto(CFG.url);
 async function read(expression) {return page.evaluate(expr=>{const w=document.querySelector('#phone-game')?.contentWindow||window;return Function('cc','window','document','return ('+expr+');')(w.cc,w,w.document)},expression);}
 const deadline=Date.now()+CFG.timeout_ms;
 async function until(expression){while(Date.now()<deadline){if(await read(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Expected game state did not appear: '+expression);}
 async function point(action){if(action.node)return page.evaluate(path=>{const frame=document.querySelector('#phone-game'),w=frame?.contentWindow||window,n=w.cc.find(path);if(!n||!n.activeInHierarchy)throw Error('Mouse target is not visible: '+path);const p=n.convertToWorldSpaceAR(w.cc.v2(0,0)),r=(frame?frame.contentDocument:document).querySelector('canvas').getBoundingClientRect(),v=w.cc.view.getVisibleSize(),o=w.cc.view.getVisibleOrigin(),f=frame?.getBoundingClientRect();const sx=f?f.width/frame.clientWidth:1,sy=f?f.height/frame.clientHeight:1;return{x:(f?.left||0)+(r.left+(p.x-o.x)*r.width/v.width)*sx,y:(f?.top||0)+(r.top+(1-(p.y-o.y)/v.height)*r.height)*sy}},action.node);return{x:action.click[0],y:action.click[1]};}
 async function mouse(action){if(action.drag){const [a,b]=action.drag;await page.mouse.move(a[0],a[1],{label:'Position real mouse for drag'});await page.mouse.down();await page.mouse.move(b[0],b[1],{label:'Drag real mouse in game'});await page.mouse.up();}else{const p=await point(action);(result.mouse_targets??=[]).push(p);await page.mouse.move(p.x,p.y,{label:'Position real mouse on control'});await page.mouse.down();await new Promise(r=>setTimeout(r,80));await page.mouse.up();}}
 await until(CFG.plan.ready);
 if(await read(CFG.plan.started))throw Error('Fresh check origin already reports gameplay before start input');
 // Readiness must include finished entrance animations/bindings; the plan owns that predicate.
 await mouse(CFG.plan.start);
 await until(CFG.plan.started);
 result.started=true;
 const before=await read(CFG.plan.operation_state);
 for(const action of CFG.plan.operations){await mouse(action);if(action.wait_ms)await new Promise(r=>setTimeout(r,action.wait_ms));}
 let after;
 while(Date.now()<deadline){after=await read(CFG.plan.operation_state);if(JSON.stringify(before)!==JSON.stringify(after)&&await read(CFG.plan.operation_ok))break;await new Promise(r=>setTimeout(r,50));}
 if(JSON.stringify(before)===JSON.stringify(after)||!await read(CFG.plan.operation_ok))throw Error('Mouse operation caused no verified gameplay result');
 const input=await page.evaluate(()=>{const w=document.querySelector('#phone-game')?.contentWindow||window;return w.__previewRealMouse});
 if(!input||input.down<2||input.up<2)throw Error('Missing trusted browser mouse input for both start and gameplay');
 await page.screenshot({path:CFG.screenshot});
 result={...result,passed:true,before,after,input,screenshot:CFG.screenshot};
} catch(e) {failure=e;result.error=String(e);try{await page.screenshot({path:CFG.screenshot});result.input=await page.evaluate(()=>{const w=document.querySelector('#phone-game')?.contentWindow||window;return w.__previewRealMouse})}catch(_){} }
if(!failure||!/control|hand.?off|inactive|unassigned|hard.?stop/i.test(String(failure))){try{await task.finish({keep:[]});result.space_closed=!(await listTaskSpaces()).some(s=>(s.id??s.spaceId)===task.spaceId)}catch(e){result.passed=false;result.cleanup_error=String(e)}}
if(!result.space_closed)result.passed=false;
await fs.writeFile(CFG.result_file,JSON.stringify(result,null,2));
console.log(JSON.stringify(result));
if(!result.passed)throw Error(result.error||result.cleanup_error||'Mouse validation failed');
