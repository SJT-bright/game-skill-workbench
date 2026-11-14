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
if(require.main===module){const d=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(Object.fromEntries(Object.entries(d).map(([n,s])=>[n,normalize(s)]))));}
module.exports={normalize};
