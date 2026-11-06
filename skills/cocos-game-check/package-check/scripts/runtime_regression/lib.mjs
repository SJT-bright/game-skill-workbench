import {wrapEgoPage} from '../ego_test_page.mjs';
// Shared helpers for runtime_regression suites (run under `ego-browser nodejs`).
// Contract: runtime_regression/README.md. Import with:  const L = await import(globalThis.CFG.lib);
// Timing lives in Node: every page.evaluate call stays short (Ego caps one call at 15 s).
const fs = await import('node:fs');
const path = await import('node:path');
export const C = globalThis.CFG || {};
export const A = C.adapter || {};
export const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------- result document ----------
export function result(suite) {
  const out = { suite: suite || C.suite, passed: false, cases: [], warnings: [], evidence: {}, fatal: null };
  out.add = (id, passed, detail) => { out.cases.push({ id, passed: passed === true, detail: detail === undefined ? null : detail }); save(); };
  out.warn = (msg) => { out.warnings.push(String(msg)); save(); };
  function save() {
    out.passed = !out.fatal && out.cases.length > 0 && out.cases.every(c => c.passed === true);
    const { add, warn, save: _s, ...doc } = out;
    if (C.resultFile) fs.writeFileSync(C.resultFile, JSON.stringify(doc, null, 2));
  }
  out.save = save;
  return out;
}

// Write a named evidence JSON next to the suite result; returns its path (record it in out.evidence).
export function evidence(name, data) {
  const file = path.join(C.evidenceDir || '.', name);
  fs.writeFileSync(file, typeof data === 'string' ? data : JSON.stringify(data, null, 2));
  return file;
}

// ---------- browser ----------
export async function open(name) {
  const task = await taskSpace(C.space || ('tiktok-runtime-' + C.suite));
  const page = wrapEgoPage(task.page(name || 'p1'));
  // v7.9: no HTTP cache. Ego is one browser for every session; a trial server another session ran earlier on the same
  // 127.0.0.1 port (python http.server sends no Cache-Control, so files are kept by heuristic freshness) left its
  // main.js in the cache, and a later run here booted that other game's code (2026-11-01, 甜点消消乐 R48: "home not
  // reached" while main.js asked for touch-coordinates.js that R48 does not have).
  try { await page.cdp('Network.enable', {}); await page.cdp('Network.setCacheDisabled', { cacheDisabled: true }); } catch (_) {}
  return { task, page };
}
export async function close(task, page) {
  try { await page.goto('about:blank'); } catch (_) {}
  try { await task.finish({ keep: [] }); } catch (_) {}
}
export function url(query) {
  const q = [C.hostQuery, query].filter(Boolean).join('&');
  return C.base + (C.hostPage || '/__host/play.html') + (q ? '?' + q : '');
}
// v7.9 (出包检查提速 S7, 总表 19 ③): every finished page round trip touches CFG.progressFile (at most once a second),
// so the runner can tell a slow suite from a stuck one (runtime_regression.py stops a suite after 240 s without any
// change in its folder or output). No progressFile (an older runner): nothing is written.
let lastTick = 0;
export function progress() {
  const now = Date.now();
  if (!C.progressFile || now - lastTick < 1000) return;
  lastTick = now;
  try { fs.writeFileSync(C.progressFile, String(now)); } catch (_) {}
}
export function track(p) {
  if (!p || typeof p.then !== 'function') { progress(); return p; }
  return p.then((v) => { progress(); return v; }, (e) => { progress(); throw e; });
}
export const ev = (page, fn, a) => track(a === undefined ? page.evaluate(fn) : page.evaluate(fn, a));
// R4O4: page probes read the engine through engine_adapter.mjs (a byte copy of remake-core/scripts/engine_adapter.js).
// evE runs fn in the page after installing window.__ccAdapt; fn reads `const E = window.__ccAdapt(window)` and returns
// {notReady: E.reason} while the engine is not up (引擎还没起来), never throws on a missing cc.director.
export const ENGINE = await import(new URL('engine_adapter.mjs', import.meta.url).href);
export const evE = (page, fn, a) => ev(page, ENGINE.inPage(fn, a));
// evE again while the page answers {notReady} (tries x everyMs); the last answer is returned as is.
export async function evReady(page, fn, a, tries = 3, everyMs = 1000) {
  let v = null;
  for (let i = 0; i < tries; i++) {
    v = await evE(page, fn, a);
    if (!(v && typeof v === 'object' && !Array.isArray(v) && v.notReady)) return v;
    if (i < tries - 1) await sleep(everyMs);
  }
  return v;
}

// Run an adapter JavaScript string (function body) in the page; returns its value or {adapterError}.
// The body may use window.__ccAdapt(window) (installed first).
export const adapterCall = (page, code) => ev(page, ENGINE.bodyInPage(code));

export async function viewport(page, w = 390, h = 844, dpr = 2, touch = false) {
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: true });
  await page.cdp('Emulation.setTouchEmulationEnabled', touch ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
}

// Default readiness: an engine scene exists (2.x / 3.x, engine_adapter.mjs); adapter.ready overrides.
export const READY = ENGINE.READY;
export async function waitFor(page, code, timeoutMs, everyMs = 500) {
  const t0 = Date.now();
  let notReady = null;
  while (Date.now() - t0 < timeoutMs) {
    let v = null;
    try { v = await adapterCall(page, code); } catch (_) { v = null; }
    if (v === true || (v && typeof v === 'object' && !v.adapterError && v.ok === true)) return { ok: true, ms: Date.now() - t0 };
    if (v && typeof v === 'object' && v.notReady) notReady = v.notReady;
    await sleep(everyMs);
  }
  return notReady ? { ok: false, ms: Date.now() - t0, notReady } : { ok: false, ms: Date.now() - t0 };
}

// Load the host with extra query (fault parameters) and wait until `until` (default adapter.home,
// else adapter.ready, else engine scene) is true. Returns {ok, ms, errors}.
export async function boot(page, query, opt = {}) {
  await track(page.goto(url(query)));
  const until = opt.until || A.home || A.ready || READY;
  const w = await waitFor(page, until, opt.timeoutMs || C.bootTimeoutMs || 60000);
  const r = { ok: w.ok, ms: w.ms, errors: await errors(page) };
  if (w.notReady) r.notReady = w.notReady;   // R4O4: the engine never came up (引擎还没起来), not a missing button
  return r;
}

export const hostLog = (page) => ev(page, () => (window.__hostLog || []).slice(-2000));
export const errors = (page) => ev(page, () => (window.__hostLog || [])
  .filter(r => /^(error|rejection|boot-throw)$/.test(r.kind)).slice(0, 8));
export const hostState = (page) => ev(page, () => window.__hostState && window.__hostState());

// Screen (CSS px) points of active nodes whose cc.Label text matches `pattern` (2.x and 3.x).
// R4O4: engine not up -> asked again (evReady: 3 x 1 s), then [] as before.
export const findLabels = async (page, pattern) => { const r = await evReady(page, (pattern) => {
  const E = window.__ccAdapt(window);
  if (!E.ready) return { notReady: E.reason };
  const cc = E.cc;
  const rx = new RegExp(pattern, 'i');
  const canvas = cc.game.canvas, rect = canvas.getBoundingClientRect();
  const v2api = !!(cc.Camera && cc.Camera.findCamera);
  const toCss = (p) => {
    // css-point:begin (v7.7.5, 总表 A13) the same conversion as ad_regression/cases.mjs (A5): Cocos 2.x
    // getWorldToScreenPoint works in cc.visibleRect units, 3.x worldToScreen in canvas pixels.
    const vis = (v2api && cc.visibleRect) ? { w: cc.visibleRect.width, h: cc.visibleRect.height } : { w: canvas.width, h: canvas.height };
    return { x: rect.left + p.x * rect.width / vis.w, y: rect.top + rect.height - p.y * rect.height / vis.h };
    // css-point:end
  };
  const hits = [];
  const walk = (n) => {
    if (!n || n.activeInHierarchy === false) return;
    const l = n.getComponent && (n.getComponent(cc.Label) || (cc.RichText && n.getComponent(cc.RichText)));
    if (l && typeof l.string === 'string' && rx.test(l.string)) {
      try {
        let p;
        const tw = E.toWorld(n, 0, 0);   // R4O4: engine_adapter (3.x through UITransform)
        if (!tw) throw new Error('no UITransform on ' + n.name);
        const w = v2api ? cc.v2(tw[0], tw[1]) : new cc.Vec3(tw[0], tw[1], 0);
        // cam-point:begin (v7.8, 总表 A13 补) world point -> camera screen point; identical in ad_regression/cases.mjs and runtime_regression/lib.mjs.
        // 2.x: the node's own camera. 3.x: the cameraComponent of the Canvas the node sits under (walk up the parents);
        // only when there is none, the first camera of the scene. cams[0] alone is the 3D world camera in a 3D game
        // (企鹅雪道 v4: the X came out at (818, -918) and nocallback failed a game whose ad was fine).
        if (v2api) p = cc.Camera.findCamera(n).getWorldToScreenPoint(w);
        else {
          let cam = null;
          for (let a = n; a && !cam; a = a.parent) {
            const cv = a.getComponent && a.getComponent(cc.Canvas);
            cam = (cv && (cv.cameraComponent || cv._cameraComponent)) || null;
          }
          if (!cam) cam = cc.director.getScene().getComponentsInChildren(cc.Camera)[0];
          p = new cc.Vec3(); cam.worldToScreen(w, p);
        }
        // cam-point:end
        hits.push(Object.assign({ text: l.string }, toCss(p)));
      } catch (e) { hits.push({ text: l.string, error: String(e.message || e) }); }
    }
    (n.children || []).forEach(walk);
  };
  (E.scene.children || []).forEach(walk); // not the Scene itself: Scene.activeInHierarchy logs an engine error
  return hits;
}, pattern); return Array.isArray(r) ? r : []; };

// Real pointer tap at CSS (x, y); the host turns mouse into a TikTok touch (mouse=1).
export async function tap(page, x, y) {
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await track(page.cdp('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1 }));
    if (type === 'mousePressed') await sleep(60);
  }
}

// Real touch tap (needs viewport(page, w, h, dpr, true)): reaches tt.onTouch*, DOM touch listeners on the
// canvas (platform-kit retry) and DOM buttons (host modal) like a finger does.
export async function touchTap(page, x, y) {
  await track(page.cdp('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 1, radiusX: 4, radiusY: 4, force: 1 }] }));
  await sleep(70);
  await track(page.cdp('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }));
}

// Locate a control: adapter JS (returns {x,y} CSS point, or a cc.Node -> its centre) or a label regexp.
export async function locate(page, code, labelPattern) {
  if (code) {
    const p = await evReady(page, (code) => {
      const E = window.__ccAdapt(window);
      if (!E.ready) return { notReady: E.reason };
      const cc = E.cc;
      let r; try { r = new Function(code)(); } catch (e) { return { error: String(e.message || e) }; }
      if (!r) return null;
      const n = r.node || r, canvas = cc.game.canvas, rect = canvas.getBoundingClientRect();
      // the TikTok host's canvas rect has left/top/width/height only (no right/bottom)
      const onCanvas = (q) => Object.assign(q, { onCanvas: q.x >= rect.left - 1 && q.x <= rect.left + rect.width + 1
                                                  && q.y >= rect.top - 1 && q.y <= rect.top + rect.height + 1 });
      if (typeof r.x === 'number' && typeof r.y === 'number' && !r.getComponent) return onCanvas({ x: r.x, y: r.y });
      const v2api = !!(cc.Camera && cc.Camera.findCamera);
      const toCss = (p) => {
        // css-point:begin (v7.7.5, 总表 A13) the same conversion as ad_regression/cases.mjs (A5): Cocos 2.x
        // getWorldToScreenPoint works in cc.visibleRect units, 3.x worldToScreen in canvas pixels.
        const vis = (v2api && cc.visibleRect) ? { w: cc.visibleRect.width, h: cc.visibleRect.height } : { w: canvas.width, h: canvas.height };
        return { x: rect.left + p.x * rect.width / vis.w, y: rect.top + rect.height - p.y * rect.height / vis.h };
        // css-point:end
      };
      try {
        let p;
        const tw = E.toWorld(n, 0, 0);   // R4O4: engine_adapter (3.x through UITransform)
        if (!tw) throw new Error('no UITransform on ' + n.name);
        const w = v2api ? cc.v2(tw[0], tw[1]) : new cc.Vec3(tw[0], tw[1], 0);
        // cam-point:begin (v7.8, 总表 A13 补) world point -> camera screen point; identical in ad_regression/cases.mjs and runtime_regression/lib.mjs.
        // 2.x: the node's own camera. 3.x: the cameraComponent of the Canvas the node sits under (walk up the parents);
        // only when there is none, the first camera of the scene. cams[0] alone is the 3D world camera in a 3D game
        // (企鹅雪道 v4: the X came out at (818, -918) and nocallback failed a game whose ad was fine).
        if (v2api) p = cc.Camera.findCamera(n).getWorldToScreenPoint(w);
        else {
          let cam = null;
          for (let a = n; a && !cam; a = a.parent) {
            const cv = a.getComponent && a.getComponent(cc.Canvas);
            cam = (cv && (cv.cameraComponent || cv._cameraComponent)) || null;
          }
          if (!cam) cam = cc.director.getScene().getComponentsInChildren(cc.Camera)[0];
          p = new cc.Vec3(); cam.worldToScreen(w, p);
        }
        // cam-point:end
        return onCanvas(toCss(p));
      } catch (e) { return { error: String(e.message || e) }; }
    }, code);
    return p && typeof p.x === 'number' ? p : null;
  }
  const hits = await findLabels(page, labelPattern);
  return hits.find(h => typeof h.x === 'number') || null;
}

// Timing validity (D3 problem 4): Chrome throttles a covered Ego tab to ~1 fps while
// visibilityState stays 'visible'. A tiny CDP screencast keeps frames flowing; timing runs must
// still read the page's requestAnimationFrame rate and treat < MIN_FPS as an invalid run.
export const MIN_FPS = 30;
export async function keepFrames(page) {
  try { await page.cdp('Page.stopScreencast', {}); } catch (_) {}
  try { await page.cdp('Page.startScreencast', { format: 'jpeg', quality: 5, maxWidth: 120, maxHeight: 240, everyNthFrame: 1 }); return true; }
  catch (_) { return false; }
}
// Page rAF rate over the last `ms`: host3x exposes __H.fps(); otherwise count frames for `ms` now.
export const fps = (page, ms = 1000) => ev(page, (ms) => new Promise((done) => {
  if (window.__H && window.__H.fps) return done(window.__H.fps(Math.max(ms, 3000)));
  let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < ms) requestAnimationFrame(f); else done(Math.round(n * 1000 / (performance.now() - t0))); }; requestAnimationFrame(f);
}), ms);

// Run a suite body with a fresh page and a result document; always saves and closes.
export async function suite(body, opt = {}) {
  const out = result(C.suite);
  let task, page;
  try {
    ({ task, page } = await open('p1'));
    await viewport(page, opt.w || 390, opt.h || 844, opt.dpr || 2, !!opt.touch);
    await body({ out, page, task });
  } catch (e) {
    out.fatal = String(e && e.stack || e).slice(0, 800);
  } finally {
    out.save();
    if (task) await close(task, page);
    console.log('RUNTIME_SUITE_DONE ' + C.suite);
  }
  return out;
}
