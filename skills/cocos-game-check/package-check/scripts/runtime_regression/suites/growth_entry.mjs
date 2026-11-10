const L = await import(globalThis.CFG.lib);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const B = L.A.growth_entry || {};
const query = {profile: 'getEntranceMissionReward', shortcut: 'getShortcutMissionReward'};
const launch = {profile: 'center', shortcut: 'desktop_shortcut'};
const queries = logs => logs.filter(row => row.kind === 'mission' && Object.values(query).includes(row.data));
const replies = logs => logs.filter(row => row.kind === 'growth-reply');
const showSeen = (logs, scene) => logs.some(row => row.kind === 'growth-show-scene' && row.data === scene);
const navigation = {profile: 'startEntranceMission', shortcut: 'addShortcut'};
const growthGuidance = /open\s+this\s+game\s+from\s+the\s+tiktok\s+entry\s*,?\s*then\s+check\s+again|opening\s+tiktok|available\s+in\s+tiktok|return\s+through\s+this\s+tiktok\s+entry|then\s+tap\s+check\s+reward/i;

await L.suite(async ({out, page}) => {
  if (typeof L.A.home !== 'string' || !L.A.home.trim() || !B.profile_button
      || (globalThis.CFG.policy === 'new' && !B.shortcut_button)
      || typeof B.observe_js !== 'string' || !Array.isArray(B.covered_steps) || !B.covered_steps.length
      || !Number.isFinite(B.reward_delta) || B.reward_delta <= 0) {
    out.add('adapter', false, 'Provide home readiness, both profile_button and shortcut_button for new games, covered_steps, observe_js and reward_delta.');
    return;
  }
  const run = Date.now() + '-' + Math.random().toString(36).slice(2);
  function params(id, scene, mode, delay) {
    return new URLSearchParams({growth_store: run + '-' + id, growth_launch: scene,
      mission: mode, growth_delay: delay || 200}).toString();
  }
  async function observe() {
    const state = await P.js(page, B.observe_js);
    if (!state || typeof state.covered !== 'boolean' || !Number.isFinite(state.wallet)
      || !Array.isArray(state.hints) || !state.hints.every(s => typeof s === 'string')
      || !state.claimed || Object.keys(query).some(k => typeof state.claimed[k] !== 'boolean')) {
      throw Error('observe_js must read the real wallet, claims, covered state, and visible growth hints');
    }
    // Also observe the actual engine labels, regardless of the game's adapter choices.
    const labels = await L.findLabels(page, growthGuidance.source);
    const old = labels.map(label => label.text || 'retired growth copy is visible');
    return {...state, hints: [...state.hints, ...old]};
  }
  async function boot(q) {
    const r = await L.boot(page, q, {until: L.A.home});
    if (!r.ok || r.errors.length) throw Error('Game home did not load cleanly: ' + JSON.stringify(r));
    return observe();
  }
  async function tap(spec) {
    let point;
    await poll(async () => {
      point = await P.point(page, spec);
      return !!point;
    });
    if (!point) throw Error('Required control not visible: ' + spec);
    await L.touchTap(page, point.x, point.y);
  }
  async function foreground(scene) {
    const idx = await P.hostIdx(page);
    if (!await P.hide(page)) throw Error('Missing host hide control');
    await L.sleep(100);
    await L.ev(page, scene => window.__simShow(scene), scene);
    return idx;
  }
  async function logsAfter(idx) { return (await L.hostLog(page)).slice(idx); }
  function oldToast(log) {
    return log.some(row => row.kind === 'toast' && growthGuidance.test(String(row.data || '')));
  }
  async function poll(predicate, timeout = 2500) {
    const end = Date.now() + timeout;
    do {
      if (await predicate()) return true;
      await L.sleep(100);
    } while (Date.now() < end);
    return false;
  }
  const errors = () => L.errors(page);

  async function directTap(kind, button) {
    const start = await observe();
    const idx = await P.hostIdx(page);
    await tap(button);
    const leaked = [];
    const until = Date.now() + 650;
    do {
      const state = await observe();
      leaked.push(...state.hints);
      if (state.covered !== start.covered) leaked.push('the tap opened or closed an in-game panel');
      await L.sleep(75);
    } while (Date.now() < until);
    const log = await logsAfter(idx);
    const calls = log.filter(row => row.kind === 'mission').map(row => row.data);
    const end = await observe();
    const passed = calls.length === 1 && calls[0] === navigation[kind] && !leaked.length && !oldToast(log)
      && end.wallet === start.wallet && Object.keys(query).every(k => end.claimed[k] === start.claimed[k]);
    out.add(kind + '_first_tap_navigates', passed, {calls, hints: [...new Set(leaked)], toast: oldToast(log)});
    return passed;
  }
  const standard = params('qr', 'scan_qrcode', 'reward');
  await boot(standard);
  await L.sleep(400);
  const initial = await observe();
  const qr = await L.hostLog(page);
  out.add('ordinary_cold_entry_stays_idle',
    queries(qr).length === 0 && !initial.claimed.profile && !initial.claimed.shortcut && !initial.hints.length,
    {state: initial, queries: queries(qr)});

  for (const kind of Object.keys(query)) {
    const cold = params(kind, launch[kind], 'reward');
    await boot(cold);
    await poll(async () => {
      const state = await observe();
      return state.claimed[kind] && state.wallet === initial.wallet + B.reward_delta;
    });
    const after = await observe();
    const log = await L.hostLog(page);
    const observedCalls = queries(log).map(row => row.data);
    const err = await errors();
    out.add(kind + '_cold_entry_awards_once', !err.length && observedCalls.length === 1
      && observedCalls[0] === query[kind] && replies(log).some(row => row.data.api === query[kind] && row.data.eligible)
      && after.wallet === initial.wallet + B.reward_delta && after.claimed[kind]
      && !after.claimed[kind === 'profile' ? 'shortcut' : 'profile'],
    {expectedDelta: B.reward_delta, before: initial.wallet, after, calls: observedCalls, errors: err});
    await boot(cold);
    await L.sleep(450);
    const restarted = await observe();
    out.add(kind + '_claim_persists_no_duplicate', after.claimed[kind] && restarted.claimed[kind]
      && restarted.wallet === after.wallet && !queries(await L.hostLog(page)).length,
    {after, restarted, calls: queries(await L.hostLog(page))});
  }

  await boot(params('warm-profile', 'scan_qrcode', 'reward'));
  const warmBefore = await observe();
  const warm = await foreground('center');
  await poll(async () => {
    const state = await observe();
    return state.claimed.profile && state.wallet === warmBefore.wallet + B.reward_delta;
  });
  const warmAfter = await observe();
  const warmLog = await logsAfter(warm);
  out.add('sidebar_warm_without_tap_awards_once', showSeen(warmLog, 'center')
    && queries(warmLog).length === 1 && queries(warmLog)[0].data === query.profile
    && warmAfter.claimed.profile && !warmAfter.claimed.shortcut
    && warmAfter.wallet === warmBefore.wallet + B.reward_delta && !oldToast(warmLog),
  {before: warmBefore, after: warmAfter, calls: queries(warmLog)});
  const repeated = await foreground('center');
  await L.sleep(350);
  const repeatedLog = await logsAfter(repeated);
  const repeatedState = await observe();
  out.add('sidebar_warm_repeat_does_not_pay_again', showSeen(repeatedLog, 'center')
    && !queries(repeatedLog).length && repeatedState.wallet === warmAfter.wallet && repeatedState.claimed.profile
    && !oldToast(repeatedLog),
  {before: warmAfter, after: repeatedState, calls: queries(repeatedLog)});

  await boot(params('covered', 'scan_qrcode', 'none', 1300));
  if (B.shortcut_button) {
    await directTap('shortcut', B.shortcut_button);
  } else {
    out.warn('Legacy adapter has no shortcut_button locator. Shortcut cold entry was checked; its first tap was not exercised.');
  }
  const before = await observe();
  if (!await directTap('profile', B.profile_button)) return;
  const homeOrdinary = await foreground('search');
  await L.sleep(1750);
  const homeOrdinaryState = await observe();
  const homeOrdinaryLog = await logsAfter(homeOrdinary);
  out.add('ordinary_return_after_profile_tap_stays_idle', showSeen(homeOrdinaryLog, 'search')
    && !queries(homeOrdinaryLog).length && !oldToast(homeOrdinaryLog)
    && !homeOrdinaryState.hints.length && homeOrdinaryState.wallet === before.wallet,
  {after: homeOrdinaryState, calls: queries(homeOrdinaryLog)});
  for (const step of B.covered_steps) {
    if (!step.tap && !step.tap_js) throw Error('covered_steps must use real taps');
    await tap(step);
    await L.sleep(step.after || 400);
  }
  if (!await poll(async () => (await observe()).covered)) throw Error('The real tap did not open the covered screen');
  await L.ev(page, () => window.__setMission('reward'));
  const coverStart = await observe();
  const ordinary = await foreground('search');
  let leaked = coverStart.hints.slice();
  const sampleEnd = Date.now() + 1900;
  do {
    const state = await observe();
    if (!state.covered) throw Error('Covered screen closed during ordinary return');
    leaked.push(...state.hints);
    await L.sleep(90);
  } while (Date.now() < sampleEnd);
  const ordinaryLogs = await logsAfter(ordinary);
  const ordinaryAfter = await observe();
  out.add('ordinary_resume_over_other_screen_stays_idle', showSeen(ordinaryLogs, 'search')
    && !queries(ordinaryLogs).length && !leaked.length && !oldToast(ordinaryLogs) && ordinaryAfter.wallet === before.wallet,
  {calls: queries(ordinaryLogs), leaked: [...new Set(leaked)], after: ordinaryAfter});

  await L.ev(page, () => window.__setMission('none'));
  const delayed = await foreground('center');
  leaked = [];
  let reply, replyWallTime = 0;
  const replyEnd = Date.now() + 3600;
  do {
    const state = await observe();
    if (!state.covered) throw Error('Covered screen closed during delayed eligibility check');
    leaked.push(...state.hints);
    const log = await logsAfter(delayed);
    reply = replies(log).find(row => row.data.api === query.profile && row.data.eligible === false);
    if (reply && !replyWallTime) replyWallTime = Date.now();
    if (replyWallTime && Date.now() > replyWallTime + 600) break;
    await L.sleep(90);
  } while (Date.now() < replyEnd);
  const delayedLog = await logsAfter(delayed);
  const after = await observe();
  const err = await errors();
  out.add('real_sidebar_denial_while_covered_keeps_ui_quiet',
    showSeen(delayedLog, 'center') && !!reply && queries(delayedLog).length === 1
      && !leaked.length && !oldToast(delayedLog) && after.wallet === before.wallet && !after.claimed.profile && !err.length,
    {calls: queries(delayedLog), reply: reply || null, leaked: [...new Set(leaked)], after, errors: err});
}, {touch: true, dpr: 1});
