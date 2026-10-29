'use strict';
// General SystemJS resource inventory is performed independently from actual
// cc setters by scan_runtime_resources. Private finite domains require an exact
// program AND JSON-data binding selected by the Python host.
const fs=require('fs'),cp=require('child_process'),path=require('path'),acorn=require('./vendor/acorn.cjs');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
function walk(n,fn,parents=[]){if(!n?.type)return;fn(n,parents);for(const [key,v]of Object.entries(n)){if(key==='loc')continue;if(Array.isArray(v))v.forEach(c=>walk(c,fn,[...parents,n]));else if(v?.type)walk(v,fn,[...parents,n])}}
function staticAlias(n,ast,parents=[]){
 if(n?.type!=='Identifier')return n;
 const declarations=[];let mutated=false;
 walk(ast,(x,ps)=>{if(x.type==='VariableDeclarator'&&x.id?.name===n.name&&x.init)declarations.push(x);if(x.type==='AssignmentExpression'||x.type==='UpdateExpression'){let root=x.left??x.argument;while(root?.type==='MemberExpression')root=root.object;if(root?.name===n.name)mutated=true;}});
 if(mutated||declarations.length!==1||declarations[0].start>=n.start)throw Error('nonstatic import-map alias');
 return declarations[0].init;
}
function finite(n,ast,seen=new Set()){
 if(!n||seen.has(n))throw Error('unresolved import map');seen.add(n);
 if(n.type==='Identifier')return finite(staticAlias(n,ast),ast,seen);
 if(n.type==='Literal')return n.value;
 if(n.type==='ObjectExpression')return Object.fromEntries(n.properties.map(p=>{if(p.type!=='Property'||p.computed)throw Error('dynamic import map');return [p.key.name??p.key.value,finite(p.value,ast,new Set(seen))]}));
 throw Error('unresolved import-map value');
}
function patternHas(n,name){if(!n)return false;if(n.type==='Identifier')return n.name===name;return Object.values(n).some(v=>Array.isArray(v)?v.some(x=>x?.type&&patternHas(x,name)):v?.type&&patternHas(v,name))}
function shadowed(ast,parents,name){
 let found=false;const owner=(ps,blocks)=>[...ps].reverse().find(p=>p.type==='Program'||/Function/.test(p.type)||(blocks&&(p.type==='BlockStatement'||p.type==='CatchClause')));
 walk(ast,(n,ps)=>{
  if(/Function/.test(n.type)&&parents.includes(n)&&n.params.some(p=>patternHas(p,name)))found=true;
  if(n.type==='CatchClause'&&parents.includes(n)&&patternHas(n.param,name))found=true;
  if(n.type==='VariableDeclarator'&&patternHas(n.id,name)){const decl=[...ps].reverse().find(p=>p.type==='VariableDeclaration');if(parents.includes(owner(ps,decl.kind!=='var')))found=true}
  if((n.type==='FunctionDeclaration'||n.type==='ClassDeclaration')&&n.id?.name===name&&parents.includes(owner(ps,true)))found=true;
  if(n.type==='ImportDeclaration'&&n.specifiers.some(s=>s.local?.name===name)&&parents.includes(owner(ps,true)))found=true;
 });return found;
}
function unmodifiedGlobal(ast,parents,name){
 if(shadowed(ast,parents,name))return false;let modified=false;
 walk(ast,(n,ps)=>{if(!['AssignmentExpression','UpdateExpression'].includes(n.type))return;let root=n.left??n.argument;while(root?.type==='MemberExpression')root=root.object;if(root?.name===name&&!shadowed(ast,ps,name))modified=true});return !modified;
}
function exactHandler(fn){
 if(!/Function/.test(fn?.type??'')||fn.async||fn.generator||fn.params.length!==1||fn.params[0].type!=='Identifier'||fn.params[0].name==='require')return null;
 let call=fn.body;if(call.type==='BlockStatement'){if(call.body.length!==1||!['ReturnStatement','ExpressionStatement'].includes(call.body[0].type))return null;call=call.body[0].argument??call.body[0].expression}
 if(call?.type==='ConditionalExpression'){
  const t=call.test,yes=call.consequent,no=call.alternate,param=fn.params[0].name;
  const valid=t?.type==='BinaryExpression'&&t.operator==='==='&&t.left?.type==='UnaryExpression'&&t.left.operator==='typeof'&&t.left.argument?.name==='requirePlugin'&&t.right?.value==='function'&&yes?.type==='CallExpression'&&yes.callee?.name==='requirePlugin'&&yes.arguments.length===1&&yes.arguments[0]?.name===param&&no?.type==='CallExpression'&&no.callee?.name==='require'&&no.arguments.length===1&&no.arguments[0]?.name===param;
  if(!valid)return null;call=no;
 }
 if(call?.type!=='CallExpression'||call.callee.name!=='require'||call.arguments.length!==1)return null;
 const arg=call.arguments[0],param=fn.params[0].name;
 return arg?.type==='Identifier'&&arg.name===param||arg?.type==='BinaryExpression'&&arg.operator==='+'&&arg.left.value==='.'&&arg.right.name===param?call:null;
}
function importMapFromModule(name){
 const text=input.files[name];if(typeof text!=='string')throw Error('import-map module missing');const ast=acorn.parse(text,{ecmaVersion:'latest'});let value;
 walk(ast,n=>{if(n.type==='CallExpression'&&!(n.callee.type==='MemberExpression'&&n.callee.object.name==='Object'&&n.callee.property.name==='defineProperty'&&n.arguments[0]?.name==='exports'&&n.arguments[1]?.value==='__esModule'))throw Error('import-map module is not static');if(n.type==='AssignmentExpression'&&!(n.left.type==='MemberExpression'&&n.left.object.name==='exports'&&(n.left.property.name??n.left.property.value)==='default'))throw Error('import-map module is mutated');if(n.type==='AssignmentExpression'&&n.left.type==='MemberExpression'&&n.left.object.name==='exports'&&(n.left.property.name??n.left.property.value)==='default'&&n.right.type!=='UnaryExpression')value=n.right});
 return finite(value,ast);
}
try{
 if(input.systemjs_profile){
  if(input.systemjs_profile.adapter!=='swole-authored-art-v1')throw Error('unsupported reviewed SystemJS adapter');
  const run=cp.spawnSync(process.execPath,[path.join(__dirname,'scan_systemjs_finite_art.cjs')],{input:JSON.stringify(input),encoding:'utf8',timeout:25000,maxBuffer:32*1024*1024});
  if(run.error||run.status!==0)throw Error('reviewed SystemJS adapter refused: '+(run.error||run.stderr));
  const result=JSON.parse(run.stdout);result.reviewed_profile=input.systemjs_profile.name;process.stdout.write(JSON.stringify(result));
 }else{
  const escapes=[],files=[];
  for(const [source,text]of Object.entries(input.files)){
   let ast;try{ast=acorn.parse(text,{ecmaVersion:'latest',sourceType:'script',allowReturnOutsideFunction:true})}catch(_){ast=acorn.parse(text,{ecmaVersion:'latest',sourceType:'module'})}
   walk(ast,(n,parents)=>{if(n.type!=='CallExpression'||n.callee.type!=='MemberExpression'||n.callee.object.name!=='System'||n.callee.property.name!=='warmup')return;
    if(!unmodifiedGlobal(ast,parents,'System')||!unmodifiedGlobal(ast,parents,'require'))throw Error('SystemJS warmup uses shadowed or modified globals');
    const config=n.arguments[0];if(config?.type!=='ObjectExpression')throw Error('dynamic SystemJS warmup configuration');
    const keys=config.properties.map(p=>p.type==='Property'&&!p.computed?(p.key?.name??p.key?.value):null);if(keys.some(k=>k===null)||new Set(keys).size!==keys.length)throw Error('dynamic or duplicate SystemJS warmup configuration');
    const get=key=>config.properties.find(p=>(p.key?.name??p.key?.value)===key)?.value;
    const url=get('importMapUrl');if(url?.type!=='Literal'||typeof url.value!=='string')return;
    const importName=path.posix.normalize(path.posix.join(path.posix.dirname(source),url.value));
    if(importName.startsWith('../')||path.posix.isAbsolute(importName))throw Error('unsafe SystemJS import map URL');
    const map=staticAlias(get('importMap'),ast,parents);let data;
    if(map?.type==='ObjectExpression')data=finite(map,ast);else {
     const call=map?.type==='MemberExpression'&&(map.property.name??map.property.value)==='default'?map.object:null;
     if(call?.type!=='CallExpression'||call.callee.name!=='require'||call.arguments.length!==1||typeof call.arguments[0]?.value!=='string'||path.posix.normalize(path.posix.join(path.posix.dirname(source),call.arguments[0].value))!==importName)throw Error('unknown SystemJS import-map expression');
     data=importMapFromModule(importName);
    }
    if(!data||typeof data.imports!=='object'||Array.isArray(data.imports))throw Error('SystemJS local import map missing');
    const targetFiles=[];
    for(const value of Object.values(data.imports)){
     if(typeof value!=='string'||/^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(value))throw Error('nonlocal SystemJS import target');
     const rel=path.posix.normalize(path.posix.join(path.posix.dirname(importName),value));
     if(rel.startsWith('../')||path.posix.isAbsolute(rel))throw Error('SystemJS import target escapes package');targetFiles.push(rel);
    }
    // Only exact warmup namespace handlers are delegated. Arbitrary require,
    // eval and actual resource calls remain in the independent inventory.
    const handlers=[get('defaultHandler')],table=get('handlers');
    if(table&&table.type!=='ObjectExpression')throw Error('dynamic SystemJS namespace handlers');
    if(table?.type==='ObjectExpression')for(const entry of table.properties){if(entry.type!=='Property'||entry.computed)throw Error('dynamic SystemJS namespace handler');handlers.push(entry.value)}
    for(const handler of handlers){if(!handler)continue;const call=exactHandler(handler);if(!call)throw Error('unknown SystemJS namespace handler');escapes.push({id:source+':'+call.start,source,reason:'Exact System.warmup local import-map handler; original target files and scriptPackages validated each call'})}
    for(const rel of [importName,...targetFiles])files.push({id:source+':'+n.start,source,path:rel,reason:'SystemJS warmup local module target'});
   });
  }
  process.stdout.write(JSON.stringify({schema:'cocos_resource_sites.v1',profile:'generic-systemjs-cc-imports-v1',root_files:input.files,sites:[],escapes:[],owned_method_definitions:[],delegated_sites:[],native_file_sites:[],module_file_sites:files,module_handler_escapes:escapes}));
 }
}catch(error){process.stdout.write(JSON.stringify({error:String(error)}));process.exitCode=1}
