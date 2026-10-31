// trial_link (v7.8, 总表 B21 + B30 F): the local trial link exactly as Saul opens it (CFG.trialUrl, no URL switches),
// from the 全民飞车门禁 prototype trial_link_smoke.mjs. Any trial page whose game runs in the top window or in an iframe
// (found by window.cc): serve_preview.py's fixed-phone shell with --ad-simulator, or a TikTok-package host page.
// Desktop window 1180 x 960, fresh save, stable scene, then the taps that lead to a rewarded ad with the real mouse:
// adapter.trial.taps (or trial.open[].tap + trial.ad_button), else the first home button whose texts / sprite names
// read like an ad entry (layout_rules.AD_WORDS; up to 3 tried). Within 2.5 s the player must SEE an answer:
//   a page element covers the game and is on top at its centre (the simulated ad window: serve_preview's
//   #__ad-simulator in its shadow root, the TikTok host's #__adOverlay), or a toast / modal, or an on-screen text change.
// If an ad window is up, its 看完 / complete button is clicked once it is enabled; the game must then change
// (adapter.trial.reward_js changes, else any on-screen text changes).
//   ad_window_hidden  tapped, nothing visible: the game waits for an ad result and looks frozen (B21: the window was
//                     appended to the adapter's fake body)
//   reward_missing    看完 picked in the ad window, nothing changed in the game
// No ad entry known or found: the suite records "not run" with the reason (a warning, never a pass of the window check).
const L = await import(globalThis.CFG.lib);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const fs = await import('node:fs/promises');
const path = await import('node:path');
const C = L.C, A = L.A;
const URL0 = C.trialUrl;
const T = (A && A.trial) || {};

// the game window: top, or an iframe holding window.cc
const GW = `(function(){ if (window.cc && window.cc.director) return { w: window, f: null }; var fs = document.querySelectorAll('iframe');
  for (var i = 0; i < fs.length; i++) { try { var w = fs[i].contentWindow; if (w && w.cc && w.cc.director) return { w: w, f: fs[i] }; } catch (e) {} } return null; })()`;
// page point of a node centre (2.x through cc.view's viewport, 3.x through the camera of the node's Canvas)
const where = (page, p) => page.evaluate(`(function(path){ var g = ${GW}; if (!g) return null; var w = g.w, cc = w.cc, n = cc.find(path);
  var roots = function (s) { return cc.UITransform ? (s.children || []) : [s]; };
  if (!n) { var tail = '/' + path.replace(/^[*][/]/, ''); roots(cc.director.getScene()).forEach(function (r0) { r0.walk(function (x) { if (n || !x.activeInHierarchy) return; var p = [], y = x; while (y && y.parent) { p.unshift(y.name); y = y.parent; } if (('/' + p.join('/')).slice(-tail.length) === tail) n = x; }); }); }
  if (!n || !n.activeInHierarchy) return null;
  var cv = Document.prototype.querySelector.call(w.document, 'canvas'), cr = Element.prototype.getBoundingClientRect.call(cv), fr = g.f ? g.f.getBoundingClientRect() : { left: 0, top: 0 };
  var sc = g.f ? (fr.width / (g.f.offsetWidth || fr.width)) : 1;
  if (cc.UITransform) {
    var ut = n.getComponent(cc.UITransform); if (!ut) return null; var b3 = ut.getBoundingBoxToWorld();
    var p, v2api = false, centre = new cc.Vec3(b3.x + b3.width / 2, b3.y + b3.height / 2, n.worldPosition ? n.worldPosition.z : 0);
    (function (n, w) {
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
    })(n, centre);
    var q = (function (canvas, rect) {
      // css-point:begin (v7.7.5, 总表 A13) the same conversion as ad_regression/cases.mjs (A5): Cocos 2.x
      // getWorldToScreenPoint works in cc.visibleRect units, 3.x worldToScreen in canvas pixels.
      const vis = (v2api && cc.visibleRect) ? { w: cc.visibleRect.width, h: cc.visibleRect.height } : { w: canvas.width, h: canvas.height };
      return { x: rect.left + p.x * rect.width / vis.w, y: rect.top + rect.height - p.y * rect.height / vis.h };
      // css-point:end
    })(cv, cr);
    return { x: fr.left + q.x * sc, y: fr.top + q.y * sc };
  }
  var bb = n.getBoundingBoxToWorld(), o = cc.view.getVisibleOrigin(), vs = cc.view.getVisibleSize();
  var v = cc.view, vp = v.getViewportRect ? v.getViewportRect() : null, mx = cv.width / cr.width, my = cv.height / cr.height;
  if (vp && vp.width > 0 && v.getScaleX && v.getScaleX() > 0)
    return { x: fr.left + (cr.left + (vp.x + (bb.x + bb.width / 2) * v.getScaleX()) / mx) * sc, y: fr.top + (cr.top + cr.height - (vp.y + (bb.y + bb.height / 2) * v.getScaleY()) / my) * sc };
  return { x: fr.left + (cr.left + (bb.x + bb.width / 2 - o.x) * cr.width / vs.width) * sc, y: fr.top + (cr.top + cr.height - (bb.y + bb.height / 2 - o.y) * cr.height / vs.height) * sc }; })(${JSON.stringify(p)})`);
const texts = (page) => page.evaluate(`(function(){ var g = ${GW}; if (!g) return null; var cc = g.w.cc, s = cc.director.getScene(), out = [];
  (cc.UITransform ? (s.children || []) : [s]).forEach(function (r0) { r0.walk(function (n) { if (!n.activeInHierarchy) return; var l = n.getComponent(cc.Label); if (l && l.string) out.push(n.name + '=' + l.string); }); });
  return out.join('|'); })()`);
// home buttons that read like an ad entry, top to bottom (texts, sprite frame names, node names of the button subtree)
const adCandidates = (page) => page.evaluate(`(function(rx){ var g = ${GW}; if (!g) return []; var cc = g.w.cc, s = cc.director.getScene(), out = [], re = new RegExp(rx, 'i');
  var path = function (n) { var p = []; while (n && n.parent) { p.unshift(n.name); n = n.parent; } return p.join('/'); };
  (cc.UITransform ? (s.children || []) : [s]).forEach(function (r0) { r0.walk(function (n) { if (!n.activeInHierarchy || !n.getComponent(cc.Button)) return;
    var b = n.getComponent(cc.Button); if (!b.enabled || b.interactable === false) return; var bits = [n.name];
    n.walk(function (x) { if (!x.activeInHierarchy) return; var l = x.getComponent(cc.Label); if (l && l.string) bits.push(l.string); var sp = x.getComponent(cc.Sprite); if (sp && sp.spriteFrame) bits.push(sp.spriteFrame.name); bits.push(x.name); });
    var sig = bits.join(' '); if (re.test(sig)) out.push({ path: path(n), sig: sig.slice(0, 80) }); }); });
  return out.slice(0, 6); })(${JSON.stringify(R.AD_WORDS.source)})`).catch(() => []);
// what the player sees after the tap: an element over the game's centre (top document, and the game document when the
// game is in an iframe), its 看完 / complete button (light DOM or shadow root), ad / toast counters in the game window
const SEEN = `(function(){ var g = ${GW}; if (!g) return { err: 'no game window' }; var docs = [document]; if (g.f) docs.push(g.w.document);
  var cv = Document.prototype.querySelector.call(g.w.document, 'canvas'), cr = Element.prototype.getBoundingClientRect.call(cv);
  var fr = g.f ? g.f.getBoundingClientRect() : { left: 0, top: 0, width: 0 }, sc = g.f ? (fr.width / (g.f.offsetWidth || fr.width)) : 1;
  var tt0 = g.w.tt || (g.w.__H && g.w.__H.G && g.w.__H.G.tt);
  var res = { smoke: tt0 && tt0.__smoke, overlay: null };
  function findBtn(root) { var all = root.querySelectorAll('button,[data-r],a,div'), hit = null;
    for (var i = 0; i < all.length && !hit; i++) { var tx = (all[i].textContent || '') + ' ' + (all[i].getAttribute('data-r') || '');
      if (/看完|complete|finish|发奖|watched/i.test(tx) && all[i].children.length === 0) hit = all[i]; } return hit; }
  for (var k = 0; k < docs.length && !res.overlay; k++) { var d = docs[k], inGame = k === 1;
    var cx = inGame ? cr.left + cr.width / 2 : fr.left + (cr.left + cr.width / 2) * sc, cy = inGame ? cr.top + cr.height / 2 : fr.top + (cr.top + cr.height / 2) * sc;
    var hit = Document.prototype.elementFromPoint.call(d, cx, cy);
    if (!hit || hit === cv || hit.tagName === 'CANVAS' || hit.tagName === 'IFRAME' || hit === d.body || hit === d.documentElement) continue;
    var el = hit; while (el.parentElement && el.parentElement !== d.body) { var r0 = Element.prototype.getBoundingClientRect.call(el.parentElement); if (r0.width >= cr.width * 0.5) el = el.parentElement; else break; }
    var r = Element.prototype.getBoundingClientRect.call(el); if (r.width < cr.width * 0.5 * (inGame ? 1 : sc) || r.height < cr.height * 0.3 * (inGame ? 1 : sc)) continue;
    var btn = findBtn(el) || (el.shadowRoot && findBtn(el.shadowRoot)) || (hit.shadowRoot && findBtn(hit.shadowRoot));
    var br = btn && btn.getBoundingClientRect(), off = inGame ? fr : { left: 0, top: 0 }, k2 = inGame ? sc : 1;
    res.overlay = { doc: inGame ? 'game' : 'top', tag: el.tagName, id: el.id, size: [Math.round(r.width), Math.round(r.height)],
      complete: br ? { x: off.left + (br.left + br.width / 2) * k2, y: off.top + (br.top + br.height / 2) * k2, disabled: !!btn.disabled, text: String(btn.textContent).slice(0, 40) } : null }; }
  return res; })()`;

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'trial_link', url: URL0, taps: null, steps: [], notRun: null };
  const shot = async (name) => { const r = await page.cdp('Page.captureScreenshot', { format: 'png' }); const f = path.join(C.evidenceDir, 'trial-' + name + '.png'); await fs.writeFile(f, Buffer.from(r.data, 'base64')); return f; };
  const tapXY = (x, y) => L.tap(page, x, y);
  const reward = () => (T.reward_js ? page.evaluate(`(function(){ var g = ${GW}; try { return String(g.w.eval('(function(){' + ${JSON.stringify(T.reward_js || '')} + '\\n})()')); } catch (e) { return 'err ' + e; } })()`) : texts(page));
  const finish = () => { out.evidence.report = L.evidence('trial_link.json', rep); out.evidence.notRun = rep.notRun; };
  if (!URL0) { rep.notRun = 'no trial link given'; out.warn('trial_link: not run: ' + rep.notRun); out.add('ran', true, 'not run: ' + rep.notRun); return finish(); }
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: 1180, height: 960, deviceScaleFactor: 1, mobile: false });
  await page.goto(URL0);
  await page.evaluate(`(function(){ try { localStorage.clear(); var g = ${GW}; if (g && g.f) g.w.localStorage.clear(); } catch (e) {} })()`).catch(() => {});
  await page.goto(URL0);
  await L.keepFrames(page);
  let last = null, since = 0; const t0 = Date.now();
  while (Date.now() - t0 < 60000) {
    const s = await page.evaluate(`(function(){ var g = ${GW}; if (!g) return null; var sc = g.w.cc.director.getScene(); return sc ? sc.name : null; })()`).catch(() => null);
    if (s && s === last) { if (Date.now() - since > 3000) break; } else { last = s; since = Date.now(); }
    await L.sleep(500);
  }
  rep.steps.push({ scene: last, ms: Date.now() - t0 });
  if (!last) { out.add('game_loaded', false, 'no Cocos game found in the trial page within 60 s (top window or iframe)'); return finish(); }
  out.add('game_loaded', true, { scene: last });
  await L.sleep(1500);
  // count ad calls / prompts in the game window, whatever the host is
  await page.evaluate(`(function(){ var g = ${GW}; var tt = g && (g.w.tt || (g.w.__H && g.w.__H.G && g.w.__H.G.tt)); if (!tt || tt.__smoke) return; tt.__smoke = { ads: 0, shows: 0, toasts: 0 };
    var c = tt.createRewardedVideoAd; if (c) tt.createRewardedVideoAd = function () { tt.__smoke.ads++; var a = c.apply(tt, arguments); try { var s = a.show; a.show = function () { tt.__smoke.shows++; return s.apply(a, arguments); }; } catch (e) {} return a; };
    ['showToast', 'showModal'].forEach(function (k) { var f = tt[k]; if (f) tt[k] = function () { tt.__smoke.toasts++; return f.apply(tt, arguments); }; }); })()`).catch(() => {});
  let plans = null;
  if (T.taps) plans = [T.taps];
  else if (T.open || T.ad_button) plans = [(T.open || []).filter((s) => s.tap).map((s) => s.tap).concat(T.ad_button ? [T.ad_button] : [])];
  else plans = (await adCandidates(page)).slice(0, 3).map((c) => [c.path]);
  if (!plans.length) { rep.notRun = 'no ad entry known (adapter trial.taps) and no home button reads like one'; out.warn('trial_link: not run: ' + rep.notRun); out.add('ran', true, 'not run: ' + rep.notRun); return finish(); }
  let seen = null, taps = null, before = null;
  for (const plan of plans) {
    taps = plan; rep.taps = plan;
    let reached = true;
    for (let i = 0; i < plan.length; i++) {
      const p = await where(page, plan[i]);
      if (!p) { reached = false; rep.steps.push({ tap: plan[i], reached: false }); break; }
      if (i === plan.length - 1) before = await reward();
      await tapXY(p.x, p.y);
      rep.steps.push({ tap: plan[i], at: [Math.round(p.x), Math.round(p.y)] });
      await L.sleep(i === plan.length - 1 ? 250 : 1500);
    }
    if (!reached) continue;
    const t1 = Date.now();
    while (Date.now() - t1 < 2500) {
      seen = await page.evaluate(SEEN).catch((e) => ({ err: String(e) }));
      if ((seen && seen.overlay) || (seen && seen.smoke && seen.smoke.toasts)) break;
      await L.sleep(250);
    }
    const now = await reward();
    rep.afterTap = seen;
    if ((seen && seen.overlay) || (seen && seen.smoke && seen.smoke.toasts) || now !== before) break;
    // an auto-found candidate that asked for no ad at all is not an ad entry: try the next one
    if (!T.taps && !T.open && !T.ad_button && !(seen && seen.smoke && (seen.smoke.ads || seen.smoke.shows))) { seen = null; continue; }
    break;
  }
  rep.shotAfterTap = await shot('after-ad-tap');
  if (!rep.afterTap && !T.taps && !T.open && !T.ad_button) {
    rep.notRun = 'none of the ad-like home buttons (' + plans.map((p) => p.join(' > ')).join('; ') + ') asked for an ad; give adapter trial.taps';
    out.warn('trial_link: not run: ' + rep.notRun); out.add('ran', true, 'not run: ' + rep.notRun); return finish();
  }
  const r1 = await reward();
  const visible = !!((seen && seen.overlay) || (seen && seen.smoke && seen.smoke.toasts) || r1 !== before);
  out.add('ad_window_visible', visible, visible ? { overlay: seen && seen.overlay, smoke: seen && seen.smoke }
    : 'ad_window_hidden: tapped ' + taps[taps.length - 1] + ': within 2.5 s no ad window over the game, no toast, nothing changed on screen; the game waits for an ad result (looks frozen). ad calls: ' + JSON.stringify(seen && seen.smoke) + ' (B21: append trial-page elements to the canvas parent, not document.body)');
  if (!visible) return finish();
  if (seen && seen.overlay && seen.overlay.complete) {
    let c = seen.overlay.complete;
    for (let i = 0; i < 20 && c && c.disabled; i++) { await L.sleep(250); const s2 = await page.evaluate(SEEN).catch(() => null); c = (s2 && s2.overlay && s2.overlay.complete) || c; if (s2 && s2.overlay && s2.overlay.complete) c = s2.overlay.complete; }
    await tapXY(c.x, c.y);
    let after = before;
    for (let i = 0; i < 16 && after === before; i++) { await L.sleep(250); after = await reward(); }
    rep.changed = after !== before;
    rep.after = T.reward_js ? after : undefined;
    rep.shotAfterReward = await shot('after-complete');
    out.add('reward_after_complete', rep.changed, rep.changed ? { button: c.text } : 'reward_missing: picked ' + (c.text || '看完') + ' in the ad window: nothing changed in the game');
  } else if (seen && seen.overlay) out.warn('trial_link: the ad window is visible but has no recognisable 看完 / complete button; only visibility was checked');
  finish();
}, { w: 1180, h: 960 });
