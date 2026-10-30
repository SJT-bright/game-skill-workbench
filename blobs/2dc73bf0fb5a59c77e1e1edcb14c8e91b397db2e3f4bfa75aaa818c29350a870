'use strict';
// Runs build-templates/bytedance/main.js + touch-coordinates.js in a sandbox with a fake Cocos and a
// fake TikTok runtime. Checks the startup chain, Retry after failures, the 10 s stall watchdog,
// background pause, stale callbacks, the per-file load guard (download AND image decode, v1.4) and the touch fix.
// It does NOT prove a real phone or real engine (host runs on real 2.4 engines: briefs/out/W-D3).
var assert = require('assert'), fs = require('fs'), path = require('path'), vm = require('vm');
var dir = process.env.BOOT_DIR || path.join(__dirname, '..', 'build-templates', 'bytedance');
var mainSource = fs.readFileSync(path.join(dir, 'main.js'), 'utf8');
var touchPath = path.join(dir, 'touch-coordinates.js');
// v1.3: storage-guard.js lives in parts/ (copied to the package root next to main.js); the WebP probe in webp-probe/.
var storagePath = process.env.STORAGE_GUARD || path.join(__dirname, '..', 'parts', 'storage-guard.js');
var probePath = path.join(__dirname, '..', 'webp-probe', 'cocos2.4', 'webp-decode-probe.js');
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

function sandbox(opts) {
  opts = opts || {};
  var now = 1000, timers = [], log = {modal: [], loadScene: 0, run: 0, sub: [], hide: 0, loading: [], bundles: [], scenes: []};
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
  // Fake 2.4 downloader/parser: handlers registered by ext, like the minigame adapter does.
  var fileCalls = [];
  function fakeFile(kind) {
    return function (url, options, done) { var c = {kind: kind, url: url, done: done}; fileCalls.push(c); if (opts.file) opts.file(c, fileCalls.length); };
  }
  var downloader = {_downloaders: {'.png': fakeFile('download'), '.json': fakeFile('download'), bundle: fakeFile('bundle')}, maxRetryCount: 3,
    register: function (ext, fn) { this._downloaders[ext] = fn; }};
  // Fake 2.4 parser, shaped like the real one (engine asset-manager/parser.js, 2.4.4-2.4.15): the handler table
  // is private (no _parsers), parse() joins a request for an id already being parsed, and only the handler's
  // answer releases that id. The adapter registers downloader.downloadDomImage (no timeout) for images.
  var parserTable = {}, parsing = {};
  var parser = {
    register: function (ext, fn) {
      if (typeof ext === 'object') Object.keys(ext).forEach(function (k) { parserTable[k] = ext[k]; });
      else parserTable[ext] = fn;
    },
    parse: function (id, file, type, options, done) {
      if (parsing[id]) { parsing[id].push(done); return; }
      var handler = parserTable[type];
      if (!handler) { done(null, file); return; }
      parsing[id] = [done];
      handler(file, options, function (error, value) {
        var waiting = parsing[id] || []; delete parsing[id];
        waiting.forEach(function (f) { f(error, value); });
      });
    }
  };
  downloader.downloadDomImage = fakeFile('image');
  var plistParser = fakeFile('plist');
  parser.register({'.png': downloader.downloadDomImage, '.jpg': downloader.downloadDomImage,
    '.webp': downloader.downloadDomImage, '.image': downloader.downloadDomImage, '.plist': plistParser});
  var initCalls = 0, runCalls = 0;
  // v1.6: the 2.4 file cache (asset-manager/shared.js `files`, exposed as cc.assetManager._files; `parsed` as _parsed).
  function fakeCache() {
    var map = {};
    return {map: map, get: function (k) { return map[k]; }, add: function (k, v) { map[k] = v; return v; },
      has: function (k) { return k in map; }, remove: function (k) { var v = map[k]; delete map[k]; return v; }};
  }
  var files = fakeCache(), parsedCache = fakeCache();
  var mainBundle = {getSceneInfo: function (name) { return name === 'db://assets/Home.fire' ? {uuid: 'home-scene'} : null; }};
  var bundleList = [{getSceneInfo: function () { return null; }}, mainBundle];
  // v1.6: mode 'engine' loads the scene the way 2.4.4-2.4.15 do (CCDirector.loadScene + asset-manager load.js/parser.js):
  // the scene JSON is downloaded into `files`, deserialized IN PLACE (a second deserialize of the same object fails at
  // once, as the debug engine's "Can not deserialize the same JSON data again"), then its image is decoded through
  // parser.parse. `files` loses the entry only on success or on a parse error; a scene is never put in `parsed`.
  function engineScene(onLaunched) {
    var director = cc.director;
    if (director._loadingScene) return false;
    director._loadingScene = 'db://assets/Home.fire';
    var id = 'home-scene@import';
    function end(error) {
      director._loadingScene = '';
      if (error) { onLaunched && onLaunched('Failed to load scene: ' + (error.message || error)); return; }
      if (onLaunched) onLaunched(null, {});
      if (log.afterLaunch) log.afterLaunch();
    }
    var json = files.get(id);
    if (!json) { json = files.add(id, {deserialized: false}); log.sceneDownloads = (log.sceneDownloads || 0) + 1; }
    if (json.deserialized) { log.deserializeAgain = (log.deserializeAgain || 0) + 1; files.remove(id);
      end(new Error('Can not deserialize the same JSON data again.')); return true; }
    json.deserialized = true;
    var dependency = opts.sceneDependency || function (cb) { parser.parse('home-img@native', 'home.png', '.png', {}, cb); };
    dependency(function (error) {
      if (error) { end(error); return; }
      files.remove(id); parsedCache.remove(id);
      end(null);
    });
    return true;
  }
  var cc = {
    view: {enableRetina: function () {}, resizeWithBrowserSize: function () {}},
    debug: {DebugMode: {INFO: 1, ERROR: 2}},
    AssetManager: {BuiltinBundleName: {INTERNAL: 'internal', MAIN: 'main', RESOURCES: 'resources'}},
    assetManager: {
      downloader: opts.noDownloader ? undefined : downloader, parser: parser,
      _files: files, _parsed: parsedCache,
      bundles: {find: function (pred) { for (var i = 0; i < bundleList.length; i++) if (pred(bundleList[i], String(i))) return bundleList[i]; return null; }},
      init: function () { initCalls++; if (opts.initThrows && initCalls === 1) throw new Error('init'); },
      loadScript: function (list, cb) { log.scripts = (log.scripts || 0) + 1; if (opts.onScript) opts.onScript(); cb(opts.scriptError ? new Error('script') : null); },
      loadBundle: function (name, cb) { log.bundles.push(name); var e = opts.bundleError && opts.bundleError(name, log.bundles.length); cb(e || null); }
    },
    game: {run: function (option, cb) { runCalls++; if (opts.runThrows && runCalls === 1) throw new Error('run'); log.run++; cb(); }},
    // 2.4.15 signature: loadScene(name, onLaunched, onUnloaded); onLaunched(error) on failure.
    // The engine fires EVENT_AFTER_SCENE_LAUNCH for a scene launched by any attempt, even a superseded one.
    Director: {EVENT_AFTER_SCENE_LAUNCH: 'director_after_scene_launch'},
    director: {once: function (event, fn) { log.afterLaunch = fn; }, loadScene: function (name, onLaunched, onUnloaded) {
      log.loadScene++; var n = log.loadScene;
      var mode = opts.scene ? opts.scene(n) : 'ok';
      log.scenes.push(mode);
      if (mode === 'engine') return engineScene(onLaunched);
      if (mode === 'hang') return true;
      if (mode === 'hold') { log.heldScene = onLaunched; return true; }
      if (mode === 'error') { if (onLaunched) onLaunched(new Error('scene')); return true; }
      if (onUnloaded) onUnloaded();
      if (onLaunched) onLaunched(null, {});
      return true;
    }},
    internal: {inputManager: inputManager}, sys: opts.sys
  };
  function addTimer(fn, ms, once) { var t = {fn: fn, ms: ms, next: now + ms, on: true, once: once}; timers.push(t); return t; }
  var ctx = {
    console: {log: function () {}, error: function () {}},
    TTMinis: {game: platform}, __globalAdapter: {isSubContext: false}, cc: cc,
    Date: {now: function () { return now; }},
    setInterval: function (fn, ms) { return addTimer(fn, ms, false); },
    clearInterval: function (t) { if (t) t.on = false; },
    setTimeout: function (fn, ms) { return addTimer(fn, ms || 0, true); },
    clearTimeout: function (t) { if (t) t.on = false; },
    requestAnimationFrame: function (fn) { return addTimer(fn, opts.rafMs || 16, true); },
    require: function (p) {
      if (p === './touch-coordinates') return require(touchPath);
      if (p === './storage-guard') { log.storageInstalls = (log.storageInstalls || 0) + 1; return opts.storageGuard || require(storagePath); }
      if (p === './webp-decode-probe') { if (opts.probe) return opts.probe; return require(probePath); }
      throw new Error('unexpected require ' + p);
    }
  };
  ctx.window = ctx;
  if (opts.login) platform.login = opts.login;
  if (opts.webpFlag) ctx.__TIKTOK_KIT_WEBP_PROBE__ = true;
  if (opts.loginSent) ctx.__tiktokKitLoginSent = true;
  ctx.window._CCSettings = {subpackages: ['resources'], jsList: ['assets/a.js'], launchScene: 'db://assets/Home.fire', bundleVers: {}, debug: false, groupList: [], collisionMatrix: []};
  vm.createContext(ctx);
  vm.runInContext(mainSource, ctx);
  return {
    ctx: ctx, log: log, platform: platform, inputManager: inputManager, handlers: handlers,
    downloader: downloader, parser: parser, fileCalls: fileCalls, files: files,
    boot: function () { ctx.window.boot(); },
    advance: function (ms) {
      var end = now + ms;
      while (true) {
        var due = timers.filter(function (t) { return t.on && t.next <= end; }).sort(function (a, b) { return a.next - b.next; })[0];
        if (!due) break;
        now = due.next;
        if (due.once) due.on = false; else due.next += due.ms;
        due.fn();
      }
      now = end;
    },
    // The main thread is blocked: wall time jumps without any timer or frame running.
    stall: function (ms) { now += ms; timers.forEach(function (t) { if (t.on && t.next < now) t.next = now; }); },
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

// ---------- v1.2 (MergeShot2048 v81 -> v82/v84, D6 items 1, 3, 8) ----------
function okBoot(extra) {
  var o = {sub: function (x) { x.success(); }};
  Object.keys(extra || {}).forEach(function (k) { o[k] = extra[k]; });
  var s = sandbox(o); s.boot(); return s;
}
function callFile(s, table, ext) {
  var out = [];
  var done = function (e, v) { out.push({error: e, value: v}); };
  if (table === 'downloader') s.downloader._downloaders[ext]('a' + ext, {}, done);
  else s.parser.parse('a' + ext, 'a' + ext, ext, {}, done);   // the engine's own entry point
  return out;
}
test('file_without_answer_is_requested_again_at_10s_first_answer_wins', function () {
  var s = okBoot({file: function (c, n) { if (n >= 2) c.done(null, 'second'); }});
  var out = callFile(s, 'downloader', '.png');
  assert.strictEqual(s.fileCalls.length, 1);
  s.advance(9500); assert.strictEqual(s.fileCalls.length, 1, 'not before 10 s'); assert.strictEqual(out.length, 0);
  s.advance(1000); assert.strictEqual(s.fileCalls.length, 2, 'requested again at 10 s');
  assert.deepStrictEqual(out.map(function (x) { return x.value; }), ['second']);
  s.fileCalls[0].done(null, 'late first'); assert.strictEqual(out.length, 1, 'late first answer dropped, no double callback');
});
test('file_late_first_answer_still_wins_when_it_comes_first', function () {
  var s = okBoot();
  var out = callFile(s, 'parser', '.png');
  s.advance(10500); assert.strictEqual(s.fileCalls.length, 2);
  s.fileCalls[0].done(null, 'first'); s.fileCalls[1].done(null, 'second');
  assert.deepStrictEqual(out.map(function (x) { return x.value; }), ['first'], 'a late answer is used, never thrown away');
});
test('file_error_is_retried_once_then_reported', function () {
  var s = okBoot({file: function (c) { c.done(new Error('io')); }});
  var out = callFile(s, 'downloader', '.json');
  assert.strictEqual(out.length, 0, 'first error is retried');
  s.advance(600);
  assert.strictEqual(s.fileCalls.length, 2); assert.strictEqual(out.length, 1); assert(out[0].error);
});
test('silent_file_fails_at_30s_not_before', function () {
  var s = okBoot();
  var out = callFile(s, 'downloader', '.png');
  s.advance(29000); assert.strictEqual(out.length, 0, 'not before 30 s');
  s.advance(1500); assert.strictEqual(out.length, 1); assert(out[0].error, 'reported as failed so Retry can start fresh');
});
test('file_guard_background_time_and_long_frames_not_counted', function () {
  var s = okBoot();
  var out = callFile(s, 'downloader', '.png');
  s.advance(5000); s.handlers.hide(); s.advance(120000); s.handlers.show();
  assert.strictEqual(s.fileCalls.length, 1, 'background time not counted');
  s.stall(60000); s.advance(16);
  assert.strictEqual(s.fileCalls.length, 1, 'one blocked frame adds at most 1 s');
  assert.strictEqual(out.length, 0);
  s.advance(5000); assert.strictEqual(s.fileCalls.length, 2, 'foreground time still counts');
});
test('scene_error_shows_retry_and_retry_reloads_only_the_scene', function () {
  var s = okBoot({scene: function (n) { return n === 1 ? 'error' : 'ok'; }});
  assert.strictEqual(s.log.modal.length, 1, 'visible Retry after scene error');
  s.tapRetry();
  assert.strictEqual(s.log.loadScene, 2); assert.strictEqual(s.log.run, 1, 'engine started once');
  assert.strictEqual(s.log.sub.length, 1, 'subpackage not downloaded again');
  s.advance(30000); assert.strictEqual(s.log.modal.length, 1, 'scene up: no later Retry');
});
test('scene_without_answer_shows_retry_within_20s', function () {
  var s = okBoot({scene: function (n) { return n === 1 ? 'hang' : 'ok'; }});
  s.advance(9000); assert.strictEqual(s.log.modal.length, 0);
  s.advance(11000); assert.strictEqual(s.log.modal.length, 1, 'Retry within 20 s');
  s.tapRetry(); assert.strictEqual(s.log.loadScene, 2); assert.strictEqual(s.log.run, 1);
});
test('startup_exception_shows_retry_never_frozen', function () {
  var s1 = sandbox({sub: function (x) { x.success(); }, initThrows: true}); s1.boot();
  assert.strictEqual(s1.log.modal.length, 1, 'exception during setup shows Retry');
  s1.tapRetry(); assert.strictEqual(s1.log.loadScene, 1, 'Retry runs setup again and starts');
  var s2 = sandbox({sub: function (x) { x.success(); }, runThrows: true}); s2.boot();
  assert.strictEqual(s2.log.modal.length, 1, 'exception while starting the engine shows Retry');
  s2.tapRetry(); assert.strictEqual(s2.log.loadScene, 1);
});
test('retry_after_later_step_does_not_download_subpackage_again', function () {
  var s = okBoot({bundleError: function (name, n) { return name === 'main' && n === 3 ? new Error('x') : null; }});
  assert.strictEqual(s.log.modal.length, 1);
  s.tapRetry();
  assert.strictEqual(s.log.sub.length, 1, 'finished subpackage is not requested again');
  assert.strictEqual(s.log.loadScene, 1);
});
test('silent_bundle_request_is_released_before_the_stall_retry', function () {
  var s = okBoot();
  var out = callFile(s, 'downloader', 'bundle');
  s.advance(8500); assert.strictEqual(out.length, 0);
  s.advance(1000); assert.strictEqual(out.length, 1); assert(out[0].error);
  assert.strictEqual(s.fileCalls.length, 1, 'a bundle request is never duplicated');
});

test('long_blocked_frame_does_not_fake_a_stall', function () {
  var held = null;
  var s = sandbox({sub: function (o) { held = o; }});
  s.boot(); s.advance(3000);
  s.stall(30000); s.advance(1000);
  assert.strictEqual(s.log.modal.length, 0, 'a 30 s blocked main thread counts as at most 1 s');
  held.success(); assert.strictEqual(s.log.loadScene, 1);
});

// ---------- v1.4 (v7.7 W-D3): the image-decode guard reaches the real 2.4 parser ----------
test('v14_image_decode_without_answer_requested_again_at_10s', function () {
  var s = okBoot({file: function (c, n) { if (c.kind === 'image' && n >= 2) c.done(null, 'img2'); }});
  var out = callFile(s, 'parser', '.png');
  assert.strictEqual(s.fileCalls.length, 1, 'decode started through parser.parse');
  s.advance(9500); assert.strictEqual(s.fileCalls.length, 1, 'not before 10 s');
  s.advance(1000); assert.strictEqual(s.fileCalls.length, 2, 'decode requested again at 10 s');
  assert.strictEqual(s.fileCalls[1].kind, 'image', 'the second request is a real decode (downloadDomImage)');
  assert.deepStrictEqual(out.map(function (x) { return x.value; }), ['img2']);
});
test('v14_silent_decode_released_at_30s_and_next_request_starts_fresh', function () {
  var s = okBoot();
  var out = callFile(s, 'parser', '.jpg');
  s.advance(29000); assert.strictEqual(out.length, 0, 'not before 30 s');
  s.advance(1500); assert.strictEqual(out.length, 1); assert(out[0].error, 'reported as failed');
  var before = s.fileCalls.length;
  var again = callFile(s, 'parser', '.jpg');
  assert.strictEqual(s.fileCalls.length, before + 1, 'the id was released: a later request decodes again, not joined to the stuck one');
  s.fileCalls[s.fileCalls.length - 1].done(null, 'ok');
  assert.deepStrictEqual(again.map(function (x) { return x.value; }), ['ok']);
});
test('v14_decode_guard_background_not_counted', function () {
  var s = okBoot();
  var out = callFile(s, 'parser', '.webp');
  s.advance(4000); s.handlers.hide(); s.advance(120000); s.handlers.show();
  assert.strictEqual(s.fileCalls.length, 1, 'background time not counted'); assert.strictEqual(out.length, 0);
  s.advance(7000); assert.strictEqual(s.fileCalls.length, 2, 'foreground time counts');
});
test('v14_decode_error_retried_once', function () {
  var s = okBoot({file: function (c, n) { if (c.kind === 'image') { if (n === 1) c.done(new Error('decode')); else c.done(null, 'img'); } }});
  var out = callFile(s, 'parser', '.png');
  assert.strictEqual(out.length, 0, 'first error is retried');
  s.advance(600);
  assert.deepStrictEqual(out.map(function (x) { return x.value; }), ['img']);
});
test('v14_non_image_parsers_untouched', function () {
  var s = okBoot();
  callFile(s, 'parser', '.plist');
  assert.strictEqual(s.fileCalls[0].kind, 'plist', 'adapter plist parser still used');
  s.advance(40000); assert.strictEqual(s.fileCalls.length, 1, 'no bounded wrapper on a parser the kit cannot read');
});
test('v14_retry_after_scene_came_up_hides_loading', function () {
  var s = okBoot({scene: function (n) { return n === 1 ? 'hold' : 'ok'; }});
  s.advance(12000); assert.strictEqual(s.log.modal.length, 1, 'stall Retry shown while the scene is still loading');
  s.log.heldScene(null);                       // the scene comes up a moment later (old attempt: ignored)
  s.log.afterLaunch();                         // ... and the engine reports it launched
  var shown = s.log.loading.length, hides = s.log.hide;
  s.tapRetry();
  assert.strictEqual(s.log.loading.length, shown, 'no masked loading put back over the running game');
  assert(s.log.hide > hides, 'loading hidden');
  assert.strictEqual(s.log.loadScene, 1, 'scene not loaded again'); assert.strictEqual(s.log.run, 1);
  s.advance(30000); assert.strictEqual(s.log.modal.length, 1, 'no later Retry');
});
test('v14_decode_guard_needs_no_private_table', function () {
  var s = okBoot();
  assert.strictEqual(s.parser._parsers, undefined, 'fake parser is shaped like the real one');
  var out = callFile(s, 'parser', '.image');
  s.advance(10500); assert.strictEqual(s.fileCalls.length, 2);
  assert.strictEqual(out.length, 0);
});

// ---------- v1.5 (v7.7 W-F1a): a per-file re-request is progress; the watchdog waits for a guarded file ----------
// The scene is held; the "engine" decodes one image through parser.parse and launches the scene (or reports the
// error) when that decode answers. rafMs 1200 = the ~1 frame per second the W-D3 host showed at startup, where the
// v1.4 stall Retry (11 s) beat the file re-request (12 s) and stayed over the home page.
function heldSceneWithImage(answer, extra) {
  var o = {rafMs: 1200, scene: function (n) { return n === 1 ? 'hold' : 'ok'; },
    file: function (c, n) { if (c.kind === 'image') answer(c, n); }};
  Object.keys(extra || {}).forEach(function (k) { o[k] = extra[k]; });
  var s = okBoot(o);
  s.parser.parse('home.png', 'home.png', '.png', {}, function (error) {
    if (!s.log.heldScene) return;
    var launch = s.log.heldScene; s.log.heldScene = null;
    if (error) { launch(error); return; }
    launch(null); s.log.afterLaunch();
  });
  return s;
}
test('v15_rerequest_loads_home_without_a_load_failed_dialog', function () {
  var s = heldSceneWithImage(function (c, n) { if (n >= 2) c.done(null, 'img'); });
  s.advance(25000);
  assert.strictEqual(s.fileCalls.length, 2, 'the stuck decode was requested again');
  assert.strictEqual(s.log.heldScene, null, 'home came up from the re-request');
  assert.strictEqual(s.log.modal.length, 0, 'no Load failed dialog over the home page');
});
test('v15_single_stuck_file_shows_retry_only_when_it_fails', function () {
  var s = heldSceneWithImage(function () { /* never answers */ });
  s.advance(25000);
  assert.strictEqual(s.fileCalls.length, 2, 're-requested once at 10 s');
  assert.strictEqual(s.log.modal.length, 0, 'no Retry while the file is inside its 30 s budget (not at 10 s or 20 s)');
  s.advance(15000);
  assert.strictEqual(s.log.modal.length, 1, 'Retry when the file really fails');
  s.tapRetry(); assert.strictEqual(s.log.loadScene, 2, 'Retry loads the scene again');
});
test('v15_watchdog_runs_again_once_the_file_answered', function () {
  var s = heldSceneWithImage(function () {});
  s.parser.parse('icon.png', 'icon.png', '.png', {}, function () {});   // answered at 3 s, scene never launches
  s.advance(3000); s.fileCalls[1].done(null, 'icon');
  var pending = s.fileCalls[0];
  s.log.heldScene = null;                                               // the engine will never launch the scene
  s.advance(1000); pending.done(null, 'home');                          // home image answers at 4 s
  s.advance(9000); assert.strictEqual(s.log.modal.length, 0, 'not before 10 s without progress');
  s.advance(3000); assert.strictEqual(s.log.modal.length, 1, 'the 10 s watchdog is back once no file is waiting');
});
test('v15_rerequest_counts_as_progress', function () {
  // a decode that is re-requested at 10 s and then answers with an error the engine swallows: the watchdog
  // starts its 10 s from the re-request, so Retry comes once nothing moved for 10 s after it
  var s = okBoot({scene: function (n) { return n === 1 ? 'hold' : 'ok'; },
    file: function (c, n) { if (c.kind === 'image' && n === 2) s2 = c; }});
  var s2 = null;
  s.parser.parse('a.png', 'a.png', '.png', {}, function () {});
  s.advance(10500); assert.strictEqual(s.fileCalls.length, 2);
  s2.done(new Error('swallowed'));                                      // last attempt: guard finishes with an error
  s.fileCalls[0].done(new Error('late'));
  s.advance(8000); assert.strictEqual(s.log.modal.length, 0, 'the re-request at 10 s restarted the 10 s clock');
  s.advance(3000); assert.strictEqual(s.log.modal.length, 1);
});

// ---------- v1.6 (v7.7 W-G1): the first Retry after a failed launch scene works ----------
// The scene loads through the engine-shaped fake (mode 'engine'): its JSON stays in the file cache after a failed
// dependency, exactly as in 2.4.4-2.4.15, so a Retry that does not drop it fails at once.
test('v16_scene_dependency_timeout_one_retry_enters_scene', function () {
  var s = okBoot({scene: function () { return 'engine'; },
    file: function (c, n) { if (c.kind === 'image' && n >= 3) c.done(null, 'img'); }});
  s.advance(29000); assert.strictEqual(s.log.modal.length, 0, 'no Retry while the image is inside its 30 s');
  s.advance(2000); assert.strictEqual(s.log.modal.length, 1, 'Retry when the image really failed');
  assert.strictEqual(s.fileCalls.length, 2, 'image asked twice (0 s, 10 s)');
  s.tapRetry();
  assert.strictEqual(s.log.deserializeAgain, undefined, 'the scene JSON was not deserialized a second time');
  assert.strictEqual(s.log.sceneDownloads, 2, 'Retry read the scene file fresh');
  assert.strictEqual(s.fileCalls.length, 3, 'Retry asked for the image again');
  assert.strictEqual(s.files.has('home-scene@import'), false, 'scene entered (engine dropped the cache entry)');
  assert.strictEqual(s.log.run, 1, 'engine started once');
  s.advance(40000); assert.strictEqual(s.log.modal.length, 1, 'ONE Retry was enough: no second dialog');
});
test('v16_retry_while_file_still_stuck_comes_back_only_when_it_fails_again', function () {
  var s = okBoot({scene: function () { return 'engine'; }});
  s.advance(31000); assert.strictEqual(s.log.modal.length, 1);
  s.tapRetry();
  s.advance(2000); assert.strictEqual(s.log.modal.length, 1, 'no immediate re-fail after Retry');
  assert.strictEqual(s.log.deserializeAgain, undefined, 'no deserialize-again error');
  assert.strictEqual(s.fileCalls.length, 3, 'Retry asked for the image again');
  s.advance(25000); assert.strictEqual(s.log.modal.length, 1, 'not while the image is inside its new 30 s (10 s, 20 s)');
  assert.strictEqual(s.fileCalls.length, 4, 'and re-requested it at 10 s');
  s.advance(5000); assert.strictEqual(s.log.modal.length, 2, 'Retry again only when the image really failed again');
  s.tapRetry(); s.advance(1000);
  assert.strictEqual(s.log.modal.length, 2, 'and the next Retry does not re-fail at once either');
  assert.strictEqual(s.log.sceneDownloads, 3);
});
test('v16_superseded_scene_failure_is_released_too', function () {
  // the scene waits on engine work with no file guard: the 10 s watchdog shows Retry while the scene is still
  // loading; the Retry waits for that load, which then fails for the OLD attempt; the new load must start clean
  var held = [];
  var s = okBoot({scene: function () { return 'engine'; },
    sceneDependency: function (cb) { if (held.length === 0) held.push(cb); else cb(null); }});
  s.advance(12000); assert.strictEqual(s.log.modal.length, 1, 'stall Retry while the scene is loading');
  s.tapRetry(); s.advance(1000);
  held[0](new Error('engine work failed'));                 // the old attempt's scene fails now
  s.advance(1000);
  assert.strictEqual(s.log.deserializeAgain, undefined, 'the new load did not reuse the rewritten JSON');
  assert.strictEqual(s.log.sceneDownloads, 2);
  assert.strictEqual(s.files.has('home-scene@import'), false, 'scene entered');
  s.advance(30000); assert.strictEqual(s.log.modal.length, 1, 'no second dialog');
});
test('v16_normal_start_and_other_scene_errors_unchanged', function () {
  var s = okBoot({scene: function () { return 'engine'; }, file: function (c) { c.done(null, 'img'); }});
  assert.strictEqual(s.log.sceneDownloads, 1); assert.strictEqual(s.log.modal.length, 0);
  assert.strictEqual(s.files.has('home-scene@import'), false, 'scene entered on the first try');
  // an engine without bundles/_files (or a launch scene no bundle knows) must not break the Retry
  var t = okBoot({scene: function (n) { return n === 1 ? 'error' : 'ok'; }});
  delete t.ctx.cc.assetManager.bundles; delete t.ctx.cc.assetManager._files;
  t.tapRetry(); assert.strictEqual(t.log.loadScene, 2); assert.strictEqual(t.log.modal.length, 1);
});

// ---------- v1.3 (kit 2.0): storage layer, silent login, WebP-probe exception ----------
function tiktokStorage() {
  var map = {};
  return {getItem: function (k) { return k in map ? map[k] : false; }, setItem: function (k, v) { map[k] = v; }, map: map};
}
test('v13_storage_guard_installed_before_game_scripts', function () {
  var st = tiktokStorage(), seen = null;
  var s = sandbox({sub: function (o) { o.success(); }, sys: {localStorage: st},
    onScript: function () { seen = st.getItem.__tiktokKitStorageGuard === true; }});
  s.boot();
  assert.strictEqual(seen, true, 'guard is on cc.sys.localStorage when the game scripts load');
  assert.strictEqual(st.getItem('never_written'), null, 'unwritten key reads null, not false');
  st.setItem('level', 3); assert.strictEqual(st.map.level, '3');
  assert.strictEqual(s.log.loadScene, 1);
});
test('v13_storage_guard_error_does_not_block_startup', function () {
  var s = sandbox({sub: function (o) { o.success(); }, storageGuard: function () { throw new Error('boom'); }});
  s.boot();
  assert.strictEqual(s.log.storageInstalls, 1);
  assert.strictEqual(s.log.loadScene, 1); assert.strictEqual(s.log.modal.length, 0);
});
test('v13_one_silent_login_never_awaited', function () {
  var logins = [];
  var s = sandbox({sub: function (o) { o.success(); }, login: function (o) { logins.push(o); /* never answers */ }});
  s.boot();
  assert.strictEqual(s.log.loadScene, 1, 'startup does not wait for login');
  s.advance(100);
  assert.strictEqual(logins.length, 1, 'login sent once');
  assert.strictEqual(typeof logins[0].fail, 'function');
  s.advance(30000); assert.strictEqual(s.log.modal.length, 0, 'an unanswered login never shows Retry');
  assert.strictEqual(logins.length, 1, 'still one login after 30 s');
});
test('v13_login_not_sent_twice_in_one_runtime', function () {
  var logins = 0;
  var s = sandbox({sub: function (o) { o.success(); }, loginSent: true, login: function () { logins++; }});
  s.boot(); s.advance(100);
  assert.strictEqual(logins, 0, 'an earlier boot already sent the login');
});
test('v13_login_throw_or_reject_does_not_break_startup', function () {
  var s = sandbox({sub: function (o) { o.success(); }, login: function () { throw new Error('login'); }});
  s.boot(); s.advance(100);
  assert.strictEqual(s.log.loadScene, 1); assert.strictEqual(s.log.modal.length, 0);
  var r = sandbox({sub: function (o) { o.success(); }, login: function (o) { o.fail({errMsg: 'x'}); return {then: function (a, b) { b(new Error('no')); }, catch: function () {}}; }});
  r.boot(); r.advance(100);
  assert.strictEqual(r.log.loadScene, 1); assert.strictEqual(r.log.modal.length, 0);
});
test('v13_webp_probe_off_without_the_exception_flag', function () {
  var probed = 0;
  var s = sandbox({sub: function (o) { o.success(); }, sys: {capabilities: {webp: false}}, probe: function (root, ready) { probed++; ready(); }});
  s.boot();
  assert.strictEqual(probed, 0); assert.strictEqual(s.log.loadScene, 1);
});
test('v13_webp_probe_runs_before_scripts_and_again_on_retry', function () {
  var order = [], answer = null;
  var caps = {webp: false};
  var s = sandbox({webpFlag: true, sys: {capabilities: caps},
    sub: function (o, n) { if (n === 1) o.fail({errMsg: 'net'}); else o.success(); },
    onScript: function () { order.push('scripts'); },
    probe: function (root, ready) { order.push('probe'); answer = ready; }});
  s.boot();
  assert.deepStrictEqual(order, ['probe'], 'nothing loads before the probe answers');
  answer();                                   // probe answered: WebP still off
  assert.deepStrictEqual(order, ['probe', 'scripts']);
  assert.strictEqual(s.log.modal.length, 1);
  s.tapRetry();
  assert.deepStrictEqual(order, ['probe', 'scripts', 'probe'], 'Retry runs the probe again');
  caps.webp = true; answer();
  assert.strictEqual(s.log.loadScene, 1);
});
test('v13_webp_probe_silent_ends_in_retry', function () {
  var s = sandbox({webpFlag: true, sys: {capabilities: {webp: false}}, sub: function (o) { o.success(); },
    probe: function () { /* never answers */ }});
  s.boot(); s.advance(12000);
  assert.strictEqual(s.log.modal.length, 1, 'a probe that never answers still ends in Retry');
});
test('v13_real_webp_probe_module_decodes_through_createImage', function () {
  var caps = {webp: false}, made = 0;
  var s = sandbox({webpFlag: true, sys: {capabilities: caps}, sub: function (o) { o.success(); }});
  s.platform.createImage = function () { made++; var img = {}; setTimeoutHook(function () { img.width = 16; img.height = 16; img.onload(); }); return img; };
  function setTimeoutHook(fn) { s.ctx.setTimeout(fn, 10); }
  // the real probe reads root.TTMinis.game / root.cc: the sandbox window is the context itself
  s.boot(); s.advance(50);
  assert.strictEqual(made, 1); assert.strictEqual(caps.webp, true); assert.strictEqual(s.log.loadScene, 1);
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
console.log(JSON.stringify({suite: 'boot-templates', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
if (failed.length) process.exitCode = 1;
