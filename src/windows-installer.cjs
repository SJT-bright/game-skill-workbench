'use strict';
const fs=require('node:fs/promises');const path=require('node:path');const {spawn}=require('node:child_process');
const quote=value=>"'"+String(value).replaceAll("'","''")+"'";
function commandFor(scriptPath,logPath){const script=`$ErrorActionPreference = 'Stop'; try { & ${quote(scriptPath)} *>> ${quote(logPath)} } catch { $_ | Out-String | Add-Content -LiteralPath ${quote(logPath)}; exit 1 }`;return 'start "" /b powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand '+Buffer.from(script,'utf16le').toString('base64');}
const sameTarget=(a,b)=>typeof a==='string'&&path.win32.normalize(a).toLowerCase()===path.win32.normalize(b).toLowerCase();
async function launchWindowsInstaller({scriptPath,startup,logPath,timeoutMs=10000,pollMs=100,spawnFn=spawn}={}){
 if(!startup?.path||!startup.cancelPath||!startup.attemptId||!startup.version||!startup.target||!scriptPath||!logPath)throw Error('Windows 更新启动参数不完整');
 await fs.mkdir(path.dirname(logPath),{recursive:true});await fs.mkdir(path.dirname(startup.path),{recursive:true});
 const log=async message=>fs.appendFile(logPath,new Date().toISOString()+' '+message+'\n').catch(()=>{});
 await log('installer launch '+startup.attemptId+' '+startup.version);
 let child,error,exitCode,settled=false;const start=Date.now();
 try{
  // A non-detached hidden cmd owns a console; START /B transfers that console to
  // PowerShell 5.1. Direct detached + hidden PowerShell may exit before its script.
  const cmd=process.env.ComSpec||'cmd.exe';child=spawnFn(cmd,['/d','/s','/c',commandFor(scriptPath,logPath)],{detached:false,windowsHide:true,windowsVerbatimArguments:true,stdio:'ignore'});
  child.on('error',e=>{error=e;});child.on('exit',code=>{exitCode=code;});
  while(Date.now()-start<timeoutMs){
   if(error)throw Error('Windows 更新启动失败：'+error.message);
   if(exitCode!==undefined&&exitCode!==0)throw Error('Windows 更新启动桥提前退出 ('+exitCode+')');
   let ready;try{ready=JSON.parse((await fs.readFile(startup.path,'utf8')).replace(/^\uFEFF/,''));}catch(e){if(e.code!=='ENOENT')throw Error('Windows 更新启动握手无法读取');}
   if(ready){if(ready.status!=='ready'||ready.attemptId!==startup.attemptId||ready.version!==startup.version||!sameTarget(ready.target,startup.target)||!Number.isSafeInteger(ready.pid)||ready.pid<1)throw Error('Windows 更新启动握手不匹配');
    await log('installer ready '+startup.attemptId+' pid='+ready.pid);settled=true;child.unref?.();return ready;
   }
   await new Promise(resolve=>setTimeout(resolve,Math.min(pollMs,Math.max(1,timeoutMs-(Date.now()-start)))));
  }
  throw Error('Windows 更新安装器未就绪，已保留当前版本；请查看更新日志');
 }catch(e){
  // Persist before rejecting: a delayed PowerShell must not install on a later
  // ordinary app exit. Unique attempt paths prevent one retry cancelling another.
  const tmp=startup.cancelPath+'.tmp';await fs.mkdir(path.dirname(startup.cancelPath),{recursive:true});await fs.writeFile(tmp,JSON.stringify({status:'cancelled',attemptId:startup.attemptId,version:startup.version,target:startup.target,at:new Date().toISOString()}));await fs.rename(tmp,startup.cancelPath);await log('installer cancelled '+startup.attemptId+': '+e.message);if(!settled)child?.unref?.();throw e;
 }
}
module.exports={launchWindowsInstaller,commandFor};
