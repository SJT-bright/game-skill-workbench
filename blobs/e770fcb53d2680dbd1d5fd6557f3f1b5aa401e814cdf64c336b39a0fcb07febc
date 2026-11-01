// image_stall (v7.9, 手机才出的五类问题 4): the home entries PLAY, add-to-desktop and profile revisit stay visible and
// tappable when their own pictures never arrive (射击高手 v81: on a real iPhone fs.access never answered for 4 files and
// the two platform entries were empty spots; v82 drew a text fallback). Until v7.9 a written rule only.
// 1st load (empty save, iPhone 14): home; for every entry (adapter.image_stall.entries, else the home buttons whose
// path / text / picture names add-to-desktop or profile revisit, plus adapter.play when image_stall.play is true) collect
// the picture files it and its
// active children draw. 2nd load: exactly those files stall (host imghang + accesshang, every attempt). Every entry must
// be active and on screen, drawn (a picture that still loaded, or visible non-empty text inside its box), and react to a
// real tap within 2.5 s (ad / toast / modal / mission call / new text / another page). New game: refuses; legacy: warns.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const B = A.image_stall || {};
const PLATFORM = /add.?to.?home|addtohome|shortcut|desktop|桌面|profile|revisit|回访|主页/i;

// entry node paths on the home page: adapter list, else PLAY (adapter.play) + platform entries found on screen
async function entryPaths(page) {
  if (Array.isArray(B.entries) && B.entries.length) return B.entries.map((p) => ({ path: p, kind: PLATFORM.test(p) ? 'platform' : 'entry' }));
  const out = [];
  // PLAY only when asked (image_stall.play: true): its picture is often a shared atlas / the home background, and
  // stalling it stalls the whole home page (射击高手 v86, which works on phones). The platform entries always.
  if (A.play && B.play === true) {
    const p = await G.evalJs(page, 'var r = (function(){' + A.play + '\n})(); var n = r && (r.node || r); return n && n.parent !== undefined ? pathOf(n) : null;').catch(() => null);
    if (p) out.push({ path: p, kind: 'play' });
  }
  const v = await G.visibleNodes(page).catch(() => ({ nodes: [] }));
  for (const n of v.nodes) if (n.kind === 'button' && PLATFORM.test(n.path + ' ' + (n.sig || ''))) out.push({ path: n.path.replace(/#[0-9]+$/, ''), kind: 'platform' });
  const seen = new Set();
  return out.filter((e) => !seen.has(e.path) && seen.add(e.path));
}

// picture files an entry and its active children draw (2.x texture nativeUrl / url, 3.x texture image url)
const filesOf = (page, p) => G.evalJs(page, 'var n = findNode(' + JSON.stringify(p) + '); if (!n) return null; var out = {};' +
  'var all = [n]; (function add(x){ x.children.forEach(function(c){ if (c.activeInHierarchy) { all.push(c); add(c); } }); })(n);' +
  'all.forEach(function (x) { var s = x.getComponent(cc.Sprite); var sf = s && s.spriteFrame; if (!sf) return; var t = sf.getTexture ? sf.getTexture() : sf.texture;' +
  ' var u = t && (t.nativeUrl || t.url || (t.image && t.image.url) || (t._image && t._image.nativeUrl) || ""); if (u) out[String(u).split("/").pop().split("?")[0]] = 1; });' +
  'return Object.keys(out);').catch(() => null);

// drawn: a sprite whose texture loaded, or a visible label with text, inside the entry
const drawn = (page, p) => G.evalJs(page, 'var n = findNode(' + JSON.stringify(p) + '); if (!n || !n.activeInHierarchy) return { on: false };' +
  'var pic = 0, text = []; var all = [n]; (function add(x){ x.children.forEach(function(c){ if (c.activeInHierarchy) { all.push(c); add(c); } }); })(n);' +
  'all.forEach(function (x) { if (!shownChain(x)) return; var s = x.getComponent(cc.Sprite); var sf = s && s.enabled !== false && s.spriteFrame; var t = sf && (sf.getTexture ? sf.getTexture() : sf.texture);' +
  ' if (t && (t.loaded || (t.width > 0 && t.height > 0))) pic++; var l = x.getComponent(cc.Label) || (cc.RichText && x.getComponent(cc.RichText)); if (l && l.enabled !== false && String(l.string || "").trim()) text.push(String(l.string).trim().slice(0, 20)); });' +
  'return { on: !!screenOf(n), pic: pic, text: text };').catch(() => ({ on: false }));

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'image_stall', policy: POLICY, entries: [] };
  if (B.entries && !(Array.isArray(B.entries) && B.entries.every((x) => typeof x === 'string'))) { out.add('adapter', POLICY === 'legacy', 'image_stall.entries must be a list of node paths'); return; }
  const q = 'capsule=pt&ad=complete&adms=600' + (B.query ? '&' + B.query : '');
  await G.openGame(page, 'iphone14', q);
  let h = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
  if (!h.ok) { const inv = h.fps != null && h.fps < G.MIN_FPS; out.add('home', !inv && POLICY === 'legacy', inv ? 'invalid run: the page ran at ' + h.fps + ' fps' : 'untestable: home not reached on a normal load'); return; }
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
  const entries = await entryPaths(page);
  if (!entries.length) { out.add('entries', POLICY === 'legacy', 'no PLAY / add-to-desktop / profile-revisit entry found on the home page (write image_stall.entries)'); return; }
  if (!entries.some((e) => e.kind === 'platform')) out.warn('image_stall: no add-to-desktop / profile-revisit entry found on the home page');
  const files = new Set();
  for (const e of entries) { e.files = (await filesOf(page, e.path)) || []; e.files.forEach((f) => files.add(f)); rep.entries.push(e); }
  if (!files.size) { out.add('files', true, 'the entries draw no picture files (text or vector only): nothing can stall'); out.evidence.report = L.evidence('image_stall.json', rep); return; }
  const list = [...files].map((f) => f.replace(/[|&#?]/g, '')).join('|');
  rep.stalled = [...files];
  // 2nd load: exactly these files never arrive (createImage never fires load / error; fs.access never answers)
  await G.openGame(page, 'iphone14', q + '&imghang=' + encodeURIComponent(list) + '&imghang_n=999&accesshang=' + encodeURIComponent(list));
  h = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null, timeout: 60000 });
  rep.home2 = h.ok;
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
  // the platform kit HomeGrowthEntries switches to its text 2 s after init when the icon did not load: wait for it
  await P.sleep(B.settle_ms || 4000);
  rep.png = await G.shot(page, path.join(C.evidenceDir, 'image-stall-home.png'));
  rep.hits = await page.evaluate(() => (window.__faults ? window.__faults.hits.slice(0, 20) : [])).catch(() => []);
  for (const e of entries) {
    let fail = null;
    const d = await drawn(page, e.path);
    e.after = d;
    if (!h.ok && !d.on) fail = 'with its pictures stalled the home page never came up (' + (h.fps != null && h.fps < G.MIN_FPS ? 'page ' + h.fps + ' fps: invalid run' : 'home not reached') + ')';
    else if (!d.on) fail = e.path + ' is not on screen when its pictures (' + e.files.join(', ') + ') never arrive';
    else if (!d.pic && !d.text.length) fail = e.path + ' is an empty spot when its pictures (' + e.files.join(', ') + ') never arrive: no picture, no text (give it a text fallback; 射击高手 v81)';
    if (!fail) {
      const c = await G.nodeCentre(page, e.path).catch(() => null);
      const idx = await P.hostIdx(page);
      const r = c ? await P.reaction(page, c.x, c.y, 2500) : null;
      const rows = await P.hostSince(page, idx);
      const mission = rows.find((x) => x.kind === 'mission' || x.kind === 'scene-launch' || x.kind === 'subpackage');
      e.reaction = r || (mission ? { kind: mission.kind, detail: mission.data } : null);
      if (!e.reaction) fail = 'tapped ' + e.path + ' with its pictures stalled: no reaction within 2.5 s';
      await page.goto('about:blank').catch(() => {});
      await G.openGame(page, 'iphone14', q + '&imghang=' + encodeURIComponent(list) + '&imghang_n=999&accesshang=' + encodeURIComponent(list));
      await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null, timeout: 60000 });
      if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
      await P.sleep(B.settle_ms || 4000);
    }
    e.result = fail ? 'fail' : 'pass';
    const blocks = !!fail && (POLICY === 'new' || /invalid run/.test(fail));
    if (fail && !blocks) out.warn('image_stall ' + e.path + ': ' + fail + ' [legacy game: warning]');
    out.add(e.path, !blocks, fail || ('drawn (' + (d.pic ? d.pic + ' picture(s)' : 'text ' + JSON.stringify(d.text.slice(0, 2))) + ') and reacts: ' + (e.reaction && e.reaction.kind)));
  }
  out.evidence.report = L.evidence('image_stall.json', rep);
}, { w: 390, h: 844 });
