'use strict';
// Runs build-templates/bytedance/main.js + touch-coordinates.js in a sandbox with a fake Cocos and a
// fake TikTok runtime. Checks the startup chain, Retry after failures, the 10 s stall watchdog,
// background pause, stale callbacks and the touch fix. It does NOT prove a real phone or real engine.
var assert = require('assert'), fs = require('fs'), path = require('path'), vm = require('vm');
var dir = process.env.BOOT_DIR || path.join(__dirname, '..', 'build-templates', 'bytedance');
var mainSource = fs.readFileSync(path.join(dir, 'main.js'), 'utf8');
var touchPath = path.join(dir, 'touch-coordinates.js');
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

function sandbox(opts) {
  opts = opts || {};
  var now = 1000, timers = [], log = {modal: [], loadScene: 0, run: 0, sub: [], hide: 0, loading: [], bundles: []};
  var handlers = {};
  var platform = {
    showLoading: function (o) { log.loading.push(o.title); },
    hideLoading: function () { log.hide++; },
    showModal: function (o) { log.modal.push(o); },
    showToast: function () {},
    onHide: function (fn) { handlers.hide = fn; }, onShow: function (fn) { handlers.show = fn; },
    loadSubpackage: function (o) { log.sub.push(o); if (opts.sub) opts.sub(o, log.sub.length); return {onProgressUpdate: function (fn) { o.progress = fn; }}; }
  };
  var inputManager = {getTouchesByEvent: function (event) { return event.changedTouches; }};
  var cc = {
    view: {enableRetina: function () {}, resizeWithBrowserSize: function () {}},
    debug: {DebugMode: {INFO: 1, ERROR: 2}},
    AssetManager: {BuiltinBundleName: {INTERNAL: 'internal', MAIN: 'main', RESOURCES: 'resources'}},
    assetManager: {
      init: function () {},
      loadScript: function (list, cb) { cb(opts.scriptError ? new Error('script') : null); },
      loadBundle: function (name, cb) { log.bundles.push(name); var e = opts.bundleError && opts.bundleError(name, log.bundles.length); cb(e || null); }
    },
    game: {run: function (option, cb) { log.run++; cb(); }},
    director: {loadScene: function (name, a, cb) { log.loadScene++; if (cb) cb(); }},
    internal: {inputManager: inputManager}
  };
  var ctx = {
    console: {log: function () {}, error: function () {}},
    TTMinis: {game: platform}, __globalAdapter: {isSubContext: false}, cc: cc,
    Date: {now: function () { return now; }},
    setInterval: function (fn, ms) { var t = {fn: fn, ms: ms, next: now + ms, on: true}; timers.push(t); return t; },
    clearInterval: function (t) { if (t) t.on = false; },
    require: function (p) { if (p === './touch-coordinates') return require(touchPath); throw new Error('unexpected require ' + p); }
  };
  ctx.window = ctx;
  ctx.window._CCSettings = {subpackages: ['resources'], jsList: ['assets/a.js'], launchScene: 'db://assets/Home.fire', bundleVers: {}, debug: false, groupList: [], collisionMatrix: []};
  vm.createContext(ctx);
  vm.runInContext(mainSource, ctx);
  return {
    ctx: ctx, log: log, platform: platform, inputManager: inputManager, handlers: handlers,
    boot: function () { ctx.window.boot(); },
    advance: function (ms) {
      var end = now + ms;
      while (true) {
        var due = timers.filter(function (t) { return t.on && t.next <= end; }).sort(function (a, b) { return a.next - b.next; })[0];
        if (!due) break;
        now = due.next; due.next += due.ms; due.fn();
      }
      now = end;
    },
    tapRetry: function () { var m = log.modal[log.modal.length - 1]; m.success({confirm: true}); }
  };
}

test('normal_start_loads_every_stage_once_and_hides_loading', function () {
  var s = sandbox({sub: function (o) { o.success(); }});
  s.boot();
  assert.deepStrictEqual(s.log.bundles, ['internal', 'resources', 'main']);
  assert.strictEqual(s.log.sub.length, 1, 'resources subpackage requested');
  assert.strictEqual(s.log.run, 1); assert.strictEqual(s.log.loadScene, 1); assert(s.log.hide >= 1);
  assert.strictEqual(s.log.modal.length, 0);
});
test('subpackage_failure_shows_retry_and_retry_succeeds', function () {
  var s = sandbox({sub: function (o, n) { if (n === 1) o.fail({errMsg: 'net'}); else o.success(); }});
  s.boot();
  assert.strictEqual(s.log.modal.length, 1, 'visible Retry');
  assert.strictEqual(s.log.loadScene, 0);
  s.tapRetry();
  assert.strictEqual(s.log.sub.length, 2, 'Retry makes a NEW request');
  assert.strictEqual(s.log.loadScene, 1);
});
test('subpackage_without_any_callback_stalls_then_retry', function () {
  var s = sandbox({sub: function (o, n) { if (n >= 2) o.success(); }});
  s.boot();
  s.advance(9000); assert.strictEqual(s.log.modal.length, 0, 'not before 10 s');
  s.advance(3000); assert.strictEqual(s.log.modal.length, 1, 'stall ends in a visible Retry within 2 s of the 10 s limit');
  s.tapRetry();
  assert.strictEqual(s.log.loadScene, 1);
});
test('late_callback_from_old_attempt_cannot_start_game_twice', function () {
  var first = null;
  var s = sandbox({sub: function (o, n) { if (n === 1) first = o; else o.success(); }});
  s.boot(); s.advance(11000); s.tapRetry();
  assert.strictEqual(s.log.loadScene, 1);
  first.success();
  assert.strictEqual(s.log.loadScene, 1, 'old attempt ignored');
  assert.strictEqual(s.log.run, 1);
});
test('progress_keeps_watchdog_alive', function () {
  var held = null;
  var s = sandbox({sub: function (o) { held = o; }});
  s.boot();
  for (var i = 0; i < 5; i++) { s.advance(8000); held.progress({progress: 10 + i * 10}); }
  assert.strictEqual(s.log.modal.length, 0, 'download that keeps moving is not killed');
  held.success();
  assert.strictEqual(s.log.loadScene, 1);
});
test('time_in_background_is_not_counted', function () {
  var held = null;
  var s = sandbox({sub: function (o) { held = o; }});
  s.boot(); s.advance(5000);
  s.handlers.hide(); s.advance(60000); s.handlers.show();
  s.advance(5000);
  assert.strictEqual(s.log.modal.length, 0);
  held.success(); assert.strictEqual(s.log.loadScene, 1);
});
test('script_or_bundle_error_shows_retry_never_silent', function () {
  var s1 = sandbox({scriptError: true}); s1.boot();
  assert.strictEqual(s1.log.modal.length, 1);
  var s2 = sandbox({sub: function (o) { o.success(); }, bundleError: function (name) { return name === 'main' ? new Error('x') : null; }});
  s2.boot();
  assert.strictEqual(s2.log.modal.length, 1); assert.strictEqual(s2.log.loadScene, 0);
});
test('touch_fix_installed_and_fills_missing_client_coordinates', function () {
  var s = sandbox({sub: function (o) { o.success(); }});
  s.boot();
  var out = s.inputManager.getTouchesByEvent({changedTouches: [{identifier: 0, screenX: 120, screenY: 300}], touches: []});
  assert.strictEqual(out[0].clientX, 120); assert.strictEqual(out[0].clientY, 300);
  var kept = s.inputManager.getTouchesByEvent({changedTouches: [{identifier: 1, clientX: 5, clientY: 6, screenX: 99, screenY: 99}]});
  assert.strictEqual(kept[0].clientX, 5, 'existing clientX untouched');
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
console.log(JSON.stringify({suite: 'boot-templates', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
if (failed.length) process.exitCode = 1;
