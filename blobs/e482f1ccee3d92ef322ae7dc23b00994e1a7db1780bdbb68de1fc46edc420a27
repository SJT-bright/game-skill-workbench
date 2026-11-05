'use strict';
// node tests/screen-fit.test.js  -- parts/ScreenFit.js (v7.9, 生成时预防 P07): background cover, safe-area groups and one
// canvas fit, from the engine's REAL visible rect. Fake engines: Cocos 2.4 (node.x/scaleX/width, convertToWorldSpaceAR,
// getBoundingBoxToWorld with children) and 3.x (UITransform, worldPosition, setWorldPosition, ResolutionPolicy).
// Design 720 x 1280 portrait. Visible sizes: 720x1280 (16:9), 720x1560 (19.5:9 long phone), 900x1200 (tablet-like) and a
// 2133x1200 desktop window. Negative controls: the old design-size background (scale 1 at the centre), a Canvas with
// fitWidth AND fitHeight on, and a top bar whose icon sits at -80 clamped by its own anchor only.
var assert = require('assert');
var path = require('path');
var Fit = require(path.join(__dirname, '..', 'parts', 'ScreenFit.js'));

// ---------- a tiny scene model shared by both fake engines ----------
function Model(o) {
  o = o || {};
  this.x = o.x || 0; this.y = o.y || 0; this.sx = o.sx == null ? 1 : o.sx; this.sy = o.sy == null ? 1 : o.sy;
  this.w = o.w || 0; this.h = o.h || 0; this.ax = o.ax == null ? 0.5 : o.ax; this.ay = o.ay == null ? 0.5 : o.ay;
  this.parent = null; this.kids = [];
}
Model.prototype.add = function (k) { k.parent = this; this.kids.push(k); return k; };
Model.prototype.w2 = function (lx, ly) {          // local point -> world
  var x = this.x + lx * this.sx, y = this.y + ly * this.sy;
  return this.parent ? this.parent.w2(x, y) : { x: x, y: y };
};
Model.prototype.l2 = function (wx, wy) {          // world point -> local
  var p = this.parent ? this.parent.l2(wx, wy) : { x: wx, y: wy };
  return { x: (p.x - this.x) / this.sx, y: (p.y - this.y) / this.sy };
};
Model.prototype.box = function () {               // world AABB, children included (like the engines)
  var l = -this.ax * this.w, b = -this.ay * this.h, a = this.w2(l, b), c = this.w2(l + this.w, b + this.h);
  var r = this.w > 0 || this.h > 0 ? { left: Math.min(a.x, c.x), right: Math.max(a.x, c.x), bottom: Math.min(a.y, c.y), top: Math.max(a.y, c.y) } : null;
  this.kids.forEach(function (k) { var q = k.box(); if (!q) return; r = r ? { left: Math.min(r.left, q.left), right: Math.max(r.right, q.right), bottom: Math.min(r.bottom, q.bottom), top: Math.max(r.top, q.top) } : q; });
  return r;
};
function rect(b) { return { x: b.left, y: b.bottom, width: b.right - b.left, height: b.top - b.bottom }; }

// ---------- Cocos 2.4 fake ----------
function cc24(vw, vh, extra) {
  extra = extra || {};
  return {
    v2: function (x, y) { return { x: x, y: y }; },
    view: { getVisibleSize: function () { return { width: vw, height: vh }; }, getVisibleOrigin: function () { return extra.origin || { x: 0, y: 0 }; },
      getDesignResolutionSize: function () { return { width: 720, height: 1280 }; } },
    sys: extra.safe ? { getSafeAreaRect: function () { return extra.safe; } } : undefined
  };
}
function n24(m) {
  var n = {
    _m: m, get x() { return m.x; }, set x(v) { m.x = v; }, get y() { return m.y; }, set y(v) { m.y = v; },
    get scaleX() { return m.sx; }, set scaleX(v) { m.sx = v; }, get scaleY() { return m.sy; }, set scaleY(v) { m.sy = v; },
    get width() { return m.w; }, get height() { return m.h; }, get anchorX() { return m.ax; }, get anchorY() { return m.ay; },
    setPosition: function (x, y) { m.x = x; m.y = y; },
    convertToWorldSpaceAR: function (p) { return m.w2(p.x, p.y); },
    convertToNodeSpaceAR: function (p) { return m.l2(p.x, p.y); },
    getBoundingBoxToWorld: function () { return rect(m.box()); }
  };
  return n;
}
// scene: Canvas node at the visible centre (as the 2.4 Canvas component puts it)
function scene24(cc) {
  var vs = cc.view.getVisibleSize(), vo = cc.view.getVisibleOrigin();
  var canvas = new Model({ x: vo.x + vs.width / 2, y: vo.y + vs.height / 2, w: vs.width, h: vs.height });
  return { root: canvas, node: function (o, parent) { var m = (parent || canvas).add(new Model(o)); var n = n24(m); n.parent = n24(m.parent); return n; } };
}

// ---------- Cocos 3.x fake ----------
function cc3(vw, vh, extra) {
  var cc = cc24(vw, vh, extra);
  cc.UITransform = function () {};
  cc.Vec3 = function (x, y, z) { this.x = x; this.y = y; this.z = z; };
  return cc;
}
function n3(cc, m) {
  var t = { get width() { return m.w; }, get height() { return m.h; }, get anchorX() { return m.ax; }, get anchorY() { return m.ay; },
    convertToWorldSpaceAR: function (p) { return m.w2(p.x, p.y); }, convertToNodeSpaceAR: function (p) { return m.l2(p.x, p.y); },
    getBoundingBoxToWorld: function () { return rect(m.box()); } };
  return {
    _m: m, get position() { return { x: m.x, y: m.y, z: 0 }; }, get scale() { return { x: m.sx, y: m.sy, z: 1 }; },
    get worldPosition() { var p = m.w2(0, 0); return { x: p.x, y: p.y, z: 0 }; },
    setPosition: function (x, y) { m.x = x; m.y = y; }, setScale: function (x, y) { m.sx = x; m.sy = y; },
    setWorldPosition: function (x, y) { var p = m.parent ? m.parent.l2(x, y) : { x: x, y: y }; m.x = p.x; m.y = p.y; },
    getComponent: function (K) { return K === cc.UITransform ? t : null; }
  };
}
function scene3(cc) {
  var vs = cc.view.getVisibleSize(), vo = cc.view.getVisibleOrigin();
  var canvas = new Model({ x: vo.x + vs.width / 2, y: vo.y + vs.height / 2, w: vs.width, h: vs.height });
  return { root: canvas, node: function (o, parent) { var m = (parent || canvas).add(new Model(o)); var n = n3(cc, m); n.parent = n3(cc, m.parent); return n; } };
}

var results = [];
function test(name, fn) {
  try { fn(); results.push(['PASS', name]); } catch (e) { results.push(['FAIL', name + ': ' + (e && e.stack || e)]); }
}
var EPS = 1e-6;
function coversAll(box, vis) { return box.left <= vis.left + EPS && box.right >= vis.right - EPS && box.bottom <= vis.bottom + EPS && box.top >= vis.top - EPS; }
function inside(box, r, m) { m = m || 0; return box.left >= r.left + m - EPS && box.right <= r.right - m + EPS && box.bottom >= r.bottom + m - EPS && box.top <= r.top - m + EPS; }

var SCREENS = [[720, 1280], [720, 1560], [900, 1200], [2133, 1200]];

test('cover: 2.4 background covers the real visible rect on every screen, picture ratio kept', function () {
  SCREENS.forEach(function (s) {
    var cc = cc24(s[0], s[1]), sc = scene24(cc), bg = sc.node({ w: 720, h: 1280 });
    var r = Fit.cover(cc, bg);
    var box = bg._m.box(), vis = Fit.visibleRect(cc);
    assert.ok(coversAll(box, vis), s.join('x') + ' not covered: ' + JSON.stringify(box));
    assert.strictEqual(bg.scaleX, bg.scaleY, 'uniform scale');
    assert.ok(Math.abs((box.right - box.left) / (box.top - box.bottom) - 720 / 1280) < 1e-9, 'ratio kept');
    assert.strictEqual(r.scale, bg.scaleX);
  });
});

test('negative control: the old design-size background (scale 1 at the centre) leaves edges on the wide screens', function () {
  var bad = 0;
  SCREENS.forEach(function (s) {
    var cc = cc24(s[0], s[1]), sc = scene24(cc), bg = sc.node({ w: 720, h: 1280 });   // as built: 720x1280, scale 1
    if (!coversAll(bg._m.box(), Fit.visibleRect(cc))) bad++;
  });
  assert.strictEqual(bad, 3, '720x1560, 900x1200 and the desktop window show edges with the design-size background');
});

test('cover: 3.x API, scaled parent, corner anchor, mirrored picture, visible origin off 0', function () {
  var cc = cc3(900, 1200, { origin: { x: -90, y: 40 } }), sc = scene3(cc);
  var layer = sc.node({ sx: 0.5, sy: 0.5, x: 30, y: -20 });
  var bg = sc.node({ w: 720, h: 1280, ax: 0, ay: 0, sx: -1 }, layer._m);
  Fit.cover(cc, bg);
  assert.ok(coversAll(bg._m.box(), Fit.visibleRect(cc)), JSON.stringify(bg._m.box()));
  assert.ok(bg._m.sx < 0 && bg._m.sy > 0, 'mirror kept');
  var b = bg._m.box(), vis = Fit.visibleRect(cc);
  assert.ok(Math.abs((b.left + b.right) / 2 - (vis.left + vis.right) / 2) < 1e-6, 'centred x');
  assert.ok(Math.abs((b.bottom + b.top) / 2 - (vis.bottom + vis.top) / 2) < 1e-6, 'centred y');
});

test('cover: opts.watch re-covers on canvas-resize; a node without size throws', function () {
  var size = { width: 720, height: 1280 }, handlers = {};
  var cc = cc24(720, 1280);
  cc.view.getVisibleSize = function () { return size; };
  cc.view.on = function (e, fn) { (handlers[e] = handlers[e] || []).push(fn); };
  cc.view.off = function (e, fn) { handlers[e] = (handlers[e] || []).filter(function (f) { return f !== fn; }); };
  var sc = scene24(cc), bg = sc.node({ w: 720, h: 1280 });
  var h = Fit.cover(cc, bg, { watch: true });
  size = { width: 2133, height: 1200 }; sc.root.x = 2133 / 2; sc.root.y = 600;
  handlers['canvas-resize'].forEach(function (f) { f(); });
  assert.ok(coversAll(bg._m.box(), Fit.visibleRect(cc)), 'after resize');
  h.off(); assert.strictEqual(handlers['canvas-resize'].length, 0);
  assert.throws(function () { Fit.cover(cc, sc.node({})); }, /no size/);
});

test('safeTop: a top bar with its icon at -80 ends up inside the safe rect as a whole (2.4 and 3.x)', function () {
  [[cc24, scene24], [cc3, scene3]].forEach(function (E) {
    [[720, 1280], [720, 1560]].forEach(function (s) {
      var cc = E[0](s[0], s[1], { safe: { x: 0, y: 0, width: s[0], height: s[1] - 88 } }), sc = E[1](cc);
      // bar anchored at the left edge of the design (x -300), top at the design top; icon child 80 further left
      var bar = sc.node({ x: -300, y: 600, w: 200, h: 90 });
      sc.node({ x: -80, y: 0, w: 100, h: 100 }, bar._m);
      var before = bar._m.box(), rect = Fit.safeRect(cc);
      assert.ok(!inside(before, rect, Fit.MARGIN), 'the built bar sticks out: ' + JSON.stringify(before));
      var r = Fit.safeTop(cc, bar);
      assert.ok(r.fits);
      assert.ok(inside(bar._m.box(), rect, Fit.MARGIN), s.join('x') + ' ' + JSON.stringify(bar._m.box()));
    });
  });
});

test('negative control: clamping only the bar anchor (old per-node fix) leaves the -80 icon outside', function () {
  var cc = cc24(720, 1280, { safe: { x: 0, y: 0, width: 720, height: 1192 } }), sc = scene24(cc);
  var bar = sc.node({ x: -300, y: 600, w: 200, h: 90 });
  sc.node({ x: -80, y: 0, w: 100, h: 100 }, bar._m);
  var rect = Fit.safeRect(cc), w = bar.convertToWorldSpaceAR({ x: 0, y: 0 });
  var minX = rect.left + 8 + 100;                          // half the bar's own width + margin, no children
  if (w.x < minX) bar.x += minX - w.x;
  var topMax = rect.top - 8 - 45; if (w.y > topMax) bar.y -= w.y - topMax;
  assert.ok(!inside(bar._m.box(), rect, 8), 'old fix still out of the safe rect');
});

test('safeTop: lowered under the TikTok capsule when CapsuleLayout is loaded; align top sticks to it', function () {
  var cc = cc24(720, 1560), sc = scene24(cc);
  var cap = { safeTopY: function () { return 1400; } };
  var bar = sc.node({ x: 0, y: 760, w: 600, h: 80 });   // top at 1560 - 0 = visible top
  var r = Fit.safeTop(cc, bar, { capsuleLayout: cap });
  assert.ok(Math.abs(bar._m.box().top - (1400 - 8)) < 1e-6, JSON.stringify(r.box));
  var low = sc.node({ x: 0, y: 0, w: 600, h: 80 });
  Fit.safeTop(cc, low, { capsuleLayout: cap, align: 'top' });
  assert.ok(Math.abs(low._m.box().top - 1392) < 1e-6);
  assert.strictEqual(Fit.safeRect(cc, { capsuleLayout: cap, capsule: false }).top, 1560);
});

test('safeBottom: a group of two sibling buttons moves by one dy (spacing kept) above the bottom inset; too wide -> fits false', function () {
  var cc = cc3(720, 1560, { safe: { x: 0, y: 68, width: 720, height: 1492 } }), sc = scene3(cc);
  // the second button is the lower one: the group box, not the first node's box, decides dy
  var a = sc.node({ x: -150, y: -740, w: 200, h: 100 }), b = sc.node({ x: 150, y: -760, w: 200, h: 100 });
  var gap = b._m.box().bottom - a._m.box().bottom;
  var r = Fit.safeBottom(cc, [a, b]);
  assert.ok(r.dy > 0 && r.fits);
  assert.ok(Math.abs(Math.min(a._m.box().bottom, b._m.box().bottom) - (68 + 8)) < 1e-6);
  assert.ok(Math.abs((b._m.box().bottom - a._m.box().bottom) - gap) < 1e-6, 'spacing kept');
  var wide = sc.node({ x: 0, y: 0, w: 900, h: 100 });
  assert.strictEqual(Fit.safeBottom(cc, wide).fits, false);
});

// fake 2.4 view policy: visible area for a screen given the Canvas fit flags (what cc.Canvas.applySettings picks)
function visibleFor(canvas, screenW, screenH) {
  var dw = 720, dh = 1280, sx = screenW / dw, sy = screenH / dh;
  if (canvas.fitWidth && canvas.fitHeight) { var s = Math.min(sx, sy); return { w: dw, h: dh, barX: screenW - dw * s, barY: screenH - dh * s }; } // SHOW_ALL
  if (canvas.fitWidth) return { w: dw, h: screenH / sx, barX: 0, barY: 0 };
  if (canvas.fitHeight) return { w: screenW / sy, h: dh, barX: 0, barY: 0 };
  var s2 = Math.max(sx, sy); return { w: screenW / s2, h: screenH / s2, barX: 0, barY: 0, cropped: true };            // NO_BORDER
}

test('canvasPolicy (2.4): both fits on is reported and fixed to fitWidth only; negative control shows bars with both on', function () {
  var cc = cc24(720, 1280), canvas = { fitWidth: true, fitHeight: true };
  var bad = visibleFor(canvas, 390, 844);
  assert.ok(bad.barY > 1 || bad.barX > 1, 'both on: letterbox bars on a 390x844 phone (positions shift)');
  assert.ok(Fit.checkCanvas(cc, canvas).length === 1 && /both/.test(Fit.checkCanvas(cc, canvas)[0]));
  var r = Fit.canvasPolicy(cc, canvas);
  assert.deepStrictEqual([r.policy, r.changed, canvas.fitWidth, canvas.fitHeight], ['fitWidth', true, true, false]);
  assert.deepStrictEqual(Fit.checkCanvas(cc, canvas), []);
  var good = visibleFor(canvas, 390, 844);
  assert.deepStrictEqual([good.barX, good.barY, good.w], [0, 0, 720]);
  assert.strictEqual(Fit.canvasPolicy(cc, canvas).changed, false, 'second call changes nothing');
  var none = { fitWidth: false, fitHeight: false };
  assert.ok(/neither/.test(Fit.checkCanvas(cc, none)[0]));
  var land = { fitWidth: true, fitHeight: false };
  assert.ok(/needs fitHeight/.test(Fit.checkCanvas(cc, land, { orientation: 'landscape' })[0]));
  Fit.canvasPolicy(cc, land, { orientation: 'landscape' });
  assert.deepStrictEqual([land.fitWidth, land.fitHeight], [false, true]);
});

test('canvasPolicy (3.x): SHOW_ALL is reported and replaced by FIXED_WIDTH through setDesignResolutionSize', function () {
  var cc = cc3(720, 1280), calls = [];
  var FW = { name: 'FIXED_WIDTH' }, FH = { name: 'FIXED_HEIGHT' }, SA = { name: 'SHOW_ALL' }, cur = SA;
  cc.ResolutionPolicy = { FIXED_WIDTH: 4, FIXED_HEIGHT: 3, SHOW_ALL: 2 };
  cc.view._rpFixedWidth = FW; cc.view._rpFixedHeight = FH;
  cc.view.getResolutionPolicy = function () { return cur; };
  cc.view.setDesignResolutionSize = function (w, h, p) { calls.push([w, h, p]); cur = p === 4 ? FW : p === 3 ? FH : SA; };
  assert.strictEqual(Fit.checkCanvas(cc, {}).length, 1);
  var r = Fit.canvasPolicy(cc, {});
  assert.deepStrictEqual(calls, [[720, 1280, 4]]);
  assert.ok(r.changed && r.policy === 'fitWidth');
  assert.deepStrictEqual(Fit.checkCanvas(cc, {}), []);
  assert.strictEqual(Fit.canvasPolicy(cc, {}).changed, false);
});

var failed = results.filter(function (r) { return r[0] !== 'PASS'; });
results.forEach(function (r) { console.log(r[0] + ' ' + r[1]); });
console.log('\n' + (results.length - failed.length) + '/' + results.length + ' passed');
if (failed.length) process.exitCode = 1;
