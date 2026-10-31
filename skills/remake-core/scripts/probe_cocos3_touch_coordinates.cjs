'use strict';
// Cocos 3.x TikTok touch probe. TikTok touch points carry only identifier/screenX/screenY/force, while the
// Cocos 3.8 minigame TouchInputSource reads clientX/clientY. This runs the package's actual game.js prefix
// (web-adapter.js and every root module it requires before the SystemJS loader), then the engine's own SDK
// clone and its own TouchInputSource callbacks, and records the coordinates the engine touch manager receives.
// Not renderer, hit-test or device acceptance.
const vm = require('vm'), fs = require('fs'), posix = require('path').posix;

const INFO = {windowWidth: 390, windowHeight: 844, screenWidth: 390, screenHeight: 844, pixelRatio: 3,
  devicePixelRatio: 3, platform: 'android', system: 'Android 14', language: 'en', version: '38.0.0',
  SDKVersion: '3.0.0', safeArea: {left: 0, top: 0, right: 390, bottom: 844, width: 390, height: 844}};
const SCREEN = {width: INFO.windowWidth * INFO.pixelRatio, height: INFO.windowHeight * INFO.pixelRatio};
const PHASES = ['Start', 'Move', 'End', 'Cancel'];

class Stop extends Error {}

function stubCanvas() {
  const ctx = new Proxy({}, {get: (t, k) => (k in t ? t[k] : () => ({}))});
  return {width: INFO.windowWidth * INFO.pixelRatio, height: INFO.windowHeight * INFO.pixelRatio,
    getContext() { return ctx; }, addEventListener() {}, removeEventListener() {}, toDataURL() { return ''; }};
}

function makeSdk(files) {
  const listeners = {};
  const sdk = {};
  for (const phase of PHASES) {
    listeners[phase] = [];
    sdk['onTouch' + phase] = function (fn) { if (typeof fn === 'function') listeners[phase].push(fn); };
    sdk['offTouch' + phase] = function (fn) { const i = listeners[phase].indexOf(fn); if (i >= 0) listeners[phase].splice(i, 1); };
  }
  const storage = new Map();
  Object.assign(sdk, {
    getSystemInfoSync: () => JSON.parse(JSON.stringify(INFO)),
    getSystemInfo: o => o && o.success && o.success(JSON.parse(JSON.stringify(INFO))),
    createCanvas: stubCanvas,
    createImage: () => ({width: 0, height: 0, onload: null, onerror: null, set src(v) {}}),
    createInnerAudioContext: () => new Proxy({}, {get: (t, k) => (k in t ? t[k] : () => {})}),
    getStorageSync: k => (storage.has(k) ? storage.get(k) : ''), setStorageSync: (k, v) => { storage.set(k, v); },
    removeStorageSync: k => { storage.delete(k); }, clearStorageSync: () => storage.clear(),
    getStorageInfoSync: () => ({keys: [...storage.keys()], currentSize: 0, limitSize: 10240}),
    getFileSystemManager: () => ({
      readFileSync(path, encoding) {
        const key = posix.normalize(String(path).replace(/^\.?\//, ''));
        if (!(key in files)) throw Error('readFileSync:fail no such file or directory ' + path);
        return files[key];
      },
      accessSync(path) { if (!(posix.normalize(String(path)) in files)) throw Error('accessSync:fail ' + path); },
    }),
    getPerformance: () => ({now: () => Date.now()}),
    onShow() {}, offShow() {}, onHide() {}, offHide() {}, onError() {}, offError() {},
    onDeviceOrientationChange() {}, onWindowResize() {}, onNetworkStatusChange() {}, onAudioInterruptionBegin() {},
    onAudioInterruptionEnd() {}, onAccelerometerChange() {}, startAccelerometer() {}, stopAccelerometer() {},
    setPreferredFramesPerSecond() {}, triggerGC() {}, request() { return {abort() {}}; }, connectSocket() { return {}; },
    loadSubpackage() { return {onProgressUpdate() {}}; }, getLaunchOptionsSync: () => ({query: {}}),
  });
  return {sdk, listeners};
}

function engineParts(engine) {
  // Creator 3.8.8 builds mangle private names (_ccprivate$_createCallback); the probe runs this code in its own
  // scope only, so the prefix is dropped uniformly (W-D4 request 1).
  engine = engine.replace(/_ccprivate\$_/g, '_');
  // The engine binds a copy of the global SDK when cc is evaluated: `X=tt,Object.keys(X).forEach(...bind...)`.
  const clone = /([\w$]+)=([\w$]+),([\w$]+)=tt,Object\.keys\(\3\)\.forEach\(\(function\(([\w$]+)\)\{"function"!=typeof \3\[\4\]\?\1\[\4\]=\3\[\4\]:\1\[\4\]=\3\[\4\]\.bind\(\3\)\}\)\)/.exec(engine);
  if (!clone) throw Error('unsupported Cocos 3 SDK clone (expected Object.keys(tt) bind copy); do not mark input verified');
  const reg = /_registerEvent=function\(\)\{([\w$]+)\.onTouchStart\(this\._createCallback\("touch-start"\)\),\1\.onTouchMove\(this\._createCallback\("touch-move"\)\),\1\.onTouchEnd\(this\._createCallback\("touch-end"\)\),\1\.onTouchCancel\(this\._createCallback\("touch-cancel"\)\)\}/.exec(engine);
  if (!reg) throw Error('unsupported Cocos 3 minigame TouchInputSource; do not mark input verified');
  if (reg[1] !== clone[2]) throw Error('engine touch source does not read the cloned SDK object');
  const start = engine.indexOf('e._createCallback=function(t){', reg.index);
  const end = engine.indexOf(',e.on=function(', start);
  if (start < 0 || end < 0 || start - reg.index > 400) throw Error('unsupported Cocos 3 touch callback shape');
  const body = engine.slice(start, end);
  const screen = /=([\w$]+)\.windowSize,[\w$]+=\1\.devicePixelRatio/.exec(body);
  const manager = /([\w$]+)\.getOrCreateTouch\(/.exec(body);
  const event = /new ([\w$]+)\([\w$]+,!1,[\w$]+,/.exec(body);
  const vec = /_getLocation=function\([\w$]+,[\w$]+,[\w$]+\)\{[^}]*return new ([\w$]+)\([\w$]+,[\w$]+\)\}$/.exec(body);
  if (!screen || !manager || !event || !vec || !body.includes('.clientX') || !body.includes('.clientY'))
    throw Error('unsupported Cocos 3 touch location shape; do not mark input verified');
  return {cloneLoop: clone[0].slice(clone[0].indexOf('Object.keys(')), sdkName: clone[3], targetName: clone[1],
    body, names: {screen: screen[1], manager: manager[1], event: event[1], vec: vec[1]}};
}

function runPrefix(files, sdk) {
  // Executes the shipped game.js with its real root modules; SystemJS/polyfill bundles are not executed and the
  // first use of `System` ends the prefix (the engine is evaluated there, after every earlier install).
  const ctx = {tt: sdk, console: {log() {}, info() {}, warn() {}, error() {}, debug() {}, time() {}, timeEnd() {}},
    setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {}, requestAnimationFrame: () => 0,
    cancelAnimationFrame() {}, Date, Math, JSON, Promise, Number, String, Object, Array, Error, TypeError, Map, Set,
    WeakMap, Proxy, Reflect, Symbol, isFinite, isNaN, parseInt, parseFloat, Uint8Array, Float32Array, ArrayBuffer};
  ctx.window = ctx; ctx.globalThis = ctx; ctx.GameGlobal = ctx;
  // A vm global accessor does not fire on every Node build, so the SystemJS object itself ends the prefix.
  ctx.System = new Proxy({}, {get(target, key) { throw new Stop('System.' + String(key)); }});
  vm.createContext(ctx);
  const cache = {}, loaded = [];
  function load(name) {
    if (cache[name]) return cache[name].exports;
    const module = {exports: {}};
    cache[name] = module; loaded.push(name);
    const fn = vm.runInContext('(function(exports,require,module,__filename,__dirname){' + files[name] + '\n})', ctx,
      {filename: name, timeout: 2000});
    fn.call(module.exports, module.exports, makeRequire(name), module, name, posix.dirname(name));
    return module.exports;
  }
  function makeRequire(from) {
    return function require(request) {
      request = String(request);
      const base = request.startsWith('.') ? posix.join(posix.dirname(from), request) : request;
      const key = posix.normalize(base);
      if (key.startsWith('src/')) return {default: {}};  // polyfills, SystemJS, import map: engine loader territory
      for (const candidate of [key, key + '.js', key + '/index.js']) if (candidate in files) return load(candidate);
      throw Error('game.js prefix required a module the probe was not given: ' + request);
    };
  }
  let stopped = null;
  try { load('game.js'); } catch (e) { if (e instanceof Stop) stopped = e.message; else throw e; }
  return {stopped_at: stopped, executed_modules: loaded};
}

function probe(files, engine) {
  if (!files['game.js']) throw Error('game.js missing');
  if (!files['web-adapter.js']) throw Error('web-adapter.js missing; not a Cocos 3 TikTok package');
  const parts = engineParts(engine || '');
  const {sdk, listeners} = makeSdk(files);
  let prefix;
  try { prefix = runPrefix(files, sdk); } catch (e) { throw Error('game.js startup prefix threw before the engine loads: ' + e.message); }
  if (!prefix.executed_modules.includes('web-adapter.js')) throw Error('game.js did not load web-adapter.js before the engine');
  // Engine evaluation: its own SDK copy, then its own TouchInputSource registration through that copy.
  const received = [], raw = [], emitted = [];
  const scope = {};
  scope[parts.sdkName] = sdk;
  scope[parts.targetName] = {};
  scope[parts.names.screen] = {windowSize: SCREEN, devicePixelRatio: INFO.pixelRatio};
  scope[parts.names.manager] = {
    getOrCreateTouch(id, x, y) { const touch = {id, x, y}; received.push(touch); return touch; },
    releaseTouch() {}, getAllTouches() { return received.slice(-1); }};
  scope[parts.names.event] = function EventTouch(touches, bubbles, type) { this.touches = touches; this.type = type; };
  // Cocos 3.8 Vec2 stores `x || 0`, so a NaN location reaches the touch manager as 0: a finite, on-screen
  // (0, 0). The probe keeps that coercion and records the raw location, which is why it checks position too.
  scope[parts.names.vec] = function Vec2(x, y) { raw.push({x, y}); this.x = x || 0; this.y = y || 0; };
  scope.Object = Object;
  vm.createContext(scope);
  vm.runInContext(parts.cloneLoop, scope, {timeout: 1000});
  const source = {_eventTarget: {emit(type, event) { emitted.push(type); }}};
  vm.runInContext('(function(e){' + parts.body + '})', scope, {timeout: 1000})(source);
  const engineSdk = scope[parts.targetName];
  const before = {};
  for (const phase of PHASES) before[phase] = listeners[phase].length;
  const callbacks = {Start: 'touch-start', Move: 'touch-move', End: 'touch-end', Cancel: 'touch-cancel'};
  for (const phase of PHASES) {
    if (typeof engineSdk['onTouch' + phase] !== 'function') throw Error('engine SDK copy has no onTouch' + phase);
    engineSdk['onTouch' + phase](source._createCallback(callbacks[phase]));
  }
  const engineListeners = {};
  for (const phase of PHASES) {
    engineListeners[phase] = listeners[phase].slice(before[phase]);
    if (engineListeners[phase].length !== 1) throw Error('engine onTouch' + phase + ' did not reach the TikTok SDK exactly once');
  }
  function fire(phase, point) {
    const count = received.length, rawCount = raw.length;
    const event = {touches: phase === 'End' || phase === 'Cancel' ? [] : [point], changedTouches: [point], timeStamp: 1};
    for (const fn of engineListeners[phase]) fn.call(sdk, event);
    const show = v => (Number.isFinite(v) ? v : String(v));
    return {observed: received.slice(count).map(t => ({id: t.id, x: show(t.x), y: show(t.y)})),
      raw: raw.slice(rawCount).map(t => ({x: show(t.x), y: show(t.y)}))};
  }
  const inside = t => typeof t.x === 'number' && typeof t.y === 'number' && t.x >= 0 && t.x <= SCREEN.width && t.y >= 0 && t.y <= SCREEN.height;
  const sdkPoint = (x, y) => ({identifier: 0, screenX: x, screenY: y, force: 1});
  const rows = [];
  const dpr = INFO.pixelRatio;
  // Expected engine location for a full-screen game: clientX/clientY equal screenX/screenY, then the engine's own
  // DPR scale and Y flip. Pass only when it is finite, inside the screen and at that point (1 px tolerance).
  function row(id, point, result) {
    const x = point.clientX !== undefined ? point.clientX : point.screenX;
    const y = point.clientY !== undefined ? point.clientY : point.screenY;
    const expected = {x: x * dpr, y: SCREEN.height - y * dpr}, t = result.observed[0];
    const ok = result.observed.length === 1 && t.id === 0 && inside(t) &&
      Math.abs(t.x - expected.x) <= 1 && Math.abs(t.y - expected.y) <= 1;
    rows.push({id, passed: ok, sdk_touch: point, expected, observed: result.observed, raw_location: result.raw});
  }
  const center = sdkPoint(195, 422), topRight = sdkPoint(370, 40), bottomLeft = sdkPoint(20, 800), zero = sdkPoint(0, 0);
  for (const phase of PHASES) row('sdk_screen_' + phase.toLowerCase(), center, fire(phase, center));
  row('sdk_screen_top_right', topRight, fire('Start', topRight)); fire('End', topRight);
  row('sdk_screen_bottom_left', bottomLeft, fire('Start', bottomLeft)); fire('End', bottomLeft);
  row('sdk_screen_zero', zero, fire('Start', zero)); fire('End', zero);
  const client = {identifier: 0, clientX: 20, clientY: 30, force: 1};
  row('client_coordinates_preserved', client, fire('Start', client)); fire('End', client);
  return {schema: 'cocos3_touch_coordinates.v1', passed: rows.every(r => r.passed), screen: SCREEN,
    sdk_fields: ['identifier', 'screenX', 'screenY', 'force'], prefix, emitted: [...new Set(emitted)], rows,
    boundary: "package game.js -> web-adapter.js prefix, engine's own SDK copy and TouchInputSource callbacks, controlled SDK payloads; not renderer/hit-test/device acceptance"};
}

if (require.main === module) {
  try {
    const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
    const result = probe(payload.files || {}, payload.engine);
    console.log(JSON.stringify(result));
    process.exitCode = result.passed ? 0 : 1;
  } catch (e) {
    console.log(JSON.stringify({schema: 'cocos3_touch_coordinates.v1', passed: false, error: e.message}));
    process.exitCode = 1;
  }
}
module.exports = {probe};
