(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.ThreadSelection=factory();})(globalThis,()=>{
 'use strict';
 const LABELS={all:'全部',ongoing:'进行中',ended:'本轮结束',unknown:'待确认'};
 const PHASES={'玩法阶段':['玩法制作','玩法结束'],'美工阶段':['美工制作'],'测试阶段':['待试玩','游玩','检查']};
 function phase(stage){return Object.keys(PHASES).find(key=>PHASES[key].includes(stage))||(stage==='已完成'?'已完成':'待识别');}
 function activity(game,{stale=false}={}){
  if(stale)return 'unknown';
  const raw=game.metadataStatus,kind=typeof raw==='object'?raw?.type:raw;
  if(kind==='active')return 'ongoing';
  if(kind==='idle')return 'ended';
  if(kind==='systemError')return 'unknown';
  const t=game.telemetry||{};
  if(t.active===true||['active','waitingOnApproval','waitingOnUserInput'].includes(t.status))return 'ongoing';
  if(['idle','interrupted','completed'].includes(t.status))return 'ended';
  return 'unknown';
 }
 function identity(game,roots=[]){
  // Dedicated directories win. Shared workspace roots must never merge games.
  const norm=p=>String(p||'').replace(/\\/g,'/').replace(/\/+$/,'');
  const cwd=norm(game.path),base=cwd.split('/').pop();
  const shared=roots.some(r=>norm(r)===cwd)||/^(?:游戏出海项目制作|New project|工作工程|交付|游戏制作|games?|projects?)$/i.test(base||'');
  if(cwd&&!shared)return {key:'path:'+(/^[A-Z]:/i.test(cwd)?cwd.toLowerCase():cwd),name:base||game.name};
  const name=String(game.name||'').normalize('NFKC').replace(/\((?:自制|外包|完结\s*\d*|待试玩|玩法制作|美工制作|检查|已完成)\)/g,'').trim();
  // No fuzzy substring matching: ambiguous identities stay separate.
  return {key:'thread:'+(game.threadId||game.id),name:name||'未命名游戏'};
 }
 function select(games,{roots=[],stage='全部',activityFilter='all',query='',stale=false,sort='recent'}={}){
  const text=query.trim().toLowerCase(),groups=new Map(),counts={all:0,ongoing:0,ended:0,unknown:0};
  for(const game of games){
   const item=identity(game,roots);
   if(stage!=='全部'&&(PHASES[stage]?!PHASES[stage].includes(game.stage):(game.stage||'待识别')!==stage))continue;
   if(text&&![game.name,game.note,game.path,item.name].join(' ').toLowerCase().includes(text))continue;
   const status=activity(game,{stale:stale&&game.source==='codex'});counts.all++;counts[status]++;
   if(activityFilter!=='all'&&status!==activityFilter)continue;
   if(!groups.has(item.key))groups.set(item.key,{...item,threads:[]});
   groups.get(item.key).threads.push(game);
  }
  const recent=g=>Number.isFinite(Date.parse(g.updatedAt))?Date.parse(g.updatedAt):0;
  const score=group=>[group.threads.some(g=>g.pinned)?1:0,group.threads.some(g=>activity(g,{stale:stale&&g.source==='codex'})==='ongoing')?1:0,Math.max(...group.threads.map(recent))];
  const ordered=[...groups.values()];for(const group of ordered)group.threads.sort((a,b)=>(activity(b,{stale:stale&&b.source==='codex'})==='ongoing')-(activity(a,{stale:stale&&a.source==='codex'})==='ongoing')||recent(b)-recent(a));
  ordered.sort((a,b)=>{const x=score(a),y=score(b);if(sort==='number'){const number=g=>g.threads.find(t=>Number.isSafeInteger(t.projectNumber))?.projectNumber??Number(g.name.match(/^(\d+)/)?.[1]||Infinity),owner=g=>g.threads.find(t=>t.projectOwner)?.projectOwner||'';return y[0]-x[0]||Number(Number.isFinite(number(b)))-Number(Number.isFinite(number(a)))||owner(a).localeCompare(owner(b),'zh-CN',{numeric:true})||number(a)-number(b)||a.name.localeCompare(b.name,'zh-CN',{numeric:true});}return y[0]-x[0]||y[1]-x[1]||y[2]-x[2];});
  return {groups:ordered,counts,threadCount:[...groups.values()].reduce((n,g)=>n+g.threads.length,0)};
 }
 return {LABELS,PHASES,phase,activity,identity,select};
});
