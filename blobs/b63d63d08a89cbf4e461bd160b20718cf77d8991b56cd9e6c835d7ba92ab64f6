'use strict';
const fs=require('fs'),acorn=require('./vendor/acorn.cjs');
function literal(n){
 if(n.type==='Literal')return n.value;
 if(n.type==='ArrayExpression')return n.elements.map(x=>x===null?null:literal(x));
 if(n.type==='ObjectExpression'){const out={};for(const p of n.properties){if(p.type!=='Property'||p.computed||p.kind!=='init')throw Error('Unsupported settings property');const k=p.key.name??p.key.value;if(k in out)throw Error('Duplicate settings key');out[k]=literal(p.value);}return out;}
 if(n.type==='UnaryExpression'&&['-','+','!'].includes(n.operator)){const v=literal(n.argument);return n.operator==='-'?-v:n.operator==='+'?+v:!v;}
 throw Error('Settings must contain literal exported data, not executable expressions');
}
function read(s){const ast=acorn.parse(s,{ecmaVersion:'latest'});if(ast.body.length!==1)throw Error('Expected only the exported settings assignment');const e=ast.body[0].expression;if(e?.type!=='AssignmentExpression'||e.operator!=='='||e.left.type!=='MemberExpression'||e.left.object.name!=='window'||e.left.property.name!=='_CCSettings')throw Error('Invalid Creator settings export');return literal(e.right);}
if(require.main===module)try{console.log(JSON.stringify(read(fs.readFileSync(0,'utf8'))))}catch(e){console.error(String(e));process.exitCode=1}
module.exports={read};
