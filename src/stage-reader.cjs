const fs=require('node:fs/promises'),path=require('node:path'),{VERSION,inferStage,messageOf}=require('./stage-detection.cjs');
async function readLatestStage(thread,{previous,maxBytes=1024*1024}={}){
 const id=thread.threadId||thread.id,file=thread.rolloutPath||thread.path;if(!file||!path.isAbsolute(file))return {available:false,reason:'no-rollout'};
 let handle;try{
  handle=await fs.open(file,'r');const stat=await handle.stat();if(!stat.isFile())return {available:false,reason:'not-file'};
  const stamp={path:file,inode:String(stat.ino),size:stat.size,mtime:stat.mtimeMs,algorithmVersion:VERSION};
  if(previous?.rolloutStamp&&Object.keys(stamp).every(key=>previous.rolloutStamp[key]===stamp[key])&&previous.stageInfo?.algorithmVersion===VERSION)return {available:true,stageInfo:previous.stageInfo,rolloutStamp:stamp,contextStatus:'local-cached'};
  const head=Buffer.alloc(Math.min(65536,stat.size));await handle.read(head,0,head.length,0);const end=head.indexOf(10);if(end<0)return {available:false,reason:'identity-unavailable'};
  let meta;try{meta=JSON.parse(head.subarray(0,end).toString('utf8').replace(/^\uFEFF/,''));}catch{return {available:false,reason:'identity-unavailable'};}
  if(meta.type!=='session_meta'||String(meta.payload?.id).toLowerCase()!==String(id).toLowerCase())return {available:false,reason:'identity-mismatch'};
  const length=Math.min(stat.size,maxBytes),start=stat.size-length,tail=Buffer.alloc(length);await handle.read(tail,0,length,start);let text=tail.toString('utf8');if(start)text=text.slice(text.indexOf('\n')+1);
  const messages=[];for(const line of text.split('\n')){if(!/"type"\s*:\s*"(?:event_msg|response_item)"/.test(line.slice(0,250)))continue;try{const m=messageOf(JSON.parse(line));if(m)messages.push(m);}catch{}}
  const old=previous?.rolloutStamp,canContinue=old?.algorithmVersion===VERSION&&old.path===file&&old.inode===stamp.inode&&old.size<=stamp.size;
  return {available:true,stageInfo:inferStage(messages.slice(-120),{previous:canContinue?previous.stageInfo:undefined}),rolloutStamp:stamp,contextStatus:'local-read',messageCount:messages.length};
 }catch{return {available:false,reason:'rollout-unavailable'};}finally{await handle?.close();}
}
module.exports={readLatestStage};
