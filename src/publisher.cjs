const path=require('node:path');
const github=require('./github.cjs');
const {collect,digest}=require('./core.cjs');
const SHA=/^[a-f0-9]{40}$/;
const HASH=/^[a-f0-9]{64}$/;
const FOLDER=/^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/;
function folderName(value){if(!FOLDER.test(value)||value.toLowerCase()==='cocos-game-finished-product-check')throw Error('此目录不能发布到内置 Skill 仓库');return value;}
function relativeFile(value){if(typeof value!=='string'||!value||value.length>500||/[\\\x00-\x1f<>:"|?*]/.test(value)||value.startsWith('/')||value.split('/').some(p=>!p||p==='.'||p==='..'||/[. ]$/.test(p)||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i.test(p)))throw Error('仓库 Skill 文件路径无效');return value;}
function checkSha(value){if(!SHA.test(value||''))throw Error('GitHub Git 对象校验失败');return value;}
function catalogValue(raw){let result;try{result=Buffer.isBuffer(raw)||typeof raw==='string'?JSON.parse(raw.toString().replace(/^\uFEFF/,'')):structuredClone(raw);}catch{throw Error('仓库 Skill 目录无法解析');}if(result?.schema!==1||!Array.isArray(result.skills)||result.skills.length>10000)throw Error('仓库 Skill 目录无效');const names=new Set();for(const s of result.skills){folderName(s.name);if(names.has(s.name.toLowerCase()))throw Error('仓库 Skill 名称冲突');names.add(s.name.toLowerCase());if(!HASH.test(s.treeHash||''))throw Error('仓库 Skill 校验值无效');}return result;}
function previousFiles(entry){if(!entry)return [];if(!Array.isArray(entry.files))throw Error('仓库 Skill 目录缺少文件清单，请先同步内置 Skill');const names=new Set();for(const f of entry.files){relativeFile(f.path);const key=f.path.normalize('NFC').toLowerCase();if(names.has(key)||!HASH.test(f.hash||'')||!Number.isSafeInteger(f.size)||f.size<0)throw Error('仓库 Skill 文件清单无效');names.add(key);}return entry.files;}
async function publishSkill({repository,source,name,root,note='',transport,platform=process.platform}){
 const repo=github.repository(repository),folder=folderName(path.basename(source));
 // Source collection is completed before any remote write. It excludes local-only Skills and links.
 const snapshot=await collect(source);
 const read=transport?.read||transport?.api||github.api;
 const write=transport?.write||transport?.apiWrite||github.apiWrite;
 const base=`repos/${repo}/git`;
 const commitMessage='Update Skill '+folder+(note?': '+String(note).replace(/[\r\n]/g,' ').slice(0,100):'');
 for(let attempt=0;attempt<3;attempt++){
  const ref=await read(`${base}/ref/heads/main`),head=checkSha(ref?.object?.sha);
  const catalog=catalogValue(await read(`repos/${repo}/contents/skills/catalog.json?ref=${head}`,{binary:true}));
  const old=catalog.skills.find(s=>s.name===folder);
  if(old?.treeHash===snapshot.treeHash)return {changed:false,status:'current'};
  const oldFiles=previousFiles(old),oldByPath=new Map(oldFiles.map(f=>[f.path,f]));
  // Windows cannot represent POSIX executable bits. Keep the repository's declared mode there.
  const files=snapshot.files.map(f=>({...f,executable:platform==='win32'&&oldByPath.get(f.path)?.executable?true:f.executable}));
  const treeHash=digest(JSON.stringify(files));
  if(old?.treeHash===treeHash)return {changed:false,status:'current'};
  const commit=await read(`${base}/commits/${head}`),baseTree=checkSha(commit?.tree?.sha),tree=[];
  for(const f of files){
   const oldFile=oldByPath.get(f.path);if(oldFile?.hash===f.hash&&!!oldFile.executable===!!f.executable)continue;
   const blob=await write(`${base}/blobs`,{content:snapshot.blobs.get(f.hash).toString('base64'),encoding:'base64'});
   tree.push({path:`skills/${folder}/${relativeFile(f.path)}`,mode:f.executable?'100755':'100644',type:'blob',sha:checkSha(blob?.sha)});
  }
  const currentPaths=new Set(files.map(f=>f.path));
  for(const f of oldFiles)if(!currentPaths.has(f.path))tree.push({path:`skills/${folder}/${relativeFile(f.path)}`,mode:f.executable?'100755':'100644',type:'blob',sha:null});
  const entry={name:folder,treeHash,fileCount:files.length,bytes:snapshot.bytes,files};
  catalog.skills=catalog.skills.filter(s=>s.name!==folder).concat(entry).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
  catalog.createdAt=new Date().toISOString();catalog.treeHash=digest(JSON.stringify(catalog.skills));
  const catalogData=Buffer.from(JSON.stringify(catalog,null,2)+'\n');
  const blob=await write(`${base}/blobs`,{content:catalogData.toString('base64'),encoding:'base64'});
  tree.push({path:'skills/catalog.json',mode:'100644',type:'blob',sha:checkSha(blob?.sha)});
  const nextTree=await write(`${base}/trees`,{base_tree:baseTree,tree});
  const nextCommit=await write(`${base}/commits`,{message:commitMessage,tree:checkSha(nextTree?.sha),parents:[head]});
  const sha=checkSha(nextCommit?.sha);
  try{await write(`${base}/refs/heads/main`,{sha,force:false},{method:'PATCH'});return {changed:true,status:'submitted',commit:sha};}
  catch(e){if(![409,422].includes(Number(e.status))||attempt===2)throw e;}
 }
}
module.exports={publishSkill};
