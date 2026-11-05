// resume_play (v7.9, 手机才出的五类问题 1): in the middle of a level the phone takes the game away and gives it back; the
// level must still play. 甜点消消乐 R39-R47 (six fix rounds): after Resume the timer stood still and every tap only played
// the button click - the pause popup had copied back the "paused" flag it saved while an ad wait had the round stopped.
// Desktop checks never saw it: a browser tab is never sent to the background by a rewarded video, a mouse never leaves a
// finger on the glass. Cases, each after adapter.resume_play.start reached a level that plays (checked first: the clock
// moves, one real probe changes state_js):
//   background             tt.onHide, 3 s, tt.onShow (lock screen, Control Center, a call)
//   finger_held            a finger is down on the board when the phone takes the game and never lifts; the next finger
//                          gets the same touch id (2.x host: a real mouse press without release, the host's touch id 0;
//                          3.x host: holdTouch with the mouse pointer id). 甜点消消乐 R47 lost the first tap after it.
//   finger_held_new_id     the same, the next finger gets a new id
//   pause_background       the game's own pause popup is open, onHide, onShow
//   ad_background          an in-level rewarded ad plays as on a phone: onHide when it starts, onShow 50 ms before its
//                          onClose when it ends (host adhide=1)
//   ad_background_close_first   the same with onClose 50 ms before onShow (TikTok does not document the order)
// Then: a pause popup is closed with ONE real tap (needing a second tap = the first tap after returning was lost: fails),
// the clock must move again (clock_js) and one real probe must change state_js.
// v7.9 (手机检查补全, Saul 11-04「全部补上」):割草 v011-v015 and 人鱼 v14 left pause_button and ad out, and the two cases that
// caught 甜点消消乐 were skipped with a warning. Now nothing is skipped by leaving a field out:
//   pause control  resume_play.pause_button, else found in the level: a button whose popup (opened by button_sweep's
//                  real taps this run) has a continue / resume button, whatever its name (香肠 R17 resetBtn「重置」),
//                  else a button named / drawn pause, else settings / menu. Its popup's way back = continue_button, else
//                  that continue / resume button, else the close button that appeared. Not found and not declared
//                  {"none": "reason"}: a new game is refused (logic-rules.md: 关卡内暂停或设置键 → Continue/Restart/Home).
//   in-level ad    resume_play.ad, else an in-level ad entry button_sweep found with real taps this run (CFG.prior).
//                  None and not declared {"none": "reason"} while the package shows rewarded ads: a new game is refused.
// New game: refuses. Legacy game (Saul 11-04「老游戏先不管」): nothing is looked for, pause_button / ad as written, a
// missing one skips its case with a warning; failures only warn. A run below 20 fps is invalid and always refused.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
// legacy game (Saul 11-04「老游戏先不管」): nothing is looked for, the fields as written, a missing one skips its case
// with a warning (as before 手机检查补全)
const LEGACY = POLICY === 'legacy';
const B = A.resume_play || {};
const FACTS = C.facts || {};
const KEYS = new Set(['start', 'probe', 'state_js', 'clock_js', 'pause_button', 'continue_button', 'ad', 'settle_ms', 'background_ms', 'query', 'note', 'cases']);
const isNone = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && typeof v.none === 'string' && !!v.none.trim();

function problems(b) {
  const out = [];
  if (!b || typeof b !== 'object') return ['resume_play must be an object'];
  for (const k of Object.keys(b)) if (!KEYS.has(k)) out.push('resume_play has unknown key ' + JSON.stringify(k));
  if (!Array.isArray(b.start) || !b.start.length) out.push('resume_play.start must list the real steps from home into a level that plays');
  const pr = b.probe;
  if (!pr || typeof pr !== 'object' || !(pr.tap || pr.tap_js || pr.drag_js)) out.push('resume_play.probe must be {"tap": path} or {"tap_js": "...return node"} or {"drag_js": "...return [a, b]"}: one real gameplay operation');
  if (typeof b.state_js !== 'string' || !b.state_js.trim()) out.push('resume_play.state_js must return what the probe changes (pieces left, tray, score ...)');
  for (const k of ['clock_js', 'continue_button', 'query', 'note']) if (k in b && typeof b[k] !== 'string') out.push('resume_play.' + k + ' must be a string');
  if ('pause_button' in b && !(typeof b.pause_button === 'string' && b.pause_button) && !isNone(b.pause_button)) out.push('resume_play.pause_button must be a node path or {"none": "why the level has no pause / settings button"}');
  if ('ad' in b && !isNone(b.ad) && !(b.ad && typeof b.ad === 'object' && (b.ad.tap || b.ad.tap_js) && (!b.ad.actions || Array.isArray(b.ad.actions)))) out.push('resume_play.ad must be {"actions": [steps to make the entry show an ad], "tap": path | "tap_js": ...} or {"none": "why the level has no rewarded ad"}');
  if ('cases' in b && !(Array.isArray(b.cases) && b.cases.every((x) => typeof x === 'string'))) out.push('resume_play.cases must be a list of case ids');
  return out;
}

const safe = (s) => String(s).replace(/[^\w.-]+/g, '_').slice(0, 60);

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'resume_play', policy: POLICY, cases: [] };
  const bad = problems(B);
  if (bad.length) { out.add('adapter', POLICY === 'legacy', bad.join('; ')); if (POLICY === 'legacy') out.warn('resume_play adapter: ' + bad.join('; ') + ' [legacy game: warning]'); return; }

  // ---- where the pause control and the in-level ad are (adapter, else found) ----
  const prior = LEGACY ? null : await P.priorAdEntries();
  const inLevel = (prior || []).filter((e) => e.taps[0] === '<play>' && e.taps.length >= 2);
  let ad = null, adWhy = null;
  if (isNone(B.ad)) adWhy = 'declared none: ' + B.ad.none;
  else if (B.ad) ad = B.ad;
  else if (inLevel.length) { const t = inLevel[0].taps.slice(1); ad = { actions: t.slice(0, -1).map((p) => ({ tap: p, after: 1300 })), tap: t[t.length - 1], found: inLevel[0].taps.join(' > ') }; }
  rep.ad = ad ? { tap: ad.tap || 'tap_js', found: ad.found || null } : { none: adWhy };
  const disc = { pause: typeof B.pause_button === 'string' ? B.pause_button : null, cont: B.continue_button || null, none: isNone(B.pause_button) ? B.pause_button.none : null, done: LEGACY };

  let cases = [{ id: 'background' }, { id: 'finger_held', finger: 'same' }, { id: 'finger_held_new_id', finger: 'new' }, { id: 'pause_background' },
    { id: 'ad_background', order: 'show-first' }, { id: 'ad_background_close_first', order: 'close-first' }];
  if (Array.isArray(B.cases) && B.cases.length) { cases = cases.filter((c) => B.cases.includes(c.id)); out.warn('resume_play: only the cases ' + B.cases.join(', ') + ' ran (resume_play.cases is for diagnosis; leave it out for a package)'); }

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
    if (!disc.done) await discover(c);
    return null;
  }
  // once, in the first level that plays: find the pause control and its way back, close the popup again
  async function discover(c) {
    disc.done = true;
    if (!disc.pause && !disc.none) {
      const f = await P.findPause(page);
      if (f) { disc.pause = f.pause; disc.found = f.how; if (!disc.cont && f.cont) { disc.cont = f.cont; disc.contFound = true; } }
      else disc.popups = await P.priorLevelPopups();
    }
    if (!disc.pause) return;
    const o = await P.openPause(page, disc.pause);
    disc.opened = o.opened; disc.added = o.added;
    if (!disc.cont) { disc.cont = o.cont; disc.contFound = !!o.cont; }
    if (!o.opened) { disc.why = o.why || ('tapping ' + disc.pause + ' opened nothing'); return; }
    if (!disc.cont) { disc.why = 'tapping ' + disc.pause + ' opened a popup (' + o.added.join(', ') + ') with no continue / resume / close button found: write resume_play.continue_button'; return; }
    const k = await P.tapContinue(page, disc.cont, 2);
    if (k.still) disc.why = 'the pause popup did not close with 2 taps on ' + disc.cont;
    await P.sleep(800);
    c.discovery = { pause: disc.pause, found: !!disc.found, cont: disc.cont, contFound: !!disc.contFound, why: disc.why || null };
  }
  async function event(c, cs) {
    const idx = await P.hostIdx(page);
    const bg = B.background_ms || 3000;
    let fail = null, warn = null;
    if (cs.id === 'background') {
      await P.hide(page); await P.sleep(bg); await P.show(page);
    } else if (cs.finger) {
      const p = await P.point(page, B.probe.tap || B.probe.tap_js ? B.probe : null) || { x: 195, y: 422 };
      const how = cs.finger === 'same' ? await P.fingerHold(page, p.x, p.y) : await P.touchHold(page, p.x, p.y, 7);
      if (!how) warn = cs.id + ' not covered on this host (Cocos ' + (C.engine || '2.x') + ')';
      // Cocos 2.4 drops a touch older than 5 s at the next touchstart (inputManager TOUCH_TIMEOUT): a short trip to
      // Control Center is the case that loses the next tap, so the game is gone 1.5 s here
      await P.sleep(150); await P.hide(page); await P.sleep(Math.min(bg, 1500)); await P.show(page);
      c.finger = how ? [Math.round(p.x), Math.round(p.y), how] : null;
    } else if (cs.id === 'pause_background') {
      const p = await G.nodeCentre(page, disc.pause).catch(() => null);
      if (!p) fail = 'untestable: pause control ' + disc.pause + ' not on screen in the level';
      else { await G.click(page, p.x, p.y); await P.sleep(1000); await P.hide(page); await P.sleep(bg); await P.show(page); }
    } else {
      if (ad.actions && ad.actions.length) { const r = await P.steps(page, ad.actions); if (!r.ok) fail = 'untestable: the steps to the in-level ad entry: ' + r.why; }
      if (!fail) {
        let seen = null;
        // an item may give free uses first (甜点消消乐 restart: 2 free): tap it until it starts an ad, at most 3 times
        for (let k = 0; k < 3 && !(seen && seen.shown) && !fail; k++) {
          const p = await P.point(page, ad.tap ? ad.tap : ad);
          if (!p) { fail = 'untestable: the in-level ad entry ' + (ad.tap || 'tap_js') + ' is not on screen' + (ad.found ? ' (button_sweep found it as ' + ad.found + ')' : ''); break; }
          await G.click(page, p.x, p.y);
          const t0 = Date.now();
          while (Date.now() - t0 < 9000) {
            await P.sleep(400);
            const rows = await P.hostSince(page, idx);
            const shown = rows.some((r) => r.kind === 'ad-show'), ended = rows.some((r) => r.kind === 'ad-result'), back = rows.filter((r) => r.kind === 'lifecycle').map((r) => r.data);
            seen = { shown, ended, lifecycle: back, taps: k + 1 };
            if (!shown && Date.now() - t0 > 2500) break;
            if (ended && back.includes('show')) break;
          }
          if (!seen.shown) await P.sleep(1500);
        }
        c.ad = seen;
        if (!fail && (!seen || !seen.shown)) fail = 'untestable: tapping the in-level ad entry 3 times did not start a rewarded ad (resume_play.ad must make it show one, e.g. use the item up first)';
      }
    }
    c.lifecycle = (await P.hostSince(page, idx)).filter((r) => r.kind === 'lifecycle').map((r) => r.data);
    return { fail, warn };
  }
  async function back(c, cs) {
    await P.sleep(1500);
    c.back_png = await G.shot(page, path.join(C.evidenceDir, 'resume-' + safe(cs.id) + '-back.png'));
    const k = await P.tapContinue(page, disc.cont, 2);
    c.continue_taps = k.taps;
    if (k.still) return 'after ' + cs.id + ': the pause popup did not close with 2 real taps on ' + disc.cont;
    if (k.taps > 1) return 'after ' + cs.id + ': the pause popup needed ' + k.taps + ' taps on ' + disc.cont + ' (the first tap after returning was lost; 甜点消消乐 R47)';
    await P.sleep(800);
    const after = await P.playable(page, B);
    c.after = after;
    c.after_png = await G.shot(page, path.join(C.evidenceDir, 'resume-' + safe(cs.id) + '-after.png'));
    if (!after.ok) return 'after ' + cs.id + ': ' + after.why + (disc.cont ? '' : ' (if the game shows a pause popup after returning, give resume_play.continue_button)');
    return null;
  }
  // a case that cannot run because something was not found or declared: refused for a new game, warning for legacy
  function gap(cs) {
    if (cs.id === 'pause_background') {
      if (disc.none) return { skip: 'declared none: ' + disc.none };
      if (!disc.pause && LEGACY) return { warnSkip: 'no pause_button given - the case "pause popup open while the phone takes the game" did not run [legacy game: the pause control is not looked for]' };
      if (!disc.pause) return { fail: 'no pause control found in the level (no button whose popup has continue / resume' + (prior === null ? '' : ' among the level popups button_sweep opened' + (disc.popups && disc.popups.length ? ': ' + disc.popups.join('; ') : ': none')) + ', none named or drawn pause / 暂停, settings / 设置, menu): write resume_play.pause_button; a level without one breaks the rule 关卡内暂停或设置键 → Continue / Restart / Home (cocos-game-check/test/references/logic-rules.md; 英化固定入口第 9 项): add one, or write {"none": "why"}' };
      if (disc.why) return { fail: 'pause control ' + disc.pause + (disc.found ? ' (found: ' + disc.found + ')' : '') + ': ' + disc.why };
    }
    if (cs.order) {
      if (!ad && adWhy) return { skip: adWhy };
      if (!ad && LEGACY) return { warnSkip: 'no in-level ad entry given (resume_play.ad) - the case "a rewarded ad sends the game to the background" did not run [legacy game: the entries button_sweep found are not used]' };
      if (!ad && prior === null) return { warnSkip: 'no in-level ad entry known: button_sweep did not run before this suite (it runs first in a full run) and resume_play.ad is not written' };
      if (!ad && FACTS.rewarded_ads === false) return { skip: 'the package shows no rewarded ads' };
      if (!ad) return { fail: 'no in-level rewarded ad entry known: button_sweep found none in the level and resume_play.ad is not written. Write resume_play.ad (an in-level prop, hint or revive button that shows a rewarded ad) or {"none": "why the level has no rewarded ad"}' };
    }
    return null;
  }
  async function attempt(cs, reuse) {
    const c = { id: cs.id, reused_level: reuse };
    // a gap that is already known costs no load (the ad gap never needs one, the pause gap after the first discovery)
    if (cs.order || disc.done) { const g = gap(cs); if (g) return Object.assign({ c, gap: true }, g); }
    let fail = reuse ? null : await fresh(c, cs);
    let warn = null;
    if (!fail) { const g = gap(cs); if (g) return Object.assign({ c, gap: true }, g); }
    if (!fail) { const e = await event(c, cs); fail = e.fail; warn = e.warn; }
    if (!fail) fail = await back(c, cs);
    return { c, fail, warn };
  }
  for (const cs of cases) {
    const shareable = !cs.order;            // ad cases use the item up: always a fresh load
    let r = await attempt(cs, live && shareable);
    if (r.fail && !r.gap && r.c.reused_level && !/^invalid run/.test(r.fail)) { r.c.first_try = r.fail; rep.cases.push(r.c); r = await attempt(cs, false); }
    const { c } = r;
    rep.cases.push(c);
    if (r.skip || r.warnSkip) {
      c.result = 'skip';
      if (r.warnSkip) out.warn('resume_play ' + cs.id + ': ' + r.warnSkip);
      out.add(cs.id, true, 'not run: ' + (r.skip || r.warnSkip));
      continue;
    }
    const { fail, warn } = r;
    if (!r.gap) live = !fail && shareable;
    if (warn) { out.warn('resume_play ' + cs.id + ': ' + warn); if (!fail && cs.finger) { out.add(cs.id, true, warn); continue; } }
    c.result = fail ? 'fail' : 'pass';
    const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
    if (fail && !blocks) out.warn('resume_play ' + cs.id + ': ' + fail + ' [legacy game: warning]');
    out.add(cs.id, !blocks, fail || ('plays after ' + cs.id + (c.continue_taps ? ' (pause popup closed with 1 tap)' : '') + (c.reused_level ? ', same level as the case before' : '')));
  }
  rep.discovery = { pause: disc.pause, pause_found: disc.found || false, continue: disc.cont, continue_found: !!disc.contFound, none: disc.none, why: disc.why || null };
  out.evidence.report = L.evidence('resume_play.json', rep);
  out.evidence.discovery = rep.discovery;
  out.evidence.ad = rep.ad;
}, { w: 390, h: 844 });
