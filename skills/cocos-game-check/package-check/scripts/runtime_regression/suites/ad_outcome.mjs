// ad_outcome (v7.9, 手机才出的五类问题 2): what happens AFTER a player taps a rewarded-ad entry, on a phone. ad_entries
// (v7.8) only proves the tap reaches an ad; ad_regression drives the SDK through adapter.request, not through the button.
// The ad plays like on a phone: tt.onHide when the video starts, tt.onShow + onClose when it ends (host adhide=1).
// v7.9 手机检查补全 (Saul 11-04「全部补上」): 割草 v011-v015, 人鱼 v14, 香肠 R17 never wrote ad_entries, so this suite
// never ran on any game but 甜点消消乐. Now it runs for every package that calls tt.createRewardedVideoAd, and the
// entries come from what the run already knows:
//   adapter.ad_entries      each entry in each of its states (real actions, as ad_entries)
//   resume_play.ad          the in-level entry, in the level resume_play.start reaches
//   button_sweep            every button its real taps saw start an ad this run (home, its popups, the level; CFG.prior).
//                           List items of one kind (same route, same picture, path differing in numbers) count once.
// Each entry, one load (a fresh one again only when the cancel took the entry away):
//   <entry>/cancel     the video is closed early: no reward (reward_js unchanged, when written); a pause popup the game
//                      opened meanwhile closes with ONE tap; then the SAME button must start the ad again (a lock or an
//                      "ad in progress" flag left set by the cancel is 「广告点了第二次没反应」)
//   <entry>/complete   that second ad is watched to the end: the reward arrives (reward_js changes; without reward_js
//                      something on screen must change: a counter, a popup, the board), after_js / after_visible when
//                      written, and the game still answers: the resume_play level still plays (clock_js, probe,
//                      state_js), any other entry reacts to the next tap or is gone / greyed out
// adapter.ad_outcome is optional: {continue_button, entries: {<ad_entries id | "resume_play.ad" | node path>: {reward_js,
// after_js, after_visible, continue_button}}}, or {"n/a": "why no player can start a rewarded ad"}.
// No entry known while button_sweep ran: a new game is refused (write ad_entries). New game: refuses. Legacy game
// (Saul 11-04「老游戏先不管」): only adapter.ad_entries runs, as before 手机检查补全, and only warns.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const O = A.ad_outcome || {};
const FACTS = C.facts || {};
const RP = A.resume_play && typeof A.resume_play === 'object' && !Array.isArray(A.resume_play) && !('n/a' in A.resume_play) ? A.resume_play : null;
const ENTRY_KEYS = new Set(['reward_js', 'after_js', 'after_visible', 'continue_button', 'note']);
const MAX_ENTRIES = 10;
const isNone = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && typeof v.none === 'string' && !!v.none.trim();
const strip = (p) => String(p).replace(/#\d+$/, '');
const short = (p) => p === '<play>' ? p : strip(p).split('/').slice(-2).join('/');
const J = (v) => JSON.stringify(v === undefined ? null : v).slice(0, 80);

function problems() {
  const out = A.ad_entries !== undefined ? R.adEntriesProblems(A.ad_entries) : [];
  if (!O || typeof O !== 'object' || Array.isArray(O)) return out.concat(['ad_outcome must be an object']);
  // none (v7.9 手机问题源头约束): {"double" | "revive": why the game has no such button}; the runner checks it
  for (const k of Object.keys(O)) if (!['entries', 'continue_button', 'note', 'none'].includes(k)) out.push('ad_outcome has unknown key ' + JSON.stringify(k));
  if ('continue_button' in O && typeof O.continue_button !== 'string') out.push('ad_outcome.continue_button must be a node path');
  const ent = O.entries || {};
  if (typeof ent !== 'object' || Array.isArray(ent)) return out.concat(['ad_outcome.entries must map an entry (ad_entries id, "resume_play.ad" or the node path of a button) to {reward_js, after_js, after_visible}']);
  const ids = new Set((A.ad_entries || []).map((e) => e && e.id));
  for (const id of Object.keys(ent)) {
    if (!ids.has(id) && id !== 'resume_play.ad' && !id.includes('/')) out.push('ad_outcome.entries.' + id + ': not an ad_entries id, "resume_play.ad" or a node path');
    const e = ent[id];
    if (!e || typeof e !== 'object' || Array.isArray(e)) { out.push('ad_outcome.entries.' + id + ' must be an object'); continue; }
    for (const k of Object.keys(e)) if (!ENTRY_KEYS.has(k)) out.push('ad_outcome.entries.' + id + ' has unknown key ' + JSON.stringify(k));
    for (const k of ['reward_js', 'after_js', 'continue_button', 'note']) if (k in e && typeof e[k] !== 'string') out.push('ad_outcome.entries.' + id + '.' + k + ' must be a string');
    if (e.after_visible && !(Array.isArray(e.after_visible) && e.after_visible.every((x) => typeof x === 'string'))) out.push('ad_outcome.entries.' + id + '.after_visible must be a list of node paths');
  }
  return out;
}

// ---- the entries ----
async function entries() {
  const list = [], skipped = [];
  for (const e of A.ad_entries || []) for (const s of e.states) list.push({ id: e.id + '/' + s.name, key: e.id, button: e.button, state: s, from: 'ad_entries', role: e.role || null });
  if (POLICY === 'legacy') return { list: A.ad_outcome ? list : [], skipped, prior: null };   // as before: ad_entries + ad_outcome
  if (RP && RP.ad && !isNone(RP.ad) && Array.isArray(RP.start))
    list.push({ id: 'resume_play.ad', key: 'resume_play.ad', button: RP.ad.tap || null, tap_js: RP.ad.tap_js || null, level: true, from: 'resume_play.ad',
      state: { name: 'level', actions: RP.start.concat(RP.ad.actions || []), settle_ms: RP.settle_ms || 1500 } });
  const prior = await P.priorAdEntries();
  const known = new Set(list.filter((x) => x.button).map((x) => strip(x.button)));
  const kinds = new Set();
  for (const f of prior || []) {
    const taps = f.taps.map((t) => (t === '<play>' ? t : strip(t)));
    const button = taps[taps.length - 1], route = taps.slice(0, -1);
    if (known.has(button)) continue;
    const kind = route.join(' > ') + ' | ' + button.replace(/\d+/g, '#') + ' | ' + (f.sig || '');
    if (kinds.has(kind)) { skipped.push(taps.join(' > ') + ': same kind as an entry tested (same route, picture and path apart from numbers)'); continue; }
    kinds.add(kind); known.add(button);
    list.push({ id: taps.map(short).join(' > '), key: button, button, route, from: 'button_sweep', sig: f.sig || null, taps,
      state: { name: 'found', play: route[0] === '<play>', actions: route.filter((t) => t !== '<play>').map((p) => ({ tap: p, after: 1300 })) } });
  }
  return { list, skipped, prior };
}

const baseQuery = String(A.ad_entries_query || '').split('&').filter((x) => x && !/^(ad|ads|adhide|adhideorder|adms)=/.test(x)).join('&');

async function reach(page, en) {
  const home = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
  if (!home.ok) return home.fps != null && home.fps < G.MIN_FPS ? 'invalid run: the page ran at ' + home.fps + ' fps, re-run with the Ego window visible' : 'untestable: home not reached';
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
  if (en.state.play) { const e = await P.enterLevel(page); if (!e.ok) return 'untestable: the level was not entered (' + e.why + ')'; }
  if (en.state.actions && en.state.actions.length) { const r = await P.steps(page, en.state.actions); if (!r.ok) return 'untestable: state not reached: ' + r.why; }
  if (en.state.setup_js) await G.evalJs(page, en.state.setup_js).catch(() => null);
  await P.sleep(en.state.settle_ms || 800);
  return null;
}

const where = (page, en) => P.point(page, en.button ? en.button : { tap_js: en.tap_js });
// the entry's button; an entry found behind an opener: the opener tapped again first
async function find(page, en) {
  let p = await where(page, en);
  const opener = en.route && en.route.length ? en.route[en.route.length - 1] : null;
  if (!p && opener && opener !== '<play>') {
    const o = await G.nodeCentre(page, opener).catch(() => null);
    if (o) { await G.click(page, o.x, o.y); await P.sleep(1300); p = await where(page, en); }
  }
  return p;
}
const promptsSince = (page, g0) => page.evaluate((g) => (window.__gateLog || []).filter((x) => x.t >= g && (x.kind === 'toast' || x.kind === 'modal'))
  .map((x) => String(x.data && typeof x.data === 'object' ? (x.data.title || x.data.content || x.kind) : (x.data || x.kind)).slice(0, 60)), g0).catch(() => []);

// one real tap on the entry while the next simulated ad ends `mode` -> {gone} | {noAd, reaction, prompts} | {ad, before, noisy, g0}
async function adTap(page, en, mode) {
  await P.setAd(page, mode);
  const p = await find(page, en);
  if (!p) return { gone: true };
  const idle0 = await P.snap(page); await P.sleep(1000); const before = await P.snap(page);
  const d0 = R.snapDiff(idle0, before);
  const noisy = new Set([...d0.add, ...d0.gone, ...d0.moved, ...d0.text, ...d0.sprite]);
  const at = (await where(page, en)) || p;
  const idx = await P.hostIdx(page);
  const g0 = await page.evaluate(() => (window.__gateNow ? window.__gateNow() : 0)).catch(() => 0);
  await G.click(page, at.x, at.y);
  let seen = { shown: false, ended: false, lifecycle: [] };
  const t0 = Date.now();
  while (Date.now() - t0 < 12000) {
    await P.sleep(300);
    const rows = await P.hostSince(page, idx);
    seen = { shown: rows.some((r) => r.kind === 'ad-show'), ended: rows.some((r) => r.kind === 'ad-result'), lifecycle: rows.filter((r) => r.kind === 'lifecycle').map((r) => r.data) };
    if (!seen.shown && Date.now() - t0 > 2500) break;
    if (seen.ended && seen.lifecycle.includes('show')) break;
  }
  const prompts = await promptsSince(page, g0);
  // a prompt from the start of the ad ("Loading ad...") is not the reward: only what comes after the ad ended counts
  const gEnd = await page.evaluate(() => (window.__gateNow ? window.__gateNow() : 0)).catch(() => 0);
  if (!seen.shown) {
    const after = await P.snap(page);
    let d = R.snapDiff(before, after, noisy);
    if (en.button) d = R.dropPress(d, strip(en.button), before, after);
    const n = d.add.length + d.gone.length + d.moved.length + d.text.length + d.sprite.length;
    return { noAd: true, prompts, reaction: prompts.length ? 'prompt' : after.scene !== before.scene ? 'scene' : n ? 'screen' : null };
  }
  return { ad: seen, before, noisy, g0, gEnd, prompts };
}

// after an ad: a dialog over the game is answered, the pause popup the game opened meanwhile goes with ONE tap. A
// continue button under another popup is part of the state, not tapped (香肠 R17: after a cancelled energy ad the
// "not enough energy" popup stays over the pause popup's Resume, as it should).
const coverState = (page, p) => G.evalJs(page, 'var n = findNode(' + JSON.stringify(p) + '); if (!n || !screenOf(n)) return null; return { cover: coverOf(n) || null };').catch(() => null);
async function closeBack(page, cont, before) {
  const modal = await P.dismissModal(page);
  let k = null, how = 'continue_button';
  if (cont && (await coverState(page, cont))) k = cont;
  if (!k) { k = P.pickContinue(P.buttonsOf(await P.snap(page)).filter((n) => !before.m[n.path])); how = 'appeared'; }
  if (!k) return { taps: 0, still: false, modal };
  const st = await coverState(page, k);
  if (st && st.cover) return { taps: 0, still: false, button: k, covered: st.cover, modal };
  return Object.assign(await P.tapContinue(page, k, 2), { button: k, how, modal });
}

// after the reward: the entry answers the next tap (or is gone / greyed out)
async function usable(page, en) {
  const p = await find(page, en);
  if (!p) return { note: 'the entry is gone after the reward' };
  await P.setAd(page, 'complete');
  const r = await P.tapReact(page, en.button ? strip(en.button) : p, { ms: 2500, game: !!(en.state.play || en.level) });
  if (r && r.kind !== 'untestable') return { note: 'next tap: ' + r.kind, r };
  const off = en.button ? await G.evalJs(page, 'var n = findNode(' + JSON.stringify(strip(en.button)) + '); var b = n && n.getComponent(cc.Button); return b ? b.interactable : null;').catch(() => null) : null;
  if (off === false) return { note: 'the button is disabled after the reward (interactable=false: it must be drawn greyed out)', warn: true };
  return { fail: 'after the reward ' + (en.button || 'the entry') + ' does nothing on the next tap (the game is left in an ad / pause state or a busy flag stayed set; 甜点消消乐 R47: after the ad nothing answered)' };
}

const safe = (s) => String(s).replace(/[^\w.-]+/g, '_').slice(0, 60);

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'ad_outcome', policy: POLICY, cases: [] };
  const bad = problems();
  if (bad.length) { out.add('adapter', POLICY === 'legacy', bad.join('; ')); if (POLICY === 'legacy') out.warn('ad_outcome adapter: ' + bad.join('; ') + ' [legacy game: warning]'); return; }
  const { list, skipped, prior } = await entries();
  const disc = ((C.prior || {}).resume_play || {}).discovery || {};
  rep.entries = list.map((e) => ({ id: e.id, from: e.from, role: e.role || null, button: e.button || 'tap_js', sig: e.sig || null, taps: e.taps || null }));
  rep.skipped = skipped;
  const done = () => { out.evidence.report = L.evidence('ad_outcome.json', rep); out.evidence.entries = rep.entries.map((e) => e.id); };
  if (!list.length) {
    if (POLICY === 'legacy') {
      if (A.ad_entries && !A.ad_outcome) { out.warn('ad_outcome not run: adapter has no "ad_outcome" [legacy game: warning]'); out.add('adapter', true, 'legacy game: warning'); }
      else out.add('entries', true, 'legacy game: only adapter.ad_entries with ad_outcome runs, none written');
      return done();
    }
    if (FACTS.rewarded_ads === false && !A.ad_entries) { out.add('entries', true, 'the package shows no rewarded ads (no createRewardedVideoAd call)'); return done(); }
    let why, block = false;
    if (prior === null) why = 'not run: no rewarded-ad entry known: button_sweep did not run before this suite (it runs first in a full run) and the adapter has no ad_entries / resume_play.ad';
    else {
      why = 'the package calls tt.createRewardedVideoAd but no button that starts a rewarded ad is known: button_sweep tapped the home buttons, their popups and the level and none started an ad, and the adapter has no ad_entries / resume_play.ad. Write ad_entries (the buttons and the states that show a rewarded ad: revive after a loss, double reward at the level end, a shop ...) or ad_outcome {"n/a": "why no player can start a rewarded ad"}';
      block = POLICY === 'new';
    }
    if (!block) out.warn('ad_outcome: ' + why + (prior !== null ? ' [legacy game: warning]' : ''));
    out.add('entries', !block, why);
    return done();
  }
  if (list.length > MAX_ENTRIES) out.warn('ad_outcome: ' + (list.length - MAX_ENTRIES) + ' more ad entries not run (at most ' + MAX_ENTRIES + ' per run): ' + list.slice(MAX_ENTRIES).map((e) => e.id).join('; '));
  for (const en of list.slice(0, MAX_ENTRIES)) {
    const spec = (O.entries || {})[en.key] || (O.entries || {})[en.id] || {};
    const cont = spec.continue_button || O.continue_button || (RP && RP.continue_button) || disc.continue || null;
    const c = { id: en.id, from: en.from, button: en.button || 'tap_js' };
    rep.cases.push(c);
    const res = { cancel: null, complete: null }, note = { cancel: '', complete: '' };
    let soft = null;                                   // a found entry that did not start an ad this time: warning
    const reward = async () => (spec.reward_js ? P.js(page, spec.reward_js) : undefined);
    const fresh = async () => { await G.openGame(page, 'iphone14', 'capsule=pt&ad=cancel&adhide=1&adms=900' + (baseQuery ? '&' + baseQuery : '')); return reach(page, en); };
    let base;
    run: {
      const f0 = await fresh();
      if (f0) { res.cancel = res.complete = f0; break run; }
      // ---- cancel ----
      c.reward0 = base = await reward();
      if (base && base.adapterError) { res.cancel = res.complete = 'untestable: reward_js threw: ' + base.adapterError; break run; }
      const t1 = await adTap(page, en, 'cancel');
      c.cancel = { ad: t1.ad || null, reaction: t1.reaction || null, prompts: t1.prompts || [] };
      if (t1.gone) { res.cancel = res.complete = 'missing_entry: ' + c.button + ' not on screen once the state is reached'; break run; }
      if (t1.noAd) {
        const said = t1.prompts.length ? ' (the game said: ' + t1.prompts.join(' / ') + ')' : t1.reaction ? ' (the screen changed: ' + t1.reaction + ')' : ' and nothing happened';
        if (en.from === 'button_sweep') { soft = 'button_sweep saw ' + en.id + ' start an ad, here a tap started none' + said + ' (state differs?): not checked'; break run; }
        res.cancel = res.complete = 'tapped ' + c.button + ' -> no rewarded ad started' + said; break run;
      }
      if (!t1.ad.ended) { res.cancel = res.complete = 'untestable: the simulated ad never ended (host log)'; break run; }
      await P.sleep(1200);
      c.cancel.back_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(en.id) + '-cancel-back.png'));
      const k1 = await closeBack(page, cont, t1.before);
      c.cancel.continue = k1;
      if (k1.still) res.cancel = 'cancel: after the ad the pause popup did not close with 2 taps on ' + k1.button;
      else if (k1.taps > 1) res.cancel = 'cancel: after the ad the pause popup needed ' + k1.taps + ' taps on ' + k1.button + ' (the first tap after returning was lost)';
      await P.sleep(900);
      if (!res.cancel && spec.reward_js) {
        c.reward1 = await reward();
        if (!P.same(c.reward1, base)) res.cancel = 'cancel: the ad was closed early but the reward was given anyway (reward_js ' + J(base) + ' -> ' + J(c.reward1) + ')';
      }
      // ---- complete: the same button again ----
      let t2 = await adTap(page, en, 'complete');
      c.second = { gone: !!t2.gone, ad: t2.ad || null, reaction: t2.reaction || null, prompts: t2.prompts || [] };
      if (t2.gone || t2.noAd) {
        if (t2.gone) note.cancel = 'the entry is gone after the cancelled ad';
        else if (t2.reaction) note.cancel = 'second tap: ' + t2.reaction + ' without an ad' + (t2.prompts.length ? ' (' + t2.prompts.join(' / ') + ')' : '');
        else if (!res.cancel) res.cancel = 'cancel: after a cancelled ad the same button does nothing on a second tap (an "ad in progress" lock stayed set: 广告点了第二次没反应)';
        // the complete from a fresh load
        const f1 = await fresh();
        if (f1) { res.complete = f1; break run; }
        c.reward0b = base = await reward();
        t2 = await adTap(page, en, 'complete');
        c.second.fresh = true;
        if (t2.gone) { res.complete = 'missing_entry: ' + c.button + ' not on screen once the state is reached'; break run; }
        if (t2.noAd) { res.complete = 'complete: tapped ' + c.button + ' -> no rewarded ad started'; break run; }
      } else if (spec.reward_js) base = c.reward1 !== undefined ? c.reward1 : await reward();
      if (!t2.ad.ended) { res.complete = 'untestable: the simulated ad never ended (host log)'; break run; }
      await P.sleep(1200);
      c.complete = { ad: t2.ad, back_png: await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(en.id) + '-complete-back.png')) };
      const k2 = await closeBack(page, cont, t2.before);
      c.complete.continue = k2;
      if (k2.still) { res.complete = 'complete: after the ad the pause popup did not close with 2 taps on ' + k2.button; break run; }
      if (k2.taps > 1) { res.complete = 'complete: after the ad the pause popup needed ' + k2.taps + ' taps on ' + k2.button + ' (the first tap after returning was lost)'; break run; }
      await P.sleep(1500);
      // the reward
      if (spec.reward_js) {
        let now = await reward(); const t0 = Date.now();
        while (P.same(now, base) && Date.now() - t0 < 3000) { await P.sleep(300); now = await reward(); }
        c.reward2 = now;
        if (P.same(now, base)) { res.complete = 'complete: the ad was watched to the end but the reward did not arrive (reward_js stays ' + J(now) + ')'; break run; }
      } else {
        const after = await P.snap(page);
        let d = R.snapDiff(t2.before, after, t2.noisy);
        if (en.button) d = R.dropPress(d, strip(en.button), t2.before, after);
        const prompts = await promptsSince(page, t2.gEnd);
        c.complete.changed = { scene: after.scene !== t2.before.scene ? after.scene : null, add: d.add.slice(0, 4), gone: d.gone.slice(0, 4), moved: d.moved.slice(0, 4), text: d.text.slice(0, 3), sprite: d.sprite.slice(0, 3), prompts };
        // a toast alone is not the reward: the ad wrapper says "Video complete." even when the reward callback never runs
        // (甜点消消乐 R48 with the reward line cut: only that toast, the board and the counters stayed as they were)
        const n = d.add.length + d.gone.length + d.moved.length + d.text.length + d.sprite.length + (after.scene !== t2.before.scene ? 1 : 0);
        if (!n) { res.complete = 'complete: the ad was watched to the end and nothing on screen changed (no counter, popup or board change' + (prompts.length ? '; only the prompt ' + JSON.stringify(prompts.join(' / ')) : '') + '): the reward did not arrive. If this reward does not show on screen, write ad_outcome.entries["' + en.key + '"].reward_js'; break run; }
        note.complete = 'screen changed (' + (d.text[0] || d.add[0] || d.gone[0] || d.moved[0] || d.sprite[0] || after.scene) + ')';
      }
      // usable again
      if (spec.after_js) {
        let ok = false; const t0 = Date.now();
        while (!ok && Date.now() - t0 < 4000) { ok = P.truthy(await P.js(page, spec.after_js)); if (!ok) await P.sleep(400); }
        c.after_ok = ok;
        if (!ok) { res.complete = 'complete: after the ad the game is not usable again (after_js false for 4 s)'; break run; }
      }
      for (const p of spec.after_visible || []) {
        if (!(await G.nodeCentre(page, p).catch(() => null))) { res.complete = 'complete: after the ad ' + p + ' is not on screen any more (拇指弹球 v5: BACK gone after a revive)'; break run; }
      }
      if (en.level && RP) {
        const pl = await P.playable(page, RP);
        c.playable = pl;
        if (!pl.ok) { res.complete = 'complete: after the ad the level does not play: ' + pl.why; break run; }
        note.complete += (note.complete ? '; ' : '') + 'the level plays';
      } else {
        const u = await usable(page, en);
        c.usable = u;
        if (u.fail) { res.complete = 'complete: ' + u.fail; break run; }
        if (u.warn) out.warn('ad_outcome ' + en.id + ': ' + u.note);
        note.complete += (note.complete ? '; ' : '') + u.note;
      }
    }
    c.after_png = await G.shot(page, path.join(C.evidenceDir, 'ad-' + safe(en.id) + '-after.png')).catch(() => null);
    if (soft) { c.result = 'warn'; out.warn('ad_outcome ' + soft); out.add(en.id, true, soft); continue; }
    for (const kind of ['cancel', 'complete']) {
      const fail = res[kind];
      const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
      c[kind + '_result'] = fail ? 'fail' : 'pass';
      if (fail && !blocks) out.warn('ad_outcome ' + en.id + '/' + kind + ': ' + fail + ' [legacy game: warning]');
      out.add(en.id + '/' + kind, !blocks, fail || (kind === 'cancel'
        ? 'no reward' + (spec.reward_js ? ' (reward_js ' + J(c.reward0) + ' kept)' : '') + '; ' + (note.cancel || 'the same button started the ad again')
        : (spec.reward_js ? 'reward ' + J(base) + ' -> ' + J(c.reward2) : '') + (note.complete ? (spec.reward_js ? '; ' : '') + note.complete : '')));
    }
  }
  done();
}, { w: 390, h: 844 });
