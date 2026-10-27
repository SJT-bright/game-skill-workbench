const SKILL_POLL_MS=60*1000,APPLICATION_POLL_MS=5*60*1000;
function mergeNotices(previous,releases,{installed={},pins={},now=new Date().toISOString()}={}){
 const result=new Map((Array.isArray(previous)?previous:[]).filter(n=>n&&n.skillId).map(n=>[n.skillId,n]));
 for(const r of releases){const status=installed[r.skillId]?.id===r.id?'updated':pins[r.skillId]?'pinned':'available';result.set(r.skillId,{id:r.id,skillId:r.skillId,kind:'skill',name:r.name,version:r.version,summary:String(r.summary||'').slice(0,8000),status,createdAt:now});}
 return [...result.values()].sort((a,b)=>b.createdAt.localeCompare(a.createdAt)).slice(0,100);
}
function notificationBody(notices){return notices.map(n=>`${n.name} ${n.version} · ${n.status==='updated'?'已更新':n.status==='pinned'?'有新版，保留历史版本':'有新版'}${n.summary?'：'+n.summary:''}`).join('\n').slice(0,800);}
module.exports={SKILL_POLL_MS,APPLICATION_POLL_MS,mergeNotices,notificationBody};
