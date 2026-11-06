'use strict';
// node tests/entity-retire.test.js  -- 生成时预防 R4L2 (问题普查 补查第 7 组 T15:invisible_enemy): an obstacle / enemy /
// bullet taken back through parts/FxPool.js or parts/RunSession.js turns off every collider and physics body on its
// node and children, stops their tweens and component schedules, and turns the colliders back on when it is reused.
// 回家快跑: the snail's animation child went back to its own pool after 5 s, the enemy root kept its collider: an
// invisible enemy blocked the runner.
// Negative controls: the old FxPool / RunSession (FX_POOL_FILE / RUN_SESSION_FILE pointing at the old copies) and the
// 回家快跑 shape written the old way (only the picture node is hidden) must FAIL the same checks.
var assert = require('assert');
var fs = require('fs');
var path = require('path');
var FX_FILE = process.env.FX_POOL_FILE || path.join(__dirname, '..', 'parts', 'FxPool.js');
var RS_FILE = process.env.RUN_SESSION_FILE || path.join(__dirname, '..', 'parts', 'RunSession.js');
delete require.cache[require.resolve(FX_FILE)];
delete require.cache[require.resolve(RS_FILE)];
var FxPool = require(FX_FILE);
var RunSession = require(RS_FILE);

// ---- a fake engine: just enough of cc.Node / components / scheduler / tween for this check ----
// Like the real engines, an inactive node pauses its tweens and component schedules and resumes them when it is
// active again; a collider takes part in hits while it is enabled and its node is active in the hierarchy.
function fakeCc(three) {
  var tweens = [], stopped = [];
  function Component() { this.enabled = true; this.node = null; this.isValid = true; this.scheduled = []; }
  Component.prototype.schedule = function (fn, sec) { this.scheduled.push({ fn: fn, every: sec, left: sec }); };
  Component.prototype.unscheduleAllCallbacks = function () { this.scheduled = []; };
  function sub(Base) { function T() { Base.call(this); } T.prototype = Object.create(Base.prototype); T.prototype.constructor = T; return T; }
  var cc = { Component: Component, tweens: tweens, stopped: stopped };
  if (three) {
    cc.UITransform = function () {};
    cc.Collider2D = sub(Component); cc.BoxCollider2D = sub(cc.Collider2D); cc.RigidBody2D = sub(Component);
  } else {
    cc.Collider = sub(Component); cc.BoxCollider = sub(cc.Collider);
    cc.PhysicsCollider = sub(Component); cc.PhysicsBoxCollider = sub(cc.PhysicsCollider); cc.RigidBody = sub(Component);
  }
  cc.Sprite = sub(Component);
  function Node(name) {
    this.name = name; this.children = []; this.parent = null; this.active = true; this.isValid = true;
    this.opacity = 255; this._components = []; this.x = 0; this.y = 0;
  }
  Node.prototype.addChild = function (c) { if (c.parent) c.parent.removeChild(c); this.children.push(c); c.parent = this; };
  Node.prototype.removeChild = function (c) { var i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; };
  Node.prototype.addComponent = function (T) { var c = new T(); c.node = this; this._components.push(c); return c; };
  Node.prototype.getComponents = function (T) { return this._components.filter(function (c) { return c instanceof T; }); };
  Node.prototype.destroy = function () { this.isValid = false; if (this.parent) this.parent.removeChild(this); };
  Node.prototype.setPosition = function (x, y) { this.x = x; this.y = y; };
  Object.defineProperty(Node.prototype, 'activeInHierarchy', { get: function () {
    for (var n = this; n; n = n.parent) if (!n.active) return false; return true; } });
  cc.Node = Node;
  cc.isValid = function (n) { return !!n && n.isValid !== false; };
  // cc.tween(target).to(sec, {prop: value}): linear, only advances while the target's node is active
  cc.tween = function (target, sec, props) { var t = { target: target, left: sec, props: props, dead: false }; tweens.push(t); return t; };
  cc.Tween = { stopAllByTarget: function (target) { stopped.push(target); tweens.forEach(function (t) { if (t.target === target) t.dead = true; }); } };
  function nodeOf(target) { return target instanceof Node ? target : target.node; }
  function all(root, out) { out.push(root); root.children.forEach(function (c) { all(c, out); }); return out; }
  cc.scene = new Node('scene');
  // one engine frame: tweens and component schedules of active nodes advance
  cc.frame = function (dt) {
    tweens.forEach(function (t) {
      if (t.dead || !nodeOf(t.target).activeInHierarchy) return;
      t.left -= dt;
      if (t.left <= 0) { for (var k in t.props) t.target[k] = t.props[k]; t.dead = true; }
    });
    all(cc.scene, []).forEach(function (n) {
      if (!n.activeInHierarchy) return;
      n._components.forEach(function (c) {
        if (!c.enabled) return;
        c.scheduled.forEach(function (s) { s.left -= dt; if (s.left <= 0) { s.left += s.every; s.fn(); } });
      });
    });
  };
  cc.bodyTypes = three ? [cc.Collider2D, cc.RigidBody2D] : [cc.Collider, cc.PhysicsCollider, cc.RigidBody];
  // what the runner hits: enabled colliders on nodes active in the hierarchy; "invisible" = no visible picture under it
  cc.blockers = function () {
    return all(cc.scene, []).filter(function (n) {
      return n.activeInHierarchy && n._components.some(function (c) { return c.enabled && (three ? c instanceof cc.Collider2D : c instanceof cc.Collider || c instanceof cc.PhysicsCollider); });
    });
  };
  cc.visible = function (n) { return all(n, []).some(function (m) { return m.activeInHierarchy && m.opacity > 0 && m.getComponents(cc.Sprite).length; }); };
  return cc;
}

// an enemy the way a generated game builds it: root with collider (+ physics body), picture child with its own collider
// (a hit box on the picture), a fade tween on the picture, a component that shoots every second
function makeEnemy(cc, three) {
  var root = new cc.Node('enemy');
  var bodies = three ? [root.addComponent(cc.BoxCollider2D), root.addComponent(cc.RigidBody2D)]
    : [root.addComponent(cc.BoxCollider), root.addComponent(cc.PhysicsBoxCollider), root.addComponent(cc.RigidBody)];
  var pic = new cc.Node('pic'); pic.addComponent(cc.Sprite); root.addChild(pic);
  var hitBox = pic.addComponent(three ? cc.BoxCollider2D : cc.BoxCollider);
  var off = root.addComponent(three ? cc.BoxCollider2D : cc.BoxCollider); off.enabled = false;   // the game's own off switch
  var ai = root.addComponent(cc.Component); ai.shots = 0;
  ai.schedule(function () { ai.shots += 1; }, 1);
  return { root: root, pic: pic, bodies: bodies.concat([hitBox]), off: off, ai: ai };
}
function enabledBodies(e) { return e.bodies.filter(function (b) { return b.enabled; }).length; }

var results = [], failures = [];
function check(name, fn) {
  try { fn(); results.push(name); } catch (err) { failures.push(name + ': ' + err.message); }
}

[false, true].forEach(function (three) {
  var tag = three ? '3.x' : '2.4';

  // 1. FxPool: an enemy hit by a bullet goes back to the pool; its death fade on the picture is still running
  check(tag + ' FxPool return turns the bodies off, spawn turns them back on', function () {
    var cc = fakeCc(three), layer = new cc.Node('enemies'); cc.scene.addChild(layer);
    var e = null;
    // reset the way game-modules.md tells generated games to: picture back to full opacity, the shoot timer started anew
    var reset = function () { e.pic.opacity = 255; e.ai.schedule(function () { e.ai.shots += 1; }, 1); e.ai.shots = 0; };
    var pool = FxPool.create(cc, { parent: layer, make: function () { e = makeEnemy(cc, three); e.ai.unscheduleAllCallbacks(); return e.root; },
      reset: reset, life: 0, max: 4, warn: function () {} });
    var n = pool.spawn(100, 0);
    cc.tween(e.pic, 0.3, { opacity: 0 });                  // death fade, started just before the hit
    cc.frame(0.1);
    pool.release(n);
    assert.strictEqual(enabledBodies(e), 0, 'after return every collider / body on the enemy and its picture is off (' + enabledBodies(e) + ' still on)');
    assert.strictEqual(e.root.active, false, 'returned enemy is inactive');
    var n2 = pool.spawn(200, 0);
    assert.strictEqual(n2, n, 'the same enemy node is reused');
    assert.strictEqual(enabledBodies(e), e.bodies.length, 'reused enemy: colliders back on');
    assert.strictEqual(e.off.enabled, false, 'a collider the game had turned off itself stays off');
    cc.frame(0.95);
    assert.strictEqual(e.pic.opacity, 255, 'the old death fade does not resume on the reused enemy (opacity ' + e.pic.opacity + ')');
    assert.ok(cc.visible(e.root) || cc.blockers().indexOf(e.root) < 0, 'no invisible enemy after reuse');
    assert.strictEqual(e.ai.shots, 0, 'the old enemy\'s shoot schedule does not carry over (' + e.ai.shots + ' shots in 0.95 s)');
    cc.frame(0.1);
    assert.strictEqual(e.ai.shots, 1, 'the timer started in reset runs once per second');
  });

  // 2. RunSession.recycle / reuse: same contract, plus session timers bound to the enemy are cancelled
  check(tag + ' RunSession.recycle / reuse', function () {
    var cc = fakeCc(three), layer = new cc.Node('enemies'); cc.scene.addChild(layer);
    var s = RunSession.create(cc, { autoHide: false, sceneBound: false, warn: function () {} });
    s.newRun(function () { return { hits: 0 }; });
    var e = makeEnemy(cc, three); layer.addChild(e.root);
    var fired = 0, other = 0;
    assert.strictEqual(typeof s.recycle, 'function', 'session.recycle exists');
    s.after(500, function () { fired += 1; }, e.pic);       // a timer bound to the enemy (its picture)
    s.after(500, function () { other += 1; });               // an unrelated run timer
    var off = s.recycle(e.root);
    assert.strictEqual(off, e.bodies.length, 'recycle reports the bodies it turned off');
    assert.strictEqual(enabledBodies(e), 0, 'after recycle every collider / body is off');
    assert.strictEqual(e.root.active, false);
    for (var i = 0; i < 10; i++) s.tick(0.1);
    assert.strictEqual(fired, 0, 'timer bound to the recycled enemy cancelled');
    assert.strictEqual(other, 1, 'unrelated timer still runs');
    assert.strictEqual(s.reuse(e.root), e.bodies.length, 'reuse turns the same bodies back on');
    assert.strictEqual(enabledBodies(e), e.bodies.length);
    assert.strictEqual(e.off.enabled, false, 'game-disabled collider stays off');
    assert.strictEqual(e.root.active, true);
    // recycle with destroy: bodies are off before the deferred destroy (no hit in the same frame)
    var e2 = makeEnemy(cc, three); layer.addChild(e2.root);
    s.recycle(e2.root, { destroy: true });
    assert.strictEqual(enabledBodies(e2), 0); assert.strictEqual(e2.root.isValid, false);
    // static form without a session
    var e3 = makeEnemy(cc, three); layer.addChild(e3.root);
    RunSession.retire(cc, e3.root); assert.strictEqual(enabledBodies(e3), 0);
    RunSession.revive(cc, e3.root); assert.strictEqual(enabledBodies(e3), e3.bodies.length);
    assert.strictEqual(RunSession.revive(cc, e3.root), 0, 'revive twice: nothing more to turn on');
  });

  // 3. 回家快跑 shape: the animation child is hidden on its own after 5 s, the enemy root stays -> invisible blocker.
  //    Old way must fail "no invisible enemy"; the new way (recycle the root) passes.
  check(tag + ' 回家快跑 snail: hide the picture only (old way) vs recycle the root (new way)', function () {
    function play(useRecycle) {
      var cc = fakeCc(three), layer = new cc.Node('enemies'); cc.scene.addChild(layer);
      var s = RunSession.create(cc, { autoHide: false, sceneBound: false, warn: function () {} });
      s.newRun();
      var e = makeEnemy(cc, three); layer.addChild(e.root);
      s.after(5000, function () {
        if (useRecycle) s.recycle(e.root);
        else e.pic.active = false;                          // old: the 5 s animation goes back, the root and collider stay
      }, e.root);
      for (var i = 0; i < 60; i++) { s.tick(0.1); cc.frame(0.1); }
      var b = cc.blockers();
      return { invisible: b.filter(function (n) { return !cc.visible(n); }).length, blockers: b.length, bodiesOn: enabledBodies(e) };
    }
    assert.ok(play(false).invisible > 0, 'negative control: the old way leaves an invisible blocker');
    var r = play(true);
    assert.deepStrictEqual(r, { invisible: 0, blockers: 0, bodiesOn: 0 }, 'recycle the root after 5 s: nothing blocks, every body off');
  });
});

// 4. the shared code is one block, byte for byte the same in both parts
check('entity-retire block identical in FxPool.js and RunSession.js', function () {
  function block(file) {
    var m = /\n[ ]*\/\/ BEGIN entity-retire[\s\S]*?\/\/ END entity-retire\n/.exec(fs.readFileSync(file, 'utf8'));
    assert.ok(m, path.basename(file) + ' has the BEGIN/END entity-retire block');
    return m[0];
  }
  assert.strictEqual(block(FX_FILE), block(RS_FILE), 'the two copies differ');
});

if (failures.length) {
  console.error('entity-retire: ' + failures.length + ' FAILED\n  ' + failures.join('\n  '));
  process.exit(1);
}
console.log('entity-retire: ' + results.length + ' groups passed (' + results.join('; ') + ')');
