// Cocos 3.x startup suite (D3, LunasJade). Runs in host3x/ (game.js inside a separate GameGlobal).
// Cases: first frame on a 1.5 MB/s cold start (the first WebGL draw of the package itself, not a
// web-mobile splash), WebP decoded slower than the engine's 500 ms check (home must not be blank),
// image objects that ignore onload/onerror properties (the splash must not wait forever).
// Every case records the page rAF rate; a run below 30 fps is INVALID and refuses (D3 problem 4).
const L = await import(globalThis.CFG.lib);
const { C, A, sleep } = L;
const path = await import('node:path');

const FIRST_FRAME_MS = (A.first_frame_ms || 5000);
const SIZE = 'w=393&h=852&dpr=3';
// id, query, limitMs, checks
const CASES = [
  ['cold_1500kbps_first_frame', 'fresh=1&bps=1500000', 120000, { firstFrame: true }],
  ['webp_slow', 'fresh=1&fault=webp_slow', 90000, { sprites: true }],
  ['img_events_only', 'fresh=1&fault=img_events_only', 90000, { firstFrame: true }],
];

async function runCase(page, out, [id, query, limitMs, want]) {
  await page.goto('about:blank');
  await page.goto(L.url([SIZE, 'store=' + id, query].join('&')));
  await L.keepFrames(page);
  const t0 = Date.now(), fpsSamples = [];
  let home = false, st = null;
  while (Date.now() - t0 < limitMs) {
    await sleep(1000);
    const f = await L.fps(page).catch(() => null);
    if (typeof f === 'number') fpsSamples.push(f);
    try { home = (await L.adapterCall(page, A.home)) === true; } catch (_) { home = false; }
    if (home) { await sleep(1500); break; }
  }
  st = await L.hostState(page).catch(() => null);
  const sprites = await L.ev(page, () => window.__H && __H.sprites && __H.sprites()).catch(() => null);
  const errs = await L.errors(page).catch(() => []);
  const sorted = fpsSamples.slice().sort((a, b) => a - b);
  const medianFps = sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
  const firstDraw = st && st.marks ? st.marks.firstDraw : undefined;
  const problems = [];
  if (medianFps === null || medianFps < L.MIN_FPS) problems.push(`run invalid: page ran at ${medianFps} fps (< ${L.MIN_FPS}); timing cannot be used, re-run with the window visible`);
  if (!home) problems.push(`home not reached within ${Math.round(limitMs / 1000)} s`);
  if (want.firstFrame) {
    if (firstDraw === undefined) problems.push('no first frame (the package never drew)');
    else if (firstDraw > FIRST_FRAME_MS) problems.push(`first frame at ${(firstDraw / 1000).toFixed(1)} s (limit ${FIRST_FRAME_MS / 1000} s)`);
  }
  if (want.sprites && home && !(sprites && sprites.total > 0 && sprites.textured === sprites.total)) problems.push(`home is blank: ${sprites ? sprites.textured + '/' + sprites.total : 'no'} sprites have a texture (webp=${st && st.webp})`);
  let shot = null;
  try { shot = path.join(C.evidenceDir, `startup3x-${id}.png`); await page.screenshot({ path: shot }); } catch (_) { shot = null; }
  out.add(id, problems.length === 0, { query, home, ms: Date.now() - t0, firstDrawMs: firstDraw === undefined ? null : firstDraw,
    sprites, webp: st && st.webp, medianFps, fpsSamples: fpsSamples.slice(0, 40), marks: st && st.marks, subpackages: st && st.sub,
    problems, errors: errs.slice(0, 4), screenshot: shot });
}

await L.suite(async ({ out, page }) => {
  try { await page.cdp('Page.stopScreencast', {}); } catch (_) {}
  for (const c of CASES) {
    await runCase(page, out, c);
    console.log(JSON.stringify(out.cases[out.cases.length - 1]).slice(0, 300));
  }
  try { await page.cdp('Page.stopScreencast', {}); } catch (_) {}
  out.evidence.log = C.logFile;
}, { w: 393, h: 852, dpr: 3 });
