// Read-only compiled-module normalization. Only the Python guard removes the
// exact reviewed fallback statements; this helper never removes game code.
const fs=require('node:fs');
const terser=require(process.argv[2]);
const acorn=require(require.resolve('acorn',{paths:[process.argv[2]]}));
function normalizeCcSetter(code){
 const ast=acorn.parse(code,{ecmaVersion:'latest'});let setter;const declarations=[];
 function walk(n){if(!n||typeof n!=='object')return;if(n.type==='Property'&&n.key?.name==='setters')setter=n.value;if(n.type==='VariableDeclaration')declarations.push(n);for(const v of Object.values(n)){if(Array.isArray(v))for(const x of v)walk(x);else if(v&&typeof v==='object')walk(v)}}walk(ast);
 if(!setter||setter.type!=='ArrayExpression'||setter.elements.length!==2)throw Error('exact two-module setter layout required');
 const fn=setter.elements[1],body=fn.body.body;
 if(fn.params.length!==1||body.length!==1||body[0].type!=='ExpressionStatement'||body[0].expression.type!=='SequenceExpression')throw Error('simple constructor setter required');
 const seq=body[0].expression,assignments=seq.expressions,param=fn.params[0].name;
 const expected=['cclegacy','assetManager','SpriteFrame','Sprite','Node','UITransform','Label','Color','Button','BitmapFont'];
 for(const n of assignments)if(n.type!=='AssignmentExpression'||n.operator!=='='||n.left.type!=='Identifier'||n.right.type!=='MemberExpression'||n.right.computed||n.right.object.name!==param||n.right.property.type!=='Identifier')throw Error('setter has executable behavior beyond imported constructor references');
 const names=assignments.map(n=>n.right.property.name).sort();if(JSON.stringify(names)!==JSON.stringify(expected.sort()))throw Error('constructor import set changed');
 const sorted=assignments.slice().sort((a,b)=>a.right.property.name.localeCompare(b.right.property.name)).map(n=>code.slice(n.start,n.end)).join(',');
 const helper=setter.elements[0].body.body[0].expression;
 if(helper.type!=='AssignmentExpression'||helper.left.type!=='Identifier'||helper.right.property?.name!=='createForOfIteratorHelperLoose')throw Error('helper setter changed');
 const order=[helper.left.name,...assignments.slice().sort((a,b)=>a.right.property.name.localeCompare(b.right.property.name)).map(n=>n.left.name)];
 const decl=declarations.filter(n=>n.declarations.length===order.length&&n.declarations.every(d=>d.id.type==='Identifier'&&!d.init&&order.includes(d.id.name)));
 if(decl.length!==1)throw Error('import declaration shape changed');
 const d=decl[0];let changes=[[seq.start,seq.end,sorted],[d.start,d.end,'var '+order.join(',')+';']];
 for(const [start,end,text]of changes.sort((a,b)=>b[0]-a[0]))code=code.slice(0,start)+text+code.slice(end);
 return code;
}
(async()=>{
 const [a,b]=JSON.parse(fs.readFileSync(0,'utf8'));
 const options={compress:{passes:3},mangle:{toplevel:true,nth_identifier:{get:n=>'v'+n,reset(){},sort(){},consider(){}}},format:{comments:false}};
 const normalize=process.argv[3]==='home'?x=>x:normalizeCcSetter;
 const [x,y]=await Promise.all([terser.minify(normalize(a),options),terser.minify(normalize(b),options)]);
 const crypto=require('node:crypto');const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
 process.stdout.write(JSON.stringify({equal:x.code===y.code,before_canonical_sha256:sha(x.code),after_canonical_sha256:sha(y.code),normalizer:'Creator 3.8.8 bundled terser, exact async-load/hide removal; fixed imported-constructor declaration order; compress + deterministic lexical mangling'}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1});
