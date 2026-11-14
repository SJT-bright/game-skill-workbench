'use strict';

// Pure AST check for legacy Cocos 2.x platform flags disabling ordinary node input.
// No game code is executed. This is not a device/runtime or callback-behaviour proof.
const FLAGS = new Set(['CC_WECHATGAME', 'CC_WECHATGAMESUB', 'CC_BYTEDANCEGAME', 'CC_QQPLAY']);
const INIT = new Set(['onLoad', 'start', 'onEnable']);
const UNKNOWN = Symbol('unknown');
const EVENT_NAMES = new Set(['click', 'touchstart', 'touchmove', 'touchend', 'touchcancel',
  'mousedown', 'mousemove', 'mouseup']);
const member = n => n?.type === 'MemberExpression'
  ? (n.computed ? n.property.type === 'Literal' ? n.property.value : null : n.property.name) : null;
const isFunction = n => /^(FunctionExpression|FunctionDeclaration|ArrowFunctionExpression)$/.test(n?.type);

function analyze({nodes, parents, isGlobal = () => true}) {
  const findings = [], unresolved = [];
  function flagOf(n) {
    if (n?.type === 'Identifier' && FLAGS.has(n.name) && isGlobal(n.name, n)) {
      const parent = parents.get(n);
      if (parent?.type === 'MemberExpression' && parent.property === n && !parent.computed) return null;
      return n.name;
    }
    if (n?.type === 'MemberExpression' && FLAGS.has(member(n)) && n.object.type === 'Identifier' &&
        ['window', 'globalThis', 'GameGlobal'].includes(n.object.name) && isGlobal(n.object.name, n)) return member(n);
    return null;
  }
  const classes = nodes.filter(n => n.type === 'CallExpression' && member(n.callee) === 'Class' &&
    n.callee.object?.name === 'cc' && isGlobal('cc', n) && n.arguments[0]?.type === 'ObjectExpression');
  for (const call of classes) {
    const methods = new Map(call.arguments[0].properties.filter(p => isFunction(p.value))
      .map(p => [p.key.name || p.key.value, p.value]));
    for (const [lifecycle, fn] of methods) {
      if (!INIT.has(lifecycle)) continue;
      const selected = new Set(), visited = new Set();
      let opaqueImmediate = false;
      function collect(n) {
        if (!n || typeof n !== 'object' || visited.has(n)) return;
        visited.add(n);
        const flag = flagOf(n);
        if (flag) selected.add(flag);
        if (n.type === 'CallExpression' && n.callee.object?.type === 'ThisExpression' && methods.has(member(n.callee))) {
          collect(methods.get(member(n.callee)).body);
        }
        // Only direct arrow IIFEs inherit component `this`. Other immediate
        // function contexts are review-only; deferred event callbacks are not run.
        if (n.type === 'CallExpression' && isFunction(n.callee)) {
          if (n.callee.type !== 'ArrowFunctionExpression') opaqueImmediate = true;
          collect(n.callee.body);
        } else if (n.type === 'CallExpression' && isFunction(n.callee.object) &&
                   ['call', 'apply'].includes(member(n.callee))) {
          opaqueImmediate = true;
          collect(n.callee.object.body);
        }
        if (isFunction(n) && n !== fn) return;
        for (const [key, value] of Object.entries(n)) {
          if (key === 'loc') continue;
          if (Array.isArray(value)) value.forEach(collect);
          else if (value && typeof value.type === 'string') collect(value);
        }
      }
      collect(fn.body);
      const flags = [...selected].sort();
      if (!flags.length) continue;
      const cases = [], sites = new Map();
      const clone = s => ({...s, vars: new Map(s.vars), bound: new Set(s.bound)});
      let limited = opaqueImmediate;
      function bounded(states) {
        if (states.length > 64) { limited = true; return states.slice(0, 64); }
        return states;
      }
      function nodeValue(n, s, env) {
        if (!n) return undefined;
        if (n.type === 'Literal') return n.value;
        if (n.type === 'ThisExpression') return '@this';
        if (n.type === 'Identifier') {
          if (s.vars.has(n.name)) return s.vars.get(n.name);
          if (flagOf(n)) return env[n.name];
          if (n.name === 'undefined' && isGlobal(n.name, n)) return undefined;
          return UNKNOWN;
        }
        if (n.type === 'MemberExpression') {
          if (flagOf(n)) return env[flagOf(n)];
          const name = member(n), base = nodeValue(n.object, s, env);
          if (base === '@this' && name === 'node') return '@node';
          if (base === '@button' && name === 'node') return '@node';
          if (base === '@node' && name === 'active') return s.active;
          const symbols = {CLICK: 'click', TOUCH_START: 'touchstart', TOUCH_MOVE: 'touchmove',
            TOUCH_END: 'touchend', TOUCH_CANCEL: 'touchcancel', MOUSE_DOWN: 'mousedown',
            MOUSE_MOVE: 'mousemove', MOUSE_UP: 'mouseup'};
          if (member(n.object) === 'EventType' && Object.hasOwn(symbols, name)) return symbols[name];
          return UNKNOWN;
        }
        if (n.type === 'UnaryExpression') {
          const v = nodeValue(n.argument, s, env);
          if (v === UNKNOWN) return UNKNOWN;
          if (n.operator === '!') return !v;
          if (n.operator === 'typeof') return typeof v;
          if (n.operator === 'void') return undefined;
        }
        if (n.type === 'BinaryExpression') {
          const a = nodeValue(n.left, s, env), b = nodeValue(n.right, s, env);
          if (a === UNKNOWN || b === UNKNOWN) return UNKNOWN;
          switch (n.operator) {
            case '===': return a === b;
            case '!==': return a !== b;
            case '==': return a == b; // Match source semantics; values are AST literals/booleans only.
            case '!=': return a != b;
          }
        }
        if (n.type === 'LogicalExpression') {
          const a = nodeValue(n.left, s, env);
          if (a === UNKNOWN) return UNKNOWN;
          if (n.operator === '&&') return a ? nodeValue(n.right, s, env) : a;
          if (n.operator === '||') return a ? a : nodeValue(n.right, s, env);
          if (n.operator === '??') return a == null ? nodeValue(n.right, s, env) : a;
        }
        if (n.type === 'ConditionalExpression') {
          const v = nodeValue(n.test, s, env);
          return v === UNKNOWN ? UNKNOWN : nodeValue(v ? n.consequent : n.alternate, s, env);
        }
        if (n.type === 'CallExpression' && member(n.callee) === 'getComponent' &&
            nodeValue(n.callee.object, s, env) === '@node' && member(n.arguments[0]) === 'Button') return '@button';
        return UNKNOWN;
      }
      function expr(n, states, env, stack) {
        if (!n) return states;
        if (n.type === 'SequenceExpression') {
          for (const e of n.expressions) states = expr(e, states, env, stack);
          return states;
        }
        if (n.type === 'LogicalExpression' || n.type === 'ConditionalExpression') {
          const test = n.type === 'LogicalExpression' ? n.left : n.test;
          states = expr(test, states, env, stack);
          return bounded(states.flatMap(s => {
            const v = nodeValue(test, s, env);
            const branch = yes => {
              if (n.type === 'ConditionalExpression') return yes ? n.consequent : n.alternate;
              const executeRight = n.operator === '&&' ? yes : n.operator === '||' ? !yes : v == null;
              return executeRight ? n.right : null;
            };
            if (v !== UNKNOWN) return expr(branch(!!v), [s], env, stack);
            return [...expr(n.type === 'ConditionalExpression' ? n.consequent : n.right,
              [clone(s)], env, stack), ...expr(n.type === 'ConditionalExpression' ? n.alternate : null,
              [clone(s)], env, stack)];
          }));
        }
        if (n.type === 'AssignmentExpression') {
          states = expr(n.right, states, env, stack);
          for (const s of states) {
            const v = n.operator === '=' ? nodeValue(n.right, s, env) : UNKNOWN;
            if (n.left.type === 'Identifier') s.vars.set(n.left.name, v);
            if (member(n.left) === 'active' && nodeValue(n.left.object, s, env) === '@node') s.active = v;
          }
          return states;
        }
        if (n.type !== 'CallExpression') return states;
        // IIFEs/local helpers run now; an event callback passed as an argument does not.
        if (isFunction(n.callee)) {
          // Do not guess function `this`, async scheduling or nested lexical writes.
          if (stack.length > 6 || n.callee.type !== 'ArrowFunctionExpression' || n.callee.async ||
              n.callee.params.length || nodes.some(x => x.start >= n.callee.body.start && x.end <= n.callee.body.end &&
                (x.type === 'VariableDeclaration' || x.type === 'AssignmentExpression' &&
                  !(member(x.left) === 'active' && member(x.left.object) === 'node' && x.left.object.object?.type === 'ThisExpression')))) {
            limited = true; return states;
          }
          return states.flatMap(s => {
            const inner = clone(s), body = n.callee.body;
            const result = body.type === 'BlockStatement' ? block(body, [inner], env, [...stack, '<iife>'])
              : expr(body, [inner], env, [...stack, '<iife>']);
            return result.map(x => ({...x, vars: s.vars, stopped: false}));
          });
        }
        const method = member(n.callee);
        if (n.callee.object?.type === 'ThisExpression' && methods.has(method)) {
          if (stack.includes(method) || stack.length > 6) { limited = true; return states; }
          const helper = methods.get(method);
          return states.flatMap(s => {
            const inner = clone(s);
            inner.vars = new Map();
            helper.params.forEach((p, i) => { if (p.type === 'Identifier') inner.vars.set(p.name, nodeValue(n.arguments[i], s, env)); });
            return block(helper.body, [inner], env, [...stack, method])
              .map(x => ({...x, vars: s.vars, stopped: false}));
          });
        }
        for (const s of states) {
          if (!['on', 'once', 'off'].includes(method) || nodeValue(n.callee.object, s, env) !== '@node') continue;
          const event = nodeValue(n.arguments[0], s, env);
          if (!EVENT_NAMES.has(event)) continue;
          const key = '@node:' + event;
          if (method === 'off' && n.arguments.length > 1) limited = true; // A different handler may remain bound.
          else if (method === 'off') s.bound.delete(key);
          else { s.bound.add(key); if (!sites.has(key)) sites.set(key, n); }
        }
        return states;
      }
      function block(n, states, env, stack) {
        if (!n) return states;
        if (n.type === 'BlockStatement') {
          for (const child of n.body) {
            const done = states.filter(s => s.stopped);
            states = bounded([...done, ...block(child, states.filter(s => !s.stopped), env, stack)]);
          }
          return states;
        }
        if (n.type === 'VariableDeclaration') {
          for (const d of n.declarations) {
            states = expr(d.init, states, env, stack);
            if (d.id.type === 'Identifier') for (const s of states) s.vars.set(d.id.name, nodeValue(d.init, s, env));
          }
          return states;
        }
        if (n.type === 'ExpressionStatement') return expr(n.expression, states, env, stack);
        if (n.type === 'ReturnStatement' || n.type === 'ThrowStatement') {
          return expr(n.argument, states, env, stack).map(s => ({...s, stopped: true}));
        }
        if (n.type === 'IfStatement') {
          states = expr(n.test, states, env, stack);
          return bounded(states.flatMap(s => {
            const test = nodeValue(n.test, s, env);
            if (test !== UNKNOWN) return block(test ? n.consequent : n.alternate, [s], env, stack);
            return [...block(n.consequent, [clone(s)], env, stack), ...block(n.alternate, [clone(s)], env, stack)];
          }));
        }
        if (/^(For|While|DoWhile|Switch|Try|With)/.test(n.type)) limited = true;
        return states;
      }
      for (let bits = 0; bits < 2 ** flags.length; bits++) {
        const env = Object.fromEntries(flags.map((f, i) => [f, !!(bits & (1 << i))]));
        const state = {vars: new Map(fn.params.filter(p => p.type === 'Identifier').map(p => [p.name, UNKNOWN])),
          bound: new Set(), active: true, stopped: false};
        cases.push({flags: env, states: block(fn.body, [state], env, [lifecycle])});
      }
      if (limited) {
        unresolved.push({line: fn.loc.start.line, lifecycle, flags, reason: 'unsupported control flow or bounded analysis limit; inspect actual platform input paths'});
        continue; // Truncated/unsupported paths cannot prove a missing binding or a safe one.
      }
      for (const [key, site] of sites) {
        const present = cases.find(c => c.states.length && c.states.every(s => s.bound.has(key)));
        const missing = cases.find(c => c.states.length && c.states.every(s => s.bound.size === 0) &&
          c.states.some(s => s.active !== false));
        if (!present || !missing) continue;
        // Another init lifecycle may establish input (including through a local
        // helper). Do not turn a method-local gap into a component-wide failure.
        const seen = new Set();
        function otherInput(n) {
          if (!n || typeof n !== 'object' || seen.has(n)) return false;
          seen.add(n);
          if (n.type === 'AssignmentExpression' && ['active', 'interactable', 'enabled'].includes(member(n.left))) return true;
          if (n.type === 'CallExpression') {
            const name = member(n.callee), event = n.arguments[0];
            if (['on', 'once'].includes(name) && (!event || event.type !== 'Literal' || EVENT_NAMES.has(event.value))) return true;
            if (n.callee.object?.type === 'ThisExpression' && methods.has(name) && otherInput(methods.get(name).body)) return true;
          }
          return Object.entries(n).some(([k, v]) => k !== 'loc' && (Array.isArray(v) ? v.some(otherInput)
            : v && typeof v.type === 'string' && otherInput(v)));
        }
        if ([...methods].some(([name, other]) => INIT.has(name) && other !== fn && otherInput(other.body))) {
          unresolved.push({line: site.loc.start.line, lifecycle, flags,
            reason: 'another init lifecycle may establish input or change visibility/interaction; inspect combined component/serialized state'});
          continue;
        }
        findings.push({id: 'platform_input_binding', line: site.loc.start.line, column: site.loc.start.column,
          offset: site.start, lifecycle, event: key.slice('@node:'.length), flags,
          bound_when: present.flags, missing_when: missing.flags,
          reason: 'Legacy platform flag can skip input binding on a node not explicitly hidden in that branch; bind common input on every supported host.'});
      }
    }
  }
  return {schema: 'platform_input_bindings.v1', findings, unresolved,
    boundary: 'Cocos 2.x cc.Class lifecycle/local helper paths, this.node and cc.Button node aliases, boolean legacy flags and simple direct arrow IIFEs only; alternate lifecycle paths are review-only; no device or general dynamic-program proof.'};
}

module.exports = {analyze};
