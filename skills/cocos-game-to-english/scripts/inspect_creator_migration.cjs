'use strict';

// Inspect Creator 2.4 CommonJS tables as syntax. Game modules are never executed here.
const acorn = require('../../remake-core/scripts/vendor/acorn.cjs');

function key(node) {
  if (!node) return null;
  if (node.type === 'Identifier') return node.name;
  if (node.type === 'Literal' && typeof node.value === 'string') return node.value;
  return null;
}

function visit(node, fn, parent = null) {
  if (!node || typeof node.type !== 'string') return;
  fn(node, parent);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach(child => visit(child, fn, node));
    else visit(value, fn, node);
  }
}

function indexed(node, object, item) {
  return node?.type === 'MemberExpression' && node.computed &&
    node.object.type === 'Identifier' && node.object.name === object &&
    node.property.type === 'Identifier' && node.property.name === item;
}

function lookupGuard(statement, table, id) {
  let test = statement?.type === 'IfStatement' && statement.test;
  if (test?.type === 'SequenceExpression') test = test.expressions.at(-1);
  return test?.type === 'UnaryExpression' && test.operator === '!' && indexed(test.argument, table, id);
}

// Recognize the emitted fallback by its operations, independent of local path and variable names.
function loaderKind(factory) {
  if (factory.type !== 'FunctionExpression' || factory.params.some(p => p.type !== 'Identifier')) return 'unknown';
  const [table, cache] = factory.params.map(p => p.name);
  for (const load of factory.body.body.filter(n => n.type === 'FunctionDeclaration')) {
    const id = load.params[0]?.name;
    const outer = load.body.body.find(n => lookupGuard(n, cache, id))?.consequent?.body;
    const fallback = outer?.find(n => lookupGuard(n, table, id))?.consequent?.body;
    if (!fallback) continue;
    const split = fallback.flatMap(n => n.declarations || []).find(n => {
      const call = n.init;
      return n.id.type === 'Identifier' && call?.type === 'CallExpression' &&
        call.callee.type === 'MemberExpression' && call.callee.object.name === id &&
        key(call.callee.property) === 'split' && call.arguments[0]?.value === '/';
    });
    if (!split) continue;
    const basename = split.id.name;
    const rekey = fallback.findIndex(n => n.type === 'ExpressionStatement' &&
      n.expression.type === 'AssignmentExpression' && n.expression.operator === '=' &&
      n.expression.left.name === id && n.expression.right.name === basename);
    const initialize = outer.find(n => n.type === 'VariableDeclaration' && n.declarations.some(d =>
      d.init?.type === 'AssignmentExpression' && indexed(d.init.left, cache, id)));
    if (rekey < 0 || !initialize || !fallback.some(n => lookupGuard(n, table, basename))) continue;
    const rest = fallback.slice(rekey + 1);
    if (!rest.length) return 'fallback_before_cache';
    const check = rest[0];
    if (rest.length === 1 && check.type === 'IfStatement' && indexed(check.test, cache, id) &&
        check.consequent.type === 'ReturnStatement' && check.consequent.argument?.type === 'MemberExpression' &&
        indexed(check.consequent.argument.object, cache, id) && key(check.consequent.argument.property) === 'exports') {
      return 'fallback_rechecks_cache';
    }
  }
  return 'unknown';
}

function requireBinding(node, requireName) {
  return node?.type === 'CallExpression' && node.callee.type === 'Identifier' &&
    node.callee.name === requireName && node.arguments.length === 1 &&
    node.arguments[0].type === 'Literal' && typeof node.arguments[0].value === 'string';
}

function fields(node) {
  const suffix = [];
  let base = node;
  while (base?.type === 'MemberExpression') {
    if (base.computed && base.property.type !== 'Literal') return null;
    const name = key(base.property);
    if (name === null) return null;
    suffix.unshift(name);
    base = base.object;
  }
  return base?.type === 'Identifier' ? [base.name, suffix] : null;
}

function inspectTable(call) {
  const loader = loaderKind(call.callee);
  const modules = new Map();
  const duplicates = new Set();
  for (const property of call.arguments[0].properties) {
    const name = key(property.key);
    const pair = property.value;
    if (!name || property.computed || pair?.type !== 'ArrayExpression' ||
        pair.elements[0]?.type !== 'FunctionExpression' ||
        pair.elements[1]?.type !== 'ObjectExpression') {
      throw new Error('Unrecognized module entry in Creator table');
    }
    if (modules.has(name)) duplicates.add(name);
    modules.set(name, pair.elements);
  }
  const uses = new Map();
  let relativeFallbacks = 0;
  for (const [caller, [body, map]] of modules) {
    const requireName = body.params[0]?.name;
    const aliases = new Map();
    const ambiguous = new Set();
    const targets = new Map(map.properties.map(n => [key(n.key), n.value]));
    for (const [request, value] of targets) {
      if (/^\.\.?\//.test(request || '') && value?.type === 'UnaryExpression' && value.operator === 'void') relativeFallbacks++;
    }
    for (const statement of body.body.body) {
      if (statement.type !== 'VariableDeclaration') continue;
      for (const d of statement.declarations) {
        if (d.id.type !== 'Identifier' || !requireBinding(d.init, requireName)) continue;
        const request = d.init.arguments[0].value;
        const mapped = targets.get(request);
        const fallback = /^\.\.?\//.test(request) && !modules.has(request) &&
          (!mapped || (mapped.type === 'UnaryExpression' && mapped.operator === 'void') ||
            (mapped.type === 'Literal' && !mapped.value));
        const target = fallback ? request.split('/').pop() :
          mapped?.type === 'Literal' && typeof mapped.value === 'string' ? mapped.value : request;
        if (modules.has(target)) aliases.set(d.id.name, {caller, target, request, fallback, declaration: d});
      }
    }
    if (!aliases.size) continue;
    // A shadowed or reassigned alias is not proof of a shared field.
    visit(body.body, node => {
      if (node.type === 'VariableDeclarator' && aliases.has(node.id.name) &&
          aliases.get(node.id.name).declaration !== node) ambiguous.add(node.id.name);
      if (node.type === 'AssignmentExpression' && node.left.type === 'Identifier') ambiguous.add(node.left.name);
      if (['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(node.type)) {
        for (const p of node.params) if (p.type === 'Identifier') ambiguous.add(p.name);
      }
      if (node.type === 'CatchClause' && node.param?.type === 'Identifier') ambiguous.add(node.param.name);
    });
    visit(body.body, (node, parent) => {
      if (node.type !== 'MemberExpression') return;
      const chain = fields(node);
      if (!chain || !chain[1].length || ambiguous.has(chain[0])) return;
      const alias = aliases.get(chain[0]);
      if (!alias) return;
      const slot = JSON.stringify([alias.target, chain[1]]);
      if (!uses.has(slot)) uses.set(slot, {module: alias.target, field: chain[1].join('.'), reads: new Map(), writes: new Map()});
      const row = uses.get(slot);
      if (parent?.type === 'AssignmentExpression' && parent.left === node) {
        row.writes.set(caller, {caller, request: alias.request, fallback: alias.fallback});
        if (parent.operator === '=') return;
      }
      row.reads.set(caller, {caller, request: alias.request, fallback: alias.fallback});
    });
  }
  const findings = [...duplicates].map(module => ({kind:'duplicate_compiled_module', module}));
  for (const row of uses.values()) {
    if (loader !== 'fallback_before_cache') break;
    const pairs = [...row.writes.values()].flatMap(writer => [...row.reads.values()]
      .filter(reader => writer.caller !== reader.caller && (writer.fallback || reader.fallback))
      .map(reader => ({writer, reader})));
    if (pairs.length) findings.push({kind:'shared_field_cache_split', module:row.module, field:row.field, pairs});
  }
  return {loader, modules:modules.size, relative_fallbacks:relativeFallbacks, findings};
}

function inspect(source) {
  const ast = acorn.parse(source, {ecmaVersion:'latest', sourceType:'script', allowHashBang:true});
  const tables = [];
  for (const statement of ast.body) {
    if (statement.type !== 'ExpressionStatement') continue;
    const node = statement.expression;
    if (node.type !== 'AssignmentExpression' || node.left.type !== 'MemberExpression' ||
        key(node.left.property) !== '__require' || node.left.object.name !== 'window') continue;
    const call = node.right;
    if (call.type !== 'CallExpression' || call.arguments[0]?.type !== 'ObjectExpression') {
      throw new Error('Unrecognized Creator module table shape');
    }
    tables.push(inspectTable(call));
  }
  return tables;
}

if (require.main === module) {
  try {
    const input = require('fs').readFileSync(0, 'utf8');
    process.stdout.write(JSON.stringify(inspect(input)));
  } catch (error) {
    process.stderr.write(String(error));
    process.exitCode = 2;
  }
}
module.exports = {inspect};
