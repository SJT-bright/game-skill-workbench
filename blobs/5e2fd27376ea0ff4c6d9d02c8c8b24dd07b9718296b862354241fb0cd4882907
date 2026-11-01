// Shared steps for the v7.9 suites resume_play and ad_outcome (手机才出的五类问题 1、2, 甜点消消乐 R39-R47).
// What a phone does and a desktop browser never does: TikTok takes the game away in the middle of a level (lock screen,
// Control Center, a call, and EVERY rewarded video, which plays as a native page) and gives it back with tt.onShow; a
// finger that was on the glass when that happened never sends touchend / touchcancel. Import with:
//   const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
export const sleep = G.sleep;

// Value of an adapter JS body (function body with `return`; gates HELPERS available: findNode, screenOf, comp, req ...).
// A cc.Node result becomes its screen point. Errors come back as {adapterError}.
export async function js(page, body) {
  try {
    return await G.evalJs(page, 'try { var __r = (function(){' + body + '\n})(); if (__r && __r.getComponent && __r.parent !== undefined) return screenOf(__r) || { node: pathOf(__r), offScreen: true }; return __r === undefined ? null : JSON.parse(JSON.stringify(__r)); } catch (e) { return { adapterError: String(e && e.message || e).slice(0, 300) }; }');
  } catch (e) { return { adapterError: String(e && e.message || e).slice(0, 300) }; }
}
export const truthy = (v) => !!v && !(typeof v === 'object' && (v.adapterError || v.offScreen)) && v.ok !== false;
const isPoint = (v) => v && typeof v.x === 'number' && typeof v.y === 'number' && !v.offScreen;
export const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// A tap target: "Canvas/a/b" | {tap: path} | {tap_js: body returning a node or {x, y}} -> CSS point or null
export async function point(page, spec) {
  if (!spec) return null;
  if (typeof spec === 'string') return G.nodeCentre(page, spec).catch(() => null);
  if (spec.tap) return G.nodeCentre(page, spec.tap).catch(() => null);
  if (spec.tap_js) { const v = await js(page, spec.tap_js); return isPoint(v) ? v : null; }
  return null;
}

// Real-input steps: everything gates.runActions knows (tap, drag_js, js, wait, wait_scene, wait_node) plus
//   {"tap_js": "...return node"}                         tap what the JS returns (null + optional: skipped)
//   {"wait_js": "...return true", "timeout": 20000}      until the JS is true
//   {"repeat": 60, "until_js": "...", "do": [steps]}     the steps again and again until until_js is true
export async function steps(page, list, log = []) {
  for (const a of list || []) {
    if (a && a.repeat) {
      const n = Math.max(1, Math.min(+a.repeat || 1, 200));
      let done = false, i = 0;
      for (; i < n && !done; i++) {
        if (a.until_js && truthy(await js(page, a.until_js))) { done = true; break; }
        const r = await steps(page, a.do || [], []);
        if (!r.ok) return { ok: false, log, why: 'repeat step ' + (i + 1) + ': ' + r.why };
      }
      if (!done && a.until_js) done = truthy(await js(page, a.until_js));
      log.push({ repeat: i, done });
      if (a.until_js && !done && !a.optional) return { ok: false, log, why: 'repeat ' + n + 'x and until_js still false' };
      continue;
    }
    if (a && a.tap_js) {
      const p = await point(page, a);
      if (!p) { log.push({ tap_js: false }); if (a.optional) { await sleep(a.after_skip || 150); continue; } return { ok: false, log, why: 'tap_js found nothing on screen' }; }
      await G.click(page, p.x, p.y);
      log.push({ tap_js: true, at: [Math.round(p.x), Math.round(p.y)] });
      await sleep(a.after || 700);
      continue;
    }
    if (a && a.wait_js) {
      const t0 = Date.now(), limit = a.timeout || 20000;
      let ok = false;
      while (Date.now() - t0 < limit && !(ok = truthy(await js(page, a.wait_js)))) await sleep(300);
      log.push({ wait_js: ok, ms: Date.now() - t0 });
      if (!ok && !a.optional) return { ok: false, log, why: 'wait_js still false after ' + limit + ' ms' };
      await sleep(a.after || 300);
      continue;
    }
    const r = await G.runActions(page, [a]);
    log.push(...r.log);
    if (!r.ok) return { ok: false, log, why: r.why };
  }
  return { ok: true, log };
}

// tt.onHide / tt.onShow (both hosts: window.__simHide / __simShow)
export const hide = (page) => page.evaluate(() => { (window.__simHide || function () {})(); return !!window.__simHide; });
export const show = (page) => page.evaluate(() => { (window.__simShow || function () {})(); return !!window.__simShow; });
export const hostIdx = (page) => page.evaluate(() => (window.__hostLog || []).length).catch(() => 0);
export const hostSince = (page, idx) => page.evaluate((i) => (window.__hostLog || []).slice(i).map((r) => ({ t: r.t, kind: r.kind, data: r.data })), idx).catch(() => []);

// A finger lands and the phone takes the game away: a touchstart on the game canvas that never gets touchend /
// touchcancel (2.x host: DOM touch -> tt.onTouchStart with screenX/screenY only). Returns false where the host does not
// take DOM touches (3.x host: pointer events), then the case is "not covered".
export const touchHold = (page, x, y, id = 7) => page.evaluate(([x, y, id]) => {
  if (!(window.__simHide && window.__faults)) return false;   // 2.x host only (window.__faults is its fault table)
  const cv = document.getElementById('GameCanvas'); if (!cv || typeof Touch !== 'function') return false;
  const t = new Touch({ identifier: id, target: cv, clientX: x, clientY: y, screenX: x, screenY: y, pageX: x, pageY: y, force: 1 });
  cv.dispatchEvent(new TouchEvent('touchstart', { touches: [t], changedTouches: [t], targetTouches: [t], bubbles: true, cancelable: true }));
  return true;
}, [x, y, id]);

// The pause popup the game may show after it comes back: tap its continue / resume button until it is gone.
// -> {taps, still}: still = the button is still on screen after `max` taps (the first tap after returning was lost).
export async function tapContinue(page, path, max = 2) {
  let taps = 0;
  if (!path) return { taps, still: false };
  for (; taps < max; taps++) {
    const c = await G.nodeCentre(page, path).catch(() => null);
    if (!c) return { taps, still: false };
    await G.click(page, c.x, c.y);
    await sleep(1300);
  }
  return { taps, still: !!(await G.nodeCentre(page, path).catch(() => null)) };
}

// Is the level playing? clock_js must change by itself over 2 s (when given); one real probe (a real tap / drag) must
// change state_js within 3 s. -> {ok, why, clock: [a, b], state: [before, after]}
export async function playable(page, B) {
  const out = { ok: true };
  if (B.clock_js) {
    const a = await js(page, B.clock_js); await sleep(2000); const b = await js(page, B.clock_js);
    out.clock = [a, b];
    if (a && a.adapterError) return Object.assign(out, { ok: false, why: 'clock_js threw: ' + a.adapterError, adapter: true });
    if (same(a, b)) return Object.assign(out, { ok: false, why: 'the level clock does not move (clock_js ' + JSON.stringify(a) + ' -> ' + JSON.stringify(b) + ' over 2 s)' });
  }
  const s0 = await js(page, B.state_js);
  if (s0 && s0.adapterError) return Object.assign(out, { ok: false, why: 'state_js threw: ' + s0.adapterError, adapter: true });
  const probe = B.probe || {};
  let r;
  if (probe.tap || probe.tap_js) {
    const p = await point(page, probe);
    if (!p) return Object.assign(out, { ok: false, why: 'probe target not on screen (' + (probe.tap || 'tap_js') + ')', state: [s0, s0] });
    await G.click(page, p.x, p.y); r = { ok: true };
  } else r = await steps(page, [probe]);
  if (!r.ok) return Object.assign(out, { ok: false, why: 'probe could not run: ' + r.why, state: [s0, s0] });
  let s1 = s0;
  const t0 = Date.now();
  while (Date.now() - t0 < 3000) { await sleep(300); s1 = await js(page, B.state_js); if (!same(s0, s1)) break; }
  out.state = [s0, s1];
  if (same(s0, s1)) return Object.assign(out, { ok: false, why: 'a real ' + (probe.tap ? 'tap on ' + probe.tap : probe.tap_js ? 'tap (probe.tap_js)' : 'probe') + ' changed nothing (state_js stays ' + JSON.stringify(s0).slice(0, 80) + ')' });
  return out;
}

// Reaction to a real click on (x, y) within `ms`: ad call / toast / modal (window.__gateLog) or a new / changed label.
export async function reaction(page, x, y, ms = 2000) {
  const labels = async () => { const v = await G.visibleNodes(page).catch(() => ({ nodes: [] })); return Object.fromEntries(v.nodes.filter((n) => n.kind === 'label').map((n) => [n.path, n.text])); };
  const before = await labels();
  const mark = await page.evaluate(() => (window.__gateNow ? window.__gateNow() : 0)).catch(() => 0);
  await G.click(page, x, y);
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    await sleep(250);
    const ev = await page.evaluate((m) => (window.__gateLog || []).filter((r) => r.t >= m && /^(ad-create|ad-show|toast|modal)$/.test(r.kind)), mark).catch(() => []);
    if (ev.length) return { kind: /^ad/.test(ev[0].kind) ? 'ad' : 'prompt', detail: ev[0], ms: Date.now() - t0 };
    const now = await labels();
    const fresh = Object.keys(now).filter((k) => now[k] && before[k] !== now[k]);
    if (fresh.length) return { kind: 'text', detail: fresh.slice(0, 3).map((k) => k + ' = ' + now[k]), ms: Date.now() - t0 };
  }
  return null;
}
