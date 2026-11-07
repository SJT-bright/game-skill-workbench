// Capture actual Web pixels on a private, immutable loopback origin. No offline "stamp this PNG" command.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {createHash, randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const sha = b => createHash('sha256').update(b).digest('hex');
const digest = o => sha(JSON.stringify(o));
const read = f => JSON.parse(fs.readFileSync(f));
const write = (f,o) => {
  fs.mkdirSync(path.dirname(f),{recursive:true});
  const tmp = f+'.'+randomUUID();
  fs.writeFileSync(tmp,JSON.stringify(o,null,2)); fs.renameSync(tmp,f);
};
const safeId = s => typeof s==='string' && /^[A-Za-z0-9_.-]+$/.test(s) && s!=='.' && s!=='..';
const isImage = f => /\.(?:png|jpe?g)$/i.test(f);
function notReady(detail,message) {
  return Object.assign(new Error(message),{code:'capture_not_ready',reason_code:'capture_not_ready',
    detail_code:detail,next_action:'recapture_current_case'});
}
function witnessSpec(w) {
  if(!w||typeof w.path!=='string'||!w.path.trim()||
     ('count' in w&&(!Number.isInteger(w.count)||w.count<=0))||
     ['frame','font','font_kind'].some(k=>k in w&&(typeof w[k]!=='string'||!w[k].trim()))||
     ('text' in w&&typeof w.text!=='string')||
     ('require_font_metrics' in w&&typeof w.require_font_metrics!=='boolean')||
     (w.require_font_metrics===true&&w.font_kind!=='bitmap'))
    throw notReady('invalid_witness','invalid state witness: '+(w?.path||'<missing path>'));
}
// This checks only the explicitly requested state, never infers a price or visual pass from a path.
export function validateWitnesses(nodes,state) {
  if(!Array.isArray(nodes)||!nodes.length||!Array.isArray(state?.witness)||!state.witness.length)
    throw notReady('missing_witness','required state witness missing: '+(state?.id||'<unknown>'));
  return state.witness.map(w=>{
    witnessSpec(w);
    const atPath=nodes.filter(n=>n?.path===w.path);
    if(!('count' in w)&&atPath.length>1)
      throw notReady('ambiguous_witness','state witness path is ambiguous; declare count: '+w.path);
    const matches=atPath.filter(n=>{
      const label=n.comps?.label||n.comps?.richtext;
      return n.active!==false && !(typeof n.opacity==='number'&&n.opacity<=0) &&
        (!('text' in w)||label?.string===w.text) &&
        (!('frame' in w)||n.comps?.sprite?.frame===w.frame) &&
        (!('font' in w)||label?.font===w.font) &&
        (!('font_kind' in w)||label?.font_kind===w.font_kind);
    });
    if(matches.length!==(w.count??1))
      throw notReady(matches.length>(w.count??1)?'ambiguous_witness':'missing_witness',
        'required state witness missing, hidden or mismatched: '+w.path);
    return matches.map(n=>{
      const label=n.comps?.label||n.comps?.richtext,sprite=n.comps?.sprite;
      if('frame' in w&&(!Array.isArray(sprite.frame_size)||sprite.frame_size.length!==2||
         !sprite.frame_size.every(x=>Number.isFinite(x)&&x>0)))
        throw notReady('frame_not_loaded','state witness frame has no loaded positive dimensions: '+w.path);
      if(w.require_font_metrics===true&&(typeof label?.font!=='string'||!label.font.trim()||
         label.text_metric!=='fnt'||!Number.isFinite(label.text_w)||label.text_w<=0))
        throw notReady('font_metrics_not_ready','state witness bitmap font metrics are not ready: '+w.path);
      // Include requested observations in the same-frame comparison, without asserting all glyphs loaded.
      return [n.id,n.path,n.screen||n.rect,label?.string,sprite?.frame,
        ...('frame' in w?[sprite.frame_size]:[]),
        ...(('font' in w||'font_kind' in w||w.require_font_metrics)?[label?.font,label?.font_kind]:[]),
        ...(w.require_font_metrics?[label.text_metric,label.text_w]:[])];
    });
  });
}
function files(root, dirs=['.']) {
  const result={};
  function walk(rel) {
    const full=path.join(root,rel);
    const stat=fs.lstatSync(full);
    if(stat.isSymbolicLink()) throw Error('untracked symbolic link: '+rel);
    if(stat.isFile()){result[rel]=sha(fs.readFileSync(full));return;}
    if(!stat.isDirectory()) throw Error('unsupported file: '+rel);
    for(const ent of fs.readdirSync(full).sort()){
      if(['.DS_Store','.git','__MACOSX'].includes(ent)||ent.startsWith('._'))continue;
      walk(path.posix.join(rel,ent));
    }
  }
  for(const dir of dirs)if(fs.existsSync(path.join(root,dir)))walk(dir);
  return result;
}
const diff=(a,b)=>[...new Set([...Object.keys(a),...Object.keys(b)])].filter(k=>a[k]!==b[k]);
function context(project,build) {
  project=fs.realpathSync(project);build=fs.realpathSync(build);
  if(!fs.existsSync(path.join(project,'assets'))||!fs.existsSync(path.join(build,'index.html')))
    throw Error('expected the Cocos project and its actual Web export');
  const policy=read(path.join(project,'docs/art/capture-plan.json'));
  if(!Array.isArray(policy.cases)||!policy.cases.length)throw Error('nonempty capture-plan cases required');
  const ids=new Set();
  for(const c of policy.cases){
    if(!safeId(c.id)||ids.has(c.id)||!c.screen||!c.kind||typeof c.stable!=='boolean'||
      typeof c.recipe!=='string'||!c.recipe.trim()||typeof c.environment!=='string'||!c.environment.trim()||![c.width,c.height].every(v=>Number.isInteger(v)&&v>0)||
      !Number.isFinite(c.dpr)||c.dpr<=0||!Array.isArray(c.witness)||!c.witness.length||c.witness.some(w=>!w||typeof w.path!=='string'||!w.path))throw Error('invalid or duplicate case '+c.id);
    if(c.storageSha!==undefined && !/^[a-f0-9]{64}$/.test(c.storageSha))throw Error('invalid storageSha: '+c.id);
    c.witness.forEach(witnessSpec);
    ids.add(c.id);
  }
  const store=path.join(project,'.tiktok-kit/art-rounds');
  const snapshot={project,build,exported:files(build),source:files(project,['assets','settings','extensions','package.json','tsconfig.json','profiles']),
    policy:digest(policy), collector:sha(Buffer.concat([fs.readFileSync(fileURLToPath(import.meta.url)),
      fs.readFileSync(new URL('./ui_dump.js',import.meta.url))]))};
  const version=digest(snapshot);
  return {project,build,policy,store,snapshot,version,loaded:new Map()};
}
function loadSnapshot(c,id) {
  if(!/^[a-f0-9]{64}$/.test(id))throw Error('bad snapshot id');
  if(c.loaded.has(id))return c.loaded.get(id);
  const snap=read(path.join(c.store,'snapshots',id+'.json'));
  if(digest(snap)!==id||snap.project!==c.project||snap.build!==c.build)throw Error('snapshot does not match');
  c.loaded.set(id,snap);return snap;
}
const active=c=>read(path.join(c.store,'current.json'));
const byId=(c,id)=>{const v=c.policy.cases.find(x=>x.id===id);if(!v)throw Error('unknown case '+id);return v;};
function status(c) {
  const result={schema:'art_capture_status.v1',read_only:true,
    source_hash:digest(c.snapshot.source),export_hash:digest(c.snapshot.exported),
    matrix_hash:c.snapshot.policy,collector_hash:c.snapshot.collector,
    current_round:null,current_round_version:null,
    changes:{source:null,export:null,matrix:null,collector:null},changed_files:{source:[],export:[]},
    suggested_action:'unknown',reason_code:'no_previous_round'};
  let previous;
  try {
    const round=active(c);
    result.current_round=round.id;result.current_round_version=round.version;
    previous=loadSnapshot(c,round.version);
  }catch(e){
    if(e.code!=='ENOENT')throw e;
    if(result.current_round!==null)result.reason_code='previous_snapshot_missing';
    return result;
  }
  const source=diff(previous.source,c.snapshot.source),exported=diff(previous.exported,c.snapshot.exported);
  result.changed_files={source,export:exported};
  result.changes={source:!!source.length,export:!!exported.length,
    matrix:previous.policy!==c.snapshot.policy,collector:previous.collector!==c.snapshot.collector};
  if(source.length&&!exported.length){
    result.suggested_action='rebuild_web';result.reason_code='source_changed_export_unchanged';
  }else if(exported.length){
    result.suggested_action='verify_export_then_new_round';result.reason_code='export_changed';
  }else if(result.changes.matrix||result.changes.collector){
    result.suggested_action='new_round';result.reason_code='capture_inputs_changed';
  }else{
    result.suggested_action='keep_round';result.reason_code='identities_unchanged';
  }
  return result;
}
export function captureStatus({project,build}) { return status(context(project,build)); }
function checkRound(c) {
  const r=active(c);
  if(r.version!==c.version)throw Error('export, source, matrix or collector changed; start a new round');
  return r;
}
function begin(c) {
  const current=path.join(c.store,'current.json');
  if(fs.existsSync(current)){
    const previous=loadSnapshot(c,active(c).version);
    if(diff(previous.source,c.snapshot.source).length && !diff(previous.exported,c.snapshot.exported).length)
      throw Error('source changed but export is still byte-identical: rebuild and verify the actual Web export');
  }
  write(path.join(c.store,'snapshots',c.version+'.json'),c.snapshot);
  const r={id:randomUUID(),version:c.version};write(path.join(c.store,'current.json'),r);return r;
}
function loadProof(c,folder,id) {
  const dumpFile=path.join(folder,'capture-ui-dump-'+id+'.json');
  const bytes=fs.readFileSync(dumpFile), dump=JSON.parse(bytes);
  if(!safeId(dump.art_capture_id))throw Error('no capture-time evidence');
  const proof=read(path.join(c.store,'proofs',dump.art_capture_id+'.json'));
  const state=byId(c,id);
  const {seal,...fields}=proof;
  if(seal!==digest(fields))throw Error('capture provenance changed');
  if(proof.id!==dump.art_capture_id || proof.caseHash!==digest(state) || proof.case!==id ||
     proof.dump!==sha(bytes) || dump.screen!==state.screen || dump.kind!==state.kind ||
     dump.viewport.width!==state.width || dump.viewport.height!==state.height ||
     dump.screenshot!==id+'.png'||proof.png!==sha(fs.readFileSync(path.join(folder,dump.screenshot))))
    throw Error('state, viewport, dump or PNG changed');
  loadSnapshot(c,proof.version);
  return proof;
}
function changes(c,old) {
  const e=diff(c.snapshot.exported,old.exported);
  const s=diff(c.snapshot.source,old.source);
  // Only replacements of existing independent native bitmap files are local. New files, deletions,
  // imports/atlas layout, scripts, shaders, fonts or settings require a full recapture.
  const local=f=>isImage(f)&&f in old.exported&&f in c.snapshot.exported;
  if(old.collector!==c.snapshot.collector||old.policy!==c.snapshot.policy||e.some(f=>!local(f)))
    return {global:'shared code, layout, inventory, recipe or environment changed',e};
  for(const f of s){
    if(!isImage(f)||!old.source[f]||!c.snapshot.source[f]||!e.some(output=>
      old.exported[output]===old.source[f]&&c.snapshot.exported[output]===c.snapshot.source[f]))
      return {global:'source change not mapped byte-for-byte to a changed export image: '+f,e};
  }
  return {global:null,e};
}
function classify(c,r,folder,state,anchor) {
  try{
    const proof=loadProof(c,folder,state.id);
    if(proof.round===r.id && proof.version===c.version)return {action:'fresh',origin:proof.id};
    if(!state.stable||state.kind==='gameplay'||state.id===anchor.id)throw Error('dynamic state or current-round viewport anchor');
    confirmCurrentFixture(state,proof,anchor);
    if(proof.auxiliary)throw Error('specialized evidence must be captured with its bound attachments');
    if(anchor.env && anchor.env!==proof.env)throw Error('browser environment changed');
    const reviewed=read(path.join(c.store,'reviews',proof.id+'.json'));
    if(reviewed.origin!==proof.id||reviewed.dump!==proof.dump||reviewed.png!==proof.png||!reviewed.stability)
      throw Error('previous evidence not reviewed');
    const stability=read(path.join(c.store,'proofs',reviewed.stability+'.json'));
    const {seal:stabilitySeal,...stabilityFields}=stability;
    if(stabilitySeal!==digest(stabilityFields))throw Error('stability proof changed');
    confirmStability(proof,stability,state);
    const delta=changes(c,loadSnapshot(c,proof.version));
    if(delta.global)throw Error(delta.global);
    const hits=delta.e.filter(f=>proof.reads.includes(f));
    if(hits.length)throw Error('changed image loaded by this state: '+hits.join(', '));
    return {action:'reuse',origin:proof.id,originVersion:proof.version,currentVersion:c.version};
  }catch(err){return {action:'recapture',reason:err.code==='ENOENT'?'missing capture or review record':err.message};}
}
function plan(c,folder) {
  const r=checkRound(c), groups=new Map();
  const key=s=>[s.width,s.height,s.dpr].join('/');
  for(const state of c.policy.cases){
    const k=key(state);
    if(!groups.has(k)||state.anchor)groups.set(k,state);
  }
  const anchors=new Map();
  for(const [key,state] of groups){
    let env=null,storage=null;
    try{const proof=loadProof(c,folder,state.id);if(proof.round===r.id&&proof.version===c.version){env=proof.env;storage=proof.storage;}}catch{}
    anchors.set(key,{id:state.id,env,storage});
  }
  const cases=c.policy.cases.map(s=>({id:s.id,screen:s.screen,viewport:[s.width,s.height,s.dpr],...classify(c,r,folder,s,anchors.get(key(s)))}));
  const missingAnchors=[...anchors.values()].filter(a=>!a.env).map(a=>a.id);
  return {round:r.id,version:c.version,cases,missingAnchors,ready:!missingAnchors.length&&cases.every(x=>x.action!=='recapture')};
}
export function confirmCurrentFixture(state,proof,anchor) {
  if(!state.storageSha||!proof.storage?.supported||proof.storage.sha256!==state.storageSha||
     !anchor.env||!anchor.storage?.supported||anchor.storage.sha256!==state.storageSha)
    throw Error('current viewport anchor does not confirm this controlled storage fixture');
  if(!Array.isArray(state.externalInputs)||state.externalInputs.length)
    throw Error('external or unknown time/random/network state must be freshly captured');
}
export function confirmStability(first,second,state) {
  if(!state.stable||state.kind==='gameplay'||!Array.isArray(state.externalInputs)||state.externalInputs.length||!state.storageSha||
     !first.storage?.supported||!second.storage?.supported||
     first.storage.sha256!==state.storageSha||second.storage.sha256!==state.storageSha)
    throw Error('controlled storage fixture missing or changed');
  if(!first.session||!second.session||first.session===second.session||
     !Number.isFinite(first.timeOrigin)||!Number.isFinite(second.timeOrigin)||first.timeOrigin===second.timeOrigin)
    throw Error('stability needs two independent real page arrivals');
  if(first.id===second.id||first.case!==second.case||first.caseHash!==second.caseHash||
     first.round!==second.round||first.version!==second.version||first.env!==second.env||
     first.png!==second.png||first.auxiliary||second.auxiliary)
    throw Error('independent full-page pixels, state or environment differ');
  // The conservative union includes both independent arrival paths and preloads.
  if(JSON.stringify(first.reads)!==JSON.stringify(second.reads))
    throw Error('independent arrival dependencies differ');
}
function evidenceReview(c,folder,id,reportFile,stabilityFolder) {
  const r=checkRound(c),v=loadProof(c,folder,id),state=byId(c,id);
  if(v.round!==r.id||v.version!==c.version)throw Error('review must use fresh capture in its originating round');
  const report=read(reportFile);
  if(report.tool!=='art_check'||report.passed!==true||!report.capture_round?.ready||
     report.capture_round.round!==r.id||!report.capture_round.cases.some(x=>x.id===id&&x.action==='fresh'&&x.origin===v.id))
    throw Error('a passing full art report must cover this fresh state');
  if(!stabilityFolder)throw Error('review for reuse needs a second independently captured directory');
  const second=loadProof(c,path.resolve(stabilityFolder),id);
  confirmStability(v,second,state);
  write(path.join(c.store,'reviews',v.id+'.json'),{origin:v.id,dump:v.dump,png:v.png,stability:second.id});
}

const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.wasm':'application/wasm','.webp':'image/webp','.svg':'image/svg+xml','.woff2':'font/woff2'};
export async function openCapture({project,build,out}) {
  const c=context(project,build),r=checkRound(c), token=randomUUID(),reads=new Set();
  const captureOut=path.resolve(out);
  const htmlMeta='<meta name="art-capture-session" content="'+token+'">';
  // Each instance owns a private origin. A random port does NOT guarantee empty browser storage. Keep its cumulative served set (including resources fetched
  // while reaching the state). False positives cost a recapture; narrowing this to visible sprites would miss atlases.
  let invalid=null;
  const server=http.createServer((req,res)=>{
    try{
      const url=new URL(req.url,'http://localhost'),key=decodeURIComponent(url.pathname).slice(1)||'index.html';
      if(!Object.hasOwn(c.snapshot.exported,key)){res.writeHead(404);res.end();return;}
      const bytes=fs.readFileSync(path.join(c.build,key));
      if(sha(bytes)!==c.snapshot.exported[key])throw Error('export changed while serving '+key);
      reads.add(key);
      const html=key==='index.html';
      res.writeHead(200,{'Content-Type':mime[path.extname(key)]||'application/octet-stream','Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; connect-src 'self' data: blob:; frame-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'self'"});
      if(html && !/<head(?:\s[^>]*)?>/i.test(bytes.toString()))throw Error('missing HTML head');
      res.end(html?bytes.toString().replace(/<head(?:\s[^>]*)?>/i,s=>s+htmlMeta):bytes);
    }catch(e){invalid=e.message;res.destroy();}
  });
  await new Promise((ok,fail)=>{server.once('error',fail);server.listen(0,'127.0.0.1',ok);});
  const url='http://127.0.0.1:'+server.address().port+'/';
  const expr=async(page,expression)=>{
    const x=await page.cdp('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(x.exceptionDetails)throw Error(x.exceptionDetails.text);
    return x.result.value;
  };
  const live=page=>expr(page,`({origin:location.origin,token:document.querySelector('meta[name="art-capture-session"]')?.content,t:performance.timeOrigin,w:innerWidth,h:innerHeight,dpr:devicePixelRatio,sw:!!navigator.serviceWorker?.controller,ua:navigator.userAgent,lang:navigator.language,tz:Intl.DateTimeFormat().resolvedOptions().timeZone})`);
  const storage=async page=>{
    try {
      const data=await expr(page,`(async()=>{
        const entries=s=>Object.keys(s).sort().map(k=>[k,s.getItem(k)]);
        const dbs=typeof indexedDB.databases==='function'?await indexedDB.databases():null;
        return {local:entries(localStorage),session:entries(sessionStorage),cookie:document.cookie,
          supported:Array.isArray(dbs)&&dbs.length===0};
      })()`);
      // Never save or print storage values; only a fingerprint of this project's origin.
      return {supported:data.supported,sha256:digest(data)};
    }catch{return {supported:false,sha256:null};}
  };
  return {
    url,
    async navigate(page){
      await page.cdp('Network.enable',{});
      await page.cdp('Network.setCacheDisabled',{cacheDisabled:true});
      await page.cdp('Network.setBypassServiceWorker',{bypass:true});
      await page.goto(url);
    },
    async capture(page,id,{dumpExpression,purpose}={}){
      const state=byId(c,id),before=await live(page);
      if(before.token!==token||before.origin+'/'!==url||before.sw||before.w!==state.width||
         before.h!==state.height||before.dpr!==state.dpr)throw Error('wrong live build, viewport, DPR or worker');
      const expression=dumpExpression||'('+fs.readFileSync(new URL('./ui_dump.js',import.meta.url),'utf8')+')({maxNodes:8000})';
      if((dumpExpression||state.adapterSha) && (!dumpExpression||sha(Buffer.from(dumpExpression))!==state.adapterSha))throw Error('registered collector missing or changed');
      const storageBefore=await storage(page);
      const dump=await expr(page,expression);
      if(!Array.isArray(dump?.nodes)||!dump.nodes.length||dump.error||dump.truncated)
        throw notReady('incomplete_dump','incomplete live dump');
      const seen=validateWitnesses(dump.nodes,state);
      const px=await page.cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      const png=Buffer.from(px.data,'base64'),after=await live(page);
      const again=await expr(page,expression);
      if(again?.error||again?.truncated)throw notReady('incomplete_dump','incomplete live dump after capture');
      const seenAfter=validateWitnesses(again?.nodes,state);
      if(digest(seen)!==digest(seenAfter))throw notReady('witness_changed','state witness changed during capture: '+id);
      if(invalid||digest(before)!==digest(after)||!reads.has('index.html')||
         png.readUInt32BE(16)!==Math.round(state.width*state.dpr)||png.readUInt32BE(20)!==Math.round(state.height*state.dpr)||
         png.toString('hex',0,8)!=='89504e470d0a1a0a')throw Error(invalid||'capture context changed');
      const storageAfter=await storage(page);
      const storageEvidence=digest(storageBefore)===digest(storageAfter)?storageBefore:{supported:false,sha256:null};
      const proofId=randomUUID(), file='capture-ui-dump-'+id+'.json',shot=id+'.png';
      const bytes=Buffer.from(JSON.stringify({...dump,screen:state.screen,kind:state.kind,viewport:{width:state.width,height:state.height},
        purpose:state.purpose||purpose||dump.purpose||'other',screenshot:shot,screenshot_sha256:sha(png),art_capture_id:proofId},null,2));
      fs.mkdirSync(out,{recursive:true});
      if(fs.existsSync(path.join(out,file))||fs.existsSync(path.join(out,shot)))throw Error('capture exists; use a fresh folder');
      // Reject overwrites: a partial attempt cannot replace reviewed evidence.
      fs.writeFileSync(path.join(out,shot),png,{flag:'wx'});
      try{fs.writeFileSync(path.join(out,file),bytes,{flag:'wx'});}catch(e){fs.unlinkSync(path.join(out,shot));throw e;}
      const proof={id:proofId,case:id,caseHash:digest(state),version:c.version,
        round:r.id,session:token,timeOrigin:before.t,storage:storageEvidence,env:digest([before.ua,before.lang,before.tz,before.dpr]),auxiliary:Object.entries(dump).some(([k,v])=>{
          if(k==='render_observation' && v?.before?.schema==='render-observation.v1' && v?.after?.schema==='render-observation.v1' && !/\.(?:png|json|webm|mp4|jpe?g)(?:[?#][^"]*)?"/i.test(JSON.stringify(v)))return false;
          return /(?:report|recording|observation|attachment)/i.test(k);
        }),dump:sha(bytes),png:sha(png),reads:[...reads].sort()};
      try{write(path.join(c.store,'proofs',proofId+'.json'),{...proof,seal:digest(proof)});}catch(e){fs.unlinkSync(path.join(out,file));fs.unlinkSync(path.join(out,shot));throw e;}
      return path.join(captureOut,file);
    },
    async close(){server.closeAllConnections?.();await new Promise(done=>server.close(done));}
  };
}
if(process.argv[1] && fs.existsSync(process.argv[1]) && fs.realpathSync(process.argv[1])===fs.realpathSync(fileURLToPath(import.meta.url))){
  try{
    const [cmd,proj,build,folder,arg]=process.argv.slice(2);
    if(!['start','plan','verify','review','identity','status'].includes(cmd))throw Error('use start|plan|verify|review|identity|status PROJECT BUILD [DUMPS] [CASE]');
    const c=context(proj,build);
    if(cmd==='status')console.log(JSON.stringify(status(c)));
    else if(cmd==='identity')console.log(JSON.stringify(checkRound(c)));
    else if(cmd==='start')console.log(JSON.stringify(begin(c)));
    else if(cmd==='review')evidenceReview(c,path.resolve(folder),arg,process.argv[7],process.argv[8]);
    else {
      const report=plan(c,path.resolve(folder));
      if(cmd==='verify'){
        const expected=new Set(c.policy.cases.map(s=>'capture-ui-dump-'+s.id+'.json'));
        function walk(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){
          const f=path.join(dir,ent.name);
          if(ent.isSymbolicLink())throw Error('symlink in capture directory');
          if(ent.isDirectory())walk(f);
          else if(ent.name.includes('ui-dump-')&&ent.name.endsWith('.json')&&!expected.has(path.relative(folder,f)))throw Error('unregistered dump '+ent.name);
        }}
        walk(path.resolve(folder));
      }
      console.log(JSON.stringify(report,null,2));
      if(cmd==='verify'&&!report.ready)process.exitCode=1;
    }
  }catch(e){
    console.log(JSON.stringify({error:e.message,reason_code:e.reason_code||'capture_command_failed',
      ...(e.detail_code?{detail_code:e.detail_code}:{}),...(e.next_action?{next_action:e.next_action}:{})}));
    console.error(e.message);process.exitCode=2;
  }
}
