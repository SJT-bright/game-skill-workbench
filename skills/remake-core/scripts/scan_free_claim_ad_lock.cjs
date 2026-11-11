'use strict';

// Read-only AST check for an optional ad and a free button sharing a guarded handler.
// The runtime cases still verify navigation, storage and callbacks for other structures.
const fs = require('node:fs');
const acorn = require('./vendor/acorn.cjs');
const AD_METHODS = new Set([
  'showVideoAd', 'showRewardedAd', 'showRewardedVideo', 'showRewardVideo',
  'showRewardAd', 'playRewardedVideo', 'watchRewardedVideo', 'runAd',
]);

function children(node) {
  const out = [];
  for (const value of Object.values(node)) {
    if (value && typeof value.type === 'string') out.push(value);
    else if (Array.isArray(value)) {
      for (const child of value) if (child && typeof child.type === 'string') out.push(child);
    }
  }
  return out;
}

function visit(node, callback) {
  callback(node);
  for (const child of children(node)) visit(child, callback);
}

function member(node) {
  if (!node || node.type !== 'MemberExpression') return null;
  return node.computed ? (node.property.type === 'Literal' ? node.property.value : null) : node.property.name;
}

function constant(node) {
  if (!node) return undefined;
  if (node.type === 'Literal') return node.value;
  if (node.type === 'UnaryExpression' && node.operator === '!') {
    const value = constant(node.argument);
    if (value !== undefined) return !value;
  }
  return undefined;
}

function last(node) {
  return node && node.type === 'SequenceExpression' ? last(node.expressions[node.expressions.length - 1]) : node;
}

function selector(node, params) {
  node = last(node);
  if (!node || node.type !== 'BinaryExpression' || !['===', '=='].includes(node.operator)) return null;
  for (const [key, value] of [[node.left, node.right], [node.right, node.left]]) {
    if (key.type === 'Identifier' && params.includes(key.name) && constant(value) !== undefined) {
      return {index: params.indexOf(key.name), value: constant(value)};
    }
  }
  return null;
}

function immediateReturn(node) {
  if (node.type === 'ReturnStatement') return true;
  return node.type === 'BlockStatement' && node.body.length === 1 && node.body[0].type === 'ReturnStatement';
}

function returnsAtEnd(node) {
  if (node.type === 'ReturnStatement') return true;
  return node.type === 'BlockStatement' && node.body.length > 0 && node.body[node.body.length - 1].type === 'ReturnStatement';
}

function scan(source, file = '<input>') {
  const options = {ecmaVersion: 'latest', sourceType: 'script', locations: true, allowReturnOutsideFunction: true};
  let ast;
  try { ast = acorn.parse(source, options); }
  catch (_) { ast = acorn.parse(source, {...options, sourceType: 'module'}); }
  const parents = new Map(), functions = [], bindings = new Map(), registrations = [];
  visit(ast, node => {
    for (const child of children(node)) parents.set(child, node);
    if (['FunctionExpression', 'FunctionDeclaration', 'ArrowFunctionExpression'].includes(node.type)) functions.push(node);
    if (node.type !== 'CallExpression') return;
    if (member(node.callee) === 'push' && member(node.callee.object) === '_RF' && typeof constant(node.arguments[2]) === 'string') {
      registrations.push({start: node.start, name: constant(node.arguments[2])});
    }
    if (member(node.callee) !== 'setButtonClickEvents' || node.arguments.length < 4 || node.arguments[0].type !== 'ThisExpression') return;
    const handler = constant(node.arguments[2]), value = constant(node.arguments[3]);
    if (typeof handler !== 'string' || value === undefined) return;
    if (!bindings.has(handler)) bindings.set(handler, []);
    bindings.get(handler).push({start: node.start, value, node});
  });
  registrations.sort((a, b) => a.start - b.start);
  const moduleAt = offset => {
    let name = file;
    for (const registration of registrations) {
      if (registration.start > offset) break;
      name = registration.name;
    }
    return name;
  };
  const ownerOf = fn => {
    const parent = parents.get(fn);
    if (parent?.type === 'AssignmentExpression' && parent.left.type === 'MemberExpression') {
      return source.slice(parent.left.object.start, parent.left.object.end);
    }
    if (parent && ['Property', 'MethodDefinition'].includes(parent.type)) {
      return String(parents.get(parent).start);
    }
    return null;
  };
  const bindingOwner = binding => {
    for (let node = parents.get(binding); node; node = parents.get(node)) {
      if (['FunctionExpression', 'FunctionDeclaration', 'ArrowFunctionExpression'].includes(node.type)) return ownerOf(node);
    }
    return null;
  };
  const findings = [];
  for (const fn of functions) {
    const parent = parents.get(fn);
    const method = parent.type === 'AssignmentExpression' ? member(parent.left) :
      ['Property', 'MethodDefinition'].includes(parent.type) ? (parent.key.name || constant(parent.key)) : null;
    if (!method || !bindings.has(method) || fn.body.type !== 'BlockStatement') continue;
    const owner = ownerOf(fn);
    const bound = bindings.get(method).filter(row => moduleAt(row.start) === moduleAt(fn.start) && owner !== null && bindingOwner(row.node) === owner);
    if (new Set(bound.map(row => row.value)).size < 2) continue;
    const aliases = new Set();
    const ownVisit = node => {
      if (node !== fn && ['FunctionExpression', 'FunctionDeclaration', 'ArrowFunctionExpression'].includes(node.type)) return;
      if (node.type === 'VariableDeclarator' && node.id.type === 'Identifier' && node.init?.type === 'ThisExpression') aliases.add(node.id.name);
      for (const child of children(node)) ownVisit(child);
    };
    ownVisit(fn);
    const isThis = node => node && (node.type === 'ThisExpression' || (node.type === 'Identifier' && aliases.has(node.name)));
    const flag = node => node?.type === 'MemberExpression' && isThis(node.object) ? member(node) : null;
    const params = fn.params.map(param => param.type === 'Identifier' ? param.name : param.left?.name);
    // Confirm the non-ad branch selects an existing base collection while the
    // alternative extends that same collection. Other handlers need runtime review.
    const reference = node => {
      if (node?.type === 'CallExpression' && member(node.callee) === 'slice' && !node.arguments.length) return reference(node.callee.object);
      if (isThis(node)) return 'this';
      if (node?.type === 'Identifier') return node.name;
      if (node?.type === 'MemberExpression' && member(node) !== null) {
        const object = reference(node.object);
        return object === null ? null : object + '.' + member(node);
      }
      return null;
    };
    const extendsBase = (base, bonus) => {
      if (bonus?.type !== 'CallExpression' || member(bonus.callee) !== 'concat') return false;
      const key = reference(base);
      return key !== null && [bonus.callee.object, ...bonus.arguments].some(value => reference(value) === key);
    };
    const rewardChoices = [];
    visit(fn.body, node => {
      if (node.type !== 'ConditionalExpression') return;
      const choice = selector(node.test, params);
      if (choice && (extendsBase(node.consequent, node.alternate) || extendsBase(node.alternate, node.consequent))) {
        rewardChoices.push({choice, node});
      }
    });
    const calls = [];
    visit(fn.body, node => { if (node.type === 'CallExpression' && AD_METHODS.has(member(node.callee))) calls.push(node); });
    for (const ad of calls) {
      let branch = parents.get(ad);
      while (branch && branch !== fn) {
        if (branch.type === 'IfStatement' && selector(branch.test, params)) break;
        branch = parents.get(branch);
      }
      if (!branch || branch === fn || !(ad.start >= branch.consequent.start && ad.end <= branch.consequent.end)) continue;
      const choice = selector(branch.test, params);
      if (choice.index !== params.length - 1) continue;
      if (!bound.some(row => row.value === choice.value) || !bound.some(row => row.value !== choice.value)) continue;
      const rewards = rewardChoices.filter(row => row.choice.index === choice.index && row.choice.value !== choice.value &&
        bound.some(binding => binding.value === row.choice.value) &&
        !(row.node.start >= branch.consequent.start && row.node.end <= branch.consequent.end));
      if (!rewards.length) continue;
      let reenters = false;
      visit(ad, node => {
        if (node.type === 'CallExpression' && member(node.callee) === method && isThis(node.callee.object)) {
          const value = constant(node.arguments[choice.index]);
          if (value !== undefined && value !== choice.value) reenters = true;
        }
      });
      if (!reenters) continue;
      const locks = new Set();
      visit(branch.consequent, node => {
        if (node.type === 'AssignmentExpression' && node.operator === '=' && node.start < ad.start && constant(node.right) === true && flag(node.left)) locks.add(flag(node.left));
      });
      for (const lock of locks) {
        let guard = null;
        for (let node = parents.get(branch); node && node !== fn; node = parents.get(node)) {
          const test = node.type === 'IfStatement' ? last(node.test) : null;
          if (test?.type === 'UnaryExpression' && test.operator === '!' && flag(test.argument) === lock &&
              parents.get(node) === fn.body && branch.start >= node.consequent.start && branch.end <= node.consequent.end &&
              rewards.some(row => row.node.start >= node.consequent.start && row.node.end <= node.consequent.end)) guard = node;
        }
        for (let node = branch; parents.has(node) && parents.get(node) !== fn; node = parents.get(node)) {
          const block = parents.get(node);
          if (block.type !== 'BlockStatement') continue;
          for (const prior of block.body) {
            if (prior.start >= node.start) break;
            if (block === fn.body && prior.type === 'IfStatement' && flag(last(prior.test)) === lock &&
                immediateReturn(prior.consequent) && rewards.some(row => row.node.start > prior.end)) guard = prior;
          }
        }
        const otherChoices = [...new Set(bound.map(row => row.value))].filter(value => value !== choice.value);
        const alreadyHandled = new Set();
        if (guard) {
          for (let node = guard; parents.has(node) && parents.get(node) !== fn; node = parents.get(node)) {
            const block = parents.get(node);
            if (block.type !== 'BlockStatement') continue;
            for (const prior of block.body) {
              if (prior.start >= node.start) break;
              const match = prior.type === 'IfStatement' ? selector(prior.test, params) : null;
              if (match && match.index === choice.index && returnsAtEnd(prior.consequent)) alreadyHandled.add(match.value);
            }
          }
        }
        const blockedChoices = otherChoices.filter(value => !alreadyHandled.has(value));
        let lockReset = false;
        if (guard) visit(fn.body, node => {
          const inGuardTest = node.start >= guard.test.start && node.end <= guard.test.end;
          if (node.start >= guard.start && !inGuardTest) return;
          if (node.type === 'AssignmentExpression' && flag(node.left) === lock && constant(node.right) === false) lockReset = true;
          if (node.type === 'CallExpression' && node.callee.type === 'MemberExpression' && isThis(node.callee.object)) lockReset = true;
        });
        if (guard && !lockReset && blockedChoices.length) findings.push({file, module: moduleAt(fn.start), handler: method, lock, line: guard.loc.start.line,
          ad_choice: choice.value, other_button_choices: blockedChoices,
          reason: 'An unconditional ad-busy guard also blocks the non-ad button bound to this reward handler.'});
      }
    }
  }
  return findings;
}

module.exports = {scan};
if (require.main === module) {
  if (process.argv.includes('--help')) {
    console.log('Usage: node scan_free_claim_ad_lock.cjs < input.json\nInput is {files:[{file,code}]}. Read-only structural check.');
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
      const findings = input.files.flatMap(row => scan(row.code, row.file));
      console.log(JSON.stringify({status: findings.length ? 'risk_detected' : 'checked', checked: input.files.length, findings,
        requires_runtime_verification: findings.length > 0,
        boundary: 'Checks the supported shared-handler structure only. No findings do not prove runtime recovery.'}));
    } catch (error) {
      const reason = phase === 'json' ? 'invalid JSON input: ' + error.message :
        phase === 'javascript' ? 'JavaScript parse failed: ' + error.message : error.message;
      console.log(JSON.stringify({status: 'not_run', checked: 0, reason}));
      process.exitCode = 2;
    }
  }
}
