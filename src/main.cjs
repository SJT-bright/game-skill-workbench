const {app,BrowserWindow,ipcMain,dialog,clipboard,shell,Notification,screen,nativeImage,Menu,nativeTheme,powerMonitor}=require('electron');
const fs=require('node:fs/promises');const path=require('node:path');const crypto=require('node:crypto');const {pathToFileURL}=require('node:url');
const {HubStore,ClientStore,startHub,makePrompt,atomicJSON,readJSON,connection,request,addresses}=require('./core.cjs');const {zipFolder}=require('./zip.cjs');
const {discover,queueMessage:codexQueueMessage,STAGES,UUID,cancelReaders,isMaintenanceTitle}=require('./codex.cjs');
const {sendWithReceipt}=require('./send-receipts.cjs');
const {scanTelemetries}=require('./telemetry.cjs');const updater=require('./updater.cjs');const github=require('./github.cjs');const {spawn}=require('node:child_process');
const {dockBounds,EXPANDED,COLLAPSED}=require('./docking.cjs');
const hover=require('./hover.cjs').hoverTrigger();let hoverTimer;
const {SKILL_POLL_MS,APPLICATION_POLL_MS,mergeNotices,notificationBody}=require('./update-notices.cjs');let updateNotices=[],importJob=null;
const smoke=process.argv.includes('--smoke-test');
if(process.platform==='win32')app.setAppUserModelId('studio.gamedesk.skill.personal');
if(process.env.SKILL_DOCK_DATA_DIR)app.setPath('userData',process.env.SKILL_DOCK_DATA_DIR);
else app.setPath('userData',path.join(app.getPath('appData'),'GameDesk-Skill-Personal'));
if(!app.requestSingleInstanceLock())app.exit(0);
app.on('second-instance',()=>{if(win&&!win.isDestroyed()){win.show();win.focus();}});
const root=app.getPath('userData');let config,win,hub,client,store,index={releases:[]},installed={},busy=false,poll,watchTimer,eventAbort,collapsed=true,quitting=false,lastCheck=null,status='未连接同步源',lastError='',syncPromise,publishPromise,watchBusy=false;
let discoverThreads=discover;
let codexSnapshot={threads:[],checkedAt:null,incomplete:false},codexError='',codexBusy=false,codexPromise,localSkillErrors=[],snapTimer,snapping=false,dockEdge='right',sending=new Set(),appUpdate={available:false,busy:false,error:''},updateTimer,downloadedUpdate=null,telemetryCache={};
function queueMessage(threadId,message){
 if(smoke&&process.env.SKILL_DOCK_SMOKE_E2E==='1')return codexQueueMessage(threadId,message,{binary:process.execPath,spawnFn:(binary,args,options)=>spawn(binary,[path.join(root,'queue-receiver.cjs'),...args],{...options,env:{...process.env,ELECTRON_RUN_AS_NODE:'1'}})});
 return codexQueueMessage(threadId,message);
}
const configPath=path.join(root,'settings.json');
const defaults=()=>({games:[],sources:[],url:'',token:'',autoDownload:true,port:47831,hostEnabled:false,hostToken:crypto.randomBytes(24).toString('hex'),window:null,autoCodex:true,repository:'',feedMode:'github',hiddenThreads:[],scanRoots:[],projectRoot:''});
let persistQueue=Promise.resolve();
async function persist(){persistQueue=persistQueue.catch(()=>{}).then(()=>atomicJSON(configPath,config));return persistQueue;}
function notify(title,body){try{if(!smoke&&Notification.isSupported())new Notification({title,body}).show();}catch{console.warn('System notification unavailable; updates remain visible in the workbench');}}
async function state(){return {importJob,updateNotices,games:config.games,sources:config.sources,settings:{projectRoot:config.projectRoot||'',scanRoots:config.scanRoots,url:config.url,autoDownload:config.autoDownload,port:config.port,connected:!!config.url},index,installed,lastCheck,status,lastError,busy,hosting:!!hub,hostUrls:hub?addresses().map(a=>`http://${a}:${hub.port}`):[],localUrl:hub?`http://127.0.0.1:${hub.port}`:'',platform:process.platform,version:app.getVersion(),collapsed,dockEdge,codex:{busy:codexBusy,error:codexError,checkedAt:codexSnapshot.checkedAt,incomplete:codexSnapshot.incomplete},localSkillErrors,appUpdate,repository:config.repository,feedMode:config.feedMode};}
async function emit(){if(win&&!win.isDestroyed())win.webContents.send('dock:state',await state());}
async function sync(){
  if(sending.size)return state();
  if(syncPromise)return syncPromise;
  syncPromise=(async()=>{
    if(!config.url&&!(config.feedMode==='github'&&config.repository))return state();busy=true;lastError='';await emit();
    try{const known=new Set(index.releases.map(r=>r.id));index=await client.sync(config);lastCheck=new Date().toISOString();const latest=new Map();for(const r of index.releases)if(!latest.has(r.skillId))latest.set(r.skillId,r);
      const pins=await readJSON(path.join(root,'pins.json'),{});let changed=[],failed=[];
      for(const r of latest.values())if(config.autoDownload&&!pins[r.skillId]&&installed[r.skillId]?.id!==r.id){try{installed[r.skillId]=await client.install(config,r.id);changed.push(r);}catch{failed.push(r.name);}}
      const updates=[...new Map([...latest.values()].filter(r=>!known.has(r.id)).concat(changed).map(r=>[r.id,r])).values()];if(updates.length){updateNotices=mergeNotices(updateNotices,updates,{installed,pins});await atomicJSON(path.join(root,'update-notices.json'),updateNotices);notify('Skill 更新',notificationBody(updateNotices.filter(n=>updates.some(r=>r.id===n.id))));}
      await require('./skill-archive.cjs').cleanImports(client.root);
      lastError=failed.length?'部分 Skill 待重试：'+failed.join('、'):'';status=failed.length?'部分文件待重试':'已同步 · '+latest.size+' 个 Skill';
    }catch(e){lastError=e.message;status='连接待恢复';}finally{busy=false;await emit();}return state();
  })();try{return await syncPromise;}finally{syncPromise=null;}
}
async function listenEvents(){
  eventAbort?.abort();const own=new AbortController();eventAbort=own;
  if(!config.url||config.feedMode==='github')return;
  try{const c=connection(config),res=await fetch(c.url+'/events',{headers:{Authorization:'Bearer '+c.token},signal:own.signal,redirect:'error'});if(!res.ok)return;let pending='';for await(const chunk of res.body){pending+=Buffer.from(chunk).toString();if(pending.includes('data: changed')){await sync();pending='';}if(pending.length>4096)pending='';}}
  catch(e){if(!own.signal.aborted)console.log('Push disconnected; polling remains active');}finally{own.abort();}
}
async function startSharing(){if(hub)return;hub=await startHub(store,{host:'0.0.0.0',port:config.port,token:config.hostToken});config.hostEnabled=true;await persist();await emit();}
async function publish(id,note=''){
 if(publishPromise)throw Error('正在发布，请稍候');
 publishPromise=(async()=>{const source=config.sources.find(s=>s.id===id);if(!source)throw Error('未找到共享目录');
  if(config.feedMode==='github'&&config.repository&&!hub){const snapshot=await require('./core.cjs').collect(source.path);let result={changed:false,status:'current'};if(source.githubTreeHash!==snapshot.treeHash){result=await require('./publisher.cjs').publishSkill({repository:config.repository,source:source.path,name:source.name,root,note});source.githubTreeHash=snapshot.treeHash;}source.lastPublished=new Date().toISOString();source.lastVersion=result.commit?result.commit.slice(0,7):(source.lastVersion||'已同步');source.error='';await persist();await emit();return {changed:result.changed,github:result,release:{treeHash:snapshot.treeHash,version:source.lastVersion}};}
  const result=await store.publish(source.path,source.name,note);source.lastPublished=new Date().toISOString();source.lastVersion=result.release.version;source.error='';if(config.feedMode==='github'&&config.repository&&source.githubTreeHash!==result.release.treeHash){result.github=await require('./publisher.cjs').publishSkill({repository:config.repository,source:source.path,name:source.name,root,note});source.githubTreeHash=result.release.treeHash;}await persist();if(result.changed){hub?.notify();if(config.url===`http://127.0.0.1:${hub?.port}`)await sync();}await emit();return result;
 })();try{return await publishPromise;}finally{publishPromise=null;}
}
function safeGame(value){const name=String(value.name||'').trim(),location=String(value.path||'').trim(),chat=String(value.chatUrl||'').trim();if(!name||name.length>160||!path.isAbsolute(location))throw Error('请选择游戏目录并填写名称');const threadId=chat.match(/codex:\/\/threads\/([0-9a-f-]{36})/i)?.[1]||value.threadId||'';if(threadId&&!UUID.test(threadId))throw Error('Codex 对话编号无效');const old=config.games.find(g=>g.id===value.id)||{};return {id:value.id||crypto.randomUUID(),name,path:location,stage:STAGES.includes(value.stage)?value.stage:null,stageMode:value.stageMode==='auto'?'auto':'manual',note:String(value.note||'').slice(0,3000),chatUrl:threadId?'codex://threads/'+threadId+'?hostId=local':'',threadId,source:old.source||'manual',workflow:['英化','重塑'].includes(value.workflow)?value.workflow:old.workflow,pinned:old.pinned||false,stageEvidence:old.stageEvidence||'',telemetry:old.threadId===threadId?(old.telemetry||null):null,rolloutPath:old.threadId===threadId?(old.rolloutPath||null):null,updatedAt:new Date().toISOString()};}
let repairQueue=Promise.resolve();
async function repairSkill(skill){const operation=repairQueue.catch(()=>{}).then(async()=>{if(skill.importedFrom)throw Error('导入文件损坏，请重新拖入原始 Skill ZIP');const repaired=await client.install(config,skill.id,{replace:skill.installMode==='replace'});installed[skill.skillId]=repaired;return repaired;});repairQueue=operation;return operation;}
async function prepareSkillBundle(id){return require('./skill-bundles.cjs').prepareBundle(root,installed,id,{repair:repairSkill});}
async function getTask(payload){const game=config.games.find(g=>g.id===payload.gameId);let skill=payload.skillId?.startsWith('bundle-')?await prepareSkillBundle(payload.skillId):installed[payload.skillId];if(!game||!skill)throw Error('请先选择游戏和已下载的 Skill');skill=await require('./skill-integrity.cjs').ensureSkill(skill,{repair:repairSkill});return {game,skill,text:makePrompt(game,skill,payload.action)};}


async function seedEmbeddedSkills(){
 const bundled=path.join(__dirname,'../bundled-skills');const source=await fs.access(bundled).then(()=>bundled,()=>path.join(__dirname,'../skills'));const catalog=await readJSON(path.join(source,'catalog.json'),null);if(!catalog)return;
 const ledger=await client.state();for(const item of catalog.skills){const skillId='s-'+require('./core.cjs').digest(item.name).slice(0,20);if(ledger[skillId])continue;const snapshot=await require('./core.cjs').collect(path.join(source,item.name));const actualFiles=new Map(snapshot.files.map(f=>[f.path,f]));if(item.files?(item.files.length!==snapshot.files.length||item.files.some(f=>actualFiles.get(f.path)?.hash!==f.hash||actualFiles.get(f.path)?.size!==f.size)):snapshot.treeHash!==item.treeHash)throw Error('内置 Skill 文件校验失败');const dest=path.join(root,'subscriber/skills',item.name);await fs.cp(path.join(source,item.name),dest,{recursive:true});ledger[skillId]={id:'built-'+item.treeHash.slice(0,24),skillId,name:item.name,version:'内置',bundled:true,local:true,path:dest,treeHash:item.treeHash,files:item.files||snapshot.files,bytes:snapshot.bytes,fileCount:snapshot.files.length,createdAt:catalog.createdAt,summary:''};}
 await atomicJSON(path.join(root,'subscriber/installed.json'),ledger);Object.assign(installed,ledger);client.seeds=installed;
}
async function confirmHealthyUpdate(){const file=path.join(root,'updates/receipt.json'),receipt=await readJSON(file,null).catch(()=>null);if(!receipt)return;const target=process.platform==='darwin'?process.execPath.split('/Contents/MacOS/')[0]:path.dirname(process.execPath);if(receipt.status==='installed'&&receipt.version===app.getVersion()&&receipt.backup===target+'.previous'){await atomicJSON(file,{status:'confirmed',version:receipt.version});await fs.rm(path.join(root,'updates',receipt.version),{recursive:true,force:true});}else if(receipt.status==='rolled-back'){notify('工作台更新未完成','已恢复此前版本');if(receipt.failed===target+'.failed')await fs.rm(receipt.failed,{recursive:true,force:true});await atomicJSON(file,{...receipt,status:'rollback-notified'});}}
async function checkApplication(){if(appUpdate.busy||!config.repository)return state();appUpdate={...appUpdate,busy:true,error:''};await emit();try{const result=await updater.check(config.repository,app.getVersion());const changed=result.available&&appUpdate.manifest?.version!==result.manifest?.version;appUpdate={...result,busy:false,error:''};if(changed)notify('工作台有更新','打开设置更新工作台');}catch(e){appUpdate={...appUpdate,busy:false,error:e.message};}await emit();return state();}
async function applyApplication(){
 if(importJob?.running)throw Error('游戏正在导入，请完成当前项后更新工作台');
 if(sending.size)throw Error('指令正在发送，请稍后更新');if(!appUpdate.available||!appUpdate.manifest)throw Error('暂无可用更新');if(appUpdate.busy)throw Error('正在更新');appUpdate.busy=true;appUpdate.progress=0;await emit();
 try{downloadedUpdate=await updater.prepare(appUpdate.manifest,{repo:config.repository,root,onProgress:bytes=>{appUpdate.progress=bytes;emit();}});if(syncPromise)await syncPromise;if(publishPromise)await publishPromise;await persist();const target=process.platform==='darwin'?process.execPath.split('/Contents/MacOS/')[0]:app.isPackaged?path.dirname(process.execPath):path.join(root,'desktop');if(process.platform==='darwin'&&!target.endsWith('.app'))throw Error('请使用独立应用更新');await fs.access(path.dirname(target),require('node:fs').constants.W_OK);const candidate=target+'.incoming-'+crypto.randomUUID();await fs.cp(downloadedUpdate.entry,candidate,{recursive:true,verbatimSymlinks:true});const scriptPath=path.join(root,'updates',process.platform==='darwin'?'apply.command':'apply.ps1'),receipt=path.join(root,'updates/receipt.json');const script=updater.installerScript({platform:process.platform,target,candidate,pid:process.pid,receipt,version:downloadedUpdate.version,bootstrapPointer:process.platform==='win32'?path.join(root,'active-app.json'):null,fallbackExe:process.platform==='win32'&&!app.isPackaged?process.execPath:null,fallbackArgs:process.platform==='win32'&&!app.isPackaged?[app.getAppPath()]:[]});await fs.writeFile(scriptPath,updater.installerBytes(script,process.platform),{mode:0o700});const child=process.platform==='darwin'?spawn('/bin/sh',[scriptPath],{detached:true,stdio:'ignore'}):spawn('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',scriptPath],{detached:true,windowsHide:true,stdio:'ignore'});child.unref();quitting=true;app.quit();return {status:'restarting'};}catch(e){appUpdate.busy=false;appUpdate.error=e.message;await emit();throw e;}
}

async function scanLocalSkills(){
 const base=path.join(process.env.CODEX_HOME||path.join(require('node:os').homedir(),'.codex'),'skills');localSkillErrors=[];
 let entries=[];try{entries=await fs.readdir(base,{withFileTypes:true});}catch(e){if(e.code==='ENOENT')return;throw e;}
 const present=new Set();for(const entry of entries){if(!entry.isDirectory()||! /^(cocos-|game-audio-library$|mobile-touch-computer-use$|chrome-mobile-testing$)/.test(entry.name))continue;
  const p=path.join(base,entry.name),id='local-'+require('./core.cjs').digest(entry.name).slice(0,20);present.add(id);
  try{const snapshot=await require('./core.cjs').collect(p,{localUse:true}),text=await fs.readFile(path.join(p,'SKILL.md'),'utf8');const description=text.match(/^description:\s*(.+)$/m)?.[1]||'';installed[id]={id:'local-'+snapshot.treeHash.slice(0,24),skillId:id,name:entry.name,version:'本机',local:true,path:p,treeHash:snapshot.treeHash,files:snapshot.files,bytes:snapshot.bytes,fileCount:snapshot.files.length,createdAt:(await fs.stat(path.join(p,'SKILL.md'))).mtime.toISOString(),summary:description};}catch(e){localSkillErrors.push({name:entry.name,error:e.message});}
 }
 for(const [id,skill]of Object.entries(installed))if(skill.local&&!skill.bundled&&!present.has(id))delete installed[id];
}
let stageRefreshQueue=Promise.resolve();
const stageWatcher=require('./stage-watch.cjs').createStageWatcher(ids=>{stageRefreshQueue=stageRefreshQueue.catch(()=>{}).then(async()=>{if(quitting)return;if(codexBusy&&codexPromise)await codexPromise.catch(()=>{});if(quitting)return;let changed=false;for(const id of ids){const thread=codexSnapshot.threads.find(t=>t.threadId===id);if(!thread)continue;const result=await require('./stage-reader.cjs').readLatestStage(thread,{previous:thread});if(!result.available||!result.contextRead)continue;Object.assign(thread,result,{contextRead:true,contextCheckedAt:new Date().toISOString()});for(const game of config.games)if(game.threadId===id&&game.stageMode==='auto'&&(game.stage!==result.stageInfo.stage||game.stageEvidence!==result.stageInfo.evidence||game.stageAt!==result.stageInfo.at)){Object.assign(game,{stage:result.stageInfo.stage,stageEvidence:result.stageInfo.evidence,stageAt:result.stageInfo.at,stageSource:result.contextStatus,contextStatus:result.contextStatus});changed=true;}}if(changed&&!quitting){await atomicJSON(path.join(root,'codex-index.json'),codexSnapshot);await persist();await emit();}});return stageRefreshQueue;});
async function syncCodex(){if(codexPromise)return codexPromise;codexPromise=(async()=>{codexBusy=true;await emit();try{
 config.games=config.games.filter(g=>!(g.source==='codex'&&g.stageMode==='auto'&&isMaintenanceTitle(g.name)));
 const cache=Object.fromEntries(codexSnapshot.threads.map(t=>[t.threadId,t]));const roots=[...config.scanRoots,...config.games.filter(g=>g.source!=='codex').map(g=>g.path),path.join(require('node:os').homedir(),'游戏出海项目制作')];
 const snapshot=await discoverThreads({roots,cache});const knownIds=new Set(snapshot.threads.map(t=>t.threadId));const tracked=snapshot.threads.concat(config.games.filter(g=>g.telemetry?.active===true&&g.rolloutPath&&!knownIds.has(g.threadId)).map(g=>({threadId:g.threadId,rolloutPath:g.rolloutPath})));const telemetry=await scanTelemetries(tracked,{cache:telemetryCache,classifyStage:require('./codex.cjs').inferStage});telemetryCache=telemetry.cache;await atomicJSON(path.join(root,'telemetry-cache.json'),telemetryCache);codexSnapshot=snapshot;if(!smoke)stageWatcher.update(snapshot.threads);codexError='';
 for(const t of snapshot.threads){if(config.hiddenThreads.includes(t.threadId)||!t.path)continue;let g=config.games.find(g=>g.threadId===t.threadId);if(!g){g={id:'codex-'+t.threadId,name:t.title,path:t.path,threadId:t.threadId,chatUrl:'codex://threads/'+t.threadId+'?hostId=local',source:'codex',stageMode:'auto',note:''};config.games.push(g);require('./game-preferences.cjs').inheritGamePreferences(g,config.games,{roots:config.scanRoots});}g.metadataStatus=t.metadataStatus;if(g.source==='codex')g.name=t.title;g.telemetry=telemetry.byThread[t.threadId]||null;g.rolloutPath=t.rolloutPath;if(g.stageMode==='auto'){g.stage=t.contextRead?t.stageInfo.stage:(g.telemetry?.latestStageCurrent&&g.telemetry.latestStageVersion===require('./stage-detection.cjs').VERSION?g.telemetry.latestStage:null);g.stageEvidence=t.contextRead?t.stageInfo.evidence:'';g.stageSource=t.contextStatus;g.stageAt=t.stageInfo.at||null;g.contextStatus=t.contextStatus;}g.updatedAt=new Date((t.updatedAt||Date.now()/1000)*1000).toISOString();}
 for(const g of config.games)if(!knownIds.has(g.threadId)){g.metadataStatus=null;if(telemetry.byThread[g.threadId])g.telemetry=telemetry.byThread[g.threadId];else if(g.source==='codex'&&g.telemetry)g.telemetry={...g.telemetry,active:null,status:'unknown'};}
 await atomicJSON(path.join(root,'codex-index.json'),snapshot);await persist();
 }catch(e){codexError=e.message;}finally{codexBusy=false;await emit();}return state();})();try{return await codexPromise;}finally{codexPromise=null;}}
function applyDock(force=false){if(!win||snapping)return;snapping=true;try{const bounds=win.getBounds(),area=screen.getDisplayMatching(bounds).workArea;const next=dockBounds(bounds,area,{collapsed,edge:force?dockEdge:undefined,force});dockEdge=next.edge||dockEdge;if(bounds.width!==next.bounds.width||bounds.height!==next.bounds.height)win.setMinimumSize(next.bounds.width,next.bounds.height);if(['x','y','width','height'].some(k=>bounds[k]!==next.bounds[k]))win.setBounds(next.bounds);config.window={...next.bounds,edge:dockEdge};persist().catch(console.error);}finally{snapping=false;}}
async function sendGame(value){
 const game=config.games.find(g=>g.id===value.gameId);if(!game||!UUID.test(game.threadId||''))throw Error('请先关联 Codex 对话');if(busy)throw Error('Skill 正在同步，请稍后推送');if(sending.has(game.threadId))throw Error('正在发送');
 sending.add(game.threadId);try{
 let message,skill;
 if(value.action==='preview')message='当前游戏：'+game.name+'\n项目目录：'+game.path+'\n请按当前项目适用的 Skill，启动最新版本的本地试玩，使用固定手机尺寸外壳给出可点击的预览链接。先检查能否进入游戏，保留原文件与存档，并收尾已被替代的旧预览。';
 else if(value.action==='check')message='当前游戏：'+game.name+'\n项目目录：'+game.path+'\n请读取本对话最新要求、项目规则和适用 Skill，检查并定点修复当前游戏，完成相称验证，保留原件与存档。不要自动上传或发布。';
 else {if(!value.skillId?.startsWith('bundle-')){skill=installed[value.skillId];if(!skill)throw Error('请选择 Skill');if(!skill.local){const latest=index.releases.find(r=>r.skillId===value.skillId);if(latest&&latest.id!==skill.id){skill=installed[value.skillId]=await client.install(config,latest.id);const pins=await readJSON(path.join(root,'pins.json'),{});pins[value.skillId]=false;await atomicJSON(path.join(root,'pins.json'),pins);}}}const task=await getTask(value);skill=task.skill;message='当前游戏：'+game.name+'\n项目目录：'+game.path+'\n请重新读取这个新版 Skill：'+skill.path+'\n先读取 SKILL.md，再按需读取配套文件。\nSkill：'+skill.name+' '+skill.version+'\n文件树 SHA-256：'+skill.treeHash+'\n请使用这个新版 Skill 继续完成后面的制作，沿用本对话的当前进度，保留原件、存档和已确认的玩法。';}
 if(skill?.archive)message+='\n完整压缩包：'+skill.archive;
 const key=game.threadId+':'+(skill?.treeHash||value.action),logPath=path.join(root,'send-receipts.json');
 const result=await sendWithReceipt({file:logPath,key,threadId:game.threadId,skillId:value.skillId,send:()=>queueMessage(game.threadId,message)});if(result.status==='failed')throw Error(result.detail);return {...result,target:game.name,skill:skill?.name};}finally{sending.delete(game.threadId);await emit();}
}

async function runProjectImports(value){
 if(importJob?.running)throw Error('正在导入，请稍候');if(appUpdate.busy)throw Error('工作台正在检查或安装更新，请稍后导入');if(!config.projectRoot)throw Error('请先选择项目保存位置');if(!['英化','重塑'].includes(value.workflow))throw Error('请选择英化或重塑');
 importJob={running:true,stopRequested:false,current:0,total:value.sources?.length||0,name:''};await emit();let lastEmit=0;
 try{const result=await require('./project-batch.cjs').importProjects({sources:value.sources,root:config.projectRoot,shouldStop:()=>importJob.stopRequested,onProgress:async progress=>{Object.assign(importJob,progress);if(Date.now()-lastEmit>150){lastEmit=Date.now();await emit();}},onItem:async project=>{const game=safeGame({...project,stageMode:'auto',workflow:value.workflow});config.games.unshift(game);await persist();return game;}});Object.assign(importJob,{running:false,result});return result;}finally{importJob.running=false;await emit();}
}
const handlers={
  ackUpdates:async()=>{updateNotices=[];await atomicJSON(path.join(root,'update-notices.json'),updateNotices);await emit();},
  githubLogin:async()=>{const binary=await github.ghBinary();if(!binary){await shell.openExternal('https://cli.github.com/');return {status:'install-required'};}if(process.platform==='darwin'){const file=path.join(root,'github-login.command');const quote=v=>"'"+v.replaceAll("'","'\\''")+"'";await fs.writeFile(file,'#!/bin/sh\nexec '+quote(binary)+' auth login --web --git-protocol https\n',{mode:0o700});await shell.openPath(file);}else{const quote=v=>"'"+v.replaceAll("'","''")+"'";spawn('powershell.exe',['-NoProfile','-Command','Start-Process -FilePath '+quote(binary)+" -ArgumentList @('auth','login','--web','--git-protocol','https')"],{windowsHide:false});}return {status:'login-opened'};},
  checkApplication:()=>checkApplication(),
  applyApplication:()=>applyApplication(),
  setRepository:async value=>{config.repository=github.repository(value);config.feedMode='github';await persist();await sync();await checkApplication();return state();},
  openRepository:async()=>shell.openExternal('https://github.com/'+github.repository(config.repository)),
  syncCodex:()=>syncCodex(),
  sendGame:value=>sendGame(value),
  openChat:async id=>{const g=config.games.find(g=>g.id===id);if(!g||!UUID.test(g.threadId||''))throw Error('未关联对话');await shell.openExternal(g.chatUrl);},
  refreshSkills:async()=>{await scanLocalSkills();await sync();await emit();},
  state:()=>state(),
  setGamePreferences:async value=>{const game=require('./game-preferences.cjs').setGamePreferences(config.games,value.id,value,{roots:config.scanRoots});await persist();await emit();return game;},
  chooseProjectFolders:async()=>{const r=await dialog.showOpenDialog(win,{title:'选择游戏文件夹',properties:['openDirectory','multiSelections']});return r.canceled?[]:r.filePaths;},
  importProjects:value=>runProjectImports(value),
  stopImport:async()=>{if(importJob?.running)importJob.stopRequested=true;await emit();},
  chooseFolder:async()=>{const r=await dialog.showOpenDialog(win,{properties:['openDirectory']});return r.canceled?null:r.filePaths[0];},
  saveGame:async value=>{const g=safeGame(value);const stat=await fs.stat(g.path);if(!stat.isDirectory())throw Error('项目目录不存在');const i=config.games.findIndex(x=>x.id===g.id);if(i<0)config.games.unshift(g);else config.games[i]=g;await persist();await emit();return g;},
  setProjectRoot:async()=>{const r=await dialog.showOpenDialog(win,{title:'项目保存位置',properties:['openDirectory','createDirectory']});if(r.canceled)return null;config.projectRoot=await fs.realpath(r.filePaths[0]);await persist();await emit();return config.projectRoot;},
  importSkillArchive:async value=>{if(busy||sending.size)throw Error('正在同步或推送，请稍后导入');let source=value?.source;if(!source){const result=await dialog.showOpenDialog(win,{filters:[{name:'Skill ZIP',extensions:['zip']}],properties:['openFile']});if(result.canceled)return null;source=result.filePaths[0];}busy=true;await emit();try{const result=await require('./skill-archive.cjs').importSkillArchive(client.root,source);Object.assign(installed,result.installed);await require('./skill-archive.cjs').cleanImports(client.root);return {category:result.category,skillId:result.skillId,memberCount:result.memberCount};}finally{busy=false;await emit();}},
  importProject:async value=>{if(appUpdate.busy)throw Error('工作台正在检查或安装更新，请稍后导入');if(importJob?.running)throw Error('正在批量导入，请稍候');if(!config.projectRoot)throw Error('请先选择项目保存位置');const result=await require('./project-import.cjs').importProject({source:value.source,root:config.projectRoot,name:value.name});const g=safeGame({name:result.name,path:result.path,stageMode:'auto',workflow:value.workflow});config.games.unshift(g);await persist();await emit();return g;},
  removeGame:async id=>{const g=config.games.find(g=>g.id===id);if(g?.threadId)config.hiddenThreads.push(g.threadId);config.games=config.games.filter(g=>g.id!==id);await persist();await emit();},
  settings:async value=>{if(syncPromise)await syncPromise;const c=connection({url:value.url,token:value.token||config.token});const changed=config.url!==c.url||config.token!==c.token;config.url=c.url;config.token=c.token;config.feedMode='hub';config.autoDownload=!!value.autoDownload;if(changed){await atomicJSON(path.join(root,'pins.json'),{});index={releases:[]};}await persist();await sync();listenEvents();return state();},
  disconnect:async()=>{eventAbort?.abort();if(syncPromise)await syncPromise;config.url='';config.token='';config.feedMode='none';index={releases:[]};status='未连接同步源';await persist();await emit();},
  sync:()=>sync(),
  install:async value=>{if(sending.size)throw Error('Skill 正在推送，请稍后恢复版本');if(busy)throw Error('正在同步，请稍候');busy=true;await emit();try{const r=index.releases.find(r=>r.id===value.id);if(!r)throw Error('版本不存在');const out=await client.install(config,r.id,{replace:!!value.pin});installed[r.skillId]=out;const pins=await readJSON(path.join(root,'pins.json'),{});pins[r.skillId]=!!value.pin;await atomicJSON(path.join(root,'pins.json'),pins);await emit();return out;}finally{busy=false;await emit();}},
  addSource:async value=>{if(config.sources.some(s=>s.name===value.name||s.path===value.path))throw Error('此名称或目录已添加');const {collect}=require('./core.cjs');await collect(value.path);const s={id:crypto.randomUUID(),name:String(value.name).trim(),path:value.path,auto:false};if(!s.name)throw Error('请输入 Skill 名称');config.sources.push(s);await persist();await emit();return s;},
  sourceAuto:async value=>{const s=config.sources.find(s=>s.id===value.id);if(s)s.auto=!!value.auto;await persist();await emit();},
  removeSource:async id=>{config.sources=config.sources.filter(s=>s.id!==id);await persist();await emit();},
  publish:async value=>publish(value.id,value.note),
  startSharing:async()=>{await startSharing();return state();},
  stopSharing:async()=>{await hub?.close();hub=null;config.hostEnabled=false;await persist();await emit();},
  subscribeSelf:async()=>{if(!hub)await startSharing();config.url=`http://127.0.0.1:${hub.port}`;config.token=config.hostToken;config.feedMode='hub';await persist();await sync();listenEvents();},
  exportConnection:async()=>{if(!hub)throw Error('请先开启共享服务');const r=await dialog.showSaveDialog(win,{defaultPath:'Skill订阅连接.json',filters:[{name:'订阅连接',extensions:['json']}]});if(r.canceled)return null;await atomicJSON(r.filePath,{schema:1,url:addresses()[0]?`http://${addresses()[0]}:${hub.port}`:`http://127.0.0.1:${hub.port}`,token:config.hostToken});shell.showItemInFolder(r.filePath);return r.filePath;},
  importConnection:async()=>{const r=await dialog.showOpenDialog(win,{filters:[{name:'订阅连接',extensions:['json']}],properties:['openFile']});if(r.canceled)return null;const c=connection(await readJSON(r.filePaths[0],null));config.url=c.url;config.token=c.token;config.feedMode='hub';await persist();await sync();listenEvents();return state();},
  copyTask:async value=>{const task=await getTask(value);clipboard.writeText(task.text);if(value.openChat){if(!task.game.chatUrl)throw Error('指令已复制；请先为游戏设置对话链接');await shell.openExternal(task.game.chatUrl);}return task.text;},
  exportBundle:async value=>{const bundle=await prepareSkillBundle(value.skillId);shell.showItemInFolder(bundle.archive);return bundle.archive;},
  taskText:async value=>(await getTask(value)).text,
  exportTask:async value=>{const {game,skill,text}=await getTask(value);const dir=path.join(root,'handoffs',game.id),archive=dir+'.zip';await fs.rm(dir,{recursive:true,force:true});await fs.mkdir(dir,{recursive:true});try{await fs.cp(skill.path,path.join(dir,'Skill'),{recursive:true});await fs.writeFile(path.join(dir,'开始这里.md'),text+'\n附件内 Skill/ 是本次完整 Skill 文件副本。若路径不可访问，以附件文件为准。\n');await zipFolder(dir,archive);}finally{await fs.rm(dir,{recursive:true,force:true});}clipboard.writeText(text+'\n完整 Skill 交接文件：'+archive);return archive;},
  reveal:async value=>{const allowed=[...config.games.map(g=>g.path),...Object.values(installed).map(s=>s.path),...config.sources.map(s=>s.path)];const target=path.resolve(value);if(!allowed.includes(target)&&!target.startsWith(path.join(root,'handoffs')+path.sep))throw Error('文件位置未授权');const err=await shell.openPath(target);if(err)throw Error(err);},
  expand:async()=>{if(!collapsed)return;collapsed=false;applyDock(true);await emit();},
  collapse:async()=>{if(!collapsed){const b=win.getBounds(),a=screen.getDisplayMatching(b).workArea;dockEdge=Math.abs(b.x-a.x)<Math.abs(a.x+a.width-b.x-b.width)?'left':'right';}collapsed=!collapsed;applyDock(true);if(collapsed)hover.closed(screen.getCursorScreenPoint(),win.getBounds());await emit();},
  quit:()=>{if(importJob?.running)throw Error('游戏正在导入，请先停止后续导入并等待当前项完成');quitting=true;app.quit();}
};
async function main(){
  nativeTheme.themeSource='dark';
  const distribution=await readJSON(path.join(__dirname,'../distribution.json'),{});config={...defaults(),repository:distribution.repository||'',...await readJSON(configPath,{})};config.hiddenThreads ||= [];config.scanRoots ||= [];for(const g of config.games){if(g.stage==='制作中')g.stage='玩法制作';if(g.stage==='待检查')g.stage='检查';g.threadId ||=g.chatUrl?.match(/threads\/([0-9a-f-]{36})/i)?.[1]||'';g.stageMode ||= 'manual';}codexSnapshot=await readJSON(path.join(root,'codex-index.json'),codexSnapshot);telemetryCache=await readJSON(path.join(root,'telemetry-cache.json'),{});updateNotices=await readJSON(path.join(root,'update-notices.json'),[]);store=new HubStore(path.join(root,'publisher'));client=new ClientStore(path.join(root,'subscriber'));await client.recover();installed=await client.state();index=await readJSON(path.join(root,'subscriber','index.json'),{releases:[]});
  const area=screen.getPrimaryDisplay().workArea;const b=config.window||{};
  win=new BrowserWindow({width:COLLAPSED.width,height:COLLAPSED.height,minWidth:COLLAPSED.width,minHeight:COLLAPSED.height,x:Math.max(area.x,Math.min(b.x??area.x+area.width-490,area.x+area.width-460)),y:Math.max(area.y,Math.min(b.y??area.y+48,area.y+area.height-740)),icon:path.join(__dirname,'../ui/window-icon.png'),frame:false,transparent:true,backgroundColor:'#00000000',...(process.platform==='darwin'?{vibrancy:'under-window',visualEffectState:'active'}:process.platform==='win32'?{backgroundMaterial:'acrylic'}:{}),resizable:false,alwaysOnTop:true,hasShadow:true,show:false,webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});
  if(process.platform==='darwin')win.setVisibleOnAllWorkspaces(true,{visibleOnFullScreen:true});Menu.setApplicationMenu(null);
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));win.webContents.on('will-navigate',e=>e.preventDefault());win.webContents.session.setPermissionRequestHandler((_,__,cb)=>cb(false));
  const url=pathToFileURL(path.join(__dirname,'../ui/index.html')).href;
  ipcMain.handle('dock:call',async(e,method,value)=>{if(e.sender!==win.webContents||e.senderFrame!==win.webContents.mainFrame||!e.senderFrame.url.startsWith(url))throw Error('无效调用来源');if(!Object.hasOwn(handlers,method))throw Error('不支持的操作');try{return {ok:true,value:await handlers[method](value)};}catch(err){return {ok:false,error:err.message};}});
  ipcMain.on('dock:drag',(e,archive)=>{if(e.sender!==win.webContents||typeof archive!=='string'||!archive.startsWith(path.join(root,'handoffs')+path.sep)||!archive.endsWith('.zip'))return;const pixels=Buffer.alloc(32*32*4);for(let n=0;n<pixels.length;n+=4){pixels[n]=77;pixels[n+1]=121;pixels[n+2]=92;pixels[n+3]=255;}const icon=nativeImage.createFromBitmap(pixels,{width:32,height:32});e.sender.startDrag({file:archive,icon});});
  win.on('close',e=>{if(!quitting&&!smoke){e.preventDefault();if(!collapsed)handlers.collapse();}});
  win.on('move',()=>{if(snapping)return;clearTimeout(snapTimer);snapTimer=setTimeout(()=>{applyDock();emit();},220);});
  await win.loadFile(path.join(__dirname,'../ui/index.html'));dockEdge=config.window?.edge||'right';applyDock(true);if(!smoke)win.show();
  hoverTimer=setInterval(()=>{if(collapsed&&win&&!win.isDestroyed()&&hover.sample(screen.getCursorScreenPoint(),win.getBounds()))handlers.expand().catch(console.error);},120);
  if(smoke){
    clearInterval(hoverTimer);
    config.feedMode='hub';config.repository='';
    await win.webContents.executeJavaScript('window.ready');await handlers.expand();
    const integration=[];let embeddedCountAtStartup=0;await handlers.expand();win.emit('blur');integration.push({expandedIdempotent:!collapsed&&win.getBounds().width===EXPANDED.width,manualCloseOnly:!collapsed});if(process.env.SKILL_DOCK_SMOKE_EMBEDDED==='1'){await seedEmbeddedSkills();embeddedCountAtStartup=Object.values(installed).filter(s=>s.bundled).length;const previousHome=process.env.CODEX_HOME;process.env.CODEX_HOME=path.join(root,'empty-codex');await fs.mkdir(path.join(process.env.CODEX_HOME,'skills/.system'),{recursive:true});try{await scanLocalSkills();}finally{if(previousHome===undefined)delete process.env.CODEX_HOME;else process.env.CODEX_HOME=previousHome;}await emit();}
    if(process.env.SKILL_DOCK_SMOKE_FIXTURE==='1'){
      const source=path.join(root,'fixture-skill'),gamePath=path.join(root,'fixture-game');await fs.mkdir(source,{recursive:true});await fs.mkdir(gamePath,{recursive:true});await fs.writeFile(path.join(source,'SKILL.md'),'# Smoke Skill\nKeep original saves.');
      async function ipc(method,value){return win.webContents.executeJavaScript('window.dock.call('+JSON.stringify(method)+','+JSON.stringify(value ?? null)+')');}
      const sourceRecord=await ipc('addSource',{name:'原生验证 Skill',path:source});const v1=await ipc('publish',{id:sourceRecord.id,note:'初始文件'});integration.push({publish:v1.changed});
      await ipc('startSharing');await ipc('subscribeSelf');integration.push({downloaded:!!Object.keys(installed).length});
      const game=await ipc('saveGame',{name:'验证游戏',path:gamePath,stage:'待检查'});const skillId=v1.release.skillId;
      const prompt=await ipc('taskText',{gameId:game.id,skillId,action:'check'});integration.push({promptBindsGame:prompt.includes(game.name),promptBindsHash:prompt.includes(v1.release.treeHash)});
      await fs.writeFile(path.join(installed[skillId].path,'SKILL.md'),'damaged local copy');
      const repairedPrompt=await ipc('taskText',{gameId:game.id,skillId,action:'check'});integration.push({sameVersionAutoRepair:installed[skillId].id===v1.release.id&&(await fs.readFile(path.join(installed[skillId].path,'SKILL.md'),'utf8')).includes('Keep original saves.')&&repairedPrompt.includes(v1.release.treeHash)});
      await fs.writeFile(path.join(source,'SKILL.md'),'# Smoke Skill\nNew mobile contract.');const v2=await ipc('publish',{id:sourceRecord.id,note:'新增手机重开检查'});integration.push({backgroundAutoUpdated:installed[skillId].id===v2.release.id});integration.push({persistentSkillNotice:updateNotices.some(n=>n.id===v2.release.id&&n.status==='updated')&&(await readJSON(path.join(root,'update-notices.json'),[])).some(n=>n.id===v2.release.id)});await ipc('ackUpdates');integration.push({acknowledgedNotices:updateNotices.length===0&&(await readJSON(path.join(root,'update-notices.json'),[])).length===0});
      await ipc('install',{id:v1.release.id,pin:true});await ipc('sync');integration.push({restoredAndPinned:installed[skillId].id===v1.release.id});
      await ipc('install',{id:v2.release.id,pin:false});await win.webContents.executeJavaScript(`document.querySelector('nav [data-tab="skills"]').click()`);
      await ipc('collapse');integration.push({capsule:win.getBounds().width===COLLAPSED.width&&win.getBounds().height===COLLAPSED.height});await ipc('collapse');
      await hub.close();hub=null;
      if(integration.some(row=>Object.values(row).some(v=>v!==true)))throw Error('Native integration checks failed');
    }
    if(process.env.SKILL_DOCK_SMOKE_SELECTION==='1'){
      config.games=[{id:'fixture-a',threadId:'11111111-1111-4111-8111-111111111111',name:'松果邮局 · 玩法',path:path.join(root,'Pinecone'),stage:'玩法制作',metadataStatus:'active',source:'codex'},{id:'fixture-b',threadId:'22222222-2222-4222-8222-222222222222',name:'松果邮局 · 检查',path:path.join(root,'Pinecone'),stage:'检查',metadataStatus:'idle',source:'codex'}];await emit();
      const selection=await win.webContents.executeJavaScript(`(()=>{document.querySelector('nav [data-tab="games"]').click();const groups=document.querySelectorAll('.thread-group').length;document.querySelector('[data-activity="ongoing"]').click();const active=[...document.querySelectorAll('[data-game]')].map(n=>n.dataset.game);document.querySelector('[data-activity="ended"]').click();const ended=[...document.querySelectorAll('[data-game]')].map(n=>n.dataset.game);document.querySelector('[data-activity="all"]').click();return {groups,active,ended,overflow:document.documentElement.scrollWidth>innerWidth};})()`);
      integration.push({threadSelection:selection.groups===1&&selection.active.join()==='fixture-a'&&selection.ended.join()==='fixture-b'&&!selection.overflow});
      if(!integration.at(-1).threadSelection)throw Error('Native conversation selection failed');
    }
    if(process.env.SKILL_DOCK_SMOKE_E2E==='1'){
      await fs.writeFile(path.join(root,'queue-receiver.cjs'),`const fs=require('node:fs'),path=require('node:path');const a=process.argv.slice(2);if(a[0]!=='queue')process.exit(2);const threadId=a[a.indexOf('--thread')+1],message=a[a.indexOf('--message')+1];fs.writeFileSync(path.join(__dirname,'queue-received.json'),JSON.stringify({threadId,message}));console.log('Queued fixture message');`);
      const e2e=await require('./native-e2e.cjs')({win,handlers,config,installed,root,dialog,setDiscovery:fn=>{discoverThreads=fn||discover;}});await atomicJSON(path.join(root,'native-e2e.json'),e2e);integration.push({nativeImportAndBundlePush:true});
    }
    if(process.env.SKILL_DOCK_SMOKE_FIXTURE==='1'){
      await fs.mkdir(root,{recursive:true});
      for(const page of ['games','settings','skills']){
        await win.webContents.executeJavaScript(`document.querySelector('nav [data-tab="${page}"]').click()`);
        await fs.writeFile(path.join(root,'view-'+page+'.png'),(await win.webContents.capturePage()).toPNG());
      }
    }
    await new Promise(r=>setTimeout(r,300));
    const result=await win.webContents.executeJavaScript(`({title:document.title,body:document.body.innerText,scroll:document.documentElement.scrollWidth,viewport:innerWidth,api:!!window.dock,nodes:document.querySelectorAll('button').length})`);
    await fs.mkdir(root,{recursive:true});await fs.writeFile(path.join(root,'smoke.json'),JSON.stringify({...result,integration,embeddedCount:embeddedCountAtStartup,remainingEmbeddedCount:Object.values(installed).filter(s=>s.bundled).length,runtime:process.versions.electron,alwaysOnTop:win.isAlwaysOnTop(),bounds:win.getBounds()},null,2));await fs.writeFile(path.join(root,'smoke.png'),(await win.webContents.capturePage()).toPNG());quitting=true;app.quit();return;
  }
  if(config.hostEnabled)await startSharing().catch(e=>{lastError=e.message;});
  await seedEmbeddedSkills();await scanLocalSkills();await emit();await confirmHealthyUpdate();syncCodex();checkApplication();updateTimer=setInterval(checkApplication,APPLICATION_POLL_MS);await sync();listenEvents();
  poll=setInterval(()=>{if(!codexBusy)syncCodex();scanLocalSkills().then(emit).catch(console.error);sync();if(!eventAbort||eventAbort.signal.aborted)listenEvents();},SKILL_POLL_MS);
  powerMonitor.on('resume',()=>{sync();checkApplication();});
  watchTimer=setInterval(async()=>{if(watchBusy||publishPromise)return;watchBusy=true;try{for(const s of config.sources.filter(s=>s.auto))try{await publish(s.id);}catch(e){s.error=e.message;await emit();}}finally{watchBusy=false;}},20000);
}
app.whenReady().then(main).catch(e=>{console.error(e);if(smoke){try{const syncFS=require('node:fs');syncFS.mkdirSync(root,{recursive:true});syncFS.writeFileSync(path.join(root,'smoke-error.txt'),e.stack||String(e));}catch{}}app.exit(1);});
app.on('before-quit',()=>{quitting=true;stageWatcher.close();clearInterval(poll);clearInterval(updateTimer);cancelReaders();clearInterval(watchTimer);clearTimeout(snapTimer);eventAbort?.abort();hub?.close();});
app.on('window-all-closed',()=>app.quit());

app.on('will-quit',()=>clearInterval(hoverTimer));
