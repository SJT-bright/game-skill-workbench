// Generic input-point regression: node decorations change visual bounds, not hit ownership.
// Run: node package-check/scripts/test_hit_center.mjs
// No browser, installed-path dependency, filesystem writes, or baseline copy is needed.
import assert from 'node:assert/strict';
globalThis.CFG = {lib: new URL('./runtime_regression/lib.mjs', import.meta.url).href};
const {HELPERS} = await import('./runtime_regression/gates.mjs');

function fake(c = {}) {
  const view = {
    getFrameSize: () => ({width: 375, height: 812}),
    getVisibleSize: () => ({width: 750, height: 1624}),
    getVisibleOrigin: () => ({x: 0, y: 0}),
    getViewportRect: () => ({x: 0, y: c.bars ? 150 : 0, width: 750, height: 1624}),
    getScaleX: () => c.bars ? 750 / 720 : 1,
    getScaleY: () => c.bars ? 750 / 720 : 1,
    getDevicePixelRatio: () => 2,
  };
  const camera = {
    getWorldToScreenPoint: p => ({x: p.x - (c.moved ? 50 : 0), y: p.y + (c.moved ? 100 : 0)}),
    worldToScreen: (p, out) => Object.assign(out, {x: p.x * 2, y: p.y * 2}),
  };
  const Canvas = class {}, UITransform = class {};
  const cc = {
    ENGINE_VERSION: c.v3 ? '3.8.1' : '2.4.5', view,
    Camera: c.noCamera ? {} : {findCamera: () => camera}, Canvas,
    v2: (x, y) => ({x, y}),
    Vec3: class { constructor(x = 0, y = 0, z = 0) { Object.assign(this, {x, y, z}); } },
    director: {getScene: () => ({getComponentsInChildren: () => [camera]})},
    game: {canvas: {width: 750, height: 1624}},
  };
  if (c.v3) cc.UITransform = UITransform;
  const parent = {
    name: 'Canvas', parent: {name: 'Scene'}, activeInHierarchy: true,
    opacity: 255, scaleX: 1, scaleY: 1,
    getComponent: K => K === Canvas ? {cameraComponent: camera} : null,
  };
  const offAnchor = c.anchor || c.rotate;
  const ax = offAnchor ? 0 : .5, ay = offAnchor ? 0 : .5;
  const width = c.zero ? 0 : 40, height = c.zero ? 0 : 20;
  const origin = c.anchor ? [180, 90] : [200, 100];
  // Rotation deliberately uses a noncentral anchor: the actual centre moves to (190,120).
  const world = p => c.rotate ? {x: 200 - p.y, y: 100 + p.x}
    : {x: origin[0] + p.x, y: origin[1] + p.y};
  const box = c.decorated ? {x: 180, y: 90, width: 220, height: 220}
    : {x: 180, y: 90, width: 40, height: 20};
  const ut = {
    contentSize: {width, height}, anchorPoint: {x: ax, y: ay},
    convertToWorldSpaceAR: world, getBoundingBoxToWorld: () => box,
  };
  const n = {
    name: 'Button', parent, activeInHierarchy: true, opacity: 255, scaleX: 1, scaleY: 1,
    width, height, anchorX: ax, anchorY: ay, worldPosition: {x: 200, y: 100, z: 0},
    getComponent: K => K === UITransform && c.v3 ? ut : null,
    convertToWorldSpaceAR: world, getBoundingBoxToWorld: () => box,
  };
  class Element {}
  Element.prototype.getBoundingClientRect = () => ({left: 0, top: 0, width: 375, height: 812});
  return {window: {cc}, Element, n};
}

function result(c) {
  const f = fake(c);
  // The legacy point is independently derived from the unchanged visual rectangle.
  return new Function('window', 'Element', 'n', HELPERS + `
    var box = cssBox(n);
    return {point: screenOf(n), box: box,
      legacy: {x: (box.x0 + box.x1) / 2, y: (box.y0 + box.y1) / 2}};
  `)(f.window, f.Element, f.n);
}

// These expected coordinates are fixed external values, not cssHitPoint's formula.
const cases = [
  ['plain', {}, [100, 762]],
  ['decorative_caption', {decorated: true}, [100, 762]],
  ['noncentral_anchor', {anchor: true, decorated: true}, [100, 762]],
  ['rotated_noncentral_anchor', {rotate: true, decorated: true}, [95, 752]],
  ['moved_camera', {moved: true, decorated: true}, [75, 712]],
  ['letterboxed', {bars: true, decorated: true}, [104.16666666666667, 684.9166666666666]],
  ['camera_absent', {noCamera: true, decorated: true}, [100, 762]],
  ['zero_own_size_fallback', {zero: true, decorated: true}, [145, 712]],
  ['cocos3_ui_camera', {v3: true, decorated: true}, [200, 712]],
];

const rows = [];
for (const [name, c, want] of cases) {
  const got = result(c);
  assert(Math.abs(got.point.x - want[0]) < 1e-7, name + ' wrong hit x');
  assert(Math.abs(got.point.y - want[1]) < 1e-7, name + ' wrong hit y');
  if (c.zero) {
    assert.deepEqual({x: got.point.x, y: got.point.y}, got.legacy,
      name + ' must preserve structural-parent fallback');
  } else if (c.decorated) {
    assert.notDeepEqual({x: got.point.x, y: got.point.y}, got.legacy,
      name + ' negative control did not expose the recursive-centre shift');
  } else {
    assert.deepEqual({x: got.point.x, y: got.point.y}, got.legacy,
      name + ' ordinary hit point must remain unchanged');
  }
  // The visible width/height still cover the complete visual rectangle.
  assert.equal(got.point.w, got.box.x1 - got.box.x0, name + ' changed visible width');
  assert.equal(got.point.h, got.box.y1 - got.box.y0, name + ' changed visible height');
  rows.push({name, passed: true});
}
console.log(JSON.stringify({passed: true, count: rows.length, cases: rows}));
