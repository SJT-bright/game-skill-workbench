'use strict';
// tiktok-kit:boot3x:1.0  Cocos Creator 3.x startup guard (TikTok Platform Kit). Copy unchanged.
// Load it in game.js right before System.warmup(...):
//   require('./boot-guard-3x.js').install(null, globalThis.TTMinis&&TTMinis.game||globalThis.tt); // tiktok-kit:boot3x:1.0
// It waits for System.import('cc') (the call game.js makes before application.init / cc.game.init), then guards
// the startup the way the 2.4 kit main.js v1.6 does. Nothing in the game's own code changes.
//
// Why (问题普查 2026-11-04: startup_stuck 46 games, startup_retry_broken 28, startup_false_timeout, retry_no_recover,
// loading_progress_missing): 3.x games had no startup part, so each wrote its own wait. TrashPanda / 恢复线场 /
// 美女快跑 failed a slow but moving download after a fixed 15 s total deadline; 农场水渠 showed Retry only after
// ~15 s; others counted background time or let Retry join the stuck request.
//
// Rules (numbers are main.js v1.6's):
//  - every package file (download, and image decode when the adapter exposes downloader.downloadDomImage) that has
//    not answered after 10 s of FOREGROUND time is requested again; the first answer wins; an error is retried once
//    after 0.5 s; only 30 s without an answer fails the file. A bundle request gives up at 9 s so the 10 s Retry
//    starts a fresh one instead of joining the stuck one.
//  - background time is not counted (tt.onHide / tt.onShow) and one frame or timer tick adds at most 1 s.
//  - any answer, and every re-request, is progress. "10 s without progress" shows Retry only while a startup step
//    (assetManager.loadBundle or director.loadScene) is waiting and no guarded file is still inside its 30 s budget.
//  - a failed startup step is NOT passed to the engine (that would leave cc.game.init rejected = frozen loading
//    screen). It is held, Retry is shown (TikTok modal; without showModal a toast + tap anywhere), and Retry issues
//    a NEW request for every waiting step. Answers of older requests are dropped. A launch scene that failed is
//    dropped from the engine file cache first (same reason as main.js v1.6).
//  - startup is complete only when the home scene's loadScene callback ran (3.x calls it after the scene's
//    components ran onLoad). opts.homeScene names it; default: the first scene loaded through director.loadScene.
//    After that the step wrappers pass straight through; the file guard stays (as in 2.4).
//  - "Loading N%" (tt.showLoading) moves with each file that loads, and is hidden when the home scene is up.
// Node-tested with a fake 3.x engine (tests/boot-3x.test.js); not yet run on a real 3.x package (待真机复测).
// R4Q5 (补查3 第 5 组 奔跑吧巨人): when the home scene is up, and one tick later, the FPS / draw-call stats are turned off
// unconditionally (cc.profiler.hideStats / cc.setDisplayStats(false)); a save or debug switch cannot leave them on.
var VERSION = '1.0';
var MARK = '__tiktokKitBoot3x';
var FILE_EXTS = ['.png', '.jpg', '.jpeg', '.webp', '.json', '.ttf', '.txt', '.plist', '.fnt', '.atlas', '.bin', '.cconb',
  '.mp3', '.ogg', '.wav', '.m4a', '.js'];
var IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tiff', '.webp', '.image'];

function rootObject() {
  return typeof globalThis !== 'undefined' ? globalThis : typeof GameGlobal !== 'undefined' ? GameGlobal
    : typeof window !== 'undefined' ? window : {};
}

function defaultClock(root) {
  return {
    now: function () { return Date.now(); },
    setTimeout: function (f, ms) { return setTimeout(f, ms); },
    clearTimeout: function (id) { clearTimeout(id); },
    setInterval: function (f, ms) { return setInterval(f, ms); },
    clearInterval: function (id) { clearInterval(id); },
    raf: typeof root.requestAnimationFrame === 'function' ? function (f) { return root.requestAnimationFrame(f); }
      : function (f) { return setTimeout(f, 16); }
  };
}

function hook(cc, sdk, opts) {
  opts = opts || {};
  var am = cc && cc.assetManager, director = cc && cc.director;
  if (!am || !director) return null;
  if (am[MARK]) return am[MARK];
  var root = opts.root || rootObject();
  var clock = opts.clock || defaultClock(root);
  var T = {stall: opts.stallMs || 10000, again: 10000, giveUp: 30000, bundleGiveUp: 9000, cap: 1000};
  var platform = sdk || (root.TTMinis && root.TTMinis.game) || root.tt || null;
  var S = {idle: 0, last: clock.now(), hidden: false, guardsWaiting: 0, started: false, retryShown: false,
    ops: [], percent: 0, shown: -1, timer: null, retryTouch: null, failedScene: '', retries: 0, failures: []};

  function safeCall(method, o) {
    if (!platform || typeof platform[method] !== 'function') return;
    try { var r = platform[method](o); if (r && typeof r.catch === 'function') r.catch(function () {}); return r; } catch (e) {}
  }
  function noteProgress() { S.idle = 0; S.last = clock.now(); }
  function showPercent() {
    if (S.started || S.retryShown) return;
    var p = Math.max(0, Math.min(99, Math.floor(S.percent)));
    if (p === S.shown) return;
    S.shown = p;
    safeCall('showLoading', {title: 'Loading ' + p + '%', mask: true});
  }
  function fileLoaded() { noteProgress(); S.percent += (95 - S.percent) * 0.08; showPercent(); }

  if (platform) {
    safeCall('onHide', function () { S.hidden = true; });
    safeCall('onShow', function () { S.hidden = false; S.last = clock.now(); });
  }

  // ---- per-file guard (main.js v1.6 bounded(), same numbers) ----
  function bounded(original, receiver, policy) {
    return function (url, options, complete) {
      var done = false, attempts = 0, waited = 0, last = clock.now();
      S.guardsWaiting++;
      function finish(error, value) {
        if (done) return;
        done = true;
        S.guardsWaiting = Math.max(0, S.guardsWaiting - 1);
        if (!error) fileLoaded();
        complete(error, value);
      }
      function again() { if (!done) { noteProgress(); attempt(); } }
      function attempt() {
        var mine = ++attempts;
        try {
          original.call(receiver, url, options, function (error, value) {
            if (done) return;
            if (!error) { finish(null, value); return; }
            if (mine !== attempts) return;
            if (attempts < policy.attempts) { clock.setTimeout(again, 500); return; }
            finish(error);
          });
        } catch (error) {
          if (mine === attempts && attempts < policy.attempts) clock.setTimeout(again, 500);
          else finish(error);
        }
      }
      function tick() {
        if (done) return;
        var now = clock.now();
        if (!S.hidden) waited += Math.min(T.cap, Math.max(0, now - last));
        last = now;
        if (policy.parallelAfter && attempts === 1 && waited >= policy.parallelAfter) again();
        if (waited >= policy.giveUp) { finish(new Error('file did not answer: ' + url)); return; }
        clock.raf(tick);
      }
      attempt();
      if (!done) clock.raf(tick);
    };
  }
  // Run at install AND before every startup step: in 3.x game.js, require('./engine-adapter') runs after
  // System.import('cc') and registers the mini-game download handlers again, replacing wrapped ones.
  function mark(fn) { try { Object.defineProperty(fn, '__kitBounded', {value: true}); } catch (e) { fn.__kitBounded = true; } return fn; }
  var decodeWrapped = null;
  function installFileGuard() {
    var downloader = am.downloader, parser = am.parser;
    if (!downloader || !downloader._downloaders || typeof downloader.register !== 'function') return;
    downloader.__kitLoadGuard = true;
    var FILE = {attempts: 2, parallelAfter: T.again, giveUp: T.giveUp};
    var BUNDLE = {attempts: 1, parallelAfter: 0, giveUp: T.bundleGiveUp};
    if ('maxRetryCount' in downloader) downloader.maxRetryCount = 0;
    FILE_EXTS.forEach(function (ext) {
      var original = downloader._downloaders[ext];
      if (typeof original === 'function' && !original.__kitBounded) downloader.register(ext, mark(bounded(original, downloader, FILE)));
    });
    var bundle = downloader._downloaders.bundle;
    if (typeof bundle === 'function' && !bundle.__kitBounded) downloader.register('bundle', mark(bounded(bundle, downloader, BUNDLE)));
    var decode = downloader.downloadDomImage;
    if (parser && typeof parser.register === 'function' && typeof decode === 'function' && decodeWrapped !== decode) {
      decodeWrapped = decode;
      var guarded = mark(bounded(decode, downloader, FILE));
      IMAGE_EXTS.forEach(function (ext) { parser.register(ext, guarded); });
    }
  }

  // ---- Retry ----
  function removeRetryTouch() {
    var canvas = root.canvas;
    if (S.retryTouch && canvas && canvas.removeEventListener) canvas.removeEventListener('touchend', S.retryTouch);
    S.retryTouch = null;
  }
  function fail(reason, error) {
    if (S.started || S.retryShown) return;
    S.retryShown = true;
    S.failures.push(reason);
    safeCall('hideLoading', {});
    try { console.error('[boot3x] startup load failed', reason, error && (error.errMsg || error.message) || error || ''); } catch (e) {}
    var used = false;
    function go() { if (used) return; used = true; retry(); }
    if (platform && typeof platform.showModal === 'function') {
      var r = safeCall('showModal', {title: 'Load failed', content: 'Could not load game assets. Try again?',
        confirmText: 'Retry', cancelText: 'Close', showCancel: true,
        success: function (res) { if (res && res.confirm) go(); }, fail: function () {}});
      if (r && typeof r.then === 'function') r.then(function (res) { if (res && res.confirm) go(); }, function () {});
      return;
    }
    safeCall('showToast', {title: 'Load failed. Tap to retry.', icon: 'none', duration: 5000});
    S.retryTouch = go;
    if (root.canvas && root.canvas.addEventListener) root.canvas.addEventListener('touchend', S.retryTouch);
  }
  function retry() {
    if (S.started) return;
    S.retries++;
    S.retryShown = false;
    removeRetryTouch();
    noteProgress();
    S.shown = -1; showPercent();
    S.ops.slice().forEach(function (op) { if (!op.done) issue(op); });
  }

  // ---- startup steps: each one owns its engine callback until it succeeds ----
  function issue(op) {
    var token = ++op.token;
    op.failed = false;
    function settle(error, value) {
      if (op.done || token !== op.token) return;  // an older request: dropped
      if (error) {
        if (S.started) { finishOp(op, error, value); return; }  // after startup the engine handles it
        op.failed = true; fail(op.name, error); return;
      }
      noteProgress();
      finishOp(op, null, value);
    }
    try { return op.run(settle, token); } catch (error) { settle(error); return false; }
  }
  function finishOp(op, error, value) {
    op.done = true;
    var i = S.ops.indexOf(op); if (i >= 0) S.ops.splice(i, 1);
    op.deliver(error, value);
  }
  function step(name, run, deliver) {
    installFileGuard();
    var op = {name: name, token: 0, done: false, failed: false, run: run, deliver: deliver};
    S.ops.push(op);
    noteProgress();
    return {op: op, result: issue(op)};
  }
  function hideStats() {
    try { if (cc.profiler && typeof cc.profiler.hideStats === 'function') cc.profiler.hideStats(); } catch (e) {}
    try { if (typeof cc.setDisplayStats === 'function') cc.setDisplayStats(false); } catch (e) {}
    try { if (cc.debug && typeof cc.debug.setDisplayStats === 'function') cc.debug.setDisplayStats(false); } catch (e) {}
  }
  function launched() {
    if (S.started) return;
    S.started = true;
    if (S.timer !== null) { clock.clearInterval(S.timer); S.timer = null; }
    removeRetryTouch();
    hideStats();
    clock.setTimeout(hideStats, 0);
    safeCall('hideLoading', {});
    // a step still held after a failure belongs to the running game now: give the engine its answer
    S.ops.slice().forEach(function (op) { if (op.failed) finishOp(op, new Error(op.name + ' failed before the home scene came up')); });
  }

  var loadBundle = am.loadBundle;
  if (typeof loadBundle === 'function') {
    am.loadBundle = function (name, options, onComplete) {
      if (S.started) return loadBundle.apply(am, arguments);
      if (typeof options === 'function' && onComplete === undefined) { onComplete = options; options = undefined; }
      var cb = typeof onComplete === 'function' ? onComplete : function () {};
      step('bundle ' + name, function (settle) {
        return options === undefined ? loadBundle.call(am, name, settle) : loadBundle.call(am, name, options, settle);
      }, function (error, bundle) { cb(error, bundle); });
    };
  }

  function releaseFailedScene(sceneName) {
    try {
      var info = null;
      if (am.bundles && typeof am.bundles.find === 'function') {
        am.bundles.find(function (b) { info = b && typeof b.getSceneInfo === 'function' ? b.getSceneInfo(sceneName) : null; return !!info; });
      }
      if (!info || !info.uuid) return;
      var id = info.uuid + '@import';
      if (am._files && typeof am._files.remove === 'function') am._files.remove(id);
      if (am._parsed && typeof am._parsed.remove === 'function') am._parsed.remove(id);
    } catch (error) { try { console.error('[boot3x] release failed scene', error); } catch (e) {} }
  }

  var loadScene = director.loadScene;
  var homeScene = opts.homeScene || '';
  if (typeof loadScene === 'function') {
    director.loadScene = function (sceneName, onLaunched, onUnloaded) {
      if (S.started) return loadScene.apply(director, arguments);
      if (!homeScene) homeScene = sceneName;
      var cb = typeof onLaunched === 'function' ? onLaunched : null;
      var s = step('scene ' + sceneName, function run(settle, token) {
        // a stuck earlier request is released by the file guard: wait for it instead of starting a second one
        if (token > 1 && director._loadingScene) {
          clock.setTimeout(function () { if (s && !s.op.done && s.op.token === token) run(settle, token); }, 500);
          return true;
        }
        if (S.failedScene === sceneName) { S.failedScene = ''; releaseFailedScene(sceneName); }
        var found = loadScene.call(director, sceneName, function (error, scene) {
          if (error) S.failedScene = sceneName;  // recorded even when this request was superseded (main.js v1.6)
          settle(error, scene);
        }, onUnloaded);
        if (found === false) settle(new Error('scene not found or another scene is loading: ' + sceneName));
        return found;
      }, function (error, scene) {
        if (!error && sceneName === homeScene) launched();
        if (cb) cb(error, scene);
      });
      return s.result;
    };
  }

  // ---- 10 s no-progress watchdog (foreground only, one tick adds at most 1 s) ----
  S.timer = clock.setInterval(function () {
    var now = clock.now();
    if (S.started) return;
    if (S.hidden || S.retryShown) { S.last = now; return; }
    S.idle += Math.min(T.cap, Math.max(0, now - S.last));
    S.last = now;
    if (S.idle > T.stall && !S.guardsWaiting && S.ops.length) fail('stalled');
  }, 1000);

  installFileGuard();
  showPercent();
  var api = {
    version: VERSION,
    retry: function () { retry(); },
    status: function () {
      return {started: S.started, retryShown: S.retryShown, idle: S.idle, waiting: S.ops.map(function (o) { return o.name; }),
        percent: Math.floor(S.percent), retries: S.retries, failures: S.failures.slice(), guardsWaiting: S.guardsWaiting};
    }
  };
  try { Object.defineProperty(am, MARK, {value: api, enumerable: false, configurable: true}); } catch (e) { am[MARK] = api; }
  return api;
}

// install(cc, sdk, opts): cc = the engine module when it is already loaded; null in game.js (before
// System.warmup), where the guard hooks the first System.import('cc'). Returns the guard (cc given), or
// {pending: true} while waiting for the engine, or null when there is nothing to hook.
function install(cc, sdk, opts) {
  opts = opts || {};
  if (cc && cc.assetManager) return hook(cc, sdk, opts);
  var root = opts.root || rootObject();
  var System = opts.System || root.System;
  if (!System || typeof System.import !== 'function') return null;
  if (System[MARK]) return System[MARK];
  var original = System.import, state = {pending: true, guard: null};
  System.import = function (id) {
    var p = original.apply(this, arguments);
    if (state.pending && /(^|\/)cc(\.js)?$/.test(String(id)) && p && typeof p.then === 'function') {
      return p.then(function (engine) {
        if (state.pending) {
          state.pending = false;
          try { state.guard = hook(engine, sdk, opts); } catch (error) { try { console.error('[boot3x] install', error); } catch (e) {} }
        }
        return engine;
      });
    }
    return p;
  };
  try { Object.defineProperty(System, MARK, {value: state, enumerable: false, configurable: true}); } catch (e) {}
  return state;
}

module.exports = {install: install, version: VERSION};
