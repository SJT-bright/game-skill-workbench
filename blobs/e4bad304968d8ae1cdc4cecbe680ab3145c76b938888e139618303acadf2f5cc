// Rewarded-ad regression cases, run by ad_regression.py under `ego-browser nodejs`.
// Engine-generic: the only game-specific input is the adapter (CFG.adapter), a few lines of
// page JavaScript that start ONE rewarded request through the game's real reward path.
// Based on the Basil (1溯白) and Marlows r5 (4周燎原) regression tools, 2026-10-28.
//
// globalThis.CFG = {space, url, adapter: {request, state?, ready?, exit_label?, no_music?},
//                   cases?: [...], bootTimeoutMs?, resultFile}
// Timing lives in Node: every page.evaluate call is short (Ego caps one call at 15 s).
const C = globalThis.CFG || {};
const fs = await import('node:fs');
const A = C.adapter || {};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = { tool: 'tiktok-rewarded-ad-regression', version: 1, url: C.url, boot: null, cases: [], warnings: [], fatal: null };
function save() { if (C.resultFile) fs.writeFileSync(C.resultFile, JSON.stringify(out, null, 2)); }

// want = rewards the case's OWN ad may pay. 'next' is the lock probe: an immediate fresh
// request that must start and pay exactly one reward. 'hold' keeps the old ad's controls so
// late SDK callbacks can be delivered after the player has already moved on.
const PLAN = {
  long200: { steps: ['start', 'warp200000', 'end'], want: 1, about: 'video plays 200 s, then completes' },
  late16: { steps: ['warp16000', 'hold', 'next', 'start_held', 'warp70000', 'end_held'], want: 0, about: 'playback starts only after 16 s' },
  bgplay: { steps: ['start', 'hide', 'warp200000', 'show', 'end'], want: 1, about: 'background 200 s during playback' },
  bgload: { steps: ['hide', 'warp200000', 'show', 'start', 'end'], want: 1, about: 'background 200 s while loading' },
  cancel: { steps: ['start', 'quit'], want: 0, about: 'closed midway' },
  error: { steps: ['start', 'err'], want: 0, about: 'onError during playback' },
  showfail: { steps: ['showfail'], want: 0, about: 'show() rejects' },
  hang: { steps: ['warp200000', 'wait', 'hold', 'next', 'quit_held'], want: 0, about: 'show() never resolves' },
  nocallback: { steps: ['start', 'warp31000', 'wait', 'x', 'hold', 'next', 'end_held'], want: 0, about: 'starts, never calls back, player presses X' },
  normal: { steps: ['start', 'end'], want: 1, about: 'normal full watch' },
};

let task, page;
try {
  task = await taskSpace(C.space || 'tiktok-ad-regression');
  page = task.page('p1');
} catch (e) {
  out.fatal = 'browser unavailable: ' + String(e && e.message || e).slice(0, 300);
  save(); console.log('AD_REGRESSION_DONE'); throw e;
}
const ev = (fn, a) => (a === undefined ? page.evaluate(fn) : page.evaluate(fn, a));

const install = () => ev((A) => {
  if (!window.__adq) {
    window.__adq = { grants: 0 };
    window.__adq.req = new Function('grant', A.request);
    window.__adq.st = A.state ? new Function(A.state) : null;
    window.__adq.ready = A.ready ? new Function(A.ready) : function () { return !!(window.cc && cc.director && cc.director.getScene && cc.director.getScene()); };
  }
  try { return !!window.__adq.ready(); } catch (e) { return false; }
}, A);

const state = () => ev(() => {
  let game = null;
  try { game = window.__adq.st ? window.__adq.st() : null; } catch (e) { game = { stateError: String(e && e.message || e).slice(0, 200) }; }
  return { grants: window.__adq.grants, shown: window.__adStats.shown, hostPending: window.__adPendingListeners(),
    music: window.__musicState(), game: game };
});

const request = () => ev(() => {
  window.__setAdPolicy('manual'); window.__adCtl = null;
  try { window.__adq.req(function () { window.__adq.grants++; }); return { ok: true }; }
  catch (e) { return { ok: false, error: String(e && e.message || e).slice(0, 200) }; }
});

const step = (code) => ev((code) => {
  const c = window.__adCtl, h = window.__adHeld;
  if (code === 'start') c && c.start();
  else if (code === 'end') c && c.close(true);
  else if (code === 'quit') c && c.close(false);
  else if (code === 'err') c && c.error();
  else if (code === 'showfail') c && c.rejectShow();
  else if (code === 'hold') window.__adHeld = c;
  else if (code === 'start_held') h && h.start();
  else if (code === 'end_held') h && h.close(true);
  else if (code === 'quit_held') h && h.close(false);
  else if (code === 'hide') __simHide();
  else if (code === 'show') __simShow();
  else if (code.startsWith('warp')) __warp(+code.slice(4));
  return !!(code.endsWith('_held') ? h : c);
}, code);

// The exit control, tapped with real pointer input at its on-screen position, never by
// calling game code. Default: an active cc.Label whose text matches exit_label. A game that
// draws its X without a label names it with adapter.exit: page JavaScript returning a cc.Node,
// or {node, x, y} (a point in that node's anchor space), or null while no X is shown.
const findExit = () => ev((A) => {
  const canvas = cc.game && cc.game.canvas, rect = canvas.getBoundingClientRect();
  const v2api = !!(cc.Camera && cc.Camera.findCamera); // Cocos Creator 2.x; otherwise 3.x
  const toWorld = (n, x, y) => v2api ? n.convertToWorldSpaceAR(cc.v2(x, y))
    : (n.getComponent(cc.UITransform) || n.getComponent('cc.UITransform')).convertToWorldSpaceAR(new cc.Vec3(x, y, 0));
  const toCss = (n, w) => {
    let p;
    if (v2api) p = cc.Camera.findCamera(n).getWorldToScreenPoint(w);
    else {
      let cam = null;
      for (let parent = n; parent && !cam; parent = parent.parent) {
        const cv = parent.getComponent && parent.getComponent(cc.Canvas);
        if (cv && cv.cameraComponent) cam = cv.cameraComponent;
      }
      if (!cam) throw new Error('Exit control has no owning Canvas camera');
      p = new cc.Vec3(); cam.worldToScreen(w, p);
    }
    // css-point:begin (v7.7.4, 总表 A5) Cocos 2.x getWorldToScreenPoint works in cc.visibleRect units, not canvas
    // pixels: dividing by canvas.width put the X off screen at DPR 2 (MusicSlice v31, 回家快跑, Meteor Blaster r3).
    const vis = (v2api && cc.visibleRect) ? { w: cc.visibleRect.width, h: cc.visibleRect.height } : { w: canvas.width, h: canvas.height };
    return { x: rect.left + p.x * rect.width / vis.w, y: rect.top + rect.height - p.y * rect.height / vis.h };
    // css-point:end
  };
  const targets = [];
  if (A.exit) {
    const r = new Function(A.exit)();
    if (r && r.node && typeof r.x === 'number') targets.push([r.node, r.x, r.y]);
    else if (r) targets.push([r, 0, 0]);
  } else {
    const rx = new RegExp(A.exit_label || '^\\s*(X|×|✕|✖|CLOSE|Close|close)\\s*$');
    const walk = (n) => {
      if (!n || n.activeInHierarchy === false) return;
      const l = n.getComponent && n.getComponent(cc.Label);
      if (l && typeof l.string === 'string' && rx.test(l.string)) targets.push([n, 0, 0]);
      (n.children || []).forEach(walk);
    };
    walk(cc.director.getScene());
  }
  return targets.map(([n, x, y]) => { try { return toCss(n, toWorld(n, x, y)); } catch (e) { return { error: String(e.message || e) }; } });
}, A);

async function tap(x, y) {
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
    await page.cdp('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1 });
    if (type === 'mousePressed') await sleep(60);
  }
}

// Lock probe: a fresh request right now must start (show() called) and pay one reward.
async function nextAd() {
  const s0 = await state();
  const r = await request(); await sleep(500);
  const s1 = await state();
  const started = r.ok && s1.shown === s0.shown + 1;
  if (started) { await step('start'); await sleep(500); await step('end'); await sleep(800); }
  const s2 = await state();
  return { started, rewarded: s2.grants === s0.grants + 1, message: s1.game && s1.game.message, requestError: r.error };
}

function musicOk(before, after) {
  // Every looped track the game had playing before the request must be playing again.
  const want = before.music.filter(m => m.playing).map(m => m.src);
  const now = after.music.filter(m => m.playing).map(m => m.src);
  const hostObserved = want.length > 0;
  const hostOk = want.every(s => now.includes(s));
  const g = after.game || {};
  const gameObserved = g.music_paused !== undefined;
  const gameOk = !g.music_paused;
  if (!hostObserved && !gameObserved) return { ok: !!A.no_music, observed: false };
  return { ok: (!hostObserved || hostOk) && (!gameObserved || gameOk), observed: true, host: hostObserved ? hostOk : 'not_observed', game: gameObserved ? g.music_paused || '' : 'not_reported' };
}

function quiet(st) {
  const g = st.game || {};
  return { hostPending: st.hostPending, gamePending: !!g.pending, locked: !!g.locked };
}

// D7 item 9 (Germ2048), a SEPARATE check that never changes a case verdict (v7.5: warning only):
// BGM and SFX must be silent while the video plays and come back after every outcome. The v7.4
// "music not resumed" problem above stays the hard check for looped BGM.
const audioSnap = () => ev(() => (window.__audioSnapshot ? window.__audioSnapshot() : null)).catch(() => null);
const TERMINAL = new Set(['end', 'quit', 'err', 'x', 'end_held', 'quit_held']);
function audioVerdict(before, during, lateDuring, after) {
  const w = [];
  if (!before || !after) return { observed: false, warnings: ['audio snapshot unavailable (old host)'] };
  for (const [when, s] of [['video start', during], ['before the outcome', lateDuring]]) {
    if (!s) continue;
    if (s.bgm.length) w.push('BGM still playing during the ad (' + when + '): ' + s.bgm.join(', '));
    if (s.sfxLive) w.push('SFX still playing during the ad (' + when + '): ' + s.sfxLive);
    if (s.engine && before.engine && before.engine.music > 0 && s.engine.music > 0 && s.bgm.length) w.push('engine music volume not lowered during the ad');
  }
  if (during && lateDuring && lateDuring.sfxPlays > during.sfxPlays) w.push('SFX played during the ad: ' + (lateDuring.sfxPlays - during.sfxPlays));
  if (after.sfxPaused > before.sfxPaused) w.push('SFX paused for the ad and not resumed: ' + (after.sfxPaused - before.sfxPaused));
  if (before.engine && after.engine) {
    if (after.engine.effects !== before.engine.effects) w.push('effects volume ' + before.engine.effects + ' -> ' + after.engine.effects + ' after the ad');
    if (after.engine.music !== before.engine.music) w.push('music volume ' + before.engine.music + ' -> ' + after.engine.music + ' after the ad');
  }
  const missing = before.bgm.filter(s => !after.bgm.includes(s));
  if (missing.length) w.push('BGM not audible after the ad: ' + missing.join(', '));
  return { observed: !!(before.bgm.length || before.sfxPlays || before.engine), warnings: w };
}

try {
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await page.cdp('Emulation.setTouchEmulationEnabled', { enabled: false });
  await page.goto(C.url);
  const t0 = Date.now(); let ready = false;
  while (Date.now() - t0 < (C.bootTimeoutMs || 60000)) {
    try { ready = await install(); } catch (e) { ready = false; }
    if (ready) break;
    await sleep(500);
  }
  const errs = await ev(() => (window.__hostLog || []).filter(r => /^(error|rejection|boot-throw)$/.test(r.kind)).slice(0, 5));
  out.boot = { ready, ms: Date.now() - t0, errors: errs };
  if (!ready) throw new Error('game did not become ready for ad requests within ' + (C.bootTimeoutMs || 60000) + ' ms');
  await sleep(C.settleMs || 2000);

  for (const k of (C.cases || Object.keys(PLAN))) {
    const plan = PLAN[k];
    if (!plan) { out.cases.push({ case: k, ok: false, problems: ['unknown case'] }); continue; }
    const before = await state();
    const aBefore = await audioSnap();
    let aDuring = null, aLate = null;
    const r = await request(); await sleep(500);
    const afterRequest = await state();
    const row = { case: k, about: plan.about, want: plan.want, opened: r.ok && afterRequest.shown === before.shown + 1, problems: [] };
    if (!r.ok) row.problems.push('adapter request threw: ' + r.error);
    let nextGrants = 0;
    for (const s of plan.steps) {
      if (TERMINAL.has(s) && aDuring && !aLate) aLate = await audioSnap();
      if (s === 'wait') { await sleep(1500); continue; }
      if (s === 'x') {
        const xs = await findExit();
        row.exitTargets = xs.slice(0, 3);
        row.exitShown = xs.some(p => p && typeof p.x === 'number');
        if (row.exitShown) { const p = xs.find(p => typeof p.x === 'number'); await tap(p.x, p.y); }
        else row.problems.push('no exit (X) on screen 30 s after playback started without a callback');
        await sleep(900);
        continue;
      }
      if (s === 'next') {
        const st = await state();
        row.afterExit = quiet(st);
        const m = musicOk(before, st);
        if (st.hostPending) row.problems.push('old ad callbacks still bound after timeout/X');
        if (row.afterExit.gamePending || row.afterExit.locked) row.problems.push('game still reports a pending/locked ad after timeout/X');
        if (!m.ok) row.problems.push('music not resumed after timeout/X');
        const n = await nextAd();
        row.immediateNext = n;
        if (n.started && n.rewarded) nextGrants++;
        else row.problems.push('immediate next ad failed (' + (n.started ? 'no reward' : 'did not start') + (n.message ? ': ' + n.message : '') + ')');
        continue;
      }
      await step(s); await sleep(s.startsWith('warp') ? 1500 : 700);
      // Only the case's own live video; a late video after the timeout (start_held) is already orphaned.
      if (s === 'start' && !aDuring) aDuring = await audioSnap();
    }
    await sleep(700);
    const end = await state();
    row.audio = audioVerdict(aBefore, aDuring, aLate, await audioSnap());
    for (const w of row.audio.warnings) out.warnings.push(k + ': ' + w);
    row.granted = end.grants - before.grants - nextGrants;
    row.end = quiet(end);
    row.message = end.game && end.game.message;
    row.music = musicOk(before, end);
    if (!row.opened) row.problems.push('the ad request did not call show()');
    if (row.granted !== plan.want) row.problems.push('reward count ' + row.granted + ', expected ' + plan.want);
    if (end.hostPending) row.problems.push('an ad that never finished still has callbacks bound');
    if (row.end.gamePending) row.problems.push('game reports a pending ad');
    if (row.end.locked) row.problems.push('game reports an ad lock');
    if (!row.music.ok) row.problems.push(row.music.observed ? 'music not resumed' : 'music state not observable (no looped audio playing and adapter reports none)');
    const n = await nextAd();
    row.nextAd = n;
    if (!(n.started && n.rewarded)) row.problems.push('next ad request failed (' + (n.started ? 'no reward' : 'did not start') + (n.message ? ': ' + n.message : '') + ')');
    row.ok = row.problems.length === 0;
    out.cases.push(row);
    console.log(JSON.stringify(row));
    save();
  }
} catch (e) {
  out.fatal = String(e && e.message || e).slice(0, 500);
} finally {
  save();
  try { await page.goto('about:blank'); } catch (_) {}
  try { await task.finish({ keep: [] }); } catch (_) {}
  console.log('AD_REGRESSION_DONE');
}
