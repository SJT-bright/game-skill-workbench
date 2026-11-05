'use strict';
// node tests/rewarded-guard.test.js   (a few seconds; no browser, no build)
// parts/rewarded-guard.js (plan P01 point 2). Three fixtures taken from real games, each run on a fake TikTok
// SDK and a virtual clock with and WITHOUT the guard, on the v7.4 cases late16 / hang / nocallback (X, then
// ask again) / normal / long200:
//   A 埃及宝石 HexPlatform.js rewarded(): 180 s timer that never releases the shared lease, X keeps the lease.
//   B 拇指弹球 v6 old RewardedService.js (kit_versions sha 04121e95): timeout settles UI but keeps the lock.
//   C 搭桥小能手 TTSdk.js showVideoAd + sdk.ts wrapper: own multi-platform SDK, no timeout, no X, one ad object.
// Without the guard every fixture must fail late16 and nocallback; with it none may lock or grant late.
// Then the CURRENT kit RewardedService.js is run through the guard (rewarded-timing.test.js, unmarked and with
// the __tiktokKitRewardedDirect mark) and ad-boost AdBoostKit.test.js (Kit.runAd -> RewardedService): same
// results as without the guard. A preload mode (REWARDED_GUARD_PRELOAD=1, node -r this file) puts the guard
// under every RewardedService instance a child test creates.
// D2 (2026-11-04): the kit RewardedService marks its own create call; the D2 cases show 11.12's unmarked file
// (kit_versions 7a446726) losing a reward after 60 s in the background and the current file granting it.
var path = require('path');
var GUARD = path.join(__dirname, '..', 'parts', 'rewarded-guard.js');
var install = require(GUARD);

if (process.env.REWARDED_GUARD_PRELOAD === '1') {
  // Preload: wrap every RewardedService constructor a child test requires, so the SDK object it gets from
  // getSDK() has the guard installed (same clock as the service; guard ticks before the service ticks).
  var Module = require('module'), origRequire = Module.prototype.require, hooked = [], guards = [];
  // REWARDED_GUARD_DIRECT=1: the service's own calls carry the pass-through mark (proposed RewardedService line).
  if (process.env.REWARDED_GUARD_DIRECT === '1') global.__tiktokKitRewardedDirect = true;
  var hook = function (RS) {
    if (typeof RS !== 'function' || !RS.prototype || typeof RS.prototype.request !== 'function') return RS;
    for (var i = 0; i < hooked.length; i++) if (hooked[i][0] === RS) return hooked[i][1];
    var tick = RS.prototype.tick;
    RS.prototype.tick = function () { guards.forEach(function (g) { g.tick(); }); return tick.apply(this, arguments); };
    var H = function (opts) {
      opts = opts || {};
      var o = {}, get = opts.getSDK, clock = opts.now;
      Object.keys(opts).forEach(function (k) { o[k] = opts[k]; });
      if (typeof get === 'function') {
        o.getSDK = function (m) {
          var sdk = get(m);
          if (sdk && typeof sdk === 'object') {
            var g = install(null, null, {owners: [sdk], now: clock, autoPoll: false, listenDom: false});
            if (g && guards.indexOf(g) < 0) guards.push(g);
            if (sdk.createRewardedVideoAd && sdk.createRewardedVideoAd.__tiktokKitRewardedGuard) global.__guardSeen = (global.__guardSeen || 0) + 1;
          }
          return sdk;
        };
      }
      RS.call(this, o);
    };
    H.prototype = RS.prototype;
    hooked.push([RS, H]);
    return H;
  };
  Module.prototype.require = function (id) {
    var m = origRequire.apply(this, arguments);
    return /RewardedService(\.js)?$/.test(String(id)) ? hook(m) : m;
  };
  process.on('exit', function () {
    if (!global.__guardSeen) { console.error('rewarded-guard preload: no RewardedService SDK went through the guard'); process.exitCode = 1; }
    else console.error('rewarded-guard preload: guard under ' + global.__guardSeen + ' getSDK() calls');
  });
  return;
}

var assert = require('assert'), fs = require('fs'), os = require('os'), child = require('child_process');
var KIT = path.join(__dirname, '..', 'assets', 'tiktok-platform');
var TREE = path.resolve(__dirname, '..', '..', '..', '..');           // skill tree root (has remake-core/, ad-boost/)
var OLD_RS = path.join(__dirname, '..', 'tools', 'kit_versions', 'RewardedService',
  '04121e95bef876cd22b2490f94216b652353a71c310eca09135c08453a8830bd.txt');
var tmp = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'kit-rguard-')));
process.on('exit', function () { fs.rmSync(tmp, {recursive: true, force: true}); });
var results = [];
function flush() { var p = Promise.resolve(); for (var i = 0; i < 8; i++) p = p.then(function () {}); return p; }

// Fake TikTok SDK on a virtual clock. Every createRewardedVideoAd call makes a new native ad; show() returns
// a Promise resolved by ad.start(); ad.close(res) / ad.fail(e) fire the bound native listeners.
function world(useGuard) {
  var w = {time: 0, events: [], ads: [], hide: [], show: [], touch: [], timers: [], ticks: []};
  w.sdk = {
    canIUse: function () { return true; },
    onHide: function (f) { w.hide.push(f); }, offHide: function (f) { w.hide = w.hide.filter(function (x) { return x !== f; }); },
    onShow: function (f) { w.show.push(f); }, offShow: function (f) { w.show = w.show.filter(function (x) { return x !== f; }); },
    onTouchStart: function (f) { w.touch.push(f); },
    createRewardedVideoAd: function () {
      var ad = {closeFns: [], errFns: [], pend: [], shows: 0, ended: false};
      ad.onClose = function (f) { ad.closeFns.push(f); };
      ad.offClose = function (f) { ad.closeFns = f ? ad.closeFns.filter(function (x) { return x !== f; }) : []; };
      ad.onError = function (f) { ad.errFns.push(f); };
      ad.offError = function (f) { ad.errFns = f ? ad.errFns.filter(function (x) { return x !== f; }) : []; };
      ad.load = function () { return Promise.resolve(); };
      ad.show = function () { ad.shows++; ad.ended = false; return new Promise(function (r) { ad.pend.push(r); }); };
      ad.start = function () { ad.pend.splice(0).forEach(function (r) { r(); }); };
      ad.close = function (res) { ad.ended = true; ad.closeFns.slice().forEach(function (f) { f(res); }); };
      ad.fail = function (e) { ad.ended = true; ad.errFns.slice().forEach(function (f) { f(e); }); };
      w.ads.push(ad);
      return ad;
    }
  };
  w.now = function () { return w.time; };
  w.setTimeout = function (fn, ms) { var t = {at: w.time + ms, fn: fn}; w.timers.push(t); return t; };
  w.clearTimeout = function (t) { w.timers = w.timers.filter(function (x) { return x !== t; }); };
  if (useGuard) {
    w.guard = install(null, null, {owners: [w.sdk], now: w.now, autoPoll: false, listenDom: false});
    w.ticks.push(w.guard.tick);
  }
  w.at = function (ms, fn) { w.events.push({at: ms, fn: fn}); };
  w.run = async function (until) {
    await flush();
    while (w.time < until) {
      w.time += 100;
      var due = w.events.filter(function (e) { return e.at <= w.time; }).concat(w.timers.filter(function (t) { return t.at <= w.time; }));
      w.events = w.events.filter(function (e) { return e.at > w.time; });
      w.timers = w.timers.filter(function (t) { return t.at > w.time; });
      for (var i = 0; i < due.length; i++) { due[i].fn(); await flush(); }
      w.ticks.forEach(function (t) { t(); }); await flush();
    }
  };
  w.tap = function () { w.touch.slice().forEach(function (f) { f(); }); };
  // Native ads that have not ended but still have a close listener bound (host check "pending ad").
  w.pending = function () { return w.ads.filter(function (a) { return !a.ended && a.closeFns.length > 0; }).length; };
  return w;
}

// ---- Fixture A: 埃及宝石 EgyptianJewelQuest-SLS37 assets/scripts/HexPlatform.js rewarded(), lines 4 and 26-84
// (verbatim; only the module globals are made per world and diagnostic() is a no-op).
function egyptFixture(w) {
  var active = null, sequence = 0;
  function diagnostic() {}
  function rewarded(adUnitId, options) {
    options = options || {};
    var set = options.setTimeout || setTimeout, clear = options.clearTimeout || clearTimeout;
    var resolve, promise = new Promise(function (r) { resolve = r; });
    var ad, timer, done = false, terminal = false, started = false;
    var session = { id: ++sequence };
    function finish(status, completed) {
        if (done) return;
        done = true; clear(timer);
        var callback = resolve; resolve = null;
        diagnostic(status, session.id);
        callback({ status: status, completed: completed === true,
            receipt: completed === true ? "video:" + Date.now() + ":" + session.id : null });
    }
    function release() {
        if (terminal) return;
        terminal = true; clear(timer);
        if (active === session) active = null;
        try { if (ad && ad.offClose) ad.offClose(close); } catch (_) {}
        try { if (ad && ad.offError) ad.offError(error); } catch (_) {}
    }
    function close(result) {
        if (terminal) return;
        var complete = false;
        try { complete = started && result && result.isEnded === true; } catch (_) {}
        release(); finish(complete ? "completed" : "cancelled", complete);
    }
    function error(value) {
        if (terminal) return;
        diagnostic("sdk-error", session.id, value);
        release(); finish("failed", false);
    }
    function cancel() {
        if (done) return;
        if (!started) release();
        finish("cancelled", false);
    }
    if (active) { finish("busy", false); return { promise: promise, cancel: cancel }; }
    var api = (options.resolveSDK || resolveSDK)(["createRewardedVideoAd"]);
    if (!api || !adUnitId) { finish("unavailable", false); return { promise: promise, cancel: cancel }; }
    active = session;
    try {
        ad = api.createRewardedVideoAd({ adUnitId: adUnitId });
        if (!ad || !["show", "onClose", "offClose", "onError", "offError"].every(function (m) { return typeof ad[m] === "function"; })) throw Error("Unsupported ad instance");
        ad.onClose(close);
        if (!terminal && !done) ad.onError(error);
        if (!terminal && !done) {
            started = true;
            timer = set(function () { finish("timeout", false); }, options.timeoutMs || 180000);
            diagnostic("show", session.id);
            Promise.resolve(ad.show()).catch(error);
        }
    } catch (e) { error(e); }
    return { promise: promise, cancel: cancel };
  }
  function resolveSDK() { return w.sdk; }
  var last = null;
  return {
    name: 'A 埃及宝石 HexPlatform.rewarded（180 秒、共用锁）', singleAd: false,
    ask: function () {
      var rec = {settled: false, rewarded: false, busy: false};
      // HexUI.ts: this.request = Platform.rewarded(Config.rewardedPlacementId); grant on completed.
      last = rewarded('ad1', {setTimeout: w.setTimeout, clearTimeout: w.clearTimeout});
      last.promise.then(function (r) { rec.settled = true; rec.busy = r.status === 'busy'; rec.rewarded = r.completed === true; });
      return rec;
    },
    x: function () { if (last) last.cancel(); }   // the game's close button
  };
}

// ---- Fixture B: 拇指弹球 ThumbPinball-v6 assets/platform/RewardedService.js (old kit, sha 04121e95, kept byte
// for byte in tools/kit_versions/RewardedService/): timeout settles the UI but nativeSession stays set.
function pinballFixture(w) {
  var dir = path.join(tmp, 'old' + Math.random().toString(36).slice(2));
  fs.mkdirSync(dir);
  fs.copyFileSync(OLD_RS, path.join(dir, 'RewardedService.js'));
  fs.copyFileSync(path.join(KIT, 'PlatformConfig.js'), path.join(dir, 'PlatformConfig.js'));
  var RS = require(path.join(dir, 'RewardedService.js'));
  var svc = new RS({getSDK: function () { return w.sdk; }, now: w.now, autoPoll: false});
  w.ticks.push(function () { svc.tick(); });
  return {
    name: 'B 拇指弹球 v6 旧版 RewardedService.js（04121e95）', singleAd: false,
    ask: function () {
      var rec = {settled: false, rewarded: false, busy: false};
      svc.request({placementKey: 'double_coins', ownerId: 'pin'}).then(function (r) {
        rec.settled = true; rec.busy = r.status === 'busy'; rec.rewarded = r.rewarded === true;
      });
      return rec;
    },
    x: function () { svc.cancelOwner('pin'); }
  };
}

// ---- Fixture C: 搭桥小能手 9703-CC assets/scripts/sdk/sdk/TTSdk.js createVideoAd/showVideoAd (lines 103-163)
// and assets/scripts/sdk/sdk.ts showVideoAd (lines 77-95), verbatim apart from tt -> the fake SDK and the
// console lines. One ad object for the whole game, no timeout, no lock, no X.
function bridgeFixture(w) {
  var tt = w.sdk;
  var SdkProxy = {
    conf: {video_posid: ['ad1']}, videoAd: null,
    createVideoAd () {
        if (this.conf && this.conf.video_posid && tt.createRewardedVideoAd) {
            let video_id = Math.floor(Math.random() * this.conf.video_posid.length);
            this.videoAd = tt.createRewardedVideoAd({ adUnitId: this.conf.video_posid[video_id] });
            this.videoAd.onError(err => {});
        }
    },
    showVideoAd (onShow, onError, onClose) {
        if (!this.videoAd) return;
        if (this._onVideoClose) {
            this.videoAd.offClose(this._onVideoClose);
        }
        this._onVideoClose = ((res) => {
            if (res && res.isEnded) {
                if (onClose) { onClose(true); }
            } else {
                if (onClose) { onClose(false) }
            }
            this.videoAd.offClose(this._onVideoClose);
            this._onVideoClose = null;
        });
        this.videoAd.onClose(this._onVideoClose);
        this.videoAd.show().then(() => {
            if (onShow) { onShow(); }
        }).catch((err) => {
            if (err && err.errCode) {
                this.videoAd.load().then(() => { return this.videoAd.show(); })
                    .catch((err) => { if (onError) { onError(err); } });
            }
        });
    }
  };
  function showVideoAd(callback) {
    SdkProxy.showVideoAd(() => {}, (e) => {}, (v) => {
        if (!v) { if (callback) { callback(false); } }
        else { if (callback) { callback(true); } }
    });
  }
  SdkProxy.createVideoAd();
  return {
    name: 'C 搭桥小能手 TTSdk.showVideoAd（自写多平台 SDK、单个广告对象）', singleAd: true,
    ask: function () {
      var rec = {settled: false, rewarded: false, busy: false};
      // GameOverView.restore(): showVideoAd((v) => { if (v) { ...currentPower += 3 } })
      showVideoAd(function (v) { rec.settled = true; rec.rewarded = v === true; });
      return rec;
    },
    x: function () {}
  };
}

var FIXTURES = [egyptFixture, pinballFixture, bridgeFixture];
function rewards(recs) { return recs.filter(function (r) { return r.rewarded; }).length; }
function lastAd(w) { return w.ads[w.ads.length - 1]; }

// v7.4 case late16 (+ hang's "ask again at once"): request never starts within 15 s; at 15.2 s ask again,
// that video plays and ends; the first ad only starts at 16 s and "ends" at 46 s. Expected reward 1 (the second).
async function caseLate16(make, useGuard) {
  var w = world(useGuard), fx = make(w), recs = [], problems = [];
  recs.push(fx.ask());
  await w.run(15100);
  if (!recs[0].settled) problems.push('15 s 到了游戏还在等第一次广告（没有超时收尾）');
  var showsBefore = w.ads.reduce(function (n, a) { return n + a.shows; }, 0);
  w.at(15200, function () { recs.push(fx.ask()); });
  await w.run(15200);
  var showsAfter = w.ads.reduce(function (n, a) { return n + a.shows; }, 0);
  if (recs[1].busy || showsAfter === showsBefore) problems.push('超时后马上再点广告没有开播（锁着）');
  var second = lastAd(w);
  w.at(15500, function () { second.start(); });
  w.at(15900, function () { second.close({isEnded: true}); });
  w.at(16000, function () { w.ads[0].start(); });
  w.at(46000, function () { w.ads[0].close({isEnded: true}); });
  await w.run(47000);
  if (rewards(recs) !== 1) problems.push('应发 1 次奖励，实际 ' + rewards(recs) + ' 次（迟到开播的旧广告也发了，或新广告没发）');
  if (w.pending()) problems.push('还有 ' + w.pending() + ' 个没结束却挂着回调的广告');
  return problems;
}
// v7.4 case nocallback: playback starts at 1 s, no callback; at 31 s the player taps the X; ask again at
// 31.5 s, it plays and ends; only then the old video "ends" late (41 s). Expected reward 1 (the second only).
// A game with ONE ad object (fixture C) cannot tell the old video from the new one, so there the old video
// "ends" late at 31.2 s, before the second request.
async function caseNoCallback(make, useGuard) {
  var w = world(useGuard), fx = make(w), recs = [], problems = [];
  recs.push(fx.ask());
  var first = null;
  w.at(1000, function () { first = w.ads[0]; first.start(); });
  w.at(31000, function () { w.tap(); fx.x(); });
  w.at(fx.singleAd ? 31200 : 41000, function () { first.close({isEnded: true}); });
  await w.run(31400);
  var showsBefore = w.ads.reduce(function (n, a) { return n + a.shows; }, 0);
  w.at(31500, function () { recs.push(fx.ask()); });
  await w.run(31500);
  var showsAfter = w.ads.reduce(function (n, a) { return n + a.shows; }, 0);
  if (recs[1].busy || showsAfter === showsBefore) problems.push('按 X 后再点广告没有开播（锁着）');
  var second = lastAd(w);
  w.at(32000, function () { second.start(); });
  w.at(40000, function () { second.close({isEnded: true}); });
  await w.run(41000);
  if (rewards(recs) !== 1) problems.push('应发 1 次奖励，实际 ' + rewards(recs) + ' 次（按 X 后迟到看完的旧广告也发了，或新广告没发）');
  if (w.pending()) problems.push('还有 ' + w.pending() + ' 个没结束却挂着回调的广告');
  return problems;
}
// Normal and long200: the guard must not take a reward away from a watched video.
async function caseWatched(make, useGuard, endAt) {
  var w = world(useGuard), fx = make(w), recs = [fx.ask()], problems = [];
  w.at(1000, function () { w.ads[0].start(); });
  w.at(endAt, function () { w.ads[0].close({isEnded: true}); });
  await w.run(endAt + 1000);
  if (rewards(recs) !== 1) problems.push('看完应发 1 次，实际 ' + rewards(recs) + ' 次');
  return problems;
}

async function test(name, run) {
  try { await run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
var table = [];

function runChild(label, file, env) {
  var r = child.spawnSync(process.execPath, ['-r', __filename, file],
    {encoding: 'utf8', timeout: 60000, env: Object.assign({}, process.env, {REWARDED_GUARD_PRELOAD: '1'}, env || {})});
  return {status: r.status, out: String(r.stdout || ''), err: String(r.stderr || '')};
}
function baseline(file, env) {
  var r = child.spawnSync(process.execPath, [file], {encoding: 'utf8', timeout: 60000, env: Object.assign({}, process.env, env || {})});
  return {status: r.status, out: String(r.stdout || '')};
}

(async function () {
  // 1. Fixtures: without the guard late16 and nocallback must fail; with it they must pass.
  for (var i = 0; i < FIXTURES.length; i++) {
    var make = FIXTURES[i], name = make(world(false)).name;
    for (var c of [['late16', caseLate16], ['nocallback', caseNoCallback]]) {
      var off = await c[1](make, false), on = await c[1](make, true);
      table.push({fixture: name, case: c[0], without_guard: off, with_guard: on});
      await test(name + ' ' + c[0] + '：不装 guard 必须失败', function () { assert(off.length > 0, 'fixture passed without the guard'); });
      await test(name + ' ' + c[0] + '：装上 guard 不锁死、不迟到发奖', function () { assert.deepStrictEqual(on, []); });
    }
    var normal = await caseWatched(make, true, 10000);
    await test(name + ' normal：装上 guard 看完照常发奖', function () { assert.deepStrictEqual(normal, []); });
    var longOff = await caseWatched(make, false, 201000), longOn = await caseWatched(make, true, 201000);
    table.push({fixture: name, case: 'long200（只记录）', without_guard: longOff, with_guard: longOn});
    await test(name + ' long200：guard 不改变结果（游戏自己的播放计时 guard 不管）', function () {
      assert.strictEqual(longOn.length > 0, longOff.length > 0);
    });
  }

  // 2. Unit rules.
  await test('只放一个 show()：第二个立刻 busy，原生 show 只调一次', async function () {
    var w = world(true), a = w.sdk.createRewardedVideoAd({}), b = w.sdk.createRewardedVideoAd({});
    a.onClose(function () {}); b.onClose(function () {});
    a.show(); var err = null; await b.show().catch(function (e) { err = e; });
    assert(err && err.errMsg === 'rewarded-guard: busy');
    assert.strictEqual(w.ads[0].shows + w.ads[1].shows, 1);
  });
  await test('isEnded 不是 true 的 onClose 转成 {isEnded:false}', async function () {
    var vals = [undefined, {}, {isEnded: 1}, {isEnded: 'true'}, {isEnded: false}];
    for (var v of vals) {
      var w = world(true), ad = w.sdk.createRewardedVideoAd({}), got = 'none';
      ad.onClose(function (r) { got = r; }); ad.show(); w.ads[0].start(); await flush();
      w.ads[0].close(v); await flush();
      assert.deepStrictEqual(got, {isEnded: false}, JSON.stringify(v));
    }
  });
  await test('后台时间不算进 15 秒（2 秒后切后台 60 秒，回来 8 秒后开播，看完发奖）', async function () {
    var w = world(true), ad = w.sdk.createRewardedVideoAd({}), got = [];
    ad.onClose(function (r) { got.push(r.isEnded); }); ad.show();
    w.at(2000, function () { w.hide.slice().forEach(function (f) { f(); }); });
    w.at(62000, function () { w.show.slice().forEach(function (f) { f(); }); });
    w.at(70000, function () { w.ads[0].start(); });
    w.at(80000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(81000);
    assert.deepStrictEqual(got, [true]);
  });
  await test('开播后不计时：开播 30 秒内的触屏不算 X，200 秒看完照常发奖', async function () {
    var w = world(true), ad = w.sdk.createRewardedVideoAd({}), got = [];
    ad.onClose(function (r) { got.push(r.isEnded); }); ad.show();
    w.at(1000, function () { w.ads[0].start(); });
    w.at(20000, function () { w.tap(); });
    w.at(201000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(202000);
    assert.deepStrictEqual(got, [true]);
  });
  await test('作废时只补一次 onClose({isEnded:false})，原生回调已解绑，show() 不 reject（不触发游戏自动重试）', async function () {
    var w = world(true), ad = w.sdk.createRewardedVideoAd({}), got = [], rejected = false;
    ad.onClose(function (r) { got.push(r.isEnded); }); ad.onError(function () { got.push('error'); });
    ad.show().catch(function () { rejected = true; });
    await w.run(15100);
    assert.deepStrictEqual(got, [false]);
    assert.strictEqual(w.ads[0].closeFns.length + w.ads[0].errFns.length, 0, 'native listeners unbound');
    w.ads[0].start(); w.ads[0].fail({errCode: 1}); await flush();
    assert.deepStrictEqual(got, [false]); assert.strictEqual(rejected, false);
  });
  await test('装两次只一层；包过的广告对象不再包', function () {
    var w = world(true), create = w.sdk.createRewardedVideoAd;
    var g2 = install(null, null, {owners: [w.sdk], now: w.now, autoPoll: false, listenDom: false});
    assert.strictEqual(g2, w.guard); assert.strictEqual(w.sdk.createRewardedVideoAd, create);
    assert.strictEqual(w.hide.length, 1, 'lifecycle listeners registered once');
  });
  await test('__tiktokKitRewardedDirect === true 时拿到原生广告对象（标记放行）', function () {
    var w = world(true);
    global.__tiktokKitRewardedDirect = true;
    try { var ad = w.sdk.createRewardedVideoAd({}); assert.strictEqual(ad, w.ads[0]); }
    finally { delete global.__tiktokKitRewardedDirect; }
    assert.notStrictEqual(w.sdk.createRewardedVideoAd({}), w.ads[1]);
  });
  await test('没有 createRewardedVideoAd 的环境、接口只读的环境都不装，返回 null，不抛错', function () {
    assert.strictEqual(install(null, null, {owners: [{}], autoPoll: false, listenDom: false}), null);
    var ro = Object.freeze({createRewardedVideoAd: function () { return {}; }});
    assert.strictEqual(install(null, null, {owners: [ro], autoPoll: false, listenDom: false}), null);
  });
  await test('TTMinis.game 和 tt 都包、一个转调另一个时广告对象只包一层', async function () {
    var w = world(false), inner = w.sdk;
    var outer = {createRewardedVideoAd: function (o) { return inner.createRewardedVideoAd(o); },
      onHide: inner.onHide, onShow: inner.onShow};
    var g = install(null, null, {owners: [outer, inner], now: w.now, autoPoll: false, listenDom: false});
    w.ticks.push(g.tick);
    var ad = outer.createRewardedVideoAd({}), got = [];
    ad.onClose(function (r) { got.push(r.isEnded); }); ad.show();
    w.at(1000, function () { w.ads[0].start(); }); w.at(5000, function () { w.ads[0].close({isEnded: true}); });
    await w.run(6000);
    assert.deepStrictEqual(got, [true]); assert.strictEqual(w.ads[0].closeFns.length <= 1, true);
  });

  // D2 (2026-11-04): the kit RewardedService marks its own create call, so only the service times the 15 s.
  // A game wired per README (ad-boost tests too) may tell only the service about the background
  // (service.onHide()); the guard never sees it. 11.12 RewardedService 7a446726 (unmarked) loses the reward of a
  // video that starts after 60 s in the background; the current file grants it. Old fails, new passes.
  var RS_1112 = path.join(__dirname, '..', 'tools', 'kit_versions', 'RewardedService',
    '7a4467265a37f9e9631ca95c4a191464611b364af8ebe57c9d63f05a022c3c52.txt');
  function loadRS(file) {
    var dir = path.join(tmp, 'rs' + Math.random().toString(36).slice(2));
    fs.mkdirSync(dir);
    fs.copyFileSync(file, path.join(dir, 'RewardedService.js'));
    fs.copyFileSync(path.join(KIT, 'PlatformConfig.js'), path.join(dir, 'PlatformConfig.js'));
    return require(path.join(dir, 'RewardedService.js'));
  }
  async function bgThenWatch(file) {
    var w = world(true), RS = loadRS(file), out = {result: null};
    var svc = new RS({getSDK: function () { return w.sdk; }, now: w.now, autoPoll: false});
    w.ticks.push(function () { svc.tick(); });
    svc.request({placementKey: 'double_coins', ownerId: 'd2'}).then(function (r) { out.result = r; });
    w.at(1000, function () { svc.onHide(); });            // service told directly, as ad-boost tests do
    w.at(61000, function () { svc.onShow(); });
    w.at(62000, function () { lastAd(w).start(); });
    w.at(70000, function () { lastAd(w).close({isEnded: true}); });
    await w.run(71000);
    return out.result || {status: 'pending', rewarded: false};
  }
  var d2Old = await bgThenWatch(RS_1112), d2New = await bgThenWatch(path.join(KIT, 'RewardedService.js'));
  table.push({fixture: 'D2 请求后切后台 60 秒、回来开播看完（只告诉 RewardedService 切后台）',
    'rs_11.12_7a446726': d2Old.status + (d2Old.rewarded ? ' 发奖' : ' 不发奖'),
    rs_current: d2New.status + (d2New.rewarded ? ' 发奖' : ' 不发奖')});
  await test('D2 旧败：11.12 原版 RewardedService（7a446726，不带标记）经 guard，切后台 60 秒后开播看完不发奖（被 guard 当成超时作废）', function () {
    assert.strictEqual(d2Old.rewarded, false, 'expected the 11.12 bug to show: ' + JSON.stringify(d2Old));
  });
  await test('D2 新过：现在的 RewardedService（自己创建广告带放行标记）经 guard，切后台 60 秒后开播看完发奖', function () {
    assert.strictEqual(d2New.status, 'completed', JSON.stringify(d2New)); assert.strictEqual(d2New.rewarded, true);
  });
  await test('D2 标记只在 RewardedService 创建广告那一下：之后清掉，游戏自己的广告照旧被 guard 包住；原来就有的标记原样放回', async function () {
    var w = world(true), RS = loadRS(path.join(KIT, 'RewardedService.js'));
    var svc = new RS({getSDK: function () { return w.sdk; }, now: w.now, autoPoll: false});
    svc.request({placementKey: 'double_coins', ownerId: 'd2m'}); await flush();
    assert.strictEqual(w.ads.length, 1);
    assert.strictEqual(Object.prototype.hasOwnProperty.call(global, '__tiktokKitRewardedDirect'), false, 'mark cleared');
    assert.notStrictEqual(w.sdk.createRewardedVideoAd({}), w.ads[1], 'game ad still wrapped');
    svc.dispose();
    global.__tiktokKitRewardedDirect = 'x';
    try {
      var w2 = world(true), svc2 = new RS({getSDK: function () { return w2.sdk; }, now: w2.now, autoPoll: false});
      svc2.request({placementKey: 'double_coins', ownerId: 'd2n'}); await flush();
      assert.strictEqual(global.__tiktokKitRewardedDirect, 'x'); svc2.dispose();
    } finally { delete global.__tiktokKitRewardedDirect; }
  });

  // 3. The current kit RewardedService.js and ad-boost Kit.runAd through the guard: same results.
  var timing = path.join(__dirname, 'rewarded-timing.test.js');
  var tBase = baseline(timing), tGuard = runChild('timing', timing), tDirect = runChild('timing-direct', timing,
    {REWARDED_GUARD_DIRECT: '1'});
  function summary(o) { try { var j = JSON.parse(o.slice(o.indexOf('{'))); return j.passed + '/' + (j.passed + j.failed); } catch (e) { return 'unparsed'; } }
  await test('rewarded-timing.test.js 经 guard 跑（平台包 RewardedService 不带标记）：结果和不装一样，全过', function () {
    assert.strictEqual(tBase.status, 0); assert.strictEqual(tGuard.status, 0, tGuard.out.slice(0, 1500) + tGuard.err.slice(0, 500));
    assert.strictEqual(summary(tGuard.out), summary(tBase.out));
    assert(/guard under [1-9]/.test(tGuard.err), 'guard really sat under the service');
  });
  await test('rewarded-timing.test.js 带放行标记跑：拿到原生对象，结果和不装一样，全过', function () {
    assert.strictEqual(tDirect.status, 0, tDirect.out.slice(0, 1500) + tDirect.err.slice(0, 500));
    assert.strictEqual(summary(tDirect.out), summary(tBase.out));
  });
  var adboost = path.join(TREE, 'ad-boost', 'ui-kit', 'test', 'AdBoostKit.test.js');
  if (fs.existsSync(adboost)) {
    var env = {AD_BOOST_SKILLS_DIR: TREE};
    var aBase = baseline(adboost, env), aGuard = runChild('adboost', adboost, env);
    var count = function (o) { var m = /(\d+)\/(\d+) passed/.exec(o); return m ? m[0] : 'unparsed'; };
    await test('ad-boost AdBoostKit.test.js 经 guard 跑（Kit.runAd -> RewardedService）：结果和不装一样', function () {
      assert.strictEqual(aGuard.status, aBase.status, aGuard.out.slice(-1500) + aGuard.err.slice(0, 500));
      assert.strictEqual(count(aGuard.out), count(aBase.out));
      assert(/guard under [1-9]/.test(aGuard.err), 'guard really sat under Kit.runAd');
    });
  } else {
    results.push({name: 'ad-boost AdBoostKit.test.js 经 guard 跑', status: 'skipped', error: 'ad-boost not next to remake-core'});
  }

  var failed = results.filter(function (x) { return x.status === 'failed'; });
  console.log(JSON.stringify({suite: 'rewarded-guard', passed: results.filter(function (x) { return x.status === 'passed'; }).length,
    failed: failed.length, fixtures: table, results: results,
    rewarded_timing: {without_guard: summary(tBase.out), with_guard: summary(tGuard.out)}}, null, 2));
  if (failed.length) process.exitCode = 1;
})();
