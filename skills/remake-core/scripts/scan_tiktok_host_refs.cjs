'use strict';
const fs = require('node:fs');
const acorn = require('./vendor/acorn.cjs');
function children(node) {
  return Object.values(node).flatMap(value => Array.isArray(value) ? value.filter(x => x && typeof x.type === 'string') :
    value && typeof value.type === 'string' ? [value] : []);
}
function walk(node, fn) { fn(node); for (const child of children(node)) walk(child, fn); }
function constantString(node) {
  if (node?.type === 'Literal' && typeof node.value === 'string') return node.value;
  if (node?.type === 'TemplateLiteral' && node.expressions.length === 0) return node.quasis[0].value.cooked;
  if (node?.type === 'BinaryExpression' && node.operator === '+') {
    const left=constantString(node.left),right=constantString(node.right);
    if (typeof left === 'string' && typeof right === 'string') return left+right;
  }
  return null;
}
function property(node) {
  return node?.type === 'MemberExpression' ? (node.computed ? constantString(node.property) : node.property.name) : null;
}
function hostName(node, name) {
  return node?.type === 'Identifier' && node.name === name ||
    node?.type === 'MemberExpression' && property(node) === name &&
    node.object.type === 'Identifier' && ['root','window','globalThis','global','self','GameGlobal'].includes(node.object.name);
}
function hasHost(node, name) {
  let found = false; walk(node, child => { if (hostName(child, name)) found = true; }); return found;
}
function parse(source) {
  const options = {ecmaVersion:'latest', locations:true, allowReturnOutsideFunction:true};
  try { return acorn.parse(source, {...options,sourceType:'script'}); }
  catch (_) { return acorn.parse(source, {...options,sourceType:'module'}); }
}
function scan(source, file, context = {}) {
  const ast = parse(source);
  const parents = new Map(), nodes = [];
  walk(ast, node => { nodes.push(node); for (const child of children(node)) parents.set(child,node); });
  // Resolve real lexical bindings, not the presence of a declaration anywhere
  // in an enclosing function. In particular, block let/const, catch parameters
  // and loop declarations must not hide a later reference outside their scope.
  const scopeOf = new Map(), boundIdentifiers = new Set();
  function newScope(type, parent) { return {type, parent, bindings:new Map()}; }
  function declare(pattern, scope, kind, init) {
    if (!pattern) return;
    if (pattern.type === 'Identifier') {
      boundIdentifiers.add(pattern);
      const previous=scope.bindings.get(pattern.name);
      if (!(kind === 'var' && !init && previous?.kind === 'var')) {
        scope.bindings.set(pattern.name,{kind,init,scope});
      }
    } else if (pattern.type === 'RestElement') declare(pattern.argument,scope,kind,init);
    else if (pattern.type === 'AssignmentPattern') declare(pattern.left,scope,kind,init);
    else if (pattern.type === 'ArrayPattern') {
      for (const item of pattern.elements) declare(item,scope,kind,init);
    } else if (pattern.type === 'ObjectPattern') {
      for (const item of pattern.properties) declare(item.type === 'RestElement' ? item.argument : item.value,scope,kind,init);
    }
  }
  function varScope(scope) {
    while (!['program','function','static'].includes(scope.type)) scope=scope.parent;
    return scope;
  }
  function assignScopes(node, scope) {
    scopeOf.set(node,scope);
    if (node.type === 'Program') {
      for (const child of node.body) assignScopes(child,scope);
      return;
    }
    if (['FunctionExpression','FunctionDeclaration','ArrowFunctionExpression'].includes(node.type)) {
      if (node.type === 'FunctionDeclaration') declare(node.id,scope,'function');
      // Parameter defaults cannot see declarations in the function body.
      const params=newScope('parameters',scope), body=newScope('function',params);
      if (node.type === 'FunctionExpression') declare(node.id,params,'function');
      if (node.id) scopeOf.set(node.id,params);
      for (const param of node.params) declare(param,params,'parameter');
      for (const param of node.params) assignScopes(param,params);
      assignScopes(node.body,body);
      return;
    }
    if (node.type === 'BlockStatement' || node.type === 'StaticBlock') {
      const block=newScope(node.type === 'StaticBlock' ? 'static' : 'block',scope);
      scopeOf.set(node,block);
      for (const child of node.body) assignScopes(child,block);
      return;
    }
    if (['ForStatement','ForInStatement','ForOfStatement'].includes(node.type)) {
      const loop=newScope('block',scope);scopeOf.set(node,loop);
      for (const child of children(node)) assignScopes(child,loop);
      return;
    }
    if (node.type === 'CatchClause') {
      const caught=newScope('catch',scope);scopeOf.set(node,caught);
      declare(node.param,caught,'catch');
      if (node.param) assignScopes(node.param,caught);
      assignScopes(node.body,caught);
      return;
    }
    if (node.type === 'SwitchStatement') {
      assignScopes(node.discriminant,scope);
      const cases=newScope('block',scope);
      for (const child of node.cases) assignScopes(child,cases);
      return;
    }
    if (node.type === 'ClassDeclaration' || node.type === 'ClassExpression') {
      if (node.type === 'ClassDeclaration') declare(node.id,scope,'class');
      const local=newScope('class',scope);declare(node.id,local,'class');
      for (const child of children(node)) assignScopes(child,local);
      return;
    }
    if (node.type === 'ImportDeclaration') {
      for (const specifier of node.specifiers) declare(specifier.local,scope,'import');
    }
    if (node.type === 'VariableDeclarator') {
      const kind=parents.get(node).kind;
      declare(node.id,kind === 'var' ? varScope(scope) : scope,kind,node.init);
    }
    for (const child of children(node)) assignScopes(child,scope);
  }
  assignScopes(ast,newScope('program',null));
  function isIdentifierReference(node) {
    const p=parents.get(node);
    if (boundIdentifiers.has(node)) return false;
    if (p?.type === 'MemberExpression' && !p.computed && p.property === node) return false;
    if (p?.type === 'Property' && p.key === node && !p.computed && !p.shorthand) return false;
    if (['MethodDefinition','PropertyDefinition'].includes(p?.type) && p.key === node && !p.computed) return false;
    if (/Function/.test(p?.type || '') && p.id === node) return false;
    if (p?.type === 'ImportSpecifier' && p.imported === node) return false;
    if (p?.type === 'ExportSpecifier' && p.exported === node) return false;
    return !(['LabeledStatement','BreakStatement','ContinueStatement'].includes(p?.type) && p.label === node);
  }
  function bindingScope(node,name) {
    for(let scope=scopeOf.get(node);scope;scope=scope.parent)if(scope.bindings.has(name))return scope;
    return null;
  }
  // An unused local alias merely reads an optional global property. If the value
  // is used, escapes, or can be accessed through eval/with it remains checked.
  const unusedReads=new Set();
  for(const declaration of nodes) {
    if(declaration.type!=='VariableDeclarator'||declaration.id.type!=='Identifier'||
       declaration.init?.type!=='MemberExpression'||!hostName(declaration.init,'wx')||
       !['window','globalThis'].includes(declaration.init.object.name))continue;
    const name=declaration.id.name,scope=bindingScope(declaration.id,name);
    if(nodes.some(n=>n.type==='Identifier'&&n.name===name&&isIdentifierReference(n)&&bindingScope(n,name)===scope))continue;
    let owner=declaration;
    while(parents.has(owner)&&!['Program','FunctionExpression','FunctionDeclaration','ArrowFunctionExpression'].includes(owner.type))owner=parents.get(owner);
    let dynamic=false;
    walk(owner,n=>{if(n.type==='WithStatement'||n.type==='CallExpression'&&n.callee.type==='Identifier'&&n.callee.name==='eval')dynamic=true;});
    if(!dynamic)unusedReads.add(declaration.init);
  }
  function rootWx(node) {
    return node?.type==='MemberExpression'&&hostName(node,'wx')?node:null;
  }
  function sameRoot(a,b) {
    return !!a&&!!b&&a.object.name===b.object.name&&property(a)===property(b);
  }
  function guardedOptional(node) {
    const base=rootWx(node)||(node.type==='MemberExpression'?rootWx(node.object):null);
    if(!base||!['window','globalThis'].includes(base.object.name))return false;
    // bare wx or an unbound local root can throw before testing the property.
    for(let current=node;parents.has(current);current=parents.get(current)) {
      const p=parents.get(current);
      if(/Function/.test(p.type))break; // A deferred callback does not inherit the guard.
      if(p.type!=='LogicalExpression'||p.operator!=='&&'||!sameRoot(rootWx(p.left),base))continue;
      // Only a direct guarded call; sequences or mutations cannot reuse a stale
      // existence check, nor can a guard for window.wx protect globalThis.wx.
      if(p.right.type!=='CallExpression'||!sameRoot(rootWx(p.right.callee?.object),base))continue;
      let writes=false;
      walk(p.right,n=>{if(n.type==='AssignmentExpression'||n.type==='UpdateExpression'||n.type==='UnaryExpression'&&n.operator==='delete')writes=true;});
      if(!writes&&(node===p.left||node===p.right.callee||node===p.right.callee.object))return true;
    }
    return false;
  }
  // Root-level Creator exports use the same real engine as cocos/<name>.js.
  // Recognize its module graph and version, but exempt only the guarded feature
  // probes below, never the entire file or appended game code.
  let engineShape=false;
  if(context.requiredEngine&&source.length>100000&&/cc\.ENGINE_VERSION\s*=\s*["']2\.4\.\d+["']/.test(source)) {
    engineShape=nodes.some(n=>n.type==='ObjectExpression'&&n.properties.filter(p=>p.type==='Property'&&p.value.type==='ArrayExpression'&&p.value.elements[0]?.type==='FunctionExpression'&&p.value.elements[1]?.type==='ObjectExpression').length>=100);
  }
  function guardedEngineProbe(node) {
    if(!engineShape||node.type!=='MemberExpression'||node.object.type!=='Identifier'||node.object.name!=='wx'||!['getSharedCanvas','getSystemInfoSync'].includes(property(node)))return false;
    if(parents.get(node)?.type!=='UnaryExpression'||parents.get(node).operator!=='!')return false;
    let owner=node;
    while(parents.has(owner)&&!['FunctionExpression','FunctionDeclaration','ArrowFunctionExpression'].includes(owner.type))owner=parents.get(owner);
    if(owner.body?.type!=='BlockStatement')return false;
    for(let current=node;parents.has(current)&&current!==owner;current=parents.get(current)) {
      const p=parents.get(current),left=p?.left;
      if(p.type!=='LogicalExpression'||p.operator!=='||'||left?.type!=='UnaryExpression'||left.operator!=='!'||left.argument.type!=='CallExpression')continue;
      const call=left.argument;
      if(call.callee.type!=='Identifier'||call.arguments.length!==1||call.arguments[0].value!=='wx')continue;
      const helper=owner.body.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name===call.callee.name);
      if(!helper||helper.params.length!==1||helper.body.body.length!==1)continue;
      const expression=helper.body.body[0].argument;
      if(helper.body.body[0].type!=='ReturnStatement'||expression?.type!=='BinaryExpression'||!['==','==='].includes(expression.operator))continue;
      const [text,test]=expression.left.value==='object'?[expression.left,expression.right]:[expression.right,expression.left];
      if(text.value!=='object'||test.type!=='UnaryExpression'||test.operator!=='typeof'||test.argument.type!=='MemberExpression'||!test.argument.computed||test.argument.property.name!==helper.params[0].name)continue;
      const globalName=test.argument.object.name;
      const globalDecl=owner.body.body.flatMap(n=>n.type==='VariableDeclaration'?n.declarations:[]).find(n=>n.id.name===globalName);
      const init=globalDecl?.init;
      if(init?.type==='ConditionalExpression'&&init.test.type==='BinaryExpression'&&
         [init.test.left,init.test.right].some(n=>n.type==='UnaryExpression'&&n.operator==='typeof'&&n.argument.name==='window')&&
         [init.test.left,init.test.right].some(n=>n.value==='undefined')&&
         ((['==','==='].includes(init.test.operator)&&init.consequent.name==='global'&&init.alternate.name==='window')||
          (['!=','!=='].includes(init.test.operator)&&init.consequent.name==='window'&&init.alternate.name==='global')))return true;
    }
    return false;
  }
  function shadowed(node) {
    for (let scope=scopeOf.get(node);scope;scope=scope.parent) {
      const binding=scope.bindings.get('wx');
      if (!binding) continue;
      // A top-level `var wx` shares the host global and may retain the real
      // WeChat object. Only an explicit ordinary local value proves otherwise.
      if (scope.type === 'program' && binding.kind === 'var') {
        return !!binding.init && ['ObjectExpression','ArrayExpression','FunctionExpression',
          'ArrowFunctionExpression','ClassExpression','Literal'].includes(binding.init.type);
      }
      return true;
    }
    return false;
  }
  function plainWx(node) { return hostName(node,'wx'); }
  function fallbackValue(node) {
    if (plainWx(node)) return true;
    return node?.type === 'LogicalExpression' && node.operator === '&&' &&
      node.left.type === 'BinaryExpression' && ['!==','!='].includes(node.left.operator) &&
      ((node.left.left.type === 'UnaryExpression' && node.left.left.operator === 'typeof' &&
        plainWx(node.left.left.argument) && node.left.right.value === 'undefined') ||
       (node.left.right.type === 'UnaryExpression' && node.left.right.operator === 'typeof' &&
        plainWx(node.left.right.argument) && node.left.left.value === 'undefined')) &&
      plainWx(node.right);
  }
  function compatible(node) {
    // Only the value expression can be exempt. Accesses such as wx.login() never qualify.
    for (let value = node; value && value.type !== 'Program'; value = parents.get(value)) {
      if (!fallbackValue(value)) continue;
      for (let array = parents.get(value); array && array.type === 'ArrayExpression'; array = parents.get(array)) {
        let element = value;
        while (parents.get(element) !== array) element = parents.get(element);
        const index = array.elements.indexOf(element);
        const earlier = array.elements.slice(0,index).filter(Boolean);
        if (earlier.some(n => hasHost(n,'TTMinis')) && earlier.some(n => hasHost(n,'tt'))) return true;
      }
      const parent = parents.get(value);
      if (parent?.type === 'LogicalExpression' && parent.operator === '||' && parent.right === value &&
          hasHost(parent.left,'TTMinis') && hasHost(parent.left,'tt')) return true;
    }
    return false;
  }
  const hits = [];
  for (const node of nodes) {
    const p = parents.get(node);
    let reference = false, unqualified = false;
    if (node.type === 'UnaryExpression' && node.operator === 'typeof' && hostName(node.argument,'wx')) {
      reference = true; unqualified = node.argument.type === 'Identifier';
    } else if (node.type === 'MemberExpression' && hostName(node.object,'wx')) {
      reference = true; unqualified = node.object.type === 'Identifier';
    } else if (node.type === 'MemberExpression' && hostName(node,'wx')) {
      if (p?.type === 'MemberExpression' && p.object === node || p?.type === 'UnaryExpression' && p.operator === 'typeof') continue;
      reference = true;
    } else if (node.type === 'Identifier' && node.name === 'wx') {
      if (boundIdentifiers.has(node)) continue;
      if (p?.type === 'MemberExpression' && (p.object === node || !p.computed && p.property === node) ||
          p?.type === 'UnaryExpression' && p.operator === 'typeof' ||
          p?.type === 'VariableDeclarator' && p.id === node ||
          p?.type === 'Property' && p.key === node && !p.computed && !p.shorthand ||
          ['MethodDefinition','PropertyDefinition'].includes(p?.type) && p.key === node && !p.computed ||
          p?.type === 'ImportSpecifier' && p.imported === node ||
          p?.type === 'ExportSpecifier' && p.exported === node ||
          ['LabeledStatement','BreakStatement','ContinueStatement'].includes(p?.type) && p.label === node ||
          /Function/.test(p?.type || '') && p.params.includes(node)) continue;
      reference = true; unqualified = true;
    }
    if (!reference || unusedReads.has(node) || guardedOptional(node) || guardedEngineProbe(node) || unqualified && shadowed(node) || compatible(node)) continue;
    hits.push({file,line:node.loc.start.line,reference:source.slice(node.start,node.end).slice(0,90)});
  }
  return hits;
}
function scanFiles(files) {
  const entry=files.find(f=>f.file==='game.js'),required=new Set();
  if(entry)walk(parse(entry.code),n=>{
    if(n.type==='CallExpression'&&n.callee.type==='Identifier'&&n.callee.name==='require'&&n.arguments.length===1&&
       /^\.\/cocos2d-js(?:-min)?\.js$/.test(n.arguments[0].value||''))required.add(n.arguments[0].value.slice(2));
  });
  return files.flatMap(f=>scan(f.code,f.file,{requiredEngine:required.has(f.file)}));
}
module.exports = {scan,scanFiles};
if (require.main === module) {
  if (process.argv.includes('--help')) {
    console.log('Usage: node scan_tiktok_host_refs.cjs < input.json\nInput is {files:[{file,code}]}. Read-only structural check.');
  } else {
    let phase = 'input';
    try {
      const raw = fs.readFileSync(0, 'utf8');
      if (!raw.trim()) throw new Error('input required');
      phase = 'json';
      const input = JSON.parse(raw);
      phase = 'input';
      if (!input || !Object.prototype.hasOwnProperty.call(input, 'files') || Array.isArray(input.files) && !input.files.length) {
        throw new Error('input required');
      }
      if (!Array.isArray(input.files)) throw new Error('files must be a nonempty array');
      if (!input.files.every(row => row && typeof row.file === 'string' && row.file.trim() && typeof row.code === 'string' && row.code.trim())) {
        throw new Error('input required');
      }
      phase = 'javascript';
      const findings = scanFiles(input.files);
      console.log(JSON.stringify({status: findings.length ? 'risk_detected' : 'checked', checked: input.files.length, findings}));
    } catch (error) {
      const reason = phase === 'json' ? 'invalid JSON input: ' + error.message :
        phase === 'javascript' ? 'JavaScript parse failed: ' + error.message : error.message;
      console.log(JSON.stringify({status: 'not_run', checked: 0, reason}));
      process.exitCode = 2;
    }
  }
}
