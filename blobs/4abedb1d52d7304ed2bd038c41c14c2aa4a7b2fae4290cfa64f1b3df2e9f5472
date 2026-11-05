'use strict';
// tiktok-kit:touch3x:2.0  Cocos 3.x TikTok touch coordinates (platform kit standard part, 待真机复测).
// TikTok touch points carry identifier/screenX/screenY/force; the Cocos 3.x minigame TouchInputSource reads
// clientX/clientY, so every tap lands at (0, 0). Copy the coordinates over BEFORE web-adapter.js runs and the
// engine clones the SDK object. Base: Marlows R6 marlow-touch.js (sha b1167bad...), generic name, install(api),
// SDK lookup TTMinis.game -> tt, one layer per SDK object however many times install() runs.
// game.js wiring (inserted by tiktok_finalize, exactly once, before require('./web-adapter')):
//   require('./tiktok-touch-3x.js').install(globalThis.TTMinis&&TTMinis.game||globalThis.tt);
// v7.9 (手机问题源头约束): a finger that is down when TikTok takes the game away (Control Center, a call, a rewarded
// video) may never get touchend / touchcancel. The engine keeps it in its touch list, so a game that ignores
// multi-finger taps (event.getAllTouches().length > 1, 猴子快跑 v12) ignores every tap after returning, and a reused
// identifier continues the old touch. The wrapper remembers the touches it handed to the engine and, on tt.onHide and
// tt.onShow, gives the engine's touchcancel listeners the ones still down, so the next finger starts clean.
var VERSION = '2.0';
var MARK = '__tiktokKitTouch3x';
var PHASES = ['Start', 'Move', 'End', 'Cancel'];

function finite(value) { return typeof value === 'number' && isFinite(value); }

function point(value) {
  if (!value || finite(value.clientX) && finite(value.clientY)) return value;
  var copy = Object.assign({}, value);
  copy.identifier = value.identifier;
  var x = finite(value.clientX) ? value.clientX : finite(value.screenX) ? value.screenX : value.x;
  var y = finite(value.clientY) ? value.clientY : finite(value.screenY) ? value.screenY : value.y;
  if (finite(x)) copy.clientX = x;
  if (finite(y)) copy.clientY = y;
  return copy;
}

function normalize(event) {
  return Object.assign({}, event, {
    touches: Array.from(event && event.touches || [], point),
    changedTouches: Array.from(event && event.changedTouches || [], point)
  });
}

function wrap(api) {
  if (!api || typeof api !== 'object' && typeof api !== 'function') return false;
  if (api[MARK]) return false;
  var wrapped = 0;
  // touches handed to the engine and not ended yet (identifier -> last point), and the engine's touchcancel listeners
  var down = {}, cancels = [];
  function track(suffix, event) {
    Array.prototype.forEach.call(event && event.changedTouches || [], function (t) {
      if (!t || t.identifier === undefined || t.identifier === null) return;
      var id = String(t.identifier);
      if (suffix === 'Start') down[id] = t;
      else if (suffix === 'Move') { if (down[id]) down[id] = t; }
      else delete down[id];
    });
  }
  PHASES.forEach(function (suffix) {
    var on = 'onTouch' + suffix, off = 'offTouch' + suffix;
    if (typeof api[on] !== 'function') return;
    var originalOn = api[on], originalOff = api[off], listeners = new WeakMap();
    try {
      api[on] = function (listener) {
        if (typeof listener !== 'function') return originalOn.call(this, listener);
        var w = listeners.get(listener);
        if (!w) {
          w = function (event) { var e = normalize(event); track(suffix, e); return listener.call(this, e); };
          listeners.set(listener, w);
        }
        if (suffix === 'Cancel' && cancels.indexOf(listener) < 0) cancels.push(listener);
        return originalOn.call(this, w);
      };
      if (typeof originalOff === 'function') api[off] = function (listener) {
        if (suffix === 'Cancel') { var i = cancels.indexOf(listener); if (i >= 0) cancels.splice(i, 1); }
        return originalOff.call(this, listeners.get(listener) || listener);
      };
      wrapped++;
    } catch (e) { console.warn('[tiktok-touch-3x] could not wrap ' + on, e); }
  });
  // the phone takes the game away / gives it back: the touches still down get a touchcancel (once)
  function release() {
    var ids = Object.keys(down);
    if (!ids.length) return;
    var event = {touches: [], changedTouches: ids.map(function (id) { return down[id]; }), timeStamp: Date.now()};
    down = {};
    cancels.slice().forEach(function (fn) {
      try { fn.call(api, event); } catch (e) { console.warn('[tiktok-touch-3x] touchcancel listener threw', e); }
    });
  }
  ['onHide', 'onShow'].forEach(function (name) {
    try { if (typeof api[name] === 'function') api[name](release); } catch (e) {}
  });
  try { Object.defineProperty(api, MARK, {value: VERSION, enumerable: false, configurable: true}); } catch (e) {}
  return wrapped > 0;
}

function sdkCandidates(api) {
  var g = typeof globalThis !== 'undefined' ? globalThis : typeof GameGlobal !== 'undefined' ? GameGlobal : {};
  var list = [api];
  try { if (g.TTMinis && g.TTMinis.game) list.push(g.TTMinis.game); } catch (e) {}
  try { if (typeof tt !== 'undefined') list.push(tt); } catch (e) {}
  try { if (g.tt) list.push(g.tt); } catch (e) {}
  var out = [];
  list.forEach(function (o) { if (o && out.indexOf(o) < 0) out.push(o); });
  return out;
}

// Wraps the given SDK object and every other TikTok SDK object found (TTMinis.game, tt), each exactly once:
// the engine clones `tt`, so `tt` must be wrapped even when the caller passed TTMinis.game.
function install(api) {
  var count = 0;
  sdkCandidates(api).forEach(function (o) { if (wrap(o)) count++; });
  return count;
}

module.exports = {install: install, version: VERSION, normalizePoint: point};
