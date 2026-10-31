// Node-side helpers for the v7.8 suites layout_state (D), button_sweep (E) and ad_entries (B) (总表 B30, A12).
// From the 全民飞车门禁 prototype lib/gatelib.mjs + lib/actions.mjs (1全民飞车漂移/_work/skill_feedback/gates, 2026-10-30),
// moved onto the official hosts (ad_regression/host.js for 2.x, host3x/ for 3.x; both take dev=, capsule=, reset=, ad=
// and write window.__gateLog). The page IS the host (play.html at the top level): window.cc is the game's engine and
// CSS px of the viewport are the phone's points, because the viewport is forced to the device size.
// Import with: const G = await import(new URL('gates.mjs', CFG.lib).href);
import { GEOM_JS } from './geom.mjs';
export { GEOM_JS };
const L = await import(globalThis.CFG.lib);

// Real phone numbers in points (Saul's iPhone 14 TikTok, 2026-10-29). SE capsule x is derived, not measured: warn only.
export const DEVICES = {
  iphone14: { W: 390, H: 844, cap: { x0: 293, y0: 51, x1: 380, y1: 83 }, safeBottom: 810 },
  se: { W: 375, H: 667, cap: { x0: 278, y0: 24, x1: 365, y1: 56 }, safeBottom: 667, capXUnmeasured: true },
};
export const MiB = 1048576;
// Pages below this frame rate are a throttled Ego tab (window covered), not a game fault: the run is invalid.
export const MIN_FPS = 20;
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function setViewport(page, dev) {
  const d = DEVICES[dev];
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: d.W, height: d.H, deviceScaleFactor: 1, mobile: false });
  await page.cdp('Emulation.setTouchEmulationEnabled', { enabled: false });
  await sleep(200);
}

export async function pageFps(page) {
  return page.evaluate(() => new Promise((done) => { let n = 0; const t0 = Date.now(); const f = () => { n++; if (Date.now() - t0 < 1000) requestAnimationFrame(f); else done(n); }; requestAnimationFrame(f); setTimeout(() => done(n), 2500); })).catch(() => null);
}

// Fresh load: device profile, empty save, the base host query (mouse=1&run=<suite> + adapter.host_query) and `query`.
export async function openGame(page, dev, query) {
  await setViewport(page, dev);
  const q = 'dev=' + dev + '&reset=1' + (query ? '&' + query : '') + '&r=' + Date.now();
  await page.goto(L.url(q));
  await L.keepFrames(page);
  return q;
}

// Home = engine running, scene stable, no script/subpackage load for quietMs, frames still rising. Without a home
// scene name: a scene counts only when no subpackage is still downloading and it shows a control (DriftRacer v1's
// loading page sat 3 s without a new request while one 9.7 MB subpackage was still coming). adapterHome: the
// runtime adapter's `home` JS (true when the home page is up) is used instead of the scene heuristics when given.
export async function waitHome(page, { homeScene = null, adapterHome = null, timeout = 90000, quietMs = 3000 } = {}) {
  const t0 = Date.now();
  let last = null, stableSince = 0, st = null;
  while (Date.now() - t0 < timeout) {
    st = await page.evaluate(() => {
      const cc = window.cc, s = cc && cc.director && cc.director.getScene && cc.director.getScene();
      const log = window.__hostLog || [];
      let lastLoad = 0;
      const lastBy = {};
      for (const r of log) {
        if (r.kind === 'subpackage' || r.kind === 'subpackage-ok' || r.kind === 'require') lastLoad = r.t;
        if (/^subpackage(-ok|-fail)?$/.test(r.kind) && r.data && r.data.name) lastBy[r.data.name] = r.kind;
      }
      const inflight = Object.keys(lastBy).filter((k) => lastBy[k] === 'subpackage').length;
      let buttons = 0;
      // controls = cc.Button nodes, or nodes with the game's own touch listeners (Rowan v77 and Tansys have no cc.Button)
      const v3 = !!(cc && cc.UITransform), TE = v3 ? 'touch-end' : 'touchend', TS = v3 ? 'touch-start' : 'touchstart';
      const notTap = cc ? [cc.BlockInputEvents, cc.ScrollView, cc.PageView, cc.Slider, cc.EditBox].filter(Boolean) : [];
      const touchy = (n) => { try { return (v3 || !!n._touchListener) && !notTap.some((K) => n.getComponent(K)) && (n.hasEventListener(TE) || n.hasEventListener(TS)); } catch (_) { return false; } };
      try { if (s) (v3 ? (s.children || []) : [s]).forEach((c) => c.walk((n) => { if (n.activeInHierarchy && (n.getComponent(cc.Button) || touchy(n))) buttons++; })); } catch (_) {}
      const hostNow = window.__hostState ? window.__hostState().t : 0;
      return { scene: s ? s.name : null, frames: cc && cc.director ? cc.director.getTotalFrames() : 0, sinceLoad: hostNow - lastLoad, inflight, buttons };
    }).catch((e) => ({ scene: null, frames: 0, err: String(e) }));
    const key = st.scene;
    if (key && key === last) { if (!stableSince) stableSince = Date.now(); } else { stableSince = 0; last = key; }
    let okScene = homeScene ? st.scene === homeScene : !!st.scene && !st.inflight && st.buttons > 0;
    // the adapter's own home test, when there is one, decides "home" (the quiet / frames conditions still apply)
    if (okScene && adapterHome) { const ok = await L.adapterCall(page, adapterHome).catch(() => null); okScene = ok === true || !!(ok && ok.ok === true); }
    if (okScene && st.frames > 60 && st.sinceLoad >= quietMs && stableSince && Date.now() - stableSince >= quietMs) {
      const f1 = st.frames;
      await sleep(500);
      const f2 = await page.evaluate(() => window.cc.director.getTotalFrames()).catch(() => f1);
      if (f2 > f1) return { ok: true, ms: Date.now() - t0, scene: st.scene, frames: f2 };
    }
    await sleep(500);
  }
  return { ok: false, ms: Date.now() - t0, last: st, fps: await pageFps(page) };
}

export async function engineMajor(page) {
  return page.evaluate(() => {
    const c = window.cc, legacy = window.__H && window.__H.G && window.__H.G.cc;
    const v = String((c && (c.ENGINE_VERSION || c.VERSION)) || (legacy && legacy.ENGINE_VERSION) || '');
    const m = v.match(/^(\d+)/);
    return { version: v || (c && c.UITransform ? '3.x' : ''), major: m ? +m[1] : (c && c.UITransform ? 3 : 2) };
  }).catch(() => ({ version: '', major: 2 }));
}

// Every visible 2D node with a Sprite / Label / Button (RichText counts as text), boxes in CSS px.
// sig (controls only) = own and descendants' label texts, sprite frame names and node names, lower case.
const VISIBLE_BODY = `
  var F = V3 ? frameCss() : null, M = V3 ? null : map2();
  var FX0 = V3 ? F.left : 0, FY0 = V3 ? F.top : 0, FW = V3 ? F.w : M.fw, FH = V3 ? F.h : M.fh;
  function bitsOf(x, bits) {
    var l = x.getComponent(cc.Label) || (cc.RichText && x.getComponent(cc.RichText)); if (l && l.string) bits.push(String(l.string));
    var s = x.getComponent(cc.Sprite); if (s && s.spriteFrame && s.spriteFrame.name) bits.push(s.spriteFrame.name);
  }
  function sigOf(n) { var bits = [n.name]; bitsOf(n, bits); n.walk(function (x) { if (x !== n && x.activeInHierarchy) { bits.push(x.name); bitsOf(x, bits); } }); return bits.join(' ').toLowerCase().slice(0, 200); }
  var notTap = [cc.BlockInputEvents, cc.ScrollView, cc.PageView, cc.Slider, cc.EditBox].filter(Boolean);
  var clipKinds = [cc.Mask, cc.ScrollView, cc.PageView].filter(Boolean);
  function touchy(n) { try { if (notTap.some(function (K) { return n.getComponent(K); })) return false; return hasTouch(n); } catch (e) { return false; } }
  // 3.x games that hit-test their own UI (CindersDragon v3.2: one touch listener on the UI layer, controls named "Btn PLAY")
  var VBTN = /^(btn|button)([\\s_:-]|$)/i;
  function virtualTap(n) {
    if (!V3 || !VBTN.test(n.name || '')) return false;
    for (var x = n.parent, k = 0; x && k < 4; x = x.parent, k++) if (touchy(x)) return true;
    return false;
  }
  var out = [], seen = {};
  walkScene(function (n) {
    if (!n.activeInHierarchy || n.is3DNode || !shownChain(n)) return;
    var sp = n.getComponent(cc.Sprite), lb = n.getComponent(cc.Label) || (cc.RichText && n.getComponent(cc.RichText));
    var bt = n.getComponent(cc.Button); if (bt && bt.enabled === false) bt = null;
    var tl = !bt && touchy(n);
    var vt = !bt && !tl && virtualTap(n);
    if (vt) tl = true;
    if (!sp && !lb && !bt && !tl) return;
    if (sp && !sp.spriteFrame && !lb && !bt && !tl) return;
    if (lb && !lb.string && !sp && !bt && !tl) return;
    var r, b; try { r = worldBox(n); } catch (e) { return; }
    if (!r || r.width <= 0 || r.height <= 0) return;
    try { b = cssBox(n); } catch (e) { return; }
    if (!b) return;
    var x0 = b.x0, x1 = b.x1, y0 = b.y0, y1 = b.y1;
    if (x1 <= FX0 || y1 <= FY0 || x0 >= FX0 + FW || y0 >= FY0 + FH) return;
    var p = pathOf(n); seen[p] = (seen[p] || 0) + 1; if (seen[p] > 1) p += '#' + seen[p];
    var big = (x1 - x0) > 0.6 * FW && (y1 - y0) > 0.4 * FH;   // full-screen tap catcher / input blocker
    var handlers;
    if (bt) { try { handlers = (bt.clickEvents ? bt.clickEvents.length : 0) + (n.hasEventListener && n.hasEventListener('click') ? 1 : 0) + ownTouchEnd(n); } catch (e) {} }
    var checked = !!(cc.Toggle && n.getComponent(cc.Toggle) && n.getComponent(cc.Toggle).isChecked);
    // W87 calibration (指尖麻将 v56 Tile Collection): every clipping ancestor counts, not only the nearest one; items
    // scrolled below the visible window (centre outside any of them) are hidden and never tapped
    var clipped = false, hidden = false;
    for (var x = n.parent; x; x = x.parent) if (clipKinds.some(function (K) { return x.getComponent(K); })) {
      clipped = true;
      try { var m = worldBox(x), cx = r.x + r.width / 2, cy = r.y + r.height / 2; if (m && (cx < m.x || cx > m.x + m.width || cy < m.y || cy > m.y + m.height)) hidden = true; } catch (e) {}
    }
    out.push({ path: p, kind: bt || tl ? 'button' : lb ? 'label' : 'sprite', text: lb ? String(lb.string).slice(0, 40) : undefined,
      frame: sp && sp.spriteFrame ? sp.spriteFrame.name : undefined, sig: bt || tl ? sigOf(n) : undefined,
      touchOnly: tl || undefined, virtual: vt || undefined, layer: (bt || tl) && big ? true : undefined, handlers: handlers, checked: checked || undefined, clipped: clipped || undefined, maskHidden: hidden || undefined, uuid: n.uuid || n._id,
      interactable: bt ? !!bt.interactable : tl ? true : undefined,
      box: { x0: +x0.toFixed(1), y0: +y0.toFixed(1), x1: +x1.toFixed(1), y1: +y1.toFixed(1) } });
  });
  return { frame: { w: FW, h: FH }, engine: V3 ? 3 : 2, nodes: out };
`;

export async function visibleNodes(page) {
  return page.evaluate('(function(){' + GEOM_JS + VISIBLE_BODY + '})()');
}

export async function shot(page, file) {
  const fs = await import('node:fs/promises');
  const res = await page.cdp('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(file, Buffer.from(res.data, 'base64'));
  return file;
}

export function overlap(a, b) {
  const w = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0), h = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
  return w > 0 && h > 0 ? { w: +w.toFixed(1), h: +h.toFixed(1) } : null;
}

// ---------- real-input steps (adapter states) ----------
// An adapter state may list "actions", run in order with the real mouse (the host turns it into TikTok touches):
//   {"tap": "Canvas/a/b"}   ("*/x/y" = any active node whose path ends in x/y)    {"drag_js": "...; return [nodeA, nodeB]"}
//   {"js": "..."}           {"wait": 1500}     {"wait_scene": "25DScene", "timeout": 30000}
//   {"wait_node": "Canvas/__revive/btn_watch_ad", "timeout": 8000}   until the node is active and drawn
// Every step may carry "after": ms and "optional": true (a missing target is not an error).
export const HELPERS = GEOM_JS + `
  function req(name) { try { return window.__require(name); } catch (e) { return null; } }
  function comp(name) { var hit = null; walkScene(function (n) { if (hit) return; var c = n.getComponent(name); if (c) hit = c; }); return hit; }
  function findNode(path) {
    var n = cc.find(path); if (n) return n;
    var tail = '/' + String(path).replace(/^[*][/]/, ''), hit = null;
    walkScene(function (x) { if (!hit && x.activeInHierarchy && ('/' + pathOf(x)).slice(-tail.length) === tail) hit = x; });
    return hit;
  }
  function node(path) { return findNode(path); }
  function boxOf(n) { return worldBox(n); }
  function screenOf(n) {
    if (!n || !n.activeInHierarchy || !shownChain(n)) return null;
    var b = cssBox(n); if (!b) return null;
    var w = b.x1 - b.x0, h = b.y1 - b.y0;
    if (w < 2 || h < 2) return null;
    return { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2, w: w, h: h, path: pathOf(n) };
  }
`;

export function evalJs(page, body) {
  return page.evaluate('(function(){' + HELPERS + '\n' + body + '\n})()');
}

// ---------- tap probe (v7.8 W93: where a dead tap got stuck) ----------
// Installed once per page load (idempotent), records only while a tap window is open (probeStart .. probeStop):
//   hit     the node the engine gave the touch to (the first touch-start dispatchEvent): the button itself, or a node
//           drawn over it (name, path, BlockInputEvents, cc.Button, opacity of the chain, full screen)
//   end     the node that got touch-end;  emits  cc.Component.EventHandler.emitEvents calls (clickEvents) with the
//           entries that point at no component / no function;  clicks  node.emit('click') and whether anyone listens
//   err     the first window.onerror / unhandledrejection / console.error / cc.error, or an exception thrown out of
//           the touch dispatch (a callback that threw)
//   pend    tt.* calls with success / fail / complete (or a promise), cc.resources / cc.loader / assetManager loads
//           and cc.director.loadScene with a callback that did not call back; the host log adds subpackages without
//           -ok / -fail and ad-show without ad-result
// Prototype patches, not per-node ones: Button handlers bound at onEnable stay untouched, emitEvents / emit /
// dispatchEvent are looked up at call time, so already enabled buttons are covered.
export const PROBE_JS = `(function () {
  var cc = window.cc; if (!cc || !cc.Node || !cc.director) return false;
  if (window.__bsProbe) return true;
  var V3 = !!cc.UITransform;
  var P = window.__bsProbe = { cur: null, pend: [], seq: 0, errLog: [] };
  function pathOf(n) { var p = []; while (n && n.parent) { p.unshift(n.name); n = n.parent; } return p.join('/'); }
  function txt(x) {
    try {
      if (x && x.stack) return (String(x.message || x) + ' @' + String(x.stack).split('\\n').slice(1, 2).join('').trim()).slice(0, 240);
      if (x && typeof x === 'object') return (x.errMsg || x.message || JSON.stringify(x) || '').slice(0, 240);
      return String(x).slice(0, 240);
    } catch (e) { return '?'; }
  }
  // an error that also came in the 3 s before the tap is the game's background noise, not this tap's (W93 calibration,
  // HappyCup: "Error 3804 getComponent: Type must be non-nil" logged on every tap by the game itself)
  function err(src, x) {
    var c = P.cur, m = txt(x), t = Date.now();
    if (c && !c.err && !(src !== 'callback' && P.errLog.some(function (e) { return e.msg === m && e.t <= c.t0 && e.t > c.t0 - 3000; }))) c.err = { src: src, msg: m, ms: t - c.t0 };
    P.errLog.push({ t: t, msg: m }); if (P.errLog.length > 60) P.errLog.shift();
  }
  function opacityOf(n) {
    var o = 255;
    for (var x = n; x; x = x.parent) {
      if (!V3) { if (typeof x.opacity === 'number') o = Math.min(o, x.opacity); continue; }
      var u = x.getComponent && cc.UIOpacity && x.getComponent(cc.UIOpacity); if (u && u.enabled !== false) o = Math.min(o, u.opacity);
    }
    return o;
  }
  function info(n) {
    if (!n) return null;
    var r = { path: pathOf(n), name: n.name, block: !!(cc.BlockInputEvents && n.getComponent(cc.BlockInputEvents)), button: !!n.getComponent(cc.Button), opacity: opacityOf(n) };
    try {
      var b = V3 ? (n.getComponent(cc.UITransform) && n.getComponent(cc.UITransform).getBoundingBoxToWorld()) : n.getBoundingBoxToWorld();
      var vs = cc.view.getVisibleSize();
      if (b && vs) r.full = b.width >= 0.6 * vs.width && b.height >= 0.4 * vs.height;
    } catch (e) {}
    return r;
  }
  P.info = info;
  window.addEventListener('error', function (e) { if (e && (e.error || e.message) && (!e.target || e.target === window)) err('window.onerror', e.error || e.message); }, true);
  window.addEventListener('unhandledrejection', function (e) { err('unhandledrejection', e && e.reason); });
  var ce = console.error;
  console.error = function () { try { err('console.error', Array.prototype.map.call(arguments, txt).join(' ')); } catch (e) {} return ce.apply(console, arguments); };
  if (typeof cc.error === 'function') { var cer = cc.error; cc.error = function () { try { err('cc.error', Array.prototype.map.call(arguments, txt).join(' ')); } catch (e) {} return cer.apply(cc, arguments); }; }
  var NP = cc.Node.prototype;
  if (typeof NP.dispatchEvent === 'function') {
    var od = NP.dispatchEvent;
    NP.dispatchEvent = function (ev) {
      var c = P.cur, t = ev && ev.type;
      if (c) {
        if ((t === 'touchstart' || t === 'touch-start') && !c.hit) c.hit = info(this);
        else if ((t === 'touchend' || t === 'touch-end') && !c.end) c.end = pathOf(this);
        else if ((t === 'touchcancel' || t === 'touch-cancel') && !c.cancel) c.cancel = pathOf(this);
      }
      try { return od.apply(this, arguments); } catch (e) { err('callback', e); throw e; }
    };
  }
  if (typeof NP.emit === 'function') {
    var oem = NP.emit;
    NP.emit = function (type) {
      var c = P.cur;
      if (c && type === 'click' && c.clicks.length < 10) { var l = false; try { l = !!this.hasEventListener('click'); } catch (e) {} c.clicks.push({ path: pathOf(this), listeners: l }); }
      return oem.apply(this, arguments);
    };
  }
  var EH = (cc.Component && cc.Component.EventHandler) || cc.EventHandler;
  function bad(h) {
    if (!h) return 'an empty clickEvents entry';
    var t = h.target; if (!t || t.isValid === false) return 'a clickEvents entry with no target node';
    var cn = h._componentName || h.component, comp = null;
    try { comp = cn ? t.getComponent(cn) : null; } catch (e) {}
    if (!comp) return 'component ' + (cn || '(none)') + ' is not on ' + pathOf(t);
    if (typeof comp[h.handler] !== 'function') return cn + '.' + (h.handler || '(empty)') + ' is not a function';
    return null;
  }
  if (EH && typeof EH.emitEvents === 'function') {
    var oee = EH.emitEvents;
    EH.emitEvents = function (events) {
      var c = P.cur;
      if (c && c.emits.length < 10) {
        var ev = arguments[1], from = ev && (ev.currentTarget || ev.target), b = [];
        (events || []).forEach(function (h) { var w = bad(h); if (w) b.push(w); });
        c.emits.push({ from: from && from.parent !== undefined ? pathOf(from) : null, n: events ? events.length : 0, bad: b });
      }
      try { return oee.apply(this, arguments); } catch (e) { err('callback', e); throw e; }
    };
  }
  function track(label, args, cbIndex) {
    var c = P.cur; if (!c) return args;
    c.calls.length < 20 && c.calls.push(label);
    if (cbIndex < 0) return args;
    var id = ++P.seq, row = { id: id, what: label, t: Date.now() };
    P.pend.push(row); if (P.pend.length > 100) P.pend.shift();
    var done = function () { P.pend = P.pend.filter(function (x) { return x.id !== id; }); };
    var a = Array.prototype.slice.call(args), f = a[cbIndex];
    if (typeof f === 'function') a[cbIndex] = function () { done(); return f.apply(this, arguments); };
    else if (f && typeof f === 'object') {
      var o = {}; for (var k in f) o[k] = f[k];
      ['success', 'fail', 'complete'].forEach(function (k) { var g = f[k]; o[k] = function () { done(); if (typeof g === 'function') return g.apply(this, arguments); }; });
      a[cbIndex] = o;
    }
    a.__done = done;
    return a;
  }
  function lastFn(args) { for (var i = args.length - 1; i >= 0; i--) if (typeof args[i] === 'function') return i; return -1; }
  function wrapLoad(obj, name, label) {
    if (!obj || typeof obj[name] !== 'function' || obj[name].__bsWrapped) return;
    var o = obj[name];
    obj[name] = function () {
      if (!P.cur) return o.apply(this, arguments);
      var i = lastFn(arguments), a = track(label + '(' + txt(arguments[0]).slice(0, 60) + ')', arguments, i);
      return o.apply(this, a);
    };
    obj[name].__bsWrapped = true;
  }
  wrapLoad(cc.resources, 'load', 'cc.resources.load'); wrapLoad(cc.resources, 'loadDir', 'cc.resources.loadDir');
  wrapLoad(cc.assetManager, 'loadBundle', 'cc.assetManager.loadBundle'); wrapLoad(cc.assetManager, 'loadRemote', 'cc.assetManager.loadRemote');
  wrapLoad(cc.loader, 'loadRes', 'cc.loader.loadRes'); wrapLoad(cc.loader, 'loadResDir', 'cc.loader.loadResDir'); wrapLoad(cc.loader, 'load', 'cc.loader.load');
  wrapLoad(cc.director, 'loadScene', 'cc.director.loadScene');
  var tt = window.tt;
  if (tt && typeof tt === 'object') Object.keys(tt).forEach(function (k) {
    var f = tt[k];
    if (typeof f !== 'function' || /^(on|off)[A-Z]|Sync$|^create/.test(k) || f.__bsWrapped) return;
    try {
      tt[k] = function (o) {
        if (!P.cur) return f.apply(this, arguments);
        var hasCb = o && typeof o === 'object' && (o.success || o.fail || o.complete);
        var a = track('tt.' + k, arguments, 0), r;
        if (!hasCb && a.__done) { var d0 = a.__done; a = Array.prototype.slice.call(arguments); a.__done = d0; }
        try { r = f.apply(this, a); } catch (e) { a.__done && a.__done(); err('tt.' + k, e); throw e; }
        if (a.__done) { if (r && typeof r.then === 'function') r.then(a.__done, a.__done); else if (!hasCb) a.__done(); }
        return r;
      };
      tt[k].__bsWrapped = true;
    } catch (e) {}
  });
  return true;
})()`;

export async function installProbe(page) {
  return page.evaluate(PROBE_JS).catch(() => false);
}
// Open a tap window; returns the page clock (ms) at its start (pass it to probeRead as `since`), or null.
export async function probeStart(page, target) {
  await installProbe(page);
  return page.evaluate((t) => { const P = window.__bsProbe; if (!P) return null; P.cur = { t0: Date.now(), target: t, hit: null, end: null, cancel: null, emits: [], clicks: [], calls: [], err: null }; return P.cur.t0; }, target).catch(() => null);
}
export async function probeStop(page) {
  await page.evaluate(() => { if (window.__bsProbe) window.__bsProbe.cur = null; }).catch(() => {});
}
// What the open tap window saw, plus the target button's own state; `since` = page ms from which unanswered requests
// count (a tap's own start, or the tap that opened a popup), hostIdx = window.__hostLog length at that point.
export async function probeRead(page, target, since, hostIdx = 0) {
  return evalJs(page, 'var P = window.__bsProbe; if (!P || !P.cur) return { installed: false };' +
    'var c = P.cur, since = ' + JSON.stringify(since == null ? 0 : since) + ', T = ' + JSON.stringify(String(target).replace(/#[0-9]+$/, '')) + ';' +
    'var pend = P.pend.filter(function (x) { return x.t >= since; }).map(function (x) { return { what: x.what, ms: Date.now() - x.t }; });' +
    'var hl = (window.__hostLog || []).slice(' + (+hostIdx || 0) + '), sub = {}, ads = 0, unit = "";' +
    'hl.forEach(function (r) { if (/^subpackage(-ok|-fail)?$/.test(r.kind) && r.data && r.data.name) sub[r.data.name] = r.kind; if (r.kind === "ad-show") { ads++; unit = (r.data && r.data.unit) || unit; } if (r.kind === "ad-result") ads = Math.max(0, ads - 1); });' +
    'Object.keys(sub).forEach(function (k) { if (sub[k] === "subpackage") pend.push({ what: "tt.loadSubpackage(" + k + ")" }); });' +
    'if (ads > 0) pend.push({ what: "rewarded ad " + unit + " (show without close)" });' +
    'var n = findNode(T), bt = n && n.getComponent(cc.Button);' +
    'var btn = n ? { exists: !!bt, interactable: bt ? !!bt.interactable : null, events: bt && bt.clickEvents ? bt.clickEvents.length : 0, touchEnd: ownTouchEnd(n) } : null;' +
    'return { installed: true, v3: V3, hit: c.hit, end: c.end, cancel: c.cancel, emits: c.emits, clicks: c.clicks, calls: c.calls, err: c.err, pend: pend, btn: btn };').catch((e) => ({ installed: false, error: String(e).slice(0, 200) }));
}
// Name / BlockInputEvents / cc.Button / opacity / full screen of the node at `path` (for "covered by X").
export async function nodeInfo(page, path) {
  await installProbe(page);
  return evalJs(page, 'var n = findNode(' + JSON.stringify(String(path).replace(/#[0-9]+$/, '')) + '); return n && window.__bsProbe ? window.__bsProbe.info(n) : (n ? { path: pathOf(n) } : null);').catch(() => null);
}

export function nodeCentre(page, path) {
  return evalJs(page, 'return screenOf(findNode(' + JSON.stringify(path) + '));');
}

export async function click(page, x, y) {
  await L.tap(page, x, y);
}

async function poll(fn, timeout) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await fn().catch(() => false)) return Date.now() - t0;
    await sleep(250);
  }
  return -1;
}

export async function runActions(page, actions) {
  const log = [];
  for (const a of actions || []) {
    if (a.wait) { await sleep(a.wait); log.push({ wait: a.wait }); continue; }
    if (a.tap) {
      const c = await nodeCentre(page, a.tap);
      if (!c) { log.push({ tap: a.tap, ok: false }); if (a.optional) continue; return { ok: false, log, why: 'tap target not visible: ' + a.tap }; }
      await click(page, c.x, c.y);
      log.push({ tap: a.tap, ok: true, at: [Math.round(c.x), Math.round(c.y)] });
      await sleep(a.after || 700);
      continue;
    }
    if (a.drag_js) {
      const pts = await evalJs(page, 'var ab = (function(){' + a.drag_js + '\n})(); if (!ab || !ab[0] || !ab[1]) return null; return [screenOf(ab[0]), screenOf(ab[1])];');
      if (!pts || !pts[0] || !pts[1]) { log.push({ drag: false }); return { ok: false, log, why: 'drag targets not found' }; }
      const [p, q] = pts;
      await page.cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x, y: p.y, button: 'left', buttons: 0 });
      await page.cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x: p.x, y: p.y, button: 'left', buttons: 1, clickCount: 1 });
      for (let k = 1; k <= 14; k++) { await page.cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x + (q.x - p.x) * k / 14, y: p.y + (q.y - p.y) * k / 14, button: 'left', buttons: 1 }); await sleep(20); }
      await page.cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x: q.x, y: q.y, button: 'left', buttons: 0, clickCount: 1 });
      log.push({ drag: [p.path, q.path] });
      await sleep(a.after || 1500);
      continue;
    }
    if (a.js) {
      const r = await evalJs(page, a.js).catch((e) => 'threw: ' + e);
      log.push({ js: String(a.js).slice(0, 50), r });
      await sleep(a.after || 300);
      continue;
    }
    if (a.wait_scene) {
      const ms = await poll(() => page.evaluate((s) => { const sc = window.cc && cc.director.getScene(); return !!(sc && (sc.name === s)); }, a.wait_scene), a.timeout || 30000);
      log.push({ wait_scene: a.wait_scene, ms });
      if (ms < 0) return { ok: false, log, why: 'scene ' + a.wait_scene + ' not reached' };
      await sleep(a.after || 1000);
      continue;
    }
    if (a.wait_node) {
      const ms = await poll(async () => !!(await nodeCentre(page, a.wait_node)), a.timeout || 8000);
      log.push({ wait_node: a.wait_node, ms });
      if (ms < 0) { if (a.optional) continue; return { ok: false, log, why: 'node ' + a.wait_node + ' did not appear' }; }
      await sleep(a.after || 500);
      continue;
    }
    log.push({ unknown: a });
    return { ok: false, log, why: 'unknown action ' + JSON.stringify(a).slice(0, 80) };
  }
  return { ok: true, log };
}

// ---------- 3D occlusion ----------
// In-page, started without awaiting (the result is polled into window.__occ): pixel occlusion of 2D candidates by
// 3D content. With the director paused, the node's opacity is toggled once with 3D on and once with every
// MeshRenderer off; visible share = pixels it changes in the real frame / pixels it changes with no 3D.
export const OCCLUSION_JS = `(function (cands) {
  window.__occ = null;
  ${GEOM_JS}
  var gl = glContext();
  if (!gl || !gl.readPixels) { window.__occ = { error: 'no webgl context' }; return; }
  var W = gl.drawingBufferWidth, H = gl.drawingBufferHeight, T = 20;
  var FR = V3 ? frameCss() : null, FS = V3 ? null : cc.view.getFrameSize();
  var fx = V3 ? FR.left : 0, fy = V3 ? FR.top : 0, kx = V3 ? W / FR.w : W / FS.width, ky = V3 ? H / FR.h : H / FS.height;
  function grab() { return new Promise(function (res) { cc.director.once(cc.Director.EVENT_AFTER_DRAW, function () { res(readFrame(gl, W, H)); }); }); }
  function settle() { return grab().then(grab); }
  var byPath = {}, seen = {};
  walkScene(function (n) { if (!n.activeInHierarchy) return; var p = pathOf(n); seen[p] = (seen[p] || 0) + 1; byPath[seen[p] > 1 ? p + '#' + seen[p] : p] = n; });
  var meshes = meshRenderers();
  if (!meshes.length) { window.__occ = { W: W, H: H, meshes: 0, res: [] }; return; }
  function d(P, Q, i) { return Math.max(Math.abs(P[i] - Q[i]), Math.abs(P[i + 1] - Q[i + 1]), Math.abs(P[i + 2] - Q[i + 2])); }
  function rect(b) { return { x0: Math.max(0, Math.floor((b.x0 - fx) * kx)), x1: Math.min(W, Math.ceil((b.x1 - fx) * kx)), y0: Math.max(0, Math.floor(H - (b.y1 - fy) * ky)), y1: Math.min(H, Math.ceil(H - (b.y0 - fy) * ky)) }; }
  var A, A2, B, out = [];
  settle().then(function (a) { A = a; return grab(); }).then(function (a2) { A2 = a2; meshes.forEach(function (c) { c.enabled = false; }); return settle(); })
  .then(function (b) { B = b; meshes.forEach(function (c) { c.enabled = true; }); return settle(); })
  .then(function () {
    var chain = Promise.resolve();
    cands.forEach(function (cd) {
      chain = chain.then(function () {
        var r = rect(cd.box), area = Math.max(0, r.x1 - r.x0) * Math.max(0, r.y1 - r.y0);
        var o = { path: cd.path, kind: cd.kind };
        if (area < 16) { out.push(o); return; }
        var m = 0;
        for (var y = r.y0; y < r.y1; y++) for (var x = r.x0; x < r.x1; x++) { var i = (y * W + x) * 4; if (d(A, A2, i) <= T && d(A, B, i) > T) m++; }
        o.m3d = +(m / area).toFixed(3);
        if (o.m3d < 0.03) { out.push(o); return; }
        var n = byPath[cd.path]; if (!n) { o.err = 'node gone'; out.push(o); return; }
        var restore = hideNode(n), Aoff, Boff;
        return settle().then(function (x) { Aoff = x; meshes.forEach(function (c) { c.enabled = false; }); return settle(); })
          .then(function (x) { Boff = x; restore(); meshes.forEach(function (c) { c.enabled = true; }); return settle(); })
          .then(function () {
            var u = 0, v = 0;
            for (var y = r.y0; y < r.y1; y++) for (var x = r.x0; x < r.x1; x++) { var i = (y * W + x) * 4; if (d(B, Boff, i) > T) { u++; if (d(A, Aoff, i) > T) v++; } }
            o.footprint = u; o.visible = u ? +(v / u).toFixed(3) : null; o.covered = u ? +(1 - v / u).toFixed(3) : null; out.push(o);
          });
      });
    });
    return chain;
  })
  .then(function () { window.__occ = { W: W, H: H, meshes: meshes.length, res: out }; })
  .catch(function (e) { meshes.forEach(function (c) { c.enabled = true; }); window.__occ = { error: String(e && e.stack || e) }; });
})`;

// Share of a node's screen box whose pixels change when the node is hidden (0 = the player cannot see it: scrolled
// out of a list window, or under a frame drawn later). W87 calibration, 指尖麻将 v56: Skin5/6 of the Tile Collection
// sit below the list window under the panel frame; the mask box is larger than what is drawn, so only pixels tell.
export async function drawnShare(page, path) {
  await page.evaluate('(function(path){' + GEOM_JS + `
    window.__drawn = null;
    var n = cc.find(path.replace(/#[0-9]+$/, '')); var gl = glContext(); if (!n || !gl || !gl.readPixels) { window.__drawn = { error: 'no node or no webgl' }; return; }
    var W = gl.drawingBufferWidth, H = gl.drawingBufferHeight, F = V3 ? frameCss() : null, FS = V3 ? null : cc.view.getFrameSize();
    var fx = V3 ? F.left : 0, fy = V3 ? F.top : 0, kx = V3 ? W / F.w : W / FS.width, ky = V3 ? H / F.h : H / FS.height;
    var b = cssBox(n); if (!b) { window.__drawn = { error: 'no box' }; return; }
    var r = { x0: Math.max(0, Math.floor((b.x0 - fx) * kx)), x1: Math.min(W, Math.ceil((b.x1 - fx) * kx)), y0: Math.max(0, Math.floor(H - (b.y1 - fy) * ky)), y1: Math.min(H, Math.ceil(H - (b.y0 - fy) * ky)) };
    var area = Math.max(0, r.x1 - r.x0) * Math.max(0, r.y1 - r.y0); if (area < 16) { window.__drawn = { share: 0, area: area }; return; }
    function grab() { return new Promise(function (res) { cc.director.once(cc.Director.EVENT_AFTER_DRAW, function () { res(readFrame(gl, W, H)); }); }); }
    var A, restore;
    grab().then(grab).then(function (a) { A = a; restore = hideNode(n); return grab().then(grab); }).then(function (B) {
      restore(); var c = 0;
      for (var y = r.y0; y < r.y1; y++) for (var x = r.x0; x < r.x1; x++) { var i = (y * W + x) * 4; if (Math.max(Math.abs(A[i] - B[i]), Math.abs(A[i + 1] - B[i + 1]), Math.abs(A[i + 2] - B[i + 2])) > 20) c++; }
      window.__drawn = { share: +(c / area).toFixed(3), area: area };
    }).catch(function (e) { try { restore && restore(); } catch (x) {} window.__drawn = { error: String(e) }; });
  })(` + JSON.stringify(path) + ')');
  for (let i = 0; i < 40; i++) { await sleep(150); const d = await page.evaluate(() => window.__drawn).catch(() => null); if (d) return d; }
  return { error: 'timeout' };
}

// Measure 3D occlusion of candidates {path, kind, box} with the director paused (caller pauses / resumes).
export async function occlusion(page, cands, maxPolls = 240) {
  if (!cands.length) return { res: [], meshes: 0 };
  await page.evaluate(OCCLUSION_JS + '(' + JSON.stringify(cands) + ')');
  let occ = null;
  for (let i = 0; i < maxPolls && !occ; i++) { await sleep(250); occ = await page.evaluate(() => window.__occ).catch(() => null); }
  return occ || { error: 'timeout' };
}
// covered_3d thresholds: a button >= 30 % painted over, a label >= 50 %, on at least 40 px of its own footprint
export const coveredOf = (occ) => ((occ && occ.res) || []).filter((r) => r.covered != null && r.footprint >= 40 && r.covered >= (r.kind === 'button' ? 0.3 : 0.5));
