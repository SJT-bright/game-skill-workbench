'use strict';
// node tests/capsule-auto.test.js  -- parts/CapsuleAuto.js (生成时预防 P06 第 4 点): the top bar moves out from under
// the capsule with nothing to call. Fake Cocos 2.4: Saul's iPhone 14 (390 x 844 pt @3, capsule 293/51/380/83 pt),
// design 720 x 1280 fit-width (visible 720 x 1558). Old way (CapsuleLayout opt-in, nobody calls it): the bar stays
// under the capsule (census: 99 overlaps in 64 games, 16 top bars / coin counters under the capsule).
var assert = require('assert');
var path = require('path');
require(path.join(__dirname, '..', 'parts', 'CapsuleLayout.js'));          // sets globalThis.TikTokCapsuleLayout
var Auto = require(path.join(__dirname, '..', 'parts', 'CapsuleAuto.js'));

var FW = 390, FH = 844, DPR = 3, DW = 720, S = FW / DW, VH = FH / S;
var SDK = { getSystemInfoSync: function () { return { windowWidth: FW, windowHeight: FH, pixelRatio: DPR, statusBarHeight: 47 }; },
  getMenuButtonBoundingClientRect: function () { return { left: 293 * 3, top: 51 * 3, right: 380 * 3, bottom: 83 * 3 }; } }; // px build
function Widget() {}
var cc = { v2: function (x, y) { return { x: x, y: y }; }, Widget: Widget,
  view: { getDevicePixelRatio: function () { return DPR; }, getFrameSize: function () { return { width: FW, height: FH }; },
    getViewportRect: function () { return { x: 0, y: 0, width: FW * DPR, height: FH * DPR }; },
    getScaleX: function () { return S * DPR; }, getScaleY: function () { return S * DPR; },
    getVisibleSize: function () { return { width: DW, height: VH }; }, getVisibleOrigin: function () { return { x: 0, y: 0 }; } } };
global.TTMinis = { game: SDK };

// translation-only scene graph (anchor 0.5): world = parent world + local
function N(name, x, y, w, h, kids, widget) {
  var n = { name: name, x: x, y: y, w: w, h: h, children: kids || [], activeInHierarchy: true, parent: null, widget: widget || null };
  n.children.forEach(function (c) { c.parent = n; });
  n.world = function () { var p = n.parent ? n.parent.world() : { x: 0, y: 0 }; return { x: p.x + n.x, y: p.y + n.y }; };
  n.getBoundingBoxToWorld = function () { var c = n.world(); return { x: c.x - w / 2, y: c.y - h / 2, width: w, height: h }; };
  n.convertToWorldSpaceAR = function (p) { var c = n.world(); return { x: c.x + p.x, y: c.y + p.y }; };
  n.convertToNodeSpaceAR = function (p) { var c = n.world(); return { x: p.x - c.x, y: p.y - c.y }; };
  n.setPosition = function (p) { n.x = p.x; n.y = p.y; };
  n.getComponent = function (k) { return k === Widget ? n.widget : null; };
  if (widget) { widget.enabled = true; widget.updateAlignment = function () { n.y = VH - widget.top - h / 2 - (n.parent ? n.parent.world().y : 0); }; }
  return n;
}
function top(n) { var b = n.getBoundingBoxToWorld(); return b.y + b.height; }
var CAP = global.TikTokCapsuleLayout.designRect(cc, SDK), SAFE = global.TikTokCapsuleLayout.safeTopY(cc, 8, SDK);
function under(n) { var b = n.getBoundingBoxToWorld(); return b.x + b.width > CAP.left && b.x < CAP.right && top(n) > SAFE + 0.5; }

function scene() {
  var coinLabel = N('coinLabel', 250, 0, 120, 60);
  var bar = N('TopBar', 0, VH / 2 - 60, 720, 120, [coinLabel]);
  var leftCoin = N('CoinBox', -280, VH / 2 - 50, 120, 60);
  var bg = N('bg', 0, 0, 720, VH);
  var settings = N('settingsBtn', 280, VH / 2 - 70, 100, 100);
  var shop = N('coinShopPanel', 0, -80, 600, 300);
  var page = N('Page_Home', 0, 0, 720, VH, [settings, shop]);
  var canvas = N('Canvas', DW / 2, VH / 2, 720, VH, [bg, bar, leftCoin, page]);
  return { canvas: canvas, bar: bar, coinLabel: coinLabel, leftCoin: leftCoin, bg: bg, settings: settings, shop: shop, page: page };
}
var n = 0;
function ok(name, fn) { fn(); n++; console.log('ok ' + name); }

ok('old way (CapsuleLayout opt-in, nothing calls it): TopBar and settingsBtn sit under the capsule', function () {
  var s = scene();
  assert.ok(under(s.bar), 'TopBar should overlap the capsule in the fixture');
  assert.ok(under(s.settings), 'settingsBtn should overlap the capsule in the fixture');
});
ok('one pass: TopBar (name) and settingsBtn (top 15% of a page root) move just below the capsule', function () {
  var s = scene(), moved = Auto.pass(cc, s.canvas, SDK);
  assert.deepStrictEqual(moved.map(function (m) { return m.name; }).sort(), ['TopBar', 'settingsBtn']);
  assert.ok(!under(s.bar) && !under(s.settings), 'still under the capsule after the pass');
  assert.ok(Math.abs(top(s.bar) - SAFE) < 1e-6, 'bar top on the safe line: ' + top(s.bar) + ' vs ' + SAFE);
});
ok('nothing else moves: left coin box, full-screen bg and page root, coin panel in the middle, child of a moved bar', function () {
  var s = scene(), before = [s.leftCoin, s.bg, s.page, s.shop].map(top), childY = s.coinLabel.y;
  Auto.pass(cc, s.canvas, SDK);
  assert.deepStrictEqual([s.leftCoin, s.bg, s.page, s.shop].map(top), before);
  assert.strictEqual(s.coinLabel.y, childY, 'child moved twice');
});
ok('second pass changes nothing (idempotent; runs again every 30 frames)', function () {
  var s = scene();
  Auto.pass(cc, s.canvas, SDK);
  assert.deepStrictEqual(Auto.pass(cc, s.canvas, SDK), []);
});
ok('a top-aligned cc.Widget gets widget.top += dy instead of a position that would snap back', function () {
  var w = { isAlignTop: true, isAlignBottom: false, top: 0 };
  var hud = N('hud', 0, VH / 2 - 50, 720, 100, [], w);
  var canvas = N('Canvas', DW / 2, VH / 2, 720, VH, [hud]);
  var moved = Auto.pass(cc, canvas, SDK);
  assert.strictEqual(moved.length, 1);
  assert.ok(Math.abs(w.top - moved[0].dy) < 1e-6, 'widget.top ' + w.top);
});
ok('switches: TikTokCapsuleAuto.off and a nocapsule name leave the bar alone', function () {
  var s = scene();
  Auto.off = true; assert.deepStrictEqual(Auto.pass(cc, s.canvas, SDK), []); Auto.off = false;
  s.bar.name = 'TopBar_nocapsule'; s.settings.name = 'settings_nocapsule';
  assert.deepStrictEqual(Auto.pass(cc, s.canvas, SDK), []);
});
ok('install listens to EVENT_AFTER_SCENE_LAUNCH and runs a pass on the first frame after it', function () {
  var s = scene(), on = {}, offs = 0;
  var dir = { on: function (e, f) { on[e] = f; }, off: function () { offs++; }, getScene: function () {
    return { getComponentInChildren: function () { return { node: s.canvas }; } }; } };
  var cc2 = Object.assign({}, cc, { director: dir, Director: { EVENT_AFTER_SCENE_LAUNCH: 'L', EVENT_AFTER_UPDATE: 'U' }, Canvas: function () {} });
  assert.ok(Auto.install(cc2));
  on.L(); on.U(); assert.ok(under(s.bar), 'frame 0: widgets not aligned yet, no pass');
  on.U(); assert.ok(!under(s.bar), 'frame 1: pass ran');
});
console.log(n + ' tests passed');
