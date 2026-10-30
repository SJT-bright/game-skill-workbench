"use strict";

// Cocos Creator 2.4.15 ByteDance bootstrap with an explicit resources
// subpackage wait. This file is copied by Creator from build-templates.
// TikTok Platform Kit v1.1: MetalMaster r5 boot (passed on device) + one line that installs the
// touch-coordinate fix (StarPop / Double Jump Duo / Run Home / Chase Girl). v1.1: stall limit 20 s -> 10 s
// (skill rule: <= 10 s without progress, then Retry). Copy unchanged.
// v1.2 (MergeShot2048 v81 -> v82/v84 real-iPhone findings; pending device retest):
//  - per-file load guard: a package file that has not answered after 10 s of foreground time is requested
//    again and the first answer wins; an error is retried once; only 30 s without an answer fails the file.
//    Background time is not counted and one frame adds at most 1 s.
//  - the launch scene is part of the watched chain: a scene error or 10 s without progress shows Retry,
//    and that Retry only reloads the scene (the engine is never started twice).
//  - an exception anywhere in the startup chain shows Retry instead of a frozen loading screen.
//  - Retry skips steps that already finished (scripts, resources subpackage).
// v1.3 (kit 2.0, v7.7; Node-tested, 待真机复测):
//  - installs ./storage-guard.js on cc.sys.localStorage before any game script is loaded;
//  - sends ONE silent login at startup and never waits for it (a missing API, a throw, fail or a
//    rejected Promise change nothing);
//  - WebP exception only: when the package sets __TIKTOK_KIT_WEBP_PROBE__ = true (finalize
//    --keep-webp-exception), every start and every Retry first runs ./webp-decode-probe.js.
// v1.4 (v7.7 W-D3; host-tested on 2.4.4 / 2.4.6 / 2.4.13 / 2.4.15, 待真机复测): the image-decode half of the
//  load guard now reaches the real image parser (downloader.downloadDomImage); v1.2-v1.3 looked for
//  parser._parsers, which no 2.4 engine has, so a decode that never answered was never requested again.
//  A Retry tapped after the scene came up no longer leaves a masked "Loading 95%" over the game.
// v1.5 (v7.7 W-F1a; Node-tested + host-tested on 2.4.13, 待真机复测): the numbers stay (10 s re-request per file,
//  30 s file fail, background not counted). A per-file re-request counts as progress, and the 10 s "no progress"
//  watchdog waits while a guarded file is still inside its own 30 s budget: one stuck file shows Retry only when
//  it really fails, and no "Load failed" dialog is left over a home page that loaded after a re-request (v1.4: the
//  two 10 s clocks raced and the Retry dialog usually won by about 1 s at ~1 frame per second).
// v1.6 (v7.7 W-G1; Node-tested + host-tested, 待真机复测): the first Retry after a failed launch scene works. A scene
//  that failed after it was deserialized (an image timed out) stayed in the engine's file cache, so the first Retry
//  deserialized it again and failed at once; Retry now drops that cache entry before loading the scene again.
//  Timer numbers unchanged.
window.boot = function () {
  var settings = window._CCSettings;
  window._CCSettings = undefined;
  try { require('./touch-coordinates').install(cc); } catch (touchError) { console.error('touch fix', touchError); }
  var platform = typeof TTMinis !== 'undefined' && TTMinis.game
    ? TTMinis.game : typeof tt !== 'undefined' ? tt : null;
  try { require('./storage-guard')(cc, platform); } catch (storageError) { console.error('storage guard', storageError); }
  var webpProbe = null;
  if (window.__TIKTOK_KIT_WEBP_PROBE__ === true) {
    try { webpProbe = require('./webp-decode-probe'); } catch (probeError) { console.error('webp probe', probeError); }
  }
  var STALL_MS = 10000;
  var generation = 0;
  var loadingTimer = null;
  var idle = 0;
  var lastTick = 0;
  var hiddenAt = 0;
  var retryTouch = null;
  var retryShown = false;
  var setupDone = false;
  var scriptsDone = false;
  var subpackageDone = false;
  var engineRunning = false;
  var sceneUp = false;
  var option = null;
  var guardsWaiting = 0;  // guarded file requests still inside their own 30 s budget (v1.5)
  var sceneFailed = false;  // a launch-scene load reported an error (any attempt, even a superseded one) (v1.6)

  function safeCall(method, options) {
    if (!platform || typeof platform[method] !== 'function') return;
    try {
      var result = platform[method](options);
      if (result && typeof result.catch === 'function') result.catch(function () {});
      return result;
    } catch (_error) {}
  }

  // Any real answer (stage change, download progress, a file that loaded) resets the stall clock.
  function noteProgress() {
    idle = 0;
    lastTick = Date.now();
  }

  function visibleProgress(percent) {
    percent = Math.max(0, Math.min(100, Math.floor(percent)));
    noteProgress();
    safeCall('showLoading', {title: 'Loading ' + percent + '%', mask: true});
  }

  function removeRetryTouch() {
    if (retryTouch && window.canvas && window.canvas.removeEventListener) {
      window.canvas.removeEventListener('touchend', retryTouch);
    }
    retryTouch = null;
  }

  function clearAttempt() {
    if (loadingTimer) clearInterval(loadingTimer);
    loadingTimer = null;
    removeRetryTouch();
  }

  function fail(reason, token, error) {
    if (token !== generation || retryShown || sceneUp) return;
    retryShown = true;
    clearAttempt();
    safeCall('hideLoading', {});
    console.error('startup load failed', reason, error && error.message ? error.message : error || '');
    var retry = function () {
      if (token !== generation) return;
      removeRetryTouch();
      start();
    };
    if (platform && typeof platform.showModal === 'function') {
      var acted = false;
      var modalResult = safeCall('showModal', {
        title: 'Load failed', content: 'Could not load game assets. Try again?',
        confirmText: 'Retry', cancelText: 'Close',
        success: function (res) {
          if (acted) return;
          acted = true;
          if (res && res.confirm) retry();
        },
        fail: function () { acted = true; }
      });
      if (modalResult && typeof modalResult.then === 'function') {
        modalResult.then(function (res) {
          if (acted) return;
          acted = true;
          if (res && res.confirm) retry();
        }, function () {});
      }
      return;
    }
    safeCall('showToast', {title: 'Load failed. Tap to retry.', icon: 'none', duration: 5000});
    retryTouch = retry;
    if (window.canvas && window.canvas.addEventListener) {
      window.canvas.addEventListener('touchend', retryTouch);
    }
  }

  function onHide() { hiddenAt = Date.now(); }
  function onShow() {
    hiddenAt = 0;
    lastTick = Date.now();
  }
  if (platform && platform.onHide) safeCall('onHide', onHide);
  if (platform && platform.onShow) safeCall('onShow', onShow);

  // One silent login (TikTok's publish scan asks for the Login API). Deferred and never awaited.
  function noop() {}
  if (!window.__tiktokKitLoginSent && platform && typeof platform.login === 'function') {
    window.__tiktokKitLoginSent = true;
    try { setTimeout(function () { safeCall('login', {success: noop, fail: noop, complete: noop}); }, 0); } catch (_error) {}
  }

  // Per-file load guard (MergeShot2048 v82 native-load-guard.js). v81 failed a file after one 8 s fatal
  // timeout with no retry and dropped late answers, so home-page images never appeared.
  function installLoadGuard() {
    var manager = cc.assetManager;
    var downloader = manager && manager.downloader, parser = manager && manager.parser;
    if (!downloader || !downloader._downloaders || downloader.__kitLoadGuard) return;
    downloader.__kitLoadGuard = true;
    var raf = typeof requestAnimationFrame === 'function' ? requestAnimationFrame
      : function (f) { return setTimeout(f, 16); };
    var FILE = {attempts: 2, parallelAfter: 10000, giveUp: 30000};
    // A bundle request is not duplicated; a silent one is released before the 10 s stall Retry, so the
    // Retry starts a fresh request instead of joining the stuck one.
    var BUNDLE = {attempts: 1, parallelAfter: 0, giveUp: 9000};
    function bounded(original, receiver, policy) {
      return function (url, options, complete) {
        var done = false, attempts = 0, waited = 0, last = Date.now();
        guardsWaiting++;
        function finish(error, value) {
          if (done) return;
          done = true;
          guardsWaiting = Math.max(0, guardsWaiting - 1);
          if (!error) noteProgress();
          complete(error, value);
        }
        // v1.5: asking again is progress (the 10 s watchdog restarts from it)
        function again() { if (!done) { noteProgress(); attempt(); } }
        function attempt() {
          var mine = ++attempts;
          try {
            original.call(receiver, url, options, function (error, value) {
              if (done) return;                       // first answer already won
              if (!error) { finish(null, value); return; }
              if (mine !== attempts) return;          // a newer attempt is still running
              if (attempts < policy.attempts) { setTimeout(again, 500); return; }
              finish(error);
            });
          } catch (error) {
            if (mine === attempts && attempts < policy.attempts) setTimeout(again, 500);
            else finish(error);
          }
        }
        function tick() {
          if (done) return;
          var now = Date.now();
          if (!hiddenAt) waited += Math.min(1000, Math.max(0, now - last));
          last = now;
          if (policy.parallelAfter && attempts === 1 && waited >= policy.parallelAfter) again();
          if (waited >= policy.giveUp) { finish(new Error('file did not answer: ' + url)); return; }
          raf(tick);
        }
        attempt();
        if (!done) raf(tick);
      };
    }
    downloader.maxRetryCount = 0;  // retries are owned by bounded()
    ['.png', '.jpg', '.jpeg', '.webp', '.json', '.ttf', '.txt', '.plist', '.fnt', '.atlas', '.bin', '.mp3', '.ogg', '.wav', '.m4a']
      .forEach(function (ext) {
        var original = downloader._downloaders[ext];
        if (typeof original === 'function') downloader.register(ext, bounded(original, downloader, FILE));
      });
    if (typeof downloader._downloaders.bundle === 'function') {
      downloader.register('bundle', bounded(downloader._downloaders.bundle, downloader, BUNDLE));
    }
    // v1.4: on a mini-game the image is decoded in the PARSE stage. Every 2.4 ByteDance adapter (2.4.4, 2.4.6,
    // 2.4.13, 2.4.15) registers downloader.downloadDomImage as the parser of these extensions, and that function
    // has no timeout. The engine keeps its parser table private (no parser._parsers), so the same function is
    // registered again, bounded. The handler is wrapped, not parser.parse: parse() joins a second request for the
    // same id to the stuck one and only the handler's answer clears it, so a give-up here lets a Retry start fresh.
    var decode = downloader.downloadDomImage;
    if (parser && typeof parser.register === 'function' && typeof decode === 'function') {
      ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.tiff', '.webp', '.image'].forEach(function (ext) {
        parser.register(ext, bounded(decode, downloader, FILE));
      });
    }
  }

  function setup() {
    cc.view.enableRetina(true);
    cc.view.resizeWithBrowserSize(true);
    cc.assetManager.init({
      bundleVers: settings.bundleVers,
      subpackages: settings.subpackages,
      remoteBundles: settings.remoteBundles,
      server: settings.server,
      subContextRoot: settings.subContextRoot
    });
    installLoadGuard();
    option = {
      id: 'GameCanvas',
      debugMode: settings.debug ? cc.debug.DebugMode.INFO : cc.debug.DebugMode.ERROR,
      showFPS: !__globalAdapter.isSubContext && settings.debug,
      frameRate: 60,
      groupList: settings.groupList,
      collisionMatrix: settings.collisionMatrix
    };
    // A scene that comes up through any attempt (even a late one) ends the loading screen.
    if (cc.Director && cc.Director.EVENT_AFTER_SCENE_LAUNCH && cc.director && typeof cc.director.once === 'function') {
      cc.director.once(cc.Director.EVENT_AFTER_SCENE_LAUNCH, launched);
    }
  }

  function launched() {
    if (sceneUp) return;
    sceneUp = true;
    clearAttempt();
    safeCall('hideLoading', {});
    console.log('Success to load scene: ' + settings.launchScene);
  }

  // v1.6: a launch scene that failed AFTER its JSON was deserialized (a dependency such as an image timed out)
  // leaves that JSON in cc.assetManager's file cache, already rewritten in place by the deserializer. The engine
  // drops the entry only on success or on a parse error, and never keeps a scene in its parsed cache, so the next
  // loadScene deserializes the same rewritten JSON again and fails at once (debug engines log "Can not deserialize
  // the same JSON data again"); only the Retry after that one worked. Same code in 2.4.4, 2.4.6, 2.4.13, 2.4.15
  // (asset-manager/load.js + parser.js). Dropping the entry makes the next load read the scene file fresh.
  function releaseFailedScene() {
    var manager = cc.assetManager;
    if (!manager || !manager.bundles || typeof manager.bundles.find !== 'function') return;
    try {
      var info = null;
      manager.bundles.find(function (bundle) {
        info = bundle && typeof bundle.getSceneInfo === 'function' ? bundle.getSceneInfo(settings.launchScene) : null;
        return !!info;
      });
      if (!info || !info.uuid) return;
      var id = info.uuid + '@import';
      if (manager._files && typeof manager._files.remove === 'function') manager._files.remove(id);
      if (manager._parsed && typeof manager._parsed.remove === 'function') manager._parsed.remove(id);
    } catch (error) { console.error('release failed scene', error); }
  }

  function start() {
    // A Retry tapped after the scene already came up (its dialog appeared a moment before a late answer) must not
    // put a masked "Loading 95%" back over the running game: v1.2-v1.3 showed it and never hid it.
    if (sceneUp) { clearAttempt(); safeCall('hideLoading', {}); return; }
    var token = ++generation;
    retryShown = false;
    clearAttempt();
    visibleProgress(engineRunning ? 95 : 0);
    loadingTimer = setInterval(function () {
      var now = Date.now();
      if (token !== generation || hiddenAt) { lastTick = now; return; }
      idle += Math.min(1000, Math.max(0, now - lastTick));  // a long frame counts as at most 1 s
      lastTick = now;
      // v1.5: while a guarded file is still inside its 30 s budget, that file owns the wait (it re-requests at
      // 10 s and fails at 30 s); its failure reaches fail() through the step's error callback.
      if (idle > STALL_MS && !guardsWaiting) fail('stalled', token);
    }, 1000);

    function current() { return token === generation && !retryShown; }
    // Every callback in the chain runs inside this: an exception shows Retry, never a frozen screen.
    function guarded(name, fn) {
      return function () {
        if (!current()) return;
        try { return fn.apply(this, arguments); } catch (error) { fail(name, token, error); }
      };
    }
    function loadBundle(name, next) {
      cc.assetManager.loadBundle(name, guarded(name, function (error) {
        if (error) fail(name, token, error);
        else next();
      }));
    }
    var loadScene = guarded('scene', function () {
      if (sceneUp) return;
      // A stuck earlier scene request is released by the file guard; wait for it instead of starting a second one.
      if (cc.director._loadingScene) { setTimeout(loadScene, 500); return; }
      if (sceneFailed) { sceneFailed = false; releaseFailedScene(); }
      var sceneDone = guarded('scene', function (error) {
        if (error) { fail('scene', token, error); return; }
        launched();
      });
      var found = cc.director.loadScene(settings.launchScene, function (error) {
        if (error) sceneFailed = true;  // v1.6: recorded even when this attempt was already superseded
        return sceneDone.apply(this, arguments);
      });
      if (found === false) fail('scene', token, 'launch scene not found');
    });
    var finish = guarded('engine', function () {
      visibleProgress(95);
      engineRunning = true;
      cc.game.run(option, loadScene);
    });
    var loadEngine = guarded('main', function () {
      visibleProgress(90);
      loadBundle(cc.AssetManager.BuiltinBundleName.MAIN, finish);
    });
    var loadResources = guarded('resources', function () {
      visibleProgress(75);
      loadBundle(cc.AssetManager.BuiltinBundleName.RESOURCES, loadEngine);
    });
    var loadSubpackage = guarded('resources subpackage', function () {
      var present = settings.subpackages && settings.subpackages.indexOf('resources') !== -1;
      if (subpackageDone || !present || !platform || typeof platform.loadSubpackage !== 'function') {
        loadResources();
        return;
      }
      var settled = false;
      function success() {
        if (settled || !current()) return;
        settled = true;
        subpackageDone = true;
        loadResources();
      }
      function error() {
        if (settled || !current()) return;
        settled = true;
        fail('resources subpackage', token);
      }
      try {
        var task = platform.loadSubpackage({name: 'resources', success: success, fail: error, complete: function () {}});
        if (task && task.onProgressUpdate) task.onProgressUpdate(function (res) {
          if (current() && res && typeof res.progress === 'number') {
            visibleProgress(10 + res.progress * 0.6);
          }
        });
        if (task && typeof task.then === 'function') task.then(success, error);
      } catch (_error) { error(); }
    });
    var loadInternal = guarded('internal', function () {
      visibleProgress(5);
      loadBundle(cc.AssetManager.BuiltinBundleName.INTERNAL, loadSubpackage);
    });

    var begin = guarded('startup', function () {
      if (engineRunning) { loadScene(); return; }  // Retry after the engine started: only the scene again
      if (scriptsDone) { loadInternal(); return; }
      cc.assetManager.loadScript((settings.jsList || []).map(function (x) {
        return 'src/' + x;
      }), guarded('scripts', function (error) {
        if (error) { fail('scripts', token, error); return; }
        scriptsDone = true;
        loadInternal();
      }));
    });

    try {
      if (!setupDone) { setup(); setupDone = true; }
      var caps = cc.sys && cc.sys.capabilities;
      if (webpProbe && caps && !caps.webp) { visibleProgress(engineRunning ? 95 : 2); webpProbe(window, begin); return; }
      begin();
    } catch (error) { fail('startup', token, error); }
  }

  start();
};
