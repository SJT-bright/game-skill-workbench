const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {collect,digest,atomicJSON}=require('./core.cjs');
async function seedEmbedded(client,source,catalog){
 const ledger=await client.state(),base=path.join(client.root,'skills');
 const same=(a,b)=>{a=path.resolve(a);b=path.resolve(b);return process.platform==='win32'?a.toLowerCase()===b.toLowerCase():a===b;};
 for(const item of catalog.skills){
  const skillId='s-'+digest(item.name).slice(0,20);if(ledger[skillId])continue;
  if(!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(item.name))throw Error('内置 Skill 目录无效');
  // Preserve an existing canonical component and any history lock. Online sync
  // can adopt its old identity transactionally; startup must not overwrite it.
  if(Object.values(ledger).some(s=>s.name===item.name&&path.basename(s.path)===item.name))continue;
  const snapshot=await collect(path.join(source,item.name)),actual=new Map(snapshot.files.map(f=>[f.path,f]));
  if(item.files?(item.files.length!==snapshot.files.length||item.files.some(f=>actual.get(f.path)?.hash!==f.hash||actual.get(f.path)?.size!==f.size)):snapshot.treeHash!==item.treeHash)throw Error('内置 Skill 文件校验失败');
  let dest=path.join(base,item.name);if(Object.values(ledger).some(s=>same(s.path,dest)))dest+='--'+digest(skillId).slice(0,20);
  // Never overwrite an orphaned or differently owned directory during seeding.
  if(await fs.lstat(dest).then(()=>true,e=>{if(e.code==='ENOENT')return false;throw e;}))dest+='--'+crypto.randomUUID();
  const stage=dest+'.stage-'+crypto.randomUUID();try{await fs.cp(path.join(source,item.name),stage,{recursive:true});await fs.rename(stage,dest);}finally{await fs.rm(stage,{recursive:true,force:true});}
  ledger[skillId]={id:'built-'+item.treeHash.slice(0,24),skillId,name:item.name,version:'内置',bundled:true,local:true,path:dest,treeHash:item.treeHash,files:item.files||snapshot.files,bytes:snapshot.bytes,fileCount:snapshot.files.length,createdAt:catalog.createdAt,summary:''};
  await atomicJSON(path.join(client.root,'installed.json'),ledger);
 }
 return ledger;
}
module.exports={seedEmbedded};
