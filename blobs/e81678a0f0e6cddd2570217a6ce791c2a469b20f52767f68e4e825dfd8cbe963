// layout_state (v7.8, 总表 B30 D + S8 补 + U1): the 全民飞车门禁 prototype layout_state_gate.mjs as a runtime suite.
// Passes = device (iphone14 with its 34 pt home indicator, se) x capsule unit (pt, px) x adapter state (layout_states;
// default: the new-player home). In every pass, with the director paused (logic frozen, rendering on), every visible
// button and text label is checked:
//   covered_3d  >= 30 % of a button (>= 50 % of a label) painted over by 3D content (pixel test, gates.OCCLUSION_JS)
//   offscreen   a button cut by the screen edge          capsule   a button / label on the TikTok capsule (se: warning)
//   safe_area   a button centre in the bottom home-indicator band (only reaching into it: warning)
//   unit_shift  a still button / label moves > 4 pt between the pt and the px pass of the same device and state
//   state       an adapter state could not be reached (its actions / expect_visible failed)
// Home rules (first state, iphone14, pt), by CFG.board: remake = settings_pos + bottom_row + platform_entries,
// localize = platform_entries only (原首页按钮不动), unknown board = not checked (warning).
// Startup download (first pass): main package + every subpackage requested before the home scene starts loading
// (EVENT_BEFORE_SCENE_LOADING, host beacons): startup_size <= 10 MiB, startup_audio = no sound in it.
// Block vs warning: layout_rules.level (new game blocks; legacy warns; Cocos 3.x blocks only on the startup download).
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const R = await import(new URL('layout_rules.mjs', globalThis.CFG.lib).href);
const fs = await import('node:fs/promises');
const path = await import('node:path');
const C = L.C, A = L.A;
const ENGINE = C.engine || '2.x', POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const BOARD = C.board || null;
const CODES = ['home', 'startup_size', 'startup_audio', 'state', 'offscreen', 'capsule', 'safe_area', 'covered_3d', 'unit_shift',
  'settings_pos', 'bottom_row', 'platform_entries', 'invalid_run'];

async function dirBytes(dir) {
  let total = 0, audio = 0;
  const walk = async (d) => {
    for (const e of await fs.readdir(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) await walk(p);
      else { const s = await fs.stat(p); total += s.size; if (R.AUDIO.test(e.name)) audio += s.size; }
    }
  };
  await walk(dir);
  return { total, audio };
}
async function startupSize(pkgDir, names) {
  const gj = JSON.parse(await fs.readFile(path.join(pkgDir, 'game.json'), 'utf8'));
  const subs = (gj.subpackages || gj.subPackages || []).map((s) => ({ name: s.name, root: String(s.root || '').replace(/\/$/, '') }));
  const all = await dirBytes(pkgDir), per = {};
  for (const s of subs) per[s.name] = await dirBytes(path.join(pkgDir, s.root)).catch(() => ({ total: 0, audio: 0 }));
  return R.startupBytes(all, subs, per, names);
}
const kitEntries = (page) => G.evalJs(page, `var out = []; walkScene(function (n) { var c = n.getComponent('HomeGrowthEntries');
  if (c) { if (c.shortcutNode) out.push(pathOf(c.shortcutNode)); if (c.profileNode) out.push(pathOf(c.profileNode)); } }); return out;`).catch(() => []);
const hookScenes = (page) => page.evaluate(() => {
  const cc = window.cc;
  if (!cc || !cc.director || !cc.Director || !window.__hostState) return false;
  if (!window.__sceneLog) {
    window.__sceneLog = [];
    cc.director.on(cc.Director.EVENT_BEFORE_SCENE_LOADING, (name) => window.__sceneLog.push({ loading: name, t: window.__hostState().t }));
    cc.director.on(cc.Director.EVENT_AFTER_SCENE_LAUNCH, (s) => window.__sceneLog.push({ launched: s && s.name, t: window.__hostState().t }));
  }
  return true;
}).catch(() => false);

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'layout_state', engine: ENGINE, policy: POLICY, board: BOARD, passes: [], findings: [], startup: null, homeRules: null };
  const add = (f, key) => rep.findings.push(Object.assign({ key }, f));
  const states = Array.isArray(A.layout_states) && A.layout_states.length ? A.layout_states : [{ name: 'home' }];
  const devices = ['iphone14', 'se'], units = ['pt', 'px'];
  const P = {};
  let startupDone = false;
  for (const dev of devices) for (const st of states) for (const unit of units) {
    const key = dev + '/' + st.name + '/' + unit, d = G.DEVICES[dev];
    const pass = { key };
    rep.passes.push(pass);
    await G.openGame(page, dev, 'capsule=' + unit + '&ad=complete' + (A.layout_query ? '&' + A.layout_query : ''));
    for (let i = 0; i < 300 && !(await hookScenes(page)); i++) await G.sleep(40);
    const home = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
    pass.home = { ok: home.ok, ms: home.ms, scene: home.scene, fps: home.fps };
    if (!home.ok) {
      if (home.fps != null && home.fps < G.MIN_FPS) add({ code: 'invalid_run', msg: key + ': the page ran at ' + home.fps + ' fps (< ' + G.MIN_FPS + '); the Ego tab was throttled, re-run with its window visible' }, key);
      else add({ code: 'home', msg: key + ': home screen not reached in ' + Math.round(home.ms / 1000) + ' s (last scene ' + (home.last && home.last.scene) + ')' }, key);
      continue;
    }
    const homeScene = A.home_scene || home.scene;
    if (!startupDone) {
      startupDone = true;
      const lg = await page.evaluate(() => ({
        subs: (window.__hostLog || []).filter((r) => r.kind === 'subpackage').map((r) => ({ t: r.t, name: r.data && r.data.name })),
        scenes: (window.__sceneLog || []).concat((window.__hostLog || []).filter((r) => r.kind === 'scene-loading' || r.kind === 'scene-launch')
          .map((r) => (r.kind === 'scene-loading' ? { loading: r.data, t: r.t, from: 'host' } : { launched: r.data, t: r.t, from: 'host' }))) }));
      const { cut, names } = R.startupCut(lg.scenes, lg.subs, homeScene);
      const sz = await startupSize(C.package, names);
      rep.startup = Object.assign({ homeScene, cutoff: cut || 'no scene event: every subpackage requested before home counted', requestedBeforeHome: names }, sz);
      for (const f of R.startupFindings(sz, names)) add(f, key);
      rep.engineVersion = (await G.engineMajor(page)).version;
    }
    if (A.after_home_js) { pass.afterHome = await G.evalJs(page, A.after_home_js).catch((e) => 'threw: ' + e); await G.sleep(400); }
    if (st.actions) {
      const r = await G.runActions(page, st.actions);
      pass.actions = r.log;
      if (!r.ok) { add({ code: 'state', msg: key + ': state not reached: ' + r.why }, key); continue; }
    }
    let missing = null;
    for (const p of st.expect_visible || []) if (!(await G.nodeCentre(page, p))) { missing = p; break; }
    if (missing) { add({ code: 'state', msg: key + ': state not reached, ' + missing + ' not visible' }, key); continue; }
    await G.sleep(st.settle_ms || 1200);
    // two unpaused samples: nodes that move by themselves are left out of the pt / px comparison
    const a = await G.visibleNodes(page);
    await G.sleep(700);
    const b = await G.visibleNodes(page);
    const prev = Object.fromEntries(a.nodes.map((n) => [n.path, n.box]));
    const moving = new Set(b.nodes.filter((n) => { const q = prev[n.path]; return !q || Math.abs(q.x0 - n.box.x0) > 1 || Math.abs(q.y0 - n.box.y0) > 1; }).map((n) => n.path));
    await page.evaluate(() => window.cc.director.pause());
    await G.sleep(150);
    const snap = await G.visibleNodes(page);
    const nodes = snap.nodes.map((n) => Object.assign({}, n, { moving: moving.has(n.path) }));
    pass.nodes = nodes;
    for (const f of R.passFindings(nodes, d)) add(Object.assign({}, f, { msg: key + ': ' + f.msg }), key);
    const cands = nodes.filter((n) => (n.kind === 'button' && !n.layer) || (n.kind === 'label' && n.text && String(n.text).trim())).map((n) => ({ path: n.path, kind: n.kind, box: n.box }));
    const occ = await G.occlusion(page, cands);
    pass.occlusion = occ.error ? { error: occ.error } : { meshes: occ.meshes, tested: (occ.res || []).filter((r) => r.covered != null).length };
    for (const x of G.coveredOf(occ)) add({ code: 'covered_3d', path: x.path, msg: key + ': ' + x.kind + ' ' + x.path + ' is ' + (x.covered * 100).toFixed(0) + ' % painted over by 3D content (visible ' + x.visible + ', ' + x.footprint + ' px)' }, key);
    if (occ.error) out.warn('layout_state ' + key + ': 3D occlusion not measured: ' + occ.error);
    pass.png = await G.shot(page, path.join(C.evidenceDir, 'layout-' + dev + '-' + st.name + '-' + unit + '.png'));
    await page.evaluate(() => window.cc.director.resume()).catch(() => {});
    if (dev === devices[0] && st === states[0] && unit === 'pt') {
      if (BOARD === 'remake' || BOARD === 'localize') {
        const hr = R.homeRules(nodes, d, BOARD, { settings: A.settings, platform: A.platform_entries, kitEntries: await kitEntries(page) });
        rep.homeRules = hr.info;
        for (const f of hr.findings) add(f, key);
      } else out.warn('layout_state: home rules not checked: board unknown (the writers pass remake / localize; runtime_regression.py run --board)');
    }
    P[key] = pass;
  }
  for (const dev of devices) for (const st of states) {
    const pt = P[dev + '/' + st.name + '/pt'], px = P[dev + '/' + st.name + '/px'];
    if (!pt || !px) continue;
    const shift = R.unitShift(pt.nodes, px.nodes);
    pt.unitShift = shift;
    if (shift.length) add({ code: 'unit_shift', msg: dev + '/' + st.name + ': ' + shift.length + ' node(s) move when the capsule rect comes in pixels instead of points, e.g. ' + shift.slice(0, 3).map((s) => s.path.split('/').slice(-2).join('/') + ' dy=' + s.dy).join(', ') + ' (read the capsule with platform-kit CapsuleLayout.js)' }, dev + '/' + st.name);
  }
  if (!rep.startup) add({ code: 'startup_size', msg: 'startup download not measured: the home screen was never reached' }, 'startup');
  for (const p of rep.passes) delete p.nodes;
  // verdict: one case per check; a finding blocks unless the rules say warning (legacy game, Cocos 3.x, SE capsule, edge of band)
  for (const f of rep.findings) f.level = f.warnOnly ? 'warn' : R.level(f.code, { engine: ENGINE, policy: POLICY });
  const ran = new Set(['home', 'startup_size', 'startup_audio', 'offscreen', 'capsule', 'safe_area', 'covered_3d', 'unit_shift'].concat(
    states.some((s) => s.actions || s.expect_visible) ? ['state'] : [],
    BOARD === 'remake' ? ['settings_pos', 'bottom_row', 'platform_entries'] : BOARD === 'localize' ? ['platform_entries'] : []));
  for (const code of CODES) {
    const fs2 = rep.findings.filter((f) => f.code === code);
    if (!ran.has(code) && !fs2.length) continue;
    const blocks = fs2.filter((f) => f.level === 'block');
    for (const f of fs2.filter((f) => f.level === 'warn')) out.warn('layout_state ' + code + ': ' + f.msg + (POLICY === 'legacy' ? ' [legacy game: warning]' : ENGINE === '3.x' && !f.warnOnly ? ' [Cocos 3.x: warning, only the startup download blocks]' : ''));
    out.add(code, blocks.length === 0, blocks.length ? blocks.map((f) => f.msg).slice(0, 6) : (fs2.length ? 'warnings only' : null));
  }
  out.evidence.report = L.evidence('layout_state.json', rep);
  out.evidence.startupMiB = rep.startup && rep.startup.startupMiB;
  out.evidence.startup = rep.startup && { MiB: rep.startup.startupMiB, audioBytes: rep.startup.startupAudioBytes, beforeHome: rep.startup.requestedBeforeHome, cutoff: rep.startup.cutoff };
}, { w: 390, h: 844 });
