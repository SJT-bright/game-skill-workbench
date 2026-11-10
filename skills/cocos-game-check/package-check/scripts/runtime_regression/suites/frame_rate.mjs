// Explicit diagnostic for suspected frame-rate-dependent motion. Compare trajectories under simulated 60/120 Hz clocks.
// Per run: fresh save (reset=1), home (adapter.home, else the home scene), adapter.after_home_js, frame_rate.start
// (real actions, optional), frame_rate.prepare_js (optional), settle_ms, then at t0 frame_rate.drive_js (the operation,
// e.g. press RACE) and frame_rate.steps [{at_s, js}] at real times; frame_rate.track (JS body: the node or {x,y[,z]})
// sampled every 10 ms for run_s seconds. Comparison: runtime_regression/frame_rate_compare.mjs.
// Clock, setup and motion errors can invalidate this diagnostic. The trajectory threshold only flags a difference.
// adapter.frame_rate = {"n/a": "reason"} (no physics, nothing moves on its own): the runner passes it without a browser.
// Cocos 3.x: not covered (the sidecar's "uncovered"; the runner warns).
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const FR = await import(new URL('frame_rate_compare.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A, P = A.frame_rate || {};
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const RUN_S = +P.run_s || 5, RATES = [60, 120];

async function oneRun(page, hz, rep) {
  const run = { hz, steps: [] };
  rep.runs.push(run);
  const fail = (code, msg) => { run.setup = code; rep.findings.push({ code, msg: hz + ' Hz: ' + msg }); return run; };
  const add = await page.cdp('Page.addScriptToEvaluateOnNewDocument', { source: FR.RAF_JS(hz) });
  try {
    await page.goto(L.url('reset=1&ad=complete' + (P.query ? '&' + P.query : '') + '&r=' + Date.now()));
    await L.keepFrames(page);
    const home = A.home ? await L.waitFor(page, A.home, C.bootTimeoutMs || 60000) : await G.waitHome(page, { homeScene: A.home_scene || null });
    run.homeMs = home.ms;
    if (!home.ok) return fail('home', 'home screen not reached in ' + Math.round(home.ms / 1000) + ' s');
    const clock = await page.evaluate(() => window.__fr ? { hz: window.__fr.hz, ticks: window.__fr.ticks } : null);
    if (!clock || clock.hz !== hz) return fail('clock', 'the display clock was not installed before the page scripts (got ' + JSON.stringify(clock) + ')');
    if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await G.sleep(400); }
    await G.sleep(1000);
    if (Array.isArray(P.start) && P.start.length) {
      const r = await G.runActions(page, P.start);
      run.start = r.log;
      if (!r.ok) return fail('start', 'frame_rate.start did not finish: ' + r.why);
    }
    if (P.prepare_js) {
      run.prepare = await L.adapterCall(page, P.prepare_js).catch((e) => ({ adapterError: String(e) }));
      if (run.prepare && run.prepare.adapterError) return fail('prepare', 'frame_rate.prepare_js threw: ' + run.prepare.adapterError);
    }
    await G.sleep(+P.settle_ms || 1000);
    const cfg = { track: P.track, drive_js: P.drive_js, steps: P.steps || [], run_s: RUN_S };
    const ok = await page.evaluate(FR.SAMPLER_JS + '(' + JSON.stringify(cfg) + ')').catch((e) => 'threw: ' + e);
    if (ok !== true) return fail('drive', 'the sampler did not start: ' + JSON.stringify(ok).slice(0, 200));
    await G.sleep(RUN_S * 1000 + 300);
    let W = null;
    for (let i = 0; i < 20 && !(W && W.done); i++) { W = await page.evaluate(() => window.__fps && Object.assign({}, window.__fps, { iv: undefined })); if (!(W && W.done)) await G.sleep(250); }
    if (!W || !W.done) return fail('drive', 'the sampler did not finish');
    Object.assign(run, { samples: W.s, drive: W.drive === undefined ? null : W.drive, error: W.err, seconds: W.t1 / 1000,
                         ticks: W.k1 - W.k0, frames: W.f1 == null || W.f0 == null ? null : W.f1 - W.f0 });
    run.png = await G.shot(page, path.join(C.evidenceDir, 'frame_rate-' + hz + 'hz.png')).catch(() => null);
    if (W.err) return fail('drive', W.err);
    if (!W.s.some((r) => r[1] != null)) return fail('track', 'frame_rate.track gave no position (null every sample)');
    return run;
  } finally {
    if (add && add.identifier) await page.cdp('Page.removeScriptToEvaluateOnNewDocument', { identifier: add.identifier }).catch(() => null);
  }
}

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'frame_rate', policy: POLICY, adapter: P, runs: [], findings: [], warnings: [] };
  for (const hz of RATES) await oneRun(page, hz, rep);
  const setup = rep.findings.filter((f) => ['home', 'clock', 'start', 'prepare', 'drive', 'track'].includes(f.code));
  for (const run of rep.runs) {
    if (run.setup) continue;
    const c = FR.clockCheck(run);
    out.add('clock_' + run.hz, !c.invalid.length, c.invalid.length ? c.invalid : { hz: run.hz, seconds: Math.round(run.seconds * 100) / 100, ticks: run.ticks, frames: run.frames });
    for (const w of c.warnings) out.warn('frame_rate: ' + w);
  }
  if (setup.length) {
    // the operation could not run: a new game must fix the adapter; a legacy game only warns
    if (POLICY === 'legacy') for (const f of setup) out.warn('frame_rate ' + f.code + ': ' + f.msg + ' [legacy game: warning]');
    out.add('setup', POLICY === 'legacy', setup.map((f) => f.msg).slice(0, 4));
  } else {
    const [slow, fast] = rep.runs;
    const v = FR.compare(slow, fast, { run_s: RUN_S, min_move: P.min_move, align: P.align });
    rep.compare = v;
    const detail = v.code === 'no_motion' ? v.why : { worst: v.worst, start_ms: v.start_ms, checkpoints: v.checkpoints.length };
    if (v.code === 'no_motion') {
      if (POLICY === 'legacy') out.warn('frame_rate no_motion: ' + v.why + ' [legacy game: warning]');
      out.add('no_motion', POLICY === 'legacy', detail);
    } else {
      if (!v.passed) out.warn('frame_rate: displacement differed by ' + Math.round(v.worst.rel * 1000) / 10 +
        ' % at ' + v.worst.t_s + ' s under simulated 60/120 Hz clocks. Verify the affected gameplay at normal device settings.');
      out.add('same_motion', true, { ...detail, trajectory_differs: !v.passed });
    }
  }
  out.evidence.report = L.evidence('frame_rate.json', rep);
  out.evidence.runs = rep.runs.map((r) => ({ hz: r.hz, seconds: r.seconds, ticks: r.ticks, frames: r.frames, samples: (r.samples || []).length, setup: r.setup || null, png: r.png || null }));
}, { w: 390, h: 844 });
