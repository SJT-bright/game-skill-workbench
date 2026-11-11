// save_restart (v7.9, 手机才出的五类问题 3): what the player earned is still there after closing and reopening the game,
// with the storage of a real TikTok phone (tiktok-fixed-adaptation 第一部分第4条: a key never written reads back false,
// a number written as 0 / 1 reads back as a Boolean; host missing=false&numbool=01). Until v7.9 「过一关、领一次奖、买一件，
// 重开都还在」 was a written rule only (射击高手 v84 lost progress after a restart, 方块冲冲 BUGFIX4, CindersDragon v3.1).
// adapter.save_restart.steps = [{name, why, actions: [real steps], read_js: "return what the player sees"}]:
// fresh load (empty save) -> home -> every step: read_js before, the real actions, read_js after (a step that changes
// nothing proves nothing: adapter error) -> cold restart (the same host page reloaded WITHOUT reset=1, storage kept) ->
// home -> every read_js again must equal its value after the step. New game: refuses; legacy game: warnings.
// v7.9 手机检查补全 (Saul 11-04「全部补上」): 割草 v015, 人鱼 v14, 香肠 R17 each wrote ONE step (a platform or video
// reward); a lost level or a lost purchase was never tried. Every step now says what it earns, "kind":
//   level   progress from playing: a level won / unlocked, a best score       (every game with a PLAY button)
//   buy     an item bought or unlocked in a shop / skins page                  (when the home shows one)
//   claim   a reward claimed: platform entry, daily gift, video coins          (when the home shows one)
//   other   anything else worth keeping
// and a new game must have a step of each kind its home shows, or say why not: save_restart.none = {"buy": "why"}.
// Legacy game (「老游戏先不管」): kind is optional and nothing is required, as before.
const L = await import(globalThis.CFG.lib);
const G = await import(new URL('gates.mjs', globalThis.CFG.lib).href);
const P = await import(new URL('phone.mjs', globalThis.CFG.lib).href);
const path = await import('node:path');
const C = L.C, A = L.A;
const POLICY = C.policy === 'legacy' ? 'legacy' : 'new';
const B = A.save_restart || {};
// a key never written reads false; a stored 0 / 1 reads back false / true (host numbool=01; numbool=all, every number
// read back as a Boolean, is a diagnosis switch: it also breaks games whose phone build works)
const PHONE = 'missing=false&numbool=01';
const KINDS = ['level', 'buy', 'claim', 'other'];
// what the home shows: the button's path tail, or whole words of its picture / label names (layout_rules.sweepButtons
// sig; whole words so a decoration named "SkinArtwork" is not a skins page)
const SHOP = [/shop|store|商店|商城|mall|skin|皮肤|wardrobe|衣橱|outfit|装扮/i, /\b(shop|store|skins?|mall|wardrobe|outfits?)\b|商店|商城|皮肤|衣橱|装扮/i];
const CLAIM = [/gift|reward|daily|bonus|sign.?in|签到|奖励|礼包|福利|addcoin|add.?(to.?)?home|shortcut|profile|revisit|侧边栏|桌面/i,
  /\b(gift|rewards?|daily|bonus|free|sign.?in|shortcut|profile)\b|\badd.?(to.?)?home\b|签到|奖励|礼包|福利/i];

function problems(b) {
  const out = [];
  if (!b || typeof b !== 'object') return ['save_restart must be an object'];
  for (const k of Object.keys(b)) if (!['steps', 'query', 'note', 'none'].includes(k)) out.push('save_restart has unknown key ' + JSON.stringify(k));
  if (!Array.isArray(b.steps) || !b.steps.length) out.push('save_restart.steps must list what the player earns: win a level, claim a reward, buy an item');
  (b.steps || []).forEach((s, i) => {
    if (!s || typeof s.name !== 'string' || !s.name) out.push('save_restart.steps[' + i + '].name must be a string');
    if (!s || !Array.isArray(s.actions) || !s.actions.length) out.push('save_restart.steps[' + i + '].actions must be the real steps');
    if (!s || typeof s.read_js !== 'string' || !s.read_js.trim()) out.push('save_restart.steps[' + i + '].read_js must return what the player sees (level reached, coins, owned item ...)');
    if (s && 'kind' in s ? !KINDS.includes(s.kind) : POLICY === 'new') out.push('save_restart.steps[' + i + '].kind must be ' + KINDS.join(' / ') + ' (what the step earns)');
  });
  const names = (b.steps || []).map(step => step && step.name);
  if (new Set(names).size !== names.length) out.push('save_restart.steps names must be unique');
  const explicit = (b.steps || []).filter(step => step && 'requires' in step);
  if (explicit.length && explicit.length !== (b.steps || []).length)
    out.push('save_restart split steps must all declare requires (use [] for an independent step)');
  for (const step of explicit) {
    if (!Array.isArray(step.requires) || !step.requires.every(name => typeof name === 'string' && names.includes(name) && name !== step.name)
        || new Set(step.requires || []).size !== (step.requires || []).length)
      out.push('save_restart step ' + step.name + ' has invalid prerequisite names');
  }
  if (explicit.length && !out.length) {
    const visiting = new Set(), visited = new Set();
    const visit = name => {
      if (visiting.has(name)) throw new Error('save_restart prerequisites contain a cycle');
      if (visited.has(name)) return;
      visiting.add(name);
      const step = b.steps.find(item => item.name === name);
      step.requires.forEach(visit);
      visiting.delete(name);
      visited.add(name);
    };
    try { names.forEach(visit); } catch (error) { out.push(error.message); }
  }
  if ('none' in b && !(b.none && typeof b.none === 'object' && !Array.isArray(b.none) && Object.entries(b.none).every(([k, v]) => KINDS.includes(k) && typeof v === 'string' && v.trim())))
    out.push('save_restart.none must map a kind (' + KINDS.join(' / ') + ') to why the game has nothing of that kind');
  return out;
}

// The kinds a new game must keep, from what its home shows: [{kind, why}]
function needed(homeButtons) {
  const none = B.none || {};
  const has = new Set((B.steps || []).map((s) => s.kind));
  const hit = ([onPath, onSig]) => homeButtons.find((n) => onPath.test(String(n.path).replace(/#\d+$/, '').split('/').slice(-1)[0]) || onSig.test(n.sig || ''));
  const out = [];
  if (A.play || A.resume_play) out.push({ kind: 'level', why: 'the game has a level (adapter play / resume_play): win one, or reach a best score, and keep it' });
  const shop = hit(SHOP);
  if (shop) out.push({ kind: 'buy', why: 'the home shows ' + String(shop.path).replace(/#\d+$/, '') + ' (a shop / skins page): buy or unlock one item' });
  const claim = hit(CLAIM);
  if (claim) out.push({ kind: 'claim', why: 'the home shows ' + String(claim.path).replace(/#\d+$/, '') + ' (a reward entry): claim it once' });
  return out.filter((x) => !has.has(x.kind) && !none[x.kind]);
}

async function home(page) {
  const h = await G.waitHome(page, { homeScene: A.home_scene || null, adapterHome: A.home || null });
  if (!h.ok) return h.fps != null && h.fps < G.MIN_FPS ? 'invalid run: the page ran at ' + h.fps + ' fps, re-run with the Ego window visible' : 'untestable: home not reached';
  if (A.after_home_js) { await G.evalJs(page, A.after_home_js).catch(() => null); await P.sleep(400); }
  return null;
}

const safe = value => String(value).replace(/[^\w.-]+/g, '_').slice(0, 60);
const independentSteps = Array.isArray(B.steps) && B.steps.length > 0 &&
  B.steps.every(step => step && Array.isArray(step.requires));
const chosen = C.selection == null || C.selection.includes('@suite') ? null : new Set(C.selection);

function prerequisites(target) {
  const ordered = [], visited = new Set();
  const visit = name => {
    if (visited.has(name)) return;
    const step = B.steps.find(item => item.name === name);
    for (const dependency of step.requires || []) visit(dependency);
    visited.add(name);
    ordered.push(step);
  };
  visit(target.name);
  return ordered;
}

async function runRestart(page, out, steps, unit, rep, verifyKinds = false) {
  const q = 'capsule=pt&ad=complete&adms=600&' + PHONE + (B.query ? '&' + B.query : '');
  await G.openGame(page, 'iphone14', q);
  let fail = await home(page);
  if (!fail && verifyKinds && POLICY === 'new') {
    const miss = needed(P.buttonsOf(await P.snap(page)));
    rep.kinds = { steps: B.steps.map(step => step.kind), none: B.none || null, missing: miss };
    if (miss.length) {
      fail = 'save_restart.steps has no step of kind ' + miss.map(m => '"' + m.kind + '" (' + m.why + ')').join(', ') +
        '. Write the step (real actions, read_js) or save_restart.none.' + miss[0].kind + ' = "why the game has none"';
      out.add('kinds', false, fail);
      rep.result = 'fail';
      return;
    }
  }
  const done = [];
  for (const s of steps) {
    if (fail) break;
    const row = { name: s.name, kind: s.kind || null, why: s.why || null };
    rep.steps.push(row);
    row.before = await P.js(page, s.read_js);
    const r = await P.steps(page, s.actions);
    row.log = r.log.slice(-6);
    // v7.9 手机检查补全: a step that cannot even run under phone storage gets the same browser-storage comparison as a
    // step that earns nothing (甜点消消乐 R48 on a fresh install: the never-written save key read back false, the save
    // was judged damaged and the sign-in popup never opened)
    if (!r.ok) { fail = 'untestable: step ' + s.name + ': ' + r.why; row.stuck = true; row.why = r.why; break; }
    await P.sleep(s.settle_ms || 1200);
    row.after = await P.js(page, s.read_js);
    if (row.after && row.after.adapterError) { fail = 'untestable: step ' + s.name + ': read_js threw: ' + row.after.adapterError; break; }
    if (P.same(row.before, row.after)) { fail = 'untestable: step ' + s.name + ' changed nothing (read_js stays ' + JSON.stringify(row.after) + '): the step must earn something'; row.stuck = true; break; }
    done.push(row);
  }
  // A step that earns nothing under phone storage: the same steps again with browser storage. Earning there means the
  // phone storage itself breaks the game (SorensRivet r21: a key never written read back false, the home gift paid 0).
  const stuck = rep.steps.find((r) => r.stuck);
  if (stuck) {
    await G.openGame(page, 'iphone14', 'capsule=pt&ad=complete&adms=600' + (B.query ? '&' + B.query : ''));
    let why = await home(page), earned = null;
    for (const s of steps) {
      if (why) break;
      const before = await P.js(page, s.read_js);
      const r = await P.steps(page, s.actions);
      if (!r.ok) { why = r.why; break; }
      await P.sleep(s.settle_ms || 1200);
      const after = await P.js(page, s.read_js);
      if (s.name === stuck.name) { earned = !P.same(before, after); stuck.browser_storage = [before, after]; break; }
    }
    if (earned) fail = 'with TikTok phone storage (a key never written reads false, 0/1 read back as false/true) step ' + stuck.name + (stuck.why ? ' cannot run (' + stuck.why + ')' : ' earns nothing (' + JSON.stringify(stuck.after) + ')') + '; with browser storage the same steps give ' + JSON.stringify(stuck.browser_storage[0]) + ' -> ' + JSON.stringify(stuck.browser_storage[1]) + ': the game breaks on a phone';
  }
  if (!fail) {
    rep.before_png = await G.shot(page, path.join(C.evidenceDir, 'save-' + safe(unit) + '-before-restart.png'));
    rep.store_before = await page.evaluate(() => (window.__storeDump ? Object.keys(window.__storeDump()).length : null)).catch(() => null);
    // cold restart: the same host page, storage kept (no reset=1)
    await page.goto(L.url('dev=iphone14&' + q + '&r=' + Date.now()));
    await L.keepFrames(page);
    fail = await home(page);
    if (fail) fail = 'after the restart: ' + fail;
  }
  const lost = [];
  if (!fail) {
    for (const row of done) {
      let now = await P.js(page, steps.find((s) => s.name === row.name).read_js);
      const t0 = Date.now();
      while (!P.same(now, row.after) && Date.now() - t0 < 3000) { await P.sleep(400); now = await P.js(page, steps.find((s) => s.name === row.name).read_js); }
      row.after_restart = now;
      if (!P.same(now, row.after)) lost.push(row.name + ': ' + JSON.stringify(row.after) + ' before the restart, ' + JSON.stringify(now) + ' after it');
    }
    rep.after_png = await G.shot(page, path.join(C.evidenceDir, 'save-' + safe(unit) + '-after-restart.png'));
    if (lost.length) fail = 'lost after closing and reopening the game (TikTok phone storage): ' + lost.join('; ');
  }
  rep.result = fail ? 'fail' : 'pass';
  const blocks = !!fail && (POLICY === 'new' || /^invalid run/.test(fail));
  if (fail && !blocks) out.warn('save_restart: ' + fail + ' [legacy game: warning]');
  out.add(unit, !blocks, fail || ('kept after a restart: ' + done.map((r) => r.name + (r.kind ? ' (' + r.kind + ')' : '') + ' = ' + JSON.stringify(r.after)).join(', ')));
}

await L.suite(async ({ out, page }) => {
  const rep = { suite: 'save_restart', policy: POLICY, storage: PHONE, steps: [], units: [] };
  const bad = problems(B);
  if (bad.length) {
    out.add('adapter', POLICY === 'legacy', bad.join('; '));
    if (POLICY === 'legacy') out.warn('save_restart adapter: ' + bad.join('; ') + ' [legacy game: warning]');
    return;
  }
  const save = () => {
    out.evidence.report = L.evidence('save_restart.json', rep);
    out.units = {};
    for (const row of rep.units) {
      const cases = out.cases.filter(item => item.id === row.unit);
      out.units[row.unit] = { passed: cases.length === 1 && cases[0].passed === true, cases };
    }
    out.save();
  };
  if (!independentSteps) {
    if (chosen && (chosen.size !== 1 || !chosen.has('@suite'))) {
      out.add('selection', false, 'legacy save_restart steps need explicit requires before selecting a single step');
      save();
      return;
    }
    await runRestart(page, out, B.steps, 'restart', rep, true);
    save();
    return;
  }
  const known = new Set(['@kinds', ...B.steps.map(step => 'step/' + step.name)]);
  if (chosen && (!chosen.size || [...chosen].some(unit => !known.has(unit)))) {
    out.add('selection', false, 'save_restart selection contains an unknown step or is empty');
    save();
    return;
  }
  if (!chosen || chosen.has('@kinds')) {
    await G.openGame(page, 'iphone14', 'capsule=pt&ad=complete&adms=600&' + PHONE + (B.query ? '&' + B.query : ''));
    const fail = await home(page);
    const miss = !fail && POLICY === 'new' ? needed(P.buttonsOf(await P.snap(page))) : [];
    rep.kinds = { steps: B.steps.map(step => step.kind), none: B.none || null, missing: miss };
    rep.units.push({ unit: '@kinds', missing: miss });
    out.add('@kinds', !fail && !miss.length,
      fail || (miss.length ? 'save_restart.steps lacks required kinds: ' + miss.map(item => item.kind).join(', ')
        : 'complete declared level, buy and claim coverage checked against the actual home'));
    save();
  }
  for (const step of B.steps) {
    const unit = 'step/' + step.name;
    if (chosen && !chosen.has(unit)) continue;
    const row = { unit, name: step.name, prerequisites: step.requires, steps: [] };
    rep.units.push(row);
    await runRestart(page, out, prerequisites(step), unit, row);
    save();
  }
  save();
}, { w: 390, h: 844 });
