// Startup suite (mandatory for every TikTok package). Contract: ../README.md.
// Each case boots the REAL package in the strict host with one fault, then needs: the home screen
// (adapter.home), at most one Retry tap, and any Retry visible within 20 s of the fault. Lifecycle cases
// (LIFE) also need adapter.play and judge a real PLAY tap after a clock jump / background / hung image.
// Sources: Mabel r7/r8 (D4 2.2), MergeShot2048 v81-v84 (D6 items 3, 4, 8), MusicSlice v29b/v30 (D5 5.3).
const L = await import(globalThis.CFG.lib);
const { C, A, sleep } = L;
const fs = await import('node:fs');
const path = await import('node:path');

const RETRY_RX = A.retry_label || '^\\s*(RETRY|Retry|retry|TRY AGAIN|Try again|Try Again|Reload|RELOAD|重试|重新加载)\\s*[!.]?\\s*$';
const MODAL_RX = /retry|try again|reload|load failed|重试|加载失败/i;
const RETRY_WITHIN_MS = 20000;
let lastTapHost = -1;

// Which subpackage the package faults target: 'resources' when present, else the first declared one.
function subpackages() {
  try {
    const g = JSON.parse(fs.readFileSync(path.join(C.package, 'game.json'), 'utf8'));
    return (g.subpackages || g.subPackages || []).map(s => s.name || s.root).filter(Boolean);
  } catch (_) { return []; }
}
const PKGS = subpackages();
const PKG = PKGS.includes('resources') ? 'resources' : PKGS[0];
function mainConfig() {
  // 2.4: assets/main/config.<hash>.json; 3.x: assets/main/config.json (or cc.config.json)
  return fs.existsSync(path.join(C.package, 'assets', 'main')) ? 'assets/main/config' : null;
}
const CFGFILE = mainConfig();

// id, query, limitMs, maxRetries, needs (skip reason when the package cannot express that fault)
const CASES = [
  ['cold', '', 60000, 0, null],
  ['pkg_slow_progress', PKG && `pkgprog=1&pkgms=40000`, 90000, 0, PKG ? null : 'no subpackage'],
  ['pkg_stall_40pct', PKG && `pkgprog=1&stallpkg=0.4&pkgms=20000`, 110000, 1, PKG ? null : 'no subpackage'],
  ['pkg_fail_once', PKG && `failpkg=${PKG}`, 60000, 1, PKG ? null : 'no subpackage'],
  ['pkg_2nd_fail', PKG && `nthpkg=${PKG}:2&nthmode=fail`, 60000, 1, PKG ? null : 'no subpackage'],
  ['pkg_2nd_hang', PKG && `nthpkg=${PKG}:2&nthmode=hang`, 70000, 1, PKG ? null : 'no subpackage'],
  ['config_fail_once', CFGFILE && `failfile=${CFGFILE}&failfile_n=1`, 60000, 1, CFGFILE ? null : 'no assets/main'],
  ['config_hang_once', CFGFILE && `hangfile=${CFGFILE}&hangfile_n=1`, 70000, 1, CFGFILE ? null : 'no assets/main'],
  // D6 item 8 (SDKVersion[0] throws) and D5 problem 5 (isSubContext = getOpenDataContext === undefined)
  // are separate cases so a refusal names which adapter line is old.
  ['sdk_missing', 'sdk=missing', 60000, 0, null],
  ['opendata_missing', 'opendata=missing', 60000, 0, null],
  ['storage_missing_true', 'missing=true', 60000, 0, null],
];

const HOME = A.home;
const isHome = async (page) => { const v = await L.adapterCall(page, HOME); return v === true; };

// Find a visible Retry control. Order: host tt.showModal, adapter.retry, a cc.Label, a DOM button
// on the real body, a "tap to retry" toast (tap the canvas). Returns {how, x, y} or null.
async function findRetry(page) {
  const m = await L.ev(page, () => window.__modalOpen ? { m: window.__modalOpen, r: window.__modalRect('ok') } : null);
  if (m && m.r && MODAL_RX.test([m.m.title, m.m.content, m.m.confirmText].join(' '))) return { how: 'modal', x: m.r.x, y: m.r.y, text: m.m.confirmText };
  if (A.retry) { const p = await L.locate(page, A.retry); if (p) return { how: 'adapter', x: p.x, y: p.y }; }
  const lab = await L.findLabels(page, RETRY_RX).catch(() => []);
  const hitL = (lab || []).find(h => typeof h.x === 'number');
  if (hitL) return { how: 'label', x: hitL.x, y: hitL.y, text: hitL.text };
  // No DOM branch: TikTok draws no DOM, and the host hides what the game appends (window.__domHidden).
  // Finger Mahjong v57's DOM Retry passed here and was invisible on the phone.
  // Canvas-drawn Retry before the engine exists (MergeShot2048 v82 native-preload "Tap to Retry").
  const drawn = await L.ev(page, (after) => window.__canvasText ? window.__canvasText('retry|reload|重试|重新加载', after) : null, lastTapHost);
  if (drawn) return { how: 'canvas-text', x: drawn.x, y: drawn.y, text: drawn.text };
  const toast = await L.ev(page, (after) => { const s = window.__hostState(); return (s.toasts || []).filter(t => /retry/i.test(t.title || '') && t.t > after).pop() || null; }, lastTapHost);
  if (toast) return { how: 'toast', x: 195, y: 422, text: toast.title };
  return null;
}

// Lifecycle cases (Finger Mahjong v57, 10-30). On a phone the lock screen / Control Center freezes JS,
// sometimes with no onHide, and leaving the app fires onHide/onShow while Date.now jumps. Neither is a
// loading failure: no Retry, the home page must come, and its PLAY button must answer a REAL tap
// (v57's watchdog counted the pause as a stall and silently locked every home button).
// Lifecycle cases (Finger Mahjong v57, 10-30). On a phone the lock screen / Control Center freezes JS,
// sometimes with no onHide, and leaving the app fires onHide/onShow while Date.now jumps. Neither is a
// loading failure: no Retry, the home page must come, and its PLAY button must answer a REAL tap
// (v57's watchdog counted the pause as a stall and silently locked every home button). A frozen thread
// is modelled as a Date.now jump with no hide event: a real debugger pause lets queued load callbacks
// reset a watchdog first, so it only sometimes catches v57; the jump always does.
// image_hang_once: the first package image never answers (G7 runtime half). A good loader asks again;
// one visible, working Retry is allowed. v57 failed the image after 8 s and locked the home page.
const LIFE = [
  // id, fault, extra query, Retry taps allowed
  ['home_play', null, '', 0],
  ['clock_jump_12s_loading', 'jump', '', 0],
  ['background_60s_loading', 'background', '', 0],
  ['image_hang_once', null, 'imghang=native&imghang_n=1', 1],
];
async function runLife(page, out, [id, fault, query, maxRetries]) {
  if (!A.play) { out.add(id, false, { problems: ['adapter.play is missing: a locator for the home PLAY button (return CSS {x, y} on Cocos 2.4)'] }); return; }
  lastTapHost = -1;
  await page.goto(L.url(['reset=1', query].filter(Boolean).join('&')));
  const t0 = Date.now(), problems = [];
  let how = null, home = false, left = false, struck = null, retries = 0;
  if (fault) {
    // Strike while the game is really loading: a scene runs, a package image is in flight, no home yet.
    const loading = () => L.ev(page, () => !!(window.cc && cc.director && cc.director.getScene && cc.director.getScene()) &&
      !!(window.__hostPending && window.__hostPending().images > 0)).catch(() => false);
    while (Date.now() - t0 < 30000) {
      if (await loading()) break;
      if (await isHome(page).catch(() => false)) break;
      await sleep(20);
    }
    struck = (await isHome(page).catch(() => false)) ? 'after-home' : 'before-home';
    if (struck === 'after-home') out.warn(`${id}: the home page was already shown when the ${fault} began`);
    // Repeat while loading continues (at most 6 times, 300 ms apart): a game's own watchdog may be created a
    // moment later and must see at least one jump while it is alive.
    let strikes = 0;
    do {
      if (fault === 'jump') await L.ev(page, () => window.__warp(12000));
      else { await L.ev(page, () => { window.__simHide(); window.__warp(60000); }); await sleep(200); await L.ev(page, () => window.__simShow()); }
      strikes++;
      await sleep(300);
    } while (strikes < 6 && !(await isHome(page).catch(() => false)) && await loading());
    how = (fault === 'jump' ? 'Date.now +12 s, no hide event' : 'onHide + 60 s + onShow') + ` x${strikes}`;
  }
  while (Date.now() - t0 < 90000) {
    if (await isHome(page).catch(() => false)) { home = true; break; }
    const r = await findRetry(page).catch(() => null);
    if (r) {
      if (++retries > maxRetries) { problems.push(`a Retry (${r.how}) appeared after ${fault ? 'a ' + fault : 'the fault'}` + (maxRetries ? ` ${retries} times` : '; a pause is not a loading failure')); break; }
      await sleep(600); await L.touchTap(page, r.x, r.y); await sleep(1500); continue;
    }
    await sleep(500);
  }
  if (!home && !problems.length) problems.push('home not reached within 90 s');
  if (home) {
    await sleep(1500);
    const p = await L.locate(page, A.play);
    if (!p) problems.push('adapter.play found no PLAY button on the home page');
    else {
      await L.touchTap(page, p.x, p.y);
      for (let i = 0; i < 20 && !left; i++) {
        await sleep(500);
        left = !(await isHome(page).catch(() => true)) || (A.in_level ? (await L.adapterCall(page, A.in_level).catch(() => false)) === true : false);
      }
      if (!left) problems.push('the home page is shown but PLAY did not answer a real tap (home locked)');
    }
  }
  let shot = null;
  try { shot = path.join(C.evidenceDir, `startup-${id}.png`); await page.screenshot({ path: shot }); } catch (_) { shot = null; }
  out.add(id, problems.length === 0, { fault, how, struck, home, left, retries, problems, ms: Date.now() - t0,
    domHidden: await L.ev(page, () => window.__domHidden || []).catch(() => []),
    errors: (await L.errors(page).catch(() => [])).slice(0, 4), screenshot: shot });
}

async function runCase(page, out, [id, query, limitMs, maxRetries, skip]) {
  if (skip) { out.add(id, true, { skipped: skip }); return; }
  lastTapHost = -1;
  const q = ['reset=1', query].filter(Boolean).join('&');
  await page.goto(L.url(q));
  const t0 = Date.now(), timeline = [];
  let home = false, retries = 0, lastRetryText = null, problems = [], firstFault = null;
  while (Date.now() - t0 < limitMs) {
    await sleep(500);
    let st = null;
    try { st = await L.hostState(page); } catch (_) {}
    if (st && st.faults && st.faults.hits) {
      // Retry deadline counts from the latest fault hit or the latest Retry tap, whichever is later.
      const f = await L.ev(page, () => { const h = window.__faults.hits || []; return h.length ? h[h.length - 1] : null; });
      if (f) firstFault = Math.max(f.t, lastTapHost);
    }
    try { home = await isHome(page); } catch (_) { home = false; }
    if (home) { timeline.push({ ms: Date.now() - t0, k: 'home' }); break; }
    const r = await findRetry(page).catch(() => null);
    if (r) {
      const hostMs = st ? st.t : null;
      timeline.push({ ms: Date.now() - t0, k: 'retry-visible', how: r.how, text: r.text, hostMs, faultMs: firstFault });
      if (firstFault !== null && hostMs !== null && hostMs - firstFault > RETRY_WITHIN_MS + 1500) problems.push(`Retry appeared ${Math.round((hostMs - firstFault) / 1000)} s after the fault (limit 20 s)`);
      retries++;
      if (retries > maxRetries) { problems.push(`Retry needed ${retries} times (allowed ${maxRetries})`); break; }
      await sleep(600);
      await L.touchTap(page, r.x, r.y);
      lastTapHost = hostMs === null ? lastTapHost : hostMs;
      timeline.push({ ms: Date.now() - t0, k: 'tap-retry' });
      await sleep(1500);
      continue;
    }
    if (firstFault !== null && st && st.t - firstFault > RETRY_WITHIN_MS + 2000 && retries === 0 && !home) {
      // Fault fired, no Retry within 20 s and no home: stuck (MergeShot2048 v81 "Ready").
      const later = await isHome(page).catch(() => false);
      if (!later) { problems.push('no Retry within 20 s of the fault and home not reached (stuck)'); break; }
    }
  }
  const st = await L.hostState(page).catch(() => null);
  const errs = await L.errors(page).catch(() => []);
  const warns = await L.ev(page, () => (window.__hostLog || []).filter(r => /^console\.(warn|error)$/.test(r.kind) && /saved value is unavailable|unavailable|JSON|parse/i.test(String(r.data))).slice(0, 6).map(r => String(r.data).slice(0, 200))).catch(() => []);
  if (!home && !problems.length) problems.push(`home not reached within ${Math.round(limitMs / 1000)} s` + (retries ? ` (after ${retries} Retry tap)` : ''));
  if (id === 'storage_missing_true') {
    const bad = warns.filter(w => /saved value is unavailable/i.test(w));
    if (bad.length) problems.push('missing key read as unavailable: ' + bad[0]);
    if (st && !st.storageWrites) out.warn('storage_missing_true: no default save written after reaching home');
  }
  let shot = null;
  try { shot = path.join(C.evidenceDir, `startup-${id}.png`); await page.screenshot({ path: shot }); } catch (_) { shot = null; }
  out.add(id, problems.length === 0, {
    query: q, home, ms: Date.now() - t0, retries, problems, timeline,
    subpackageAttempts: st && st.faults && st.faults.pkg, faultHits: st && st.faults && st.faults.hits,
    errors: errs.slice(0, 4), savedValueWarnings: warns, screenshot: shot });
}

await L.suite(async ({ out, page }) => {
  out.evidence.subpackage = PKG || null;
  out.evidence.config = CFGFILE;
  const only = (A.startup_cases || '').split(',').filter(Boolean);
  for (const c of CASES) {
    if (only.length && !only.includes(c[0])) continue;
    await runCase(page, out, c);
    console.log(JSON.stringify(out.cases[out.cases.length - 1]).slice(0, 300));
  }
  for (const c of LIFE) {
    if (only.length && !only.includes(c[0])) continue;
    await runLife(page, out, c);
    console.log(JSON.stringify(out.cases[out.cases.length - 1]).slice(0, 300));
  }
  out.evidence.log = C.logFile;
}, { w: 393, h: 852, dpr: 3, touch: true });
