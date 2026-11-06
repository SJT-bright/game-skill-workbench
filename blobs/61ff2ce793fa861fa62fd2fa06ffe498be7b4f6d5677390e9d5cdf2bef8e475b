// Shared steps for the v7.9 suites resume_play and ad_outcome (手机才出的五类问题 1、2, 甜点消消乐 R39-R47).
// What a phone does and a desktop browser never does: TikTok takes the game away in the middle of a level (lock screen,
// Control Center, a call, and EVERY rewarded video, which plays as a native page) and gives it back with tt.onShow; a
// finger that was on the glass when that happened never sends touchend / touchcancel. Import with:
//   const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const LIB = await import(globalThis.CFG.lib);   // R4O4: evE (engine_adapter) for snap()
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
// touchcancel. Host hook first (3.x host: window.__H.holdTouch(x, y, id), pointer ids), else a DOM touch on the 2.x
// host's canvas (-> tt.onTouchStart with screenX/screenY only). false = not covered on this host.
export const touchHold = (page, x, y, id = 7) => page.evaluate(([x, y, id]) => {
  if (window.__H && typeof window.__H.holdTouch === 'function') return window.__H.holdTouch(x, y, id) !== false;
  if (!(window.__simHide && window.__faults)) return false;   // 2.x host only (window.__faults is its fault table)
  const cv = (window.__NDoc || document).getElementById('GameCanvas'); if (!cv || typeof Touch !== 'function') return false;
  const t = new Touch({ identifier: id, target: cv, clientX: x, clientY: y, screenX: x, screenY: y, pageX: x, pageY: y, force: 1 });
  cv.dispatchEvent(new TouchEvent('touchstart', { touches: [t], changedTouches: [t], targetTouches: [t], bubbles: true, cancelable: true }));
  return true;
}, [x, y, id]);

// v7.9 (手机检查补全 ⑤): the finger that never lifts, made the way the host makes every real tap. 2.x host: a real mouse
// press without the release (the host turns the mouse into TikTok touch id 0, the id the next finger gets again); that is
// what lost 甜点消消乐 R47's first tap after returning (the engine still held touch 0 and dropped the new touchstart).
// The DOM-touch path above did not reproduce it. 3.x host (pointer events): its holdTouch hook with the mouse pointer id
// 1, because a second press of a held mouse button gives no pointerdown. -> 'mouse' | 'hook' | false
export async function fingerHold(page, x, y) {
  const host3 = await page.evaluate(() => !!(window.__H && typeof window.__H.holdTouch === 'function')).catch(() => false);
  if (host3) return (await touchHold(page, x, y, 1)) ? 'hook' : false;
  await page.cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y, button: 'none', buttons: 0 });
  await page.cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', buttons: 1, clickCount: 1 });
  return 'mouse';
}

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
    out.tap = {x: p.x, y: p.y};
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

// ---------- v7.9 (手机检查补全): screen snapshots, reactions, pause popup ----------
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
export const DEV = G.DEVICES.iphone14;
// an in-level pause control (the Skill rule: every mode has an in-level pause or settings button); pause words first
export const PAUSE = /pause|暂停|zant/i;
export const PAUSE2 = /setting|设置|gear|menu|option|齿轮/i;
// the button of a pause popup that goes back to the level; continue words first, then any close (layout_rules.CLOSE)
export const CONTINUE = /continue|resume|继续|go ?on|keep ?playing|back ?to ?game|返回游戏/i;

// {scene, sceneId, m: {path: visible node}} like button_sweep (layout_rules.snapDiff compares two of them)
export async function snap(page) {
  const v = await G.visibleNodes(page).catch(() => ({ nodes: [] }));
  const sc = await LIB.evE(page, () => { const E = window.__ccAdapt(window); const s = E.ready ? E.scene : null; return s ? { name: s.name, id: s.uuid || s._id } : { notReady: E.reason }; }).catch(() => ({}));   // R4O4 engine_adapter
  const m = {};
  for (const n of v.nodes || []) m[n.path] = n;
  return { scene: sc.name, sceneId: sc.id, m };
}
export const buttonsOf = (s) => R.sweepButtons(s, DEV);
const tail = (p) => String(p).replace(/#\d+$/, '').split('/').slice(-2).join('/');

// What a real tap on `target` (node path or {x, y}) did within `ms`: ad / prompt / platform call / scene / screen / text
// / sprite, or null. Changes in a short idle window before the tap and the button's own press feedback do not count.
export async function tapReact(page, target, opt = {}) {
  const ms = opt.ms || 2500;
  const idle0 = await snap(page); await sleep(opt.idleMs || 1000); const before = await snap(page);
  const d0 = R.snapDiff(idle0, before);
  const noisy = new Set([...d0.add, ...d0.gone, ...d0.moved, ...d0.text, ...d0.sprite]);
  const par = opt.game ? R.noisyParents(noisy) : null;
  const p = typeof target === 'string' ? await G.nodeCentre(page, target).catch(() => null) : target;
  if (!p) return { kind: 'untestable', why: 'not on screen' };
  const mark = await page.evaluate(() => ({ g: window.__gateNow ? window.__gateNow() : 0, h: (window.__hostLog || []).length })).catch(() => ({ g: 0, h: 0 }));
  await G.click(page, p.x, p.y);
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    await sleep(300);
    const ev = await page.evaluate((mk) => (window.__gateLog || []).filter((x) => x.t >= mk.g && /^(ad-create|ad-show|toast|modal)$/.test(x.kind)).map((x) => x.kind)
      .concat((window.__hostLog || []).slice(mk.h).map((x) => 'host:' + x.kind)), mark).catch(() => []);
    if (ev.some((k) => /^(host:)?(ad-create|ad-show|legacy-ad-create)$/.test(k))) return { kind: 'ad', ms: Date.now() - t0 };
    if (ev.some((k) => k === 'toast' || k === 'modal')) return { kind: 'prompt', ms: Date.now() - t0 };
    const plat = ev.find((k) => k.startsWith('host:') && R.PLATFORM_BEACON.test(k.slice(5)));
    if (plat) return { kind: 'platform', detail: plat.slice(5), ms: Date.now() - t0 };
    const after = await snap(page);
    if (after.scene !== before.scene || (after.sceneId && before.sceneId && after.sceneId !== before.sceneId)) return { kind: 'scene', detail: after.scene, ms: Date.now() - t0 };
    let d = R.snapDiff(before, after, noisy);
    if (typeof target === 'string') d = R.dropPress(d, target, before, after);
    if (par) d = R.dropUnder(d, par);
    if (d.add.length || d.gone.length || d.moved.length) return { kind: 'screen', paths: d.add.concat(d.gone, d.moved).slice(0, 4), ms: Date.now() - t0 };
    if (d.text.length) return { kind: 'text', detail: d.text.slice(0, 3), ms: Date.now() - t0 };
    if (d.sprite.length) return { kind: 'sprite', detail: d.sprite.slice(0, 3), ms: Date.now() - t0 };
  }
  return null;
}
// Reaction to a real click on (x, y) (kept for the v7.9 suites written before tapReact)
export const reaction = async (page, x, y, ms = 2000) => { const r = await tapReact(page, { x, y }, { ms }); return r && r.kind !== 'untestable' ? r : null; };

// The level's pause control -> {pause, cont, how} | null. First a button whose popup button_sweep opened in the level this
// run and that popup has a continue / resume button (any name: 香肠 R17 resetBtn「重置」), then a visible button named /
// drawn like pause, then settings / menu.
export async function findPause(page) {
  for (const x of (await priorPausePopups()) || []) if (await G.nodeCentre(page, x.pause).catch(() => null)) return { pause: x.pause, cont: x.cont, how: 'button_sweep popup' };
  const s = await snap(page);
  const bs = buttonsOf(s);
  const hit = (rx) => bs.find((n) => rx.test(tail(n.path)) || rx.test(n.sig || ''));
  const n = hit(PAUSE) || hit(PAUSE2);
  return n ? { pause: String(n.path).replace(/#\d+$/, ''), cont: null, how: 'name' } : null;
}

// Every in-level popup button_sweep opened this run, as "opener -> button, button" (for a refusal that says what the
// level has instead of a pause popup: 割草 v015 btnBack -> close, New Button). [] when none or no button_sweep.
export async function priorLevelPopups() {
  const bs = (globalThis.CFG.prior || {}).button_sweep;
  if (!bs || !bs.report) return [];
  try {
    const fs = await import('node:fs');
    const rep = JSON.parse(fs.readFileSync(bs.report, 'utf-8'));
    return ((rep.game && rep.game.popups) || []).map((p) => tail(p.opener) + ' -> ' + (p.all || p.buttons || []).map((b) => String(b.path).replace(/#\d+$/, '').split('/').pop()).join(', '));
  } catch (_) { return []; }
}

// In-level popups button_sweep opened with real taps this run that have a continue / resume button: [{pause, cont}];
// null = button_sweep did not run before this suite.
export async function priorPausePopups() {
  const bs = (globalThis.CFG.prior || {}).button_sweep;
  if (!bs) return null;
  try {
    const fs = await import('node:fs');
    const rep = bs.report ? JSON.parse(fs.readFileSync(bs.report, 'utf-8')) : null;
    const out = [];
    for (const p of (rep && rep.game && rep.game.popups) || []) {
      const k = (p.all || p.buttons || []).find((b) => CONTINUE.test(tail(b.path)) || CONTINUE.test(b.sig || ''));
      if (k && p.opener) out.push({ pause: String(p.opener).replace(/#\d+$/, ''), cont: String(k.path).replace(/#\d+$/, '') });
    }
    return out;
  } catch (_) { return []; }
}

// Tap the pause control and find the popup's way back. -> {opened, cont, added}: cont = continue / resume button of the
// buttons that appeared (else a close button), added = their paths. The popup is left open.
export async function openPause(page, pausePath) {
  const before = await snap(page);
  const c = await G.nodeCentre(page, pausePath).catch(() => null);
  if (!c) return { opened: false, why: 'pause control not on screen: ' + pausePath };
  await G.click(page, c.x, c.y);
  await sleep(1300);
  const after = await snap(page);
  const added = buttonsOf(after).filter((n) => !before.m[n.path]);
  const pick = (rx) => added.find((n) => rx.test(tail(n.path)) || rx.test(n.sig || ''));
  const n = pick(CONTINUE) || pick(R.CLOSE);
  return { opened: added.length > 0, cont: n ? String(n.path).replace(/#\d+$/, '') : null, added: added.map((x) => x.path).slice(0, 8) };
}

// The continue / resume button among buttons that appeared (a pause popup the game opened while it was away), else null
export const pickContinue = (added) => { const n = (added || []).find((x) => CONTINUE.test(tail(x.path)) || CONTINUE.test(x.sig || '')); return n ? String(n.path).replace(/#\d+$/, '') : null; };

// A tt.showModal dialog the host drew over the game takes every tap: tap its OK like a player would. -> its text | null
export async function dismissModal(page) {
  const r = await page.evaluate(() => {
    if (window.__modalOpen && typeof window.__modalRect === 'function') { const b = window.__modalRect('ok'); return b ? { x: b.x, y: b.y, text: String(window.__modalOpen.title || window.__modalOpen.content || 'modal') } : null; }
    const ov = document.getElementById('ov'), b = document.getElementById('ovb');   // 3.x host
    if (ov && b && ov.style.display === 'flex') { const q = b.getBoundingClientRect(); return { x: q.left + q.width / 2, y: q.top + q.height / 2, text: String((document.getElementById('ovt') || {}).textContent || 'modal') }; }
    return null;
  }).catch(() => null);
  if (!r) return null;
  await G.click(page, r.x, r.y);
  await sleep(700);
  return r.text.slice(0, 60);
}

// How the next simulated ads end (both hosts: window.__setAdPolicy): complete | cancel | error ...
export const setAd = (page, mode) => page.evaluate((m) => { if (typeof window.__setAdPolicy !== 'function') return false; window.__setAdPolicy(m); return true; }, mode).catch(() => false);

// From the home page into a level with a real tap on adapter.play (button_sweep's in-game route '<play>', same rules):
// left = adapter.in_level true, or adapter.home false, or (no home test) the scene changed / most home buttons went away.
export async function enterLevel(page) {
  const L = await import(globalThis.CFG.lib);
  const A = L.A;
  if (!A.play) return { ok: false, why: 'the adapter has no "play" (the startup suite\'s PLAY locator)' };
  const p = await L.locate(page, A.play).catch(() => null);
  if (!p) return { ok: false, why: 'adapter.play found no PLAY button on the home page' };
  const s0 = await snap(page);
  const homeB = buttonsOf(s0);
  await G.click(page, p.x, p.y);
  for (let i = 0; i < 20; i++) {
    await sleep(500);
    let left = false;
    if (A.in_level) left = (await L.adapterCall(page, A.in_level).catch(() => false)) === true;
    if (!left && A.home) { const h = await L.adapterCall(page, A.home).catch(() => true); left = !(h === true || (h && h.ok === true)); }
    if (!left && !A.home && !A.in_level) { const s = await snap(page); left = s.scene !== s0.scene || homeB.filter((n) => !s.m[n.path]).length > homeB.length / 2; }
    if (left) { await sleep(2500); return { ok: true, ms: (i + 1) * 500 }; }
  }
  return { ok: false, why: 'a real tap on PLAY did not leave the home page within 10 s' };
}

// Ad entries another suite of this run found with real taps (button_sweep evidence via CFG.prior): [{taps, sig}];
// taps[0] === '<play>' = the route starts with a real tap on adapter.play (an in-level entry).
// null = button_sweep did not run before this suite in this run (a suite run alone with --suites).
export async function priorAdEntries() {
  const bs = (globalThis.CFG.prior || {}).button_sweep;
  if (!bs) return null;
  let list = Array.isArray(bs.adEntries) ? bs.adEntries.slice() : [];
  // the in-game sweep's entries are only in the report file (rep.game.adEntries)
  try {
    const fs = await import('node:fs');
    const rep = bs.report ? JSON.parse(fs.readFileSync(bs.report, 'utf-8')) : null;
    if (rep && rep.game && Array.isArray(rep.game.adEntries)) list = list.concat(rep.game.adEntries);
  } catch (_) {}
  const seen = new Set();
  return list.filter((e) => e && Array.isArray(e.taps) && e.taps.length && !seen.has(e.taps.join('>')) && seen.add(e.taps.join('>')));
}
