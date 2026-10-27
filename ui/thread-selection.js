(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.ThreadSelection=factory();})(globalThis,()=>{
 'use strict';
 const LABELS={all:'全部',ongoing:'进行中',ended:'本轮结束',unknown:'待确认'};
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
 function select(games,{roots=[],stage='全部',activityFilter='all',query='',stale=false}={}){
  const text=query.trim().toLowerCase(),groups=new Map(),counts={all:0,ongoing:0,ended:0,unknown:0};
  for(const game of games){
   const item=identity(game,roots);
   if(stage!=='全部'&&(game.stage||'待识别')!==stage)continue;
   if(text&&![game.name,game.note,game.path,item.name].join(' ').toLowerCase().includes(text))continue;
   const status=activity(game,{stale:stale&&game.source==='codex'});counts.all++;counts[status]++;
   if(activityFilter!=='all'&&status!==activityFilter)continue;
   if(!groups.has(item.key))groups.set(item.key,{...item,threads:[]});
   groups.get(item.key).threads.push(game);
  }
  return {groups:[...groups.values()],counts,threadCount:[...groups.values()].reduce((n,g)=>n+g.threads.length,0)};
 }
 return {LABELS,activity,identity,select};
});
