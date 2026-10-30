const {collect}=require('./core.cjs');
async function inspect(skill){
 const tree=await collect(skill.path,{localUse:!!skill.local});
 if(skill.local)return {...skill,treeHash:tree.treeHash,files:tree.files,bytes:tree.bytes};
 const actual=new Map(tree.files.map(f=>[f.path,f]));
 const changed=skill.files?skill.files.filter(f=>actual.get(f.path)?.hash!==f.hash||actual.get(f.path)?.size!==f.size).map(f=>f.path):[];
 if(changed.length||(!skill.files&&tree.treeHash!==skill.treeHash)||(skill.files&&skill.installMode!=='merge'&&tree.files.length!==skill.files.length))throw Error('文件缺失或内容不一致'+(changed.length?'：'+changed.slice(0,3).join('、'):''));
 return skill;
}
async function ensureSkill(skill,{repair}={}){
 try{return await inspect(skill);}catch(initial){
  if(skill.local)throw initial;
  if(!repair)throw Error('Skill 文件需要修复：'+initial.message+'；请在桌面版重新获取当前版本');
  try{const restored=await repair(skill);return await inspect(restored);}catch(error){throw Error('Skill 自动修复失败，未发送到对话：'+error.message+'。请检查网络后重试');}
 }
}
module.exports={ensureSkill};
