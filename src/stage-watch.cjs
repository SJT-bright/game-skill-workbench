const fs=require('node:fs'),path=require('node:path');
function createStageWatcher(onChange,{delay=1200,maxWait=5000,watch=fs.watch}={}){
 const dirs=new Map(),pending=new Set();let quietTimer,maxTimer,closed=false;
 const key=s=>process.platform==='win32'?s.toLowerCase():s;
 function flush(){clearTimeout(quietTimer);clearTimeout(maxTimer);quietTimer=maxTimer=null;if(closed||!pending.size)return;const ids=[...pending];pending.clear();Promise.resolve().then(()=>{if(!closed)return onChange(ids);}).catch(()=>{});}
 function schedule(ids){if(closed)return;for(const id of ids)pending.add(id);clearTimeout(quietTimer);quietTimer=setTimeout(flush,delay);if(!maxTimer)maxTimer=setTimeout(flush,maxWait);}
 function update(threads){if(closed)return;const needed=new Map();for(const t of threads){const file=t.rolloutPath;if(!file||!path.isAbsolute(file))continue;const dir=path.dirname(file);if(!needed.has(dir))needed.set(dir,new Map());const names=needed.get(dir),name=key(path.basename(file));if(!names.has(name))names.set(name,[]);names.get(name).push(t.threadId);}
  for(const [dir,entry]of dirs)if(!needed.has(dir)){entry.watcher.close();dirs.delete(dir);}
  for(const [dir,names]of needed){const prior=dirs.get(dir);if(prior){prior.names=names;continue;}try{const entry={names};entry.watcher=watch(dir,{persistent:false},(_,filename)=>{if(filename){const ids=entry.names.get(key(String(filename)));if(ids)schedule(ids);}else schedule([...entry.names.values()].flat());});entry.watcher.on('error',()=>{entry.watcher.close();if(dirs.get(dir)===entry)dirs.delete(dir);});dirs.set(dir,entry);}catch{}}
 }
 function close(){closed=true;clearTimeout(quietTimer);clearTimeout(maxTimer);pending.clear();for(const e of dirs.values())e.watcher.close();dirs.clear();}
 return {update,close};
}
module.exports={createStageWatcher};
