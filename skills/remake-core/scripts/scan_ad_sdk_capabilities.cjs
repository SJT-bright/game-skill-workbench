'use strict';
// Known-shape, read-only proof of optional canIUse rejecting callable rewarded APIs.
// No game code is executed. This is not a general SDK resolver verifier.
const acorn = require('./vendor/acorn.cjs');
function children(n) { return Object.values(n).flatMap(v => Array.isArray(v) ? v.filter(x => x && typeof x.type === 'string') : v && typeof v.type === 'string' ? [v] : []); }
const isFn = n => n && ['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(n.type);
const prop = n => n?.type === 'MemberExpression' ? (!n.computed ? n.property.name : n.property.type === 'Literal' ? n.property.value : null) : null;
function scanAST(ast, file = '<source>') {
  let factory=false,capability=false;
  function relevant(n){if(n.type==='CallExpression'){if(prop(n.callee)==='canIUse')capability=true;if(prop(n.callee)==='createRewardedVideoAd'||['call','apply'].includes(prop(n.callee))&&prop(n.callee.object)==='createRewardedVideoAd')factory=true;}if(factory&&capability)return;for(const c of children(n))relevant(c);}
  relevant(ast);if(!factory||!capability)return {findings:[],unresolved:[]};
  const nodes=[],parents=new Map(),scopeOf=new Map(),fnOf=new Map(),scopeParent=new Map(),bindings=new Map();
  const functionScopes=new Set(),fieldWrites=new Map();
  function scope(parent,fn=false) { const s={};scopeParent.set(s,parent);bindings.set(s,new Map());if(fn)functionScopes.add(s);return s; }
  const program=scope(null,true);
  const container = n => { const fn=fnOf.get(n);return fn ? (fnOf.get(parents.get(fn))||ast) : ast; };
  function declare(s,name,init,fn) { if(!name)return;const m=bindings.get(s);if(!m.has(name))m.set(name,{init:init||null,fn:fn||null,writes:init?1:0,values:init?[init]:[]});else if(init){const b=m.get(name);b.init=null;b.writes++;b.values.push(init);} }
  function visit(n,parent,s,fn) {
    if (!n || !n.type) return;
    parents.set(n,parent);nodes.push(n);
    if(isFn(n)) {
      if(n.type==='FunctionDeclaration')declare(s,n.id?.name,n,n);
      s=scope(s,true);fn=n;if(n.id)declare(s,n.id.name,n,n);
      for(const p of n.params)if(p.type==='Identifier')declare(s,p.name,null,null);
    } else if(n.type==='BlockStatement' || n.type==='CatchClause' || ['ForStatement','ForInStatement','ForOfStatement'].includes(n.type)) {
      s=scope(s);if(n.type==='CatchClause'&&n.param?.type==='Identifier')declare(s,n.param.name,null,null);
    }
    scopeOf.set(n,s);fnOf.set(n,fn);
    if(n.type==='VariableDeclarator'&&n.id.type==='Identifier') {
      let owner=s;
      if(parent?.kind==='var')while(!functionScopes.has(owner))owner=scopeParent.get(owner);
      declare(owner,n.id.name,n.init,isFn(n.init)?n.init:null);
    }
    for(const c of children(n))visit(c,n,s,fn);
  }
  visit(ast,null,program,null);
  function binding(name,n) { for(let s=scopeOf.get(n);s;s=scopeParent.get(s)){const b=bindings.get(s).get(name);if(b)return b;}return null; }
  for(const n of nodes)if(n.type==='AssignmentExpression'&&n.operator==='=') {
    if(n.left.type==='Identifier') { const b=binding(n.left.name,n);if(b){if(b.writes===0){b.init=n.right;b.fn=isFn(n.right)?n.right:null;}else b.init=null;b.writes++;b.values.push(n.right);} }
    else if(n.left.type==='MemberExpression'&&n.left.object.type==='ThisExpression') {
      const name=prop(n.left);if(name){if(!fieldWrites.has(name))fieldWrites.set(name,[]);fieldWrites.get(name).push({value:n.right,container:container(n)});}
    }
  }
  function constant(n) {
    if(!n)return {known:false};if(n.type==='Literal')return {known:true,value:n.value};
    if(n.type==='UnaryExpression'){const x=constant(n.argument);if(x.known&&n.operator==='!')return {known:true,value:!x.value};if(n.operator==='void')return {known:true,value:undefined};}
    return {known:false};
  }
  function root(n,seen=new Set()) {
    if(!n||seen.has(n))return false;seen=new Set(seen).add(n);
    if(n.type==='Identifier'){if(['window','globalThis','global','self','GameGlobal'].includes(n.name)&&!binding(n.name,n))return true;const b=binding(n.name,n);return !!b?.init&&root(b.init,seen);}
    if(n.type==='ConditionalExpression')return root(n.consequent,seen)&&root(n.alternate,seen);
    if(n.type==='CallExpression'&&n.callee.type==='CallExpression'&&n.callee.callee.type==='Identifier'&&n.callee.callee.name==='Function'&&!binding('Function',n)) {
      const args=n.callee.arguments;return args.length>0&&args.at(-1).value==='return this';
    }
    return false;
  }
  function returns(fn) { const out=[];function v(n){if(n!==fn&&isFn(n))return;if(n.type==='ReturnStatement'&&n.argument)out.push(n.argument);for(const c of children(n))v(c);}v(fn.body);return out; }
  function host(n,seen=new Set()) {
    if(!n||seen.has(n))return false;seen=new Set(seen).add(n);
    if(n.type==='Identifier'){
      const b=binding(n.name,n);if(!b&&['tt','wx'].includes(n.name))return true;
      return !!b?.init&&host(b.init,seen)||!!b?.values.length&&b.values.some(x=>host(x,seen))&&b.values.every(x=>x.type==='Literal'&&x.value===null||host(x,seen));
    }
    if(n.type==='MemberExpression') {
      if(prop(n)==='game') {
        const o=n.object;
        if(o.type==='Identifier'&&o.name==='TTMinis'&&!binding(o.name,o))return true;
        if(o.type==='MemberExpression'&&prop(o)==='TTMinis'&&root(o.object,seen))return true;
      }
      if(['tt','wx'].includes(prop(n))&&root(n.object,seen))return true;
      // A candidate selected from a literal host array, not an arbitrary object property.
      if(n.computed)return host(n.object,seen);
      return false;
    }
    if(n.type==='ArrayExpression')return n.elements.some(x=>host(x,seen));
    if(n.type==='LogicalExpression'||n.type==='ConditionalExpression')return host(n.right||n.consequent,seen)||host(n.left||n.alternate,seen);
    if(isFn(n))return returns(n).some(x=>host(x,seen));
    if(n.type==='CallExpression') {
      if(n.callee.type==='Identifier'){const b=binding(n.callee.name,n);return !!b?.fn&&host(b.fn,seen);}
      if(n.callee.type==='MemberExpression'&&n.callee.object.type==='ThisExpression')return (fieldWrites.get(prop(n.callee))||[]).filter(x=>x.container===container(n)).some(x=>host(x.value,seen));
    }
    return false;
  }
  // Resolve function references without treating a local lookalike as a platform object.
  function functions(n) { if(!n)return [];if(isFn(n))return[n];if(n.type==='Identifier'){const b=binding(n.name,n);return b?.fn?[b.fn]:[];}if(n.type==='LogicalExpression')return [...functions(n.left),...functions(n.right)];return []; }
  const adParams=new Map();
  const UNKNOWN=Symbol('unknown');
  function rejected(call) { for(let n=parents.get(call);n&&fnOf.get(n)===fnOf.get(call);n=parents.get(n))if(n.type==='IfStatement'&&deny(n.consequent)&&value(n.test,call,false,fnOf.get(call))===true&&value(n.test,call,true,fnOf.get(call))===false)return true;return false; }
  function mark(fn,receiver,method) { if(!adParams.has(fn))adParams.set(fn,[]);adParams.get(fn).push({receiver,method}); }
  for(const call of nodes.filter(x=>x.type==='CallExpression')) {
    if(call.callee.type==='Identifier') {
      const target=functions(call.callee)[0];if(!target||!rejected(call))continue;
      for(let i=0;i<call.arguments.length;i++)if(call.arguments[i]?.value==='createRewardedVideoAd') {
        for(let j=0;j<call.arguments.length;j++)if(i!==j&&host(call.arguments[j]))mark(target,target.params[j]?.name,target.params[i]?.name);
      }
    } else if(call.callee.type==='MemberExpression'&&call.callee.object.type==='ThisExpression'&&call.arguments[0]?.value==='createRewardedVideoAd') {
      for(const write of (fieldWrites.get(prop(call.callee))||[]).filter(x=>x.container===container(call)))for(const target of functions(write.value))mark(target,null,target.params[0]?.name);
    }
  }
  function adMethod(n,fn) { return n?.value==='createRewardedVideoAd'||n?.type==='Identifier'&&(adParams.get(fn)||[]).some(x=>x.method===n.name); }
  function receiver(n,fn) { return host(n)||n?.type==='Identifier'&&(adParams.get(fn)||[]).some(x=>x.receiver===n.name); }
  function adFactory(n) { return n?.type==='CallExpression'&& (prop(n.callee)==='createRewardedVideoAd'||['call','apply'].includes(prop(n.callee))&&prop(n.callee.object)==='createRewardedVideoAd'); }
  const hasFactory=nodes.some(adFactory);
  if(!hasFactory)return {findings:[],unresolved:[]};
  const out=[],seen=new Set();
  function emit(n,rule,reason) { const key=rule+':'+n.start;if(seen.has(key))return;seen.add(key);out.push({file,line:n.loc?.start.line||1,column:n.loc?.start.column||0,rule,reason}); }
  function deny(n) {
    if(!n)return false;
    if(n.type==='ContinueStatement'||n.type==='ThrowStatement')return true;
    if(n.type==='BlockStatement')return n.body.some(deny);
    if(n.type!=='ReturnStatement')return false;
    if(!n.argument)return true;const x=constant(n.argument);if(x.known)return !x.value;
    let rejected=false;function v(x){if(x.type==='Literal'&&typeof x.value==='string'&&['unsupported','unavailable','sdk_missing','not_supported'].includes(x.value))rejected=true;for(const c of children(x))v(c);}v(n.argument);return rejected;
  }
  function value(n,call,cap,fn) {
    if(!n)return UNKNOWN;if(n===call)return cap;
    const c=constant(n);if(c.known)return c.value;
    if(receiver(n,fn))return {};if(adMethod(n,fn))return 'createRewardedVideoAd';
    if(n.type==='UnaryExpression') {
      if(n.operator==='typeof'&&n.argument.type==='MemberExpression'&&receiver(n.argument.object,fn)) {
        if(prop(n.argument)==='canIUse'||adMethod(n.argument.property,fn)||prop(n.argument)==='createRewardedVideoAd')return 'function';
      }
      const a=value(n.argument,call,cap,fn);if(a!==UNKNOWN&&n.operator==='!')return !a;return UNKNOWN;
    }
    if(n.type==='LogicalExpression') {
      const a=value(n.left,call,cap,fn);if(a===UNKNOWN)return UNKNOWN;
      if(n.operator==='&&')return a?value(n.right,call,cap,fn):a;
      if(n.operator==='||')return a?a:value(n.right,call,cap,fn);
    }
    if(n.type==='BinaryExpression') {
      const a=value(n.left,call,cap,fn),b=value(n.right,call,cap,fn);if(a===UNKNOWN||b===UNKNOWN)return UNKNOWN;
      if(n.operator==='===')return a===b;if(n.operator==='!==')return a!==b;if(n.operator==='==')return a==b;if(n.operator==='!=')return a!=b;
    }
    return UNKNOWN;
  }
  for(const call of nodes) {
    if(call.type!=='CallExpression'||prop(call.callee)!=='canIUse')continue;
    const fn=fnOf.get(call);if(!adMethod(call.arguments[0],fn)||!receiver(call.callee.object,fn))continue;
    for(let n=parents.get(call);n&&fnOf.get(n)===fn;n=parents.get(n)) {
      if(n.type==='IfStatement'&&deny(n.consequent)) {
        const absent=value(n.test,call,undefined,fn),yes=value(n.test,call,true,fn);
        if(absent!==UNKNOWN&&!!absent&&yes!==UNKNOWN&&!yes)emit(call,'ad_sdk_can_i_use_falsy_rejection','Callable rewarded API is rejected when canIUse returns undefined; reject only explicit false (or a failed capability call).');
      }
      if(n.type==='ReturnStatement'&&(adParams.get(fn)||[]).some(x=>x.receiver)) {
        if(value(n.argument,call,undefined,fn)===false&&value(n.argument,call,true,fn)===true)emit(call,'ad_sdk_can_i_use_strict_true','The advertised rewarded-API predicate requires canIUse === true; absent or undefined capability information must not reject a callable API.');
      }
    }
  }
  return {findings:out,unresolved:[]};
}
function scan(source,file) { let ast;const opt={ecmaVersion:'latest',locations:true,allowReturnOutsideFunction:true};try{ast=acorn.parse(source,{...opt,sourceType:'script'});}catch(_){ast=acorn.parse(source,{...opt,sourceType:'module'});}return scanAST(ast,file); }
module.exports={scan,scanAST};
if(require.main===module){
  const fs=require('fs');
  if(process.argv.slice(2).some(arg=>arg==='--help'||arg==='-h')){
    console.log('Usage: node scan_ad_sdk_capabilities.cjs < input.json\nRead JSON from stdin with a nonempty files array: {"files":[{"file":"game.js","code":"..."}]}.\nScans known rewarded SDK capability rejection shapes; no game code is executed.');
  }else{
    try{
      const raw=fs.readFileSync(0,'utf8');
      if(!raw.trim())throw Error('JSON input with nonempty files required');
      const input=JSON.parse(raw);
      if(!Array.isArray(input.files)||!input.files.length)throw Error('nonempty files required');
      const reports=input.files.map(x=>scan(x.code,x.file));
      console.log(JSON.stringify({status:reports.some(x=>x.findings.length)?'risk_detected':'checked',checked:reports.length,findings:reports.flatMap(x=>x.findings),unresolved:reports.flatMap(x=>x.unresolved)}));
    }catch(e){console.log(JSON.stringify({status:'not_run',checked:0,reason:e.message}));process.exitCode=2;}
  }
}
