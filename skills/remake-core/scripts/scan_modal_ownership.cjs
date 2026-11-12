'use strict';
// Token inventory, not a runtime verdict. Acorn's tokenizer accepts TypeScript token sequences.
const fs=require('node:fs'),acorn=require('./vendor/acorn.cjs');
function scan(source){
  const tokens=[];
  try {
    const tokenizer=acorn.tokenizer(source.replace(/@/g,' '),{ecmaVersion:'latest',locations:true});
    for(let t=tokenizer.getToken();t.type.label!=='eof';t=tokenizer.getToken())tokens.push({v:t.value===undefined?t.type.label:t.value,type:t.type.label,line:t.loc.start.line});
  }catch(e){return {status:'unresolved',reason:String(e.message),risks:[]};}
  const mask=/mask|shade|blackbg|backdrop|blocker|overlay/i,names=new Set(),risks=[];
  for(let i=0;i<tokens.length-4;i++){
    // name = 'blackBg' + view.name (a name describes a type, not a specific modal instance).
    if(tokens[i].type==='name'&&tokens[i+1].v==='='&&tokens[i+2].type==='string'&&mask.test(tokens[i+2].v)&&tokens[i+3].v==='+')names.add(tokens[i].v);
  }
  for(let i=0;i<tokens.length-6;i++){
    if(tokens[i].v!=='getChildByName'||tokens[i+1].v!=='(')continue;
    const arg=tokens[i+2];
    if(!(arg.type==='string'&&mask.test(arg.v))&&!names.has(arg.v))continue;
    let end=i+3,depth=1;
    for(;end<tokens.length;end++){if(tokens[end].v==='(')depth++;if(tokens[end].v===')'&&!--depth)break;}
    if(tokens[end+1]?.v==='.'&&tokens[end+2]?.v==='destroy'&&tokens[end+3]?.v==='('){
      risks.push({code:'MODAL_NAME_RELEASE',line:tokens[i].line,lookup:arg.v,reason:'A name lookup destroys a modal blocker; repeated same-name instances may release another owner. Bind an exact instance and run modal_lifecycle.'});
    }
  }
  return {status:'scanned',risks};
}
module.exports={scan};
if(require.main===module){const data=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(data.sources.map(scan)));}
