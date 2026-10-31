// ad_entries (v7.8, 总表 A12 + B30 B): every rewarded-ad entry the adapter lists ("ad_entries", up to the five entries
// plus revive) must react to a REAL click in a REAL state. From the 全民飞车门禁 prototype ad_entry_reaction_gate.mjs.
// For each entry x state: fresh load (empty save, iPhone 14), reach home, run the state's real-input "actions"
// (gates.runActions: tap, drag, wait_scene, wait_node ...) and then its setup_js, check the button is on screen and not
// covered, record 2 s of idle labels, click its centre with the real mouse. Within 2 s one of:
//   tt.createRewardedVideoAd or ad.show() was called (the ad starts), or tt.showToast / showModal was called, or a new
//   visible label appears / a label's text changes (the player is told why not)
// otherwise dead_button. missing_entry: the button is not on screen once the state is reached (DriftRacer v1: no revive
// page at all). A disabled cc.Button (interactable=false) that stays silent is a warning (must be drawn greyed out).
// Revive: let the hero fail by itself (wait_node on the revive button); forcing finish(false) 3 s in comes before the
// first point where the game rightly offers a revive (layout_rules.adEntriesProblems refuses such a state).
// Division of work: ad_regression.py drives the ad SDK callbacks (timeouts, X, rewards once) through adapter.request;
// this suite only proves the buttons a player taps reach that flow. New game: refuses; legacy game: warnings.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const WINDOW_MS = 2000;

const centre = (page, p) => G.evalJs(page, `var n = findNode(${JSON.stringify(p)});
  if (!n || !n.activeInHierarchy || !shownChain(n)) return null;
  var c = cssBox(n); if (!c) return null;
  var w = c.x1 - c.x0, h = c.y1 - c.y0; if (w < 2 || h < 2) return null;
  var b = n.getComponent(cc.Button);
  return { x: (c.x0 + c.x1) / 2, y: (c.y0 + c.y1) / 2, w: w, h: h, interactable: b ? b.interactable : null, hasButton: !!b, coveredBy: coverOf(n) };`);
async function labels(page) {
  const v = await G.visibleNodes(page);
  return Object.fromEntries(v.nodes.filter((n) => n.kind === 'label').map((n) => [n.path, n.text]));
}
const safe = (s) => String(s).replace(/[^\w.-]+/g, '_').slice(0, 60);

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'ad_entries', policy: POLICY, cases: [] };
  const bad = R.adEntriesProblems(A.ad_entries);
  if (bad.length) { out.add('adapter', false, bad); return; }
  for (const entry of A.ad_entries) for (const state of entry.states) {
    const id = entry.id + '/' + state.name;
    const c = { id, button: entry.button, why: state.why };
    rep.cases.push(c);
    let fail = null, warn = null;
    await G.openGame(page, 'iphone14', 'capsule=pt&' + (A.ad_entries_query || 'ad=complete'));
    const home = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
    if (!home.ok) fail = home.fps != null && home.fps < G.MIN_FPS ? 'invalid run: the page ran at ' + home.fps + ' fps, re-run with the Ego window visible' : 'untestable: home not reached';
    if (!fail && A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await G.sleep(400); }
    if (!fail && state.actions) {
      const ra = await G.runActions(page, state.actions);
      c.actions = ra.log;
      if (!ra.ok) fail = 'untestable: state not reached: ' + ra.why;
    }
    if (!fail && state.setup_js) {
      c.setup = await G.evalJs(page, state.setup_js).catch((e) => 'setup threw: ' + e);
      await G.sleep(state.settle_ms || 800);
    } else if (!fail && state.settle_ms) await G.sleep(state.settle_ms);
    let pos = null;
    if (!fail) {
      pos = await centre(page, entry.button).catch(() => null);
      c.position = pos;
      if (!pos) { fail = 'missing_entry: button ' + entry.button + ' not on screen once the state is reached'; c.png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(id) + '-missing.png')); }
      else if (pos.coveredBy) fail = 'untestable: button covered by ' + pos.coveredBy + ' (the state must close it)';
    }
    if (!fail) {
      const idle0 = await labels(page); await G.sleep(2000); const before = await labels(page);
      const noisy = new Set(Object.keys(before).filter((k) => idle0[k] !== before[k]));
      const mark = await page.evaluate(() => (window.__gateNow ? window.__gateNow() : 0));
      c.before_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(id) + '-before.png'));
      await G.click(page, pos.x, pos.y);
      let reaction = null;
      const t0 = Date.now();
      while (Date.now() - t0 < WINDOW_MS && !reaction) {
        await G.sleep(250);
        const ev = await page.evaluate((mark) => (window.__gateLog || []).filter((r) => r.t >= mark && /^(ad-create|ad-show|toast|modal)$/.test(r.kind)), mark).catch(() => []);
        const ad = ev.find((r) => r.kind === 'ad-create' || r.kind === 'ad-show'), prompt = ev.find((r) => r.kind === 'toast' || r.kind === 'modal');
        if (ad) reaction = { kind: 'ad', detail: ad, ms: Date.now() - t0 };
        else if (prompt) reaction = { kind: 'prompt', detail: prompt, ms: Date.now() - t0 };
        else {
          const now = await labels(page).catch(() => ({}));
          const fresh = Object.keys(now).filter((k) => !noisy.has(k) && now[k] && before[k] !== now[k]);
          if (fresh.length) reaction = { kind: 'text', detail: fresh.slice(0, 4).map((k) => k + ' = ' + now[k]), ms: Date.now() - t0 };
        }
      }
      c.after_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(id) + '-after.png'));
      c.reaction = reaction;
      if (!reaction && pos.interactable === false) warn = entry.button + ' is a disabled cc.Button (interactable=false) and stays silent; acceptable only if it is drawn greyed out (see ' + c.before_png + ')';
      else if (!reaction) fail = 'dead_button: clicked ' + entry.button + ' -> no ad call, no toast / modal, no new text within ' + WINDOW_MS + ' ms';
    }
    c.result = fail ? 'fail' : warn ? 'warn' : 'pass';
    if (warn) out.warn('ad_entries ' + id + ': ' + warn);
    const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
    if (fail && !blocks) out.warn('ad_entries ' + id + ': ' + fail + ' [legacy game: warning]');
    out.add(id, !blocks, fail || (c.reaction ? c.reaction.kind + ' after ' + c.reaction.ms + ' ms' : warn));
  }
  out.evidence.report = L.evidence('ad_entries.json', rep);
}, { w: 390, h: 844 });
