// button_sweep (v7.8, 总表 B30 E + H4): the 全民飞车门禁 prototype button_sweep_gate.mjs as a runtime suite, iPhone 14.
// Every button a new player sees on the home screen is tapped once with the real mouse (the host turns it into a
// TikTok touch); every popup a home button opens is then swept one level deep (fresh load, open it, tap one button).
// A tap reacts within 2 s if any of: an ad call (tt.createRewardedVideoAd / show), a prompt (showToast / showModal),
// a platform call (profile revisit, add to home, login ...), a scene change, nodes appearing / going / moving, a text
// or a sprite frame changing. Changes in a 1.5 s idle window before the tap are ignored.
//   dead_button   an interactable cc.Button with no reaction (one retry after the target holds still)
//   popup_layout  a button a home tap opened is cut by the edge, on the capsule, or with its centre in the bottom band
//   covered_3d    a button a home tap made appear is >= 30 % painted over by 3D (DriftRacer v3: RACE behind the turntable)
// v7.8 W93 (Saul 10-30 21:5x, Meteor Blaster r9 analysis: "tapped" is not "it worked"):
//   blocked_after_close  a popup's close / back / X button hid the popup, and then WITHOUT a reload the page below
//                 did not answer: the opener did not open the popup a second time, or another button that reacted
//                 before did not react (a transparent mask or a full-screen BlockInputEvents left behind, a busy flag
//                 never released). Names the popup's opener and the close button.
//   diagnosis     every dead_button / blocked_after_close says where the tap got stuck, from a page probe
//                 (gates.PROBE_JS): 「点不到（被 X 盖住）」「回调没执行（…）」「回调报错：…」「请求没回来：…」
//                 「点到了也执行了，但画面没变」(layout_rules.diagnose).
//   in game       with adapter.play (the startup suite's PLAY locator) the sweep taps PLAY, then sweeps the in-game
//                 buttons (pause, settings, skills) and one level of the popups they open, close-then-tap included;
//                 own clock min(sweep_budget_s, 90 s); in-game popup geometry only warns. Without play: not run, the
//                 reason in the evidence (notRun) and a warning.
// Warnings: touch-only nodes without reaction (drag targets), already selected items and tabs, disabled buttons,
// buttons covered by a later-drawn blocker, the time budget. Every ad entry found is listed in the evidence (the
// trial-link smoke and an ad_entries adapter use it). Block vs warning: layout_rules.level (new / legacy / 3.x).
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const ENGINE = C.engine || '2.x', POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const DEV = G.DEVICES.iphone14;
const SKIP = A.sweep_skip ? new RegExp(A.sweep_skip, 'i') : null;
const BUDGET = (A.sweep_budget_s || 480) * 1000, MAX_HOME = 30, MAX_POPUP = 40;
const GAME_BUDGET = Math.min(BUDGET, 90000), MAX_GAME = 12, MAX_GAME_POPUP = 12;
const strip = (p) => String(p).replace(/#\d+$/, '');
const isCloser = (n) => R.CLOSE.test(n.path) || R.CLOSE.test(n.sig || '');

async function snap(page) {
  const v = await G.visibleNodes(page);
  const sc = await page.evaluate(() => { const s = window.cc.director.getScene(); return { name: s.name, id: s.uuid || s._id }; });
  const m = {};
  for (const n of v.nodes) m[n.path] = n;
  return { scene: sc.name, sceneId: sc.id, m };
}
const coveredBy = (page, p) => G.evalJs(page, 'var n = findNode(' + JSON.stringify(strip(p)) + '); if (!n) return "gone"; return coverOf(n);').catch(() => null);

// opt: touchOnly, game (in-level noise filter), since / hostIdx (unanswered requests counted from an earlier tap)
async function tapAndWatch(page, p, clipped = false, opt = {}) {
  const windowMs = opt.windowMs || 2000;
  const idle0 = await snap(page); await G.sleep(1500); const before = await snap(page);
  const d0 = R.snapDiff(idle0, before);
  const noisy = new Set([...d0.add, ...d0.gone, ...d0.moved, ...d0.text, ...d0.sprite]);
  const par = opt.game ? R.noisyParents(noisy) : null;
  const c = await G.nodeCentre(page, strip(p));
  if (!c) return { kind: 'untestable', why: 'not on screen' };
  const cov = await coveredBy(page, p);
  if (cov && cov !== 'gone') {
    const cb = (await G.nodeInfo(page, cov).catch(() => null)) || { path: cov };
    return { kind: 'untestable', why: 'covered by ' + cov, coveredBy: cb, diag: R.diagnose({ path: p }, { coveredBy: cb }) };
  }
  // W87 calibration (指尖麻将 v56): a list item the player cannot see (below the list window, under the panel frame)
  // is not tapped; only list items are measured (one frame compare each)
  if (clipped) {
    const d = await G.drawnShare(page, p);
    if (d && typeof d.share === 'number' && d.share < 0.05) return { kind: 'untestable', why: 'not drawn on screen (' + Math.round(d.share * 100) + ' % of its box changes when it is hidden: scrolled out of the list window or under a frame drawn later)' };
  }
  const mark = await page.evaluate(() => ({ g: window.__gateNow ? window.__gateNow() : 0, h: (window.__hostLog || []).length }));
  const since = await G.probeStart(page, p);
  await G.click(page, c.x, c.y);
  const t0 = Date.now(); let r = null, after = before;
  while (Date.now() - t0 < windowMs && !r) {
    await G.sleep(300);
    const ev = await page.evaluate((mark) => (window.__gateLog || []).filter((x) => x.t >= mark.g && /^(ad-create|ad-show|toast|modal)$/.test(x.kind)).map((x) => x.kind)
      .concat((window.__hostLog || []).slice(mark.h).map((x) => 'host:' + x.kind)), mark).catch(() => []);
    if (ev.some((k) => k === 'ad-create' || k === 'ad-show' || k === 'host:ad-create' || k === 'host:ad-show' || k === 'host:legacy-ad-create')) { r = { kind: 'ad' }; break; }
    if (ev.some((k) => k === 'toast' || k === 'modal')) { r = { kind: 'prompt', detail: ev[0] }; break; }
    const plat = ev.find((k) => k.startsWith('host:') && R.PLATFORM_BEACON.test(k.slice(5)));
    if (plat) { r = { kind: 'platform', detail: plat.slice(5) }; break; }
    after = await snap(page).catch(() => after);
    if (after.scene !== before.scene || (after.sceneId && before.sceneId && after.sceneId !== before.sceneId)) { r = { kind: 'scene', detail: after.scene }; break; }
    const dp = R.dropPress(R.snapDiff(before, after, noisy), p, before, after);
    const d = par ? R.dropUnder(dp, par) : dp;
    if (d.add.length || d.gone.length || d.moved.length) r = { kind: 'screen', added: d.add.length, gone: d.gone.length, moved: d.moved.length, paths: d.add.concat(d.gone, d.moved).slice(0, 4) };
    else if (d.text.length) r = { kind: 'text', detail: d.text.slice(0, 2) };
    else if (d.sprite.length) r = { kind: 'sprite', detail: d.sprite.slice(0, 2) };
  }
  if (r) {
    r.ms = Date.now() - t0; await G.sleep(800); after = await snap(page).catch(() => after); r.after = after;
    const pr = await G.probeRead(page, p, since, mark.h).catch(() => null);
    if (pr && pr.err && pr.err.src === 'callback') r.threw = pr.err.msg;
  } else {
    r = { kind: 'none', ms: windowMs };
    const pr = await G.probeRead(page, p, opt.since != null ? opt.since : since, opt.hostIdx != null ? opt.hostIdx : mark.h);
    r.diag = R.diagnose({ path: p, touchOnly: !!opt.touchOnly }, pr);
    r.probe = pr;
  }
  await G.probeStop(page);
  r.since = since; r.hostIdx = mark.h;
  return r;
}
// fix 6: a popup still sliding / scaling in ignores taps: wait until the target holds still (two samples 400 ms apart)
async function settled(page, p, maxMs = 3000) {
  const t0 = Date.now(); let prev = null;
  while (Date.now() - t0 < maxMs) {
    const c = await G.nodeCentre(page, strip(p)).catch(() => null);
    if (c && prev && Math.abs(c.x - prev.x) < 1 && Math.abs(c.y - prev.y) < 1 && Math.abs(c.w - prev.w) < 1) return true;
    prev = c; await G.sleep(400);
  }
  return false;
}
async function tapTwice(page, p, clipped = false, opt = {}) {
  await settled(page, p);
  let r = await tapAndWatch(page, p, clipped, opt);
  if (r.kind === 'none') { await G.sleep(1200); await settled(page, p); const r2 = await tapAndWatch(page, p, clipped, opt); if (r2.kind !== 'none') r2.secondTap = true; r = r2; }
  return r;
}
async function fresh(page, quietMs) {
  await G.openGame(page, 'iphone14', 'capsule=pt&ad=complete' + (A.layout_query ? '&' + A.layout_query : ''));
  const h = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null, quietMs });
  if (h.ok) await G.sleep(800);
  if (h.ok && A.after_home_js) { h.afterHome = await G.evalJs(page, A.after_home_js).catch((e) => 'threw: ' + e); await G.sleep(400); }
  if (h.ok) await G.installProbe(page);
  return h;
}
// W93 (3): from the home page into a level with a real tap on adapter.play; left = in_level true, or home false,
// or (no home test) the scene changed / most home buttons went away.
async function enterGame(page) {
  const p = await L.locate(page, A.play).catch(() => null);
  if (!p) return { ok: false, why: 'adapter.play found no PLAY button on the home page' };
  if (p.onCanvas === false) return { ok: false, why: 'adapter.play points outside the game canvas' };
  const s0 = await snap(page).catch(() => null);
  const homeB = s0 ? R.sweepButtons(s0, DEV) : [];
  await G.click(page, p.x, p.y);
  for (let i = 0; i < 20; i++) {
    await G.sleep(500);
    let left = false;
    if (A.in_level) left = (await L.adapterCall(page, A.in_level).catch(() => false)) === true;
    if (!left && A.home) { const h = await L.adapterCall(page, A.home).catch(() => true); left = !(h === true || (h && h.ok === true)); }
    if (!left && !A.home && !A.in_level) {
      const s = await snap(page).catch(() => null);
      left = !!(s && s0 && (s.scene !== s0.scene || homeB.filter((n) => !s.m[n.path]).length > homeB.length / 2));
    }
    if (left) { await G.sleep(2500); return { ok: true, ms: (i + 1) * 500 }; }
  }
  return { ok: false, why: 'a real tap on PLAY did not leave the home page within 10 s (the startup suite judges PLAY)' };
}
async function covered3d(page, nodes) {
  const cands = nodes.filter((n) => !n.layer).map((n) => ({ path: n.path, kind: 'button', box: n.box }));
  if (!cands.length) return [];
  await G.sleep(1000);
  await page.evaluate(() => window.cc.director.pause());
  await G.sleep(150);
  const occ = await G.occlusion(page, cands, 120);
  await page.evaluate(() => window.cc.director.resume()).catch(() => {});
  return G.coveredOf(occ);
}
async function closeTap(page, p) {
  const c = await G.nodeCentre(page, strip(p)).catch(() => null);
  if (!c) return false;
  await G.probeStart(page, p); await G.click(page, c.x, c.y); await G.sleep(900); await G.probeStop(page);
  return true;
}
// a button of this stage that reacted before (a toggle / text change first: it leaves no popup behind)
function pickOther(rows, opener) {
  const ok = rows.filter((r) => r.path !== opener && !r.touchOnly);
  return (ok.find((r) => r.reaction === 'text' || r.reaction === 'sprite') || ok.find((r) => r.reaction === 'screen') || {}).path || null;
}

await L.suite(async ({ out, page }) => {
  const T0 = Date.now();
  const rep = { suite: 'button_sweep', engine: ENGINE, policy: POLICY, home: [], popups: [], adEntries: [], afterClose: [], game: null, notRun: [], findings: [], warnings: [] };
  const add = (code, msg, extra) => rep.findings.push(Object.assign({ code, msg }, extra || {}));
  const warn = (msg) => rep.warnings.push(msg);
  const say = (r) => (r && r.diag ? ' — ' + r.diag.say : '');
  const deadOrWarn = (n, where, r) => {
    const dw = R.deadWhy(n);
    if (n.touchOnly) warn('touch-only node ' + n.path + where + ' did not react to a tap (fine for drag targets)' + say(r));
    else if (dw.startsWith('warn:')) warn('button ' + n.path + where + ': no reaction, ' + dw.slice(5) + say(r));
    else add('dead_button', 'button ' + n.path + ' ("' + (n.sig || '').slice(0, 40) + '")' + where + ': ' + dw.slice(5) + say(r), { diag: r && r.diag || null });
  };

  // W93 (1): the popup's close button hid it; without a reload, the opener must open it again and another button
  // that reacted before must still react. Returns 'blocked' | 'skip' | 'ok'.
  async function afterClose(st, ctx) {
    const row = { where: st.where, opener: ctx.opener, closer: ctx.closer, checks: [] };
    rep.afterClose.push(row);
    const s = await snap(page).catch(() => null);
    if (!s) { row.skipped = 'no snapshot after the close tap'; return 'skip'; }
    if (ctx.popupPaths.some((p) => s.m[p])) { row.skipped = 'the popup is still shown after the close tap'; return 'skip'; }
    const blocked = (what, r) => {
      row.blocked = what;
      add('blocked_after_close', 'popup opened by ' + ctx.opener + st.where + ', closed with ' + ctx.closer + ': ' + what + say(r), { diag: r && r.diag || null, opener: ctx.opener, closer: ctx.closer });
      return 'blocked';
    };
    const dead = (r) => r.kind === 'none' || (r.kind === 'untestable' && !!r.coveredBy);
    const r1 = await tapTwice(page, ctx.opener, false, { since: ctx.since, hostIdx: ctx.hostIdx, game: st.game });
    const back = r1.after || (await snap(page).catch(() => null));
    const again = !!(back && ctx.popupPaths.some((p) => back.m[p]));
    row.checks.push({ tap: ctx.opener, reaction: r1.kind, reopened: again, diag: r1.diag ? r1.diag.say : undefined });
    if (dead(r1)) return blocked('after it was gone, tapping ' + ctx.opener + ' again did nothing (closed, then not opened again)', r1);
    if (r1.kind === 'untestable') { row.skipped = 'opener ' + r1.why; return 'skip'; }
    if (!again) { warn('popup of ' + ctx.opener + st.where + ': after closing it with ' + ctx.closer + ', tapping the opener again reacted (' + r1.kind + ') but the same popup did not come back'); return 'skip'; }
    if (!ctx.other) return 'ok';
    await closeTap(page, ctx.closer);
    const s2 = await snap(page).catch(() => null);
    if (!s2 || ctx.popupPaths.some((p) => s2.m[p])) { row.skipped = 'second close did not hide the popup'; return 'ok'; }
    const r2 = await tapTwice(page, ctx.other, false, { since: ctx.since, hostIdx: ctx.hostIdx, game: st.game });
    row.checks.push({ tap: ctx.other, reaction: r2.kind, diag: r2.diag ? r2.diag.say : undefined });
    if (dead(r2)) return blocked('after it was gone, ' + ctx.other + ' (it reacted before) did not react', r2);
    return 'ok';
  }

  // One page (home, or the running level): tap each button; popups found go to st.popupsTodo.
  async function sweepStage(st) {
    let dirty = false;
    for (const b of st.buttons) {
      if (Date.now() > st.deadline) { warn('time budget used up: ' + (st.buttons.length - st.rows.length) + ' ' + st.name + ' buttons not swept'); break; }
      if (dirty) { if (!(await st.reload())) { st.reloadFailed(); break; } dirty = false; }
      const r = await tapTwice(page, b.path, !!b.clipped, { touchOnly: !!b.touchOnly, game: st.game });
      const row = { path: b.path, sig: (b.sig || '').slice(0, 60), touchOnly: !!b.touchOnly, reaction: r.kind, why: r.why, ms: r.ms, diag: r.diag ? r.diag.say : undefined, changed: r.paths };
      st.rows.push(row);
      if (r.threw) warn(st.name + ' button ' + b.path + ' reacted (' + r.kind + ') but a callback threw: ' + r.threw);
      if (r.kind === 'none') { deadOrWarn(b, st.where, r); continue; }
      if (r.kind === 'untestable') { warn(st.name + ' button ' + b.path + ': ' + r.why + say(r)); continue; }
      if (r.kind === 'ad') st.adEntries.push({ taps: st.prefix.concat([b.path]), sig: row.sig });
      if (r.kind === 'scene' || r.kind === 'ad' || r.kind === 'prompt') { dirty = true; continue; }
      if (r.kind === 'screen' && r.after) {
        const new0 = R.sweepButtons(r.after, DEV).filter((n) => !st.base.m[n.path]);
        const key = new0.map((n) => n.path).sort().join('|');
        if (new0.length) {
          if (!st.popupsTodo.some((p) => p.key === key)) st.popupsTodo.push({ key, opener: b.path, buttons: new0 });
          for (const n of new0) {
            const [g, gw] = R.popupGeom(n, DEV);
            if (g.length && !st.game) add('popup_layout', 'button ' + n.path + ' opened by ' + b.path + ' is ' + g.join(', '));
            const ws = st.game ? g.concat(gw) : gw;
            if (ws.length) warn('button ' + n.path + ' opened by ' + b.path + st.where + ' is ' + ws.join(', '));
          }
          if (!st.game) for (const o of await covered3d(page, new0).catch(() => [])) add('covered_3d', 'button ' + o.path + ' that appeared after tapping ' + b.path + ' is ' + Math.round(o.covered * 100) + ' % painted over by 3D content (iPhone 14)');
        }
        const closer = new0.find(isCloser);
        if (closer && await closeTap(page, closer.path)) {
          st.checked.add(key + '>' + closer.path);
          await afterClose(st, { opener: b.path, closer: closer.path, popupPaths: new0.map((n) => n.path), other: pickOther(st.rows, b.path), since: r.since, hostIdx: r.hostIdx });
        }
        const back = await snap(page).catch(() => null);
        dirty = !back || back.scene !== st.base.scene || R.sweepButtons(back, DEV).some((n) => !st.base.m[n.path]);
        continue;
      }
      dirty = r.kind !== 'text' && r.kind !== 'sprite';
    }
  }
  // One level of popups, each button after a fresh load + opener tap; a close button that hid its popup gets the
  // reopen check (W93 1) unless the page sweep already checked that close button.
  async function sweepPopups(st) {
    let tested = 0;
    for (const p of st.popupsTodo) {
      const pr = { opener: p.opener, where: st.name, buttons: [] };
      st.popups.push(pr);
      for (const n of p.buttons) {
        if (tested >= st.maxPopup || Date.now() > st.deadline) { warn('popup sweep capped: ' + p.opener + ' -> ' + n.path + ' and later not swept'); return; }
        if (SKIP && (SKIP.test(n.path) || SKIP.test(n.sig || ''))) continue;
        tested++;
        if (!(await st.reload())) { st.reloadFailed(); return; }
        const o = await G.nodeCentre(page, p.opener);
        if (!o) { pr.buttons.push({ path: n.path, reaction: 'untestable', why: 'opener not on screen' }); continue; }
        const hostIdx = await page.evaluate(() => (window.__hostLog || []).length).catch(() => 0);
        const since = await G.probeStart(page, p.opener);
        await G.click(page, o.x, o.y);
        await G.sleep(1300);
        await G.probeStop(page);
        const r = await tapTwice(page, n.path, !!n.clipped, { touchOnly: !!n.touchOnly, game: st.game, since, hostIdx });
        pr.buttons.push({ path: n.path, sig: (n.sig || '').slice(0, 60), touchOnly: !!n.touchOnly, reaction: r.kind, why: r.why, ms: r.ms, diag: r.diag ? r.diag.say : undefined });
        if (r.threw) warn('popup button ' + n.path + st.where + ' reacted (' + r.kind + ') but a callback threw: ' + r.threw);
        if (r.kind === 'none') deadOrWarn(n, ' (popup of ' + p.opener + st.where + ')', r);
        else if (r.kind === 'untestable') warn('popup button ' + n.path + st.where + ': ' + r.why + say(r));
        else if (r.kind === 'ad') st.adEntries.push({ taps: st.prefix.concat([p.opener, n.path]), sig: (n.sig || '').slice(0, 60) });
        else if (r.kind === 'screen' && isCloser(n) && !st.checked.has(p.key + '>' + n.path)) {
          st.checked.add(p.key + '>' + n.path);
          await afterClose(st, { opener: p.opener, closer: n.path, popupPaths: p.buttons.map((x) => x.path), other: null, since, hostIdx });
        }
      }
    }
  }

  let h = await fresh(page, 3000);
  if (!h.ok) {
    if (h.fps != null && h.fps < G.MIN_FPS) add('invalid_run', 'the page ran at ' + h.fps + ' fps (< ' + G.MIN_FPS + '); the Ego tab was throttled, re-run with its window visible');
    else add('home', 'home screen not reached');
  } else {
    rep.homeScene = h.scene;
    const home0 = await snap(page);
    const all = R.sweepButtons(home0, DEV).filter((n) => !(SKIP && (SKIP.test(n.path) || SKIP.test(n.sig || ''))));
    rep.homeButtonCount = all.length;
    await G.shot(page, path.join(C.evidenceDir, 'sweep-home.png'));
    const home = { name: 'home', where: ' (home)', game: false, base: home0, rows: rep.home, popups: rep.popups, adEntries: rep.adEntries, prefix: [],
      buttons: all.sort((a, b) => a.box.y0 - b.box.y0 || a.box.x0 - b.box.x0).slice(0, MAX_HOME), popupsTodo: [], checked: new Set(),
      deadline: T0 + BUDGET, maxPopup: MAX_POPUP,
      reload: async () => (h = await fresh(page, 1500)).ok, reloadFailed: () => add('home', 'home screen not reached on reload') };
    await sweepStage(home);
    await sweepPopups(home);

    // W93 (3): the running level
    if (!A.play) rep.notRun.push('in-game sweep: the adapter has no "play" (the startup suite\'s PLAY locator), so the level was not entered');
    else {
      const G0 = Date.now();
      const g = rep.game = { entered: false, rows: [], popups: [], adEntries: [], ms: 0 };
      const enter = async () => { const hh = await fresh(page, 1500); if (!hh.ok) return { ok: false, why: 'home screen not reached on reload' }; return enterGame(page); };
      const e = await enter();
      if (!e.ok) { g.why = e.why; rep.notRun.push('in-game sweep: ' + e.why); }
      else {
        g.entered = true;
        const game0 = await snap(page);
        await G.shot(page, path.join(C.evidenceDir, 'sweep-game.png')).catch(() => {});
        const gb = R.sweepButtons(game0, DEV).filter((n) => !(SKIP && (SKIP.test(n.path) || SKIP.test(n.sig || '')))
          && !(game0.scene === home0.scene && home0.m[n.path]));   // same scene: a button the home sweep already tapped (uuids differ between loads)
        g.buttonCount = gb.length;
        const st = { name: 'in-game', where: ' (in game)', game: true, base: game0, rows: g.rows, popups: g.popups, adEntries: g.adEntries, prefix: ['<play>'],
          buttons: gb.sort((a, b) => a.box.y0 - b.box.y0 || a.box.x0 - b.box.x0).slice(0, MAX_GAME), popupsTodo: [], checked: new Set(),
          deadline: G0 + GAME_BUDGET, maxPopup: MAX_GAME_POPUP,
          reload: async () => (await enter()).ok, reloadFailed: () => warn('in-game sweep stopped: the level could not be entered again') };
        await sweepStage(st);
        await sweepPopups(st);
      }
      g.ms = Date.now() - G0;
    }
  }
  rep.ms = Date.now() - T0;
  for (const r of rep.home) delete r.after;
  for (const f of rep.findings) f.level = R.level(f.code, { engine: ENGINE, policy: POLICY });
  for (const n of rep.notRun) out.warn('button_sweep not run: ' + n);
  for (const w of rep.warnings) out.warn('button_sweep: ' + w);
  for (const code of ['home', 'invalid_run', 'dead_button', 'blocked_after_close', 'popup_layout', 'covered_3d']) {
    const fs2 = rep.findings.filter((f) => f.code === code);
    if ((code === 'home' || code === 'invalid_run') && !fs2.length) continue;
    const blocks = fs2.filter((f) => f.level === 'block');
    for (const f of fs2.filter((f) => f.level === 'warn')) out.warn('button_sweep ' + code + ': ' + f.msg + (POLICY === 'legacy' ? ' [legacy game: warning]' : ' [Cocos 3.x: warning, only the startup download blocks]'));
    out.add(code, blocks.length === 0, blocks.length ? blocks.map((f) => f.msg).slice(0, 8) : (fs2.length ? 'warnings only' : null));
  }
  // nothing tapped although the home showed buttons = the sweep did not run (fail closed on a new 2.x game)
  const swept = rep.home.length > 0 || rep.homeButtonCount === 0;
  if (!swept || rep.homeButtonCount === 0) out.warn('button_sweep: ' + (rep.homeButtonCount === 0 ? 'no home button found to tap' : 'no home button was tapped'));
  out.add('swept', swept || R.level('home', { engine: ENGINE, policy: POLICY }) === 'warn',
    { homeButtons: rep.homeButtonCount, tapped: rep.home.length, popups: rep.popups.length, adEntries: rep.adEntries.map((a) => a.taps.join(' > ')),
      afterClose: rep.afterClose.length, game: rep.game ? { entered: rep.game.entered, buttons: rep.game.buttonCount, tapped: rep.game.rows.length, popups: rep.game.popups.length, ms: rep.game.ms, why: rep.game.why } : null,
      notRun: rep.notRun, ms: rep.ms });
  out.evidence.report = L.evidence('button_sweep.json', rep);
  out.evidence.adEntries = rep.adEntries;
  out.evidence.notRun = rep.notRun;
}, { w: 390, h: 844 });
