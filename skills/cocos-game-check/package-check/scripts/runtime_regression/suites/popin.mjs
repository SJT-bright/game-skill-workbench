// popin (v7.8, 总表 P2 补): obstacles may not appear, vanish or jump while the player can see them.
// From the BreezyBalloon prototype 热气球/_skill反馈_障碍生成/popin_gate.mjs (2026-10-30); the 潜艇冲冲 node names it
// hard-coded (submarineItem, LevelView, HomeView) are adapter fields now (adapter.popin, references/runtime-regression.md).
// Per screen 390x844, 375x667, 768x1024, 1115x791 (CSS px, deviceScaleFactor 2, fresh save): home (adapter.home), start a
// run (popin.start real actions, else a real tap on adapter.play), wait for popin.game_node, make the player invincible
// (popin.invincible_js), first touch, fly popin.fly_s (18 s), call the revive path (popin.revive_js), watch 4 s more.
// Every drawn frame (EVENT_AFTER_DRAW), every node with a collider (cc.PhysicsCollider / cc.Collider) that draws something
// (a render component on it or below it), except the player and its children, popin.ignore / popin.ignore_groups:
//   appeared_on_screen  not shown (or opacity < 5 %) the frame before, shown (>= 25 %) inside the visible area now
//   vanished_on_screen  shown (>= 25 %) inside the visible area, gone / inactive / opacity < 5 % the next frame
//   jumped_on_screen    moved > 40 world units in one frame (x the frame time / 16.7 ms) while inside the area before or after
// Fades are allowed (a 0.3 s fade never steps from >= 25 % to < 5 %). An event under a full-screen opaque cover
// (opacity >= 98 %, drawn after the obstacle) is not counted. Visible area = the engine's real visible rect, through the
// node's camera (2.4 cc.Camera.findCamera(n).getWorldToScreenPoint: visibleRect units; wide screens and letterbox bars
// follow cc.view). No obstacle seen at all = the adapter is wrong (fails). Page < 20 fps = invalid_run (re-run).
// New game blocks, legacy game (CFG.policy) warns. Cocos 3.x: not covered (the runner warns, popin.json "uncovered");
// adapter.popin = {"n/a": "reason"} (no scrolling obstacles): the runner passes it without a browser.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A, P = A.popin || {};
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
export const SCREENS = [[390, 844], [375, 667], [768, 1024], [1115, 791]];
const FLY_S = +P.fly_s || 18, AFTER_S = 4;
const KINDS = ['appeared_on_screen', 'vanished_on_screen', 'jumped_on_screen'];

const { WATCH_JS } = await import(new URL('popin_watch.mjs', globalThis.CFG.lib).href);

const SNAP = '(function(){var W=window.__popin;if(!W)return null;return {visible:W.V,camera:W.camera,frames:W.frames,watched:W.watched,counts:W.counts,covered:W.covered,hitches:W.hitches,seconds:(performance.now()-W.t0)/1000,examples:W.ev.slice(0,6),events:W.ev.length}})()';

async function oneScreen(page, w, h, rep) {
  const key = w + 'x' + h, row = { viewport: key };
  rep.screens.push(row);
  const fail = (code, msg) => { row.setup = code; rep.findings.push({ code, screen: key, msg: key + ': ' + msg }); return row; };
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 2, mobile: true });
  await page.cdp('Emulation.setTouchEmulationEnabled', { enabled: false });
  await G.sleep(200);
  await page.goto(L.url('reset=1&ad=complete' + (P.query ? '&' + P.query : '') + '&r=' + Date.now()));
  await L.keepFrames(page);
  const home = A.home ? await L.waitFor(page, A.home, C.bootTimeoutMs || 60000) : await G.waitHome(page, { homeScene: A.home_scene || null });
  row.homeMs = home.ms;
  if (!home.ok) return fail('home', 'home screen not reached in ' + Math.round(home.ms / 1000) + ' s');
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await G.sleep(400); }
  await G.sleep(1500);
  if (Array.isArray(P.start) && P.start.length) {
    const r = await G.runActions(page, P.start);
    row.start = r.log;
    if (!r.ok) return fail('start', 'run not started: ' + r.why);
  } else if (A.play) {
    const p = await L.locate(page, A.play);
    if (!p) return fail('start', 'adapter.play gave no point on the home screen');
    await L.tap(page, p.x, p.y);
    row.start = { tap: [Math.round(p.x), Math.round(p.y)] };
  } else return fail('start', 'no way to start a run: give popin.start (real actions) or adapter.play');
  const gameJs = 'var n = findNode(' + JSON.stringify(String(P.game_node)) + '); return !!(n && n.activeInHierarchy);';
  let inGame = false;
  for (let i = 0; i < 60 && !inGame; i++) { await G.sleep(250); inGame = (await G.evalJs(page, gameJs).catch(() => false)) === true; }
  if (!inGame) return fail('game_node', 'popin.game_node ' + P.game_node + ' not active 15 s after the start');
  await G.sleep(+P.settle_ms || 2500);
  if (P.after_start_js) row.afterStart = await G.evalJs(page, P.after_start_js).catch((e) => 'threw: ' + e);
  const inv = await L.adapterCall(page, P.invincible_js).catch((e) => ({ adapterError: String(e) }));
  if (!inv || (inv && inv.adapterError)) return fail('invincible', 'popin.invincible_js did not return true: ' + JSON.stringify(inv).slice(0, 200));
  row.watch = await page.evaluate(WATCH_JS + '(' + JSON.stringify({ player: P.player, ignore: P.ignore || null, ignore_groups: P.ignore_groups || [] }) + ')');
  if (!row.watch || !row.watch.player) rep.warnings.push(key + ': player node ' + P.player + ' not found when the watch started (its children are not left out)');
  if (P.first_touch !== false) {
    const c = await page.evaluate(() => { const r = window.cc.game.canvas.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
    await page.cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y, button: 'left', buttons: 0 });
    await page.cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x: c.x, y: c.y, button: 'left', buttons: 1, clickCount: 1 });
    for (let i = 1; i <= 6; i++) { await page.cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y - i * 4, button: 'left', buttons: 1 }); await G.sleep(30); }
    await page.cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x: c.x, y: c.y - 24, button: 'left', buttons: 0, clickCount: 1 });
  }
  for (let t = 0; t < FLY_S; t += 3) await G.sleep(Math.min(3, FLY_S - t) * 1000);
  row.flight = await page.evaluate(SNAP);
  await page.evaluate(() => { if (window.__popin) window.__popin.phase = 'revive'; });
  const rv = await L.adapterCall(page, P.revive_js).catch((e) => ({ adapterError: String(e) }));
  if (rv && rv.adapterError) return fail('revive', 'popin.revive_js threw: ' + rv.adapterError);
  row.revive = rv;
  await G.sleep(AFTER_S * 1000);
  const s = await page.evaluate(SNAP);
  await page.evaluate(() => { const W = window.__popin; if (W && W.fn) window.cc.director.off(window.cc.Director.EVENT_AFTER_DRAW, W.fn); }).catch(() => {});
  Object.assign(row, s || {});
  row.fps = s && s.seconds ? Math.round(s.frames / s.seconds) : null;
  row.png = await G.shot(page, path.join(C.evidenceDir, 'popin-' + key + '.png')).catch(() => null);
  if (!s) return fail('watch', 'the frame watcher did not run');
  if (row.fps != null && row.fps < G.MIN_FPS) rep.findings.push({ code: 'invalid_run', screen: key, msg: key + ': the page ran at ' + row.fps + ' fps (< ' + G.MIN_FPS + '); the Ego tab was throttled, re-run with its window visible' });
  if (!s.watched) rep.findings.push({ code: 'obstacles_seen', screen: key, msg: key + ': no obstacle with a collider was drawn in ' + Math.round(s.seconds) + ' s (wrong popin.player / game_node, the run never started, or the game has no scrolling obstacles: write popin {"n/a": "why"})' });
  for (const kind of KINDS) {
    const n = Object.entries(s.counts || {}).filter(([k]) => k.endsWith(':' + kind)).reduce((a, [, v]) => a + v, 0);
    if (!n) continue;
    const by = Object.entries(s.counts).filter(([k]) => k.endsWith(':' + kind)).map(([k, v]) => k.split(':')[0] + ' ' + v).join(', ');
    const ex = (s.examples || []).filter((e) => e.kind === kind).slice(0, 2).map((e) => e.path + (e.from ? ' ' + JSON.stringify(e.from) + '->' + JSON.stringify(e.to) : ' at ' + JSON.stringify(e.at))).join('; ');
    rep.findings.push({ code: kind, screen: key, msg: key + ': ' + n + ' x ' + kind + ' (' + by + '; visible area ' + JSON.stringify(s.visible) + ') e.g. ' + ex });
  }
  return row;
}

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'popin', policy: POLICY, adapter: P, screens: [], findings: [], warnings: [] };
  for (const [w, h] of SCREENS) await oneScreen(page, w, h, rep);
  for (const m of rep.warnings) out.warn('popin: ' + m);
  const codes = ['setup', 'obstacles_seen'].concat(KINDS, ['invalid_run']);
  const setupCodes = new Set(['home', 'start', 'game_node', 'invincible', 'revive', 'watch']);
  for (const code of codes) {
    const fs2 = rep.findings.filter((f) => (code === 'setup' ? setupCodes.has(f.code) : f.code === code));
    if (code === 'invalid_run' && !fs2.length) continue;
    const block = code === 'invalid_run' || POLICY !== 'legacy';
    if (fs2.length && !block) for (const f of fs2) out.warn('popin ' + f.code + ': ' + f.msg + ' [legacy game: warning]');
    out.add(code, !fs2.length || !block, fs2.length ? fs2.map((f) => f.msg).slice(0, 6) : rep.screens.map((r) => r.viewport + ' ' + (r.frames || 0) + ' frames, ' + (r.watched || 0) + ' watched'));
  }
  out.evidence.report = L.evidence('popin.json', rep);
  out.evidence.screens = rep.screens.map((r) => ({ viewport: r.viewport, frames: r.frames, fps: r.fps, watched: r.watched, counts: r.counts, setup: r.setup || null }));
}, { w: 390, h: 844 });
