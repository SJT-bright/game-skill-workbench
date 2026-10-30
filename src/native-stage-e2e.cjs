// Isolated public-record fixtures; this does not read or message employee chats.
const fs=require('node:fs/promises'),path=require('node:path'),{discover}=require('./codex.cjs');
module.exports=async function({win,handlers,config,root,setDiscovery}){
 const execute=js=>win.webContents.executeJavaScript(js),base=path.join(root,'stage-fixtures'),rows=[],expected=new Map(),requests=['开始玩法制作','用美工skill重做界面','生成最终测试包'],stages=['玩法制作','美工制作','检查'];await fs.mkdir(base,{recursive:true});
 const record=text=>JSON.stringify({timestamp:new Date().toISOString(),type:'response_item',payload:{type:'message',role:'user',content:[{type:'input_text',text}]}})+'\n';
 for(let i=0;i<60;i++){const id='33333333-3333-4333-8333-'+String(i).padStart(12,'0'),cwd=path.join(base,'游戏'+i),file=path.join(base,id+'.jsonl');await fs.mkdir(cwd);await fs.writeFile(file,JSON.stringify({type:'session_meta',payload:{id}})+'\n'+record('开始玩法制作')+record(requests[i%3]));rows.push({id,name:'阶段测试游戏'+i,cwd,path:file,source:'vscode',updatedAt:1,status:'idle'});expected.set(id,stages[i%3]);}
 let rpcFallbacks=0;setDiscovery(options=>discover({...options,readerFactory:()=>({deadline:Date.now()+30000,init:async()=>{},close:async()=>{},rpc:async method=>{if(method==='thread/list')return {data:rows};rpcFallbacks++;return {data:[{type:'userMessage',content:[{type:'text',text:'开始玩法制作'}]}]};}})}));
 try{await handlers.syncCodex();for(const [id,stage]of expected)if(config.games.find(g=>g.threadId===id)?.stage!==stage)throw Error('Initial per-thread stage mismatch: '+id);
  await execute(`document.querySelector('nav [data-tab="games"]').click();const input=document.querySelector('#search');input.value='阶段测试游戏';input.dispatchEvent(new Event('input',{bubbles:true}))`);
  const labels=await execute(`Array.from(document.querySelectorAll('[data-phase-menu]')).map(b=>b.textContent.trim())`);if(labels.length!==60||!['玩法阶段','美工阶段','测试阶段'].every(s=>labels.filter(x=>x===s).length===20))throw Error('Three-phase UI did not show all fixture games');
  for(let i=0;i<3;i++){await fs.appendFile(rows[i].path,record(requests[(i+1)%3]));expected.set(rows[i].id,stages[(i+1)%3]);}await handlers.syncCodex();for(const [id,stage]of expected)if(config.games.find(g=>g.threadId===id)?.stage!==stage)throw Error('Latest progress did not refresh independently: '+id);
  let game=config.games.find(g=>g.threadId===rows[0].id);await handlers.saveGame({...game,stageMode:'manual',stage:'玩法制作'});await fs.appendFile(rows[0].path,record('测试一下'));await handlers.syncCodex();game=config.games.find(g=>g.threadId===rows[0].id);if(game.stage!=='玩法制作')throw Error('Manual stage was overwritten');await handlers.saveGame({...game,stageMode:'auto',stage:null});await handlers.syncCodex();if(config.games.find(g=>g.threadId===rows[0].id)?.stage!=='检查')throw Error('Auto recognition did not resume from latest progress');
  if(rpcFallbacks!==0)throw Error('Valid local records unexpectedly fell back to stale RPC content');
  await execute(`const input=document.querySelector('#search');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))`);
  return {multiGameStageCount:60,threeStageUI:true,latestProgressStages:true,unchangedMetadataRefresh:true,manualStageOverride:true,autoStageResume:true,staleRpcBypassed:true};
 }finally{setDiscovery(null);}
};
