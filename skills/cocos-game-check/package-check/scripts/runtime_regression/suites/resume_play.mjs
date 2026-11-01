// resume_play (v7.9, 手机才出的五类问题 1): in the middle of a level the phone takes the game away and gives it back; the
// level must still play. 甜点消消乐 R39-R47 (six fix rounds): after Resume the timer stood still and every tap only played
// the button click - the pause popup had copied back the "paused" flag it saved while an ad wait had the round stopped.
// Desktop checks never saw it: a browser tab is never sent to the background by a rewarded video, a mouse never leaves a
// finger on the glass. Cases, each on a fresh load (empty save, iPhone 14), after adapter.resume_play.start reached a
// level that plays (checked first: the clock moves, one real probe changes state_js):
//   background             tt.onHide, 3 s, tt.onShow (lock screen, Control Center, a call)
//   finger_held            a finger is down on the board when the phone takes the game (no touchend / touchcancel ever)
//   pause_background       the game's own pause popup is open, onHide, onShow   (adapter pause_button)
//   ad_background          an in-level rewarded ad plays as on a phone: onHide when it starts, onShow 50 ms before its
//                          onClose when it ends (host adhide=1)                  (adapter ad)
//   ad_background_close_first   the same with onClose 50 ms before onShow (TikTok does not document the order)
// Then: a pause popup (adapter continue_button) is closed with ONE real tap (needing a second tap = the first tap after
// returning was lost: fails), the clock must move again (clock_js) and one real probe must change state_js.
// New game: refuses; legacy game: warnings. A run below 20 fps is invalid and always refused.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const B = A.resume_play || {};
const KEYS = new Set(['start', 'probe', 'state_js', 'clock_js', 'pause_button', 'continue_button', 'ad', 'settle_ms', 'background_ms', 'query', 'note', 'cases']);

function problems(b) {
  const out = [];
  if (!b || typeof b !== 'object') return ['resume_play must be an object'];
  for (const k of Object.keys(b)) if (!KEYS.has(k)) out.push('resume_play has unknown key ' + JSON.stringify(k));
  if (!Array.isArray(b.start) || !b.start.length) out.push('resume_play.start must list the real steps from home into a level that plays');
  const pr = b.probe;
  if (!pr || typeof pr !== 'object' || !(pr.tap || pr.tap_js || pr.drag_js)) out.push('resume_play.probe must be {"tap": path} or {"tap_js": "...return node"} or {"drag_js": "...return [a, b]"}: one real gameplay operation');
  if (typeof b.state_js !== 'string' || !b.state_js.trim()) out.push('resume_play.state_js must return what the probe changes (pieces left, tray, score ...)');
  for (const k of ['clock_js', 'pause_button', 'continue_button', 'query', 'note']) if (k in b && typeof b[k] !== 'string') out.push('resume_play.' + k + ' must be a string');
  if ('cases' in b && !(Array.isArray(b.cases) && b.cases.every((x) => typeof x === 'string'))) out.push('resume_play.cases must be a list of case ids');
  if (b.pause_button && !b.continue_button) out.push('resume_play.pause_button needs continue_button (the button that closes the pause popup)');
  if ('ad' in b && !(b.ad && typeof b.ad === 'object' && (b.ad.tap || b.ad.tap_js) && (!b.ad.actions || Array.isArray(b.ad.actions)))) out.push('resume_play.ad must be {"actions": [steps to make the entry show an ad], "tap": path | "tap_js": ...}');
  return out;
}

const safe = (s) => String(s).replace(/[^\w.-]+/g, '_').slice(0, 60);

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'resume_play', policy: POLICY, cases: [] };
  const bad = problems(B);
  if (bad.length) { out.add('adapter', POLICY === 'legacy', bad.join('; ')); if (POLICY === 'legacy') out.warn('resume_play adapter: ' + bad.join('; ') + ' [legacy game: warning]'); return; }
  // finger_held: the stale finger has id 0, the id the next finger gets again on a phone that numbers fingers from 0
  // (the host's mouse taps are id 0 too); finger_held_new_id: the next finger gets a new id
  let cases = [{ id: 'background' }, { id: 'finger_held', touchId: 0 }, { id: 'finger_held_new_id', touchId: 7 }];
  if (B.pause_button) cases.push({ id: 'pause_background' });
  if (B.ad) cases.push({ id: 'ad_background', order: 'show-first' }, { id: 'ad_background_close_first', order: 'close-first' });
  else out.warn('resume_play: no in-level ad entry given (resume_play.ad) - the case "a rewarded ad sends the game to the background" did not run');
  if (!B.pause_button) out.warn('resume_play: no pause_button given - the case "pause popup open while the phone takes the game" did not run');
  if (Array.isArray(B.cases) && B.cases.length) { cases = cases.filter((c) => B.cases.includes(c.id)); out.warn('resume_play: only the cases ' + B.cases.join(', ') + ' ran (resume_play.cases is for diagnosis; leave it out for a package)'); }
  const engine = C.engine || '2.x';
  // Speed (Saul: checks as short as possible without missing anything): the lifecycle cases run one after the other in
  // the same level while they pass; the two ad cases (they use the item up) and any retry start from a fresh load. A case
  // that fails in the shared level is run once more on a fresh load and only that result counts.
  let live = false;
  async function fresh(c, cs) {
    const q = 'capsule=pt&ad=complete&adhide=1&adms=1500' + (cs.order === 'close-first' ? '&adhideorder=close-first' : '') + (B.query ? '&' + B.query : '');
    await G.openGame(page, 'iphone14', q);
    const home = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
    if (!home.ok) return home.fps != null && home.fps < G.MIN_FPS ? 'invalid run: the page ran at ' + home.fps + ' fps, re-run with the Ego window visible' : 'untestable: home not reached';
    if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
    const r = await P.steps(page, B.start);
    c.start = r.log.slice(-6);
    if (!r.ok) return 'untestable: resume_play.start did not reach the level: ' + r.why;
    await P.sleep(B.settle_ms || 1500);
    const base = await P.playable(page, B);
    c.before = base;
    if (!base.ok) return 'untestable: the level does not play even before the phone event (' + base.why + '); fix resume_play.start / probe / state_js / clock_js';
    return null;
  }
  async function event(c, cs) {
    const idx = await P.hostIdx(page);
    const bg = B.background_ms || 3000;
    let fail = null, warn = null;
    if (cs.id === 'background') {
      await P.hide(page); await P.sleep(bg); await P.show(page);
    } else if (cs.touchId !== undefined) {
      const p = await P.point(page, B.probe.tap || B.probe.tap_js ? B.probe : null) || { x: 195, y: 422 };
      const held = await P.touchHold(page, p.x, p.y, cs.touchId);
      if (!held) warn = 'finger_held not covered on this host (Cocos ' + (C.engine || '2.x') + ' host takes pointer events, not DOM touches)';
      // Cocos 2.4 drops a touch older than 5 s at the next touchstart (inputManager TOUCH_TIMEOUT): a short trip to
      // Control Center is the case that loses the next tap, so the game is gone 1.5 s here
      await P.sleep(150); await P.hide(page); await P.sleep(Math.min(bg, 1500)); await P.show(page);
      c.finger = held ? [Math.round(p.x), Math.round(p.y), cs.touchId] : null;
    } else if (cs.id === 'pause_background') {
      const p = await G.nodeCentre(page, B.pause_button).catch(() => null);
      if (!p) fail = 'untestable: pause_button ' + B.pause_button + ' not on screen in the level';
      else { await G.click(page, p.x, p.y); await P.sleep(1000); await P.hide(page); await P.sleep(bg); await P.show(page); }
    } else {
      if (B.ad.actions) { const r = await P.steps(page, B.ad.actions); if (!r.ok) fail = 'untestable: resume_play.ad.actions: ' + r.why; }
      if (!fail) {
        const p = await P.point(page, B.ad);
        if (!p) fail = 'untestable: the in-level ad entry is not on screen';
        else {
          await G.click(page, p.x, p.y);
          let seen = null; const t0 = Date.now();
          while (Date.now() - t0 < 9000) {
            await P.sleep(400);
            const rows = await P.hostSince(page, idx);
            const shown = rows.some((r) => r.kind === 'ad-show'), ended = rows.some((r) => r.kind === 'ad-result'), back = rows.filter((r) => r.kind === 'lifecycle').map((r) => r.data);
            seen = { shown, ended, lifecycle: back };
            if (!shown && Date.now() - t0 > 3000) break;
            if (ended && back.includes('show')) break;
          }
          c.ad = seen;
          if (!seen || !seen.shown) fail = 'untestable: tapping the in-level ad entry did not start a rewarded ad (resume_play.ad must make it show one, e.g. use the item up first)';
        }
      }
    }
    c.lifecycle = (await P.hostSince(page, idx)).filter((r) => r.kind === 'lifecycle').map((r) => r.data);
    return { fail, warn };
  }
  async function back(c, cs) {
    await P.sleep(1500);
    c.back_png = await G.shot(page, path.join(C.evidenceDir, 'resume-' + safe(cs.id) + '-back.png'));
    const k = await P.tapContinue(page, B.continue_button, 2);
    c.continue_taps = k.taps;
    if (k.still) return 'after ' + cs.id + ': the pause popup did not close with 2 real taps on ' + B.continue_button;
    if (k.taps > 1) return 'after ' + cs.id + ': the pause popup needed ' + k.taps + ' taps on ' + B.continue_button + ' (the first tap after returning was lost; 甜点消消乐 R47)';
    await P.sleep(800);
    const after = await P.playable(page, B);
    c.after = after;
    c.after_png = await G.shot(page, path.join(C.evidenceDir, 'resume-' + safe(cs.id) + '-after.png'));
    if (!after.ok) return 'after ' + cs.id + ': ' + after.why + (B.continue_button ? '' : ' (if the game shows a pause popup after returning, give resume_play.continue_button)');
    return null;
  }
  async function attempt(cs, reuse) {
    const c = { id: cs.id, reused_level: reuse };
    let fail = reuse ? null : await fresh(c, cs);
    let warn = null;
    if (!fail) { const e = await event(c, cs); fail = e.fail; warn = e.warn; }
    if (!fail) fail = await back(c, cs);
    return { c, fail, warn };
  }
  for (const cs of cases) {
    const shareable = !cs.order;            // ad cases use the item up: always a fresh load
    let r = await attempt(cs, live && shareable);
    if (r.fail && r.c.reused_level && !/^invalid run/.test(r.fail)) { r.c.first_try = r.fail; rep.cases.push(r.c); r = await attempt(cs, false); }
    const { c, fail, warn } = r;
    rep.cases.push(c);
    live = !fail && shareable;
    if (warn) { out.warn('resume_play ' + cs.id + ': ' + warn); if (!fail && cs.touchId !== undefined) { out.add(cs.id, true, warn); continue; } }
    c.result = fail ? 'fail' : 'pass';
    const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
    if (fail && !blocks) out.warn('resume_play ' + cs.id + ': ' + fail + ' [legacy game: warning]');
    out.add(cs.id, !blocks, fail || ('plays after ' + cs.id + (c.continue_taps ? ' (pause popup closed with 1 tap)' : '') + (c.reused_level ? ', same level as the case before' : '')));
  }
  out.evidence.report = L.evidence('resume_play.json', rep);
}, { w: 390, h: 844 });
