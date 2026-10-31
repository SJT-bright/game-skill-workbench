'use strict';
// node test_asset_load_guard.cjs - behaviour of remake-core/assets/loading-recovery-examples/asset-load-guard.js
// with a fake clock (no engine, no browser). Exit 1 on any failure.
const path = require('path');
const assert = require('assert');
const GUARD = path.join(__dirname, '..', 'assets', 'loading-recovery-examples', 'asset-load-guard.js');

function harness() {
  let now = 0;
  const timers = [];
  const realNow = Date.now, realSetTimeout = global.setTimeout;
  Date.now = () => now;
  global.setTimeout = (fn, ms) => { timers.push({at: now + (ms || 0), fn}); return timers.length; };
  delete require.cache[require.resolve(GUARD)];
  const install = require(GUARD);
  const registered = {};
  const downloader = {register(type, handler) { registered[type] = handler; }, download() {}, downloadFile() {}};
  const engine = {assetManager: {downloader, parser: {register() {}}}};
  const root = {};
  const api = install(root, engine, true);
  const calls = [];
  downloader.register('.png', function raw(url, opts, cb) { calls.push(cb); return {abort() {}}; });
  function load() {
    const results = [];
    registered['.png']('a.png', {}, (err, value) => results.push({err, value, at: now}));
    return results;
  }
  function advance(ms, step) {
    const end = now + ms;
    while (now < end) {
      now = Math.min(end, now + (step || 100));
      timers.filter(t => t.at <= now && !t.done).forEach(t => { t.done = true; t.fn(); });
      api.update();
    }
  }
  function restore() { Date.now = realNow; global.setTimeout = realSetTimeout; }
  return {api, calls, load, advance, restore, get now() { return now; }};
}

const cases = {
  'second request after 10 s, first good answer wins'() {
    const h = harness();
    const r = h.load();
    h.advance(9900);
    assert.strictEqual(h.calls.length, 1, 'no second request before 10 s');
    h.advance(200);
    assert.strictEqual(h.calls.length, 2, 'second request at 10 s');
    h.calls[1](null, 'img');
    assert.deepStrictEqual(r.map(x => x.value), ['img']);
    h.calls[0](null, 'late');               // the first request answers late: ignored
    assert.strictEqual(r.length, 1);
    h.restore();
  },
  'fails only after 30 s of foreground silence'() {
    const h = harness();
    const r = h.load();
    h.advance(29800);
    assert.strictEqual(r.length, 0, 'still waiting before 30 s');
    h.advance(400);
    assert.strictEqual(r.length, 1);
    assert.ok(r[0].err instanceof Error, 'fails with an error');
    h.calls[1](null, 'late');               // an answer after the failure is ignored
    assert.strictEqual(r.length, 1);
    h.restore();
  },
  'background time does not count'() {
    const h = harness();
    const r = h.load();
    h.advance(5000);
    h.api.setBackground(true);
    h.advance(120000);
    h.api.setBackground(false);
    assert.strictEqual(r.length, 0, 'no failure while in the background');
    assert.strictEqual(h.calls.length, 1, 'no second request while in the background');
    h.advance(5100);
    assert.strictEqual(h.calls.length, 2, 'second request after 10 s of foreground time');
    h.restore();
  },
  'one long stall counts at most 1 s'() {
    const h = harness();
    const r = h.load();
    h.advance(25000, 25000);                // one update after a 25 s main-thread stall
    assert.strictEqual(r.length, 0);
    assert.strictEqual(h.calls.length, 1);
    h.restore();
  },
  'an error answer is retried once'() {
    const h = harness();
    const r = h.load();
    h.calls[0](new Error('io'));
    h.advance(600);
    assert.strictEqual(h.calls.length, 2, 'retried after 0.5 s');
    h.calls[1](null, 'img');
    assert.deepStrictEqual(r.map(x => x.value), ['img']);
    h.restore();
  },
  'two error answers fail'() {
    const h = harness();
    const r = h.load();
    h.calls[0](new Error('io'));
    h.advance(600);
    h.calls[1](new Error('io again'));
    assert.strictEqual(r.length, 1);
    assert.ok(r[0].err instanceof Error);
    h.restore();
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(cases)) {
  try { fn(); console.log('ok   ' + name); } catch (e) { failed++; console.log('FAIL ' + name + ': ' + e.message); }
}
console.log(failed ? failed + ' failed' : 'all ' + Object.keys(cases).length + ' passed');
process.exit(failed ? 1 : 0);
