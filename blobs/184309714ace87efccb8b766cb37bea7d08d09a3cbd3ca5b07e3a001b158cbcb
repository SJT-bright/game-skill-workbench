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
  const page = task.page(name || 'p1');
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
export const ev = (page, fn, a) => (a === undefined ? page.evaluate(fn) : page.evaluate(fn, a));

// Run an adapter JavaScript string (function body) in the page; returns its value or {adapterError}.
export const adapterCall = (page, code) => ev(page, (code) => {
  try { return new Function(code)(); } catch (e) { return { adapterError: String(e && e.message || e).slice(0, 300) }; }
}, code);

export async function viewport(page, w = 390, h = 844, dpr = 2, touch = false) {
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: true });
  await page.cdp('Emulation.setTouchEmulationEnabled', touch ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
}

// Default readiness: an engine scene exists (2.x / 3.x); adapter.ready overrides.
const READY = "return !!(window.cc && cc.director && cc.director.getScene && cc.director.getScene());";
export async function waitFor(page, code, timeoutMs, everyMs = 500) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    let v = null;
    try { v = await adapterCall(page, code); } catch (_) { v = null; }
    if (v === true || (v && typeof v === 'object' && !v.adapterError && v.ok === true)) return { ok: true, ms: Date.now() - t0 };
    await sleep(everyMs);
  }
  return { ok: false, ms: Date.now() - t0 };
}

// Load the host with extra query (fault parameters) and wait until `until` (default adapter.home,
// else adapter.ready, else engine scene) is true. Returns {ok, ms, errors}.
export async function boot(page, query, opt = {}) {
  await page.goto(url(query));
  const until = opt.until || A.home || A.ready || READY;
  const w = await waitFor(page, until, opt.timeoutMs || C.bootTimeoutMs || 60000);
  return { ok: w.ok, ms: w.ms, errors: await errors(page) };
}

export const hostLog = (page) => ev(page, () => (window.__hostLog || []).slice(-2000));
export const errors = (page) => ev(page, () => (window.__hostLog || [])
  .filter(r => /^(error|rejection|boot-throw)$/.test(r.kind)).slice(0, 8));
export const hostState = (page) => ev(page, () => window.__hostState && window.__hostState());

// Screen (CSS px) points of active nodes whose cc.Label text matches `pattern` (2.x and 3.x).
export const findLabels = (page, pattern) => ev(page, (pattern) => {
  if (!(window.cc && cc.director && cc.director.getScene())) return [];
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
        const w = v2api ? n.convertToWorldSpaceAR(cc.v2(0, 0)) : n.getComponent(cc.UITransform).convertToWorldSpaceAR(new cc.Vec3(0, 0, 0));
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
  (cc.director.getScene().children || []).forEach(walk); // not the Scene itself: Scene.activeInHierarchy logs an engine error
  return hits;
}, pattern);

// Real pointer tap at CSS (x, y); the host turns mouse into a TikTok touch (mouse=1).
export async function tap(page, x, y) {
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await page.cdp('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1 });
    if (type === 'mousePressed') await sleep(60);
  }
}

// Real touch tap (needs viewport(page, w, h, dpr, true)): reaches tt.onTouch*, DOM touch listeners on the
// canvas (platform-kit retry) and DOM buttons (host modal) like a finger does.
export async function touchTap(page, x, y) {
  await page.cdp('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 1, radiusX: 4, radiusY: 4, force: 1 }] });
  await sleep(70);
  await page.cdp('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}

// Locate a control: adapter JS (returns {x,y} CSS point, or a cc.Node -> its centre) or a label regexp.
export async function locate(page, code, labelPattern) {
  if (code) {
    const p = await ev(page, (code) => {
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
        const w = v2api ? n.convertToWorldSpaceAR(cc.v2(0, 0)) : n.getComponent(cc.UITransform).convertToWorldSpaceAR(new cc.Vec3(0, 0, 0));
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
