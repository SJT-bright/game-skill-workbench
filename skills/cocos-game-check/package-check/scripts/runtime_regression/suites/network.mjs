// Network log suite (D5 4.2). Contract: ../README.md.
// Boots the REAL package in the strict host (every external request is logged and blocked), stays on
// home, enters one level (adapter.enter_level) and plays it for level_timeout_s. Every external URL
// (tt.request, downloadFile, connectSocket, XHR, fetch, WebSocket, sendBeacon, image) is listed;
// hosts outside ../network-allowlist.json are a WARNING with the list (not a refusal in v7.5).
// Cases fail only when the log is incomplete: home not reached, or enter_level given but it threw.
const L = await import(globalThis.CFG.lib);
const { C, A, sleep } = L;
const fs = await import('node:fs');
const path = await import('node:path');
const { fileURLToPath } = await import('node:url');

const HERE = path.dirname(fileURLToPath(import.meta.url));
function allowlist() {
  try { return (JSON.parse(fs.readFileSync(path.join(HERE, '..', 'network-allowlist.json'), 'utf8')).domains || []).map(d => String(d).toLowerCase()); }
  catch (_) { return []; }
}
const ALLOW = allowlist();
const hostOf = (u) => { try { return new URL(u, 'http://127.0.0.1/').hostname.toLowerCase(); } catch (_) { return ''; } };
const allowed = (h) => ALLOW.some(d => h === d || h.endsWith('.' + d));

// Host log rows written by server.py: page beacons {kind:'net-<kind>', data:{url, t}} survive reloads.
function logged() {
  let rows = [];
  try { rows = fs.readFileSync(C.logFile, 'utf8').split('\n').filter(Boolean).map(l => { try { return JSON.parse(l); } catch (_) { return null; } }).filter(Boolean); } catch (_) {}
  return rows.filter(r => /^net-/.test(String(r.kind || ''))).map(r => {
    const d = r.data || r;
    return { kind: String(r.kind).slice(4), url: String(d.url || ''), phase: r.phase || null };
  }).filter(r => r.url);
}

await L.suite(async ({ out, page }) => {
  const phases = [];
  const mark = async (name) => { const n = await L.ev(page, () => (window.__net || []).length).catch(() => null); phases.push({ phase: name, netCount: n }); };
  const b = await L.boot(page, 'reset=1');
  await mark('startup');
  out.add('home_reached', b.ok, { ms: b.ms, errors: b.errors });
  if (!b.ok) { out.evidence.log = C.logFile; return; }
  await sleep(5000); // idle on home: analytics / cross-promo calls usually fire here
  await mark('home');
  if (A.enter_level) {
    const r = await L.adapterCall(page, A.enter_level);
    const err = r && r.adapterError;
    out.add('level_entered', !err, { result: err ? r : (typeof r === 'object' ? null : r) });
    await sleep(1000 * (A.level_timeout_s || 20));
    await mark('level');
  } else {
    out.warn('network: adapter has no enter_level; only startup and home were logged');
  }
  const inPage = await L.ev(page, () => (window.__net || []).slice(0, 500)).catch(() => []);
  const all = inPage.concat(logged());
  const seen = new Map();
  for (const r of all) {
    const h = hostOf(r.url);
    if (!h || h === '127.0.0.1' || h === 'localhost') continue;
    const k = r.kind + ' ' + r.url;
    if (!seen.has(k)) seen.set(k, { kind: r.kind, url: r.url, host: h, allowed: allowed(h), t: r.t });
  }
  const urls = Array.from(seen.values());
  const unlisted = urls.filter(u => !u.allowed);
  const hosts = Array.from(new Set(unlisted.map(u => u.host))).sort();
  if (unlisted.length) out.warn('network: ' + unlisted.length + ' request(s) to host(s) not in network-allowlist.json: ' + hosts.join(', '));
  out.add('network_logged', true, { allowlist: ALLOW, total: urls.length, unlistedHosts: hosts, urls: urls.slice(0, 100), phases });
  out.evidence.network = L.evidence('network-urls.json', { allowlist: ALLOW, urls, phases });
  out.evidence.log = C.logFile;
}, { w: 393, h: 852, dpr: 3, touch: true });
