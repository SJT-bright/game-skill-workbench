// ad_outcome (v7.9, 手机才出的五类问题 2): what happens AFTER a player taps a rewarded-ad entry, on a phone. ad_entries
// (v7.8) only proves the tap reaches an ad; ad_regression drives the SDK through adapter.request, not through the button.
// Here every entry of adapter.ad_entries, in each of its states (same real actions as ad_entries), is tapped for real
// and the ad plays like on a phone: tt.onHide when the video starts, tt.onShow + onClose when it ends (host adhide=1).
//   <entry>/<state>/complete  the reward arrives (adapter.ad_outcome.entries[id].reward_js changes), the game is usable
//                             again (after_js true, after_visible nodes on screen: 拇指弹球 v5 lost BACK after a revive)
//   <entry>/<state>/cancel    no reward (reward_js unchanged) and the same button still reacts to a second tap (a lock
//                             or "ad in progress" flag left set after a cancelled ad is the "广告点了第二次没反应" bug)
// A pause popup the game opens on onHide is closed first (ad_outcome continue_button, or resume_play.continue_button).
// New game: refuses (and adapter.ad_outcome is required next to ad_entries); legacy game: warnings.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const O = A.ad_outcome || {};
const ENTRY_KEYS = new Set(['reward_js', 'after_js', 'after_visible', 'continue_button', 'note']);

function problems() {
  const out = R.adEntriesProblems(A.ad_entries);
  if (!O || typeof O !== 'object' || Array.isArray(O)) return out.concat(['ad_outcome must be an object']);
  for (const k of Object.keys(O)) if (!['entries', 'continue_button', 'note'].includes(k)) out.push('ad_outcome has unknown key ' + JSON.stringify(k));
  const ent = O.entries || {};
  if (typeof ent !== 'object' || Array.isArray(ent)) return out.concat(['ad_outcome.entries must map ad_entries ids to {reward_js, after_js, after_visible}']);
  const ids = new Set((A.ad_entries || []).map((e) => e && e.id));
  for (const id of Object.keys(ent)) {
    if (!ids.has(id)) out.push('ad_outcome.entries.' + id + ': no ad_entries entry with this id');
    const e = ent[id] || {};
    for (const k of Object.keys(e)) if (!ENTRY_KEYS.has(k)) out.push('ad_outcome.entries.' + id + ' has unknown key ' + JSON.stringify(k));
    if (!e.reward_js && !e.after_js) out.push('ad_outcome.entries.' + id + ' needs reward_js (the value the ad gives: coins, item count, lives ...) or after_js (true when the game is usable again, e.g. the hero runs after a revive)');
    if (e.after_visible && !(Array.isArray(e.after_visible) && e.after_visible.every((x) => typeof x === 'string'))) out.push('ad_outcome.entries.' + id + '.after_visible must be a list of node paths');
  }
  for (const id of ids) if (id && !ent[id]) out.push('ad_outcome.entries has no "' + id + '" (write what this entry gives: reward_js / after_js)');
  return out;
}

const safe = (s) => String(s).replace(/[^\w.-]+/g, '_').slice(0, 60);
const baseQuery = String(A.ad_entries_query || '').split('&').filter((x) => x && !/^(ad|adhide|adhideorder|adms)=/.test(x)).join('&');

async function reach(page, state) {
  const home = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
  if (!home.ok) return home.fps != null && home.fps < G.MIN_FPS ? 'invalid run: the page ran at ' + home.fps + ' fps, re-run with the Ego window visible' : 'untestable: home not reached';
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
  if (state.actions) { const r = await P.steps(page, state.actions); if (!r.ok) return 'untestable: state not reached: ' + r.why; }
  if (state.setup_js) await G.evalJs(page, state.setup_js).catch(() => null);
  await P.sleep(state.settle_ms || 800);
  return null;
}

// tap the entry, wait for the simulated video to start and end (and the game to come back) -> {ad, why}
async function watch(page, button) {
  const pos = await G.nodeCentre(page, button).catch(() => null);
  if (!pos) return { why: 'missing_entry: ' + button + ' not on screen once the state is reached' };
  const idx = await P.hostIdx(page);
  await G.click(page, pos.x, pos.y);
  let seen = { shown: false, ended: false, lifecycle: [] };
  const t0 = Date.now();
  while (Date.now() - t0 < 10000) {
    await P.sleep(400);
    const rows = await P.hostSince(page, idx);
    seen = { shown: rows.some((r) => r.kind === 'ad-show'), ended: rows.some((r) => r.kind === 'ad-result'), lifecycle: rows.filter((r) => r.kind === 'lifecycle').map((r) => r.data),
      prompt: rows.filter((r) => r.kind === 'toast' || r.kind === 'modal').map((r) => String(r.data && (r.data.title || r.data.content) || r.data)).slice(0, 2) };
    if (!seen.shown && Date.now() - t0 > 3000) break;
    if (seen.ended && seen.lifecycle.includes('show')) break;
  }
  if (!seen.shown) return { ad: seen, why: 'tapped ' + button + ' -> no rewarded ad started' + (seen.prompt.length ? ' (the game said: ' + seen.prompt.join(' / ') + ')' : '') };
  if (!seen.ended) return { ad: seen, why: 'the simulated ad never ended (host log)' };
  return { ad: seen, pos };
}

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'ad_outcome', policy: POLICY, cases: [] };
  const bad = problems();
  if (bad.length) { out.add('adapter', POLICY === 'legacy', bad.join('; ')); if (POLICY === 'legacy') out.warn('ad_outcome adapter: ' + bad.join('; ') + ' [legacy game: warning]'); return; }
  const contDefault = O.continue_button || (A.resume_play && A.resume_play.continue_button) || null;
  for (const entry of A.ad_entries) for (const state of entry.states) for (const kind of ['complete', 'cancel']) {
    const spec = (O.entries || {})[entry.id] || {};
    const cont = spec.continue_button || contDefault;
    const id = entry.id + '/' + state.name + '/' + kind;
    const c = { id };
    rep.cases.push(c);
    let fail = null;
    await G.openGame(page, 'iphone14', 'capsule=pt&ad=' + kind + '&adhide=1&adms=' + (kind === 'complete' ? 1500 : 900) + (baseQuery ? '&' + baseQuery : ''));
    fail = await reach(page, state);
    if (!fail) {
      c.reward_before = spec.reward_js ? await P.js(page, spec.reward_js) : undefined;
      if (c.reward_before && c.reward_before.adapterError) fail = 'untestable: reward_js threw: ' + c.reward_before.adapterError;
    }
    let pos = null;
    if (!fail) {
      const w = await watch(page, entry.button);
      c.ad = w.ad; pos = w.pos;
      if (w.why) fail = (/^missing_entry/.test(w.why) ? '' : kind + ': ') + w.why;
    }
    if (!fail) {
      await P.sleep(1200);
      c.back_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(id) + '-back.png'));
      const k = await P.tapContinue(page, cont, 2);
      c.continue_taps = k.taps;
      if (k.still) fail = kind + ': after the ad the pause popup did not close with 2 taps on ' + cont;
      else if (k.taps > 1) fail = kind + ': after the ad the pause popup needed ' + k.taps + ' taps on ' + cont + ' (the first tap after returning was lost)';
    }
    if (!fail) {
      await P.sleep(900);
      if (spec.reward_js) {
        let now = await P.js(page, spec.reward_js); const t0 = Date.now();
        while (kind === 'complete' && P.same(now, c.reward_before) && Date.now() - t0 < 3000) { await P.sleep(300); now = await P.js(page, spec.reward_js); }
        c.reward_after = now;
        if (kind === 'complete' && P.same(now, c.reward_before)) fail = 'complete: the ad was watched to the end but the reward did not arrive (reward_js stays ' + JSON.stringify(now) + ')';
        if (kind === 'cancel' && !P.same(now, c.reward_before)) fail = 'cancel: the ad was closed early but the reward was given anyway (reward_js ' + JSON.stringify(c.reward_before) + ' -> ' + JSON.stringify(now) + ')';
      }
    }
    if (!fail && kind === 'complete') {
      if (spec.after_js) {
        let ok = false; const t0 = Date.now();
        while (!ok && Date.now() - t0 < 4000) { ok = P.truthy(await P.js(page, spec.after_js)); if (!ok) await P.sleep(400); }
        c.after_ok = ok;
        if (!ok) fail = 'complete: after the ad the game is not usable again (after_js false for 4 s)';
      }
      for (const p of spec.after_visible || []) {
        if (fail) break;
        if (!(await G.nodeCentre(page, p).catch(() => null))) fail = 'complete: after the ad ' + p + ' is not on screen any more (拇指弹球 v5: BACK gone after a revive)';
      }
    }
    if (!fail && kind === 'cancel') {
      const again = await G.nodeCentre(page, entry.button).catch(() => null);
      c.second_tap = !!again;
      if (again) {
        const r = await P.reaction(page, again.x, again.y, 2500);
        c.second_reaction = r;
        if (!r) fail = 'cancel: after a cancelled ad the same button does nothing on a second tap (an "ad in progress" lock stayed set)';
      }
    }
    c.after_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(id) + '-after.png'));
    c.result = fail ? 'fail' : 'pass';
    const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
    if (fail && !blocks) out.warn('ad_outcome ' + id + ': ' + fail + ' [legacy game: warning]');
    out.add(id, !blocks, fail || (kind === 'complete' ? 'reward ' + JSON.stringify(c.reward_before) + ' -> ' + JSON.stringify(c.reward_after) : 'no reward; second tap: ' + (c.second_reaction ? c.second_reaction.kind : 'button gone after the cancel')));
  }
  out.evidence.report = L.evidence('ad_outcome.json', rep);
}, { w: 390, h: 844 });
