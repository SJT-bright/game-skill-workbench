'use strict';
// Rewarded-ad timing cases (v7.5, D8 item 1 / D9; rule decided by Saul 2026-10-29 03:18 PDT, unchanged from v7.4):
//   - the request phase (until show() resolves) times out after 15 s, counting foreground time only;
//   - after show() resolves there is no timeout; reward only on onClose(res) with res.isEnded === true;
//   - 30 s into playback with no callback the X becomes available; X / timeout / cancel release the session at once;
//   - a video that starts or ends after a timeout, X or cancel never grants.
// Cases: long200, late16, bgplay, bgload, hang, nocallback. Default numbers are used (no timing overrides).
// Usage: node tests/rewarded-timing.test.js [/path/to/RewardedService.js]   (default: this kit's file)
// The file under test is copied into a temporary folder with this kit's PlatformConfig.js; nothing is written
// next to it.
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path');
var KIT = path.join(__dirname, '..', 'assets', 'tiktok-platform');
var target = path.resolve(process.argv[2] || path.join(KIT, 'RewardedService.js'));
var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kit-rewarded-'));
fs.copyFileSync(target, path.join(dir, 'RewardedService.js'));
fs.copyFileSync(path.join(KIT, 'PlatformConfig.js'), path.join(dir, 'PlatformConfig.js'));
// A fresh module per case: the one-live-session lock is module-global, so cases never leak into each other.
function freshService() {
  Object.keys(require.cache).forEach(function (k) { if (k.indexOf(dir) === 0) delete require.cache[k]; });
  return require(path.join(dir, 'RewardedService.js'));
}
process.on('exit', function () { fs.rmSync(dir, {recursive: true, force: true}); });
var results = [];

function flush() { var p = Promise.resolve(); for (var i = 0; i < 6; i++) p = p.then(function () {}); return p; }

// A TikTok SDK stand-in on a fake clock. at(ms, fn) schedules an SDK/user event; run(ms) advances in 100 ms
// steps (the service's own poll interval), firing due events and calling service.tick() each step.
function world() {
  var w = {time: 0, events: [], ads: [], hide: [], show: [], exitNotices: 0, offs: []};
  w.sdk = {
    canIUse: function () { return true; },
    onHide: function (fn) { w.hide.push(fn); }, offHide: function (fn) { w.hide = w.hide.filter(function (f) { return f !== fn; }); },
    onShow: function (fn) { w.show.push(fn); }, offShow: function (fn) { w.show = w.show.filter(function (f) { return f !== fn; }); },
    createRewardedVideoAd: function () {
      var ad = {h: {}, startResolve: null,
        onClose: function (fn) { ad.h.close = fn; }, onError: function (fn) { ad.h.error = fn; },
        offClose: function (fn) { if (ad.h.close === fn) { ad.h.close = null; w.offs.push('close'); } },
        offError: function (fn) { if (ad.h.error === fn) { ad.h.error = null; w.offs.push('error'); } },
        show: function () { return new Promise(function (resolve) { ad.startResolve = resolve; }); },
        start: function () { if (ad.startResolve) ad.startResolve(); },
        close: function (res) { if (ad.h.close) ad.h.close(res); }};
      w.ads.push(ad); return ad;
    }
  };
  var RewardedService = freshService();
  w.service = new RewardedService({getSDK: function () { return w.sdk; }, now: function () { return w.time; }, autoPoll: false,
    onExitAvailable: function () { w.exitNotices++; }});
  w.at = function (ms, fn) { w.events.push({at: ms, fn: fn}); };
  // App lifecycle as a game wired per README: SDK onHide/onShow listeners plus the service's onHide()/onShow().
  w.background = function () { w.hide.slice().forEach(function (f) { f(); }); if (typeof w.service.onHide === 'function') w.service.onHide(); };
  w.foreground = function () { w.show.slice().forEach(function (f) { f(); }); if (typeof w.service.onShow === 'function') w.service.onShow(); };
  w.request = function () {
    var r = {result: null, at: null};
    r.promise = w.service.request({placementKey: 'double_coins', ownerId: 'result',
      onExitAvailable: function () { w.exitNotices++; }}).then(function (x) { r.result = x; r.at = w.time; return x; });
    return r;
  };
  w.run = async function (until) {
    await flush();
    while (w.time < until) {
      w.time += 100;
      var due = w.events.filter(function (e) { return e.at <= w.time; });
      w.events = w.events.filter(function (e) { return e.at > w.time; });
      for (var i = 0; i < due.length; i++) { due[i].fn(); await flush(); }
      w.service.tick(); await flush();
    }
  };
  return w;
}
async function test(name, run) {
  try { await run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
function released(w, label) {
  assert.strictEqual(w.service.isNativeBusy(), false, label + ': session must be released at once');
  var next = w.request();
  return flush().then(function () {
    assert.notStrictEqual(next.result && next.result.status, 'busy', label + ': the next request must not be busy');
    assert.strictEqual(w.ads.length >= 2, true, label + ': the next request must create a new ad');
  });
}

(async function () {
  await test('long200_video_of_200_s_completed_is_rewarded', async function () {
    var w = world(), r = w.request();
    w.at(1000, function () { w.ads[0].start(); });
    w.at(201000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(200900);
    assert.strictEqual(r.result, null, 'no result while the 200 s video plays (no playback timeout)');
    await w.run(201500);
    assert(r.result, 'settles on onClose'); assert.strictEqual(r.result.status, 'completed'); assert.strictEqual(r.result.rewarded, true);
  });

  await test('late16_playback_starting_after_16_s_times_out_at_15_s_and_never_grants', async function () {
    var w = world(), r = w.request();
    w.at(16000, function () { w.ads[0].start(); });
    w.at(46000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(15100);
    assert(r.result, 'request phase must time out at 15 s'); assert.strictEqual(r.result.status, 'timeout');
    assert.strictEqual(r.result.rewarded, false);
    assert(w.offs.indexOf('close') >= 0, 'onClose unbound at the timeout');
    await released(w, 'late16');
    await w.run(47000);
    assert.strictEqual(r.result.status, 'timeout', 'a video that starts after the timeout never grants');
    assert.strictEqual(r.result.rewarded, false);
  });

  await test('bgplay_background_during_playback_then_completed_is_rewarded', async function () {
    var w = world(), r = w.request();
    w.at(1000, function () { w.ads[0].start(); });
    w.at(5000, function () { w.background(); });
    w.at(185000, function () { w.foreground(); });
    w.at(190000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(189000);
    assert.strictEqual(r.result, null, 'background during playback neither cancels nor times out');
    await w.run(191000);
    assert(r.result); assert.strictEqual(r.result.status, 'completed'); assert.strictEqual(r.result.rewarded, true);
  });

  await test('bgload_background_while_loading_does_not_count_toward_15_s', async function () {
    var w = world(), r = w.request();
    w.at(2000, function () { w.background(); });
    w.at(62000, function () { w.foreground(); });
    w.at(70000, function () { w.ads[0].start(); });      // 2 s + 8 s = 10 s of foreground request time
    w.at(100000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(69900);
    assert.strictEqual(r.result, null, '60 s in the background must not time out the request');
    await w.run(101000);
    assert(r.result); assert.strictEqual(r.result.status, 'completed'); assert.strictEqual(r.result.rewarded, true);
  });

  await test('hang_show_never_resolves_times_out_at_15_s_and_releases', async function () {
    var w = world(), r = w.request();
    await w.run(14900);
    assert.strictEqual(r.result, null, 'no timeout before 15 s');
    await w.run(15100);
    assert(r.result); assert.strictEqual(r.result.status, 'timeout'); assert.strictEqual(r.result.rewarded, false);
    assert(w.offs.indexOf('close') >= 0 && w.offs.indexOf('error') >= 0, 'callbacks unbound at the timeout');
    await released(w, 'hang');
    w.ads[0].start(); w.ads[0].close({isEnded: true}); await flush();
    assert.strictEqual(r.result.status, 'timeout', 'an old video that ends after the timeout never grants');
  });

  await test('nocallback_no_timeout_after_show_X_after_30_s_and_no_late_grant', async function () {
    var w = world(), r = w.request();
    w.at(1000, function () { w.ads[0].start(); });
    await w.run(30900);
    assert.strictEqual(typeof w.service.exitAvailable, 'function', 'service must offer exitAvailable()/exit() for the X');
    assert.strictEqual(w.service.exitAvailable(), false, 'no X before 30 s of playback');
    await w.run(31100);
    assert.strictEqual(w.service.exitAvailable(), true, 'X available 30 s after playback started');
    assert.strictEqual(w.exitNotices, 1, 'onExitAvailable fired once');
    await w.run(300000);
    assert.strictEqual(r.result, null, 'no timeout after show(): still waiting at 300 s');
    w.service.exit(); await flush();
    assert(r.result); assert.strictEqual(r.result.status, 'cancelled'); assert.strictEqual(r.result.rewarded, false);
    assert(w.offs.indexOf('close') >= 0, 'callbacks unbound at X');
    await released(w, 'nocallback');
    w.ads[0].close({isEnded: true}); await flush();
    assert.strictEqual(r.result.status, 'cancelled', 'a video that ends after X never grants');
  });

  await test('cancel_then_late_end_never_grants', async function () {
    var w = world(), r = w.request();
    w.at(1000, function () { w.ads[0].start(); });
    w.at(3000, function () { w.service.cancelOwner('result'); });
    await w.run(3500);
    assert(r.result); assert.strictEqual(r.result.status, 'cancelled'); assert.strictEqual(r.result.rewarded, false);
    await released(w, 'cancel');
    w.ads[0].close({isEnded: true}); await flush();
    assert.strictEqual(r.result.rewarded, false, 'a video that ends after cancel never grants');
  });

  await test('close_without_isEnded_true_never_rewards', async function () {
    var values = [undefined, {}, {isEnded: false}, {isEnded: 1}, {isEnded: 'true'}];
    for (var i = 0; i < values.length; i++) {
      var w = world(), r = w.request();
      w.at(1000, function () { w.ads[0].start(); });
      await w.run(1500);
      w.ads[0].close(values[i]); await flush();
      assert(r.result); assert.strictEqual(r.result.rewarded, false, JSON.stringify(values[i]) + ' must not reward');
      assert.strictEqual(r.result.status, 'cancelled');
    }
  });

  var failed = results.filter(function (x) { return x.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'rewarded-timing', file: target, passed: results.length - failed.length,
    failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
})();
