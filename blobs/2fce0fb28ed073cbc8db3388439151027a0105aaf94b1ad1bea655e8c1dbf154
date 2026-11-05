'use strict';
// node tests/res-loader.test.js  -- parts/ResLoader.js (生成时预防 P12). Fake engine (assetManager + bundles whose answers
// are scripted per path) and a fake clock, so 30 s of loading runs in a few milliseconds.
// Part A, the same 6-case matrix for ResLoader and for the negative control (甜品消除大师 v11 ResMgr, fixture
// res-loader-fixtures/ResMgr_dessert_v11.js): every load must settle in 31 s, retry a transient error, take the answer of
// the 10 s re-request, reject an empty JSON, and leave no unhandled rejection. ResLoader passes 6/6; the fixture must fail
// at least 4 cases and leave unhandled rejections (it did on the real v11: 6/9, 3 unhandled).
// Part B, ResLoader only: strings and hand-made keys throw, the type comes from the key, owner gone = no callback,
// ready() only after real success, background time not counted, Res.sprite placeholder + retry, Res.font fallback.
var assert = require('assert');
var path = require('path');
var Res = require(path.join(__dirname, '..', 'parts', 'ResLoader.js'));
var ResMgrFixture = require(path.join(__dirname, 'res-loader-fixtures', 'ResMgr_dessert_v11.js'));

var unhandled = [];
process.on('unhandledRejection', function (e) { unhandled.push(e); });

function clock() {
  var t = 0, seq = 0, timers = [];
  return {
    now: function () { return t; },
    setTimeout: function (f, ms) { var id = ++seq; timers.push({ id: id, at: t + ms, f: f }); return id; },
    clearTimeout: function (id) { timers = timers.filter(function (x) { return x.id !== id; }); },
    advance: async function (ms) {
      var end = t + ms;
      while (t < end) {
        t = Math.min(end, t + 250);
        var due = timers.filter(function (x) { return x.at <= t; });
        timers = timers.filter(function (x) { return x.at > t; });
        due.forEach(function (x) { x.f(); });
        await flush();
      }
    }
  };
}
function flush() { return new Promise(function (r) { setImmediate(r); }); }

function SpriteFrame() {}
function JsonAsset() {}
function TTFFont() {}
// plan: { bundles: {name: 'ok'|'fail'|'never'}, files: {path: [answer, answer, ...]} }; answer = 'ok'|'fail'|'never'|'empty'
function fakeEngine(plan) {
  var calls = [], made = {};
  function answer(list, i) { return (list && (list[i] || list[list.length - 1])) || 'ok'; }
  function makeBundle(name) {
    var n = {};
    return made[name] = made[name] || {
      name: name,
      load: function (p, Type, cb) {
        if (typeof Type === 'function' && !cb) { cb = Type; Type = undefined; }
        var i = n[p] = (n[p] || 0) + 1;
        calls.push({ path: p, Type: Type, n: i });
        var a = answer(plan.files[p], i - 1);
        if (a === 'never') return;
        setImmediate(function () {
          if (a === 'fail') cb(new Error('net error ' + p));
          else if (a === 'empty') cb(null, { json: {} });
          else cb(null, { path: p, json: { a: 1 } });
        });
      }
    };
  }
  var loaded = {};
  return {
    calls: calls,
    SpriteFrame: SpriteFrame, JsonAsset: JsonAsset, TTFFont: TTFFont,
    game: { EVENT_HIDE: 'hide', EVENT_SHOW: 'show', _h: {}, on: function (e, f) { (this._h[e] = this._h[e] || []).push(f); },
      emit: function (e) { (this._h[e] || []).forEach(function (f) { f(); }); } },
    assetManager: {
      getBundle: function (name) { return loaded[name] || null; },
      loadBundle: function (name, cb) {
        var a = (plan.bundles || {})[name] || 'ok';
        if (a === 'never') return;
        setImmediate(function () {
          if (a === 'fail') cb(new Error('bundle ' + name + ' failed'));
          else { loaded[name] = makeBundle(name); cb(null, loaded[name]); }
        });
      }
    }
  };
}
function key(id, p, type, bundle, extra) {
  var k = { __resKey: 1, id: id, path: p, type: type || 'SpriteFrame', bundle: bundle || 'game' };
  // F2: like a generated ResKeys entry (there the call is literal and uses the global cc; here the test engine).
  k.request = function (cb, cc) { cc.assetManager.getBundle(k.bundle).load(k.path, cc[k.type], cb); };
  Object.keys(extra || {}).forEach(function (x) { k[x] = extra[x]; });
  return Object.freeze(k);
}

// one loader under test: (engine, clock) -> function (bundle, path, type) -> Promise
var subjects = {
  ResLoader: function (cc, c) {
    var r = Res.create({ engine: cc, platform: null, now: c.now, setTimeout: c.setTimeout, clearTimeout: c.clearTimeout });
    return function (b, p, type) { return r.load(key(p.replace(/\W/g, '_'), p, type, b)); };
  },
  'ResMgr 甜品消除大师 v11': function (cc) {
    var m = ResMgrFixture.make(cc.assetManager);
    return function (b, p) { return m.loadRes(b, p); };
  }
};
var cases = [
  ['callback never comes -> settles within 31 s', { files: { 'ui/a': ['never'] } }, 'game', 'ui/a', 'SpriteFrame', 'rejected'],
  ['bundle never answers -> settles within 31 s', { bundles: { game: 'never' }, files: {} }, 'game', 'ui/a', 'SpriteFrame', 'rejected'],
  ['bundle fails -> rejects (not hang, not unhandled)', { bundles: { game: 'fail' }, files: {} }, 'game', 'ui/a', 'SpriteFrame', 'rejected'],
  ['first error, second ok -> resolves', { files: { 'ui/a': ['fail', 'ok'] } }, 'game', 'ui/a', 'SpriteFrame', 'resolved'],
  ['first silent, 10 s re-request answers -> resolves', { files: { 'ui/a': ['never', 'ok'] } }, 'game', 'ui/a', 'SpriteFrame', 'resolved'],
  ['empty JSON -> rejects', { files: { 'cfg/levels': ['empty'] } }, 'game', 'cfg/levels', 'JsonAsset', 'rejected']
];

async function runMatrix(name) {
  var failed = [], before = unhandled.length;
  for (var i = 0; i < cases.length; i++) {
    var c = cases[i], cl = clock(), cc = fakeEngine(c[1]), state = 'pending';
    var p;
    try { p = subjects[name](cc, cl)(c[2], c[3], c[4]); } catch (e) { p = Promise.reject(e); }
    p.then(function () { state = 'resolved'; }, function () { state = 'rejected'; });
    await cl.advance(31000);
    await flush();
    if (state !== c[5]) failed.push(c[0] + ' (got ' + state + ')');
  }
  await flush(); await flush();
  return { failed: failed, unhandled: unhandled.length - before };
}

async function partB() {
  var c = clock(), cc = fakeEngine({ files: { 'ui/b': ['fail', 'fail', 'fail'], 'ui/c': ['never'], 'font/main': ['fail', 'fail'] } });
  var r = Res.create({ engine: cc, platform: null, now: c.now, setTimeout: c.setTimeout, clearTimeout: c.clearTimeout });
  var A = key('ui_a', 'ui/a'), B = key('ui_b', 'ui/b'), C = key('ui_c', 'ui/c'), F = key('font_main', 'font/main', 'TTFFont');
  var name = 'gift';

  // strings, hand-made keys and unknown entries throw at once
  assert.throws(function () { r.load('ui/' + name); }, function (e) { return e.code === 'not_a_key'; }, 'string path throws');
  assert.throws(function () { r.load({ __resKey: 1, id: 'x', path: 'ui/x', type: 'SpriteFrame', bundle: 'game' }); }, /not made by ResKeys/);
  var ResKeys = Object.freeze({ ui_a: A });
  assert.throws(function () { r.load(ResKeys['ui_' + name]); }, /undefined/, 'unknown table entry throws');
  assert.throws(function () { r.sprite({}, 'ui/a'); }, /not_a_key|string/);

  // type comes from the key; ready() only after the real success
  assert.strictEqual(r.ready([A]), false);
  var got = r.load(A);
  await c.advance(2000);
  assert.strictEqual((await got).path, 'ui/a');
  assert.strictEqual(cc.calls[0].Type, SpriteFrame, 'bundle.load got the type from the key');
  assert.strictEqual(r.ready([A]), true);
  assert.strictEqual(r.ready([A, B]), false, 'B never loaded');

  // a failed load: ready stays false, loadAll rejects and names it
  var all = r.loadAll([A, B]), allErr = null;
  all.catch(function (e) { allErr = e; });
  await c.advance(2000);
  assert.ok(allErr && allErr.failed.join() === 'ui_b', 'loadAll names the failed key');
  assert.strictEqual(r.ready([B]), false, 'failed load is never ready');
  assert.strictEqual(r.status(B), 'failed');

  // owner destroyed before the answer -> no callback of that call
  var owner = { isValid: true }, ran = false;
  var c2 = clock(), cc2 = fakeEngine({ files: {} });
  var r2 = Res.create({ engine: cc2, platform: null, now: c2.now, setTimeout: c2.setTimeout, clearTimeout: c2.clearTimeout });
  r2.load(A, { owner: owner }).then(function () { ran = true; }, function () { ran = true; });
  owner.isValid = false;
  await c2.advance(1000);
  assert.strictEqual(ran, false, 'owner gone: callback dropped');
  assert.strictEqual(r2.ready([A]), true, 'the loader itself still finished');

  // background time does not count: hidden 60 s, still pending; 30 s in the foreground -> timeout
  var c3 = clock(), cc3 = fakeEngine({ files: { 'ui/c': ['never'] } }), st = 'pending';
  var r3 = Res.create({ engine: cc3, platform: null, now: c3.now, setTimeout: c3.setTimeout, clearTimeout: c3.clearTimeout });
  r3.load(C).then(function () { st = 'resolved'; }, function (e) { st = e.code; });
  await c3.advance(1000);
  cc3.game.emit('hide');
  await c3.advance(60000);
  assert.strictEqual(st, 'pending', 'background time not counted');
  cc3.game.emit('show');
  await c3.advance(30000);
  assert.strictEqual(st, 'timeout', 'foreground 30 s -> timeout');
  assert.strictEqual(cc3.calls.length, 2, 're-requested once at 10 s foreground');

  // Res.sprite: placeholder at once, never rejects, retry loads again
  var spr = { spriteFrame: null, node: { isValid: true } }, failSeen = null;
  var h = r.sprite(spr, B, { placeholder: A, onFail: function (e) { failSeen = e.code; } });
  await c.advance(2000);
  assert.strictEqual(await h.promise, false, 'sprite resolves false on failure');
  assert.strictEqual(spr.spriteFrame && spr.spriteFrame.path, 'ui/a', 'placeholder shown');
  assert.strictEqual(failSeen, 'load_error');
  var h2 = r.sprite(spr, A);
  await c.advance(2000);
  assert.strictEqual(await h2.promise, true);
  var again = h.retry();
  await c.advance(2000);
  assert.strictEqual(await again, false, 'retry asks again (ui/b fails a third time)');
  assert.ok(cc.calls.filter(function (x) { return x.path === 'ui/b'; }).length >= 3, 'retry re-requested ui/b');

  // Res.font: failure -> fallback, never ready
  var fp = r.font(F);
  await c.advance(2000);
  var fr = await fp;
  assert.strictEqual(fr.fallback, true);
  assert.strictEqual(r.ready([F]), false, 'font fallback is not ready');
  return 9;
}

(async function () {
  var good = await runMatrix('ResLoader');
  var bad = await runMatrix('ResMgr 甜品消除大师 v11');
  assert.deepStrictEqual(good.failed, [], 'ResLoader matrix: ' + good.failed.join('; '));
  assert.strictEqual(good.unhandled, 0, 'ResLoader leaves no unhandled rejection');
  assert.ok(bad.failed.length >= 4, 'negative control must fail >= 4 cases, failed ' + bad.failed.length + ': ' + bad.failed.join('; '));
  assert.ok(bad.unhandled >= 1, 'negative control must leave an unhandled rejection, got ' + bad.unhandled);
  var groups = await partB();
  // the part carries no game names
  var code = require('fs').readFileSync(path.join(__dirname, '..', 'parts', 'ResLoader.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  ['ResMgr', 'Dessert', 'gift_box'].forEach(function (n) { assert.ok(code.indexOf(n) < 0, n); });
  console.log('res-loader: matrix ResLoader 6/6, unhandled 0; negative control ResMgr v11 failed ' + bad.failed.length +
    '/6, unhandled ' + bad.unhandled + ' (' + bad.failed.join('; ') + '); part B ' + groups + ' groups passed');
})().catch(function (e) { console.error(e && e.stack || e); process.exit(1); });
