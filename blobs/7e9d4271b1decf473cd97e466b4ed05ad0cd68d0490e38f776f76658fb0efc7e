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
function scan(source, file) {
  const options = {ecmaVersion:'latest', locations:true, allowReturnOutsideFunction:true};
  let ast; try { ast = acorn.parse(source, {...options,sourceType:'script'}); }
  catch (_) { ast = acorn.parse(source, {...options,sourceType:'module'}); }
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
    if (!reference || unqualified && shadowed(node) || compatible(node)) continue;
    hits.push({file,line:node.loc.start.line,reference:source.slice(node.start,node.end).slice(0,90)});
  }
  return hits;
}
module.exports = {scan};
if (require.main === module) {
  try {
    const input = JSON.parse(fs.readFileSync(0,'utf8'));
    if (!Array.isArray(input.files)) throw new Error('files must be an array');
    console.log(JSON.stringify({findings:input.files.flatMap(f=>scan(f.code,f.file))}));
  } catch (error) { console.error(error.message); process.exitCode=2; }
}
