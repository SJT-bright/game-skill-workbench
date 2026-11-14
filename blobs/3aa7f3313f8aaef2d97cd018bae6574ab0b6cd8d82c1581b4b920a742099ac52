'use strict';
// Token edits preserve literals, comments and property names. Only the old adapter's free SDK name changes.
const acorn=require('./vendor/acorn.cjs'),fs=require('fs');
function normalize(source){
 const tokens=[...acorn.tokenizer(source,{ecmaVersion:'latest'})],edits=[];
 for(let i=0;i<tokens.length;i++){
  const t=tokens[i],previous=tokens[i-1],next=tokens[i+1];
  if(t.type.label==='name'&&t.value==='wx'&&next?.type.label==='.'&&previous?.type.label!=='.')edits.push(t);
 }
 for(const t of edits.reverse())source=source.slice(0,t.start)+'tt'+source.slice(t.end);
 acorn.parse(source,{ecmaVersion:'latest',allowReturnOutsideFunction:true});
 return source;
}
if(require.main===module){
 if(process.argv.slice(2).some(a=>a==='--help'||a==='-h')){console.log("Usage: node normalize_cocos1_sdk.cjs < sources.json\nstdin: {\"filename.js\":\"JavaScript source\"}");process.exit(0);}
 const raw=fs.readFileSync(0,'utf8');if(!raw.trim()){console.error("Usage: node normalize_cocos1_sdk.cjs < sources.json\nstdin: {\"filename.js\":\"JavaScript source\"}");process.exit(2);}
 const d=JSON.parse(raw);console.log(JSON.stringify(Object.fromEntries(Object.entries(d).map(([n,s])=>[n,normalize(s)]))));}
module.exports={normalize};
