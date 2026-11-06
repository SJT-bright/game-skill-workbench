'use strict';
// node tests/capsule-auto-3x.test.js  -- 生成时预防 R4G2 (#29, 问题普查 capsule_overlap 15/15): on Cocos 3.x the kit
// plugin scripts plugins-3x/CapsuleLayout.plugin.js + CapsuleAuto.plugin.js move a top bar out from under the TikTok
// capsule with nothing to call. Fake Cocos 3.x (no node.getBoundingBoxToWorld / convertToWorldSpaceAR: boxes on
// cc.UITransform, moves with setWorldPosition), Saul's iPhone 14 (390 x 844 pt @3, capsule 293/51/380/83 pt), design
// 720 x 1280 fit-width. The plugins run as plain global scripts in a vm context, like Cocos 3.x plugin scripts.
// Old way (简化.11.14): no 3.x CapsuleAuto (capsule_auto was 2.4 only, info line): the bar stays under the capsule.
var assert = require('assert');
var fs = require('fs');
var path = require('path');
var vm = require('vm');

var KIT = path.join(__dirname, '..');
var FW = 390, FH = 844, DPR = 3, DW = 720, S = FW / DW, VH = FH / S;
var passed = 0;
function ok(name, fn) {
  var r = fn();
  if (r && typeof r.then === 'function') return r.then(function () { passed++; console.log('ok ' + name); });
  passed++; console.log('ok ' + name);
  return Promise.resolve();
}

function engine() {
  function UITransform() {}
  function Widget() {}
  var listeners = {};
  var cc = { UITransform: UITransform, Widget: Widget, Canvas: function Canvas() {},
    screen: { windowSize: { width: FW * DPR, height: FH * DPR }, devicePixelRatio: DPR },
    view: { getDevicePixelRatio: function () { return DPR; }, getFrameSize: function () { return { width: FW, height: FH }; },
      getViewportRect: function () { return { x: 0, y: 0, width: FW * DPR, height: FH * DPR }; },
      getScaleX: function () { return S * DPR; }, getScaleY: function () { return S * DPR; },
      getVisibleSize: function () { return { width: DW, height: VH }; }, getVisibleOrigin: function () { return { x: 0, y: 0 }; } },
    Director: { EVENT_AFTER_SCENE_LAUNCH: 'director_after_scene_launch', EVENT_AFTER_UPDATE: 'director_after_update' },
    director: { scene: null,
      on: function (e, f) { (listeners[e] = listeners[e] || []).push(f); },
      off: function (e, f) { listeners[e] = (listeners[e] || []).filter(function (g) { return g !== f; }); },
      emit: function (e) { (listeners[e] || []).slice().forEach(function (f) { f(); }); },
      getScene: function () { return cc.director.scene; } },
    _listeners: listeners };
  // 3.x node: translation only (anchor 0.5); world box from the UITransform component
  cc.N = function (name, x, y, w, h, kids, widget) {
    var n = { name: name, x: x, y: y, children: kids || [], activeInHierarchy: true, parent: null, widget: widget || null };
    n.children.forEach(function (c) { c.parent = n; });
    function world() { var p = n.parent ? n.parent.world() : { x: 0, y: 0 }; return { x: p.x + n.x, y: p.y + n.y }; }
    n.world = world;
    var t = new UITransform();
    t.getBoundingBoxToWorld = function () { var c = world(); return { x: c.x - w / 2, y: c.y - h / 2, width: w, height: h }; };
    Object.defineProperty(n, 'worldPosition', { get: function () { var c = world(); return { x: c.x, y: c.y, z: 0 }; } });
    n.setWorldPosition = function (wx, wy) { var p = n.parent ? n.parent.world() : { x: 0, y: 0 }; n.x = wx - p.x; n.y = wy - p.y; };
    n.getComponent = function (k) { return k === UITransform ? t : (k === Widget ? n.widget : null); };
    if (widget) { widget.enabled = true; widget.updateAlignment = function () { n.y = VH - widget.top - h / 2 - (n.parent ? n.parent.world().y : 0); }; }
    return n;
  };
  return cc;
}

function sandbox(cc) {
  var sdk = { getSystemInfoSync: function () { return { windowWidth: FW, windowHeight: FH, pixelRatio: DPR, statusBarHeight: 47 }; },
    getMenuButtonBoundingClientRect: function () { return { left: 293 * 3, top: 51 * 3, right: 380 * 3, bottom: 83 * 3 }; } };
  var g = { console: console, setTimeout: setTimeout, clearTimeout: clearTimeout, TTMinis: { game: sdk } };
  if (cc) g.cc = cc;
  vm.createContext(g);
  ['CapsuleLayout', 'CapsuleAuto'].forEach(function (name) {     // load order of plugin scripts is not fixed: Auto last here
    var file = path.join(KIT, 'plugins-3x', name + '.plugin.js');
    assert.ok(fs.existsSync(file), 'old way: no 3.x plugin ' + path.relative(KIT, file) + ' (capsule_auto is 2.4 only)');
    vm.runInContext(fs.readFileSync(file, 'utf8'), g, { filename: file });
  });
  return g;
}

function scene(cc) {
  var coin = cc.N('coinLabel', 250, 0, 120, 60);
  var bar = cc.N('TopBar', 0, VH / 2 - 50, DW, 100, [coin]);
  var left = cc.N('LeftCoins', -260, VH / 2 - 50, 160, 70);
  var bg = cc.N('Background', 0, 0, DW, VH);
  var canvas = cc.N('Canvas', DW / 2, VH / 2, DW, VH, [bg, bar, left]);
  var sc = { getComponentInChildren: function (k) { return k === cc.Canvas ? { node: canvas } : null; } };
  return { canvas: canvas, bar: bar, coin: coin, left: left, bg: bg, scene: sc };
}
function top(cc, n) { var b = n.getComponent(cc.UITransform).getBoundingBoxToWorld(); return b.y + b.height; }

var tests = [];
tests.push(function () { return ok('KIT_PARTS_3X lists capsulelayout3x / capsuleauto3x (step capsule_auto) with the plugin hashes', function () {
  var parts = JSON.parse(fs.readFileSync(path.join(KIT, 'parts-3x', 'KIT_PARTS_3X.json'), 'utf8')).parts;
  var crypto = require('crypto');
  ['capsulelayout3x', 'capsuleauto3x'].forEach(function (k) {
    assert.ok(parts[k], 'old way: KIT_PARTS_3X has no ' + k);
    assert.strictEqual(parts[k].step, 'capsule_auto');
    assert.strictEqual(parts[k].plugin, true);
    var data = fs.readFileSync(path.join(KIT, parts[k].file.src));
    assert.strictEqual(crypto.createHash('sha256').update(data).digest('hex'), parts[k].file.sha256);
  });
}); });

tests.push(function () { return ok('3.x: the top bar under the capsule moves just below it; left coins and background stay', function () {
  var cc = engine(), g = sandbox(cc), s = scene(cc);
  var Capsule = g.TikTokKit.CapsuleLayout, SAFE = Capsule.safeTopY(cc, 8);
  assert.ok(top(cc, s.bar) > SAFE + 1, 'fixture: bar starts under the capsule');
  var leftTop = top(cc, s.left), bgY = s.bg.y;
  var moved = g.TikTokKit.CapsuleAuto.pass(cc, s.canvas);
  assert.strictEqual(JSON.stringify(moved.map(function (m) { return m.name; })), '["TopBar"]');
  assert.ok(Math.abs(top(cc, s.bar) - SAFE) < 0.01, 'bar top on safeTopY, got ' + top(cc, s.bar) + ' vs ' + SAFE);
  assert.ok(Math.abs(top(cc, s.coin) - (top(cc, s.bar) - 50 + 30)) < 0.01, 'child moved with its parent, once');
  assert.strictEqual(top(cc, s.left), leftTop, 'left coin counter beside the capsule stays');
  assert.strictEqual(s.bg.y, bgY, 'full-screen background is not a bar');
  assert.strictEqual(g.TikTokKit.CapsuleAuto.pass(cc, s.canvas).length, 0, 'second pass changes nothing');
}); });

tests.push(function () { return ok('3.x: a top-aligned cc.Widget gets widget.top += dy', function () {
  var cc = engine(), g = sandbox(cc);
  var w = { isAlignTop: true, top: 20 };
  var bar = cc.N('HudTop', 0, 0, DW, 100, [], w);
  var canvas = cc.N('Canvas', DW / 2, VH / 2, DW, VH, [bar]);
  w.updateAlignment();
  var before = w.top, SAFE = g.TikTokKit.CapsuleLayout.safeTopY(cc, 8);
  g.TikTokKit.CapsuleAuto.pass(cc, canvas);
  assert.ok(w.top > before, 'widget.top grew');
  assert.ok(Math.abs(top(cc, bar) - SAFE) < 0.01);
}); });

tests.push(function () { return ok('3.x: the plugin starts by itself (eager) once cc exists and passes after scene launch', function () {
  var g = sandbox(null);                                   // plugin scripts ran before the engine namespace
  var cc = engine(), s = scene(cc);
  g.cc = cc;
  return new Promise(function (resolve) { setTimeout(resolve, 350); }).then(function () {
    assert.ok((cc._listeners[cc.Director.EVENT_AFTER_SCENE_LAUNCH] || []).length === 1, 'listens to scene launch');
    cc.director.scene = s.scene;
    cc.director.emit(cc.Director.EVENT_AFTER_SCENE_LAUNCH);
    cc.director.emit(cc.Director.EVENT_AFTER_UPDATE);      // frame 0
    cc.director.emit(cc.Director.EVENT_AFTER_UPDATE);      // frame 1: pass
    assert.ok(Math.abs(top(cc, s.bar) - g.TikTokKit.CapsuleLayout.safeTopY(cc, 8)) < 0.01, 'bar moved by the auto pass');
  });
}); });

tests.reduce(function (p, t) { return p.then(t); }, Promise.resolve()).then(function () {
  console.log(passed + ' tests passed');
}).catch(function (e) { console.error('FAIL', e && e.message); process.exit(1); });
