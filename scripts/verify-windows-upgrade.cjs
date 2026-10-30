// Run only on a Windows runner. Installs/restarts real packaged Electron applications in an isolated profile.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {spawn,execFile}=require('node:child_process'),{promisify}=require('node:util');
const run=promisify(execFile),github=require('../src/github.cjs'),updater=require('../src/updater.cjs');
const formal=process.argv.includes('--published');
const base=path.resolve('.qa/windows-upgrade-'+(formal?'published':'candidate')),profile=path.join(base,'用户数据'),target=path.join(base,'中文 安装目录'),reportPath=path.join(base,'upgrade-proof.json');
const proof={schema:1,mode:formal?'published':'candidate',platform:process.platform,startedAt:new Date().toISOString(),checks:{},boundary:formal?'Published 0.2.13 native app uses unchanged production GitHub check/download and settings update button to install the public latest release discovered at runtime; no transport injection. Native health/data/stages are checked.':'Published baseline is downloaded from GitHub. Unpublished candidate release metadata is injected and candidate bytes are downloaded from an isolated HTTP server. Production old updater validation, installer, new native startup health and installed native stage tests execute on Windows. Actual settings update button is clicked over CDP; only GitHub transport in the isolated baseline copy is replaced. Rollback fault injection is not covered.'};
let oldProcess,server,cdp;const children=new Set();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function json(file){return JSON.parse(await fs.readFile(file,'utf8'));}
async function waitFor(label,fn,ms=120000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const value=await fn();if(value)return value;}catch(e){last=e;}await sleep(500);}throw Error(label+' timed out'+(last?': '+last.message:''));}
function start(exe,args,env,label){const child=spawn(exe,args,{env,windowsHide:true,stdio:['ignore','pipe','pipe']});children.add(child);const logs=[];child.stdout.on('data',b=>logs.push(b));child.stderr.on('data',b=>logs.push(b));child.finished=new Promise((resolve,reject)=>{child.once('error',reject);child.once('close',async code=>{children.delete(child);await fs.writeFile(path.join(base,label+'.log'),Buffer.concat(logs));resolve(code);});});return child;}
async function installedPids(){const script='$p='+"'"+path.join(target,'GameDeskSkill.exe').replaceAll("'","''")+"'"+'; @(Get-CimInstance Win32_Process -Filter "Name = \'GameDeskSkill.exe\'" | Where-Object {$_.ExecutablePath -eq $p} | Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress';const {stdout}=await run('powershell.exe',['-NoProfile','-Command',script]);const p=stdout.trim()?JSON.parse(stdout):[];return Array.isArray(p)?p:[p];}
async function stopInstalled(){for(const pid of await installedPids())try{process.kill(pid);}catch{}await waitFor('Isolated installed application exit',async()=>(await installedPids()).length===0,20000);}
async function installerDiagnostics(label){
 const scriptPath=path.join(profile,'updates/apply.ps1'),quote=v=>"'"+v.replaceAll("'","''")+"'";
 const command=`$tokens=$null;$errors=$null;$f=${quote(scriptPath)};if(Test-Path -LiteralPath $f){[void][System.Management.Automation.Language.Parser]::ParseFile($f,[ref]$tokens,[ref]$errors)}; $processes=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*'+$f+'*')) -or ($_.Name -eq 'GameDeskSkill.exe' -and $_.ExecutablePath -like (${quote(base)}+'*'))} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine); @{parserErrors=@($errors | ForEach-Object {$_.Message});processes=$processes} | ConvertTo-Json -Depth 6 -Compress`;
 const result={label,at:new Date().toISOString()};try{result.scriptPresent=await fs.stat(scriptPath).then(()=>true,()=>false);const {stdout,stderr}=await run('powershell.exe',['-NoProfile','-Command',command],{timeout:20000});result.powershell=JSON.parse(stdout);if(stderr)result.stderr=stderr;}catch(e){result.error=e.message;}
 result.directories=[];for(const e of await fs.readdir(base,{withFileTypes:true}))if(e.isDirectory())result.directories.push(e.name);
 result.updates=await fs.readdir(path.join(profile,'updates')).catch(()=>[]);await fs.writeFile(path.join(base,'installer-'+label+'.json'),JSON.stringify(result,null,2));return result;
}
async function connectCDP(url){
 const socket=new WebSocket(url),pending=new Map();let serial=0;
 await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data)),p=pending.get(m.id);if(!p)return;pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);});
 socket.addEventListener('close',()=>{for(const p of pending.values())p.reject(Error('CDP connection closed'));pending.clear();});
 return {close:()=>socket.close(),evaluate:async expression=>{const id=++serial,result=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP evaluation timed out'));},15000);pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});socket.send(JSON.stringify({id,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}));});if(result.exceptionDetails)throw Error(result.exceptionDetails.text);return result.result?.value;}};
}
async function main(){
 if(process.platform!=='win32')throw Error('Native Windows runner required; Mac/package-only checks are not accepted');
 await fs.mkdir(base,{recursive:true});
 const repo=github.repository(process.env.GITHUB_REPOSITORY||'SJT-bright/game-skill-workbench'),baseline=process.env.WINDOWS_UPGRADE_BASELINE||(formal?'0.2.13':'0.2.14');
 const publicLatest=await github.api(`repos/${repo}/releases/latest`);if(publicLatest.draft||publicLatest.prerelease)throw Error('Public latest release is not stable');
 const publicVersion=String(publicLatest.tag_name).replace(/^v/,'');updater.version(publicVersion);
 const next=formal?publicVersion:require('../package.json').version;
 if(!updater.newer(next,baseline))throw Error('Upgrade candidate must be newer than published baseline '+baseline);
 proof.baseline=baseline;proof.candidate=next;
 const release=await github.api(`repos/${repo}/releases/tags/v${baseline}`),asset=release.assets.find(a=>a.name==='gamedesk-update.json');if(!asset||release.draft||release.prerelease)throw Error('Published baseline manifest missing');
 const baselineManifest=updater.manifest(JSON.parse((await github.api(`repos/${repo}/releases/assets/${asset.id}`,{binary:true})).toString('utf8')),repo);if(baselineManifest.version!==baseline)throw Error('Baseline version mismatch');
 const baselinePackage=await updater.prepare(baselineManifest,{repo,root:path.join(base,'baseline-cache'),platform:'win32',arch:'x64'});
 await fs.cp(baselinePackage.entry,target,{recursive:true});
 const oldUpdater=require(path.join(target,'resources/app/src/updater.cjs'));
 const published=await oldUpdater.check(repo,formal?baseline:'0.2.13');
 if(!published.available||published.manifest.version!==publicVersion)throw Error('Old updater failed to discover published baseline');proof.checks.publishedDiscovery=true;
 const archive=path.resolve(`release/GameDesk-${next}-windows-x64.zip`),bytes=formal?null:await fs.readFile(archive),candidateManifest=formal?published.manifest:{schema:1,kind:'application',repository:repo,version:next,packages:{'win32-x64':{assetId:123,url:`https://github.com/${repo}/releases/download/v${next}/GameDesk-${next}-windows-x64.zip`,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')}}};
 const available=formal?published:await oldUpdater.check(repo,baseline,{api:async()=>({draft:false,prerelease:false,tag_name:'v'+next,html_url:`https://github.com/${repo}/releases/tag/v${next}`,assets:[{id:124,name:'gamedesk-update.json'}]}),readAsset:async()=>Buffer.from(JSON.stringify(candidateManifest))});if(!available.available)throw Error('Baseline updater failed to discover candidate');proof.checks.candidateDiscovery=true;
 await fs.mkdir(profile,{recursive:true});const gamePath=path.join(base,'保留游戏');await fs.mkdir(gamePath,{recursive:true});
 const game={id:'upgrade-preserved',name:'升级保留游戏',path:gamePath,stage:'美工制作',stageMode:'manual',workflow:'英化',pinned:true};
 await fs.writeFile(path.join(profile,'settings.json'),JSON.stringify({games:[game],sources:[],repository:repo,feedMode:'hub',url:'',autoCodex:false,autoDownload:false,scanRoots:[],projectRoot:gamePath}));
 const sentinel=Buffer.from('User-owned payload survives update: '+crypto.randomUUID());await fs.mkdir(path.join(profile,'handoffs'),{recursive:true});const sentinelPath=path.join(profile,'handoffs','用户文件.bin');await fs.writeFile(sentinelPath,sentinel);
 const env={...process.env,SKILL_DOCK_DATA_DIR:profile,CODEX_HOME:path.join(base,'empty-codex'),ELECTRON_ENABLE_LOGGING:'1'};delete env.ELECTRON_RUN_AS_NODE;for(const key of Object.keys(env))if(key.startsWith('SKILL_DOCK_SMOKE_'))delete env[key];await fs.mkdir(env.CODEX_HOME,{recursive:true});
 const oldApp=path.join(target,'resources/app'),mainHash=crypto.createHash('sha256').update(await fs.readFile(path.join(oldApp,'src/main.cjs'))).digest('hex'),updaterHash=crypto.createHash('sha256').update(await fs.readFile(path.join(oldApp,'src/updater.cjs'))).digest('hex');
 if(!formal){
 server=http.createServer((req,res)=>{if(req.url!=='/candidate.zip'){res.writeHead(404).end();return;}proof.candidateDownloadRequests=(proof.candidateDownloadRequests||0)+1;res.writeHead(200,{'Content-Type':'application/zip','Content-Length':bytes.length});res.end(bytes);});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const candidateURL=`http://127.0.0.1:${server.address().port}/candidate.zip`;
 // Patch transport only in the disposable published copy. Keep its main/updater/UI unchanged.
 const releaseFixture={draft:false,prerelease:false,tag_name:'v'+next,html_url:`https://github.com/${repo}/releases/tag/v${next}`,assets:[{id:124,name:'gamedesk-update.json'}]};
 await fs.appendFile(path.join(oldApp,'src/github.cjs'),`\n// Isolated CI candidate transport; never distributed.\n{const originalApi=module.exports.api,originalDownload=module.exports.downloadAsset;module.exports.api=async(endpoint,options)=>{if(endpoint===${JSON.stringify(`repos/${repo}/releases/latest`)})return ${JSON.stringify(releaseFixture)};if(endpoint===${JSON.stringify(`repos/${repo}/releases/assets/124`)})return Buffer.from(${JSON.stringify(JSON.stringify(candidateManifest))});return originalApi(endpoint,options);};module.exports.downloadAsset=async(repo,id,url,dest,progress)=>{if(id!==123)return originalDownload(repo,id,url,dest,progress);const response=await require('electron').net.fetch(${JSON.stringify(candidateURL)});if(!response.ok)throw Error('CI HTTP download failed');const bytes=Buffer.from(await response.arrayBuffer());await require('node:fs/promises').writeFile(dest,bytes);progress(bytes.length);};}\n`);
 }
 oldProcess=start(path.join(target,'GameDeskSkill.exe'),['--disable-gpu','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1'],env,'baseline-start');
 const port=await waitFor('Baseline native DevTools endpoint',async()=>Number((await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]));
 const page=await waitFor('Baseline native renderer',async()=>{const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();return pages.find(p=>p.type==='page'&&p.url.startsWith('file:'));});cdp=await connectCDP(page.webSocketDebuggerUrl);
 await waitFor('Old native automatic candidate discovery',async()=>{const s=await cdp.evaluate(`window.dock?.call('state')`);if(s?.appUpdate?.error)throw Error(s.appUpdate.error);return s?.appUpdate?.available&&s.appUpdate.manifest.version===next;});proof.checks.baselineNativeRunning=true;proof.checks.nativeAutomaticDiscovery=true;
 await cdp.evaluate(`window.dock.call('expand')`);
 await waitFor('Expanded native navigation',()=>cdp.evaluate(`!!document.querySelector('nav [data-tab="settings"]')`));
 await cdp.evaluate(`document.querySelector('nav [data-tab="settings"]').click();true`);
 await waitFor('Native update button',()=>cdp.evaluate(`(()=>{const b=document.querySelector('[data-action="applyApplication"]');return b&&!b.disabled&&b.textContent.includes('更新并重启');})()`));
 await cdp.evaluate(`document.querySelector('[data-action="applyApplication"]').click();true`);proof.checks.nativeUpdateButtonClicked=true;
 await waitFor('Old native exit after update click',async()=>{if(oldProcess.exitCode!==null)return true;const s=await cdp.evaluate(`window.dock.call('state')`);if(s?.appUpdate?.error)throw Error(s.appUpdate.error);return false;},120000);if(await oldProcess.finished!==0)throw Error('Baseline exited unsuccessfully');cdp.close();cdp=null;
 await installerDiagnostics('after-old-exit');
 const receipt=path.join(profile,'updates/receipt.json');
 const confirmed=await waitFor('New native application health receipt',async()=>{const r=await json(receipt);if(r.status==='rolled-back'||r.status==='rollback-notified')throw Error('Installer rolled back');return r.status==='confirmed'&&r.version===next?r:false;});proof.checks.nativeRestartConfirmed=confirmed.status==='confirmed';
 await waitFor('Installer final cleanup and pointer',async()=>!(await fs.stat(target+'.previous').then(()=>true,()=>false))&&(await json(path.join(profile,'active-app.json'))).exe===path.join(target,'GameDeskSkill.exe'));
 if(!formal&&!proof.candidateDownloadRequests)throw Error('Native update never requested candidate HTTP bytes');proof.checks.downloadHashAndExtract=true;
 const actualInstaller=await fs.readFile(path.join(profile,'updates/apply.ps1'));if(actualInstaller.subarray(0,3).toString('hex')!=='efbbbf')throw Error('Real main wrote installer without UTF-8 BOM');proof.installerScriptSha256=crypto.createHash('sha256').update(actualInstaller).digest('hex');proof.baselineMainSha256=mainHash;proof.baselineUpdaterSha256=updaterHash;
 if(server){await new Promise(r=>server.close(r));server=null;}
 // The same old updater must reject corrupt bytes before installation.
 let rejected=false;try{await oldUpdater.prepare(available.manifest,{repo,root:path.join(base,'corrupt-cache'),platform:'win32',arch:'x64',download:async(_r,_id,_url,dest)=>fs.writeFile(dest,Buffer.alloc(128))});}catch(e){rejected=/哈希/.test(e.message);}if(!rejected)throw Error('Old updater accepted corrupt update');proof.checks.corruptDownloadRejected=true;
 if((await json(path.join(target,'resources/app/package.json'))).version!==next)throw Error('Installed version differs');if((await json(path.join(profile,'active-app.json'))).exe!==path.join(target,'GameDeskSkill.exe'))throw Error('Bootstrap pointer not updated');if(await fs.stat(target+'.previous').then(()=>true,()=>false))throw Error('Healthy installation left backup');proof.checks.installIdentityAndPointer=true;
 const settings=await json(path.join(profile,'settings.json')),saved=settings.games.find(g=>g.id===game.id);if(!saved||Object.entries(game).some(([k,v])=>saved[k]!==v)||settings.projectRoot!==gamePath||!sentinel.equals(await fs.readFile(sentinelPath)))throw Error('User data changed during update');proof.checks.userDataPreserved=true;
 await stopInstalled();
 // Same installed binary, isolated fixture profile: native UI and real local stage reader, no live chats.
 const stageProfile=path.join(base,'upgraded-native-stages'),native=start(path.join(target,'GameDeskSkill.exe'),['--smoke-test','--disable-gpu'],{...env,SKILL_DOCK_DATA_DIR:stageProfile,SKILL_DOCK_SMOKE_EMBEDDED:'1',SKILL_DOCK_SMOKE_E2E:'1',SKILL_DOCK_SMOKE_FIXTURE:'1'},'upgraded-native-stages');
 let timeout;const exit=await Promise.race([native.finished,new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('Upgraded native stage smoke timeout')),180000);})]).finally(()=>clearTimeout(timeout));if(exit!==0)throw Error('Upgraded native stage smoke failed: '+exit);
 const stage=await json(path.join(stageProfile,'native-e2e.json'));for(const k of ['threeStageUI','latestProgressStages','unchangedMetadataRefresh','manualStageOverride','autoStageResume','staleRpcBypassed'])if(stage[k]!==true)throw Error('Upgraded stage regression: '+k);if(stage.multiGameStageCount!==60)throw Error('Missing 60-game native stage fixture');proof.nativeStage=stage;proof.checks.upgradedNativeStageRecognition=true;proof.passed=true;
}
(async()=>{try{await main();}catch(e){proof.passed=false;proof.error=e.stack||e.message;process.exitCode=1;}finally{if(cdp)cdp.close();if(server)server.close();if(process.platform==='win32'&&!proof.passed)try{proof.installerDiagnostics=await installerDiagnostics('failure');}catch{}for(const child of children)try{child.kill();}catch{}if(process.platform==='win32')try{await stopInstalled();}catch(e){proof.cleanupError=e.message;process.exitCode=1;}proof.finishedAt=new Date().toISOString();await fs.mkdir(base,{recursive:true});await fs.writeFile(reportPath,JSON.stringify(proof,null,2));console.log(JSON.stringify({passed:proof.passed,checks:proof.checks,error:proof.error,report:reportPath}));}})();
