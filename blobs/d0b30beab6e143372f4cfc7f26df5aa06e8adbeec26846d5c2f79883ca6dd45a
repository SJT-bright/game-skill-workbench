// A session file belongs to one user goal. The lease covers the whole page operation,
// not just space creation; simultaneous checker processes must not share a live page.
import fs from 'node:fs';
const leases=new Map();
function alive(pid) { try {process.kill(pid,0);return true;}catch(e){return e.code!=='ESRCH';} }
function release(config) {
  const file=config.sessionFile,token=leases.get(file);if(!file||!token)return;
  const lock=file+'.active.json';
  if(fs.existsSync(lock)&&JSON.parse(fs.readFileSync(lock,'utf8')).token===token)fs.unlinkSync(lock);
  leases.delete(file);
}
function acquire(config) {
  const file=config.sessionFile;if(!file)return;
  const lock=file+'.active.json';
  if(fs.existsSync(lock)) {
    const owner=JSON.parse(fs.readFileSync(lock,'utf8'));
    if(alive(owner.pid)) {const e=new Error('Another checker is operating this Ego page; wait for that node, do not start another browser');e.code='EGO_CHECK_BUSY';throw e;}
    fs.unlinkSync(lock); // crashed process, not a browser control recovery
  }
  const token=process.pid+'-'+Date.now()+'-'+Math.random();
  let fd;try{fd=fs.openSync(lock,'wx');}catch(e){e.code='EGO_CHECK_BUSY';throw e;}
  fs.writeFileSync(fd,JSON.stringify({pid:process.pid,token,started:new Date().toISOString()}));fs.closeSync(fd);leases.set(file,token);
}
export function stopped(config,error) {
  if(error?.code==='EGO_CHECK_BUSY')return;
  if(config.sessionFile)fs.writeFileSync(config.sessionFile+'.stopped.json',JSON.stringify({error:String(error),at:new Date().toISOString()}));
  release(config);
}
export async function open(config) {
  if(config.sessionFile&&fs.existsSync(config.sessionFile+'.stopped.json'))throw new Error('Ego session stopped; resolve the recorded error/control state before continuing');
  if(config.sessionFile&&fs.existsSync(config.sessionFile+'.closed.json'))throw new Error('Ego task already finished; do not operate its pages again');
  acquire(config);
  try {
    let previous=null,task;
    if(config.sessionFile&&fs.existsSync(config.sessionFile))previous=JSON.parse(fs.readFileSync(config.sessionFile,'utf8'));
    if(previous) {
      const found=(await listTaskSpaces()).find(s=>s.id===previous.id);
      if(found)task=await taskSpace(previous.id);
      else task=await taskSpace(config.space+'-replacement-'+Date.now()); // user authorized only after original ID disappeared
    } else task=await taskSpace(config.space);
    if(config.sessionFile)fs.writeFileSync(config.sessionFile,JSON.stringify({id:task.spaceId,name:task.name}));
    return task;
  }catch(e){stopped(config,e);release(config);throw e;}
}
export async function leave(task,page,config) {
  try {
    await page.goto('about:blank');
    if(!config.sessionFile) {
      await task.finish({keep:[]});
      if((await listTaskSpaces()).some(s=>s.id===task.spaceId))throw new Error('Owned Ego space did not close: '+task.spaceId);
    }
  }catch(e){stopped(config,e);throw e;}finally{release(config);}
}
export async function finish(file) {
  if(fs.existsSync(file+'.closed.json'))return JSON.parse(fs.readFileSync(file+'.closed.json','utf8'));
  if(!fs.existsSync(file))return {closed:false,reason:'no browser was opened'};
  if(fs.existsSync(file+'.stopped.json'))return {closed:false,stopped:true,reason:'preserved after an error/control stop; no browser operation attempted'};
  if(fs.existsSync(file+'.active.json')&&alive(JSON.parse(fs.readFileSync(file+'.active.json','utf8')).pid))throw new Error('Ego page still has an active checker; cannot finish');
  const saved=JSON.parse(fs.readFileSync(file,'utf8'));
  const found=(await listTaskSpaces()).find(s=>s.id===saved.id);
  if(found){
    try { const task=await taskSpace(saved.id);await task.finish({keep:[]}); }
    catch(e){stopped({sessionFile:file},e);throw e;}
  }
  if((await listTaskSpaces()).some(s=>s.id===saved.id))throw new Error('Owned Ego space did not close: '+saved.id);
  const result={closed:true,id:saved.id};fs.writeFileSync(file+'.closed.json',JSON.stringify(result));return result;
}
