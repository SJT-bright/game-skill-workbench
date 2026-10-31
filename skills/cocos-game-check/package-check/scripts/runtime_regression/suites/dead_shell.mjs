// VIS_DEAD_SHELL suite (v7.8, 总表 E1 补). Contract: ../README.md.
// A retired cross-promo / ranking / more-games widget whose code was removed but whose node is still drawn: Holly's
// Hay Hop v1 swapped the WeChat WxGameBox (it set its nodes inactive when no config came) for an EmptyGameBox that
// did nothing, so gameView/info/gameBox kept showing a "Try It" frame under the in-game settings gear. H14_cross_promo
// reads code only and passed. Prototype: 启动包工坊/！Skill更新/互推空框检查_20261030/dead_shell_probe.mjs.
//
// Scans the home page, then the game after a REAL tap on adapter.play, then (adapter.enter_level given) after that
// call from a fresh start. A hit needs BOTH: the player can see it (activeInHierarchy, opacity > 0 down the parent
// chain, an enabled Sprite with a spriteFrame or an enabled non-empty Label, on screen, wider and taller than 4 px)
// AND the node's own name or sprite frame name is a retired slot (SLOT; item_bg only inside one). New game: a hit fails
// the case. Legacy game (CFG.policy 'legacy', frozen list): the case passes and each hit is a warning.
const L = await import(globalThis.CFG.lib);
const { C, A, sleep } = L;
const path = await import('node:path');

// Saul 2026-10-31: places inside one match against local bots are allowed (68 小熊拳击 names its score tags rank), so
// rank / ranking are not slots any more; the friend board (friendRank, phb = 排行榜) still is.
// Retired slot names (总表 E1 补), matched against the WHOLE node name or sprite frame name, case-insensitive. The node itself
// must match: a descendant of a slot-named node does not count by inheritance (Meteor Blaster r9 names its playfield
// Canvas/gameBox, so every brick would have matched). WEAK names are generic (Finger Mahjong v56 draws its coin and energy
// bars with an item_bg frame): they count only inside a node whose own name or frame is a slot.
const SLOT = '^(gameBox|leftGameBox|leftGameBtn|gameIcon|popBox|fullScreenBox|leftBox|moreGame|moreGames|more|bannerAdv|banner_border|friendRank|phb|jxyx|hy|tj)$';
const WEAK = '^(item_bg)$';
const LEGACY = C.policy === 'legacy';
const SETTLE_MS = 3000;
const FIX = 'set the node inactive (active = false); when a WxGameBox-like class was replaced by an empty one, its ' +
  'init(nodes) must set the nodes it is given inactive';

// In the page (2.x): every node under the scene; hits + slot nodes that were not hits (and why), for evidence.
const scan = (page) => L.ev(page, ([src, weakSrc]) => {
  if (!(window.cc && cc.director && cc.director.getScene())) return { error: 'no scene' };
  const SLOT = new RegExp(src, 'i'), WEAK = new RegExp(weakSrc, 'i');
  const vs = cc.view.getVisibleSize(), vo = cc.view.getVisibleOrigin();
  const hits = [], hidden = [];
  let nodes = 0;
  const sprite = n => { const s = n.getComponent(cc.Sprite); return s && s.enabled && s.spriteFrame ? s : null; };
  const frameName = n => { const s = n.getComponent(cc.Sprite); return s && s.spriteFrame ? String(s.spriteFrame.name || '') : ''; };
  const drawn = n => { if (sprite(n)) return true; const l = n.getComponent(cc.Label); return !!(l && l.enabled && typeof l.string === 'string' && l.string.trim()); };
  const pathOf = n => { const a = []; while (n && n.parent) { a.unshift(n.name); n = n.parent; } return a.join('/'); };
  const walk = (n, slotAncestor, seen) => {
    nodes++;
    const frame = frameName(n);
    let slot = SLOT.test(n.name) ? n.name : (SLOT.test(frame) ? frame : null);
    if (!slot && slotAncestor && (WEAK.test(n.name) || WEAK.test(frame))) slot = WEAK.test(n.name) ? n.name : frame;
    const why = !n.activeInHierarchy ? 'inactive' : (!seen || n.opacity === 0) ? 'opacity 0' : null;
    if (slot) {
      let reason = why;
      let box = null;
      if (!reason && !drawn(n)) reason = 'draws nothing';
      if (!reason) {
        const b = n.getBoundingBoxToWorld();
        box = [Math.round(b.x - vo.x), Math.round(vs.height - (b.y + b.height - vo.y)), Math.round(b.width), Math.round(b.height)];
        if (!(b.width > 4 && b.height > 4)) reason = 'not larger than 4 px';
        else if (!(b.x + b.width > vo.x && b.x < vo.x + vs.width && b.y + b.height > vo.y && b.y < vo.y + vs.height)) reason = 'off screen';
      }
      const row = { path: pathOf(n), slot, frame, box };
      if (slotAncestor && slotAncestor !== slot) row.under = slotAncestor;
      if (reason) { if (hidden.length < 40) hidden.push(Object.assign(row, { reason })); }
      else hits.push(row);
    }
    (n.children || []).forEach(c => walk(c, slotAncestor || (SLOT.test(n.name) || SLOT.test(frame) ? slot : null), seen && n.opacity !== 0));
  };
  (cc.director.getScene().children || []).forEach(c => walk(c, null, true)); // not the Scene itself (engine error)
  return { hits, hidden, nodes, scene: cc.director.getScene().name };
}, [SLOT, WEAK]);

const isHome = async (page) => (await L.adapterCall(page, A.home).catch(() => false)) === true;

async function record(page, out, id, extra) {
  const s = await scan(page).catch(e => ({ error: String(e && e.message || e).slice(0, 300) }));
  let shot = null;
  try { shot = path.join(C.evidenceDir, `dead_shell-${id}.png`); await page.screenshot({ path: shot }); } catch (_) { shot = null; }
  const problems = (extra && extra.problems) || [];
  if (s.error) problems.push('scan failed: ' + s.error);
  const hits = s.hits || [];
  const text = hits.map(h => `${h.path} (slot ${h.slot}${h.frame ? ', sprite ' + h.frame : ''}, ${h.box[2]}x${h.box[3]} at ${h.box[0]},${h.box[1]})`);
  if (hits.length) {
    const msg = `VIS_DEAD_SHELL ${id}: retired cross-promo / ranking / more-games slot still visible: ${text.join('; ')}; ${FIX}`;
    if (LEGACY) out.warn(msg + ' (legacy game: warning)');
    else problems.push(msg);
  }
  // problems first: the runner's refusal quotes the first 300 characters of the detail
  out.add(id, problems.length === 0, Object.assign({ problems, level: hits.length ? (LEGACY ? 'warning' : 'block') : null, policy: C.policy || null,
    hits, hidden: s.hidden || [], nodes: s.nodes || 0, scene: s.scene || null, problems, screenshot: shot }, extra || {}, { problems }));
  console.log(JSON.stringify(out.cases[out.cases.length - 1]).slice(0, 400));
}

await L.suite(async ({ out, page }) => {
  out.evidence.slots = SLOT;
  out.evidence.policy = C.policy || null;
  out.evidence.policyReason = C.policyReason || null;
  // 1. home
  const b = await L.boot(page, 'reset=1');
  if (!b.ok) { out.add('home', false, { problems: [`home not reached within ${Math.round(b.ms / 1000)} s`], errors: b.errors }); return; }
  await sleep(SETTLE_MS);
  await record(page, out, 'home', { ms: b.ms });
  // 2. in game through the real PLAY button (the player's way in)
  if (!A.play && !A.enter_level) {
    out.add('in_game', false, { problems: ['adapter.play is missing: a locator for the home PLAY button (return the cc.Node, or CSS {x, y}); ' +
      'or adapter.enter_level (calls the game\'s real start method). Without one the in-game screen is not scanned'] });
  }
  if (A.play) {
    const p = await L.locate(page, A.play);
    const problems = [];
    let left = false;
    if (!p) problems.push('adapter.play found no PLAY button on the home page');
    else if (p.onCanvas === false) problems.push(`adapter.play points outside the game canvas (${Math.round(p.x)}, ${Math.round(p.y)}): a locate error in the adapter or the tool`);
    else {
      await L.touchTap(page, p.x, p.y);
      for (let i = 0; i < 20 && !left; i++) {
        await sleep(500);
        left = !(await isHome(page)) || (A.in_level ? (await L.adapterCall(page, A.in_level).catch(() => false)) === true : false);
      }
      if (!left) problems.push(`PLAY did not leave the home page after a real tap at (${Math.round(p.x)}, ${Math.round(p.y)}): the in-game screen was not scanned`);
    }
    if (left) await sleep(SETTLE_MS + 1500);
    await record(page, out, 'after_play', { tap: p, left, problems });
  }
  // 3. in game through adapter.enter_level (a level directly, when PLAY opens a map or a menu first)
  if (A.enter_level) {
    const b2 = await L.boot(page, 'reset=1');
    const problems = [];
    let r = null;
    if (!b2.ok) problems.push('home not reached on the second start');
    else {
      await sleep(1500);
      r = await L.adapterCall(page, A.enter_level);
      if (r && r.adapterError) problems.push('adapter.enter_level threw: ' + r.adapterError);
      else await sleep(SETTLE_MS + 1500);
    }
    await record(page, out, 'enter_level', { result: r && typeof r === 'object' ? r : null, problems });
  }
  out.evidence.log = C.logFile;
}, { w: 393, h: 852, dpr: 3, touch: true });
