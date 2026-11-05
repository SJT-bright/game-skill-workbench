'use strict';
// TikTok Platform Kit rewarded-ad guard (rewarded-guard.js). Copy unchanged; Node-tested only, 待真机复测.
// Plan P01 point 2 (问题普查 2026-11-04: ad lock after close 50 games, wrong timeout 32, late reward 14).
// Installed by main.js before any game script, the same way as storage-guard.js. It wraps
// createRewardedVideoAd on TTMinis.game / tt / wx so that ad code the localisation did not rewire
// (a game's own ad manager, an old copied RewardedService.js) follows Saul's rule of 2026-10-29
// (remake-ads/references/ad-timeout-and-regression.md):
//   - one show() at a time: a second show() while one is live is rejected at once
//     ({errCode: -1, errMsg: 'rewarded-guard: busy'}); nothing is queued, no lock is kept;
//   - from show() to playback start at most 15 s of FOREGROUND time (background not counted). When
//     the budget runs out the attempt is void: the game's close listeners get ONE onClose({isEnded:false})
//     so its own lock/flags release, the native listeners are unbound (offClose/offError), and the show()
//     Promise is left pending (a rejection would make some games auto-retry);
//   - after playback starts there is no timeout. If no callback came 30 s after playback started, the
//     player's next touch on the game counts as the X: onClose({isEnded:false}) once, attempt void;
//   - onClose/onError/show() results of a void or finished attempt never reach the game (no late reward,
//     no double callback);
//   - an onClose whose res.isEnded is not exactly true reaches the game as {isEnded:false};
//   - when the game removes all its close listeners (offClose) of a live attempt, the attempt is over
//     (the kit RewardedService does this on timeout / X / cancel) and the next show() may start.
// Pass-through: while root.__tiktokKitRewardedDirect === true, createRewardedVideoAd returns the native ad
// unwrapped (for a RewardedService that marks its own call). The current kit RewardedService.js does not
// set the mark and runs unchanged through the guard (tests/rewarded-guard.test.js runs rewarded-timing.test.js
// and ad-boost AdBoostKit.test.js through it). install() is idempotent: a second call wraps nothing again.
// install(cc, api, options) -> guard {tick, onHide, onShow, touch, live, events}; options (tests):
//   now (ms clock), autoPoll (default true, 250 ms, unref), owners (array of SDK objects),
//   requestTimeoutMs (15000), exitAfterMs (30000), listenDom (default true).
var MARK = '__tiktokKitRewardedGuard';
function forEachMethod(obj, fn) {
  var seen = {};
  for (var o = obj; o && o !== Object.prototype && o !== Function.prototype; o = Object.getPrototypeOf(o)) {
    var names;
    try { names = Object.getOwnPropertyNames(o); } catch (e) { names = []; }
    for (var key in o) if (names.indexOf(key) < 0) names.push(key);
    names.forEach(function (name) {
      if (name === 'constructor' || seen[name]) return;
      seen[name] = true;
      var d;
      try { d = Object.getOwnPropertyDescriptor(o, name); } catch (e) { d = null; }
      if (d && d.get && !d.value) return;          // an accessor is not a method; leave it alone
      var v;
      try { v = obj[name]; } catch (e) { return; }
      if (typeof v === 'function') fn(name);
    });
  }
}
module.exports = function install(cc, api, options) {
  options = options || {};
  var root = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this);
  var owners = options.owners || [api, root.TTMinis && root.TTMinis.game, root.tt, root.wx];
  owners = owners.filter(function (o, i) { return o && typeof o === 'object' && owners.indexOf(o) === i; });
  for (var k = 0; k < owners.length; k++) {
    var made = owners[k].createRewardedVideoAd;
    if (typeof made === 'function' && made[MARK]) return made[MARK];
  }
  var now = options.now || Date.now;
  var REQUEST_MS = options.requestTimeoutMs || 15000, EXIT_MS = options.exitAfterMs || 30000;
  var G = {live: null, hiddenAt: null, events: [], proxies: []};
  function note(kind) { if (G.events.length < 80) G.events.push({kind: kind, at: now()}); }
  function safely(fn) { try { return fn(); } catch (_) { return undefined; } }
  function call(list, value) { list.slice().forEach(function (fn) { safely(function () { fn(value); }); }); }

  // The single place an attempt becomes void: listeners unbound, game told "not watched" once if asked.
  function voidAttempt(a, tell, kind) {
    if (a.terminal) return;
    a.terminal = true; a.void = true;
    if (G.live === a) G.live = null;
    note(kind);
    unbindRaw(a.proxy);
    if (tell) call(a.proxy.closeFns, {isEnded: false});
  }
  function end(a) { a.terminal = true; if (G.live === a) G.live = null; }
  function expire(a, at) {
    if (!a || a.terminal || a.phase !== 'request' || a.hiddenAt !== null) return false;
    if ((at === undefined ? now() : at) < a.deadline) return false;
    voidAttempt(a, true, 'timeout');
    return true;
  }
  G.tick = function () { expire(G.live); };
  G.onHide = function () {
    var t = now();
    if (G.hiddenAt === null) G.hiddenAt = t;
    var a = G.live;
    if (a && a.hiddenAt === null && !expire(a, t)) a.hiddenAt = t;
  };
  G.onShow = function () {
    var t = now();
    G.hiddenAt = null;
    var a = G.live;
    if (!a || a.hiddenAt === null) return;
    var away = Math.max(0, t - a.hiddenAt);
    a.hiddenAt = null;
    if (a.phase === 'request') a.deadline += away;
  };
  // A touch that reaches the game while playback has had no callback for EXIT_MS = the player is back (X).
  G.touch = function () {
    var a = G.live;
    if (a && !a.terminal && a.phase === 'playing' && now() - a.startedAt >= EXIT_MS) voidAttempt(a, true, 'exit');
  };

  function bindRaw(P) {
    if (P.rawBound) return;
    P.rawBound = true;
    if (typeof P.raw.onClose === 'function') safely(function () { P.raw.onClose(P.rawClose); });
    if (typeof P.raw.onError === 'function') safely(function () { P.raw.onError(P.rawError); });
  }
  function unbindRaw(P) {
    if (!P.rawBound) return;
    P.rawBound = false;
    if (typeof P.raw.offClose === 'function') safely(function () { P.raw.offClose(P.rawClose); });
    if (typeof P.raw.offError === 'function') safely(function () { P.raw.offError(P.rawError); });
  }
  function remove(list, fn) {
    if (fn === undefined) return list.splice(0, list.length);
    var i = list.indexOf(fn);
    if (i >= 0) list.splice(i, 1);
  }
  function busy() { note('busy'); return Promise.reject({errCode: -1, errMsg: 'rewarded-guard: busy'}); }

  function wrapAd(raw) {
    if (!raw || typeof raw !== 'object' || raw[MARK]) return raw;
    for (var i = 0; i < G.proxies.length; i++) if (G.proxies[i].raw === raw) return G.proxies[i].proxy;
    var P = {raw: raw, closeFns: [], errorFns: [], rawBound: false, everShown: false, attempt: null};
    P.rawClose = function (res) {
      var a = P.attempt;
      var value = res && res.isEnded === true ? res : {isEnded: false};
      if (value !== res) note('normalized');
      if (!a) { if (!P.everShown) call(P.closeFns, value); return; }   // before any show(): unchanged
      if (a.terminal) { note('late_drop'); return; }
      if (expire(a)) return;
      end(a);
      call(P.closeFns, value);
    };
    P.rawError = function (e) {
      var a = P.attempt;
      if (!a) { if (!P.everShown) call(P.errorFns, e); return; }
      if (a.terminal) { note('late_drop'); return; }
      if (expire(a)) return;
      end(a);
      call(P.errorFns, e);
    };
    var proxy = {};
    // Every method of the native ad is forwarded, own, inherited and non-enumerable ones alike (class methods such
    // as load() and destroy() on an SDK prototype), by one loop that names none of them. F2 (发版自检 C4): the old
    // extra line naming the ad's load method was read by the package resource check as a Cocos loader escaping.
    forEachMethod(raw, function (name) {
      proxy[name] = function () { return raw[name].apply(raw, arguments); };
    });
    proxy.onClose = function (fn) {
      if (typeof fn === 'function' && P.closeFns.indexOf(fn) < 0) P.closeFns.push(fn);
      bindRaw(P);
    };
    proxy.onError = function (fn) {
      if (typeof fn === 'function' && P.errorFns.indexOf(fn) < 0) P.errorFns.push(fn);
      bindRaw(P);
    };
    proxy.offClose = function (fn) {
      remove(P.closeFns, fn);
      var a = P.attempt;
      if (!P.closeFns.length && a && !a.terminal) voidAttempt(a, false, 'abandoned');
      if (!P.closeFns.length && !P.errorFns.length) unbindRaw(P);
    };
    proxy.offError = function (fn) {
      remove(P.errorFns, fn);
      if (!P.closeFns.length && !P.errorFns.length) unbindRaw(P);
    };
    proxy.show = function () {
      G.tick();
      if (G.live && !G.live.terminal) return busy();
      var t = now();
      var a = {proxy: P, phase: 'request', deadline: t + REQUEST_MS, hiddenAt: G.hiddenAt === null ? null : t,
        startedAt: 0, terminal: false, void: false};
      P.attempt = a; P.everShown = true; G.live = a;
      if (P.closeFns.length || P.errorFns.length) bindRaw(P);
      function started() {
        if (a.terminal || expire(a)) return;
        a.phase = 'playing';
        a.startedAt = now();
      }
      var shown;
      try { shown = raw.show(); }
      catch (e) { if (!a.terminal) end(a); return Promise.reject(e); }
      if (!shown || typeof shown.then !== 'function') { started(); return Promise.resolve(shown); }
      return new Promise(function (resolve, reject) {
        shown.then(function (v) {
          if (a.void) return;                 // void attempt: a late start never reaches the game
          started();
          if (!a.void) resolve(v);
        }, function (e) {
          if (a.void) return;
          if (!a.terminal) { if (expire(a)) return; end(a); }
          reject(e);
        });
      });
    };
    proxy[MARK] = true;
    G.proxies.push({raw: raw, proxy: proxy});
    return proxy;
  }

  var wrapped = 0;
  owners.forEach(function (owner) {
    var create = owner.createRewardedVideoAd;
    if (typeof create !== 'function' || create[MARK]) return;
    var guarded = function () {
      var ad = create.apply(owner, arguments);
      if (root.__tiktokKitRewardedDirect === true) return ad;   // kit service marked its own call
      return wrapAd(ad);
    };
    guarded[MARK] = G;
    safely(function () { owner.createRewardedVideoAd = guarded; });
    if (owner.createRewardedVideoAd !== guarded) { note('not_writable'); return; }   // read-only host API
    wrapped++;
    if (typeof owner.onHide === 'function') safely(function () { owner.onHide(G.onHide); });
    if (typeof owner.onShow === 'function') safely(function () { owner.onShow(G.onShow); });
    if (typeof owner.onTouchStart === 'function') safely(function () { owner.onTouchStart(G.touch); });
  });
  if (!wrapped) return null;
  if (cc && cc.game && typeof cc.game.on === 'function') {
    safely(function () { cc.game.on(cc.game.EVENT_HIDE || 'game_on_hide', G.onHide); });
    safely(function () { cc.game.on(cc.game.EVENT_SHOW || 'game_on_show', G.onShow); });
  }
  var doc = root.document;
  if (options.listenDom !== false && doc && typeof doc.addEventListener === 'function') {
    ['touchstart', 'mousedown'].forEach(function (type) { safely(function () { doc.addEventListener(type, G.touch, true); }); });
  }
  if (options.autoPoll !== false && typeof setInterval === 'function') {
    var poll = setInterval(G.tick, 250);
    if (poll && poll.unref) poll.unref();
  }
  root.__tiktokKitRewardedGuardInstance = G;
  return G;
};
