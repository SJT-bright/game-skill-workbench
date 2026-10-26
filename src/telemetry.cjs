'use strict';
// Read only the public rollout path of a scoped Codex thread. Cache derived counters,
// offsets and phase references; never cache message bodies or account balances.
const fs=require('node:fs/promises');
const path=require('node:path');
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const run=promisify(execFile);
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const START=new Set(['task_started','turn_started']);
const END=new Set(['task_complete','task_completed','task_aborted','task_interrupted','turn_complete','turn_completed','turn_aborted','turn_interrupted']);
const COUNTERS=['inputTokens','cachedInputTokens','outputTokens','reasoningOutputTokens','totalTokens'];
const RAW={inputTokens:'input_tokens',cachedInputTokens:'cached_input_tokens',outputTokens:'output_tokens',reasoningOutputTokens:'reasoning_output_tokens',totalTokens:'total_tokens'};
function epoch(value){if(typeof value==='number'&&Number.isFinite(value))return value<1e12?value*1000:value;if(typeof value==='string'){const stamp=Date.parse(value);return Number.isFinite(stamp)?stamp:null;}return null;}
function finite(value){return Number.isSafeInteger(value)&&value>=0?value:null;}
function fresh(threadId,rolloutPath){return {schema:1,threadId,rolloutPath,offset:0,inode:null,identityConfirmed:false,identityMismatch:false,intervals:[],openTasks:{},lastTaskId:null,lastStart:null,lastActivity:null,lastOutcome:null,phaseHistory:[],tokens:null,lastReportedTotal:null,usageDiscontinuity:false,invalidRecords:0,invalidTime:false,historyTruncated:false,draining:false};}
function merged(intervals){const out=[];for(const [start,end] of intervals.filter(i=>Number.isFinite(i[0])&&Number.isFinite(i[1])&&i[1]>=i[0]).sort((a,b)=>a[0]-b[0])){const last=out[out.length-1];if(last&&start<=last[1])last[1]=Math.max(last[1],end);else out.push([start,end]);}return out;}
function messageOf(record){
 const p=record.payload||{};let item=p.type==='item_completed'?p.item:p;
 if(record.type==='response_item')item=p;
 const type=String(item?.type||'').toLowerCase();let role;
 if(type==='usermessage'||type==='user_message'||item?.role==='user')role='user';
 else if(type==='agentmessage'||type==='agent_message'||item?.role==='assistant')role='assistant';
 else return null;
 const content=item.content;
 const text=typeof item.text==='string'?item.text:typeof content==='string'?content:Array.isArray(content)?content.filter(x=>['text','input_text','output_text'].includes(String(x.type).toLowerCase())).map(x=>x.text||'').join('\n'):'';
 if(!text||/^\s*#\s*AGENTS\.md\b/.test(text)||/<(?:environment_context|permissions instructions|collaboration_mode)>/.test(text))return null;
 return {role,text,id:item.id||null};
}
function defaultStage(messages){const text=messages[messages.length-1]?.text||'';const clean=text.replace(/```[\s\S]*?```/g,'');const lines=clean.split(/[\n。！？，,；;]/).map(x=>x.trim()).filter(Boolean);const rules=[['已完成',/(?:本游戏|游戏|项目)(?:已全部完成|已完成交付|全部完成)|最终验收(?:已)?通过/],['待试玩',/待试玩|美工(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)/],['游玩',/正在(?:本地)?试玩|进入(?:本地)?(?:游玩|试玩)阶段|游玩阶段|开始(?:本地)?试玩/],['检查',/检查阶段|进入(?:成品)?检查|开始(?:检查|验收)|正在(?:检查|验收)|检测成品/],['美工制作',/开始(?:做|进行)?美工|进入美工|美工(?:制作|阶段)/],['玩法结束',/玩法(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)/],['玩法制作',/玩法制作|制作玩法|玩法阶段|开始(?:制作|重塑)/]];
 for(let n=lines.length-1;n>=0;n--){const line=lines[n];if(/尚未|还未|未开始|不要|暂不|未完成|未通过|之前|此前|历史|上次|不代表|之后|下一阶段|下一步|接下来|后续|计划/.test(line))continue;for(const [stage,re]of rules)if(re.test(line))return {stage};}return {stage:null};}
function applyRecord(state,record,{now=Date.now(),classifyStage=defaultStage}={}){
 const p=record.payload;if(!p||typeof p!=='object')return;
 if(record.type==='session_meta'){
  const id=p.id||p.session_id;if(id!==state.threadId){state.identityMismatch=true;return;}
  state.identityConfirmed=true;state.sessionSource=typeof p.source==='string'?p.source:'subagent';state.originator=typeof p.originator==='string'?p.originator:null;state.inherited=!!(p.forked_from_id||p.parent_thread_id);return;
 }
 if(!state.identityConfirmed||state.identityMismatch)return;
 const stamp=epoch(record.timestamp||p.timestamp);if(stamp===null||stamp>now+30000){state.invalidTime=true;return;}
 const kind=p.type;const turn=String(p.turn_id||p.turnId||p.task_id||p.turn_attribution?.turn_id||p.root_turn_id||'');
 if(record.type==='event_msg'){
  if(START.has(kind)){
   const start=epoch(p.started_at)??stamp;if(start>now+30000){state.invalidTime=true;return;}
   const key=turn||'anonymous-'+start;state.openTasks[key]=Math.min(state.openTasks[key]??start,start);state.lastTaskId=key;state.lastStart=Math.max(state.lastStart??0,start);state.lastOutcome='open';
  }else if(END.has(kind)){
   const key=turn||state.lastTaskId;const end=epoch(p.completed_at)??stamp;const duration=finite(p.duration_ms);let start=state.openTasks[key]??epoch(p.started_at);
   if(duration!==null)start=end-duration;
   if(start!==null&&start!==undefined&&start<=end&&start>=0){state.intervals=merged(state.intervals.concat([[start,end]]));if(state.intervals.length>4096){state.intervals=state.intervals.slice(-4096);state.historyTruncated=true;}}
   else state.missingDuration=true;
   if(key)delete state.openTasks[key];state.lastOutcome=/abort|interrupt/.test(kind)?'interrupted':'completed';state.lastEnd=end;
  }
  if(kind==='token_count'){
   const raw=p.info?.total_token_usage||p.total_token_usage;
   if(raw&&finite(raw.total_tokens)!==null){
    const total=raw.total_tokens;if(state.lastReportedTotal!==null&&total<state.lastReportedTotal)state.usageDiscontinuity=true;state.lastReportedTotal=total;
    const previous=state.tokens?.totalTokens??0;
    if(!state.tokens||total>=previous){const tokens={};for(const key of COUNTERS)tokens[key]=finite(raw[RAW[key]]);state.tokens=tokens;const phase=state.phaseHistory[state.phaseHistory.length-1];if(phase)phase.tokens=(phase.tokens||0)+Math.max(0,total-previous);}
   }
   const quota=p.rate_limits;if(quota){const q={scope:'account',source:'codex-rate-limit-snapshot'};for(const key of ['primary','secondary'])if(quota[key]&&typeof quota[key].used_percent==='number')q[key]={usedPercent:quota[key].used_percent,windowMinutes:quota[key].window_minutes??null,resetsAt:quota[key].resets_at??null};if(q.primary||q.secondary){q.at=new Date(stamp).toISOString();state.accountUsage=q;}}
  }
  if(!turn||state.openTasks[turn]!==undefined||START.has(kind)||END.has(kind))state.lastActivity=Math.max(state.lastActivity??0,stamp);
 }
 const message=messageOf(record);if(message){const classified=classifyStage([message]);const stage=classified?.stage;if(stage&&state.phaseHistory[state.phaseHistory.length-1]?.stage!==stage){state.phaseHistory.push({stage,at:new Date(stamp).toISOString(),turnId:turn||null,itemId:message.id,role:message.role,source:'explicit-message',tokens:0});if(state.phaseHistory.length>512){state.phaseHistory=state.phaseHistory.slice(-512);state.historyTruncated=true;}}}
}
function currentState(thread,state,desktop,complete,now){
 const raw=thread.metadataStatus||thread.status;const kind=typeof raw==='object'?raw?.type:raw;const flags=typeof raw==='object'?raw?.activeFlags||[]:[];
 if(kind==='active')return {active:true,status:flags.includes('waitingOnApproval')?'waitingOnApproval':flags.includes('waitingOnUserInput')?'waitingOnUserInput':'active'};
 if(kind==='idle')return {active:false,status:state.lastOutcome==='interrupted'?'interrupted':'idle'};
 if(kind==='systemError')return {active:null,status:'error'};
 if(!complete||state.identityMismatch)return {active:null,status:'unknown'};
 const open=Object.values(state.openTasks);
 if(!open.length){if(state.lastOutcome==='interrupted')return {active:false,status:'interrupted'};if(state.lastOutcome==='completed')return {active:false,status:'idle'};return {active:null,status:'unknown'};}
 // A cold helper's notLoaded state is never proof of desktop idleness. For an
 // unclosed task require events from the current desktop generation.
 const boot=desktop?.bootMs;if(desktop?.running&&Number.isFinite(boot)&&Math.max(state.lastStart||0,state.lastActivity||0)>=boot-1000)return {active:true,status:'active'};
 return {active:null,status:'unknown'};
}
function project(thread,state,{now=Date.now(),complete=false,desktop}={}){
 const known=state.identityConfirmed&&!state.identityMismatch;const activity=currentState(thread,state,desktop,known&&complete,now);
 const open=Object.values(state.openTasks);const closed=merged(state.intervals);let intervals=closed;
 if(activity.active===true&&complete)intervals=merged(closed.concat(open.filter(s=>s<=now).map(s=>[s,now])));
 const elapsed=intervals.length?intervals.reduce((n,[a,b])=>n+b-a,0):null;const current=activity.active===true&&complete&&open.length?Math.max(0,now-Math.min(...open)):null;
 const history=state.phaseHistory.map((h,i)=>{const begin=epoch(h.at),end=epoch(state.phaseHistory[i+1]?.at)??now;const duration=intervals.reduce((n,[a,b])=>n+Math.max(0,Math.min(b,end)-Math.max(a,begin)),0);return {...h,elapsedMs:duration,totalTokens:h.tokens||0};});
 const totals={};for(const h of history){const t=totals[h.stage]||(totals[h.stage]={elapsedMs:0,totalTokens:0});t.elapsedMs+=h.elapsedMs;t.totalTokens+=h.totalTokens;}
 const latest=history[history.length-1]||null;const stageCurrent=!!latest&&epoch(latest.at)>=(state.lastStart||0);
 const value={active:activity.active,status:activity.status,elapsedMs:known?elapsed:null,currentElapsedMs:known?current:null,recordedElapsedMs:known&&closed.length?closed.reduce((n,[a,b])=>n+b-a,0):null,totalTokens:null,inputTokens:null,outputTokens:null,cachedInputTokens:null,reasoningOutputTokens:null,stageHistory:known?history:[],stageTotals:known?totals:{},latestStage:known?latest?.stage||null:null,latestStageAt:known?latest?.at||null:null,latestStageCurrent:known&&stageCurrent,source:'codex-rollout-events',complete:!!(known&&complete&&!state.invalidRecords&&!state.invalidTime&&!state.historyTruncated),timeComplete:!!(known&&complete&&(state.lastStart!==null||state.lastEnd!==undefined)&&!state.missingDuration&&!state.historyTruncated&&(!open.length||activity.active===true)),tokenComplete:!!(known&&complete&&state.tokens&&!state.usageDiscontinuity&&!state.inherited&&!thread.forkedFromId),usageBasis:state.usageDiscontinuity?'observed-cumulative-maximum':'thread-cumulative-counter',cost:null,checkedAt:new Date(now).toISOString()};
 if(known&&state.tokens)for(const key of COUNTERS)value[key]=state.tokens[key];
 if(known&&state.accountUsage)value.accountUsage=state.accountUsage;
 if(state.identityMismatch)value.reason='thread-identity-mismatch';else if(!known)value.reason='identity-unavailable';else if(!complete)value.reason='index-incomplete';else if(state.usageDiscontinuity)value.reason='usage-counter-reset';
 return value;
}
async function desktopGeneration(){
 try{if(process.platform==='darwin'){
  const {stdout}=await run('/bin/ps',['-axo','pid=,lstart=,comm='],{timeout:2000,maxBuffer:1024*1024});const rows=[];
  for(const line of stdout.split('\n')){const m=line.match(/^\s*(\d+)\s+(.{24})\s+.*\/(?:Codex|ChatGPT)\.app\/Contents\/MacOS\/(?:Codex|ChatGPT)\s*$/);if(m){const bootMs=Date.parse(m[2]);if(Number.isFinite(bootMs))rows.push({pid:Number(m[1]),bootMs});}}
  rows.sort((a,b)=>b.bootMs-a.bootMs);return rows.length?{known:true,running:true,...rows[0]}:{known:true,running:false,bootMs:null};
 }if(process.platform==='win32'){
  const script="@(Get-Process -Name Codex,ChatGPT -ErrorAction SilentlyContinue | Select-Object Id,@{Name='bootMs';Expression={[DateTimeOffset]::new($_.StartTime).ToUnixTimeMilliseconds()}}) | ConvertTo-Json -Compress";
  const {stdout}=await run('powershell.exe',['-NoProfile','-Command',script],{timeout:2500,maxBuffer:65536,windowsHide:true});const value=stdout.trim()?JSON.parse(stdout):[];const rows=(Array.isArray(value)?value:[value]).filter(x=>Number.isFinite(x.bootMs)).sort((a,b)=>b.bootMs-a.bootMs);return rows.length?{known:true,running:true,pid:rows[0].Id,bootMs:rows[0].bootMs}:{known:true,running:false,bootMs:null};
 }}catch{}return {known:false,running:null,bootMs:null};
}
async function telemetryForThread(thread,{state:previous,now=Date.now(),desktop,maxBytes=64*1024*1024,maxLineBytes=256*1024,deadline=Date.now()+1500,classifyStage=defaultStage}={}){
 const id=thread.threadId||thread.id;const file=thread.rolloutPath||thread.publicPath;let state=previous&&previous.schema===1&&previous.threadId===id?structuredClone(previous):fresh(id,file);
 if(!UUID.test(String(id))||typeof file!=='string'||path.extname(file).toLowerCase()!=='.jsonl')return {telemetry:{...project(thread,state,{now,desktop,complete:false}),reason:'missing-public-path'},state};
 let handle;let readBytes=0;
 try{const stat=await fs.stat(file);const inode=String(stat.dev)+':'+String(stat.ino);if(!stat.isFile())throw Error('not-file');if(state.rolloutPath!==file||state.inode!==inode||state.offset>stat.size)state=fresh(id,file);state.inode=inode;handle=await fs.open(file,'r');let position=state.offset,pending=[],pendingSize=0;
  while(position<stat.size&&readBytes<maxBytes&&Date.now()<deadline){const count=Math.min(64*1024,stat.size-position,maxBytes-readBytes);const buffer=Buffer.allocUnsafe(count);const {bytesRead}=await handle.read(buffer,0,count,position);if(!bytesRead)break;const chunk=buffer.subarray(0,bytesRead),base=position;position+=bytesRead;readBytes+=bytesRead;let cursor=0;
   while(cursor<chunk.length){const nl=chunk.indexOf(10,cursor),end=nl<0?chunk.length:nl;const part=chunk.subarray(cursor,end),absolute=base+(nl<0?chunk.length:nl+1);
    if(state.draining){if(nl>=0)state.draining=false;state.offset=absolute;}
    else if(pendingSize+part.length>maxLineBytes){const prefix=Buffer.concat([...pending,part.subarray(0,Math.min(part.length,1500))]).subarray(0,2000).toString('utf8');if(/"type"\s*:\s*"(?:task_started|turn_started|task_complete|task_completed|task_aborted|turn_aborted|token_count)"/.test(prefix))state.invalidRecords++;state.draining=nl<0;pending=[];pendingSize=0;state.offset=absolute;}
    else {if(part.length){pending.push(part);pendingSize+=part.length;}if(nl>=0){const line=Buffer.concat(pending,pendingSize).toString('utf8');if(/"type"\s*:\s*"(?:session_meta|event_msg|response_item)"/.test(line.slice(0,220))){try{const record=JSON.parse(line);applyRecord(state,record,{now,classifyStage});}catch{state.invalidRecords++;}}state.offset=absolute;pending=[];pendingSize=0;}}
    cursor=nl<0?chunk.length:nl+1;
   }
  }
  const final=await handle.stat();const complete=state.offset>=final.size&&!state.draining;state.complete=complete;state.readBytes=readBytes;state.checkedAt=new Date(now).toISOString();return {telemetry:{...project(thread,state,{now,desktop,complete}),readBytes},state};
 }catch(e){return {telemetry:{...project(thread,state,{now,desktop,complete:false}),reason:e.code==='ENOENT'?'rollout-unavailable':'rollout-read-failed',readBytes},state};}
 finally{await handle?.close();}
}
async function scanTelemetries(threads,{cache={},now=Date.now(),desktop,classifyStage=defaultStage,budgetMs=6000,maxBytes=64*1024*1024,maxLineBytes}={}){
 const generation=desktop===undefined?await desktopGeneration():desktop;const deadline=Date.now()+budgetMs,byThread={},nextCache={...cache};let complete=true;
 for(const thread of threads){const id=thread.threadId||thread.id;const result=await telemetryForThread(thread,{state:cache[id],now,desktop:generation,classifyStage,maxBytes,maxLineBytes,deadline});byThread[id]=result.telemetry;nextCache[id]=result.state;complete=complete&&result.telemetry.complete;}
 return {byThread,cache:nextCache,complete,checkedAt:new Date(now).toISOString()};
}
module.exports={telemetryForThread,scanTelemetries,desktopGeneration,applyRecord,project,defaultStage,epoch,fresh,merged};
