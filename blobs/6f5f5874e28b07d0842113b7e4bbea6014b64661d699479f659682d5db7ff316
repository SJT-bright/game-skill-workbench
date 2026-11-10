'use strict';
// TikTok Platform Kit 2.0 - fixed home entries: "Add to Home Screen" and "Profile Revisit". Copy unchanged.
// 待真机复测 (Node-tested only: tests/home-entries.test.js). 简化.11.3: one tap goes to TikTok; the reward is checked on return.
//
// Put two button nodes in the home bottom row (nothing else goes in that row, rule U3), add this
// component to their parent, drag the two nodes into shortcutNode / profileNode, then from the home scene:
//     this.getComponent('HomeGrowthEntries').init(saveStore, {onGranted: function (kind, data) { ...top bar... }});
// The reward is ALWAYS PlatformConfig.growthReward() (5B in this game's currency, Saul 2026-10-29);
// there is no option to change it. MissionFlow does the platform calls (TTMinis.game -> tt -> wx).
// R4O3 (补查2 第 5 组, SLS07; Saul 2026-11-04 ECON-SHORTCUT / ECON-REVISIT): a game with NO coins keeps
// normalLevelCoins 0 and passes its no-coin replacement, same option names as MissionFlow:
//     init(saveStore, {reward: function (kind, draft) { draft.energy = (Number(draft.energy) || 0) + 3; },
//                      rewardText: '+3 Energy', onGranted: ...});
// (economy_capabilities no_wallet_substitutes says what to pay). Only used while growthReward() has no coin amount;
// a game with coins always pays 5B. Neither coins nor a reward option: the entries still open TikTok, pay nothing,
// never show a save error, and say why in a [TikTokKit] line and controller.rewardIssue (check_kit_project.py
// reports such a project before packaging: K_home_entries_no_reward).
// Rules taken from earlier games:
//  - the entries are always shown, also in a browser (ThumbPinball / GimblesGem hid them, nobody saw them);
//  - without the TikTok runtime the buttons stay visible and taps stay quiet;
//  - an entry whose icon did not load shows its text instead of an empty box;
//  - taps during a request are merged and a reward is paid once per entry per save.
// 生成时预防 N 批 (P06 3 / P14 2, Saul 2026-11-04): WHERE the two entries sit is decided here, at runtime, from the
// boxes of the home's own buttons (cc.Button nodes and, N2, plain nodes with a touch listener; after Widgets ran). Entries that already touch no button stay
// where they are; entries that cover a button are moved to a free place; no free place -> a [TikTokKit] error and the
// nodes are not moved (never a guessed position). Do not hand-write entry coordinates. Same search as
// tools/home_free_slot.js (parity: tests/home-entries-slot.test.js). init(store, {place: false}) turns it off.
var MissionFlow = require('./MissionFlow');

// 11.17.15 (Saul 2026-11-08): a tap goes straight to TikTok and the kit draws no words on or around the entries
// (no reward amount, no "Collected", no notice). Purpose and reward are part of the icon art. The claimed state is
// shown only by the game's own art-style badge (shortcutClaimedNode / profileClaimedNode), switched on after the
// reward is saved. The entry title is drawn as text only when its icon failed to load (never an empty box).
var TEXT = {
  shortcut: 'Add to Home',
  profile: 'Profile Revisit',
  collected: 'Collected'
};
var ICON_WAIT_MS = 2000;
var SAVE_FAILED = 'Could not save your reward. Please try again.';   // MissionFlow TEXT.saveFailed
var NO_REWARD_DONE = 'Thanks for visiting!';

// R4O3: who pays the two entries. Coins (growthReward() > 0) -> MissionFlow's own 5B, a reward option is ignored.
// No coins + options.reward -> the game's replacement. Neither -> nothing is paid, the claim is still saved once.
function pickReward(config, options) {
  var coins = 0;
  try { coins = Number(config.growthReward()) || 0; } catch (_) { coins = 0; }
  var given = typeof options.reward === 'function';
  if (coins > 0) {
    return {source: 'coins', issue: given ? 'reward option ignored: this game has coins, growthReward() = ' + coins +
      ' (5B, Saul 2026-10-29)' : ''};
  }
  if (options.reward != null && !given) throw new Error('HomeGrowthEntries reward must be function (kind, draft)');
  if (given) {
    var t = options.rewardText;
    if (typeof t === 'string' || t === undefined) t = {shortcut: t || '', profile: t || ''};
    return {source: 'game', reward: options.reward, rewardText: {shortcut: t.shortcut || '', profile: t.profile || ''}};
  }
  // false = MissionFlow writes nothing (not even the claim), so a build that later sets B or a reward still pays once
  return {source: 'none', reward: function () { return false; }, rewardText: {shortcut: '', profile: ''},
    issue: 'no reward: PlatformConfig.normalLevelCoins is 0 and init() got no reward option; the two entries pay ' +
      'nothing. A game without coins passes {reward, rewardText} (economy_capabilities no_wallet_substitutes, ' +
      'ECON-SHORTCUT / ECON-REVISIT: +3 energy, or add a coin and pay 5B)'};
}

function Controller(options) {
  options = options || {};
  if (!options.store) throw new Error('HomeGrowthEntries needs the game SaveStore');
  var self = this;
  this.config = options.config || require('./PlatformConfig');
  this.renderState = typeof options.render === 'function' ? options.render : function () {};
  this.iconFallback = {shortcut: false, profile: false};
  this.lastView = null;
  var pick = pickReward(this.config, options);
  this.rewardSource = pick.source;               // 'coins' | 'game' | 'none' (R4O3)
  this.rewardIssue = pick.issue || '';
  this.gameRewardText = pick.rewardText || null;
  var flowOptions = {
    store: options.store, config: this.config, missions: options.missions, native: options.native,
    missionTimeoutMs: options.missionTimeoutMs,
    render: function (view) { self.lastView = view; self._render(); },
    onGranted: options.onGranted
  };
  if (pick.reward) { flowOptions.reward = pick.reward; flowOptions.rewardText = pick.rewardText; }
  this.flow = new MissionFlow(flowOptions);
  if (pick.issue) log('HomeGrowthEntries: ' + pick.issue);
  logPlatformCalls(this.flow.missions);
  log('runtime ' + describeRuntime() + ', native ' + this.flow.native);
  this._render();
}

// 简化.11.3: what the platform answered goes to the console (vConsole on the phone), so a tap that does nothing
// can be told apart: no SDK object, canIUse false, a fail() with errorCode, or no answer (timeout).
// Only inside the engine (cc.sys exists): the Node tests keep their stdout for the JSON result.
function log(text) {
  try {
    if (typeof cc === 'undefined' || !cc || !cc.sys) return;
    if (typeof console === 'undefined' || !console || typeof console.info !== 'function') return;
    console.info('[TikTokKit] ' + text);
  } catch (_) {}
}

function describeRuntime() {
  var found = [], names = ['addShortcut', 'getShortcutMissionReward', 'startEntranceMission', 'getEntranceMissionReward'];
  var candidates = [
    ['TTMinis.game', typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game],
    ['tt', typeof tt !== 'undefined' && tt],
    ['wx', typeof wx !== 'undefined' && wx]
  ];
  candidates.forEach(function (pair) {
    var sdk = pair[1];
    if (!sdk) return;
    var can = typeof sdk.canIUse === 'function';
    var parts = names.map(function (name) {
      var answer = '?';
      try { answer = can ? String(sdk.canIUse(name)) : 'no canIUse'; } catch (e) { answer = 'throws'; }
      return name + (typeof sdk[name] === 'function' ? '' : '(missing)') + '=' + answer;
    });
    found.push(pair[0] + ' {' + parts.join(', ') + '}');
  });
  return found.length ? found.join('; ') : 'no TTMinis.game / tt / wx';
}

function logPlatformCalls(missions) {
  if (!missions) return;
  ['navigate', 'query'].forEach(function (action) {
    var call = missions[action];
    if (typeof call !== 'function') return;
    missions[action] = function (kind, opts) {
      log(kind + ' ' + action + ' ...');
      var answer = call.call(missions, kind, opts);
      if (answer && typeof answer.then === 'function') {
        answer.then(function (r) {
          r = r || {};
          log(kind + ' ' + action + ' -> ' + r.status + (r.api ? ' (' + r.api + ')' : '') +
            (r.errorCode !== null && r.errorCode !== undefined ? ' errorCode ' + r.errorCode : '') +
            (r.errMsg ? ' errMsg ' + r.errMsg : ''));
        }, function () {});
      }
      return answer;
    };
  });
}

Controller.TEXT = TEXT;

Controller.prototype.rewardAmount = function () {
  try { return this.config.growthReward(); } catch (_) { return 0; }
};

Controller.prototype.state = function () {
  var flow = this.flow, amount = this.rewardAmount(), self = this, view = this.lastView;
  function rewardLabel(kind) {
    if (self.rewardSource === 'game') return self.gameRewardText[kind] || '';
    return amount > 0 ? '+' + amount : '';
  }
  function entry(kind) {
    var claimed = flow.isClaimed(kind), label = rewardLabel(kind);
    return {
      kind: kind, title: TEXT[kind], claimed: claimed, rewardText: label,
      reward: '',
      busy: !!(view && view.kind === kind && view.busy),
      iconFallback: self.iconFallback[kind],
      text: self.iconFallback[kind] ? TEXT[kind] : ''
    };
  }
  var message = view ? view.message : '';
  // R4O3: no reward to pay is not a save error (the old code showed "Could not save" after every visit)
  if (this.rewardSource === 'none' && message === SAVE_FAILED) message = NO_REWARD_DONE;
  return {shortcut: entry('shortcut'), profile: entry('profile'), message: message, native: flow.native,
    rewardSource: this.rewardSource, rewardIssue: this.rewardIssue};
};

Controller.prototype._render = function () { try { this.renderState(this.state()); } catch (_) {} };

// One tap on an entry. Returns what happened, for tests and logs.
// 简化.11.3 (Saul 2026-11-02): every tap goes to TikTok at once (addShortcut / startEntranceMission inside the
// tap, the user gesture). Until 简化.11.2 the first tap only asked for the reward and a second tap was needed;
// together with canIUse answering undefined on the phone, the entries looked dead (77~86, Mosslight v20).
// Coming back to the game (onShow) checks the reward and pays once. A collected entry still opens TikTok.
Controller.prototype.press = function (kind) {
  if (kind !== 'shortcut' && kind !== 'profile') return 'ignored';
  var flow = this.flow;
  if (!flow.native) return 'unsupported';
  if (flow.kind !== kind) { flow.open(kind, {navigate: true}); return 'start'; }
  if (flow.view().busy) return 'busy';                             // merged
  flow.start();
  return 'start';
};

// The icon of this entry is missing or did not load: show its text instead.
Controller.prototype.iconFailed = function (kind) {
  if (this.iconFallback[kind] === false) { this.iconFallback[kind] = true; this._render(); }
};

Controller.prototype.onShow = function (entry) { return this.flow.onShow(entry); };
Controller.prototype.tick = function () { this.flow.tick(); };
Controller.prototype.dispose = function () { this.flow.dispose(); };

function platformToast(text) {
  var sdk = (typeof TTMinis !== 'undefined' && TTMinis && TTMinis.game) || (typeof tt !== 'undefined' && tt) || null;
  if (sdk && typeof sdk.showToast === 'function') {
    try { sdk.showToast({title: text, icon: 'none', duration: 2000}); return true; } catch (_) {}
  }
  return false;
}

// R4Q6 (补查3 第 6 组, 火箭三消: "Available in TikTok" hung in the middle of the screen with no backing, stayed on the
// next page, and two of them stacked; 奔跑吧巨人: notices stacked up). Any legacy reward message uses one notice:
// the GameUIKit toast when the game has the kit
// (single node, backing, timed, cleared on the next page), else TikTok's own showToast, else messageLabel shown for
// NOTICE_MS and then hidden, else only a [TikTokKit] line. Never a text that stays. clear() runs when the home is left
// (component onDisable). makeNotice({ui, platform(text) -> bool, label: {set(text), hide()}, later(ms, fn) -> cancel}).
var NOTICE_MS = 2200;
function findKitUI() {
  var g = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : null);
  var ui = g && g.TikTokGameUIKit;
  return ui && typeof ui.toast === 'function' ? ui : null;
}
function makeNotice(o) {
  o = o || {};
  var ui = o.ui && typeof o.ui.toast === 'function' ? o.ui : null;
  var cancel = null, current = '', via = '';
  function stop() { if (cancel) { try { cancel(); } catch (_) {} cancel = null; } }
  var notice = {
    text: function () { return via === 'GameUIKit' && typeof ui.toastText === 'function' ? ui.toastText() : current; },
    via: function () { return via; },
    show: function (text) {
      text = text === undefined || text === null ? '' : String(text);
      if (!text) return '';
      stop();
      if (via === 'label' && o.label) o.label.hide();
      current = text;
      if (ui) { via = 'GameUIKit'; ui.toast(text, {ms: NOTICE_MS}); return via; }
      if (typeof o.platform === 'function' && o.platform(text)) { via = 'platform'; return via; }
      if (o.label && typeof o.later === 'function') {
        via = 'label';
        o.label.set(text);
        cancel = o.later(NOTICE_MS, function () { cancel = null; current = ''; o.label.hide(); });
        return via;
      }
      via = 'log';
      log('HomeGrowthEntries: ' + text);
      current = '';
      return via;
    },
    clear: function () {
      stop();
      if (via === 'GameUIKit' && typeof ui.clearToast === 'function' && typeof ui.toastText === 'function' &&
          ui.toastText() === current) ui.clearToast();
      if (via === 'label' && o.label) o.label.hide();
      current = '';
    }
  };
  return notice;
}

function textureLoaded(sprite) {
  var frame = sprite && sprite.spriteFrame;
  var texture = frame && typeof frame.getTexture === 'function' ? frame.getTexture() : null;
  return !!(texture && texture.loaded);
}

// ------------------------------------------------------------- free place for the entries (生成时预防 N 批)
// Design units, origin at the centre of `root` (the Canvas), y up. The search is tools/home_free_slot.js's.
var SLOT = {gap: 16, topReserve: 0.12, step: 4};

function slotBox(b) { return {x0: b.x - b.w / 2, y0: b.y - b.h / 2, x1: b.x + b.w / 2, y1: b.y + b.h / 2}; }
function slotGrow(b, g) { return {x0: b.x0 - g, y0: b.y0 - g, x1: b.x1 + g, y1: b.y1 + g}; }
function slotHits(a, b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }

function slotRows(screen, obstacles, entry, o) {
  var hw = entry.w / 2, hh = entry.h / 2, rows = [];
  var safe = o.safe || {x0: -screen.w / 2, y0: -screen.h / 2, x1: screen.w / 2, y1: screen.h / 2 - screen.h * o.topReserve};
  var left = safe.x0 + o.gap + hw, right = safe.x1 - o.gap - hw;
  var bottom = safe.y0 + o.gap + hh, top = safe.y1 - hh;
  for (var y = bottom; y <= top; y += o.step) {
    var xs = [];
    for (var x = left; x <= right; x += o.step) {
      var b = {x0: x - hw, y0: y - hh, x1: x + hw, y1: y + hh};
      if (!obstacles.some(function (ob) { return slotHits(b, ob); })) xs.push(x);
    }
    if (xs.length) rows.push({y: y, xs: xs});
  }
  return rows;
}

function slotPair(row, entry, gap) {
  var best = null, xs = row.xs, need = entry.w + gap;
  for (var i = 0; i < xs.length; i++) {
    for (var j = xs.length - 1; j > i; j--) {
      var d = xs[j] - xs[i];
      if (d < need) break;
      var off = Math.abs(xs[i] + xs[j]), score = off * 4 + (d - need);
      if (!best || score < best.score) best = {score: score, a: xs[i], b: xs[j]};
    }
  }
  return best;
}

// {screen: {w, h}, buttons: [{name, x, y, w, h}], entry: {w, h}, safe?, gap?, topReserve?}
//   -> {ok: true, slots: [{x, y, w, h} x2]} | {ok: false, error}
function findFreeSlots(spec) {
  spec = spec || {};
  var screen = spec.screen, entry = spec.entry, count = spec.count || 2;
  if (!screen || !(screen.w > 0) || !(screen.h > 0)) return {ok: false, error: 'screen {w, h} is required'};
  if (!entry || !(entry.w > 0) || !(entry.h > 0)) return {ok: false, error: 'entry {w, h} is required'};
  var o = {gap: spec.gap === undefined ? SLOT.gap : spec.gap,
    topReserve: spec.topReserve === undefined ? SLOT.topReserve : spec.topReserve, step: spec.step || SLOT.step,
    safe: spec.safe || null};
  if (o.safe && !(o.safe.x1 > o.safe.x0 && o.safe.y1 > o.safe.y0)) return {ok: false, error: 'safe {x0, y0, x1, y1} is empty'};
  var buttons = (spec.buttons || []).concat(spec.obstacles || []);
  var bad = buttons.filter(function (b) { return ![b.x, b.y, b.w, b.h].every(isFinite); });
  if (bad.length) return {ok: false, error: 'button without x, y, w, h: ' + bad.map(function (b) { return b.name; }).join(', ')};
  var obstacles = buttons.map(function (b) { return slotGrow(slotBox(b), o.gap); });
  var rows = slotRows(screen, obstacles, entry, o);
  var slots = [];
  for (var r = 0; r < rows.length && count === 2; r++) {
    var p = slotPair(rows[r], entry, o.gap);
    if (p) { slots = [{x: p.a, y: rows[r].y}, {x: p.b, y: rows[r].y}]; break; }
  }
  if (!slots.length) {
    for (var k = 0; k < count; k++) {
      var extra = obstacles.concat(slots.map(function (s) { return slotGrow(slotBox({x: s.x, y: s.y, w: entry.w, h: entry.h}), o.gap); }));
      var free = slotRows(screen, extra, entry, o);
      if (!free.length) {
        return {ok: false, error: 'no free place for ' + count + ' entries of ' + entry.w + 'x' + entry.h + ' on a ' +
          screen.w + 'x' + screen.h + ' home with ' + buttons.length + ' buttons/obstacles (gap ' + o.gap +
          '): make the entries smaller, or ask before moving an original button -- do not guess a position',
          placed: slots.length};
      }
      var row = free[0], best = row.xs.reduce(function (m, x) { return Math.abs(x) < Math.abs(m) ? x : m; }, row.xs[0]);
      slots.push({x: best, y: row.y});
    }
  }
  return {ok: true, coords: 'design units, origin at the screen centre, y up', gap: o.gap,
    slots: slots.map(function (s) { return {x: s.x, y: s.y, w: entry.w, h: entry.h}; })};
}

// Engine glue, Cocos 2.4 (node.getBoundingBoxToWorld, node.convertToNodeSpaceAR) and 3.x (UITransform).
function uiTransform(cc, node) {
  var T = cc && cc.UITransform;
  return T && node && typeof node.getComponent === 'function' ? node.getComponent(T) : null;
}
function worldRect(cc, node) {
  var t = uiTransform(cc, node);
  if (t && typeof t.getBoundingBoxToWorld === 'function') return t.getBoundingBoxToWorld();
  return typeof node.getBoundingBoxToWorld === 'function' ? node.getBoundingBoxToWorld() : null;
}
function vec(cc, x, y) { return cc.v3 ? cc.v3(x, y, 0) : (cc.v2 ? cc.v2(x, y) : {x: x, y: y}); }
function toLocal(cc, node, x, y) {
  var t = uiTransform(cc, node), owner = t && typeof t.convertToNodeSpaceAR === 'function' ? t : node;
  return owner.convertToNodeSpaceAR(vec(cc, x, y));
}
function toWorld(cc, node, x, y) {
  var t = uiTransform(cc, node), owner = t && typeof t.convertToWorldSpaceAR === 'function' ? t : node;
  return owner.convertToWorldSpaceAR(vec(cc, x, y));
}
// A node's box in root space as {name, x, y, w, h} (centre).
function boxIn(cc, node, root) {
  var r = worldRect(cc, node);
  if (!r) return null;
  var a = toLocal(cc, root, r.x, r.y), b = toLocal(cc, root, r.x + r.width, r.y + r.height);
  var w = Math.abs(b.x - a.x), h = Math.abs(b.y - a.y);
  return {name: node.name, x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, w: w, h: h};
}
function shown(node) {
  if (!node || node.active === false || node.activeInHierarchy === false) return false;
  var op = node.opacity;
  if (op === undefined && node.getComponent) {
    var uo = node.getComponent('cc.UIOpacity');
    op = uo ? uo.opacity : undefined;
  }
  return op === undefined || op >= 13;                       // 0.05 of 255, like the ui_dump checks
}
// N2 批: a plain node with a touch listener is a button too (ad-boost home entries: WheelPanel.entry() and the
// other modules do node.on(TOUCH_END); original Chinese games often do the same). 2.4 types are 'touchstart' /
// 'touchend', 3.x 'touch-start' / 'touch-end'; both engines have node.hasEventListener(type), 2.4 also keeps
// node._touchListener while any touch callback is on. Full-screen backgrounds and masks with a touch listener (or
// cc.BlockInputEvents) are not obstacles: a touch-only node covering >= BACKDROP_SHARE of the screen is skipped,
// its children are still walked.
var BACKDROP_SHARE = 0.5;
function touchTypes(cc) {
  var out = ['touchstart', 'touchend', 'touch-start', 'touch-end'];
  [cc && cc.Node && cc.Node.EventType, cc && cc.NodeEventType].forEach(function (T) {
    if (T) [T.TOUCH_START, T.TOUCH_END].forEach(function (t) { if (t && out.indexOf(t) < 0) out.push(t); });
  });
  return out;
}
function listensTouch(cc, node, types) {
  if (typeof node.hasEventListener === 'function') {
    for (var i = 0; i < types.length; i++) { try { if (node.hasEventListener(types[i])) return true; } catch (_) {} }
  }
  return !!node._touchListener;
}
function blocksInput(cc, node) {
  var B = cc && cc.BlockInputEvents;
  return !!(B && node.getComponent && node.getComponent(B));
}
// Visible cc.Button nodes and visible touch-listening nodes under root, minus the skipped nodes and everything
// inside them. opts: {screen?: {w, h}, ignore?: [node]} -> boxes {name, x, y, w, h, by: 'button' | 'touch'};
// opts.backdrops (array) gets the touch nodes left out as background / mask.
// R4Q6 (补查3 第 6 组, 奔跑吧巨人): opts.searchRoot = the home panel. Only buttons inside it are obstacles (boxes are
// still in root space); the settings / shop popups and other pages kept under the Canvas are not.
function collectButtons(cc, root, skip, opts) {
  opts = opts || {};
  var out = [], Btn = cc && cc.Button, types = touchTypes(cc), ignore = opts.ignore || [];
  var area = opts.screen ? opts.screen.w * opts.screen.h : 0;
  var start = opts.searchRoot || root;
  (function walk(node) {
    if (!shown(node) || (skip || []).indexOf(node) >= 0) return;
    if (node !== root && node !== start && ignore.indexOf(node) < 0) {
      var isBtn = !!(Btn && node.getComponent && node.getComponent(Btn));
      var isTouch = !isBtn && listensTouch(cc, node, types);
      if (isBtn || isTouch) {
        var b = boxIn(cc, node, root);
        if (b && b.w > 0 && b.h > 0) {
          b.by = isBtn ? 'button' : 'touch';
          if (isTouch && (blocksInput(cc, node) || (area && b.w * b.h >= area * BACKDROP_SHARE))) {
            if (opts.backdrops) opts.backdrops.push(b.name);
          } else out.push(b);
        }
      }
    }
    (node.children || []).forEach(walk);
  })(start);
  return out;
}

// opts: {root (Canvas node), entries: [node, node], screen?: {w, h} (default root size), obstacles?: [node],
//        ignore?: [node] (touch nodes that are not tap targets), safe?, gap?, topReserve?}
// -> {ok, kept|moved, slots, buttons} or {ok: false, error}; on error nothing is moved.
function placeEntries(cc, opts) {
  opts = opts || {};
  var root = opts.root, entries = (opts.entries || []).filter(Boolean);
  if (!root || entries.length !== 2) return {ok: false, error: 'placeEntries needs root and two entry nodes'};
  var rootBox = boxIn(cc, root, root);
  var screen = opts.screen || (rootBox ? {w: rootBox.w, h: rootBox.h} : null);
  var backdrops = [];
  var buttons = collectButtons(cc, root, entries, {screen: screen, ignore: opts.ignore, backdrops: backdrops, searchRoot: opts.searchRoot}).concat((opts.obstacles || []).map(function (n) { return boxIn(cc, n, root); }).filter(Boolean));
  var boxes = entries.map(function (n) { return boxIn(cc, n, root); });
  if (!boxes[0] || !boxes[1]) return {ok: false, error: 'entry node has no size'};
  var gap = opts.gap === undefined ? SLOT.gap : opts.gap;
  var top = screen ? screen.h / 2 - screen.h * (opts.topReserve === undefined ? SLOT.topReserve : opts.topReserve) : Infinity;
  var inside = function (b) {
    return screen && b.x - b.w / 2 >= -screen.w / 2 && b.x + b.w / 2 <= screen.w / 2 && b.y - b.h / 2 >= -screen.h / 2 && b.y + b.h / 2 <= top;
  };
  var clear = boxes.every(function (b) {
    return inside(b) && !buttons.some(function (o) { return slotHits(slotBox(b), slotBox(o)); });
  }) && !slotHits(slotBox(boxes[0]), slotBox(boxes[1]));
  if (clear) return {ok: true, kept: true, slots: boxes, buttons: buttons, backdrops: backdrops};
  var entry = {w: Math.max(boxes[0].w, boxes[1].w), h: Math.max(boxes[0].h, boxes[1].h)};
  var r = findFreeSlots({screen: screen, buttons: buttons, entry: entry, safe: opts.safe, gap: gap, topReserve: opts.topReserve});
  r.buttons = buttons; r.backdrops = backdrops;
  if (!r.ok) { log('HomeGrowthEntries: ' + r.error); return r; }
  entries.forEach(function (node, i) {
    var s = r.slots[i], b = boxes[i];
    // move by the difference between the box centre now and the slot centre (anchor and scale stay as they are)
    var nowW = toWorld(cc, root, b.x, b.y), toW = toWorld(cc, root, s.x, s.y), parent = node.parent || root;
    var p0 = toLocal(cc, parent, nowW.x, nowW.y), p1 = toLocal(cc, parent, toW.x, toW.y);
    var pos = node.position || {x: node.x, y: node.y};
    node.setPosition(vec(cc, pos.x + (p1.x - p0.x), pos.y + (p1.y - p0.y)));
  });
  r.moved = true;
  return r;
}

// R4Q6 (补查3 第 6 组, 奔跑吧巨人: the entries were placed from boxes taken while the home was still laying out).
// Place only after the home has settled: at least SETTLE.minFrames frames, and the same layout signature (every
// obstacle box and both entry boxes, rounded) on two frames in a row. Still moving after maxFrames: placed on the last
// frame with a [TikTokKit] line. settleGate({signature, place}).tick() once per frame -> null until placed, then the
// placeEntries result (+ frames, settled).
var SETTLE = {minFrames: 3, maxFrames: 90};
function layoutSignature(cc, opts) {
  opts = opts || {};
  var root = opts.root, entries = (opts.entries || []).filter(Boolean);
  if (!root) return '';
  var list = collectButtons(cc, root, entries, {searchRoot: opts.searchRoot, ignore: opts.ignore})
    .concat(entries.map(function (n) { return boxIn(cc, n, root); }).filter(Boolean));
  return list.map(function (b) {
    return b.name + ':' + Math.round(b.x) + ',' + Math.round(b.y) + ',' + Math.round(b.w) + ',' + Math.round(b.h);
  }).join('|');
}
function settleGate(o) {
  o = o || {};
  var minF = o.minFrames || SETTLE.minFrames, maxF = o.maxFrames || SETTLE.maxFrames;
  var frame = 0, last = null, gate = {result: null, done: false};
  gate.frames = function () { return frame; };
  gate.tick = function () {
    if (gate.done) return gate.result;
    frame++;
    var sig = null;
    try { sig = String(o.signature()); } catch (_) { sig = null; }
    var steady = sig !== null && sig === last;
    last = sig;
    if (!(frame >= minF && steady) && frame < maxF) return null;
    gate.done = true;
    if (!steady) log('HomeGrowthEntries: home layout still moving after ' + frame + ' frames; entries placed on this frame');
    var r = null;
    try { r = o.place(); } catch (e) { r = {ok: false, error: 'place failed: ' + (e && e.message)}; }
    r = r || {ok: false, error: 'place returned nothing'};
    r.frames = frame; r.settled = steady;
    gate.result = r;
    return r;
  };
  return gate;
}

Controller.findFreeSlots = findFreeSlots;
Controller.placeEntries = placeEntries;

Controller.settleGate = settleGate;
Controller.layoutSignature = layoutSignature;
Controller.makeNotice = makeNotice;

var exported = {Controller: Controller, TEXT: TEXT, findFreeSlots: findFreeSlots, placeEntries: placeEntries,
  collectButtons: collectButtons, settleGate: settleGate, layoutSignature: layoutSignature, makeNotice: makeNotice,
  SETTLE: SETTLE, NOTICE_MS: NOTICE_MS};
if (typeof cc !== 'undefined' && cc && typeof cc.Class === 'function') {
  exported = cc.Class({
    extends: cc.Component,
    properties: {
      shortcutNode: {default: null, type: cc.Node},
      profileNode: {default: null, type: cc.Node},
      shortcutClaimedNode: {default: null, type: cc.Node},
      profileClaimedNode: {default: null, type: cc.Node},
      messageLabel: {default: null, type: cc.Label}
    },
    statics: {Controller: Controller, TEXT: TEXT, findFreeSlots: findFreeSlots, placeEntries: placeEntries,
      settleGate: settleGate, layoutSignature: layoutSignature, makeNotice: makeNotice},
    init: function (store, options) {
      options = options || {};
      var self = this;
      if (this.controller) this.controller.dispose();
      this.controller = new Controller({
        store: store, onGranted: options.onGranted, missions: options.missions, native: options.native,
        reward: options.reward, rewardText: options.rewardText,
        render: function (state) { self._paint(state); }
      });
      ['shortcut', 'profile'].forEach(function (kind) {
        var node = self[kind + 'Node'];
        if (!node) { cc.error('HomeGrowthEntries: ' + kind + 'Node is not set'); return; }
        node.active = true;
        node.off(cc.Node.EventType.TOUCH_END, self['_tap_' + kind], self);
        self['_tap_' + kind] = function () { self.controller.press(kind); };
        node.on(cc.Node.EventType.TOUCH_END, self['_tap_' + kind], self);
        var sprite = node.getComponent(cc.Sprite);
        if (!sprite || !sprite.spriteFrame) { self.controller.iconFailed(kind); return; }
        self.scheduleOnce(function () { if (!textureLoaded(sprite)) self.controller.iconFailed(kind); }, ICON_WAIT_MS / 1000);
      });
      // R4Q6: one notice for every message (GameUIKit toast > TikTok showToast > messageLabel for NOTICE_MS)
      this._lastMessage = '';
      this._isHomeVisible = options.isHomeVisible;
      this._notice = makeNotice({ui: options.ui || findKitUI(), platform: platformToast,
        label: this.messageLabel ? {set: function (t) { self.messageLabel.string = t; self.messageLabel.node.active = true; },
          hide: function () { if (cc.isValid(self.messageLabel.node)) self.messageLabel.node.active = false; }} : null,
        later: function (ms, fn) { self.scheduleOnce(fn, ms / 1000); return function () { self.unschedule(fn); }; }});
      if (this.messageLabel) this.messageLabel.node.active = false;
      // R4Q6: keep or move the entries clear of every home button once the home has settled (>= 3 frames, the same
      // layout on two frames in a row, update() ticks it); obstacles only inside the home panel
      if (options.place !== false) {
        this._placeOptions = options;
        this._settle = settleGate({signature: function () { return layoutSignature(cc, self._placeSpec()); },
          place: function () { return self.placeEntries(); }});
      }
      this.controller._render();
      this.controller.flow.startEntryTracking();
      return this.controller;
    },
    // Also callable again after the home layout changed. -> result of placeEntries (kept / moved / error).
    // R4Q6: root = coordinate frame (homeRoot or the Canvas); searchRoot = where obstacles are looked for:
    // init({homePanel}), else homeRoot, else the nearest parent of this component named like "home" (homePanel,
    // HomeView, ...), else the Canvas (and a [TikTokKit] line, because then popups under the Canvas count too).
    _placeSpec: function () {
      var o = this._placeOptions || {};
      var root = o.homeRoot || (cc.Canvas && cc.Canvas.instance && cc.Canvas.instance.node) || cc.find('Canvas') || this.node.parent;
      var panel = o.homePanel || o.homeRoot || null;
      for (var n = this.node; !panel && n && n !== root; n = n.parent) if (/home/i.test(n.name || '')) panel = n;
      if (!panel && !this._warnedPanel) {
        this._warnedPanel = true;
        log('HomeGrowthEntries: no home panel found (init({homePanel}) or a parent named like "home"); obstacles are taken from the whole Canvas');
      }
      var size = cc.view && typeof cc.view.getVisibleSize === 'function' ? cc.view.getVisibleSize() : null;
      return {root: root, searchRoot: panel || root, entries: [this.shortcutNode, this.profileNode],
        screen: size ? {w: size.width, h: size.height} : undefined, obstacles: o.obstacles, ignore: o.ignore, safe: o.safe,
        gap: o.gap, topReserve: o.topReserve};
    },
    placeEntries: function () {
      this.placement = placeEntries(cc, this._placeSpec());
      if (this.controller) this.controller.placement = this.placement;
      return this.placement;
    },
    _label: function (node) {
      var child = node.getChildByName('HomeEntryText');
      if (!child) {
        child = new cc.Node('HomeEntryText');
        child.parent = node;
        var label = child.addComponent(cc.Label);
        label.fontSize = 24; label.lineHeight = 28;
        label.horizontalAlign = cc.Label.HorizontalAlign.CENTER;
        label.overflow = cc.Label.Overflow.SHRINK;
        child.setContentSize(node.width || 160, node.height || 80);
        child.color = cc.Color.WHITE;
      }
      return child.getComponent(cc.Label);
    },
    _paint: function (state) {
      var self = this;
      ['shortcut', 'profile'].forEach(function (kind) {
        var node = self[kind + 'Node'];
        if (!node) return;
        var e = state[kind], label = self._label(node), badge = self[kind + 'ClaimedNode'];
        // 11.17.15: the claimed state is the game's art badge only; the kit adds no words to the entry.
        if (badge && cc.isValid(badge)) badge.active = !!e.claimed;
        // Icon missing or not loaded: the entry title is drawn as text, so the slot is never an empty box.
        label.string = e.iconFallback ? e.title : '';
        label.node.active = label.string !== '';
        var button = node.getComponent(cc.Button);
        if (button) button.interactable = !e.busy;
      });
      // a message is shown once when it changes (render runs on every flow step; the same text never stacks)
      if (state.message !== this._lastMessage) {
        this._lastMessage = state.message || '';
        if (state.message) this._message(state.message);
        else if (this._notice) this._notice.clear();
      }
    },
    _canShowNotice: function () {
      return this.node.activeInHierarchy &&
        (typeof this._isHomeVisible !== 'function' || this._isHomeVisible() === true);
    },
    _message: function (text) {
      if (this._notice && this._canShowNotice()) this._notice.show(text);
    },
    update: function () {
      if (this._settle && !this._settle.done) this._settle.tick();
      if (this.controller) this.controller.tick();
      if (this._notice && this._lastMessage && !this._canShowNotice()) {
        this._notice.clear();
        this._lastMessage = '';
      }
    },
    // leaving the home (another page / panel switched on, the home node hidden): no notice stays behind
    onDisable: function () {
      if (this._notice) this._notice.clear();
      this._lastMessage = '';
    },
    onDestroy: function () {
      if (this._notice) this._notice.clear();
      if (this.controller) this.controller.dispose();
      this.controller = null;
    }
  });
}
module.exports = exported;
