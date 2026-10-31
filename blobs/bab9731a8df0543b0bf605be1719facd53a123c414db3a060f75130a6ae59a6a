/* TikTok mini-game strict host for a Cocos 3.x bytedance build (runtime_regression.py, engine 3.x).
 * Runs the UNCHANGED package files (served at /) inside a separate global
 * object (GameGlobal), like the native runtime, and provides a fake `tt` SDK.
 * Faults are chosen with ?fault=a,b and ads with ?ads=complete,cancel,...
 * Source: LunasJade v0.10.0/v0.10.1 QA host (docs/fix-2026-10-28/host, D3), made game-generic for
 * the Skill: subpackage sizes come from the server (/__host/sizes.json), no game component names,
 * every log row is mirrored to window.__hostLog and posted to /__log (runtime_regression lib.mjs).
 * Faults: webp_nodecode, webp_slow, img_events_only, res_fail[N], res_hang[N], res_stall[N] (also
 * wasm_*), modal_nocb, storage_throw, caniuse_false, no_ads, no_ttminis, firstrun; bps=<bytes/s>.
 * Test-only file: never part of the game package. Not a phone pass.
 */
(function () {
'use strict';
const Q = new URLSearchParams(location.search);
const F = new Set((Q.get('fault') || '').split(',').filter(Boolean));
// v7.8 (总表 B30): ad=<policy> is the same as ads=<policy> (the 2.x host query name)
const ADS = (Q.get('ads') || Q.get('ad') || '').split(',').filter(Boolean);
let W = +(Q.get('w') || 393), H = +(Q.get('h') || 852), DPR = +(Q.get('dpr') || 3);
// ---- v7.8 (总表 B30, 全民飞车门禁 2026-10-30): the same switches as the 2.x host ad_regression/host.js ----
// dev=iphone14|se: device profile measured from real phones (points); the gate sets the page viewport to W x H.
// capsule=pt (default) | px: getMenuButtonBoundingClientRect in points, or every value multiplied by pixelRatio
// (what Saul's iPhone TikTok returned on 2026-10-29); getSystemInfoSync stays in points.
// reset=1: start from an empty save (same as fresh=1). window.__gateLog / __gateNow / __gateDevice / __adStats.
const DEVS = {
  iphone14: { model: 'iPhone 14', W: 390, H: 844, pr: 3, sb: 47, cap: { left: 293, top: 51, right: 380, bottom: 83 }, safeBottom: 810 },
  se: { model: 'iPhone SE', W: 375, H: 667, pr: 2, sb: 20, cap: { left: 278, top: 24, right: 365, bottom: 56 }, safeBottom: 667 },
};
const DEV = DEVS[Q.get('dev') || ''] || null;
let CAPK = 1;
if (DEV) { W = DEV.W; H = DEV.H; DPR = DEV.pr; CAPK = Q.get('capsule') === 'px' ? DEV.pr : 1; }
window.__gateDevice = DEV ? { name: Q.get('dev'), W, H, pixelRatio: DPR, statusBarHeight: DEV.sb, capsule: DEV.cap, capsuleUnit: CAPK === 1 ? 'pt' : 'px', capsuleK: CAPK, safeBottom: DEV.safeBottom, host: 'host3x' } : null;
const PNow = performance.now.bind(performance);
const GATE = window.__gateLog = [];
function gateLog(kind, data) { GATE.push({ t: Math.round(PNow()), kind, data }); }
window.__gateNow = () => Math.round(PNow());
const AD = window.__adStats = { created: 0, reused: 0, shown: 0, closedEnded: 0, closedEarly: 0, errors: 0, live: 0, units: {} };
const STORE = 'RR3:' + (Q.get('store') || 'default') + ':';
const T0 = performance.now();
const now = () => Math.round(performance.now() - T0);
const X = window.__H = { log: [], faults: [...F], modals: [], ads: [], firstErr: null, marks: {}, missing: {} };
const NXHR = window.XMLHttpRequest;
window.__hostLog = [];
const KIND = { 'window.error': 'error', unhandledrejection: 'rejection', 'boot.throw': 'boot-throw', 'net.request': 'net-request', 'net.download': 'net-download' };
function beacon(kind, data) {
  const row = { t: now(), kind, data };
  window.__hostLog.push(row);
  try { const x = new NXHR(); x.open('POST', '/__log', true); x.setRequestHeader('Content-Type', 'application/json'); x.send(JSON.stringify(row)); } catch (_) {}
}
function log(k, v) {
  const s = v === undefined ? '' : (typeof v === 'string' ? v : JSON.stringify(v)).slice(0, 400);
  X.log.push([now(), k, s]);
  if (KIND[k]) beacon(KIND[k], /^net-/.test(KIND[k]) ? { url: s } : s);
  else if (k === 'mark' || /^(sub\.|img\.webp_refused|img\.onload_property_ignored|modal\.|ad\.show|tt\.missing|audio\.error)/.test(k)) beacon(k, s);
}
function mark(k) { if (!(k in X.marks)) { X.marks[k] = now(); log('mark', k); } }
window.addEventListener('error', e => { log('window.error', String(e.message) + ' @' + (e.filename || '') + ':' + e.lineno); X.firstErr = X.firstErr || String(e.message); });
window.addEventListener('unhandledrejection', e => { const r = e.reason; log('unhandledrejection', String(r && r.stack || r && r.errMsg || r)); X.firstErr = X.firstErr || String(r && r.message || r); });
const oc = { error: console.error.bind(console), warn: console.warn.bind(console), log: console.log.bind(console) };
console.error = (...a) => { log('console.error', a.map(x => x && x.stack || (typeof x === 'object' ? JSON.stringify(x) : String(x))).join(' ')); oc.error(...a); };
console.warn = (...a) => { log('console.warn', a.map(x => typeof x === 'object' ? JSON.stringify(x) : String(x)).join(' ')); oc.warn(...a); };
console.log = (...a) => { const s = a.map(String).join(' '); if (/subpac|fail|error|wasm|spine|\[boot\]/i.test(s)) log('console.log', s); oc.log(...a); };
for (const k of ['cv', 'ov', 'ad', 'spin']) { const el = document.getElementById(k); el.style.width = W + 'px'; el.style.height = H + 'px'; }
// The adapter replaces canvas.style with a plain object, so pin the display size in a stylesheet.
{ const st = document.createElement('style'); st.textContent = '#cv{width:' + W + 'px!important;height:' + H + 'px!important}'; document.head.appendChild(st); }

// ---------- files ----------
function clean(p) {
  p = String(p);
  if (/(^|\/)\.\.(\/|$)/.test(p)) log('fs.parent_path', p);
  p = p.replace(/^\.\//, '').replace(/^\/+/, '');
  const out = []; for (const s of p.split('/')) { if (s === '..') out.pop(); else if (s && s !== '.') out.push(s); }
  return out.join('/');
}
function xhrSync(path, mode) {
  const x = new XMLHttpRequest(); x.open(mode === 'HEAD' ? 'HEAD' : 'GET', '/' + path, false);
  if (mode === 'bin') x.overrideMimeType('text/plain; charset=x-user-defined');
  x.send(); if (x.status !== 200) return null; if (mode === 'HEAD') return true;
  if (mode !== 'bin') return x.responseText;
  const s = x.responseText, u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; return u.buffer;
}
const userFS = new Map();
const isUser = p => String(p).startsWith('ttfile://');
function existsSync(p) { return isUser(p) ? userFS.has(String(p)) : !!xhrSync(clean(p), 'HEAD'); }
function readSync(p, enc) {
  if (isUser(p)) { if (!userFS.has(String(p))) throw new Error('readFileSync:fail no such file or directory ' + p); return userFS.get(String(p)); }
  const v = xhrSync(clean(p), enc ? 'text' : 'bin'); if (v == null) throw new Error('readFileSync:fail no such file or directory ' + p); return v;
}
const later = fn => setTimeout(fn, 0);
const cb = (o, ok, res) => later(() => { try { ok ? o.success && o.success(res) : o.fail && o.fail(res); } finally { o.complete && o.complete(res); } });
const FS = {
  access(o) { const ok = existsSync(o.path); if (!ok) log('fs.access_miss', o.path); cb(o, ok, ok ? { errMsg: 'access:ok' } : { errMsg: 'access:fail no such file or directory ' + o.path }); },
  accessSync(p) { if (!existsSync(p)) throw new Error('accessSync:fail no such file or directory ' + p); },
  readFile(o) {
    if (isUser(o.filePath)) { const has = userFS.has(o.filePath); return cb(o, has, has ? { data: userFS.get(o.filePath) } : { errMsg: 'readFile:fail no such file' }); }
    const url = '/' + clean(o.filePath);
    const r = new XMLHttpRequest(); r.open('GET', url, true); if (!o.encoding) r.responseType = 'arraybuffer';
    r.onload = () => { if (r.status === 200) cb(o, true, { data: o.encoding ? r.responseText : r.response }); else { log('fs.read_miss', o.filePath); cb(o, false, { errMsg: 'readFile:fail no such file or directory ' + o.filePath }); } };
    r.onerror = () => cb(o, false, { errMsg: 'readFile:fail io error' }); r.send();
  },
  readFileSync(p, enc) { return readSync(p, enc); },
  writeFile(o) { userFS.set(String(o.filePath), o.data); cb(o, true, {}); }, writeFileSync(p, d) { userFS.set(String(p), d); },
  appendFile(o) { cb(o, true, {}); }, mkdir(o) { cb(o, true, {}); }, mkdirSync() {}, rmdir(o) { cb(o, true, {}); }, rmdirSync() {},
  unlink(o) { userFS.delete(String(o.filePath)); cb(o, true, {}); }, unlinkSync(p) { userFS.delete(String(p)); },
  readdir(o) { cb(o, false, { errMsg: 'readdir:fail no such directory' }); }, readdirSync() { return []; },
  stat(o) { const ok = existsSync(o.path); cb(o, ok, ok ? { stats: { isFile: () => true, isDirectory: () => false, size: 1 } } : { errMsg: 'stat:fail' }); },
  statSync(p) { if (!existsSync(p)) throw new Error('statSync:fail'); return { isFile: () => true, isDirectory: () => false, size: 1 }; },
  getFileInfo(o) { const ok = existsSync(o.filePath); cb(o, ok, ok ? { size: 1 } : { errMsg: 'getFileInfo:fail' }); },
  copyFile(o) { cb(o, false, { errMsg: 'copyFile:fail' }); }, saveFile(o) { cb(o, false, { errMsg: 'saveFile:fail' }); },
  getSavedFileList(o) { cb(o, true, { fileList: [] }); }, removeSavedFile(o) { cb(o, true, {}); }, unzip(o) { cb(o, false, { errMsg: 'unzip:fail' }); },
};

// ---------- separate global object ----------
const GT = Object.create(null);
const DENY = new Set(['window', 'self', 'document', 'location', 'navigator', 'Image', 'Audio', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'canvas',
  'addEventListener', 'removeEventListener', 'dispatchEvent', 'top', 'parent', 'frames', 'innerWidth', 'innerHeight', 'devicePixelRatio', 'screen',
  'ontouchstart', 'FontFace', 'DOMParser', 'Worker', 'WebSocket', 'alert', 'prompt', 'confirm', 'history', 'customElements', 'visualViewport',
  'getComputedStyle', 'matchMedia', 'WebAssembly', 'fetch', 'indexedDB', 'caches', 'HTMLElement', 'HTMLCanvasElement', 'HTMLImageElement',
  'HTMLAudioElement', 'HTMLVideoElement', 'Event', 'TouchEvent', 'MouseEvent', 'KeyboardEvent', 'Element', 'Node', 'pageXOffset', 'pageYOffset', 'scrollX', 'scrollY']);
const BIND = new Set(['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'requestAnimationFrame', 'cancelAnimationFrame', 'atob', 'btoa', 'queueMicrotask']);
const bound = {};
const RESERVED = new Set(['__G', '__FAST', 'arguments', 'require', 'module', 'exports', '__filename', '__dirname']);
const G = new Proxy(GT, {
  has(t, k) { return typeof k === 'string' && !RESERVED.has(k); },
  get(t, k) {
    if (k === Symbol.unscopables) return undefined;
    if (k in t) return t[k];
    if (typeof k !== 'string' || DENY.has(k)) return undefined;
    const v = window[k];
    if (typeof v === 'function' && BIND.has(k)) return bound[k] || (bound[k] = v.bind(window));
    return v;
  },
  set(t, k, v) { t[k] = v; return true; },
  deleteProperty(t, k) { delete t[k]; return true; },
  defineProperty(t, k, d) { Object.defineProperty(t, k, d); return true; },
});
GT.GameGlobal = G; GT.globalThis = G;
X.G = G;

// module loader (CommonJS, paths relative to the requiring file, then package root)
const FAST = ['Math', 'Object', 'Array', 'Number', 'String', 'Boolean', 'JSON', 'Date', 'Promise', 'Symbol', 'Map', 'Set', 'WeakMap', 'Error', 'TypeError',
  'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'Reflect', 'ArrayBuffer', 'DataView', 'Float32Array', 'Float64Array', 'Int8Array', 'Int16Array', 'Int32Array',
  'Uint8Array', 'Uint16Array', 'Uint32Array', 'Uint8ClampedArray', 'RegExp', 'Function'];
const modules = {};
function resolve(dir, req) {
  const cands = [];
  const rel = (req.startsWith('./') || req.startsWith('../')) ? clean((dir ? dir + '/' : '') + req) : null;
  if (rel !== null) cands.push(rel); else { cands.push(clean((dir ? dir + '/' : '') + req)); cands.push(clean(req)); }
  for (const c of cands) { for (const p of [c, c + '.js', c + '/index.js']) { if (modules[p] || /\.js$/.test(p) && xhrSync(p, 'HEAD')) return p; } }
  throw new Error("module '" + req + "' is not defined (from " + (dir || '/') + ')');
}
function load(p) {
  if (modules[p]) return modules[p].exports;
  const code = xhrSync(p, 'text'); if (code == null) throw new Error('module file missing: ' + p);
  const module = { exports: {} }; modules[p] = module;
  const dir = p.split('/').slice(0, -1).join('/');
  const fn = new Function('__G', '__FAST',
    'with(__G){return (function(' + FAST.join(',') + ',require,module,exports,__filename,__dirname){' + code + '\n}).apply(this,__FAST);}\n//# sourceURL=' + location.origin + '/' + p);
  log('require', p); beacon('require', { path: p });
  fn.call(module.exports, G, FAST.map(k => window[k]).concat([makeRequire(dir), module, module.exports, p, dir]));
  return module.exports;
}
function makeRequire(dir) { return function require(req) { return load(resolve(dir, String(req))); }; }

// ---------- canvas, image, audio, font ----------
const main = document.getElementById('cv');
main.width = W; main.height = H;
let canvasN = 0;
const ogc = main.getContext.bind(main);
main.getContext = function (type, attrs) {
  const ctx = ogc(type, attrs);
  if (ctx && /webgl/.test(type) && !ctx.__wrapped) {
    ctx.__wrapped = true;
    for (const m of ['drawElements', 'drawArrays']) { const o = ctx[m].bind(ctx); ctx[m] = function () { if (!X.marks.firstDraw) { mark('firstDraw'); document.getElementById('spin').style.display = 'none'; } return o.apply(null, arguments); }; }
  }
  return ctx;
};
class TTImage extends HTMLImageElement {
  set src(v) {
    const raw = String(v); let u = raw;
    if (!/^(data:|blob:|https?:)/.test(u)) u = '/' + clean(u);
    if (F.has('webp_nodecode') && (/\.webp($|\?)/.test(raw) || /^data:image\/webp/.test(raw))) { log('img.webp_refused', raw.slice(0, 80)); u = '/__host/__no_such_image__.webp'; }
    // fault webp_slow: WebP data URIs decode 800 ms late (decoder works, just slower than the engine's 500 ms check)
    if (F.has('webp_slow') && /^data:image\/webp/.test(raw)) { log('img.webp_slow', raw.slice(0, 40)); setTimeout(() => { super.src = u; }, 800); return; }
    if (/\.webp($|\?)/.test(raw)) { const t0 = now(); log('img.webp', raw.slice(-24)); this.addEventListener('load', () => log('img.webp_loaded', raw.slice(-24) + ' ' + (now() - t0) + 'ms ' + this.width + 'x' + this.height)); }
    super.src = u;
  }
  get src() { return super.src; }
  // fault img_events_only: the image object fires load/error events but ignores onload/onerror properties
  set onload(f) { if (F.has('img_events_only')) { this._ol = f; log('img.onload_property_ignored'); } else super.onload = f; }
  get onload() { return F.has('img_events_only') ? this._ol || null : super.onload; }
  set onerror(f) { if (F.has('img_events_only')) this._oe = f; else super.onerror = f; }
  get onerror() { return F.has('img_events_only') ? this._oe || null : super.onerror; }
}
customElements.define('tt-image', TTImage, { extends: 'img' });
class TTAudio {
  constructor() { this.a = new Audio(); this.a.muted = true; this.h = {}; this._src = ''; this._vol = 1;
    const fire = (k, e) => (this.h[k] || []).slice().forEach(f => { try { f(e || {}); } catch (err) { log('audio.cb_err', String(err)); } });
    this.a.addEventListener('canplay', () => fire('Canplay')); this.a.addEventListener('play', () => fire('Play')); this.a.addEventListener('pause', () => fire('Pause'));
    this.a.addEventListener('ended', () => fire('Ended')); this.a.addEventListener('timeupdate', () => fire('TimeUpdate')); this.a.addEventListener('waiting', () => fire('Waiting'));
    this.a.addEventListener('seeked', () => fire('Seeked')); this.a.addEventListener('seeking', () => fire('Seeking'));
    this.a.addEventListener('error', () => { log('audio.error', this._src); fire('Error', { errMsg: 'audio error', errCode: 10001 }); });
    for (const k of ['Canplay', 'Play', 'Pause', 'Stop', 'Ended', 'Error', 'TimeUpdate', 'Waiting', 'Seeking', 'Seeked']) {
      this['on' + k] = f => (this.h[k] = this.h[k] || []).push(f);
      this['off' + k] = f => { if (!f) this.h[k] = []; else this.h[k] = (this.h[k] || []).filter(x => x !== f); };
    }
    this._fire = fire;
  }
  get src() { return this._src; } set src(v) { this._src = String(v); this.a.src = /^(https?:|data:)/.test(v) ? v : '/' + clean(v); }
  get loop() { return this.a.loop; } set loop(v) { this.a.loop = !!v; }
  get autoplay() { return this.a.autoplay; } set autoplay(v) { this.a.autoplay = !!v; }
  get volume() { return this._vol; } set volume(v) { this._vol = v; }
  get currentTime() { return this.a.currentTime; } get duration() { return this.a.duration || 0; } get paused() { return this.a.paused; }
  get startTime() { return 0; } set startTime(v) {} get buffered() { return this.a.duration || 0; } get obeyMuteSwitch() { return true; } set obeyMuteSwitch(v) {}
  play() { const p = this.a.play(); if (p && p.catch) p.catch(() => {}); } pause() { this.a.pause(); } stop() { this.a.pause(); try { this.a.currentTime = 0; } catch (e) {} this._fire('Stop'); }
  seek(t) { try { this.a.currentTime = t; } catch (e) {} } destroy() { this.a.pause(); this.a.src = ''; }
}
let fontN = 0;

// ---------- storage ----------
if (F.has('firstrun') || Q.get('fresh') === '1' || Q.get('reset') === '1') Object.keys(localStorage).filter(k => k.startsWith(STORE)).forEach(k => localStorage.removeItem(k));
const storage = {
  get(k) { const v = localStorage.getItem(STORE + k); if (v == null) return ''; try { return JSON.parse(v).v; } catch (e) { return ''; } },
  set(k, v) { if (F.has('storage_throw')) throw new Error('setStorageSync:fail exceeded'); localStorage.setItem(STORE + k, JSON.stringify({ v })); },
  keys() { return Object.keys(localStorage).filter(k => k.startsWith(STORE)).map(k => k.slice(STORE.length)); },
};
X.storage = storage;

// ---------- touch ----------
const touchCbs = { Start: [], Move: [], End: [], Cancel: [] };
const active = new Map();
function tp(e) { const r = main.getBoundingClientRect(); const x = e.clientX - r.left, y = e.clientY - r.top; return { identifier: e.pointerId, clientX: x, clientY: y, pageX: x, pageY: y, force: 1 }; }
function emitTouch(kind, e) {
  const t = tp(e);
  if (kind === 'Start') active.set(e.pointerId, t); else if (kind === 'Move') { if (!active.has(e.pointerId)) return; active.set(e.pointerId, t); } else active.delete(e.pointerId);
  const ev = { touches: [...active.values()], changedTouches: [t], timeStamp: e.timeStamp };
  X.touches = (X.touches || 0) + 1; if (kind !== 'Move') log('touch.' + kind, Math.round(t.clientX) + ',' + Math.round(t.clientY));
  touchCbs[kind].slice().forEach(f => { try { f(ev); } catch (err) { log('touch.cb_err', String(err && err.stack || err)); } });
}
main.addEventListener('pointerdown', e => { main.setPointerCapture(e.pointerId); emitTouch('Start', e); });
main.addEventListener('pointermove', e => emitTouch('Move', e));
main.addEventListener('pointerup', e => emitTouch('End', e));
main.addEventListener('pointercancel', e => emitTouch('Cancel', e));

// ---------- subpackages ----------
const GJ = JSON.parse(xhrSync('game.json', 'text'));
const roots = {}; (GJ.subpackages || []).forEach(s => { roots[s.name] = s.root; });
// Real byte size of each subpackage root, computed by server.py from the package on disk.
const SIZES = (() => { try { return JSON.parse(xhrSync('__host/sizes.json', 'text')) || {}; } catch (_) { return {}; } })();
const loaded = new Set(), attempts = {};
function subFault(name, n) {
  const kind = name === 'resources' ? 'res' : 'wasm';
  for (const m of ['fail', 'hang', 'stall']) if (F.has(kind + '_' + m + n) || F.has(kind + '_' + m)) return m;
  return 'ok';
}
function loadSubpackage(o) {
  const name = o.name; const n = attempts[name] = (attempts[name] || 0) + 1; const mode = subFault(name, n);
  log('sub.request', name + ' #' + n + ' ' + mode);
  // v7.8 (B30): the same subpackage beacons as the 2.x host (startup download size, "home = nothing still downloading")
  beacon('subpackage', { name, attempt: n, fault: mode });
  const pcbs = []; const task = { onProgressUpdate(f) { pcbs.push(f); }, offProgressUpdate() {} };
  if (!roots[name]) { beacon('subpackage-fail', { name, msg: 'not found' }); cb(o, false, { errMsg: 'loadSubpackage:fail subpackage not found' }); return task; }
  if (loaded.has(name)) { beacon('subpackage-ok', { name, attempt: n, cached: true }); cb(o, true, { errMsg: 'loadSubpackage:ok' }); return task; }
  if (mode === 'hang') return task;
  const total = SIZES[name] || 500000, bps = +(Q.get('bps') || 2e7); let got = 0;
  const finish = () => {
    if (mode === 'fail') { log('sub.fail', name); beacon('subpackage-fail', { name, msg: 'network error' }); cb(o, false, { errMsg: 'loadSubpackage:fail network error' }); return; }
    try { const entry = clean(roots[name] + 'game.js'); if (xhrSync(entry, 'HEAD')) load(entry); loaded.add(name); log('sub.ok', name); beacon('subpackage-ok', { name, attempt: n }); cb(o, true, { errMsg: 'loadSubpackage:ok' }); }
    catch (e) { log('sub.exec_error', String(e && e.stack || e)); beacon('subpackage-fail', { name, msg: String(e) }); cb(o, false, { errMsg: String(e) }); }
  };
  const step = () => {
    got = Math.min(total, got + bps * 0.2);
    if (mode === 'stall' && got > total * 0.4) { log('sub.stalled', name); return; }
    pcbs.forEach(f => f({ progress: Math.floor(got / total * 100), totalBytesWritten: got, totalBytesExpectedToWrite: total }));
    if (got < total) setTimeout(step, 200); else finish();
  };
  setTimeout(step, 30);
  return task;
}

// ---------- modal / ads / growth ----------
function showModal(o) {
  o = o || {}; X.modals.push({ t: now(), title: o.title, content: o.content }); log('modal.show', o.title + ' | ' + o.content);
  gateLog('modal', o.title || o.content); beacon('modal', { title: o.title, content: o.content, confirmText: o.confirmText });
  const ov = document.getElementById('ov'); document.getElementById('ovt').textContent = o.title || ''; document.getElementById('ovc').textContent = o.content || '';
  const b = document.getElementById('ovb'); b.textContent = o.confirmText || 'OK'; ov.style.display = 'flex';
  b.onclick = () => { ov.style.display = 'none'; log('modal.confirm', o.title); if (F.has('modal_nocb')) { log('modal.no_callback', o.title); return; } cb(o, true, { confirm: true, cancel: false }); };
}
let adSeq = 0;
function createRewardedVideoAd(opt) {
  const id = ++adSeq; const unit = opt && opt.adUnitId; log('ad.create', id + ' ' + unit);
  AD.created++; AD.units[unit] = (AD.units[unit] || 0) + 1; gateLog('ad-create', unit); beacon('ad-create', unit);
  const h = { close: [], error: [], load: [] }; let destroyed = false;
  const fire = (k, e) => h[k].slice().forEach(f => { try { f(e); } catch (err) { log('ad.cb_err', String(err)); } });
  return {
    onClose(f) { h.close.push(f); }, offClose(f) { h.close = h.close.filter(x => x !== f); },
    onError(f) { h.error.push(f); }, offError(f) { h.error = h.error.filter(x => x !== f); },
    onLoad(f) { h.load.push(f); }, offLoad(f) { h.load = h.load.filter(x => x !== f); },
    load() { return Promise.resolve(); }, destroy() { destroyed = true; log('ad.destroy', id); },
    show() {
      const showN = X.ads.length; const mode = ADS[showN] || ADS[ADS.length - 1] || 'complete';
      X.ads.push({ id, unit, mode, t: now() }); log('ad.show', id + ' ' + mode + ' ' + unit);
      AD.shown++; gateLog('ad-show', unit); beacon('ad-show', { unit, policy: mode });
      if (destroyed) return Promise.reject({ errMsg: 'show:fail destroyed' });
      if (mode === 'reject') { AD.errors++; return Promise.reject({ errMsg: 'show:fail no ad', errCode: 1004 }); }
      if (mode === 'error') { AD.errors++; setTimeout(() => fire('error', { errMsg: 'ad load error', errCode: 1004 }), 300); return Promise.resolve(); }
      if (mode === 'hang') return Promise.resolve();
      const el = document.getElementById('ad'); el.style.display = 'flex'; el.textContent = 'Rewarded video (' + mode + ')';
      setTimeout(() => { el.style.display = 'none'; log('ad.close', id + ' ended=' + (mode === 'complete')); AD[mode === 'complete' ? 'closedEnded' : 'closedEarly']++; fire('close', { isEnded: mode === 'complete' }); }, mode === 'complete' ? 1500 : 700);
      return Promise.resolve();
    },
  };
}

// ---------- tt ----------
const showCbs = [], hideCbs = [];
const sys = { brand: 'Apple', model: DEV ? DEV.model : 'iPhone', pixelRatio: DPR, devicePixelRatio: DPR, screenWidth: W, screenHeight: H, windowWidth: W, windowHeight: H,
  statusBarHeight: DEV ? DEV.sb : 47, language: 'en', version: '34.0.0', system: 'iOS 17.5', platform: Q.get('os') || 'ios', SDKVersion: Q.get('sdk') || '3.9.0', appName: 'TikTok',
  safeArea: DEV ? { top: DEV.sb, left: 0, right: W, bottom: DEV.safeBottom, width: W, height: DEV.safeBottom - DEV.sb } : { top: 47, left: 0, right: W, bottom: H - 34, width: W, height: H - 81 },
  deviceOrientation: 'portrait', benchmarkLevel: 30 };
const tt = {
  env: { USER_DATA_PATH: 'ttfile://user' },
  getSystemInfoSync: () => Object.assign({}, sys, { safeArea: Object.assign({}, sys.safeArea) }),
  getSystemInfo(o) { cb(o, true, tt.getSystemInfoSync()); },
  getLaunchOptionsSync: () => ({ scene: '011004', query: {}, path: '' }), getEnterOptionsSync: () => ({ scene: '011004', query: {} }),
  getMenuButtonBoundingClientRect: () => {
    const c = DEV ? DEV.cap : { top: 52, left: W - 95, right: W - 8, bottom: 84 }, k = CAPK;
    const r = { top: c.top * k, left: c.left * k, right: c.right * k, bottom: c.bottom * k, width: (c.right - c.left) * k, height: (c.bottom - c.top) * k };
    gateLog('capsule-rect', r); return r;
  },
  onShow(f) { showCbs.push(f); }, offShow(f) { const i = showCbs.indexOf(f); if (i >= 0) showCbs.splice(i, 1); },
  onHide(f) { hideCbs.push(f); }, offHide(f) { const i = hideCbs.indexOf(f); if (i >= 0) hideCbs.splice(i, 1); },
  onError(f) {}, offError() {}, onMemoryWarning() {}, onWindowResize() {}, offWindowResize() {}, onAudioInterruptionBegin() {}, onAudioInterruptionEnd() {},
  offAudioInterruptionBegin() {}, offAudioInterruptionEnd() {}, setKeepScreenOn(o) { o && cb(o, true, {}); }, triggerGC() {},
  createCanvas() { canvasN++; if (canvasN === 1) { log('canvas.main', W + 'x' + H); return main; } return document.createElement('canvas'); },
  createImage: () => new TTImage(),
  createInnerAudioContext: () => new TTAudio(),
  loadFont(p) { const fam = 'ttfont' + (++fontN); try { const ff = new FontFace(fam, 'url(/' + clean(p) + ')'); ff.load().then(f => document.fonts.add(f)).catch(() => log('font.fail', p)); } catch (e) { log('font.err', String(e)); } return fam; },
  getFileSystemManager: () => FS,
  loadSubpackage,
  getStorageSync: k => storage.get(k), setStorageSync: (k, v) => storage.set(k, v),
  removeStorageSync: k => localStorage.removeItem(STORE + k), clearStorageSync: () => storage.keys().forEach(k => localStorage.removeItem(STORE + k)),
  getStorageInfoSync: () => ({ keys: storage.keys(), currentSize: 1, limitSize: 10240 }),
  getStorage(o) { cb(o, true, { data: storage.get(o.key) }); }, setStorage(o) { try { storage.set(o.key, o.data); cb(o, true, {}); } catch (e) { cb(o, false, { errMsg: String(e) }); } },
  onTouchStart: f => touchCbs.Start.push(f), onTouchMove: f => touchCbs.Move.push(f), onTouchEnd: f => touchCbs.End.push(f), onTouchCancel: f => touchCbs.Cancel.push(f),
  offTouchStart() {}, offTouchMove() {}, offTouchEnd() {}, offTouchCancel() {},
  onAccelerometerChange() {}, offAccelerometerChange() {}, startAccelerometer(o) { o && cb(o, true, {}); }, stopAccelerometer(o) { o && cb(o, true, {}); },
  onDeviceOrientationChange() {}, offDeviceOrientationChange() {},
  getNetworkType(o) { cb(o, true, { networkType: 'wifi' }); }, onNetworkStatusChange() {}, offNetworkStatusChange() {},
  request(o) { log('net.request', o && o.url); cb(o, false, { errMsg: 'request:fail offline in simulator' }); return { abort() {} }; },
  downloadFile(o) { log('net.download', o && o.url); cb(o, false, { errMsg: 'downloadFile:fail offline in simulator' }); return { onProgressUpdate() {}, abort() {} }; },
  connectSocket() { return { onOpen() {}, onClose() {}, onError() {}, onMessage() {}, send() {}, close() {} }; },
  getUpdateManager: () => ({ onCheckForUpdate() {}, onUpdateReady() {}, onUpdateFailed() {}, applyUpdate() {} }),
  showModal, showToast(o) { log('toast', o && o.title); gateLog('toast', o && o.title); beacon('toast', o && o.title); o && cb(o, true, {}); }, hideToast() {}, showLoading(o) { log('showLoading', o && o.title); }, hideLoading() {},
  vibrateShort(o) { log('vibrate', 'short'); beacon('vibrate', 'short'); o && cb(o, true, {}); }, vibrateLong(o) { beacon('vibrate', 'long'); o && cb(o, true, {}); },
  createRewardedVideoAd,
  addShortcut(o) { log('growth.addShortcut'); beacon('mission', 'addShortcut'); cb(o, true, {}); }, getShortcutMissionReward(o) { beacon('mission', 'getShortcutMissionReward'); cb(o, true, { canReceiveReward: F.has('growth_yes') }); },
  startEntranceMission(o) { log('growth.startEntranceMission'); beacon('mission', 'startEntranceMission'); cb(o, true, {}); }, getEntranceMissionReward(o) { beacon('mission', 'getEntranceMissionReward'); cb(o, true, { canReceiveReward: F.has('growth_yes') }); },
  setPreferredFramesPerSecond() {}, getBatteryInfoSync: () => ({ level: 80, isCharging: false }), getPerformance: () => performance,
  showKeyboard() {}, hideKeyboard() {}, onKeyboardInput() {}, offKeyboardInput() {}, onKeyboardConfirm() {}, offKeyboardConfirm() {}, onKeyboardComplete() {}, offKeyboardComplete() {},
};
tt.canIUse = name => { if (F.has('caniuse_false')) return false; return typeof tt[String(name).split('.')[0]] === 'function'; };
if (F.has('no_ads')) delete tt.createRewardedVideoAd;
// Names starting with __ are kit / host markers (tiktok-touch-3x.js reads tt.__tiktokKitTouch3x to see whether it is
// installed), never SDK APIs, so they are not logged as missing (W-D4 request 6).
const ttProxy = new Proxy(tt, { get(t, k) { if (typeof k === 'string' && !k.startsWith('__') && !(k in t) && !X.missing[k]) { X.missing[k] = now(); log('tt.missing', k); } return t[k]; } });
GT.tt = ttProxy;
if (!F.has('no_ttminis')) GT.TTMinis = { game: ttProxy };
GT.TTWebAssembly = Object.assign({}, WebAssembly, {
  Memory: WebAssembly.Memory, Table: WebAssembly.Table, Module: WebAssembly.Module, Instance: WebAssembly.Instance, RuntimeError: WebAssembly.RuntimeError,
  instantiate(src, imports) { if (typeof src === 'string') { const buf = readSync(src); log('wasm.instantiate', src); return WebAssembly.instantiate(buf, imports); } return WebAssembly.instantiate(src, imports); },
  validate: WebAssembly.validate,
});

// lifecycle helpers for tests
X.hide = () => { log('lifecycle', 'hide'); hideCbs.slice().forEach(f => f({})); };
X.show = () => { log('lifecycle', 'show'); showCbs.slice().forEach(f => f({ scene: '011004', query: {} })); };

// ---------- inspection (read-only, game-generic) ----------
let ccNS = null;
X.cc = () => ccNS;
X.scene = () => { const s = ccNS && ccNS.director.getScene(); return s ? s.name : null; };
function sceneCam() { const s = ccNS && ccNS.director.getScene(); if (!s) return null; let cam = null; const walk = n => { if (cam) return; const c = n.getComponent && n.getComponent(ccNS.Camera); if (c) { cam = c; return; } n.children.forEach(walk); }; walk(s); return cam; }
function rectWith(cam, n) { const cc = ccNS; const ut = n.getComponent(cc.UITransform); if (!ut || !cam) return null; const b = ut.getBoundingBoxToWorld(); const p1 = new cc.Vec3(), p2 = new cc.Vec3();
  cam.worldToScreen(new cc.Vec3(b.x, b.y, 0), p1); cam.worldToScreen(new cc.Vec3(b.x + b.width, b.y + b.height, 0), p2); const sx = W / main.width, sy = H / main.height;
  const x1 = p1.x * sx, x2 = p2.x * sx, y1 = H - p2.y * sy, y2 = H - p1.y * sy; return { x: (x1 + x2) / 2, y: (y1 + y2) / 2, w: x2 - x1, h: y2 - y1 }; }
X.findAny = name => { const s = ccNS && ccNS.director.getScene(); if (!s) return []; const cam = sceneCam(); const out = []; const walk = n => { if (!n.activeInHierarchy) return; if (n.name === name) out.push(Object.assign({ name }, rectWith(cam, n))); n.children.forEach(walk); }; walk(s); return out; };
X.sceneTexts = () => { const s = ccNS && ccNS.director.getScene(); if (!s) return []; const out = []; const walk = n => { if (!n.activeInHierarchy) return; const l = n.getComponent(ccNS.Label); if (l && l.string) out.push(l.string.replace(/\n/g, ' / ')); n.children.forEach(walk); }; walk(s); return out; };
X.webp = () => ccNS ? ccNS.sys.hasFeature(ccNS.sys.Feature.WEBP) : null;
// Active sprites in the whole scene and how many have a real texture (> 2 px): a blank home after a
// WebP misdetection has sprites without textures (LunasJade v0.10.0 webp_slow; v0.10.1 14/14).
X.sprites = () => { const s = ccNS && ccNS.director.getScene(); if (!s) return null; let n = 0, ok = 0;
  const walk = m => { if (!m.activeInHierarchy) return; const sp = m.getComponent(ccNS.Sprite); if (sp) { n++; const t = sp.spriteFrame && sp.spriteFrame.texture; if (t && t.width > 2) ok++; } m.children.forEach(walk); };
  walk(s); return { total: n, textured: ok }; };
X.summary = () => ({ t: now(), scene: X.scene(), webp: X.webp(), marks: X.marks, firstErr: X.firstErr, modals: X.modals.length,
  ads: X.ads.map(a => a.mode), missing: Object.keys(X.missing), fps: X.fps(), sub: Object.assign({}, attempts) });
window.__hostState = X.summary;

// rAF health: record gaps > 100 ms so a throttled browser tab is visible in the results
X.rafGaps = []; X.rafN = 0; const RAF = [];
// Frames per second over the last `ms` (default 3000) of host time; timing runs below 30 fps are invalid (D3 problem 4).
X.fps = (ms = 3000) => { const t = performance.now(); const n = RAF.filter(x => t - x <= ms).length; const span = Math.min(ms, t - T0); return span > 0 ? Math.round(n * 1000 / span) : null; };
{ let last = performance.now(); const f = () => { const t = performance.now(); X.rafN++; RAF.push(t); if (RAF.length > 600) RAF.shift(); if (t - last > 100) X.rafGaps.push([Math.round(last - T0), Math.round(t - last), document.visibilityState]); last = t; requestAnimationFrame(f); }; requestAnimationFrame(f); }
document.addEventListener('visibilitychange', () => log('visibility', document.visibilityState));
// ---------- boot ----------
log('boot', JSON.stringify({ W, H, DPR, faults: [...F], ads: ADS, sdk: sys.SDKVersion }));
setTimeout(() => {
  try { load('game.js'); } catch (e) { log('boot.throw', String(e && e.stack || e)); X.firstErr = X.firstErr || String(e); }
  // v7.8 (B30): poll every 30 ms (was 300) and beacon scene-loading / scene-launch, so the startup-download cut-off
  // (subpackages requested before the home scene starts loading) is seen for a fast-booting 3.x game too
  let asked = false;
  const poll = setInterval(() => {
    const S = GT.System; if (!S || ccNS || !GT.cc || asked) return; // only after the game itself has evaluated cc.js
    asked = true;
    try { const p = S.import('cc'); p.then(ns => { if (ns && ns.director && !ccNS) { ccNS = ns; window.cc = ns; mark('ccReady');
      try { ns.director.on(ns.Director.EVENT_BEFORE_SCENE_LOADING, (name) => beacon('scene-loading', name));
        ns.director.on(ns.Director.EVENT_AFTER_SCENE_LAUNCH, (s) => beacon('scene-launch', s && s.name)); } catch (e) {}
      ns.director.on(ns.Director.EVENT_AFTER_DRAW, () => { const sc = X.scene(); if (sc) mark('scene:' + sc); }); } else asked = false; }).catch(() => { asked = false; }); } catch (e) { asked = false; }
  }, 30);
  setTimeout(() => clearInterval(poll), 120000);
}, 0);
})();
