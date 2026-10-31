'use strict';
// node tests/capsule-layout.test.js  -- parts/CapsuleLayout.js (v7.8, 总表 U1 / B30): points vs pixels, design coords.
// Fake engines: Cocos 2.4 (view.getFrameSize in points, viewport + scale in device pixels) and 3.x (screen.windowSize
// in physical pixels, cc.UITransform). Numbers: Saul's iPhone 14 TikTok (capsule 293/51/380/83 pt, pixelRatio 3, the
// px build returned every value x3), SE 375x667 @2, and a letterboxed SHOW_ALL game (MergeShot2048: bars 75 pt).
var assert = require('assert');
var path = require('path');
var Capsule = require(path.join(__dirname, '..', 'parts', 'CapsuleLayout.js'));

function tt(unitK, cap, sys) {
  return {
    getSystemInfoSync: function () { return sys; },
    getMenuButtonBoundingClientRect: function () {
      return { left: cap.left * unitK, top: cap.top * unitK, right: cap.right * unitK, bottom: cap.bottom * unitK,
        width: (cap.right - cap.left) * unitK, height: (cap.bottom - cap.top) * unitK };
    }
  };
}
// design 750 x H fit-width: scale = frameW * dpr / 750; letterbox: viewport y offset
function cc24(frameW, frameH, dpr, designW, designH, showAll) {
  var s = showAll ? Math.min(frameW / designW, frameH / designH) : frameW / designW;
  var vpW = designW * s * dpr, vpH = (showAll ? designH : frameH / s) * s * dpr;
  var vpX = (frameW * dpr - vpW) / 2, vpY = (frameH * dpr - vpH) / 2;
  return { v2: function (x, y) { return { x: x, y: y }; },
    view: { getDevicePixelRatio: function () { return dpr; }, getFrameSize: function () { return { width: frameW, height: frameH }; },
      getViewportRect: function () { return { x: vpX, y: vpY, width: vpW, height: vpH }; },
      getScaleX: function () { return s * dpr; }, getScaleY: function () { return s * dpr; },
      getVisibleSize: function () { return { width: frameW / s, height: frameH / s }; }, getVisibleOrigin: function () { return { x: 0, y: 0 }; } },
    _s: s, _vpY: vpY / dpr };
}
function cc3(frameW, frameH, dpr, designW) {
  var s = frameW / designW;
  return { UITransform: function () {}, screen: { devicePixelRatio: dpr, windowSize: { width: frameW * dpr, height: frameH * dpr } },
    view: { getViewportRect: function () { return { x: 0, y: 0, width: frameW * dpr, height: frameH * dpr }; },
      getScaleX: function () { return s * dpr; }, getScaleY: function () { return s * dpr; },
      getVisibleSize: function () { return { width: designW, height: frameH / s }; } }, _s: s };
}
var I14 = { windowWidth: 390, windowHeight: 844, screenWidth: 390, pixelRatio: 3, statusBarHeight: 47 };
var CAP14 = { left: 293, top: 51, right: 380, bottom: 83 };
var SE = { windowWidth: 375, windowHeight: 667, pixelRatio: 2, statusBarHeight: 20 };
var CAPSE = { left: 278, top: 24, right: 365, bottom: 56 };
var n = 0;
function ok(name, fn) { fn(); n++; console.log('ok ' + name); }
function near(a, b, msg) { assert.ok(Math.abs(a - b) < 1e-6, msg + ': ' + a + ' vs ' + b); }

ok('screenRect: points stay points, pixels are recognised and converted (iPhone 14 and SE)', function () {
  var pt = Capsule.screenRect(tt(1, CAP14, I14)), px = Capsule.screenRect(tt(3, CAP14, I14));
  assert.strictEqual(pt.unit, 'pt'); assert.strictEqual(px.unit, 'px');
  ['left', 'top', 'right', 'bottom', 'width', 'height'].forEach(function (k) { near(px[k], pt[k], 'iphone14 ' + k); });
  near(pt.bottom, 83, 'bottom');
  var se = Capsule.screenRect(tt(2, CAPSE, SE));
  assert.strictEqual(se.unit, 'px'); near(se.bottom, 56, 'se bottom'); near(se.left, 278, 'se left');
});
ok('designRect: the same UI world rect for pt and px (2.4 fit-width, 2.4 letterboxed SHOW_ALL, 3.x)', function () {
  [cc24(390, 844, 3, 750, 1334, false), cc24(390, 844, 3, 720, 1280, true), cc3(390, 844, 3, 750)].forEach(function (cc, i) {
    var a = Capsule.designRect(cc, tt(1, CAP14, I14)), b = Capsule.designRect(cc, tt(3, CAP14, I14));
    ['left', 'right', 'top', 'bottom'].forEach(function (k) { near(b[k], a[k], 'engine ' + i + ' ' + k); });
    // points -> design: 2.4 fit-width / 3.x: bottom 83 pt = (844 - 83) / s design units above the screen bottom
    var vpY = cc._vpY || 0;
    near(a.bottom, (844 - 83 - vpY) / cc._s, 'engine ' + i + ' bottom in design units');
    assert.ok(a.top > a.bottom, 'y up');
  });
});
ok('the raw pixel value used as points (the DriftRacer v2 bug) lands far below: the part is needed', function () {
  var cc = cc24(390, 844, 3, 750, 1334, false), raw = tt(3, CAP14, I14).getMenuButtonBoundingClientRect();
  var naiveBottom = (844 - raw.bottom) / cc._s, good = Capsule.designRect(cc, tt(3, CAP14, I14)).bottom;
  assert.ok(good - naiveBottom > 300, 'raw px would move the bar ' + (good - naiveBottom) + ' design units');
});
ok('no SDK / a rect without size: the default capsule below the status bar', function () {
  var d = Capsule.screenRect({ getSystemInfoSync: function () { return I14; }, getMenuButtonBoundingClientRect: function () { return { left: 0, top: 0, right: 0, bottom: 0 }; } });
  assert.strictEqual(d.source, 'default'); near(d.top, 51, 'top'); near(d.bottom, 83, 'bottom'); near(d.right, 380, 'right');
  assert.strictEqual(Capsule.screenRect({}).source, 'default');
  var thrown = Capsule.screenRect({ getSystemInfoSync: function () { throw new Error('x'); }, getMenuButtonBoundingClientRect: function () { throw new Error('y'); } });
  assert.strictEqual(thrown.source, 'default');
});
ok('placeBelow moves a top bar under the capsule only when it is above it, the same for pt and px (2.4 and 3.x)', function () {
  // 2.4 node: world box from position + size, parent at the origin
  function node24(y, h) {
    var nd = { y: y, x: 0, h: h, parent: { convertToNodeSpaceAR: function (p) { return p; } },
      getBoundingBoxToWorld: function () { return { x: 0, y: nd.y - nd.h / 2, width: 100, height: nd.h }; },
      convertToWorldSpaceAR: function () { return { x: nd.x, y: nd.y }; }, setPosition: function (p) { nd.x = p.x; nd.y = p.y; } };
    return nd;
  }
  function node3(y, h) {
    var nd = { worldPosition: { x: 0, y: y, z: 0 }, h: h,
      getComponent: function () { return { getBoundingBoxToWorld: function () { return { x: 0, y: nd.worldPosition.y - nd.h / 2, width: 100, height: nd.h }; } }; },
      setWorldPosition: function (x, yy, z) { nd.worldPosition = { x: x, y: yy, z: z }; } };
    return nd;
  }
  var c2 = cc24(390, 844, 3, 750, 1334, false), c3 = cc3(390, 844, 3, 750);
  [[c2, node24, function (nd) { return nd.y; }], [c3, node3, function (nd) { return nd.worldPosition.y; }]].forEach(function (row, i) {
    var cc = row[0], make = row[1], y = row[2];
    var a = make(1600, 60), b = make(1600, 60);
    var da = Capsule.placeBelow(cc, a, 8, tt(1, CAP14, I14)), db = Capsule.placeBelow(cc, b, 8, tt(3, CAP14, I14));
    assert.ok(da > 0, 'engine ' + i + ' moved'); near(y(a), y(b), 'engine ' + i + ' same place for pt and px');
    var limit = Capsule.safeTopY(cc, 8, tt(1, CAP14, I14));
    near(y(a) + 30, limit, 'engine ' + i + ' top edge on the limit');
    var low = make(limit - 200, 60);
    assert.strictEqual(Capsule.placeBelow(cc, low, 8, tt(3, CAP14, I14)), 0, 'engine ' + i + ': a node already below is not moved');
  });
});
ok('alignBelow puts the top edge exactly under the capsule from above and from below, same for pt and px', function () {
  var cc = cc24(390, 844, 3, 750, 1334, false);
  function node24(y) {
    var nd = { y: y, x: 0, parent: null,
      getBoundingBoxToWorld: function () { return { x: 0, y: nd.y - 30, width: 100, height: 60 }; },
      convertToWorldSpaceAR: function () { return { x: nd.x, y: nd.y }; }, setPosition: function (p) { nd.x = p.x; nd.y = p.y; } };
    return nd;
  }
  var limit = Capsule.safeTopY(cc, 8, tt(1, CAP14, I14));
  [node24(1600), node24(900)].forEach(function (nd, i) {
    var other = node24(nd.y);
    Capsule.alignBelow(cc, nd, 8, tt(1, CAP14, I14)); Capsule.alignBelow(cc, other, 8, tt(3, CAP14, I14));
    near(nd.y + 30, limit, 'case ' + i + ' top on the limit'); near(nd.y, other.y, 'case ' + i + ' pt == px');
  });
});
ok('one file for both engines: CommonJS export and the global TikTokCapsuleLayout', function () {
  assert.strictEqual(typeof Capsule.designRect, 'function');
  assert.strictEqual(global.TikTokCapsuleLayout, Capsule);
  assert.strictEqual(Capsule.VERSION, '1.0');
});
console.log('capsule-layout: ' + n + ' passed');
