// Pure rules of the v7.8 layout_state (D), button_sweep (E) and ad_entries (B) suites (总表 B30): no browser, no
// page. The suites collect node boxes in the host; these functions turn them into findings, and decide block vs
// warning. Tested in Node by ../test_layout_gates.py with node lists shaped like the real dumps.
// Every rule comes from the 全民飞车门禁 prototype (1全民飞车漂移/_work/skill_feedback/gates, README_通用自查.md) and keeps
// its 10 calibrated false-positive fixes (2.4) and 4 (3.x); the number of each fix is in the comment next to it.

export const MiB = 1048576;
export const AUDIO = /\.(mp3|ogg|oga|wav|m4a|aac)$/i;
export const STARTUP_LIMIT = 10 * MiB;
export const DEFAULT_SETTINGS = 'setting|gear|option|cog\\b|齿轮|设置';
export const DEFAULT_PLATFORM = 'profile|revisit|shortcut|add ?to ?home|add_?home|addhome|desktop|home ?screen|桌面|回访';

const cx = (b) => (b.x0 + b.x1) / 2, cy = (b) => (b.y0 + b.y1) / 2, hgt = (b) => b.y1 - b.y0, wid = (b) => b.x1 - b.x0;

export function overlap(a, b) {
  const w = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0), h = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
  return w > 0 && h > 0 ? { w: +w.toFixed(1), h: +h.toFixed(1) } : null;
}

// Block or warning (Saul 2026-10-30, 22.6 q2): a new game is refused, a game on the frozen legacy list only warned.
// Cocos 3.x: only the startup download (over 10 MiB, or sound in it) is refused for now; every other finding warns.
export const BLOCK_ON_3X = new Set(['startup_size', 'startup_audio']);
// Never a game fault: the run itself could not judge (throttled tab, home never reached) -> fails closed on any game.
export const ALWAYS = new Set(['invalid_run']);
export function level(code, { engine = '2.x', policy = 'new' } = {}) {
  if (ALWAYS.has(code)) return 'block';
  if (policy === 'legacy') return 'warn';
  if (engine === '3.x' && !BLOCK_ON_3X.has(code)) return 'warn';
  return 'block';
}

// One pass (device x capsule unit x state): buttons cut by the edge, buttons / labels on the capsule, buttons in the
// bottom home-indicator band. fix 2: items inside a scroll list / mask may sit past the edge on purpose.
// fix 3: a button only reaching into the band is a warning; its centre in the band blocks.
export function passFindings(nodes, dev) {
  const out = [];
  for (const n of nodes) {
    const btn = n.kind === 'button' && !n.layer;
    if (n.clipped) continue;
    if (btn && (n.box.x0 < -1 || n.box.x1 > dev.W + 1 || n.box.y0 < -1 || n.box.y1 > dev.H + 1))
      out.push({ code: 'offscreen', path: n.path, msg: 'button ' + n.path + ' is cut by the screen edge (' + JSON.stringify(n.box) + ')' });
    if (btn || n.kind === 'label') {
      const ov = overlap(n.box, dev.cap);
      if (ov && ov.w * ov.h >= 4)
        out.push({ code: 'capsule', path: n.path, warnOnly: !!dev.capXUnmeasured, msg: n.kind + ' ' + n.path + ' overlaps the TikTok capsule' + (dev.capXUnmeasured ? ' (SE capsule x is derived, not measured: warning)' : '') });
    }
    if (btn && n.box.y1 > dev.safeBottom + 2) {
      const into = +(n.box.y1 - dev.safeBottom).toFixed(1), centreIn = cy(n.box) > dev.safeBottom;
      out.push({ code: 'safe_area', path: n.path, warnOnly: !centreIn, msg: 'button ' + n.path + ' reaches ' + into + ' pt into the bottom safe area' + (centreIn ? ' (its centre is in the home-indicator band)' : ' (centre above the band: move it up when convenient)') });
    }
  }
  return out;
}

// pt pass vs px pass of the same device and state: a still button / label that moves > 4 pt follows the raw capsule
// value without a unit check (DriftRacer v2: the top bar fell 166 px into the 3D turntable).
// fix 9: game-world sprites placed at random on every load (SpiderSwing walls) are not compared, only buttons / texts.
export function unitShift(ptNodes, pxNodes) {
  const m = Object.fromEntries(pxNodes.map((n) => [n.path, n]));
  const shift = [];
  for (const n of ptNodes) {
    const q = m[n.path];
    if (!q || n.moving || q.moving || (n.kind !== 'button' && n.kind !== 'label') || n.layer) continue;
    const dy = q.box.y0 - n.box.y0, dx = q.box.x0 - n.box.x0;
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) shift.push({ path: n.path, dx: +dx.toFixed(1), dy: +dy.toFixed(1) });
  }
  return shift.sort((a, b) => Math.abs(b.dy) - Math.abs(a.dy));
}

// Home rules by board (22.1, Saul 2026-10-30). remake: settings top-left, the lowest button row holds only the two
// platform entries. localize: original home buttons stay; only both platform entries on the home page, tappable, not
// on top of another button. kitEntries: paths of HomeGrowthEntries' shortcutNode / profileNode.
export function homeRules(nodes, dev, board, { settings, platform, kitEntries = [] } = {}) {
  const out = [], info = { board, kitEntries };
  if (board !== 'remake' && board !== 'localize') return { findings: out, info };
  const btns = nodes.filter((n) => n.kind === 'button' && !n.layer && n.interactable !== false && hgt(n.box) >= 20 && wid(n.box) >= 20 && n.box.y0 < dev.H && n.box.y1 > 0);
  const sre = new RegExp(settings || DEFAULT_SETTINGS, 'i');
  const pre = new RegExp(platform || DEFAULT_PLATFORM, 'i');
  const isPlat = (n) => kitEntries.some((k) => n.path === k || n.path.startsWith(k + '/')) || pre.test(n.path) || pre.test(n.sig || '');
  const plats = btns.filter((n) => isPlat(n) && !btns.some((m) => m !== n && isPlat(m) && n.path.startsWith(m.path + '/')));
  info.platformEntries = plats.map((n) => n.path);
  if (board === 'remake') {
    const s = btns.find((n) => sre.test(n.path) || sre.test(n.sig || ''));
    info.settings = s ? { path: s.path, centre: [+cx(s.box).toFixed(1), +cy(s.box).toFixed(1)] } : null;
    if (!s) out.push({ code: 'settings_pos', msg: 'home: no settings button recognised (/' + (settings || DEFAULT_SETTINGS) + '/ on node names, texts, sprite names; adapter "settings" names it)' });
    else if (!(cx(s.box) < 0.35 * dev.W && cy(s.box) < 0.15 * dev.H))
      out.push({ code: 'settings_pos', msg: 'home: settings ' + s.path + ' centre (' + cx(s.box).toFixed(0) + ', ' + cy(s.box).toFixed(0) + ') is not in the top-left corner (x < ' + (0.35 * dev.W).toFixed(0) + ', y < ' + (0.15 * dev.H).toFixed(0) + ')' });
    if (btns.length) {
      const low = btns.reduce((m, n) => (n.box.y1 > m.box.y1 ? n : m));
      const row = btns.filter((n) => Math.min(n.box.y1, low.box.y1) - Math.max(n.box.y0, low.box.y0) >= 0.5 * Math.min(hgt(n.box), hgt(low.box)));
      const outer = row.filter((n) => !row.some((m) => m !== n && n.path.startsWith(m.path + '/')));
      const others = outer.filter((n) => !isPlat(n)), rowPlats = outer.filter(isPlat);
      info.bottomRow = outer.map((n) => n.path);
      if (others.length || rowPlats.length < 2)
        out.push({ code: 'bottom_row', msg: 'home: the lowest button row is [' + outer.map((n) => n.path.split('/').slice(-2).join('/')).join(', ') + ']; it must hold only the two platform entries (Profile revisit, Add to Home)' });
    }
  }
  if (plats.length < 2)
    out.push({ code: 'platform_entries', msg: 'home: ' + plats.length + ' of the 2 platform entries (Profile revisit, Add to Home) found on the home screen' + (plats.length ? ': ' + plats.map((n) => n.path).join(', ') : '') + ' (adapter "platform_entries" names them)' });
  for (const p of plats) {
    const hit = btns.filter((m) => m !== p && !isPlat(m) && !m.path.startsWith(p.path + '/') && !p.path.startsWith(m.path + '/'))
      .map((m) => ({ m, ov: overlap(p.box, m.box) })).filter((x) => x.ov && x.ov.w * x.ov.h > 0.15 * wid(p.box) * hgt(p.box));
    if (hit.length) out.push({ code: 'platform_entries', msg: 'home: platform entry ' + p.path + ' sits on top of ' + hit.map((x) => x.m.path).slice(0, 3).join(', ') + ' (an English game adds the entries in empty space only)' });
  }
  return { findings: out, info };
}

// Startup download: main package + the subpackages requested before the home scene starts loading
// (EVENT_BEFORE_SCENE_LOADING of the home scene, from the host's scene beacons); no sound in it (S8 补).
// dirBytes(subRoot) -> {total, audio}; all = whole package {total, audio}; subs = [{name, root}].
export function startupBytes(all, subs, per, names) {
  let subTotal = 0, subAudio = 0;
  for (const s of subs) { const b = per[s.name] || { total: 0, audio: 0 }; subTotal += b.total; subAudio += b.audio; }
  const main = { total: all.total - subTotal, audio: all.audio - subAudio };
  let total = main.total, audio = main.audio;
  const used = [];
  for (const n of names) if (per[n]) { total += per[n].total; audio += per[n].audio; used.push({ name: n, bytes: per[n].total, audio: per[n].audio }); }
  const audioWhere = (main.audio ? ['main package ' + (main.audio / MiB).toFixed(2) + ' MiB'] : []).concat(used.filter((u) => u.audio).map((u) => u.name + ' ' + (u.audio / MiB).toFixed(2) + ' MiB'));
  return { mainBytes: main.total, mainAudioBytes: main.audio, startupBytes: total, startupAudioBytes: audio, startupMiB: +(total / MiB).toFixed(2),
    audioWhere, subpackages: used, notStartup: subs.filter((s) => !names.includes(s.name)).map((s) => ({ name: s.name, bytes: per[s.name] ? per[s.name].total : 0 })) };
}
export function startupFindings(sz, names) {
  const out = [];
  if (sz.startupBytes > STARTUP_LIMIT)
    out.push({ code: 'startup_size', msg: 'startup download ' + sz.startupMiB + ' MiB > 10 MiB (main ' + (sz.mainBytes / MiB).toFixed(2) + ' MiB + ' + names.length + ' subpackage(s) requested before home: ' + (names.join(', ') || 'none') + ')' });
  if (sz.startupAudioBytes > 0)
    out.push({ code: 'startup_audio', msg: 'startup download holds ' + (sz.startupAudioBytes / MiB).toFixed(2) + ' MiB of audio (' + sz.audioWhere.join(', ') + '); sound belongs in its own subpackage loaded after HOME' });
  return out;
}
// Cut-off for the startup download: the first scene-loading (else scene-launch) event of the home scene.
// fix 3.x-4: Cocos 3.x passes the scene URL (db://assets/start_menu.scene), 2.x the name.
export function startupCut(scenes, subs, homeScene) {
  const same = (x) => typeof x === 'string' && (x === homeScene || x.replace(/\.scene$/, '').split('/').pop() === homeScene);
  const first = (f) => scenes.filter(f).sort((a, b) => a.t - b.t)[0];
  const cut = first((s) => same(s.loading)) || first((s) => same(s.launched));
  const names = [...new Set(subs.filter((s) => (cut ? s.t <= cut.t : true)).map((s) => s.name).filter(Boolean))];
  return { cut: cut || null, names };
}

// ---------- button sweep (E) ----------
// diff of two snapshots {scene, sceneId, m: {path: node}}; noisy = paths that changed by themselves before the tap.
// fix 5: same path, new node uuid = the view was rebuilt (HappyCup RETRY) -> counts as a reaction.
export function snapDiff(a, b, noisy = new Set()) {
  const add = [], gone = [], moved = [], text = [], sprite = [];
  for (const k in b.m) {
    if (noisy.has(k)) continue;
    const x = a.m[k], y = b.m[k];
    if (!x) { add.push(k); continue; }
    if (x.uuid && y.uuid && x.uuid !== y.uuid) { moved.push(k); continue; }
    if (Math.abs(x.box.x0 - y.box.x0) > 3 || Math.abs(x.box.y0 - y.box.y0) > 3 || Math.abs(wid(x.box) - wid(y.box)) > 3) moved.push(k);
    if ((x.text || '') !== (y.text || '')) text.push(k);
    if ((x.frame || '') !== (y.frame || '')) sprite.push(k);
  }
  for (const k in a.m) if (!b.m[k] && !noisy.has(k)) gone.push(k);
  return { add, gone, moved, text, sprite };
}
// The outermost interactable on-screen button of each nested group (fix 2: a mask-hidden list item is not tapped).
export function sweepButtons(s, dev) {
  return Object.values(s.m).filter((n) => n.kind === 'button' && !n.layer && !n.maskHidden && n.interactable !== false &&
    wid(n.box) >= 12 && hgt(n.box) >= 12 && cx(n.box) > 0 && cx(n.box) < dev.W && cy(n.box) > 0 && cy(n.box) < dev.H)
    .filter((n, _, all) => !all.some((m) => m !== n && n.path.startsWith(m.path + '/')));
}
// Popup buttons: [failures, warnings] for cut by the edge, on the capsule, in the bottom band.
export function popupGeom(n, dev) {
  const p = [], w = [];
  if (n.clipped) return [p, w];
  if (n.box.x0 < -1 || n.box.x1 > dev.W + 1 || n.box.y0 < -1 || n.box.y1 > dev.H + 1) p.push('cut by the screen edge');
  const ov = overlap(n.box, dev.cap); if (ov && ov.w * ov.h >= 4) p.push('on the TikTok capsule');
  if (n.box.y1 > dev.safeBottom + 2) (cy(n.box) > dev.safeBottom ? p : w).push('in the bottom safe area (' + (n.box.y1 - dev.safeBottom).toFixed(1) + ' pt)');
  return [p, w];
}
// fix 4: a tap on the already selected item / open tab may rightly do nothing (warning).
// W87 calibration (指尖麻将 v56 skin list): the equipped item ("txt_equipped_button") is the selected one too
const SELECTED = /\bchecked\b|selected|current|equipped|_on\b|\bon\b|active_?tab|已选|使用中|已装备/i;
const TAB = /tab\b|_tab|tab_|\btab/i;
export function deadWhy(n) {
  if (n.checked || SELECTED.test(n.sig || '')) return 'warn:already selected (toggle / current tab / equipped item)';
  if (TAB.test(n.path) || TAB.test(n.sig || '')) return 'warn:a tab, maybe the one already open';
  if (n.handlers === 0) return 'fail:cc.Button with no click handler at all (a fake button)';
  return 'fail:reacted to nothing within 2 s';
}
// Host log kinds that mean the game asked the platform for something (fix 7: profile revisit, shortcut, login count).
export const PLATFORM_BEACON = /^(mission|mission-mode|modal|modal-.*|toast|login|vibrate|legacy-ad-create|ad-create|ad-show|ad-result|growth\..*)$/;
// W93: resume / 继续 closes an in-game pause popup (Meteor r6 InGamePause -> ResumeRun)
export const CLOSE = /close|btn_?x\b|\bx\b|back|return|cancel|no ?thanks|skip|later|resume|关闭|返回|取消|继续/i;
// ---------- where a dead tap got stuck (v7.8 W93) ----------
// The chain: touch sent -> node hit -> callback run -> load / ad / platform call sent -> answer back -> screen changes.
// pr = gates.probeRead() of the tap window (hit, end, emits, clicks, err, pend, btn), or {coveredBy: info} when the
// sweep saw a later-drawn blocker over the target before tapping. One sentence for the report, the stage for tools.
const strip = (p) => String(p || '').replace(/#\d+$/, '');
const under = (p, root) => !!p && !!root && (p === root || p.startsWith(root + '/'));
export function coverWords(h) {
  if (!h) return '?';
  const bits = [];
  if (h.block) bits.push('BlockInputEvents');
  if (h.button) bits.push('cc.Button');
  if (typeof h.opacity === 'number') bits.push('opacity ' + h.opacity + (h.opacity === 0 ? ' 全透明' : ''));
  if (h.full) bits.push('全屏');
  return (h.path || h.name || '?') + (bits.length ? '（' + bits.join('，') + '）' : '');
}
export function diagnose(target, pr) {
  const tp = strip(target && target.path);
  if (pr && pr.coveredBy) return { stage: 'hit', say: '点不到（被 ' + coverWords(pr.coveredBy) + ' 盖住）', cover: pr.coveredBy };
  if (!pr || !pr.installed) return { stage: 'unknown', say: '没有诊断（页面探针没装上' + (pr && pr.error ? '：' + pr.error : '') + '）' };
  const hit = pr.hit;
  if (!hit) return { stage: 'hit', say: '点不到（触点没落到任何能接触摸的节点上' + (pr.v3 ? '；Cocos 3.x 上探针可能看不到命中' : '') + '）' };
  if (!under(strip(hit.path), tp)) return { stage: 'hit', say: '点不到（被 ' + coverWords(hit) + ' 盖住）', cover: hit };
  // an exception thrown out of the touch dispatch = the callback threw; an error only logged (console.error, cc.error,
  // window.onerror of a timer) during the window is a clue next to the verdict, not the verdict (W93 calibration:
  // HappyCup logs "Error 3804" on every tap)
  if (pr.err && pr.err.src === 'callback') return { stage: 'callback_error', say: '回调报错：' + pr.err.msg };
  const also = pr.err ? '；2 秒内第一个报错（' + pr.err.src + '）：' + pr.err.msg : '';
  const em = (pr.emits || []).filter((e) => under(strip(e.from), tp));
  const ck = (pr.clicks || []).filter((c) => under(strip(c.path), tp));
  const btn = pr.btn || {};
  const ran = em.some((e) => e.n > e.bad.length) || ck.some((c) => c.listeners) || (btn.touchEnd > 0 && !!pr.end) || (target && target.touchOnly && !!pr.end);
  if (!ran) {
    let why;
    if (!pr.end) why = pr.cancel ? '按下后触摸被取消（touchcancel），没收到抬起' : '按下了但没收到抬起（touch-end 没到按钮）';
    else if (btn.exists && btn.interactable === false) why = '按钮不可点（interactable = false）';
    else if (em.some((e) => e.bad.length)) why = 'clickEvents 指向不存在的回调：' + em.flatMap((e) => e.bad).slice(0, 2).join('；');
    else if (em.length || ck.length) why = '按钮上没有挂任何点击回调';
    else why = btn.exists === false ? '节点上没有 cc.Button，也没有自己的 touch-end 监听' : 'cc.Button 没发出点击（按下和抬起没配成一次点击）';
    return { stage: 'callback', say: '回调没执行（' + why + '）' + also };
  }
  const pend = pr.pend || [];
  if (pend.length) return { stage: 'request', say: '请求没回来：' + pend.map((p) => p.what).slice(0, 3).join('，') + also };
  return { stage: 'no_change', say: '点到了也执行了，但画面没变' + also };
}
// In a running level things move by themselves: a change under a parent whose children already changed in the idle
// window before the tap (spawned enemies, coins) is not the tap's reaction.
const parentOf = (p) => strip(p).split('/').slice(0, -1).join('/');
export function noisyParents(noisy) {
  const s = new Set();
  for (const p of noisy) { const q = parentOf(p); if (q) s.add(q); }
  return s;
}
export function dropUnder(d, parents) {
  if (!parents || !parents.size) return d;
  const keep = (p) => !parents.has(parentOf(p));
  return { add: d.add.filter(keep), gone: d.gone.filter(keep), moved: d.moved.filter(keep), text: d.text, sprite: d.sprite };
}

// The tapped button's own press feedback is not a reaction (W93, HappyCup copy with a throwing click callback: the
// exception skipped cc.Button's release, the SCALE transition stayed at 0.95 and "moved" counted as a reaction).
// Dropped: the target and its children only resized / moved (same uuid). Kept: anything new under it, a rebuilt
// child (new uuid), text and sprite changes (sound toggles).
export function dropPress(d, target, before, after) {
  const t = strip(target);
  const keep = (k) => !(under(k, t) && before.m[k] && after.m[k] && before.m[k].uuid === after.m[k].uuid);
  return { add: d.add, gone: d.gone, moved: d.moved.filter(keep), text: d.text, sprite: d.sprite };
}

// A button found by the sweep that leads to a rewarded ad (for the trial-link smoke and an ad_entries adapter).
export const AD_WORDS = /watch|video|\bads?\b|_ad\b|\bad_|free|double|x ?2\b|revive|广告|免费|复活|双倍/i;

// ---------- ad entries (B) ----------
// Validate the adapter's ad_entries list: [{id, button, states: [{name, why, actions?, setup_js?, settle_ms?}]}].
export function adEntriesProblems(entries) {
  const out = [];
  if (!Array.isArray(entries) || !entries.length) return ['"ad_entries" must be a nonempty list'];
  const ids = new Set();
  entries.forEach((e, i) => {
    if (!e || typeof e !== 'object') { out.push('ad_entries[' + i + '] must be an object'); return; }
    if (typeof e.id !== 'string' || !e.id) out.push('ad_entries[' + i + '].id must be a string');
    else if (ids.has(e.id)) out.push('ad_entries id ' + e.id + ' twice'); else ids.add(e.id);
    if (typeof e.button !== 'string' || !e.button) out.push('ad_entries[' + i + '].button must be a node path');
    if (!Array.isArray(e.states) || !e.states.length) out.push('ad_entries[' + i + '].states must be a nonempty list');
    else e.states.forEach((s, j) => {
      if (!s || typeof s.name !== 'string' || !s.name) out.push('ad_entries[' + i + '].states[' + j + '].name must be a string');
      if (s && s.setup_js != null && typeof s.setup_js !== 'string') out.push('ad_entries[' + i + '].states[' + j + '].setup_js must be a string');
      if (s && s.actions != null && !Array.isArray(s.actions)) out.push('ad_entries[' + i + '].states[' + j + '].actions must be a list');
      // the revive case waits for the hero to fail by itself (A12 补: a forced fail 3 s in comes before the first
      // point where the game rightly offers a revive, so it reports a missing revive that is not missing)
      if (s && /revive|复活/i.test(e.id + ' ' + s.name) && typeof s.setup_js === 'string' && /finish\s*\(\s*false|gameOver\s*\(|\.fail\s*\(|die\s*\(/i.test(s.setup_js) && !(s.actions || []).some((a) => a && a.wait_node))
        out.push('ad_entries ' + e.id + '/' + s.name + ': a revive state must let the hero fail by itself (actions with wait_node on the revive button), not force the fail in setup_js');
    });
  });
  return out;
}
