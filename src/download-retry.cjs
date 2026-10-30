'use strict';
const fs=require('node:fs/promises');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function discardSmall(response){if(!response.body)return;let bytes=0;try{for await(const chunk of response.body){bytes+=chunk.length;if(bytes>8192)break;}}catch{}}
function failure(message,{retryable=true,reset=false,status}={}){const error=Error(message);Object.assign(error,{retryable,reset,status});return error;}
// Partial data is retained only within this bounded operation. The caller must still
// verify the release manifest's byte count and SHA-256 before extracting/installing.
async function downloadWithRetry(url,dest,{fetchFn=fetch,onProgress=()=>{},validateUrl=()=>{},limit=1024*1024*1024,attempts=4,idleMs=30000,attemptMs=4*60*1000,totalMs=10*60*1000,backoffMs=500}={}){
 let offset=0,expected=null,validator=null,lastError;const deadline=Date.now()+totalMs;
 await fs.writeFile(dest,Buffer.alloc(0),{mode:0o600});
 try{for(let attempt=0;attempt<attempts&&Date.now()<deadline;attempt++){
  const controller=new AbortController();let idle,timedOut=false;const touch=()=>{clearTimeout(idle);idle=setTimeout(()=>{timedOut=true;controller.abort();},idleMs);};
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},Math.max(1,Math.min(attemptMs,deadline-Date.now())));let handle,response;
  try{
   touch();let target=url;const headers={'Accept-Encoding':'identity'};if(offset){headers.Range='bytes='+offset+'-';if(validator)headers['If-Range']=validator;}
   for(let redirect=0;;redirect++){
    try{validateUrl(target);}catch(error){error.retryable=false;throw error;}response=await fetchFn(target,{headers,credentials:'omit',redirect:'manual',signal:controller.signal});touch();
    if(![301,302,303,307,308].includes(response.status))break;
    const location=response.headers.get('location');await response.body?.cancel();if(!location||redirect>=5)throw failure('更新下载重定向无效',{retryable:false});target=new URL(location,target).href;
   }
   if(response.status===416){await discardSmall(response);throw failure('更新续传范围已失效，将重新下载',{reset:true});}
   if(response.status!==200&&response.status!==206){await discardSmall(response);throw failure('更新下载请求失败 ('+response.status+')',{status:response.status,retryable:[408,429].includes(response.status)||response.status>=500});}
   const encoding=response.headers.get('content-encoding');if(encoding&&encoding!=='identity')throw failure('更新下载编码不支持续传',{retryable:false});
   const lengthHeader=response.headers.get('content-length');const length=lengthHeader===null?null:Number(lengthHeader);if(length!==null&&(!Number.isSafeInteger(length)||length<0||length>limit))throw failure('更新文件大小无效',{retryable:false});
   const tag=response.headers.get('etag');const nextValidator=tag&&!tag.startsWith('W/')?tag:response.headers.get('last-modified');let responseExpected=null;
   if(response.status===206){
    const range=response.headers.get('content-range')?.match(/^bytes (\d+)-(\d+)\/(\d+)$/);const start=Number(range?.[1]),end=Number(range?.[2]),total=Number(range?.[3]);
    if(!range||![start,end,total].every(Number.isSafeInteger)||start!==offset||end<start||end>=total||total>limit||(length!==null&&length!==end-start+1)||(expected!==null&&total!==expected)||(validator&&nextValidator&&validator!==nextValidator))throw failure('更新续传响应不匹配，将重新下载',{reset:true});
    expected=total;responseExpected=end+1;
   }else{
    // Servers may ignore Range or reject If-Range: never append a full 200 body.
    offset=0;expected=length;validator=null;await fs.truncate(dest,0);onProgress(0);
   }
   validator=nextValidator||validator;if(!response.body)throw failure('更新下载响应没有内容');
   handle=await fs.open(dest,'r+');for await(const chunk of response.body){
    const data=Buffer.from(chunk);if(offset+data.length>limit||(expected!==null&&offset+data.length>expected)||(responseExpected!==null&&offset+data.length>responseExpected))throw failure('更新文件超出声明大小',{reset:true});
    let written=0;while(written<data.length){const result=await handle.write(data,written,data.length-written,offset);if(!result.bytesWritten)throw failure('更新文件写入失败',{retryable:false});written+=result.bytesWritten;offset+=result.bytesWritten;}
    touch();onProgress(offset);
   }
   if((responseExpected!==null&&offset!==responseExpected)||(expected!==null&&offset!==expected))throw failure('更新下载未完成，将继续下载');
   return {bytes:offset,attempts:attempt+1};
  }catch(error){
   lastError=timedOut?failure('更新下载超时或长时间无进度，已尝试自动重连'):error;
   if(error.reset){offset=0;expected=null;validator=null;await fs.truncate(dest,0);onProgress(0);}
   if(error.retryable===false||['ENOSPC','EACCES','EPERM','EROFS','EIO'].includes(error.code))throw lastError;
  }finally{clearTimeout(timer);clearTimeout(idle);await response?.body?.cancel().catch(()=>{});if(!response)controller.abort();await handle?.close();}
  if(attempt+1<attempts&&Date.now()<deadline)await wait(Math.min(backoffMs*2**attempt,Math.max(0,deadline-Date.now())));
 }
 throw lastError||failure('更新下载超时，请稍后重试');
 }catch(error){await fs.rm(dest,{force:true});throw error;}
}
module.exports={downloadWithRetry};
