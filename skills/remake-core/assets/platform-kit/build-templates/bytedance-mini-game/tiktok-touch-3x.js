'use strict';
// tiktok-kit:touch3x:2.0  Cocos 3.x TikTok touch coordinates (platform kit standard part, 待真机复测).
// TikTok touch points carry identifier/screenX/screenY/force; the Cocos 3.x minigame TouchInputSource reads
// clientX/clientY, so every tap lands at (0, 0). Copy the coordinates over BEFORE web-adapter.js runs and the
// engine clones the SDK object. Base: Marlows R6 marlow-touch.js (sha b1167bad...), generic name, install(api),
// SDK lookup TTMinis.game -> tt, one layer per SDK object however many times install() runs.
// game.js wiring (inserted by tiktok_finalize, exactly once, before require('./web-adapter')):
//   require('./tiktok-touch-3x.js').install(globalThis.TTMinis&&TTMinis.game||globalThis.tt);
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
  PHASES.forEach(function (suffix) {
    var on = 'onTouch' + suffix, off = 'offTouch' + suffix;
    if (typeof api[on] !== 'function') return;
    var originalOn = api[on], originalOff = api[off], listeners = new WeakMap();
    try {
      api[on] = function (listener) {
        if (typeof listener !== 'function') return originalOn.call(this, listener);
        var w = listeners.get(listener);
        if (!w) {
          w = function (event) { return listener.call(this, normalize(event)); };
          listeners.set(listener, w);
        }
        return originalOn.call(this, w);
      };
      if (typeof originalOff === 'function') api[off] = function (listener) {
        return originalOff.call(this, listeners.get(listener) || listener);
      };
      wrapped++;
    } catch (e) { console.warn('[tiktok-touch-3x] could not wrap ' + on, e); }
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
