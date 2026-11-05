// node test_ui_dump_settle.cjs -- ui_dump.js lets labels and cc.Layout finish before it reads positions
// (Saul 2026-11-04, 蛋壳特工队 VIP「Watch 1 times to reach VIP2」: the dump had the row where the prefab put it,
// the screenshot showed it laid out, with Watch on the VIP badge). A tiny fake Cocos 3.x: a horizontal Layout whose
// children only line up when updateLayout() runs, labels whose width only follows their text after updateRenderData().
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

function fakeCc() {
  class Comp { constructor(p) { Object.assign(this, p || {}); this.enabled = true; } }
  class UITransform extends Comp {
    convertToWorldSpaceAR(v) { const w = this.node.world(); return { x: w.x + v.x, y: w.y + v.y, z: 0 }; }
  }
  class Canvas extends Comp {} class Camera extends Comp {
    worldToScreen(p, out) { out = out || {}; out.x = p.x; out.y = p.y; out.z = 0; return out; }
    screenToWorld(p) { return { x: p.x, y: p.y, z: 0 }; }
  }
  class Sprite extends Comp {}
  Sprite.Type = { SIMPLE: 0, SLICED: 1, TILED: 2 };
  class Label extends Comp {
    updateRenderData(force) {            // NONE overflow: the node takes the width of its text (10 units a letter)
      if (this.overflow === 0) this.node.ut.contentSize.width = 10 * String(this.string).length;
    }
  }
  class Layout extends Comp {
    updateLayout() {                     // horizontal, centred on the parent, spacingX between children
      const kids = this.node.children.filter((c) => c.active);
      const total = kids.reduce((s, c) => s + c.ut.contentSize.width, 0) + this.spacingX * (kids.length - 1);
      let x = -total / 2;
      for (const c of kids) { c.x = x + c.ut.contentSize.width / 2; x += c.ut.contentSize.width + this.spacingX; }
    }
  }
  class Node {
    constructor(name, x, y, w, h) {
      this.name = name; this.x = x; this.y = y; this.children = []; this.parent = null; this.active = true;
      this.components = []; this.uuid = name; this.layer = 1;
      this.ut = this.add(new UITransform({ contentSize: { width: w, height: h }, anchorPoint: { x: 0.5, y: 0.5 } }));
    }
    add(c) { c.node = this; this.components.push(c); return c; }
    child(n) { n.parent = this; this.children.push(n); return n; }
    getComponent(ctor) { return this.components.find((c) => c instanceof ctor) || null; }
    world() { let x = this.x, y = this.y, p = this.parent; while (p) { x += p.x; y += p.y; p = p.parent; } return { x, y }; }
    get eulerAngles() { return { z: 0 }; }
  }
  const scene = new Node('scene', 0, 0, 0, 0);
  const canvas = scene.child(new Node('Canvas', 200, 400, 400, 800));
  canvas.add(new Canvas());
  canvas.add(new Camera({ visibility: 0xffffffff, priority: 0 }));
  const row = canvas.child(new Node('info', 0, 0, 10, 40));
  row.add(new Layout({ spacingX: 5 }));
  const words = ['Watch', '1', 'times to reach', 'VIP2'];
  for (const w of words) {                // all four still sit at x = 0, 20 units wide, as in the prefab
    const n = row.child(new Node('text', 0, 0, 20, 30));
    n.add(new Label({ string: w, fontSize: 20, overflow: 0, horizontalAlign: 1, verticalAlign: 1, enableWrapText: false,
                      lineHeight: 24, font: null, useSystemFont: true, color: { r: 255, g: 255, b: 255 } }));
  }
  return {
    UITransform, Canvas, Camera, Sprite, Label, Layout, Vec3: function (x, y, z) { return { x, y, z }; },
    director: { getScene: () => scene }, ENGINE_VERSION: '3.8.8', game: { canvas: fakeCanvas() },
  };
}

function fakeCanvas() {
  return { width: 400, height: 800, getBoundingClientRect: () => ({ x: 0, y: 0, width: 400, height: 800 }) };
}

global.window = { innerWidth: 400, innerHeight: 800, devicePixelRatio: 1 };
global.document = {
  querySelector: () => null, querySelectorAll: () => [],
  createElement: () => ({ getContext: () => ({ font: '', measureText: (s) => ({ width: 10 * String(s).length }) }) }),
};
global.HTMLCanvasElement = function () {};

const src = fs.readFileSync(path.join(__dirname, 'ui_dump.js'), 'utf8');
const dump = (opts) => { window.cc = fakeCc(); return (new Function('return ' + src))()(opts); };

const labels = (d) => d.nodes.filter((n) => n.comps && n.comps.label).map((n) => ({ s: n.comps.label.string, r: n.rect, l: n.comps.label }));
const overlaps = (ls) => ls.some((a, i) => ls.slice(i + 1).some((b) => a.r[0] < b.r[0] + b.r[2] - 1e-6 && b.r[0] < a.r[0] + a.r[2] - 1e-6));

const before = dump({ settle: false });
assert.ok(!before.error, before.error);
assert.ok(overlaps(labels(before)), 'without the settle step the row is piled up (the old stale dump)');

const after = dump({});
assert.ok(!after.error, after.error);
const ls = labels(after);
assert.strictEqual(after.settle.layouts, 1, 'the Layout ran');
assert.strictEqual(after.settle.labels, 4, 'every label was brought up to date');
assert.ok(after.settle.moved >= 3, 'the dump says the labels moved: ' + JSON.stringify(after.settle));
assert.ok(!overlaps(ls), 'after settling the row is side by side: ' + JSON.stringify(ls.map((x) => [x.s, x.r])));
for (const x of ls) {
  assert.strictEqual(x.l.h_align, 1);
  assert.strictEqual(x.l.wrap, false);
  assert.strictEqual(x.l.text_w, 10 * x.s.length, 'measured text width for ' + x.s);
  assert.strictEqual(x.l.text_metric, 'measureText');
}
console.log('ui_dump settle: 2 dumps, row laid out, text widths measured -- OK');
