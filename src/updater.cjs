const fs=require('node:fs/promises');const path=require('node:path');const crypto=require('node:crypto');const {execFile}=require('node:child_process');const {promisify}=require('node:util');const run=promisify(execFile);const github=require('./github.cjs');
function version(v){const m=String(v).match(/^v?(\d+)\.(\d+)\.(\d+)$/);if(!m)throw Error('软件版本格式无效');return m.slice(1).map(Number);}
function newer(next,current){const a=version(next),b=version(current);for(let i=0;i<3;i++)if(a[i]!==b[i])return a[i]>b[i];return false;}
function manifest(value,repo){if(!value||value.schema!==1||value.kind!=='application'||github.repository(value.repository).toLowerCase()!==github.repository(repo).toLowerCase())throw Error('更新清单无效');version(value.version);if(!value.packages||typeof value.packages!=='object')throw Error('更新包清单无效');for(const [key,p]of Object.entries(value.packages)){if(!['darwin-arm64','darwin-x64','win32-x64','win32-arm64'].includes(key)||!/^[a-f0-9]{64}$/.test(p.sha256)||!Number.isSafeInteger(p.bytes)||p.bytes<1||p.bytes>1024*1024*1024||!Number.isSafeInteger(p.assetId))throw Error('更新包信息无效');const u=new URL(p.url);if(u.protocol!=='https:'||u.hostname!=='github.com'||!u.pathname.toLowerCase().startsWith('/'+repo.toLowerCase()+'/releases/download/'))throw Error('更新包来源与仓库不一致');}return value;}
async function check(repo,current,{api,readAsset,readPublicManifest=github.readPublicUpdateManifest}={}){repo=github.repository(repo);if(!api&&!readAsset)try{const m=manifest(await readPublicManifest(repo),repo);return {available:newer(m.version,current),manifest:m,releaseUrl:'https://github.com/'+repo+'/releases/tag/v'+m.version,notes:'',checkedAt:new Date().toISOString(),source:'public-manifest'};}catch{}api ||= github.api;const release=await api(`repos/${repo}/releases/latest`);if(release.draft||release.prerelease)return {available:false};const asset=(release.assets||[]).find(a=>a.name==='gamedesk-update.json');if(!asset)return {available:false,detail:'尚无工作台更新清单'};let data;if(readAsset)data=await readAsset(asset);else data=await github.api(`repos/${repo}/releases/assets/${asset.id}`,{binary:true});let parsed;try{parsed=JSON.parse(data.toString('utf8'));}catch{throw Error('更新清单无法解析');}const m=manifest(parsed,repo);if(m.version!==String(release.tag_name).replace(/^v/,''))throw Error('发布标签与更新清单版本不一致');return {available:newer(m.version,current),manifest:m,releaseUrl:release.html_url,notes:String(release.body||'').slice(0,4000),checkedAt:new Date().toISOString()};}
function zipEntries(data){let end=-1;for(let n=data.length-22;n>=Math.max(0,data.length-65557);n--)if(data.readUInt32LE(n)===0x06054b50){end=n;break;}if(end<0)throw Error('更新 ZIP 不完整');const count=data.readUInt16LE(end+10);let offset=data.readUInt32LE(end+16),total=0;const entries=[];if(!count||count>25000)throw Error('更新文件数量无效');for(let n=0;n<count;n++){if(offset+46>data.length||data.readUInt32LE(offset)!==0x02014b50)throw Error('ZIP 目录损坏');const length=data.readUInt16LE(offset+28),extra=data.readUInt16LE(offset+30),comment=data.readUInt16LE(offset+32);if(offset+46+length>data.length)throw Error('ZIP 文件名损坏');const name=data.subarray(offset+46,offset+46+length).toString('utf8');if(!name||/[\\:\x00]/.test(name)||name.startsWith('/')||name.split('/').some(p=>p==='..'||p==='.'||/^[a-z]:/i.test(p)))throw Error('ZIP 含不安全路径');if(data.readUInt16LE(offset+8)&1)throw Error('不支持加密更新包');total+=data.readUInt32LE(offset+24);if(total>2*1024*1024*1024)throw Error('更新包解压体积过大');entries.push(name);offset+=46+length+extra+comment;}return entries;}
async function safeLinks(root){async function walk(dir){for(const e of await fs.readdir(dir,{withFileTypes:true})){const p=path.join(dir,e.name),stat=await fs.lstat(p);if(stat.isSymbolicLink()){const resolved=await fs.realpath(p);if(resolved!==root&&!resolved.startsWith(root+path.sep))throw Error('更新包符号链接越界');}else if(stat.isDirectory())await walk(p);}}await walk(root);}
async function prepare(update,{repo,root,platform=process.platform,arch=process.arch,onProgress=()=>{},download=github.downloadAsset}={}){const m=manifest(update,repo),pkg=m.packages[platform+'-'+arch];if(!pkg)throw Error('此平台暂无更新包');const dir=path.join(root,'updates',m.version),archive=path.join(dir,'application.zip');await fs.mkdir(dir,{recursive:true});try{await download(repo,pkg.assetId,pkg.url,archive,onProgress);const data=await fs.readFile(archive);if(data.length!==pkg.bytes||crypto.createHash('sha256').update(data).digest('hex')!==pkg.sha256)throw Error('更新包哈希校验失败');zipEntries(data);const extract=path.join(dir,'extracted');await fs.rm(extract,{recursive:true,force:true});await fs.mkdir(extract);if(process.platform==='win32'){const quote=v=>"'"+v.replaceAll("'","''")+"'";await run('powershell.exe',['-NoProfile','-Command','Expand-Archive -LiteralPath '+quote(archive)+' -DestinationPath '+quote(extract)+' -Force'],{windowsHide:true});}else await run('unzip',['-q',archive,'-d',extract]);await safeLinks(extract);let entry=platform==='darwin'?path.join(extract,'游戏工作台.app'):extract;if(platform==='darwin'){const {stdout}=await run('/usr/libexec/PlistBuddy',['-c','Print :CFBundleIdentifier',path.join(entry,'Contents/Info.plist')]);if(stdout.trim()!=='studio.gamedesk.skill.personal')throw Error('更新包应用身份不匹配');await run('codesign',['--verify','--deep','--strict',entry]);}else{const p=JSON.parse(await fs.readFile(path.join(entry,'resources/app/package.json'),'utf8'));if(p.name!=='skill-game-dock'||p.version!==m.version)throw Error('Windows 更新包身份不匹配');const exe=await fs.readFile(path.join(entry,'GameDeskSkill.exe'));if(exe.subarray(0,2).toString()!=='MZ')throw Error('Windows 更新程序无效');}return {version:m.version,archive,entry};}catch(e){await fs.rm(archive,{force:true});throw e;}}
function sh(v){return "'"+String(v).replaceAll("'","'\\''")+"'";}
function ps(v){return "'"+String(v).replaceAll("'","''")+"'";}
function installerScript({platform,target,candidate,pid,receipt,version:nextVersion,bootstrapPointer,fallbackExe,fallbackArgs=[],startup}){
 if(!Number.isSafeInteger(pid)||pid<1)throw Error('更新进程无效');const backup=target+'.previous',failed=target+'.failed';
 if(platform==='darwin')return `#!/bin/sh
set -eu
n=0
while kill -0 ${pid} 2>/dev/null; do n=$((n+1)); [ "$n" -lt 60 ] || exit 1; sleep 1; done
if [ -e ${sh(backup)} ]; then rm -rf ${sh(backup)}; fi
mv ${sh(target)} ${sh(backup)} || exit 1
if ! mv ${sh(candidate)} ${sh(target)}; then mv ${sh(backup)} ${sh(target)}; open ${sh(target)}; exit 1; fi
printf '%s' ${sh(JSON.stringify({status:'installed',version:nextVersion,backup}))} > ${sh(receipt)}
${sh(path.join(target,'Contents/MacOS/GameDeskSkill'))} >/dev/null 2>&1 &
new_pid=$!
n=0
healthy=0
while [ "$n" -lt 60 ]; do
 if /usr/bin/grep -q '"status"[[:space:]]*:[[:space:]]*"confirmed"' ${sh(receipt)}; then healthy=1; break; fi
 kill -0 "$new_pid" 2>/dev/null || break
 n=$((n+1)); sleep 1
done
if [ "$healthy" = 1 ]; then rm -rf ${sh(backup)}; exit 0; fi
kill -TERM "$new_pid" 2>/dev/null || true
n=0
while kill -0 "$new_pid" 2>/dev/null && [ "$n" -lt 5 ]; do n=$((n+1)); sleep 1; done
kill -KILL "$new_pid" 2>/dev/null || true
if [ -e ${sh(failed)} ]; then rm -rf ${sh(failed)}; fi
mv ${sh(target)} ${sh(failed)}
mv ${sh(backup)} ${sh(target)}
printf '%s' ${sh(JSON.stringify({status:'rolled-back',version:nextVersion,failed,reason:'startup-not-confirmed'}))} > ${sh(receipt)}
open ${sh(target)}
`;
 if(startup&&(!startup.path||!startup.cancelPath||!startup.attemptId||startup.version!==nextVersion||startup.target!==target))throw Error('更新启动握手参数无效');
 const cancelled=startup?`if(Test-Path -LiteralPath ${ps(startup.cancelPath)}){exit 2}`:'';
 const ready=startup?`${cancelled}
$ready=@{status='ready';attemptId=${ps(startup.attemptId)};version=${ps(nextVersion)};target=${ps(target)};pid=$PID} | ConvertTo-Json -Compress
[IO.File]::WriteAllText(${ps(startup.path+'.tmp')},$ready,[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath ${ps(startup.path+'.tmp')} -Destination ${ps(startup.path)} -Force
${cancelled}`:'';
 return `$ErrorActionPreference = 'Stop'
${ready}
Wait-Process -Id ${pid} -Timeout 60 -ErrorAction SilentlyContinue
if(Get-Process -Id ${pid} -ErrorAction SilentlyContinue){exit 1}
${cancelled}
$target=${ps(target)}
$backup=${ps(backup)}
$candidate=${ps(candidate)}
$failed=${ps(failed)}
$newProcess=$null
$hadOld=Test-Path -LiteralPath $target
try {
 if(Test-Path -LiteralPath $backup){Remove-Item -LiteralPath $backup -Recurse -Force}
 if($hadOld){Move-Item -LiteralPath $target -Destination $backup}
 Move-Item -LiteralPath $candidate -Destination $target
 [IO.File]::WriteAllText(${ps(receipt)},${ps(JSON.stringify({status:'installed',version:nextVersion,backup}))},[Text.UTF8Encoding]::new($false))
 $newProcess=Start-Process -FilePath (Join-Path $target 'GameDeskSkill.exe') -PassThru
 $healthy=$false
 for($n=0;$n -lt 60;$n++){
  try {$current=Get-Content -LiteralPath ${ps(receipt)} -Raw | ConvertFrom-Json; if($current.status -eq 'confirmed' -and $current.version -eq ${ps(nextVersion)}){$healthy=$true;break}}catch{}
  if($newProcess.HasExited){break}
  Start-Sleep -Seconds 1
 }
 if(-not $healthy){throw 'New application startup was not confirmed'}
 ${bootstrapPointer?`[IO.File]::WriteAllText(${ps(bootstrapPointer)},${ps(JSON.stringify({exe:path.join(target,'GameDeskSkill.exe')}))},[Text.UTF8Encoding]::new($false))`:''}
 if(Test-Path -LiteralPath $backup){Remove-Item -LiteralPath $backup -Recurse -Force}
} catch {
 if($newProcess -and -not $newProcess.HasExited){Stop-Process -Id $newProcess.Id -Force -ErrorAction SilentlyContinue}
 if(Test-Path -LiteralPath $failed){Remove-Item -LiteralPath $failed -Recurse -Force}
 if(Test-Path -LiteralPath $target){Move-Item -LiteralPath $target -Destination $failed}
 if(Test-Path -LiteralPath $backup){Move-Item -LiteralPath $backup -Destination $target}
 [IO.File]::WriteAllText(${ps(receipt)},${ps(JSON.stringify({status:'rolled-back',version:nextVersion,failed,reason:'startup-not-confirmed'}))},[Text.UTF8Encoding]::new($false))
 if($hadOld -and (Test-Path -LiteralPath (Join-Path $target 'GameDeskSkill.exe'))){Start-Process -FilePath (Join-Path $target 'GameDeskSkill.exe')}
 ${fallbackExe?`elseif(Test-Path -LiteralPath ${ps(fallbackExe)}){Start-Process -FilePath ${ps(fallbackExe)}${fallbackArgs.length?' -ArgumentList @('+fallbackArgs.map(a=>ps('"'+a+'"')).join(',')+')':''}}`:''}
}
`;
}
function installerBytes(script,platform=process.platform){return Buffer.from((platform==='win32'?'\uFEFF':'')+script,'utf8');}
module.exports={installerBytes,version,newer,manifest,check,zipEntries,safeLinks,prepare,installerScript};
