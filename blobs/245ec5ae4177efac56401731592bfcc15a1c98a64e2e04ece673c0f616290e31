'use strict';
// node tests/course-lane.test.js  -- parts/CourseLane.js (v7.8, 总表 P2 补): spawn / recycle / lanes / revive from the
// engine's REAL visible rect. Fake engines: Cocos 2.4 (cc.view visible size + origin, node.convertToWorldSpaceAR) and
// 3.x (cc.UITransform, worldPosition, UIOpacity). Numbers: BreezyBalloon (design 750 x 1334) on 390x844 (fit width:
// 750 x 1623), 768x1024 (1000.5 x 1334) and 1115x791 (1880.4 x 1334); v2.1 recycled pillars to world x 816.
var assert = require('assert');
var path = require('path');
var Lane = require(path.join(__dirname, '..', 'parts', 'CourseLane.js'));

function cc24(vw, vh, vo) {
  var tweens = [];
  var cc = {
    v2: function (x, y) { return { x: x, y: y }; },
    view: { getVisibleSize: function () { return { width: vw, height: vh }; }, getVisibleOrigin: function () { return vo || { x: 0, y: 0 }; } },
    tween: function (t) {
      var rec = { target: t, steps: [] };
      var api = { to: function (s, props) { rec.steps.push(['to', s, props]); return api; },
        call: function (fn) { rec.steps.push(['call', fn]); return api; },
        start: function () { tweens.push(rec); return api; } };
      return api;
    },
    _tweens: tweens,
    // run every recorded tween to its end (opacity set, callbacks called)
    _finish: function () { tweens.splice(0).forEach(function (r) { r.steps.forEach(function (s) { if (s[0] === 'to') Object.assign(r.target, s[2]); else s[1](); }); }); }
  };
  return cc;
}
function node24(x, w, parentX) {
  var px = parentX || 0;
  return { x: x, width: w, scaleX: 1, opacity: 255, activeInHierarchy: true,
    convertToWorldSpaceAR: function (p) { return { x: px + this.x + p.x, y: p.y }; },
    convertToNodeSpaceAR: function (p) { return { x: p.x - px - this.x, y: p.y }; },
    getBoundingBoxToWorld: function () { return { x: px + this.x - this.width / 2, y: 0, width: this.width, height: 100 }; } };
}
function cc3(vw, vh) {
  var cc = cc24(vw, vh);
  cc.UITransform = function () {};
  cc.UIOpacity = function () { this.opacity = 255; };
  cc.Vec3 = function (x, y, z) { this.x = x; this.y = y; this.z = z; };
  return cc;
}
function node3(cc, x, w) {
  var comps = [];
  var n = { worldPosition: { x: x, y: 0, z: 0 }, activeInHierarchy: true,
    getComponent: function (K) {
      if (K === cc.UITransform) return { getBoundingBoxToWorld: function () { return { x: x - w / 2, y: 0, width: w, height: 100 }; },
        convertToNodeSpaceAR: function (p) { return { x: p.x - x, y: p.y }; } };
      return comps.filter(function (c) { return c instanceof K; })[0] || null;
    },
    addComponent: function (K) { var c = new K(); comps.push(c); return c; } };
  return n;
}

var results = [];
function test(name, fn) {
  try { fn(); results.push(['PASS', name]); } catch (e) { results.push(['FAIL', name + ': ' + (e && e.stack || e)]); }
}

var NARROW = cc24(750, 1623.08), WIDE = cc24(1880.42, 1334), TABLET = cc24(1000.5, 1334);

test('visibleRect is the engine visible rect, not the 750 design width', function () {
  assert.deepStrictEqual([NARROW.view.getVisibleSize().width, Lane.visibleRect(NARROW).right], [750, 750]);
  var r = Lane.visibleRect(WIDE);
  assert.strictEqual(r.left, 0); assert.strictEqual(r.right, 1880.42); assert.strictEqual(r.width, 1880.42);
  var off = Lane.visibleRect(cc24(900, 1334, { x: -75, y: 0 }));      // fit height with a visible origin left of 0
  assert.deepStrictEqual([off.left, off.right], [-75, 825]);
});

test('spawnX: beyond the real right edge by half width + at least 100; the gap after the last obstacle wins when larger', function () {
  assert.strictEqual(Lane.spawnX(WIDE, { halfWidth: 90 }), 1880.42 + 90 + 100);
  assert.strictEqual(Lane.spawnX(WIDE, { halfWidth: 90, margin: 20 }), 1880.42 + 90 + 100);   // margin never below 100
  assert.strictEqual(Lane.spawnX(WIDE, { halfWidth: 90, margin: 160 }), 1880.42 + 90 + 160);
  assert.strictEqual(Lane.spawnX(NARROW, { halfWidth: 90, lastX: 1500, gap: 500 }), 2000);
  // negative control: v2.1 put recycled pillars at world x 816; on the wide screen that is inside the visible area
  var v21 = 816, r = Lane.visibleRect(WIDE);
  assert.ok(v21 - 90 < r.right, 'the old design-width spawn is on screen on 1115x791');
  assert.ok(Lane.spawnX(WIDE, { halfWidth: 90 }) - 90 > r.right, 'CourseLane spawns off screen');
});

test('recycleX / isGone: only after the obstacle fully left the left edge', function () {
  assert.strictEqual(Lane.recycleX(NARROW, { halfWidth: 90 }), -90);
  assert.strictEqual(Lane.isGone(NARROW, -60, { halfWidth: 90 }), false);   // 30 still visible
  assert.strictEqual(Lane.isGone(NARROW, -91, { halfWidth: 90 }), true);
  assert.strictEqual(Lane.isGone(cc24(900, 1334, { x: -75, y: 0 }), -120, { halfWidth: 90 }), false);  // origin -75: still visible
});

test('lanesNeeded: wider screen = more groups; screens: 3 fills three screen widths', function () {
  var o = { gap: 500, halfWidth: 90 };
  var n1 = Lane.lanesNeeded(NARROW, o), n2 = Lane.lanesNeeded(TABLET, o), n3 = Lane.lanesNeeded(WIDE, o);
  assert.ok(n1 <= n2 && n2 < n3, [n1, n2, n3].join(','));
  assert.strictEqual(n3, Math.ceil((1880.42 + 180 + 100) / 500) + 1);
  assert.ok(Lane.lanesNeeded(WIDE, { gap: 500, halfWidth: 90, screens: 3 }) >= Math.ceil(3 * 1880.42 / 500));
  assert.throws(function () { Lane.lanesNeeded(WIDE, {}); }, /gap/);
});

test('clearForRevive: off screen free, visible in front of the player fades >= 0.3 s, visible farther ahead kept', function () {
  var cc = cc24(750, 1623.08);
  var items = [{ id: 'left', node: node24(-200, 160) }, { id: 'near', node: node24(300, 160) },
    { id: 'far', node: node24(700, 160) }, { id: 'right', node: node24(1100, 160) }];
  var faded = [];
  var plan = Lane.clearForRevive(cc, items, { playerX: 150, apply: true, fadeSeconds: 0.1, onFaded: function (it) { faded.push(it.id); } });
  assert.deepStrictEqual([plan.offscreen.map(function (i) { return i.id; }), plan.fade.map(function (i) { return i.id; }), plan.keep.map(function (i) { return i.id; })],
    [['left', 'right'], ['near'], ['far']]);
  assert.strictEqual(cc._tweens.length, 1);
  assert.strictEqual(cc._tweens[0].steps[0][1], 0.3, 'a fade is never shorter than 0.3 s');
  assert.deepStrictEqual(faded, []);
  cc._finish();
  assert.deepStrictEqual([faded, items[1].node.opacity], [['near'], 0]);
  // nodes of one obstacle fade together, onFaded once
  var cc2 = cc24(750, 1623.08), top = node24(300, 160), bottom = node24(300, 160), n = 0;
  Lane.clearForRevive(cc2, [{ nodes: [top, bottom] }], { playerX: 150, apply: true, onFaded: function () { n++; } });
  assert.strictEqual(cc2._tweens.length, 2); cc2._finish(); assert.deepStrictEqual([n, top.opacity, bottom.opacity], [1, 0, 0]);
  // without apply nothing moves or fades
  var cc3x = cc24(750, 1623.08); Lane.clearForRevive(cc3x, [{ node: node24(300, 160) }], { playerX: 150 }); assert.strictEqual(cc3x._tweens.length, 0);
});

test('camera: a camera that follows the course shifts the visible rect; zoom shrinks it', function () {
  var cc = cc24(750, 1334), cam = { node: node24(1375, 0), zoomRatio: 1 };
  var r = Lane.visibleRect(cc, { camera: cam });
  assert.deepStrictEqual([r.left, r.right], [1000, 1750]);
  assert.strictEqual(Lane.spawnX(cc, { camera: cam, halfWidth: 50 }), 1750 + 50 + 100);
  cam.zoomRatio = 2;
  r = Lane.visibleRect(cc, { camera: cam });
  assert.deepStrictEqual([r.left, r.right], [1375 - 187.5, 1375 + 187.5]);
});

test('space: the rect in the coordinates of the node the obstacles sit in', function () {
  var cc = cc24(750, 1334), level = node24(375, 0);     // level node centred on the screen
  var r = Lane.visibleRect(cc, { space: level });
  assert.deepStrictEqual([r.left, r.right], [-375, 375]);
  assert.strictEqual(Lane.spawnX(cc, { space: level, halfWidth: 90 }), 375 + 90 + 100);
});

test('Cocos 3.x: UITransform space, worldPosition, UIOpacity fade, orthoHeight camera', function () {
  var cc = cc3(1880.42, 1334);
  var level = node3(cc, 940.21, 0);
  var r = Lane.visibleRect(cc, { space: level });
  assert.ok(Math.abs(r.left + 940.21) < 1e-6 && Math.abs(r.right - 940.21) < 1e-6);
  var near = node3(cc, 400, 160);
  var plan = Lane.clearForRevive(cc, [{ node: near }], { playerX: 200, apply: true });
  assert.strictEqual(plan.fade.length, 1);
  assert.ok(near.getComponent(cc.UIOpacity), 'UIOpacity added for the fade');
  cc._finish();
  assert.strictEqual(near.getComponent(cc.UIOpacity).opacity, 0);
  var cam = { node: node3(cc, 1000, 0), orthoHeight: 667 };
  var c = Lane.visibleRect(cc, { camera: cam });
  assert.ok(Math.abs(c.width - 1880.42) < 1e-6 && Math.abs(c.left - (1000 - 940.21)) < 1e-6);
});

var failed = results.filter(function (r) { return r[0] !== 'PASS'; });
results.forEach(function (r) { console.log(r[0] + ' ' + r[1]); });
console.log(failed.length ? '\n' + failed.length + ' failed' : '\nCourseLane: ' + results.length + ' passed');
if (failed.length) process.exitCode = 1;
