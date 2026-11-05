'use strict';
// HomeGrowthEntries places its two entries at runtime (生成时预防 N 批, P06 3 / P14 2): from the boxes of the home's
// own cc.Button nodes, with the search of tools/home_free_slot.js. Real home: 蛋壳特工队 (MRTGD-English, Cocos 3.8.8)
// docs/test/stage5/09-home.dump.json, 9 buttons (sha256 b3c34bbbd6b2b223...). On 11-03 the AI hand-wrote the entries
// at (-150, -620) / (150, -620), 200x70, and they covered the original bottom bar (survey platform_entry_overlap).
// Same home as a Cocos 2.4 node tree and as a 3.x (UITransform) node tree. Node only, a fraction of a second.
var assert = require('assert'), path = require('path');
var HGE = require(process.env.HOME_ENTRIES || path.join(__dirname, '..', 'assets', 'tiktok-platform', 'HomeGrowthEntries.js'));
var TOOL = require(path.join(__dirname, '..', 'tools', 'home_free_slot.js'));
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

// 393x852 css page, fit width -> 720 x 1561 design units
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
var OLD = [{name: 'ProfileRevisit', x: -150, y: -620, w: 200, h: 70}, {name: 'AddToHome', x: 150, y: -620, w: 200, h: 70}];

function hit(a, b) { return TOOL.intersects(a, b); }

// ------------------------------------------------------------------ tiny engines (translation + scale only)
function Btn() {}
function makeEngine(kind) {
  var cc = {Button: Btn, v2: function (x, y) { return {x: x, y: y}; }, v3: function (x, y, z) { return {x: x, y: y, z: z || 0}; }};
  function world(n) {                       // node -> {x, y, sx, sy}: where its local origin sits in the world
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
  if (kind === '3x') {
    cc.UITransform = function UITransform() {};
  }
  function node(name, x, y, w, h, opts) {
    opts = opts || {};
    var n = {name: name, position: {x: x, y: y, z: 0}, scale: opts.scale || 1, size: {w: w, h: h},
      anchor: opts.anchor || {x: 0.5, y: 0.5}, children: [], parent: null, active: opts.active !== false,
      comps: []};
    n.setPosition = function (v) { n.position = {x: v.x, y: v.y, z: 0}; };
    n.getComponent = function (T) { return n.comps.filter(function (c) { return c instanceof T || c.type === T; })[0] || null; };
    if (kind === '24') {                     // Cocos 2.4: the node carries size and the space conversions
      n.opacity = opts.opacity === undefined ? 255 : opts.opacity;
      n.getBoundingBoxToWorld = function () { return rectOf(n); };
      n.convertToNodeSpaceAR = function (v) { return toLocal(n, v); };
      n.convertToWorldSpaceAR = function (v) { return toWorld(n, v); };
    } else {                                 // Cocos 3.x: UITransform does; opacity on cc.UIOpacity
      var t = new cc.UITransform();
      t.getBoundingBoxToWorld = function () { return rectOf(n); };
      t.convertToNodeSpaceAR = function (v) { return toLocal(n, v); };
      t.convertToWorldSpaceAR = function (v) { return toWorld(n, v); };
      n.comps.push(t);
      if (opts.opacity !== undefined) n.comps.push({type: 'cc.UIOpacity', opacity: opts.opacity});
      var get = n.getComponent;
      n.getComponent = function (T) {
        if (T === 'cc.UIOpacity') return n.comps.filter(function (c) { return c.type === 'cc.UIOpacity'; })[0] || null;
        return get(T);
      };
    }
    if (opts.button) n.comps.push(new Btn());
    return n;
  }
  function add(parent, child) { child.parent = parent; parent.children.push(child); return child; }
  return {cc: cc, node: node, add: add, rectOf: rectOf};
}

// The 蛋壳特工队 home as a node tree: Canvas -> HomeLayer -> Layout (bottom bar, offset) / TopUILayer / Tower; the
// entries live in their own row node with the AI's old hand-written positions.
function buildHome(kind, entryAt, extraButtons) {
  var E = makeEngine(kind);
  var canvas = E.node('Canvas', 0, 0, SCREEN.w, SCREEN.h);
  var layer = E.add(canvas, E.node('HomeLayer', 0, 0, SCREEN.w, SCREEN.h));
  var bar = E.add(layer, E.node('Layout', 0, -675, SCREEN.w, 114));
  var topUi = E.add(layer, E.node('TopUILayer', 0, 600, SCREEN.w, 200, {scale: 2}));
  HOME.forEach(function (b) {
    var p = /^ui_btn/.test(b.name) ? bar : (/Node$/.test(b.name) ? topUi : layer);
    var s = p === topUi ? 2 : 1, off = p === bar ? {x: 0, y: -675} : (p === topUi ? {x: 0, y: 600} : {x: 0, y: 0});
    // anchor (0, 1) for the bar buttons, like Layout children often have: the box, not the position, is what counts
    var anchor = p === bar ? {x: 0, y: 1} : {x: 0.5, y: 0.5};
    var lx = (b.x - off.x) / s - (0.5 - anchor.x) * b.w / s, ly = (b.y - off.y) / s - (0.5 - anchor.y) * b.h / s;
    E.add(p, E.node(b.name, lx, ly, b.w / s, b.h / s, {button: true, anchor: anchor}));
  });
  (extraButtons || []).forEach(function (b) { E.add(layer, E.node(b.name, b.x, b.y, b.w, b.h, {button: true})); });
  // a hidden popup's button and a faded one: not on screen, must not count
  E.add(layer, E.node('popupClose', 0, -620, 300, 300, {button: true, active: false}));
  E.add(layer, E.node('fadedBtn', 0, -620, 300, 300, {button: true, opacity: 0}));
  var row = E.add(canvas, E.node('EntryRow', 0, -400, SCREEN.w, 100));
  var entries = entryAt.map(function (b) {
    var n = E.add(row, E.node(b.name, b.x - 0, b.y + 400, b.w, b.h, {button: true}));
    E.add(n, E.node('HomeEntryText', 0, 0, b.w, b.h, {button: true}));   // a child button inside the entry: skipped
    return n;
  });
  return {E: E, canvas: canvas, entries: entries};
}
function boxOf(E, n) {
  var r = E.rectOf(n);
  return {name: n.name, x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height};
}
function insideScreen(b) {
  return b.x - b.w / 2 >= -SCREEN.w / 2 && b.x + b.w / 2 <= SCREEN.w / 2 && b.y - b.h / 2 >= -SCREEN.h / 2 &&
    b.y + b.h / 2 <= SCREEN.h / 2 - SCREEN.h * 0.12;
}

test('old_hand_written_entry_coordinates_cover_the_real_bottom_bar', function () {
  var covered = [];
  OLD.forEach(function (e) { HOME.forEach(function (b) { if (hit(e, b)) covered.push(e.name + '>' + b.name); }); });
  assert.ok(covered.length >= 2, 'the old coordinates should cover original buttons: ' + covered.join(', '));
  assert.ok(covered.some(function (c) { return /ui_btn/.test(c); }), covered.join(', '));
});

['24', '3x'].forEach(function (kind) {
  var label = kind === '24' ? 'cocos24' : 'cocos3x';
  test(label + '_runtime_moves_the_entries_off_every_button', function () {
    var h = buildHome(kind, OLD);
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok, r.error);
    assert.strictEqual(r.moved, true);
    assert.strictEqual(r.buttons.length, HOME.length, 'buttons found: ' + r.buttons.map(function (b) { return b.name; }).join(','));
    var now = h.entries.map(function (n) { return boxOf(h.E, n); });
    now.forEach(function (e) {
      HOME.forEach(function (b) { assert.ok(!hit(e, b), e.name + ' still covers ' + b.name + ' ' + JSON.stringify(e)); });
      assert.ok(insideScreen(e), e.name + ' outside the screen ' + JSON.stringify(e));
      assert.strictEqual(Math.round(e.w), 200); assert.strictEqual(Math.round(e.h), 70);
    });
    assert.ok(!hit(now[0], now[1]), 'the two entries overlap');
    // the same place the generation tool gives for this home
    var t = TOOL.findFreeSlots({screen: SCREEN, buttons: HOME, entry: {w: 200, h: 70}});
    now.forEach(function (e, i) {
      assert.ok(Math.abs(e.x - t.slots[i].x) < 1e-6 && Math.abs(e.y - t.slots[i].y) < 1e-6, JSON.stringify([e, t.slots[i]]));
    });
  });
  test(label + '_entries_already_clear_are_not_moved', function () {
    var clear = [{name: 'ProfileRevisit', x: -150, y: -520, w: 200, h: 80}, {name: 'AddToHome', x: 150, y: -520, w: 200, h: 80}];
    var h = buildHome(kind, clear);
    var before = h.entries.map(function (n) { return JSON.stringify(n.position); });
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.ok(r.ok && r.kept, JSON.stringify(r).slice(0, 300));
    assert.deepStrictEqual(h.entries.map(function (n) { return JSON.stringify(n.position); }), before);
  });
  test(label + '_no_room_is_an_error_and_nothing_moves', function () {
    var wall = [];
    for (var y = -760; y <= 760; y += 120) for (var x = -320; x <= 320; x += 160) wall.push({name: 'b' + x + '_' + y, x: x, y: y, w: 150, h: 110});
    var h = buildHome(kind, OLD, wall);
    var before = h.entries.map(function (n) { return JSON.stringify(n.position); });
    var r = HGE.placeEntries(h.E.cc, {root: h.canvas, entries: h.entries});
    assert.strictEqual(r.ok, false);
    assert.ok(/do not guess a position/.test(r.error), r.error);
    assert.deepStrictEqual(h.entries.map(function (n) { return JSON.stringify(n.position); }), before);
  });
});

test('same_search_as_tools_home_free_slot_on_the_real_home_and_200_random_homes', function () {
  var seed = 7;
  function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
  var cases = [{screen: SCREEN, buttons: HOME, entry: {w: 200, h: 70}}, {screen: SCREEN, buttons: HOME, entry: {w: 140, h: 140}}];
  for (var i = 0; i < 200; i++) {
    var screen = {w: 720, h: 1280 + Math.round(rnd() * 400)}, buttons = [];
    for (var k = Math.floor(rnd() * (i % 4 === 3 ? 60 : 12)); k > 0; k--) {
      buttons.push({name: 'b' + k, x: Math.round((rnd() - 0.5) * 700), y: Math.round((rnd() - 0.5) * screen.h),
        w: 60 + Math.round(rnd() * 300), h: 50 + Math.round(rnd() * 200)});
    }
    cases.push({screen: screen, buttons: buttons, entry: {w: 100 + Math.round(rnd() * 120), h: 60 + Math.round(rnd() * 100)},
      gap: rnd() < 0.3 ? 8 : undefined});
  }
  var okCount = 0, failCount = 0;
  cases.forEach(function (c, i) {
    var a = HGE.findFreeSlots(c), b = TOOL.findFreeSlots(c);
    assert.deepStrictEqual(a, b, 'case ' + i + ' differs');
    if (a.ok) okCount++; else failCount++;
  });
  assert.ok(okCount > 50 && failCount > 0, 'random homes should give both results: ok ' + okCount + ', no room ' + failCount);
});

test('component_api_exported_for_2_4_and_node', function () {
  assert.strictEqual(typeof HGE.findFreeSlots, 'function');
  assert.strictEqual(typeof HGE.placeEntries, 'function');
  assert.strictEqual(HGE.Controller.placeEntries, HGE.placeEntries);
});

var failed = results.filter(function (r) { return r.status !== 'passed'; }).length;
console.log(JSON.stringify({suite: 'home-entries-slot', passed: results.length - failed, failed: failed, results: results}, null, 2));
if (failed) process.exitCode = 1;
