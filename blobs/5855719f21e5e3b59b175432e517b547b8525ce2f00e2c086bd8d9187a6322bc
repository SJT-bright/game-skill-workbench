'use strict';
// node tests/fx-pool.test.js  -- parts/FxPool.js (生成时预防 P18): 120 effects do not grow the scene, the cap holds when all
// are busy, life counts game time (paused = frozen), early release / releaseAll / destroyed nodes, 2.4 and 3.x node
// shapes, devWatch warns on nodes made inside update() and on a scene that keeps growing.
// Negative control: the 方块迷阵 shape (a new node per merge effect, never removed) grows to 120 nodes and devWatch
// reports it.
var assert = require('assert');
var path = require('path');
// FX_POOL_FILE: run the same checks on a broken copy (mutation check in the patch's test record)
var FILE = process.env.FX_POOL_FILE || path.join(__dirname, '..', 'parts', 'FxPool.js');
delete require.cache[require.resolve(FILE)];
var FxPool = require(FILE);

// a tiny node tree: enough of cc.Node for the pool (2.4 shape; three = true gives the 3.x setPosition(x, y, z) shape)
function FakeNode(name, three) {
  this.name = name || 'n'; this.children = []; this.parent = null; this.active = true; this.isValid = true;
  if (three) { this.position = { x: 0, y: 0, z: 3 }; } else { this.x = 0; this.y = 0; }
  this.three = !!three;
}
FakeNode.prototype.addChild = function (c) { if (c.parent) c.parent.removeChild(c); this.children.push(c); c.parent = this; };
FakeNode.prototype.removeChild = function (c) { var i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; };
FakeNode.prototype.destroy = function () { this.isValid = false; if (this.parent) this.parent.removeChild(this); };
FakeNode.prototype.setPosition = function (x, y, z) {
  if (this.three) { this.position = { x: x, y: y, z: z === undefined ? this.position.z : z }; } else { this.x = x; this.y = y; }
};
function count(node) { var n = 1; node.children.forEach(function (c) { n += count(c); }); return n; }
function emitter() {
  var h = {};
  return { on: function (e, f) { (h[e] = h[e] || []).push(f); }, off: function (e, f) { h[e] = (h[e] || []).filter(function (g) { return g !== f; }); },
    emit: function (e) { (h[e] || []).slice().forEach(function (f) { f(); }); } };
}
function fakeCc(three) {
  var director = emitter(), scene = new FakeNode('scene', three), stopped = [];
  var cc = { director: director, Director: { EVENT_BEFORE_UPDATE: 'director_before_update', EVENT_AFTER_UPDATE: 'director_after_update' },
    Node: FakeNode, isValid: function (n) { return !!n && n.isValid !== false; },
    instantiate: function (p) { return new FakeNode(p && p.name, three); },
    Tween: { stopAllByTarget: function (n) { stopped.push(n); } }, scene: scene, stopped: stopped };
  director.getScene = function () { return scene; };
  if (three) cc.UITransform = function () {};
  return cc;
}
var quiet = function () {};
var results = [];
function check(name, fn) { fn(); results.push(name); }

// the game loop used by 1 and its negative control: a merge effect every 3 frames, 120 merges, 0.5 s effects, 60 fps
function playMerges(cc, layer, fire, tick) {
  var peak = 0;
  for (var f = 0; f < 120 * 3 + 120; f++) {
    if (f % 3 === 0 && f < 360) fire(f);
    if (tick) tick(1 / 60);
    peak = Math.max(peak, count(cc.scene));
  }
  return { after: count(cc.scene), peak: peak };
}

// 1. 120 spawns: node count does not grow; negative control grows
check('120 spawns, no growth', function () {
  var cc = fakeCc(), layer = new FakeNode('fx'); cc.scene.addChild(layer);
  var pool = FxPool.create(cc, { parent: layer, make: function () { return cc.instantiate({ name: 'spark' }); }, life: 0.5, max: 32, warn: quiet });
  var before = count(cc.scene);
  var r = playMerges(cc, layer, function (f) { pool.spawn(f, 10); }, pool.tick);
  var st = pool.stats();
  assert.ok(st.made <= 11, 'about 10 effects live at once, made ' + st.made);
  assert.strictEqual(r.after, before + st.made, 'scene holds only the pooled nodes');
  assert.ok(r.after - before < 120 / 4, 'no growth with spawn count (' + (r.after - before) + ')');
  assert.strictEqual(st.busy, 0, 'all returned after their life');
  assert.ok(layer.children.every(function (n) { return n.active === false; }), 'returned nodes are inactive');
  assert.ok(cc.stopped.length >= 120, 'tweens stopped on every return');
  // negative control: 方块迷阵 shape: new node per merge, never removed
  var cc2 = fakeCc(), layer2 = new FakeNode('fx'); cc2.scene.addChild(layer2);
  var before2 = count(cc2.scene);
  var r2 = playMerges(cc2, layer2, function () { var n = cc2.instantiate({ name: 'spark' }); layer2.addChild(n); });
  assert.ok(r2.after - before2 >= 120, 'negative control: 120 merges leave 120 nodes (' + (r2.after - before2) + ')');
});

// 2. the cap holds when every node is busy: oldest is taken back (onDone runs for it)
check('cap', function () {
  var cc = fakeCc(), layer = new FakeNode('fx'), done = [];
  var pool = FxPool.create(cc, { parent: layer, make: function () { return new FakeNode('b'); }, max: 8, life: 0, warn: quiet });
  var first = pool.spawn(0, 0, { onDone: function (n) { done.push(n); } });
  for (var i = 1; i < 50; i++) pool.spawn(i, 0);
  assert.strictEqual(layer.children.length, 8, '50 bullets in one frame, 8 nodes');
  assert.deepStrictEqual(done, [first], 'oldest recycled, onDone called');
  assert.strictEqual(pool.stats().busy, 8);
  pool.tick(100);
  assert.strictEqual(pool.stats().busy, 8, 'life 0: no auto return');
});

// 3. life counts game time: tick(0) (paused) does not age; release / releaseAll / destroyed nodes
check('life, release, destroyed', function () {
  var cc = fakeCc(), layer = new FakeNode('fx'), resets = 0;
  var pool = FxPool.create(cc, { parent: layer, make: function () { return new FakeNode('t'); }, reset: function () { resets += 1; }, life: 0.5, warn: quiet });
  var a = pool.spawn(5, 6);
  assert.strictEqual(a.x, 5); assert.strictEqual(a.y, 6); assert.strictEqual(a.active, true); assert.strictEqual(a.parent, layer);
  for (var i = 0; i < 200; i++) pool.tick(0);
  assert.strictEqual(pool.stats().busy, 1, 'paused: still playing');
  assert.strictEqual(pool.release(a), true);
  assert.strictEqual(pool.release(a), false, 'second release is a no-op');
  var b = pool.spawn(1, 1);
  assert.strictEqual(b, a, 'reused');
  assert.strictEqual(resets, 2, 'reset before every use');
  b.destroy();                                              // someone destroyed it
  var c = pool.spawn(2, 2);
  assert.notStrictEqual(c, b, 'destroyed node is not handed out');
  pool.spawn(3, 3, { life: 2 });
  pool.releaseAll();
  assert.strictEqual(pool.stats().busy, 0, 'releaseAll');
  pool.destroy();
  assert.ok(layer.children.length === 0, 'destroy removes pooled nodes');
  assert.strictEqual(pool.spawn(0, 0), null, 'no spawn after destroy');
  assert.throws(function () { FxPool.create(cc, { parent: layer }); }, /make/);
  assert.throws(function () { FxPool.create(cc, { make: function () {} }); }, /parent/);
});

// 4. 3.x node shape: setPosition(x, y) keeps z
check('3.x', function () {
  var cc = fakeCc(true), layer = new FakeNode('fx', true);
  var pool = FxPool.create(cc, { parent: layer, make: function () { return new FakeNode('t', true); }, life: 0.2, warn: quiet });
  var n = pool.spawn(40, 50);
  assert.deepStrictEqual(n.position, { x: 40, y: 50, z: 3 });
  for (var i = 0; i < 20; i++) pool.tick(1 / 60);
  assert.strictEqual(n.active, false, 'returned after 0.2 s');
});

// 5. devWatch: nodes made inside update are reported, a growing scene is reported, a pooled game is not
check('devWatch', function () {
  function frames(cc, k, inside) { for (var i = 0; i < k; i++) { cc.director.emit('director_before_update'); if (inside) inside(i); cc.director.emit('director_after_update'); } }
  // release build: nothing
  var rel = fakeCc(), relWarn = [];
  var off = FxPool.devWatch(rel, { warn: function (m) { relWarn.push(m); } });
  assert.strictEqual(off.report().active, false, 'CC_DEBUG unset -> off');
  assert.strictEqual(rel.Node, FakeNode, 'release build: cc.Node untouched');
  // 猫咪毛球 shape: new cc.Node in update, never removed
  var cc = fakeCc(), warns = [];
  var w = FxPool.devWatch(cc, { force: true, everyFrames: 10, samples: 3, warn: function (m) { warns.push(m); } });
  var outside = new cc.Node('ok');                          // onLoad-time creation: fine
  assert.ok(outside instanceof FakeNode, 'proxied cc.Node still builds real nodes');
  assert.strictEqual(w.report().madeInUpdate, 0);
  frames(cc, 60, function () { cc.scene.addChild(new cc.Node('leak')); });
  var rep = w.report();
  assert.strictEqual(rep.madeInUpdate, 60, 'every new cc.Node inside update counted');
  assert.ok(warns.some(function (m) { return /inside update/.test(m); }), 'warned: node made in update');
  assert.ok(warns.some(function (m) { return /grew/.test(m); }), 'warned: scene keeps growing');
  assert.strictEqual(warns.filter(function (m) { return /inside update/.test(m); }).length, 1, 'warns once, not every frame');
  w.stop();
  assert.strictEqual(cc.Node, FakeNode, 'stop restores cc.Node');
  // pooled game: spawns inside update but through the pool -> after warm-up no new nodes, no growth warning
  var cc2 = fakeCc(), warns2 = [], layer = new FakeNode('fx'); cc2.scene.addChild(layer);
  var pool = FxPool.create(cc2, { parent: layer, make: function () { return new FakeNode('spark'); }, life: 0.1, max: 16, warn: quiet });
  for (var k = 0; k < 16; k++) pool.release(pool.spawn(0, 0));   // warm the pool in onLoad
  var w2 = FxPool.devWatch(cc2, { force: true, everyFrames: 10, samples: 3, warn: function (m) { warns2.push(m); } });
  frames(cc2, 120, function (i) { if (i % 2 === 0) pool.spawn(i, 0); pool.tick(1 / 60); });
  assert.deepStrictEqual(warns2, [], 'pooled effects: no warnings');
  w2.stop();
  // 3.x: cc.Node is not proxied (imports), only the growth check runs
  var cc3 = fakeCc(true), warns3 = [];
  var w3 = FxPool.devWatch(cc3, { force: true, everyFrames: 10, samples: 3, warn: function (m) { warns3.push(m); } });
  assert.strictEqual(cc3.Node, FakeNode, '3.x: cc.Node untouched');
  frames(cc3, 60, function () { cc3.scene.addChild(new FakeNode('leak', true)); });
  assert.ok(warns3.some(function (m) { return /grew/.test(m); }), '3.x: growth warning');
  w3.stop();
});

// 6. the module carries no game names
var code = require('fs').readFileSync(FILE, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
['setInterval', 'setTimeout', 'autoRemoveOnFinish = true'].forEach(function (n) { assert.ok(code.indexOf(n) < 0, n); });
results.push('no engine timers in the part');

console.log('fx-pool: ' + results.length + ' groups passed (' + results.join('; ') + ')');
