(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SkillCategories=factory();})(globalThis,()=>{
 const labels=['英化','重塑'];
 function categories(skill){
  if(labels.includes(skill.category))return [skill.category];
  const name=String(skill.name||'');
  if(/^(?:cocos-game-to-english|英化|游戏英化)$/i.test(name))return ['英化'];
  if(/^(?:cocos-game-from-starter|cocos-game-art-redo|remake-art|重塑|游戏重塑)$/i.test(name))return ['重塑'];
  // Shared checks, packaging and other supporting files remain available to both workflows.
  return labels;
 }
 function includes(skill,category){return categories(skill).includes(category);}
 const shared=['remake-art','cocos-game-logic-check','cocos-game-check','remake-core','cocos-game-ad-design','cocos-game-tiktok-package','cocos-tiktok-package-check','mobile-touch-computer-use','chrome-mobile-testing','game-audio-library','ego-browser','grok-delegate','grok-image-review','grok-background-maker','desktop-agent-orchestrator'];
 const definitions=[{skillId:'bundle-english',name:'英化 Skill 包',category:'英化',entry:'cocos-game-to-english',members:['cocos-game-to-english',...shared]},{skillId:'bundle-remake',name:'重塑 Skill 包',category:'重塑',entry:'cocos-game-from-starter',members:['cocos-game-from-starter','cocos-game-to-english','cocos-game-art-redo',...shared]}];
 function bundles(skills){const all=new Map();for(const s of skills){const old=all.get(s.name);if(!old||(!s.local&&old.local))all.set(s.name,s);}return definitions.filter(d=>all.has(d.entry)).map(d=>({...d,id:d.skillId,version:'最新文件',local:true,bundle:true,summary:'完整文件与配套工具',memberCount:d.members.filter(n=>all.has(n)).length}));}
 return {labels,categories,includes,definitions,bundles};
});
