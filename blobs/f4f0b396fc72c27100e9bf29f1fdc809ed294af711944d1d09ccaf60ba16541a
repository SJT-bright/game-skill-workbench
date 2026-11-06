// R4N3 (补查2 第 1 组 1b): engine_adapter.js and ui_dump.js on three fake windows (2.4 shape, 3.x shape, engine not up).
// Run: node test_r4n3_engine_adapter.js   (exit 0 = all pass; seconds, no browser)
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const here = __dirname;
const results = [];
const test = async (name, fn) => {
  try { await fn(); results.push(['ok', name]); } catch (e) { results.push(['FAIL', name + ': ' + (e && e.message)]); }
};
const loadAdapter = () => require(path.join(here, 'engine_adapter.js'));
const block = (text) => { const m = text.match(/\/\/ ENGINE-ADAPTER-BEGIN\n([\s\S]*?)\/\/ ENGINE-ADAPTER-END/); return m && m[1].replace(/^ +/gm, ''); };

class Comp { constructor(p) { Object.assign(this, p || {}); } }
function node24(name, x, y, w, h) {  // 2.4: size on the node, convertToWorldSpaceAR on the node
  return { name, active: true, width: w, height: h, anchorX: 0.5, anchorY: 0.5, children: [], opacity: 255,
    getComponent: () => null, getComponents: () => [],
    convertToWorldSpaceAR: (v) => ({ x: x + v.x, y: y + v.y }) };
}
function win24() {
  const scene = node24('Scene', 0, 0, 0, 0);
  scene.children.push(node24('Play', 100, 200, 40, 20));
  return { cc: { ENGINE_VERSION: '2.4.15', director: { getScene: () => scene }, v2: (x, y) => ({ x, y }) } };
}
function win3x() {  // 3.x: no node.convertToWorldSpaceAR (奔跑吧巨人), the box is on UITransform
  class UITransform extends Comp { convertToWorldSpaceAR(v) { return { x: this.x0 + v.x, y: this.y0 + v.y, z: 0 }; } }
  const mk = (name, x, y, w, h) => {
    const n = { name, active: true, children: [], layer: 1 };
    const ut = new UITransform({ contentSize: { width: w, height: h }, anchorPoint: { x: 0.5, y: 0.5 }, x0: x, y0: y, node: n });
    n.getComponent = (c) => (c === UITransform ? ut : null);
    n.getComponents = () => [ut];
    return n;
  };
  const scene = mk('Scene', 0, 0, 0, 0);
  scene.children.push(mk('Play', 100, 200, 40, 20));
  class Vec3 { constructor(x, y, z) { this.x = x; this.y = y; this.z = z; } }
  return { System: { import: async () => ({}) },
    __later: { ENGINE_VERSION: '3.8.8', UITransform, Vec3, director: { getScene: () => scene } } };
}

(async () => {
  await test('ui_dump.js carries the same adapt() as engine_adapter.js', () => {
    const a = block(fs.readFileSync(path.join(here, 'engine_adapter.js'), 'utf8'));
    const b = block(fs.readFileSync(path.join(here, 'ui_dump.js'), 'utf8'));
    assert.ok(a, 'engine_adapter.js has no ENGINE-ADAPTER block');
    assert.ok(b, 'ui_dump.js has no ENGINE-ADAPTER block');
    assert.strictEqual(b, a);
  });
  await test('2.4 shape: ready, api 2.x, toWorld through the node', () => {
    const r = loadAdapter().adapt(win24());
    assert.strictEqual(r.ready, true); assert.strictEqual(r.api, '2.x');
    const play = r.scene.children[0];
    assert.deepStrictEqual(r.toWorld(play, 0, 0), [100, 200]);
    assert.deepStrictEqual(r.size(play), { w: 40, h: 20, ax: 0.5, ay: 0.5 });
  });
  await test('3.x shape: api 3.x, toWorld through UITransform (no node.convertToWorldSpaceAR)', () => {
    const w = win3x(); w.cc = w.__later;
    const r = loadAdapter().adapt(w);
    assert.strictEqual(r.api, '3.x');
    const play = r.scene.children[0];
    assert.strictEqual(typeof play.convertToWorldSpaceAR, 'undefined');
    assert.deepStrictEqual(r.toWorld(play, 0, 0), [100, 200]);
    assert.strictEqual(r.size(play).w, 40);
  });
  await test('engine not up: ready false + retry, no throw (cc missing, director missing, no scene)', () => {
    const A = loadAdapter();
    for (const w of [{}, { cc: {} }, { cc: { director: { getScene: () => null } } }, { cc: { director: { getScene: () => { throw new Error('boom'); } } } }]) {
      const r = A.adapt(w);
      assert.strictEqual(r.ready, false); assert.strictEqual(r.retry, true);
      assert.ok(/引擎还没起来/.test(r.reason), r.reason);
    }
  });
  await test('waitReady: 3.x engine only reachable through System.import(\'cc\') comes up', async () => {
    const w = win3x();
    w.System.import = async (name) => { assert.strictEqual(name, 'cc'); return w.__later; };
    const r = await loadAdapter().waitReady(w, { timeoutMs: 2000, everyMs: 10 });
    assert.strictEqual(r.ready, true); assert.strictEqual(r.api, '3.x');
  });
  await test('waitReady: gives up with retry false after the timeout', async () => {
    const r = await loadAdapter().waitReady({}, { timeoutMs: 60, everyMs: 10 });
    assert.strictEqual(r.ready, false); assert.strictEqual(r.retry, false);
  });
  const dumpFn = () => { global.window = undefined; return eval(fs.readFileSync(path.join(here, 'ui_dump.js'), 'utf8')); };
  await test('ui_dump.js: engine not up -> error 引擎还没起来 + retry, no throw', () => {
    global.window = {}; global.document = undefined;
    const fn = eval(fs.readFileSync(path.join(here, 'ui_dump.js'), 'utf8'));
    const out = fn({});
    assert.ok(out && /引擎还没起来/.test(out.error), JSON.stringify(out));
    assert.strictEqual(out.retry, true);
  });
  void dumpFn;
  for (const [s, n] of results) console.log(s + '  ' + n);
  const bad = results.filter((r) => r[0] !== 'ok').length;
  console.log(bad ? `FAILED ${bad} of ${results.length}` : `OK ${results.length}`);
  process.exit(bad ? 1 : 0);
})();
