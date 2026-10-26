'use strict';
// Tokenize JS/TS source without executing it. Strings are event names only at
// actual registration sites; comments, regexes and documentation are not code.
const fs = require('fs');
const acorn = require('./vendor/acorn.cjs');
const starts = new Set(['TOUCH_START', 'touchstart', 'touch-start', 'pointerdown', 'POINTER_DOWN']);
const nativeStarts = new Set(['onTouchStart', 'onPointerDown']);
const registrations = new Set(['on', 'once', 'addEventListener']);
const ownerNames = new Set(['touchId', 'pointerId']);
const out = (status, reason, extra = {}) => ({schema: 'input_ownership_inventory.v1', status, reason, ...extra});
function analyze(payload) {
const source = payload.source;
try {
  // @ decorators are TS syntax; removing only the marker preserves every
  // position and the runtime expression tokens. No source is run/transpiled.
  const text = source.replace(/@/g, ' ');
  const tokens = [];
  const lexer = acorn.tokenizer(text, {ecmaVersion: 'latest', sourceType: 'module', locations: true});
  for (;;) {
    const t = lexer.getToken();
    if (t.type.label === 'eof') break;
    tokens.push({kind: t.type.label, value: t.value, start: t.start, end: t.end, line: t.loc.start.line});
  }
  const val = i => tokens[i]?.value ?? tokens[i]?.kind;
  const isName = i => tokens[i]?.kind === 'name';
  const pair = new Map(), stack = [];
  for (let i = 0; i < tokens.length; i++) {
    const k = tokens[i].kind;
    if (['(', '[', '{', '${'].includes(k)) stack.push(i);
    else if ([')', ']', '}'].includes(k)) {
      const first = stack.pop(), wanted = {')': '(', ']': '[', '}': '{'}[k];
      if (first === undefined || (tokens[first].kind !== wanted && !(k === '}' && tokens[first].kind === '${'))) {
        return out('unresolved', 'unbalanced source tokens');
      }
      pair.set(first, i); pair.set(i, first);
    }
  }
  if (stack.length) { return out('unresolved', 'unbalanced source tokens'); }
  let syntaxOkay = false;
  try { acorn.parse(text, {ecmaVersion: 'latest', sourceType: 'module', allowReturnOutsideFunction: true}); syntaxOkay = true; }
  catch (_) {
    // Type annotations/decorators are accepted lexically, not claimed parsed JS.
    const ts = payload.extension === '.ts' && (source.includes('@') || tokens.some((t, i) =>
      ['interface', 'type', 'implements', 'declare', 'abstract', 'namespace', 'as', 'satisfies'].includes(t.value) ||
      t.kind === ':' && isName(i - 1)));
    if (!ts) { return out('unresolved', 'source syntax is not supported JS/TS'); }
  }
  // Type-only interfaces/declarations do not access runtime pointer state.
  const ignored = new Set();
  for (let i = 0; i < tokens.length; i++) {
    if (val(i) === 'interface' || val(i) === 'declare' && val(i + 1) === 'class') {
      let open = i + 1;
      while (open < tokens.length && tokens[open].kind !== '{' && tokens[open].kind !== ';') open++;
      const end = pair.get(open);
      if (end !== undefined) for (let j = i; j <= end; j++) ignored.add(j);
    }
  }
  const aliases = new Map();
  function memberName(end) {
    if (isName(end) && ['.', '?.'].includes(tokens[end - 1]?.kind)) return val(end);
    if (tokens[end]?.kind === ']') {
      const open = pair.get(end);
      if (open !== undefined && end === open + 2 && tokens[open + 1].kind === 'string') return val(open + 1);
    }
    return null;
  }
  function expression(a, b) {
    if (a >= b) return null;
    for (let j = a; j < b; j++) if (val(j) === 'as' && !['.', '?.'].includes(tokens[j - 1]?.kind)) { b = j; break; }
    if (tokens[b - 1]?.kind === '!') b--;
    while (tokens[a]?.kind === '(' && pair.get(a) === b - 1) { a++; b--; }
    if (b === a + 1) {
      if (tokens[a].kind === 'string' && starts.has(val(a))) return 'event';
      if (isName(a) && starts.has(val(a))) return 'event';
      if (isName(a)) return aliases.get(val(a)) ?? null;
    }
    if (b === a + 3 && tokens[a].kind === '`' && tokens[a + 1].kind === 'template' &&
        tokens[a + 2].kind === '`' && starts.has(val(a + 1))) return 'event';
    const m = memberName(b - 1);
    if (starts.has(m)) return 'event';
    if (m === 'getID') return 'owner_method';
    if (nativeStarts.has(m)) return 'registration';
    if (registrations.has(m)) return 'event_registration';
    if (tokens[b - 1]?.kind === ')') {
      const open = pair.get(b - 1);
      if (open !== undefined && memberName(open - 1) === 'bind') return expression(a, open - 2);
    }
    return null;
  }
  // Finite aliases: const start=Node.EventType.TOUCH_START; const id=e.getID;
  // and destructured enum/method aliases. Actual registration is still needed.
  for (let pass = 0; pass < 4; pass++) for (let i = 0; i < tokens.length; i++) {
    if (ignored.has(i)) continue;
    if (isName(i) && tokens[i + 1]?.kind === '=') {
      let end = i + 2;
      while (end < tokens.length && ![';', ','].includes(tokens[end].kind)) {
        if (pair.has(end) && pair.get(end) > end) end = pair.get(end);
        end++;
      }
      const kind = expression(i + 2, end);
      if (kind) aliases.set(val(i), kind);
    }
    if (['const', 'let', 'var'].includes(val(i)) && tokens[i + 1]?.kind === '{') {
      const close = pair.get(i + 1);
      if (close === undefined || tokens[close + 1]?.kind !== '=') continue;
      for (let j = i + 2; j < close; j++) if (isName(j)) {
        const name = val(j), alias = tokens[j + 1]?.kind === ':' ? val(j + 2) : name;
        if (starts.has(name)) aliases.set(alias, 'event');
        if (name === 'getID') aliases.set(alias, 'owner_method');
        if (nativeStarts.has(name)) aliases.set(alias, 'registration');
        if (registrations.has(name)) aliases.set(alias, 'event_registration');
      }
    }
  }
  const bindingPositions = new Set(), functionParens = new Set();
  for (let i = 0; i < tokens.length; i++) {
    if (isName(i) && tokens[i + 1]?.kind === '=>') bindingPositions.add(i);
    if (['const', 'let', 'var'].includes(val(i)) && tokens[i + 1]?.kind === '{') {
      const close = pair.get(i + 1);
      if (close !== undefined && tokens[close + 1]?.kind === '=') {
        for (let j = i + 2; j < close; j++) if (isName(j)) bindingPositions.add(j);
      }
    }
    if (val(i) === 'import') {
      let end = i + 1;
      while (end < tokens.length && tokens[end].kind !== ';' && tokens[end].kind !== 'string') end++;
      for (let j = i + 1; j < end; j++) bindingPositions.add(j);
    }
    if (tokens[i].kind !== '(') continue;
    const close = pair.get(i);
    if (close === undefined) continue;
    let next = close + 1;
    if (tokens[next]?.kind === ':') { while (next < tokens.length && !['{', '=>', ';'].includes(tokens[next].kind)) next++; }
    if (!['{', '=>'].includes(tokens[next]?.kind)) continue;
    functionParens.add(i);
    let expecting = true;
    for (let j = i + 1; j < close; j++) {
      if (expecting && isName(j)) { bindingPositions.add(j); expecting = false; }
      if (pair.has(j) && pair.get(j) > j) j = pair.get(j);
      if (tokens[j]?.kind === ',') expecting = true;
    }
  }
  const eventSites = [], ownerSites = [], unknownSites = [];
  let dynamicCode = false, escapedOwner = false;
  for (let i = 0; i < tokens.length; i++) {
    if (ignored.has(i)) continue;
    const t = tokens[i], name = val(i);
    if (['eval', 'Function'].includes(name) && tokens[i + 1]?.kind === '(' &&
        !['.', '?.'].includes(tokens[i - 1]?.kind)) {
      const close = pair.get(i + 1), args = tokens.slice(i + 2, close);
      // Pure literal arithmetic/utility bodies are not hidden input code.
      // Unknown/generated bodies or literal input code cannot attest absence.
      if (args.some(x => !['string', ','].includes(x.kind)) || args.some(x =>
          x.kind === 'string' && /\b(?:getID|touchId|pointerId|TOUCH_START|touchstart|pointerdown|onTouchStart|onPointerDown)\b/.test(x.value))) dynamicCode = true;
    }
    const member = memberName(i);
    if (member === 'getID' && tokens[i + 1]?.kind === '(') ownerSites.push(i);
    if (isName(i) && name === 'getID' && tokens[i + 1]?.kind === '(' && val(i - 1) !== 'function' &&
        !functionParens.has(i + 1)) ownerSites.push(i);
    if (isName(i) && aliases.has(name) && tokens[i + 1]?.kind !== '(' &&
        !['const', 'let', 'var', '.', '?.'].includes(val(i - 1)) && !['=', ':'].includes(tokens[i + 1]?.kind) &&
        !bindingPositions.has(i)) {
      if (aliases.get(name) === 'owner_method') escapedOwner = true;
      if (['registration', 'event_registration'].includes(aliases.get(name))) unknownSites.push(i);
    }

    if (ownerNames.has(member)) ownerSites.push(i);
    if (isName(i) && aliases.get(name) === 'owner_method' && tokens[i + 1]?.kind === '(') ownerSites.push(i);
    if (isName(i) && ownerNames.has(name) && !member && !bindingPositions.has(i) &&
        !['const', 'let', 'var'].includes(val(i - 1)) && tokens[i + 1]?.kind !== ':' &&
        !['.', '?.'].includes(tokens[i - 1]?.kind)) ownerSites.push(i);
    if (['const', 'let', 'var'].includes(name) && tokens[i + 1]?.kind === '{') {
      const close = pair.get(i + 1);
      if (close !== undefined && tokens[close + 1]?.kind === '=' &&
          tokens.slice(i + 2, close).some(x => ownerNames.has(x.value) || x.value === 'getID')) ownerSites.push(i);
    }
    if (t.kind !== '(' || pair.get(i) === undefined) continue;
    const callName = memberName(i - 1) ?? (isName(i - 1) ? val(i - 1) : null);
    if (val(i - 2) === 'function' || functionParens.has(i)) continue;
    if (nativeStarts.has(callName) || isName(i - 1) && aliases.get(val(i - 1)) === 'registration') { eventSites.push(i); continue; }
    const knownRegistration = registrations.has(callName) || isName(i - 1) && aliases.get(callName) === 'event_registration';
    let end = i + 1;
    while (end < pair.get(i) && tokens[end].kind !== ',') {
      if (pair.has(end) && pair.get(end) > end) end = pair.get(end);
      end++;
    }
    const event = expression(i + 1, end);
    if (!knownRegistration) {
      // An indirect registration cannot prove absence just because its method
      // name is computed or hidden behind a wrapper.
      if (tokens[i - 1]?.kind === ']' && memberName(i - 1) === null ||
          event === 'event' && !['log', 'debug', 'info', 'warn', 'error'].includes(callName)) unknownSites.push(i);
      continue;
    }
    if (event === 'event') eventSites.push(i);
    else if (!(end === i + 2 && tokens[i + 1]?.kind === 'string')) unknownSites.push(i);
  }
  const positions = list => [...new Set(list)].map(i => ({line: tokens[i].line, at: tokens[i].start}));
  if (dynamicCode) return out('unresolved', 'dynamic code may hide input ownership', {syntax: syntaxOkay ? 'js' : 'ts_tokens'});
  else if (escapedOwner && (eventSites.length || unknownSites.length)) return out('unresolved', 'contact identity method escaped a direct call');
  else if (ownerSites.length && eventSites.length) return out('owner', 'executable input registration and contact identity/state use', {
    events: positions(eventSites), ownership: positions(ownerSites), syntax: syntaxOkay ? 'js' : 'ts_tokens'});
  else if (ownerSites.length && unknownSites.length) return out('unresolved', 'contact identity/state with unresolved event registration', {
    registrations: positions(unknownSites), ownership: positions(ownerSites), syntax: syntaxOkay ? 'js' : 'ts_tokens'});
  else return out('none', 'no explicit runtime input ownership found', {syntax: syntaxOkay ? 'js' : 'ts_tokens'});
} catch (error) {
  return out('unresolved', 'source tokenization failed: ' + String(error));
}

}
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(Array.isArray(payload.sources) ? payload.sources.map(analyze) : analyze(payload)));
