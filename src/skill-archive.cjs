const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const {collect,readJSON,atomicJSON,digest}=require('./core.cjs'),{crc32}=require('./zip.cjs'),{definitions}=require('../ui/skill-categories.js');
const LIMIT=64*1024*1024;
function unpack(data){
 if(data.length>LIMIT)throw Error('Skill ZIP 超过 64 MB');
 let end=-1;for(let i=data.length-22;i>=Math.max(0,data.length-65557);i--)if(data.readUInt32LE(i)===0x06054b50){end=i;break;}
 if(end<0||end+22+data.readUInt16LE(end+20)!==data.length)throw Error('ZIP 不完整');
 const count=data.readUInt16LE(end+10),centralSize=data.readUInt32LE(end+12);let offset=data.readUInt32LE(end+16),total=0;
 if(data.readUInt16LE(end+4)||data.readUInt16LE(end+6)||data.readUInt16LE(end+8)!==count||count>4000||offset+centralSize!==end)throw Error('不支持此 ZIP 格式');
 const files=new Map(),names=new Set();
 for(let i=0;i<count;i++){
  if(offset+46>end||data.readUInt32LE(offset)!==0x02014b50)throw Error('ZIP 目录损坏');
  const flags=data.readUInt16LE(offset+8),method=data.readUInt16LE(offset+10),crc=data.readUInt32LE(offset+16),packed=data.readUInt32LE(offset+20),bytes=data.readUInt32LE(offset+24),n=data.readUInt16LE(offset+28),extra=data.readUInt16LE(offset+30),comment=data.readUInt16LE(offset+32),mode=data.readUInt32LE(offset+38)>>>16,local=data.readUInt32LE(offset+42);
  if(offset+46+n+extra+comment>end)throw Error('ZIP 目录损坏');
  const name=data.subarray(offset+46,offset+46+n).toString('utf8');offset+=46+n+extra+comment;
  if(!name||name.startsWith('/')||/[\\\x00-\x1f<>:"|?*]/.test(name)||name.split('/').some(s=>s==='..'||s==='.'||/[. ]$/.test(s)))throw Error('ZIP 文件路径不安全');
  if(name.startsWith('__MACOSX/')||name.split('/').some(s=>s.startsWith('.')))continue;
  if((mode&0o170000)===0o120000)throw Error('ZIP 不允许符号链接');
  if(name.endsWith('/'))continue;
  if((flags&1)||![0,8].includes(method))throw Error('请使用未加密的普通 ZIP');
  total+=bytes;if(total>LIMIT)throw Error('Skill 文件超过 64 MB');
  if(local+30>data.length||data.readUInt32LE(local)!==0x04034b50)throw Error('ZIP 文件头损坏');
  const start=local+30+data.readUInt16LE(local+26)+data.readUInt16LE(local+28);if(start+packed>end-centralSize)throw Error('ZIP 文件数据越界');
  const content=method===0?data.subarray(start,start+packed):zlib.inflateRawSync(data.subarray(start,start+packed),{maxOutputLength:Math.max(1,bytes)});
  if(content.length!==bytes||crc32(content)!==crc)throw Error('ZIP 文件校验失败：'+name);
  const key=name.normalize('NFC').toLowerCase();if(names.has(key))throw Error('ZIP 存在重复文件');names.add(key);files.set(name,{data:content,executable:!!(mode&0o111)});
 }
 if(offset!==end)throw Error('ZIP 目录长度不一致');return files;
}
async function importSkillArchive(root,source){
 const stat=await fs.stat(source);if(!stat.isFile()||stat.size>LIMIT||!source.toLowerCase().endsWith('.zip'))throw Error('请拖入英化或重塑 Skill ZIP');
 const archive=await fs.readFile(source);let files=unpack(archive);
 // Finder's containing-folder ZIP is accepted without asking users to rearrange it.
 if(!files.has('SKILL.md')){const prefixes=new Set([...files.keys()].map(n=>n.split('/')[0]));if(prefixes.size===1){const prefix=[...prefixes][0]+'/';files=new Map([...files].map(([n,v])=>[n.slice(prefix.length),v]));}}
 const spec=definitions.find(d=>d.skillId==='bundle-remake'&&files.has(d.entry+'/SKILL.md'))||definitions.find(d=>files.has(d.entry+'/SKILL.md'));
 if(!spec)throw Error('未识别到完整英化或重塑 Skill 包，请拖入工作台导出的 ZIP');
 const members=[...new Set([...files.keys()].filter(n=>n.includes('/')).map(n=>n.split('/')[0]))];
 if(members.some(n=>!spec.members.includes(n)))throw Error('压缩包包含不属于该流程的组件');
 for(const name of members)if(!files.has(name+'/SKILL.md'))throw Error('组件缺少 SKILL.md：'+name);
 const base=path.join(root,'imports'),id=crypto.randomUUID(),dest=path.join(base,id),stage=path.join(base,'.stage-'+id),state=await readJSON(path.join(root,'installed.json'),{});
 await fs.mkdir(stage,{recursive:true});let committed=false;
 try{
  for(const name of members){const skillId='s-'+digest(name).slice(0,20),prior=state[skillId];if(prior){await fs.cp(prior.path,path.join(stage,name),{recursive:true,preserveTimestamps:true,filter:async from=>{if((await fs.lstat(from)).isSymbolicLink())throw Error('本机 Skill 包含符号链接');return true;}}).catch(e=>{if(e.code!=='ENOENT')throw e;});}}
  for(const [name,file]of files){if(!name.includes('/'))continue;const to=path.join(stage,...name.split('/'));await fs.mkdir(path.dirname(to),{recursive:true});const same=await fs.readFile(to).then(data=>data.equals(file.data),()=>false);if(!same)await fs.writeFile(to,file.data,{mode:file.executable?0o755:0o644});}
  const installs={};for(const name of members){const tree=await collect(path.join(stage,name));const skillId='s-'+digest(name).slice(0,20);installs[skillId]={id:'import-'+tree.treeHash.slice(0,24),skillId,name,version:'ZIP 导入',path:path.join(dest,name),treeHash:tree.treeHash,files:tree.files,bytes:tree.bytes,installMode:'merge',importedFrom:path.join(dest,'package.zip'),createdAt:new Date().toISOString(),summary:'从完整 '+spec.category+' Skill 包导入'};}
  await fs.writeFile(path.join(stage,'package.zip'),archive);await fs.rename(stage,dest);await atomicJSON(path.join(root,'installed.json'),{...state,...installs});committed=true;
  return {category:spec.category,skillId:spec.skillId,installed:installs,archive:path.join(dest,'package.zip'),memberCount:members.length};
 }finally{await fs.rm(stage,{recursive:true,force:true});if(!committed)await fs.rm(dest,{recursive:true,force:true});}
}
async function cleanImports(root){const state=await readJSON(path.join(root,'installed.json'),{}),base=path.join(root,'imports'),used=new Set(Object.values(state).map(s=>path.dirname(s.path)));for(const e of await fs.readdir(base,{withFileTypes:true}).catch(()=>[]))if(e.isDirectory()&&/^[a-f0-9-]{36}$/.test(e.name)&&!used.has(path.join(base,e.name)))await fs.rm(path.join(base,e.name),{recursive:true,force:true});}
module.exports={unpack,importSkillArchive,cleanImports};
