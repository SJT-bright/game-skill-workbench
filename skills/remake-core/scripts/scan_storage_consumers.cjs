'use strict';
// Read actual JS syntax, never comments/string matches. Scope is direct storage consumers,
// not arbitrary interprocedural JavaScript; dynamic keys remain unresolved, never silently covered.
const acorn=require('./vendor/acorn.cjs'),crypto=require('node:crypto');
const kids=n=>Object.values(n).flatMap(v=>Array.isArray(v)?v.filter(x=>x&&typeof x.type==='string'):v&&typeof v.type==='string'?[v]:[]);
const str=n=>n?.type==='Literal'&&typeof n.value==='string'?n.value:n?.type==='TemplateLiteral'&&!n.expressions.length?n.quasis[0].value.cooked:n?.type==='BinaryExpression'&&n.operator==='+'&&str(n.left)!==null&&str(n.right)!==null?str(n.left)+str(n.right):null;
const prop=n=>n?.type==='MemberExpression'?(n.computed?str(n.property):n.property.name):null;
function scan(code,file){
 let ast;try{ast=acorn.parse(code,{ecmaVersion:'latest',sourceType:'script',locations:true})}catch(e){ast=acorn.parse(code,{ecmaVersion:'latest',sourceType:'module',locations:true})}
 const rows=[],scopes=new Map(),parents=new Map();
 function bind(p,s,v){if(!p)return;if(p.type==='Identifier')s.names.set(p.name,v);else for(const c of kids(p))bind(c,s,null)}
 function visit(n,s){scopes.set(n,s);if(/^(FunctionExpression|FunctionDeclaration|ArrowFunctionExpression)$/.test(n.type)){if(n.type==='FunctionDeclaration'&&n.id)bind(n.id,s,null);s={parent:s,names:new Map(),kind:'function'};if(n.id)bind(n.id,s,null);for(const p of n.params)bind(p,s,null)}
 else if(n.type==='BlockStatement'||n.type==='CatchClause')s={parent:s,names:new Map(),kind:'block'};
 scopes.set(n,s);if(n.type==='CatchClause')bind(n.param,s,null);
 if(n.type==='VariableDeclarator'){let target=s;if(parents.get(n)?.kind==='var')while(target.parent&&target.kind==='block')target=target.parent;bind(n.id,target,n.init)}
 if(n.type==='ImportDeclaration'&&n.source.value==='cc')for(const spec of n.specifiers)bind(spec.local,s,spec.type==='ImportNamespaceSpecifier'?'cc':spec.type==='ImportSpecifier'?'cc.'+spec.imported.name:null);
 for(const c of kids(n)){parents.set(c,n);visit(c,s)}}visit(ast,{parent:null,names:new Map(),kind:'program'});
 function resolve(n,seen=new Set()){
  if(!n)return '';if(typeof n==='string')return n;if(n.type==='ChainExpression')return resolve(n.expression,seen);if(n.type==='CallExpression'&&prop(n.callee)==='bind')return resolve(n.callee.object,seen);if(n.type==='CallExpression'&&n.callee.name==='require'&&n.arguments[0]?.value==='cc')return 'cc';if(n.type==='Identifier'){
   let s=scopes.get(n);while(s){if(s.names.has(n.name)){const init=s.names.get(n.name);if(!init||seen.has(init))return '';return resolve(init,new Set([...seen,init]))}s=s.parent}
   return ['cc','window','globalThis','self','GameGlobal','tt','TTMinis','localStorage'].includes(n.name)?n.name:'';
  }
  if(n.type==='MemberExpression'){const b=resolve(n.object,seen),p=prop(n);return b&&p?b+'.'+p:''}return '';
 }
 function phase(n){let p=parents.get(n);while(p){if(/Function/.test(p.type)){const a=parents.get(p),o=a&&parents.get(a);return a?.type==='ArrayExpression'&&o?.type==='Property'?'module_initialization':'callable'}p=parents.get(p)}return 'module_initialization'}
 function delegate(n,args){let fn=parents.get(n);while(fn&&!/Function/.test(fn.type))fn=parents.get(fn);const holder=fn&&parents.get(fn);return !!(fn&&fn.params.length===1&&fn.params[0].type==='Identifier'&&args[0]?.type==='Identifier'&&args[0].name===fn.params[0].name&&fn.body.type==='BlockStatement'&&fn.body.body.length===1&&fn.body.body[0].type==='ReturnStatement'&&fn.body.body[0].argument===n&&holder?.type==='Property'&&(holder.key.name||holder.key.value)==='getItem')}
 function walk(n){if(n.type==='CallExpression'){
  let path=resolve(n.callee),args=n.arguments;
  if(path.endsWith('.call')){path=path.slice(0,-5);args=args.slice(1)}
  else if(path.endsWith('.apply')){path=path.slice(0,-6);args=args[1]?.type==='ArrayExpression'?args[1].elements:[]}
  const parts=path.split('.'),method=parts.pop(),receiver=parts.join('.');
  const storage=/(^|\.)localStorage$/.test(receiver),sdk=/^(tt|TTMinis\.game|(?:window|globalThis|self|GameGlobal)\.(?:tt|TTMinis\.game))$/.test(receiver);
  if(method==='getItem'&&storage||method==='getStorageSync'&&sdk){
   const expression=code.slice(n.start,n.end),key=str(args[0]);
   rows.push({file,key,expression,line:n.loc.start.line,column:n.loc.start.column,phase:phase(n),platform_storage_delegate:key===null&&method==='getStorageSync'&&delegate(n,args),site_id:crypto.createHash('sha256').update(file+'\0'+n.start+'\0'+expression).digest('hex')});
  }
 }for(const c of kids(n))walk(c)}walk(ast);return rows;
}
module.exports={scan};
if (require.main === module) {
  const usage = 'Usage: node scan_storage_consumers.cjs < input.json\nInput: {"files":[{"file":"path.js","code":"JavaScript source"}]}\nStatic storage-consumer inventory only; no runtime or quality approval.';
  if (process.argv.length === 3 && ['--help', '-h'].includes(process.argv[2])) {
    console.log(usage);
  } else if (process.argv.length !== 2) {
    console.error('not_run: unsupported arguments; use --help');
    process.exitCode = 2;
  } else {
    try {
      const raw = require('node:fs').readFileSync(0, 'utf8');
      if (!raw.trim()) throw new Error('not_run: no JSON input; use --help');
      const x = JSON.parse(raw);
      if (!x || !Array.isArray(x.files) || x.files.some(f => !f || typeof f.file !== 'string' || typeof f.code !== 'string')) {
        throw new Error('not_run: input requires a files array of file/code strings; use --help');
      }
      console.log(JSON.stringify({schema:'storage_consumers_scan.v1', sites:x.files.flatMap(f => scan(f.code, f.file))}));
    } catch (e) {
      console.error(e.message);
      process.exitCode = 2;
    }
  }
}
