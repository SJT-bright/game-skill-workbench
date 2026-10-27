const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');const {spawn}=require('node:child_process');const readline=require('node:readline');
const activeReaders=new Set();
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const STAGES=['玩法制作','玩法结束','美工制作','待试玩','游玩','检查','已完成'];
const READ_METHODS=new Set(['initialize','thread/list','thread/turns/list','thread/items/list']);
async function executable(){
 const home=os.homedir(),platform=process.platform,arch=process.arch;const triple=platform==='win32'?(arch==='arm64'?'aarch64-pc-windows-msvc':'x86_64-pc-windows-msvc'):(arch==='arm64'?'aarch64-apple-darwin':'x86_64-apple-darwin');
 const bases=[path.join(home,'.local/lib/node_modules'),path.join(process.env.APPDATA||path.join(home,'AppData/Roaming'),'npm/node_modules'),'/opt/homebrew/lib/node_modules','/usr/local/lib/node_modules'];
 const choices=bases.map(b=>path.join(b,'@openai/codex/node_modules/@openai',`codex-${platform}-${arch}`,'vendor',triple,'bin',platform==='win32'?'codex.exe':'codex'));
 for(const dir of (process.env.PATH||'').split(path.delimiter))choices.push(path.join(dir,platform==='win32'?'codex.exe':'codex'));
 for(const p of choices)if(await fs.stat(p).then(s=>s.isFile(),()=>false))return p;
 throw Error('未找到 Codex CLI');
}
class Reader{
 constructor(binary,timeout=30000){
  activeReaders.add(this);this.next=0;this.pending=new Map();this.closed=false;this.child=spawn(binary,['app-server','--stdio'],{stdio:['pipe','pipe','ignore'],windowsHide:true,env:{...process.env,RUST_LOG:'off'}});
  this.child.on('error',e=>this.fail(e));this.child.on('exit',()=>this.fail(Error('Codex 读取进程已退出')));
  this.lines=readline.createInterface({input:this.child.stdout});this.lines.on('line',line=>{try{const msg=JSON.parse(line),p=this.pending.get(msg.id);if(!p)return;this.pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(Error(msg.error.message)):p.resolve(msg.result);}catch{}});
  this.deadline=Date.now()+timeout;
 }
 fail(e){for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(e);}this.pending.clear();}
 async rpc(method,params){if(!READ_METHODS.has(method))throw Error('只允许读取 Codex');if(this.closed)throw Error('读取连接已关闭');const id=++this.next;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Codex 读取超时'));},Math.max(1,Math.min(10000,this.deadline-Date.now())));this.pending.set(id,{resolve,reject,timer});this.child.stdin.write(JSON.stringify({id,method,params})+'\n',e=>{if(e){clearTimeout(timer);this.pending.delete(id);reject(e);}});});}
 async init(){await this.rpc('initialize',{clientInfo:{name:'skill_game_dock',version:'0.2.0'},capabilities:{experimentalApi:true}});this.child.stdin.write('{"method":"initialized","params":{}}\n');}
 async close(){if(this.closed)return;activeReaders.delete(this);this.closed=true;this.fail(Error('读取已结束'));this.lines.close();this.child.stdin.end();if(this.child.exitCode!==null)return;await new Promise(resolve=>{const done=()=>{clearTimeout(timer);resolve();};const timer=setTimeout(()=>{this.child.kill('SIGTERM');resolve();},700);this.child.once('exit',done);});if(this.child.exitCode===null){this.child.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{if(this.child.exitCode===null)this.child.kill('SIGKILL');resolve();},700);this.child.once('exit',()=>{clearTimeout(timer);resolve();});});}}
}
function textOf(entry){const i=entry.item||entry;if(i.type==='agentMessage')return {role:'assistant',text:String(i.text||'')};if(i.type==='userMessage')return {role:'user',text:(i.content||[]).filter(c=>c.type==='text').map(c=>c.text||'').join('\n')};return null;}
function inferStage(messages){
 const patterns=[['已完成',/(?:游戏|项目|本游戏|制作)(?:已全部完成|已完成交付|全部完成)|正式完成|最终验收(?:已)?通过/],['待试玩',/美工(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)|(?:等待|待|请你|交给你|给你)(?:进行)?(?:本地)?试玩|待试玩/],['游玩',/正在(?:本地)?试玩|进入(?:本地)?(?:游玩|试玩)阶段|游玩阶段|开始(?:本地)?试玩/],['检查',/进入(?:成品)?检查|检查阶段|开始(?:检查|验收)|正在(?:检查|验收)|检测成品|执行.*(?:检查|验收)/],['美工制作',/开始(?:做|进行)?美工|进入美工|美工(?:制作|阶段)|(?:修改|修复|调整|重做|替换).{0,12}(?:美术|界面|按钮|贴图|音效)|美术与声音|换皮/],['玩法结束',/玩法(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)|玩法确认(?:已)?(?:完成|通过)/],['玩法制作',/玩法制作|制作玩法|开始(?:制作|重塑)|(?:新增|修复|调整|修改|检查).{0,10}(?:玩法|关卡|机制)|玩法阶段/]];
 for(let n=messages.length-1;n>=0;n--){const message=messages[n];const text=message.text.replace(/```[\s\S]*?```/g,'').slice(-7000);const lines=text.split(/[\n。！？，,；;]/).map(s=>s.trim()).filter(Boolean);
  for(let j=lines.length-1;j>=0;j--){const line=lines[j];if(/尚未|还未|未开始|不要|暂不|没有完成|未完成|未通过|之前|此前|历史|上次|不能(?:称|视为)|不代表|之后|下一阶段|下一步|接下来|后续|计划|需要先/.test(line))continue;
   for(const [stage,re]of patterns)if(re.test(line))return {stage,evidence:line.slice(0,200),role:message.role,certainty:'explicit'};
  }
 }
 return {stage:null,evidence:'',certainty:'unknown'};
}
function isMaintenanceTitle(value){
 const title=String(value||'').normalize('NFKC').trim().replace(/^[\s\d\p{Extended_Pictographic}\uFE0F\u20E3\u2460-\u2473\u2776-\u2793.、:：#_*+\-–—()[\]（）]+/u,'').trim().replace(/^(?:(?:每(?:天|日|周|星期|月|小时|分钟|\d+\s*(?:小时|分钟|天))|定时|定期|每日|每周)\s*[:：、-]?\s*)+/u,'');
 if(!title)return false;
 if(/工作台|工坊|批量|统一规则|日报|资讯|软件开发|存储清理|空间清理|股票|短剧|课件|讲稿/i.test(title))return true;
 // A Skill/tool subject at the start is maintenance. A game identity before a
 // Skill note is intentionally retained, even if that note says "Skill 更新".
 const actions='(?:(?:优化|更新|维护|融合|合并|安装|导出|调整|修复|审查|整理|检测|检查|完善|同步|制作|开发|设计|重构|规范|建立|编写|改进|升级|打包|评估|比较|统一|研究|分析|本机|共享)\\s*)*';
 const subject='(?:(?:cocos(?:[-_a-z0-9]+)?\\s+)?skills?\\b|(?:成品检测|检测成品|美工|玩法|重塑|英化|英化与重塑|重塑与英化|游戏|游戏制作|游戏检查|游戏打包|广告|逻辑检查|手机测试|多应用|通用)\\s*skills?\\b)';
 return new RegExp('^'+actions+subject,'i').test(title)||/^cocos-game-(?:from-starter|to-english|art-redo|logic-check|ad-design|tiktok-package)(?:\s|$)/i.test(title);
}
function isGameThread(t,roots=[]){
 const title=String(t.name||t.title||''),cwd=String(t.cwd||'');
 if(!UUID.test(t.id)||!title||t.archived||t.ephemeral||t.parentThreadId||t.parent_thread_id||typeof t.source==='object'||['cli','exec','subagent','sub_agent'].includes(t.source)||isMaintenanceTitle(title))return false;
 return roots.some(r=>cwd===r||cwd.startsWith(r+path.sep))||/(?:游戏|cocos|(?:^|[\\/])games?(?:[\\/]|$))/i.test(cwd)||/游戏|关卡|重塑|英化|试玩|TikTok|Native|[A-Za-z]+[’']s\s+[A-Za-z]+/.test(title);
}
async function discover({roots=[],cache={},limit=300,binary}={}){
 const reader=new Reader(binary||await executable());const out=[];let incomplete=false;
 try{await reader.init();let cursor=null;const rows=[];for(let page=0;page<3;page++){const r=await reader.rpc('thread/list',{limit:100,sortKey:'updated_at',sortDirection:'desc',archived:false,useStateDbOnly:true,...(cursor?{cursor}:{})});rows.push(...r.data||[]);cursor=r.nextCursor;if(!cursor)break;}incomplete=!!cursor;
  const scoped=rows.filter(t=>isGameThread(t,roots)).slice(0,limit);incomplete=incomplete||rows.filter(t=>isGameThread(t,roots)).length>limit;
  for(const t of scoped){const old=cache[t.id],updated=Number(t.updatedAt)||0;let stageInfo=old?.stageInfo||{stage:null,certainty:'unknown'},contextStatus='cached',contextRead=old?.contextRead===true&&old.updatedAt===updated;
   if(!contextRead){if(Date.now()>reader.deadline-1800){incomplete=true;contextStatus='pending';}else try{const items=await reader.rpc('thread/items/list',{threadId:t.id,limit:180,sortDirection:'desc'});const messages=(items.data||[]).map(textOf).filter(Boolean).reverse();stageInfo=inferStage(messages);contextStatus='read';contextRead=true;}catch{contextStatus='unavailable';incomplete=true;}}
   out.push({threadId:t.id,title:t.name||t.title,path:t.cwd,cwd:t.cwd,rolloutPath:t.path,metadataStatus:t.status,originator:t.originator,source:t.source,forkedFromId:t.forkedFromId||null,updatedAt:updated,stageInfo,contextStatus,contextRead});
  }
  return {threads:out,incomplete,checkedAt:new Date().toISOString()};
 }finally{await reader.close();}
}
async function queueMessage(threadId,message,{binary,timeout=20000,spawnFn=spawn}={}){
 if(!UUID.test(threadId)||typeof message!=='string'||!message.trim()||message.length>50000)throw Error('对话或指令无效');
 const exe=binary||await executable();return new Promise((resolve,reject)=>{let settled=false,output='';const child=spawnFn(exe,['queue','--thread',threadId,'--message',message],{stdio:['ignore','pipe','pipe'],windowsHide:true});const finish=result=>{if(settled)return;settled=true;clearTimeout(timer);resolve(result);};const timer=setTimeout(()=>{child.kill('SIGTERM');finish({status:'uncertain',detail:'发送回执超时，请查看目标对话，勿重复发送'});const cleanup=setTimeout(()=>{if(child.exitCode===null)child.kill('SIGKILL');},1000);cleanup.unref();},timeout);
 child.stdout.on('data',d=>{output=(output+d).slice(-1600);});child.stderr.on('data',d=>{output=(output+d).slice(-1600);});child.on('error',e=>{if(settled)return;settled=true;clearTimeout(timer);reject(e);});child.on('exit',code=>finish({status:code===0?'queued':'failed',detail:output.trim().slice(-800)||'Codex 未返回发送详情'}));});
}
const cancelReaders=()=>{for(const reader of activeReaders)reader.close().catch(()=>{});};
module.exports={cancelReaders,Reader,discover,inferStage,isMaintenanceTitle,isGameThread,queueMessage,executable,STAGES,UUID};
