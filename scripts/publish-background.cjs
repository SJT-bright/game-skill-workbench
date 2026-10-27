// Maintainer-only, windowless publication. Never reads games or Codex conversations.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const {collect,readJSON,atomicJSON}=require('../src/core.cjs');
const {publishSkill}=require('../src/publisher.cjs');
const {ALLOWED}=require('./sync-skills.cjs');
async function run({dataRoot=path.join(os.homedir(),'Library/Application Support/GameDesk-Publisher'),sourceRoot=path.join(process.env.CODEX_HOME||path.join(os.homedir(),'.codex'),'skills'),repository='SJT-bright/game-skill-workbench',collectFn=collect,publishFn=publishSkill}={}){
 await fs.mkdir(dataRoot,{recursive:true});const lock=path.join(dataRoot,'running.json');let acquired=false;
 try{
  try{const fd=await fs.open(lock,'wx');await fd.writeFile(JSON.stringify({pid:process.pid}));await fd.close();acquired=true;}
  catch(e){if(e.code!=='EEXIST')throw e;const old=await readJSON(lock,{});if(!Number.isInteger(old.pid))return {status:'busy'};try{process.kill(old.pid,0);return {status:'busy'};}catch(error){if(error.code!=='ESRCH')return {status:'busy'};}await fs.rm(lock,{force:true});return run({dataRoot,sourceRoot,repository,collectFn,publishFn});}
  const file=path.join(dataRoot,'state.json'),state=await readJSON(file,{skills:{}});state.skills||={};const results=[];
  for(const name of ALLOWED){
   try{const source=path.join(sourceRoot,name),snapshot=await collectFn(source),old=state.skills[name];
    if(old?.treeHash===snapshot.treeHash&&!old.error){results.push({name,status:'current'});continue;}
    const result=await publishFn({repository,source,name,root:dataRoot});
    state.skills[name]={treeHash:snapshot.treeHash,checkedAt:new Date().toISOString(),commit:result.commit||old?.commit||null,error:null};
    results.push({name,status:result.changed?'submitted':'current',commit:result.commit||null});
   }catch{state.skills[name]={...state.skills[name],error:'发布未完成；将在下次检查重试',checkedAt:new Date().toISOString()};results.push({name,status:'failed'});}
   state.checkedAt=new Date().toISOString();await atomicJSON(file,state);
  }
  const report={status:results.some(r=>r.status==='failed')?'partial':'complete',checkedAt:new Date().toISOString(),results};await atomicJSON(path.join(dataRoot,'latest.json'),report);return report;
 }finally{if(acquired)await fs.rm(lock,{force:true});}
}
if(require.main===module)run().then(result=>{console.log(JSON.stringify(result));if(result.status==='partial')process.exitCode=1;}).catch(()=>{console.error('后台发布未完成；请检查 GitHub 登录或网络');process.exitCode=1;});
module.exports={run};
