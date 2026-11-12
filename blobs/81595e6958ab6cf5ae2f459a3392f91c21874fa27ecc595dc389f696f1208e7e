// Executes the REAL suite bodies with offline G/L/P observations. No browser,
// game, runtime host, project or generated package is opened by these tests.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const source = Object.fromEntries(await Promise.all(['ad_outcome', 'save_restart'].map(async (name) => [name,
  await fs.readFile(new URL('./runtime_regression/suites/' + name + '.mjs', import.meta.url), 'utf8')])));

function adAdapter() {
  return {
    ad_entries: ['skin', 'homegift', 'level'].map((id) => ({ id, button: id,
      states: [{ name: 'ready', actions: [{ enter: id }] }] })),
    ad_outcome: { entries: Object.fromEntries(['skin', 'homegift', 'level'].map((id) => [id, { reward_js: 'reward:' + id }])) },
  };
}

function saveAdapter({ independent = true, requires = {} } = {}) {
  return { save_restart: { steps: ['skin', 'homegift', 'level'].map((name) => ({ name,
    kind: name === 'skin' ? 'buy' : name === 'level' ? 'level' : 'claim',
    actions: [{ earn: name }], read_js: 'read:' + name,
    ...(independent ? { requires: requires[name] || [] } : {}),
  })) } };
}

async function run(name, adapter, options = {}) {
  const calls = [], evidence = {}, values = {}, rewards = {};
  let clock = 0, mode = 'cancel', button = null;
  const C = { policy: 'new', suite: name, adapter, evidenceDir: '/offline-fixture', facts: { rewarded_ads: true },
    ...(Object.hasOwn(options, 'selection') ? { selection: options.selection } : {}),
    ...(options.config || {}) };
  const out = { cases: [], warnings: [], evidence: {},
    add(id, passed, detail) { this.cases.push({ id, passed: passed === true, detail }); },
    warn(message) { this.warnings.push(message); } };
  const page = {
    async evaluate(fn) {
      const text = fn.toString();
      if (text.includes('__gateLog')) return [];
      if (text.includes('__storeDump')) return Object.keys(values).length;
      return clock;
    },
    async goto(url) {
      calls.push(['reload', url]);
      if (options.lose) values[options.lose] = 0;
    },
  };
  const L = { C, A: adapter,
    async suite(fn) { await fn({ out, page }); },
    evidence(file, value) { evidence[file] = structuredClone(value); return '/offline-fixture/' + file; },
    url(query) { return 'offline:' + query; }, async keepFrames() {},
  };
  const P = {
    async sleep(ms) { clock += ms; },
    async priorAdEntries() { return options.prior === undefined ? [] : options.prior; },
    async enterLevel() { calls.push(['enterLevel']); return { ok: true }; },
    async steps(_page, actions) {
      for (const action of actions) {
        if (action.enter) calls.push(['enter', action.enter]);
        if (action.earn) {
          calls.push(['earn', action.earn]);
          if (options.noEarn !== action.earn) values[action.earn] = (values[action.earn] || 0) + 1;
        }
      }
      return { ok: true, log: [] };
    },
    async js(_page, code) {
      calls.push(['read', code]);
      return code.startsWith('reward:') ? rewards[code.slice(7)] || 0 : values[code.slice(5)] || 0;
    },
    same(a, b) { return JSON.stringify(a) === JSON.stringify(b); },
    truthy(value) { return !!value; },
    async point(_page, target) { button = typeof target === 'string' ? target : 'level'; return { x: 1, y: 1 }; },
    async setAd(_page, value) { mode = value; },
    async snap() { return { scene: 'home', m: {} }; },
    buttonsOf() { return options.homeButtons || []; },
    async hostIdx() { return 0; },
    async hostSince() { return [{ kind: 'ad-show' }, { kind: 'ad-result' }, { kind: 'lifecycle', data: 'show' }]; },
    async dismissModal() { return {}; },
    pickContinue() { return null; },
    async tapReact() { calls.push(['react', button]); return { kind: 'reaction' }; },
    async playable() { return { ok: true }; },
  };
  const G = {
    MIN_FPS: 30,
    async openGame(_page, device, query) {
      calls.push(['fresh', query]);
      for (const key of Object.keys(values)) delete values[key];
      for (const key of Object.keys(rewards)) delete rewards[key];
    },
    async waitHome() { return { ok: true }; },
    async evalJs() { return null; },
    async shot(_page, file) { return file; },
    async nodeCentre() { return { x: 1, y: 1 }; },
    async click() {
      calls.push(['ad', button, mode]);
      if ((mode === 'cancel' && options.cancelReward) || (mode === 'complete' && !options.noReward))
        rewards[button] = (rewards[button] || 0) + 1;
    },
  };
  const emptyDiff = () => ({ add: [], gone: [], moved: [], text: [], sprite: [] });
  const R = { adEntriesProblems() { return []; }, isManualRevive() { return false; },
    snapDiff: emptyDiff, dropPress(diff) { return diff; } };
  globalThis.CFG = C; globalThis.__runtimeUnitMock = { L, G, P, R };
  let code = source[name].replace('const L = await import(globalThis.CFG.lib);', 'const L = globalThis.__runtimeUnitMock.L;');
  for (const [file, key] of [['gates.mjs', 'G'], ['phone.mjs', 'P'], ['layout_rules.mjs', 'R']])
    code = code.replace('const ' + key + " = await import(new URL('" + file + "', globalThis.CFG.lib).href);", 'const ' + key + ' = globalThis.__runtimeUnitMock.' + key + ';');
  class FixtureDate extends Date { static now() { return ++clock; } }
  try { await new AsyncFunction('Date', code)(FixtureDate); }
  finally { delete globalThis.CFG; delete globalThis.__runtimeUnitMock; }
  return { out, calls, evidence };
}

const actions = (result, name) => result.calls.filter((call) => call[0] === name);
const passed = (result) => result.out.cases.length > 0 && result.out.cases.every((row) => row.passed);

test('ad: skin-only retains full catalog and executes neither homegift nor level', async () => {
  const result = await run('ad_outcome', adAdapter(), { selection: ['skin/ready'] });
  assert.equal(passed(result), true);
  assert.deepEqual(actions(result, 'enter'), [['enter', 'skin']]);
  assert.deepEqual(actions(result, 'ad').map((row) => row.slice(1)), [['skin', 'cancel'], ['skin', 'complete']]);
  assert.deepEqual(result.evidence['ad_outcome.json'].catalog, ['skin/ready', 'homegift/ready', 'level/ready', '@discovered']);
});

test('ad: each selected atomic unit contains both original cancel and completion cases', async () => {
  const result = await run('ad_outcome', adAdapter(), { selection: ['skin/ready'] });
  assert.deepEqual(result.out.units['skin/ready'].cases.map((row) => row.id), ['skin/ready/cancel', 'skin/ready/complete']);
  assert.equal(result.out.units['skin/ready'].passed, true);
});

test('ad: a cancelled video that grants a reward still fails the original assertion', async () => {
  const result = await run('ad_outcome', adAdapter(), { selection: ['skin/ready'], cancelReward: true });
  assert.equal(result.out.units['skin/ready'].passed, false);
  assert.match(result.out.cases.find((row) => !row.passed).detail, /reward was given anyway/);
});

test('ad: a completed video with no reward still fails the original assertion', async () => {
  const result = await run('ad_outcome', adAdapter(), { selection: ['skin/ready'], noReward: true });
  assert.equal(result.out.units['skin/ready'].passed, false);
  assert.match(result.out.cases.find((row) => !row.passed).detail, /reward did not arrive/);
});

for (const selection of [[], ['unknown'], ['skin/ready', 'skin/ready'], ['skin/ready/cancel']]) {
  test('ad: invalid selection ' + JSON.stringify(selection) + ' takes zero actions', async () => {
    const result = await run('ad_outcome', adAdapter(), { selection });
    assert.equal(passed(result), false); assert.deepEqual(result.calls, []);
  });
}

test('ad: discovered directory executes only discovered entries and retains static catalog', async () => {
  const adapter = adAdapter();
  adapter.ad_outcome.entries['menu/dynamic'] = { reward_js: 'reward:menu/dynamic' };
  const result = await run('ad_outcome', adapter, { selection: ['@discovered'], prior: [{ taps: ['menu/dynamic'], sig: 'dynamic button' }] });
  assert.equal(passed(result), true);
  assert.deepEqual(actions(result, 'ad').map((row) => row[1]), ['menu/dynamic', 'menu/dynamic']);
  assert.equal(result.out.units['@discovered'].passed, true);
  assert.equal(result.evidence['ad_outcome.json'].entries.length, 4);
});

test('ad: discovered entries are never executed by a static-only selection', async () => {
  const result = await run('ad_outcome', adAdapter(), { selection: ['skin/ready'], prior: [{ taps: ['menu/dynamic'], sig: 'dynamic' }] });
  assert.deepEqual(actions(result, 'ad').map((row) => row[1]), ['skin', 'skin']);
});

test('ad: full selection preserves every declared entry with its own fresh journey', async () => {
  const result = await run('ad_outcome', adAdapter());
  assert.equal(passed(result), true);
  assert.equal(actions(result, 'fresh').length, 3);
  assert.deepEqual(Object.keys(result.out.units), ['skin/ready', 'homegift/ready', 'level/ready', '@discovered']);
});

test('ad: legacy policy without ad_outcome keeps its original warning without running entries', async () => {
  const adapter = adAdapter(); delete adapter.ad_outcome;
  const result = await run('ad_outcome', adapter, { config: { policy: 'legacy' } });
  assert.equal(passed(result), true);
  assert.ok(Object.values(result.out.units).every((unit) => unit.passed));
  assert.deepEqual(result.calls, []);
  assert.match(result.out.warnings.join(' '), /legacy game: warning/);
});

test('save: skin-only is fresh -> skin action -> reload and retains full step catalog', async () => {
  const result = await run('save_restart', saveAdapter(), { selection: ['step/skin'] });
  assert.equal(result.out.units['step/skin'].passed, true);
  assert.deepEqual(actions(result, 'earn'), [['earn', 'skin']]);
  assert.equal(actions(result, 'fresh').length, 1); assert.equal(actions(result, 'reload').length, 1);
  assert.deepEqual(result.evidence['save-restart-units.json'].catalog, ['@kinds', 'step/skin', 'step/homegift', 'step/level']);
  const report = result.evidence['step-skin-save_restart.json'];
  assert.equal(report.steps[0].after_restart, report.steps[0].after);
});

test('save: an explicitly declared prerequisite closure runs in dependency order and is fully read back', async () => {
  const result = await run('save_restart', saveAdapter({ requires: { skin: ['homegift'] } }), { selection: ['step/skin'] });
  assert.equal(passed(result), true);
  assert.deepEqual(actions(result, 'earn'), [['earn', 'homegift'], ['earn', 'skin']]);
  const report = result.evidence['step-skin-save_restart.json'];
  assert.deepEqual(report.steps.map((row) => row.name), ['homegift', 'skin']);
  assert.ok(report.steps.every((row) => row.after === row.after_restart));
});

test('save: each selected independent step gets a separate fresh save and reload', async () => {
  const result = await run('save_restart', saveAdapter(), { selection: ['step/skin', 'step/homegift'] });
  assert.equal(passed(result), true);
  assert.equal(actions(result, 'fresh').length, 2); assert.equal(actions(result, 'reload').length, 2);
  assert.deepEqual(actions(result, 'earn'), [['earn', 'skin'], ['earn', 'homegift']]);
});

for (const selection of [[], ['unknown'], ['step/skin', 'step/skin']]) {
  test('save: invalid selection ' + JSON.stringify(selection) + ' takes zero actions', async () => {
    const result = await run('save_restart', saveAdapter(), { selection });
    assert.equal(passed(result), false); assert.deepEqual(result.calls, []);
  });
}

test('save: lost state after reload still fails the original readback assertion', async () => {
  const result = await run('save_restart', saveAdapter(), { selection: ['step/skin'], lose: 'skin' });
  assert.equal(result.out.units['step/skin'].passed, false);
  assert.match(result.out.cases.find((row) => !row.passed).detail, /lost after closing and reopening/);
});

test('save: unchanged earning still fails and its comparison replays only the selected closure', async () => {
  const result = await run('save_restart', saveAdapter(), { selection: ['step/skin'], noEarn: 'skin' });
  assert.equal(result.out.units['step/skin'].passed, false);
  assert.match(result.out.cases.find((row) => !row.passed).detail, /changed nothing/);
  assert.ok(actions(result, 'earn').every((row) => row[1] === 'skin'));
});

test('save: kinds unit checks the full declared catalog without earning anything', async () => {
  const result = await run('save_restart', saveAdapter(), { selection: ['@kinds'],
    homeButtons: [{ path: 'home/shop', sig: 'Shop' }, { path: 'home/gift', sig: 'Gift' }] });
  assert.equal(result.out.units['@kinds'].passed, true); assert.deepEqual(actions(result, 'earn'), []);
  assert.equal(result.evidence['save-restart-kinds.json'].steps.length, 3);
});

test('save: missing kind cannot be hidden by selecting only a different step', async () => {
  const adapter = saveAdapter(); adapter.save_restart.steps = adapter.save_restart.steps.filter((row) => row.kind !== 'claim');
  const result = await run('save_restart', adapter, { selection: ['@kinds'], homeButtons: [{ path: 'home/gift', sig: 'Gift' }] });
  assert.equal(result.out.units['@kinds'].passed, false);
  assert.match(result.out.cases.find((row) => !row.passed).detail, /kind "claim"/);
  assert.deepEqual(actions(result, 'earn'), []);
});

test('save: legacy steps without requires keep the original cumulative suite journey', async () => {
  const result = await run('save_restart', saveAdapter({ independent: false }), { selection: ['@suite'] });
  assert.equal(passed(result), true);
  assert.deepEqual(actions(result, 'earn'), [['earn', 'skin'], ['earn', 'homegift'], ['earn', 'level']]);
  assert.equal(actions(result, 'fresh').length, 1); assert.equal(actions(result, 'reload').length, 1);
  assert.equal(result.evidence['save_restart.json'].steps.length, 3);
});

test('save: partially declared prerequisites cannot silently use cumulative execution', async () => {
  const adapter = saveAdapter(); delete adapter.save_restart.steps[1].requires;
  const result = await run('save_restart', adapter, { selection: ['step/skin'] });
  assert.equal(passed(result), false); assert.deepEqual(result.calls, []);
});

test('save: prerequisite cycles fail before any action', async () => {
  const result = await run('save_restart', saveAdapter({ requires: { skin: ['homegift'], homegift: ['skin'] } }), { selection: ['step/skin'] });
  assert.equal(passed(result), false); assert.deepEqual(result.calls, []);
});
