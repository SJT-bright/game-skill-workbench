'use strict';
// TikTok Platform Kit 2.0 - HomeEntrySlots: where the two home entries ("Add to Home", "Profile Revisit") sit, decided
// at runtime. Copy unchanged. 生成时预防 R4G1 批 (问题普查 element_overlap 64 款 / 99 次, Saul 2026-11-04).
// Cocos 3.x has no HomeGrowthEntries (a 2.4 cc.Class component), so until R4G1 the 3.x entry coordinates were computed
// once at generation time (tools/home_free_slot.js) and later home buttons / ad-boost entries landed on them. This is
// the same search as HomeGrowthEntries.placeEntries(): the code between BEGIN and END is that file's slot code byte for
// byte (tools/make_plugin_scripts.py --check and tests/plugins-3x.test.js prove it). Rules: never hand-written
// coordinates; visible cc.Button nodes (also disabled ones: interactable false still covers the place) and visible nodes
// with a touch listener are obstacles; touch-only nodes with BlockInputEvents or covering >= half the screen are
// background / mask; entries that touch nothing stay where they are; no free place -> {ok: false, error}, a
// [TikTokKit] log line, and nothing is moved (never a guessed position).
// 3.x (plugin script plugins-3x/HomeEntrySlots.plugin.js, installed by tiktok_finalize source / sync), in the home
// component after the home buttons and ad-boost entries exist:
//     import * as cc from 'cc';
//     const Slots = (globalThis as any).TikTokKit.HomeEntrySlots;
//     Slots.placeLater(cc, this, {root: canvasNode, searchRoot: homePanel, entries: [profileNode, shortcutNode]});   // once settled
//     // home layout changed later (a new button): Slots.place(cc, {root: canvasNode, entries: [...]}) again
// Node-tested only (tests/plugins-3x.test.js, 3.x node tree fixture); 待真机复测.

function log(text) {
  try {
    if (typeof console === 'undefined' || !console || typeof console.info !== 'function') return;
    console.info('[TikTokKit] ' + text);
  } catch (_) {}
}

// ---- BEGIN slot code of assets/tiktok-platform/HomeGrowthEntries.js ----
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

// ---- END slot code of assets/tiktok-platform/HomeGrowthEntries.js ----

// opts as placeEntries; screen defaults to cc.view.getVisibleSize() like the 2.4 component. -> placeEntries result.
function place(cc, opts) {
  opts = Object.assign({}, opts || {});
  if (!opts.screen && cc && cc.view && typeof cc.view.getVisibleSize === 'function') {
    var size = cc.view.getVisibleSize();
    if (size && size.width > 0 && size.height > 0) opts.screen = {w: size.width, h: size.height};
  }
  var r = placeEntries(cc, opts);
  if (!r.ok && !/^no free place/.test(r.error || '')) log('HomeEntrySlots: ' + r.error);
  if (typeof opts.onResult === 'function') { try { opts.onResult(r); } catch (_) {} }
  return r;
}

// R4Q6 (补查3 第 6 组): once the home has settled - at least SETTLE.minFrames (3) frames and the same layout signature
// on two frames in a row (settleGate, same code as 2.4), ticked by the calling component's schedule(); obstacles only
// inside opts.searchRoot (the home panel: pass it; the settings / shop popups under the Canvas are not obstacles).
// Returns the gate ({tick, done, result}); no component: placed now.
function placeLater(cc, component, opts) {
  if (!component || typeof component.schedule !== 'function') return place(cc, opts);
  if (!(opts && opts.searchRoot)) log('HomeEntrySlots: no searchRoot (the home panel); obstacles are taken from the whole root');
  var gate = settleGate({signature: function () { return layoutSignature(cc, opts); }, place: function () { return place(cc, opts); }});
  var step = function () {
    gate.tick();
    if (gate.done && typeof component.unschedule === 'function') component.unschedule(step);
  };
  component.schedule(step, 0);
  return gate;
}

module.exports = {findFreeSlots: findFreeSlots, placeEntries: placeEntries, collectButtons: collectButtons, place: place,
  placeLater: placeLater, settleGate: settleGate, layoutSignature: layoutSignature, SETTLE: SETTLE,
  SLOT: SLOT, BACKDROP_SHARE: BACKDROP_SHARE};
