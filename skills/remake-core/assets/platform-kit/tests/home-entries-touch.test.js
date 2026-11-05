'use strict';
// N2 批 (P06 3 / P14 2 follow-up, 2026-11-04): HomeGrowthEntries must keep its two entries off plain nodes that only
// have a touch listener, not just off cc.Button nodes. Fixture = how ad-boost builds its home entries
// (modules/wheel/ui/cocos2.4/WheelPanel.js entry(): new cc.Node, setContentSize, Icon / RedDot children,
// n.on(TOUCH_END, ...); checkin, coin-ad, offline, online gift and quest entries are built the same way) and how
// original Chinese games often make buttons (node.on(TOUCH_END) without cc.Button). Same 蛋壳特工队 home as
// home-entries-slot.test.js. The N version only looked at cc.Button: it moves the entries straight onto the wheel and
// check-in entries, or keeps them there. A full-screen background / mask with a touch listener must not block every
// place. Cocos 2.4 ('touchend', node._touchListener) and 3.x ('touch-end', UITransform). Node only, well under 1 s.
// HOME_ENTRIES=<file> runs the same cases against another HomeGrowthEntries.js (the N version must fail).
var assert = require('assert'), path = require('path');
var HGE = require(process.env.HOME_ENTRIES || path.join(__dirname, '..', 'assets', 'tiktok-platform', 'HomeGrowthEntries.js'));
var TOOL = require(path.join(__dirname, '..', 'tools', 'home_free_slot.js'));
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

var SCREEN = {w: 720, h: 1561};
var DUMP = [
  ['btnTower', [0.7127, 0.20931, 0.27778, 0.16657]],
  ['tilibg/Node', [0.29167, 0.09605, 0.25278, 0.03203]],
  ['baoshibg/Node', [0.53929, 0.09563, 0.20833, 0.03203]],
  ['coinbg/Node', [0.76044, 0.09605, 0.20833, 0.03203]],
  ['ui_btn1', [-0.00278, 0.89626, 0.27778, 0.07303]],
  ['ui_btn2', [0.27222, 0.89626, 0.18472, 0.07303]],
  ['ui_btn3', [0.45417, 0.89626, 0.18472, 0.07303]],
  ['ui_btn4', [0.63611, 0.89626, 0.18472, 0.07303]],
  ['ui_btn5', [0.81806, 0.89626, 0.18472, 0.07303]]
];
var HOME = DUMP.map(function (d) {
  var r = d[1];
  return {name: d[0], x: (r[0] + r[2] / 2 - 0.5) * SCREEN.w, y: (0.5 - r[1] - r[3] / 2) * SCREEN.h, w: r[2] * SCREEN.w, h: r[3] * SCREEN.h};
});
var ENTRY = {w: 200, h: 70};
var OLD = [{name: 'ProfileRevisit', x: -150, y: -620, w: 200, h: 70}, {name: 'AddToHome', x: 150, y: -620, w: 200, h: 70}];
// Where a button-only search puts the two entries on this home (= what the N version does).
var BUTTON_ONLY = TOOL.findFreeSlots({screen: SCREEN, buttons: HOME, entry: ENTRY});
// ad-boost entries (120x120, WheelPanel default size) right on those places, plus an original-game touch button.
var AD_ENTRIES = [
  {name: 'WheelEntry', x: BUTTON_ONLY.slots[0].x, y: BUTTON_ONLY.slots[0].y, w: 120, h: 120},
  {name: 'CheckinEntry', x: BUTTON_ONLY.slots[1].x, y: BUTTON_ONLY.slots[1].y, w: 120, h: 120}
];
var ORIGINAL_TOUCH = {name: 'btnSignIn', x: -260, y: 300, w: 150, h: 150};
function hit(a, b) { return TOOL.intersects(a, b); }

// ------------------------------------------------------------------ tiny engines with node.on / off / hasEventListener
function Btn() {}
function Block() {}
function makeEngine(kind) {
  var T = kind === '24' ? {TOUCH_START: 'touchstart', TOUCH_END: 'touchend'} : {TOUCH_START: 'touch-start', TOUCH_END: 'touch-end'};
  var cc = {Button: Btn, BlockInputEvents: Block, Node: {EventType: T},
    v2: function (x, y) { return {x: x, y: y}; }, v3: function (x, y, z) { return {x: x, y: y, z: z || 0}; }};
  if (kind === '3x') { cc.NodeEventType = T; cc.UITransform = function UITransform() {}; }
  function world(n) {
    if (!n.parent) return {x: n.position.x, y: n.position.y, sx: n.scale, sy: n.scale};
    var p = world(n.parent);
    return {x: p.x + n.position.x * p.sx, y: p.y + n.position.y * p.sy, sx: p.sx * n.scale, sy: p.sy * n.scale};
  }
  function rectOf(n) {
    var w = world(n), W = n.size.w * w.sx, H = n.size.h * w.sy;
    return {x: w.x - n.anchor.x * W, y: w.y - n.anchor.y * H, width: W, height: H};
  }
  function toLocal(n, v) { var w = world(n); return {x: (v.x - w.x) / w.sx, y: (v.y - w.y) / w.sy}; }
  function toWorld(n, v) { var w = world(n); return {x: w.x + v.x * w.sx, y: w.y + v.y * w.sy}; }
  var touchNames = [T.TOUCH_START, 'touchmove', 'touch-move', T.TOUCH_END, 'touchcancel', 'touch-cancel'];
  function node(name, x, y, w, h, opts) {
    opts = opts || {};
    var n = {name: name, position: {x: x, y: y, z: 0}, scale: opts.scale || 1, size: {w: w, h: h},
      anchor: opts.anchor || {x: 0.5, y: 0.5}, children: [], parent: null, active: opts.active !== false, comps: [],
      _ls: {}};
    n.setPosition = function (v) { n.position = {x: v.x, y: v.y, z: 0}; };
    n.getComponent = function (C) { return n.comps.filter(function (c) { return c instanceof C || c.type === C; })[0] || null; };
    // like the engines: listeners per type; 2.4 also holds _touchListener while any touch callback is on
    n.on = function (type, cb) { (n._ls[type] = n._ls[type] || []).push(cb); if (kind === '24' && touchNames.indexOf(type) >= 0) n._touchListener = {}; };
    n.off = function (type, cb) {
      n._ls[type] = (n._ls[type] || []).filter(function (f) { return f !== cb; });
      if (kind === '24' && !touchNames.some(function (t) { return (n._ls[t] || []).length; })) n._touchListener = null;
    };
    n.hasEventListener = function (type) { return !!(n._ls[type] && n._ls[type].length); };
    if (kind === '24') {
      n.opacity = opts.opacity === undefined ? 255 : opts.opacity;
      n.getBoundingBoxToWorld = function () { return rectOf(n); };
      n.convertToNodeSpaceAR = function (v) { return toLocal(n, v); };
      n.convertToWorldSpaceAR = function (v) { return toWorld(n, v); };
    } else {
      var t = new cc.UITransform();
      t.getBoundingBoxToWorld = function () { return rectOf(n); };
      t.convertToNodeSpaceAR = function (v) { return toLocal(n, v); };
      t.convertToWorldSpaceAR = function (v) { return toWorld(n, v); };
      n.comps.push(t);
      if (opts.opacity !== undefined) n.comps.push({type: 'cc.UIOpacity', opacity: opts.opacity});
      var get = n.getComponent;
      n.getComponent = function (C) {
        if (C === 'cc.UIOpacity') return n.comps.filter(function (c) { return c.type === 'cc.UIOpacity'; })[0] || null;
        return get(C);
      };
    }
    if (opts.button) { n.comps.push(new Btn()); n.on(T.TOUCH_START, function () {}); n.on(T.TOUCH_END, function () {}); }
    if (opts.block) n.comps.push(new Block());
    return n;
  }
  function add(parent, child) { child.parent = parent; parent.children.push(child); return child; }
  // ad-boost WheelPanel.entry(): plain node + Icon / RedDot children + TOUCH_END on the node itself
  function adEntry(parent, b) {
    var n = add(parent, node(b.name, b.x, b.y, b.w, b.h));
    add(n, node('Icon', 0, 0, b.w, b.h));
    add(n, node('RedDot', b.w * 0.36, b.h * 0.36, b.w * 0.3, b.h * 0.3));
    var last = 0;
    n.on(T.TOUCH_END, function () { var t = Date.now(); if (t - last < 500) return; last = t; });
    return n;
  }
  return {cc: cc, T: T, node: node, add: add, adEntry: adEntry, rectOf: rectOf};
}

// Canvas -> Bg (full screen, tap-anywhere TOUCH_END like many original games) -> HomeLayer (9 real buttons, the
// ad-boost entries, an original touch button) ; TipMask (full screen, BlockInputEvents + TOUCH_END) ; EntryRow.
function buildHome(kind, entryAt, o) {
  o = o || {};
  var E = makeEngine(kind);
  var canvas = E.node('Canvas', 0, 0, SCREEN.w, SCREEN.h);
  var bg = E.add(canvas, E.node('Bg', 0, 0, SCREEN.w, SCREEN.h));
  if (o.bgTouch !== false) bg.on(E.T.TOUCH_END, function () {});
  var layer = E.add(bg, E.node('HomeLayer', 0, 0, SCREEN.w, SCREEN.h));
  HOME.forEach(function (b) { E.add(layer, E.node(b.name, b.x, b.y, b.w, b.h, {button: true})); });
  var ads = (o.adEntries || AD_ENTRIES).map(function (b) { return E.adEntry(layer, b); });
  var orig = E.add(layer, E.node(ORIGINAL_TOUCH.name, ORIGINAL_TOUCH.x, ORIGINAL_TOUCH.y, ORIGINAL_TOUCH.w, ORIGINAL_TOUCH.h));
  orig.on(E.T.TOUCH_END, function () {});
  var hiddenTouch = E.add(layer, E.node('closedPopupHotspot', 0, 0, 400, 400, {active: false}));
  hiddenTouch.on(E.T.TOUCH_END, function () {});
  if (o.mask !== false) {
    var mask = E.add(canvas, E.node('TipMask', 0, 0, SCREEN.w, SCREEN.h, {block: true}));
    mask.on(E.T.TOUCH_START, function () {});
    mask.size = {w: SCREEN.w * 0.4, h: SCREEN.h * 0.4};   // smaller than the backdrop share: only BlockInputEvents skips it
  }
  var row = E.add(canvas, E.node('EntryRow', 0, -400, SCREEN.w, 100));
  var entries = entryAt.map(function (b) {
    var n = E.add(row, E.node(b.name, b.x, b.y + 400, b.w, b.h, {button: true}));
    var t = E.add(n, E.node('HomeEntryText', 0, 0, b.w, b.h));
    t.on(E.T.TOUCH_END, function () {});                    // inside the entry: skipped with it
    return n;
  });
  return {E: E, canvas: canvas, bg: bg, entries: entries, ads: ads, orig: orig};
}
function boxOf(E, n) {
  var r = E.rectOf(n);
  return {name: n.name, x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height};
}
function insideScreen(b) {
  return b.x - b.w / 2 >= -SCREEN.w / 2 && b.x + b.w / 2 <= SCREEN.w / 2 && b.y - b.h / 2 >= -SCREEN.h / 2 &&
    b.y + b.h / 2 <= SCREEN.h / 2 - SCREEN.h * 0.12;
}
function assertClear(h, label) {
  var now = h.entries.map(function (n) { return boxOf(h.E, n); });
  var targets = HOME.concat(AD_ENTRIES, [ORIGINAL_TOUCH]);
  now.forEach(function (e) {
    targets.forEach(function (b) { assert.ok(!hit(e, b), label + ': ' + e.name + ' covers ' + b.name + ' ' + JSON.stringify(e)); });
    assert.ok(insideScreen(e), label + ': ' + e.name + ' outside the screen ' + JSON.stringify(e));
  });
  assert.ok(!hit(now[0], now[1]), label + ': the two entries overlap');
}

test('button_only_search_lands_on_the_ad_boost_entries', function () {
  // the evidence for the bug: on this home a cc.Button-only search picks exactly where the wheel / check-in sit
  assert.ok(BUTTON_ONLY.ok, BUTTON_ONLY.error);
  BUTTON_ONLY.slots.forEach(function (s, i) { assert.ok(hit(s, AD_ENTRIES[i]), JSON.stringify([s, AD_ENTRIES[i]])); });
});

['24', '3x'].forEach(function (kind) {
  var label = kind === '24' ? 'cocos24' : 'cocos3x';
  test(label + '_entries_moved_off_buttons_and_touch_nodes', function () {
    var h = buildHome(kind, OLD);
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok, r.error);
    assert.strictEqual(r.moved, true);
    var names = r.buttons.map(function (b) { return b.name; });
    ['WheelEntry', 'CheckinEntry', 'btnSignIn'].forEach(function (n) { assert.ok(names.indexOf(n) >= 0, 'not seen: ' + n + ' in ' + names.join(',')); });
    assert.ok(names.indexOf('Icon') < 0 && names.indexOf('closedPopupHotspot') < 0 && names.indexOf('HomeEntryText') < 0, names.join(','));
    assertClear(h, label);
  });
  test(label + '_entries_sitting_on_an_ad_boost_entry_are_moved_not_kept', function () {
    // clear of every cc.Button, but right on the wheel and check-in entries: the N version keeps them there
    var at = BUTTON_ONLY.slots.map(function (s, i) { return {name: OLD[i].name, x: s.x, y: s.y, w: ENTRY.w, h: ENTRY.h}; });
    var h = buildHome(kind, at);
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok, r.error);
    assert.ok(r.moved && !r.kept, 'kept on top of the ad-boost entries: ' + JSON.stringify(r).slice(0, 200));
    assertClear(h, label);
  });
  test(label + '_full_screen_touch_background_and_mask_do_not_block_placing', function () {
    var h = buildHome(kind, OLD);
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok, 'a full-screen touch background must not fill the screen: ' + r.error);
    var names = r.buttons.map(function (b) { return b.name; });
    assert.ok(names.indexOf('Bg') < 0 && names.indexOf('TipMask') < 0, names.join(','));
    assert.deepStrictEqual((r.backdrops || []).slice().sort(), ['Bg', 'TipMask']);
    // the background's children (the real buttons) are still seen
    HOME.forEach(function (b) { assert.ok(names.indexOf(b.name) >= 0, 'missing ' + b.name); });
  });
  test(label + '_removed_listener_and_ignore_option', function () {
    var h = buildHome(kind, OLD);
    var cb = function () {};
    h.orig.off(h.E.T.TOUCH_END, h.orig._ls[h.E.T.TOUCH_END][0]);   // the original button's listener is gone
    h.ads[0].on(h.E.T.TOUCH_START, cb); h.ads[0].off(h.E.T.TOUCH_START, cb);  // still has its TOUCH_END
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries, ignore: [h.ads[1]]});
    assert.ok(r.ok, r.error);
    var names = r.buttons.map(function (b) { return b.name; });
    assert.ok(names.indexOf('btnSignIn') < 0, 'a node without listener is not an obstacle: ' + names.join(','));
    assert.ok(names.indexOf('WheelEntry') >= 0, names.join(','));
    assert.ok(names.indexOf('CheckinEntry') < 0, 'ignore: ' + names.join(','));
  });
  test(label + '_touch_nodes_count_for_kept_entries_too', function () {
    // entries clear of buttons and touch nodes stay where they are (no move for already-right games)
    var clear = [{name: 'ProfileRevisit', x: -150, y: -520, w: 200, h: 80}, {name: 'AddToHome', x: 150, y: -520, w: 200, h: 80}];
    var ads = [{name: 'WheelEntry', x: -280, y: 100, w: 120, h: 120}, {name: 'CheckinEntry', x: 280, y: 100, w: 120, h: 120}];
    var h = buildHome(kind, clear, {adEntries: ads});
    var before = h.entries.map(function (n) { return JSON.stringify(n.position); });
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok && r.kept, JSON.stringify(r).slice(0, 300));
    assert.deepStrictEqual(h.entries.map(function (n) { return JSON.stringify(n.position); }), before);
  });
});

var failed = results.filter(function (r) { return r.status !== 'passed'; }).length;
console.log(JSON.stringify({suite: 'home-entries-touch', passed: results.length - failed, failed: failed, results: results}, null, 2));
if (failed) process.exitCode = 1;
