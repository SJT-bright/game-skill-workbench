const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');const {execFile,spawn}=require('node:child_process');
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const READ_LIMIT=70*1024*1024,DOWNLOAD_LIMIT=1024*1024*1024;
function repository(value){const repo=String(value||'').trim().replace(/^https:\/\/github.com\//,'').replace(/\.git$/,'').replace(/\/$/,'');if(!REPO.test(repo)||repo.includes('..'))throw Error('GitHub 仓库格式应为 owner/repo');return repo;}
async function ghBinary(){const home=os.homedir();for(const p of ['/opt/homebrew/bin/gh','/usr/local/bin/gh',path.join(home,'.local/bin/gh'),path.join(process.env.ProgramFiles||'C:\\Program Files','GitHub CLI/gh.exe'),...(process.env.PATH||'').split(path.delimiter).map(p=>path.join(p,process.platform==='win32'?'gh.exe':'gh'))])if(await fs.stat(p).then(s=>s.isFile(),()=>false))return p;return null;}
function acceptType(endpoint,binary){return binary?(/\/releases\/assets\//.test(endpoint)?'application/octet-stream':'application/vnd.github.raw+json'):'application/vnd.github+json';}
function requestFetch(input,options){
 // Chromium handles system proxies/PAC in the desktop app. Node-only tools retain normal fetch.
 if(process.versions?.electron&&process.type!=='renderer')try{const electron=require('electron');if(electron.net?.fetch&&(!electron.app||electron.app.isReady()))return electron.net.fetch(input,options);}catch{}
 return fetch(input,options);
}
async function responseBytes(response,limit=READ_LIMIT){const declared=Number(response.headers?.get?.('content-length'));if(declared>limit)throw Error('GitHub 响应过大');let total=0;const chunks=[];if(response.body){for await(const chunk of response.body){const data=Buffer.from(chunk);total+=data.length;if(total>limit)throw Error('GitHub 响应过大');chunks.push(data);}return Buffer.concat(chunks);}const data=Buffer.from(await response.arrayBuffer());if(data.length>limit)throw Error('GitHub 响应过大');return data;}
function httpError(status){const error=Error(status===404?'仓库、发布或文件不存在；私有仓库需要 GitHub CLI 登录':status===401||status===403?'GitHub 读取未获授权或达到限额':'GitHub 请求失败 '+status);error.status=status;return error;}
function ghRead(gh,endpoint,binary){return new Promise((resolve,reject)=>execFile(gh,['api',endpoint,'--hostname','github.com','--header','Accept: '+acceptType(endpoint,binary)],{encoding:binary?null:'utf8',maxBuffer:READ_LIMIT,timeout:30000,windowsHide:true,env:{...process.env,GODEBUG:'http2client=0'}},(e,out,stderr)=>{if(e){const error=Error('GitHub 认证读取失败');error.status=Number(String(stderr||'').match(/HTTP\s+(\d{3})/)?.[1])||null;return reject(error);}try{resolve(binary?out:JSON.parse(out));}catch{reject(Error('GitHub 响应无效'));}}));}
async function anonymousApi(endpoint,binary){const response=await requestFetch('https://api.github.com/'+endpoint,{headers:{Accept:acceptType(endpoint,binary)},credentials:'omit',signal:AbortSignal.timeout(20000)});if(!response.ok)throw httpError(response.status);const data=await responseBytes(response);if(binary)return data;try{return JSON.parse(data.toString('utf8'));}catch{throw Error('GitHub 响应无效');}}
async function api(endpoint,{binary=false}={}){
 if(!/^repos\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\//.test(endpoint))throw Error('GitHub API 路径无效');
 const gh=await ghBinary();let authenticatedError;
 if(gh)try{return await ghRead(gh,endpoint,binary);}catch(e){authenticatedError=e;}
 // An installed but logged-out/expired gh must not prevent anonymous access to public data.
 try{return await anonymousApi(endpoint,binary);}catch(e){if(authenticatedError?.status)e.authenticatedStatus=authenticatedError.status;throw e;}
}
async function apiWrite(endpoint,body,{method='POST'}={}){
 const valid=/^repos\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/git\/(blobs|trees|commits|refs\/heads\/main)$/.test(endpoint);
 const reference=endpoint.endsWith('/refs/heads/main');
 if(!valid||(reference?method!=='PATCH':method!=='POST')||(reference&&body?.force!==false))throw Error('GitHub 写入范围无效');
 const gh=await ghBinary();if(!gh)throw Error('发布需要先登录 GitHub CLI');
 const input=JSON.stringify(body);if(Buffer.byteLength(input)>90*1024*1024)throw Error('GitHub 发布内容过大');
 return new Promise((resolve,reject)=>{
  const child=execFile(gh,['api',endpoint,'--hostname','github.com','--method',method,'--header','Accept: application/vnd.github+json','--input','-'],{encoding:'utf8',maxBuffer:4*1024*1024,timeout:120000,windowsHide:true,env:{...process.env,GODEBUG:'http2client=0'}},(e,out,stderr)=>{
   if(e){const status=Number(String(stderr||'').match(/HTTP\s+(\d{3})/)?.[1])||null;const error=Error(status===409||status===422?'GitHub 分支已变化，请重试发布':'GitHub 发布未完成，请检查登录、权限或网络');error.status=status;error.cause=e;return reject(error);}
   try{resolve(JSON.parse(out));}catch{reject(Error('GitHub 写入回执无效'));}
  });
  child.stdin.on('error',()=>{});child.stdin.end(input);
 });
}
async function readFeed(repo,route){
 repo=repository(repo);let file=route.replace(/^\//,'');if(/^releases\/[A-Za-z0-9_-]+$/.test(file))file+='.json';if(!/^(index\.json|releases\/[A-Za-z0-9_-]+\.json|blobs\/[a-f0-9]{64})$/.test(file))throw Error('Skill 文件路径无效');
 // Public Skill polling uses raw rather than the anonymous REST quota (60 requests/hour).
 const suffix=file==='index.json'?'?t='+Math.floor(Date.now()/60000):'';
 try{const response=await requestFetch(`https://raw.githubusercontent.com/${repo}/skills-feed/${file}${suffix}`,{headers:{'Cache-Control':'no-cache'},credentials:'omit',signal:AbortSignal.timeout(20000)});if(!response.ok)throw httpError(response.status);return await responseBytes(response);}catch{}
 // Private feeds and transient raw failures can still use the user's existing gh authentication.
 return api(`repos/${repo}/contents/${file}?ref=skills-feed`,{binary:true});
}
function downloadWithGh(gh,repo,assetId,dest,onProgress){return (async()=>{
 const handle=await fs.open(dest,'w',0o600);try{
  await new Promise((resolve,reject)=>{
   let settled=false,lastSize=0,lastProgress=Date.now(),checking=false,killTimer;
   const child=spawn(gh,['api',`repos/${repo}/releases/assets/${assetId}`,'--hostname','github.com','--header','Accept: application/octet-stream'],{stdio:['ignore',handle.fd,'pipe'],windowsHide:true,env:{...process.env,GODEBUG:'http2client=0'}});
   const done=error=>{if(settled)return;settled=true;clearTimeout(timer);clearInterval(progress);if(error&&child.exitCode===null){child.kill('SIGTERM');killTimer=setTimeout(()=>{if(child.exitCode===null)child.kill('SIGKILL');},1000);killTimer.unref();}error?reject(error):resolve();};
   const timer=setTimeout(()=>done(Error('更新认证下载超时')),3*60*1000);
   const progress=setInterval(async()=>{if(checking||settled)return;checking=true;try{const stat=await fs.stat(dest);if(settled)return;if(stat.size>lastSize){lastSize=stat.size;lastProgress=Date.now();onProgress(stat.size);}if(stat.size>DOWNLOAD_LIMIT)done(Error('更新文件过大'));else if(Date.now()-lastProgress>30000)done(Error('更新认证下载长时间无进度'));}catch(e){done(e);}finally{checking=false;}},600);
   child.stderr.on('data',()=>{});child.on('error',()=>done(Error('GitHub 下载进程无法启动')));child.on('close',code=>{clearTimeout(killTimer);done(code===0?null:Error('GitHub 认证下载失败'));});
  });
  const stat=await fs.stat(dest);if(stat.size>DOWNLOAD_LIMIT)throw Error('更新文件过大');onProgress(stat.size);
 }finally{await handle.close();}
})();}
function validateDownloadUrl(url){const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password||!['github.com','objects.githubusercontent.com','release-assets.githubusercontent.com'].includes(u.hostname))throw Error('更新下载地址无效');}
async function downloadAsset(repo,assetId,url,dest,onProgress=()=>{}){
 repo=repository(repo);validateDownloadUrl(url);await fs.mkdir(path.dirname(dest),{recursive:true});
 // Public release assets do not need gh login or an authenticated API round trip.
 try{return await require('./download-retry.cjs').downloadWithRetry(url,dest,{fetchFn:requestFetch,onProgress,validateUrl:validateDownloadUrl,limit:DOWNLOAD_LIMIT});}
 catch(error){
  // Private releases retain the existing authenticated transport. Do not turn
  // disk/protocol failures into another long download with a different client.
  if(![401,403,404].includes(error.status))throw error;
  const gh=await ghBinary();if(!gh||!Number.isSafeInteger(assetId)||assetId<1)throw error;
  try{await downloadWithGh(gh,repo,assetId,dest,onProgress);}catch(e){await fs.rm(dest,{force:true});e.status ||= error.status;throw e;}
 }
}
async function readPublicUpdateManifest(repo){repo=repository(repo);const response=await requestFetch(`https://github.com/${repo}/releases/latest/download/gamedesk-update.json?t=${Math.floor(Date.now()/60000)}`,{credentials:'omit',headers:{'Cache-Control':'no-cache'},signal:AbortSignal.timeout(20000)});if(!response.ok)throw httpError(response.status);const data=await responseBytes(response,128*1024);try{return JSON.parse(data.toString('utf8'));}catch{throw Error('工作台更新清单无法解析');}}
module.exports={readPublicUpdateManifest,repository,ghBinary,api,apiWrite,readFeed,downloadAsset};
