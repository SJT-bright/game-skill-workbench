'use strict';
// tiktok-kit:hostshim:1.0  TikTok host API safe defaults (TikTok Platform Kit; Cocos 2.4 and 3.x, same file).
// Copy unchanged. Load it FIRST in game.js, before the engine adapter (2.4 adapter-min.js / 3.x web-adapter.js):
//   require('./host-shim.js').install(globalThis.TTMinis&&TTMinis.game||globalThis.tt); // tiktok-kit:hostshim:1.0
//
// Why (问题普查 2026-11-04, sub host_api_mismatch, 13 games): old adapters and hand-written platform layers read
// optional TikTok host fields directly and crash or pick the wrong branch when a field is missing:
//  - 躲雨小鸭 v16 / 指尖麻将 / 音乐消消乐 / 丛林荡藤: getSystemInfoSync().SDKVersion[0] throws when SDKVersion is
//    missing; 射击高手2048: SDKVersion[0] of '10.x' reads major version 1.
//  - 躲雨小鸭 v16: "isSubContext = getOpenDataContext === undefined", so a TikTok main package without that API
//    is treated as an open-data sub-context and loads no config.
// What it does: ONLY fills what is missing, never replaces a working API.
//  1. getSystemInfoSync: missing -> returns screen-size defaults; throws -> the same defaults (the error is
//     logged); a result without SDKVersion gets SDKVersion '0.0.0'. A normal result is returned as is.
//  2. canIUse missing -> answers from the real API: canIUse('name') is true only when sdk.name exists;
//     a dotted query ('a.b.c') answers false.
//  3. getOpenDataContext missing -> a no-op stub (postMessage does nothing, canvas null), so "=== undefined"
//     checks see the main domain. If the adapter already ran and set __globalAdapter.isSubContext = true only
//     because that API was missing, it is set back to false.
// Helpers for NEW code (use these instead of reading the fields yourself): parseVersion('10.2.1') -> [10, 2, 1]
// (missing or bad -> [0, 0, 0]), sdkVersion(sdk) -> that array for the running host.
// Node-tested (tests/host-shim.test.js); 待真机复测.
var VERSION = '1.0';
var MARK = '__tiktokKitHostShim';

function rootObject() {
  return typeof globalThis !== 'undefined' ? globalThis : typeof GameGlobal !== 'undefined' ? GameGlobal
    : typeof window !== 'undefined' ? window : {};
}

function parseVersion(value) {
  var out = [0, 0, 0];
  if (typeof value !== 'string' && typeof value !== 'number') return out;
  String(value).split('.').slice(0, 3).forEach(function (part, i) {
    var n = parseInt(part, 10);
    out[i] = isFinite(n) && n >= 0 ? n : 0;
  });
  return out;
}

function screenDefaults(root) {
  function num(v, d) { return typeof v === 'number' && isFinite(v) && v > 0 ? v : d; }
  var scr = root.screen || {};
  var w = num(root.innerWidth, num(scr.width, 375)), h = num(root.innerHeight, num(scr.height, 667));
  return {
    screenWidth: num(scr.width, w), screenHeight: num(scr.height, h), windowWidth: w, windowHeight: h,
    pixelRatio: num(root.devicePixelRatio, 2), SDKVersion: '0.0.0', platform: 'unknown', system: '', version: '',
    statusBarHeight: 0, safeArea: {left: 0, top: 0, right: w, bottom: h, width: w, height: h}, __kitShimDefaults: true
  };
}

function setIfMissing(api, name, value, report) {
  if (api[name] !== undefined && api[name] !== null) return false;
  try { api[name] = value; } catch (e) {}
  if (api[name] !== value) {
    try { Object.defineProperty(api, name, {value: value, configurable: true, writable: true, enumerable: false}); } catch (e) {}
  }
  if (api[name] === value) { report.filled.push(name); return true; }
  report.skipped.push(name);
  return false;
}

function shimOne(api, root, report) {
  if (!api || (typeof api !== 'object' && typeof api !== 'function')) return false;
  if (api[MARK]) return false;
  try { Object.defineProperty(api, MARK, {value: VERSION, enumerable: false, configurable: true}); } catch (e) {}

  // 1. getSystemInfoSync
  var original = typeof api.getSystemInfoSync === 'function' ? api.getSystemInfoSync : null;
  if (!original) {
    setIfMissing(api, 'getSystemInfoSync', function () { return screenDefaults(root); }, report);
  } else if (!original[MARK]) {
    var safe = function () {
      var info;
      try { info = original.apply(this, arguments); }
      catch (error) {
        try { console.error('[host-shim] getSystemInfoSync threw; using screen defaults', error && error.message || error); } catch (e) {}
        return screenDefaults(root);
      }
      if (!info || typeof info !== 'object') return screenDefaults(root);
      if (typeof info.SDKVersion !== 'string' || !info.SDKVersion) {
        try { info.SDKVersion = info.SDKVersion == null || info.SDKVersion === '' ? '0.0.0' : String(info.SDKVersion); } catch (e) {}
      }
      return info;
    };
    try { Object.defineProperty(safe, MARK, {value: VERSION}); } catch (e) {}
    try { api.getSystemInfoSync = safe; } catch (e) {}
    if (api.getSystemInfoSync === safe) report.filled.push('getSystemInfoSync(throw/SDKVersion guard)');
    else report.skipped.push('getSystemInfoSync');
  }

  // 2. canIUse
  setIfMissing(api, 'canIUse', function (name) {
    if (typeof name !== 'string' || !name || name.indexOf('.') >= 0) return false;
    var v = api[name];
    return typeof v === 'function' || (v !== undefined && v !== null && typeof v === 'object');
  }, report);

  // 3. getOpenDataContext: a TikTok main package is never an open-data sub-context
  var filledOdc = setIfMissing(api, 'getOpenDataContext', function () {
    return {postMessage: function () {}, canvas: null, __kitShim: true};
  }, report);
  if (filledOdc) {
    var ga = root.__globalAdapter;
    if (ga && ga !== api && ga.isSubContext === true && ga.getOpenDataContext === undefined) {
      try { ga.isSubContext = false; ga.getOpenDataContext = api.getOpenDataContext; report.filled.push('__globalAdapter.isSubContext=false'); } catch (e) {}
    }
  }
  return true;
}

function install(sdk, opts) {
  opts = opts || {};
  var root = opts.root || rootObject();
  var report = {version: VERSION, targets: 0, filled: [], skipped: []};
  var list = [];
  if (sdk) list.push(sdk);
  if (opts.alsoGlobals !== false) {
    try { if (root.TTMinis && root.TTMinis.game) list.push(root.TTMinis.game); } catch (e) {}
    try { if (root.tt) list.push(root.tt); } catch (e) {}
  }
  list.filter(function (api, i) { return list.indexOf(api) === i; }).forEach(function (api) {
    if (shimOne(api, root, report)) report.targets++;
  });
  return report;
}

function sdkVersion(sdk) {
  try { return parseVersion(sdk && typeof sdk.getSystemInfoSync === 'function' ? sdk.getSystemInfoSync().SDKVersion : ''); }
  catch (e) { return [0, 0, 0]; }
}

module.exports = {install: install, parseVersion: parseVersion, sdkVersion: sdkVersion, version: VERSION};
