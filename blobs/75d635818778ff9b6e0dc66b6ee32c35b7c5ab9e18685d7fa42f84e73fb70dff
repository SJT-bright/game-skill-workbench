"use strict";

// Cocos Creator 2.4.15 ByteDance bootstrap with an explicit resources
// subpackage wait. This file is copied by Creator from build-templates.
// TikTok Platform Kit v1.1: MetalMaster r5 boot (passed on device) + one line that installs the
// touch-coordinate fix (StarPop / Double Jump Duo / Run Home / Chase Girl). v1.1: stall limit 20 s -> 10 s
// (skill rule: <= 10 s without progress, then Retry). Copy unchanged.
window.boot = function () {
  var settings = window._CCSettings;
  window._CCSettings = undefined;
  try { require('./touch-coordinates').install(cc); } catch (touchError) { console.error('touch fix', touchError); }
  var platform = typeof TTMinis !== 'undefined' && TTMinis.game
    ? TTMinis.game : typeof tt !== 'undefined' ? tt : null;
  var generation = 0;
  var loadingTimer = null;
  var lastProgress = 0;
  var hiddenAt = 0;
  var retryTouch = null;
  var retryShown = false;

  function safeCall(method, options) {
    if (!platform || typeof platform[method] !== 'function') return;
    try {
      var result = platform[method](options);
      if (result && typeof result.catch === 'function') result.catch(function () {});
      return result;
    } catch (_error) {}
  }

  function visibleProgress(percent) {
    percent = Math.max(0, Math.min(100, Math.floor(percent)));
    lastProgress = Date.now();
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

  function fail(reason, token) {
    if (token !== generation || retryShown) return;
    retryShown = true;
    clearAttempt();
    safeCall('hideLoading', {});
    console.error('startup load failed', reason);
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
    if (hiddenAt) lastProgress += Date.now() - hiddenAt;
    hiddenAt = 0;
  }
  if (platform && platform.onHide) safeCall('onHide', onHide);
  if (platform && platform.onShow) safeCall('onShow', onShow);

  cc.view.enableRetina(true);
  cc.view.resizeWithBrowserSize(true);
  cc.assetManager.init({
    bundleVers: settings.bundleVers,
    subpackages: settings.subpackages,
    remoteBundles: settings.remoteBundles,
    server: settings.server,
    subContextRoot: settings.subContextRoot
  });

  var option = {
    id: 'GameCanvas',
    debugMode: settings.debug ? cc.debug.DebugMode.INFO : cc.debug.DebugMode.ERROR,
    showFPS: !__globalAdapter.isSubContext && settings.debug,
    frameRate: 60,
    groupList: settings.groupList,
    collisionMatrix: settings.collisionMatrix
  };

  function start() {
    var token = ++generation;
    retryShown = false;
    clearAttempt();
    visibleProgress(0);
    loadingTimer = setInterval(function () {
      if (token !== generation || hiddenAt) return;
      if (Date.now() - lastProgress > 10000) fail('stalled', token);
    }, 1000);

    function current() { return token === generation && !retryShown; }
    function loadBundle(name, next) {
      cc.assetManager.loadBundle(name, function (error) {
        if (!current()) return;
        if (error) fail(name, token);
        else next();
      });
    }
    function finish() {
      if (!current()) return;
      visibleProgress(100);
      clearAttempt();
      safeCall('hideLoading', {});
      cc.game.run(option, function () {
        cc.director.loadScene(settings.launchScene, null, function () {
          console.log('Success to load scene: ' + settings.launchScene);
        });
      });
    }
    function loadEngine() {
      if (!current()) return;
      visibleProgress(90);
      loadBundle(cc.AssetManager.BuiltinBundleName.MAIN, finish);
    }
    function loadResources() {
      if (!current()) return;
      visibleProgress(75);
      loadBundle(cc.AssetManager.BuiltinBundleName.RESOURCES, loadEngine);
    }
    function loadSubpackage() {
      if (!current()) return;
      var present = settings.subpackages && settings.subpackages.indexOf('resources') !== -1;
      if (!present || !platform || typeof platform.loadSubpackage !== 'function') {
        loadResources();
        return;
      }
      var settled = false;
      function success() {
        if (settled || !current()) return;
        settled = true;
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
    }
    cc.assetManager.loadScript((settings.jsList || []).map(function (x) {
      return 'src/' + x;
    }), function (error) {
      if (!current()) return;
      if (error) { fail('scripts', token); return; }
      visibleProgress(5);
      loadBundle(cc.AssetManager.BuiltinBundleName.INTERNAL, loadSubpackage);
    });
  }

  start();
};
