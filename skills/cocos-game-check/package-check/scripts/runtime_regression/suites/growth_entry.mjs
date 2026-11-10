const L = await import(globalThis.CFG.lib);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const B = L.A.growth_entry || {};
const query = {profile: 'getEntranceMissionReward', shortcut: 'getShortcutMissionReward'};
const launch = {profile: 'center', shortcut: 'desktop_shortcut'};
const delta = kind => typeof B.reward_delta === 'number' ? B.reward_delta : B.reward_delta?.[kind];
const queries = logs => logs.filter(row => row.kind === 'mission' && Object.values(query).includes(row.data));
const queryReadiness = (logs, api) => queries(logs).filter(row => row.data === api)
  .map(row => row.growthReady ?? null);
const readyAtCall = samples => samples.length === 1
  && samples[0]?.home === true && samples[0]?.store === true;
const replies = logs => logs.filter(row => row.kind === 'growth-reply');
const showSeen = (logs, scene) => logs.some(row => row.kind === 'growth-show-scene' && row.data === scene);
const navigation = {profile: 'startEntranceMission', shortcut: 'addShortcut'};
const growthGuidance = /open\s+this\s+game\s+from\s+the\s+tiktok\s+entry\s*,?\s*then\s+check\s+again|opening\s+tiktok|available\s+in\s+tiktok|return\s+through\s+this\s+tiktok\s+entry|then\s+tap\s+check\s+reward/i;

await L.suite(async ({out, page}) => {
  if (typeof L.A.home !== 'string' || !L.A.home.trim() || !B.profile_button
      || (globalThis.CFG.policy === 'new' && !B.shortcut_button)
      || typeof B.entry_ready_js !== 'string' || !B.entry_ready_js.trim()
      || typeof B.observe_js !== 'string' || !Array.isArray(B.covered_steps) || !B.covered_steps.length
      || Object.keys(query).some(k => !Number.isFinite(delta(k)) || delta(k) <= 0)) {
    out.add('adapter', false, 'Provide home readiness, both profile_button and shortcut_button for new games, entry_ready_js, covered_steps, observe_js and reward_delta.');
    return;
  }
  // The local hosts log SDK calls synchronously, before scheduling replies.
  // Observe that moment in this suite's isolated page without changing the mock SDK.
  await page.cdp('Page.addScriptToEvaluateOnNewDocument', {source: '(' + ((readyBody, apis) => {
    const readReady = new Function(readyBody);
    Object.defineProperty(window, '__hostLog', {
      configurable: true,
      set(rows) {
        Object.defineProperty(window, '__hostLog', {value: rows, configurable: true, writable: true});
        const push = rows.push;
        rows.push = function (...items) {
          for (const row of items) {
            if (row.kind !== 'mission' || !apis.includes(row.data)) continue;
            try {
              const state = readReady();
              row.growthReady = {home: state?.home === true, store: state?.store === true};
            } catch (e) {
              row.growthReady = {home: false, store: false, error: String(e.message || e)};
            }
          }
          return push.apply(this, items);
        };
      },
    });
  }).toString() + ')(' + JSON.stringify(B.entry_ready_js) + ',' + JSON.stringify(Object.values(query)) + ')'});
  const run = Date.now() + '-' + Math.random().toString(36).slice(2);
  function params(id, scene, mode, delay) {
    return new URLSearchParams({growth_store: run + '-' + id, growth_launch: scene,
      mission: mode, growth_delay: delay || 200}).toString();
  }
  async function observe() {
    const state = await P.js(page, B.observe_js);
    if (!state || typeof state.covered !== 'boolean' || !Number.isFinite(state.wallet)
      || !Array.isArray(state.hints) || !state.hints.every(s => typeof s === 'string')
      || Object.keys(query).some(k => typeof state.claimed?.[k] !== 'boolean'
        || typeof state.claimed_visible?.[k] !== 'boolean')) {
      throw Error('observe_js must read the real wallet, saved claims, visible claim badges, covered state, and visible growth hints');
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

  async function directTap(kind, button, caseSuffix = '_first_tap_navigates') {
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
    out.add(kind + caseSuffix, passed, {calls, hints: [...new Set(leaked)], toast: oldToast(log)});
    return passed;
  }
  const standard = params('qr', 'scan_qrcode', 'reward');
  await boot(standard);
  await L.sleep(400);
  const initial = await observe();
  const qr = await L.hostLog(page);
  out.add('ordinary_cold_entry_stays_idle',
    queries(qr).length === 0 && Object.keys(query).every(k => !initial.claimed[k] && !initial.claimed_visible[k]) && !initial.hints.length,
    {state: initial, queries: queries(qr)});

  for (const kind of Object.keys(query)) {
    const cold = params(kind, launch[kind], 'reward');
    await boot(cold);
    await poll(async () => {
      const state = await observe();
      return state.claimed[kind] && state.wallet === initial.wallet + delta(kind);
    });
    const after = await observe();
    const log = await L.hostLog(page);
    const observedCalls = queries(log).map(row => row.data);
    const err = await errors();
    const ready = queryReadiness(log, query[kind]);
    out.add(kind + '_cold_query_after_home_and_store', readyAtCall(ready), {calls: observedCalls, ready});
    out.add(kind + '_cold_entry_awards_once', !err.length && observedCalls.length === 1
      && observedCalls[0] === query[kind] && replies(log).some(row => row.data.api === query[kind] && row.data.eligible)
      && after.wallet === initial.wallet + delta(kind) && after.claimed[kind] && after.claimed_visible[kind]
      && Object.keys(query).filter(k => k !== kind).every(k => !after.claimed[k] && !after.claimed_visible[k]),
    {expectedDelta: delta(kind), before: initial.wallet, after, calls: observedCalls, errors: err});
    await boot(cold);
    await L.sleep(450);
    const restarted = await observe();
    out.add(kind + '_claim_persists_no_duplicate', after.claimed[kind] && restarted.claimed[kind]
      && restarted.claimed_visible[kind]
      && restarted.wallet === after.wallet && !queries(await L.hostLog(page)).length,
    {after, restarted, calls: queries(await L.hostLog(page))});
    const button = B[kind + '_button'];
    if (button) await directTap(kind, button, '_claimed_tap_still_navigates');

    await boot(params(kind + '-denied', launch[kind], 'none'));
    const deniedReply = await poll(async () => replies(await L.hostLog(page))
      .some(row => row.data.api === query[kind] && row.data.eligible === false));
    const deniedState = await observe(), deniedLog = await L.hostLog(page);
    const deniedReady = queryReadiness(deniedLog, query[kind]);
    out.add(kind + '_cold_denial_after_ready_keeps_save', deniedReply
      && queries(deniedLog).length === 1 && readyAtCall(deniedReady)
      && deniedState.wallet === initial.wallet
      && Object.keys(query).every(k => !deniedState.claimed[k] && !deniedState.claimed_visible[k]),
    {after: deniedState, calls: queries(deniedLog), ready: deniedReady});
  }

  for (const kind of Object.keys(query)) {
    const casePrefix = kind === 'profile' ? 'sidebar' : 'shortcut';
    await boot(params('warm-' + kind, 'scan_qrcode', 'reward'));
    const warmBefore = await observe();
    const warm = await foreground(launch[kind]);
    await poll(async () => {
      const state = await observe();
      return state.claimed[kind] && state.wallet === warmBefore.wallet + delta(kind);
    });
    const warmAfter = await observe();
    const warmLog = await logsAfter(warm);
    out.add(casePrefix + '_warm_without_tap_awards_once', showSeen(warmLog, launch[kind])
      && queries(warmLog).length === 1 && queries(warmLog)[0].data === query[kind]
      && warmAfter.claimed[kind] && warmAfter.claimed_visible[kind]
      && Object.keys(query).filter(k => k !== kind).every(k => !warmAfter.claimed[k] && !warmAfter.claimed_visible[k])
      && warmAfter.wallet === warmBefore.wallet + delta(kind) && !oldToast(warmLog),
    {before: warmBefore, after: warmAfter, calls: queries(warmLog)});
    const repeated = await foreground(launch[kind]);
    await L.sleep(350);
    const repeatedLog = await logsAfter(repeated);
    const repeatedState = await observe();
    out.add(casePrefix + '_warm_repeat_does_not_pay_again', showSeen(repeatedLog, launch[kind])
      && !queries(repeatedLog).length && repeatedState.wallet === warmAfter.wallet
      && repeatedState.claimed[kind] && repeatedState.claimed_visible[kind] && !oldToast(repeatedLog),
    {before: warmAfter, after: repeatedState, calls: queries(repeatedLog)});
  }

  await boot(params('covered', 'scan_qrcode', 'none', 1300));
  if (B.shortcut_button) {
    if (!await directTap('shortcut', B.shortcut_button)) {
      // An old shortcut panel can intercept the next tap; isolate the profile check.
      await boot(params('covered-profile', 'scan_qrcode', 'none', 1300));
    }
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
