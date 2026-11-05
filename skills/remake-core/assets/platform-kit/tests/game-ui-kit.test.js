'use strict';
// node tests/game-ui-kit.test.js   (生成时预防 P05: parts/GameUIKit.js, Cocos 2.4, and parts-3x/GameUIKit.ts, Cocos 3.x)
// A2 批: every case runs on both engines (GAMEUI_KINDS=24 or 3x picks one); the hand-written copies are the same.
// Each case runs the kit AND a "hand-written the old way" copy taken from the census (问题普查 20261104): the kit must
// pass, the hand-written copy must show the bug. Taps go through env.tapAt (topmost active touch node, like 2.4).
var assert = require('assert');
var S = require('./engine-stub-ui');

var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var KIND = KINDS[0];
function fresh() { var env = S.loadKit(KIND); env.Kit._reset(); return env; }
function node(env, name, w, h, x, y, parent) {
  var n = new env.cc.Node(name); (parent || env.canvas).addChild(n);
  n.setContentSize(w, h); n.setPosition(x || 0, y || 0); return n;
}
function homeButton(env) {
  var calls = {n: 0};
  var n = node(env, 'Home', 240, 100, 0, -300);
  env.Kit.button(n, function () { calls.n++; }, {name: 'Home'});
  return {node: n, calls: calls};
}
function popup(env, o) {
  o = o || {};
  var p = env.Kit.popup(env.canvas, {panelFrame: env.frame(560, 700), closeFrame: env.frame(o.close || 64, o.close || 64), keep: o.keep});
  env.flush();
  return p;
}

// ---- hand-written copies (the old way)
// 花园守卫者 / 星星点点消: popup with its own mask; closing only fades it out (node stays active)
function handPopup(env, blockInput) {
  var root = node(env, 'HandPopup', 720, 1280);
  root.zIndex = 30000;
  var mask = node(env, 'Mask', 720, 1280, 0, 0, root);
  mask.addComponent(env.cc.Sprite);                         // a dim picture
  if (blockInput) mask.addComponent(env.cc.BlockInputEvents);
  return {root: root, mask: mask,
    close: function () { env.cc.tween(root).to(0.16, {opacity: 0}).start(); },       // fade only
    rebuild: function () { root.destroy(); return handPopup(env, blockInput); }};
}
// 割草 revive: handler bound by name, the method does not exist; Cocos 2.4 EventHandler skips it silently
function bindByName(n, comp, name) {
  n.on('touch-end', function () { var f = comp[name]; if (typeof f === 'function') f.call(comp); });
}
// cc.Button as the engine runs it: clickEvents on touch-end, SCALE transition while pressed
function engineButton(env, n, events, scale) {
  var b = n.addComponent(env.cc.Button);
  b.clickEvents = events; b.transition = scale ? env.cc.Button.Transition.SCALE : env.cc.Button.Transition.COLOR;
  n.on('touch-start', function () { if (b.transition === env.cc.Button.Transition.SCALE) n.scale = 0.9; });
  n.on('touch-end', function () { (b.clickEvents || []).forEach(function (e) { e(); }); n.scale = 1; });
  return b;
}
// engine: a Sprite whose sizeMode is not CUSTOM resizes its node to every new frame (animation)
function playFrame(env, n, frame) {
  var s = n.getComponent(env.cc.Sprite); s.spriteFrame = frame;
  if (s.sizeMode !== env.cc.Sprite.SizeMode.CUSTOM) n.setContentSize(frame.getOriginalSize());
}

test('1 popup open: a tap on the page underneath is swallowed (hand mask without BlockInputEvents lets it through)', function () {
  var env = fresh(), home = homeButton(env);
  var p = popup(env);
  assert.ok(env.tapAt(0, -300) === p.mask, 'the mask takes the tap');
  assert.strictEqual(home.calls.n, 0);
  var env2 = fresh(), home2 = homeButton(env2);
  handPopup(env2, false);
  env2.tapAt(0, -300);
  assert.strictEqual(home2.calls.n, 1, 'OLD WAY BUG: hand mask without BlockInputEvents passes the tap to Home');
});

test('2 close(): after the 160 ms fade the popup is inactive and the page works (hand fade-out keeps blocking)', function () {
  [false, true].forEach(function (keep) {
    var env = fresh(), home = homeButton(env);
    var p = popup(env, {keep: keep});
    p.close();
    env.clock.advance(160); env.flush();
    assert.ok(!env.cc.isValid(p.root) || p.root.active === false, 'popup root inactive (keep ' + keep + ')');
    env.clock.advance(600);
    env.tapAt(0, -300);
    assert.strictEqual(home.calls.n, 1, 'Home works after close (keep ' + keep + ')');
  });
  var env2 = fresh(), home2 = homeButton(env2);
  var h = handPopup(env2, true);
  h.close(); env2.flush();
  assert.strictEqual(h.root.opacity, 0, 'hand popup is invisible');
  env2.tapAt(0, -300);
  assert.strictEqual(home2.calls.n, 0, 'OLD WAY BUG: the invisible hand popup still swallows the tap');
});

test('3 two taps within 100 ms call the handler once (plain node.on calls it twice)', function () {
  var env = fresh(), home = homeButton(env);
  env.tapAt(0, -300); env.clock.advance(100); env.tapAt(0, -300);
  assert.strictEqual(home.calls.n, 1);
  env.clock.advance(500); env.tapAt(0, -300);
  assert.strictEqual(home.calls.n, 2, 'a tap after 500 ms works again');
  var n = 0, b = node(env, 'HandClaim', 200, 90, 0, 300);
  b.on('touch-end', function () { n++; });
  env.tapAt(0, 300); env.clock.advance(100); env.tapAt(0, 300);
  assert.strictEqual(n, 2, 'OLD WAY BUG: hand button pays twice');
});

test('4 a missing handler throws when the page is built (bind-by-name stays silent and does nothing)', function () {
  var env = fresh();
  var comp = {onReviveAd: function () {}};
  var n = node(env, 'Revive', 300, 110);
  assert.throws(function () { env.Kit.button(n, comp.onRevive, {name: 'Revive'}); }, /handler of "Revive" is undefined/);
  assert.throws(function () { env.Kit.button(n, 'onRevive'); }, /is string/);
  assert.throws(function () { env.Kit.wrapExisting(n, undefined); }, /wrapExisting/);
  var ran = 0, m = node(env, 'HandRevive', 300, 110, 0, 200);
  comp.onReviveAd = function () { ran++; };
  assert.doesNotThrow(function () { bindByName(m, comp, 'onRevive'); }, 'old way: no error when binding');
  env.tapAt(0, 200);
  assert.strictEqual(ran, 0, 'OLD WAY BUG: tap does nothing and nobody is told');
});

test('5 keep:true reopens the same nodes (hand rebuild creates and destroys a whole page each time)', function () {
  var env = fresh();
  var p = popup(env, {keep: true});
  p.close(); env.flush();
  var created = env.stats.created, destroyed = env.stats.destroyed;
  for (var i = 0; i < 3; i++) { assert.strictEqual(p.open(), true); env.flush(); p.close(); env.flush(); }
  assert.strictEqual(env.stats.created, created, 'no node created on reopen');
  assert.strictEqual(env.stats.destroyed, destroyed, 'no node destroyed on close');
  var env2 = fresh(), h = handPopup(env2, true), c0 = env2.stats.created;
  for (var j = 0; j < 3; j++) h = h.rebuild();
  assert.ok(env2.stats.created > c0, 'OLD WAY BUG: rebuild makes new nodes every time (flash frame)');
});

test('6 close X hit area >= 104 x 104 from a 32 px picture (hand 32 x 32 X misses a finger 40 px off)', function () {
  var env = fresh();
  var p = popup(env, {close: 32});
  assert.ok(p.closeNode.width >= 104 && p.closeNode.height >= 104, 'close hit area ' + p.closeNode.width);
  var b = env.worldBox(p.closeNode);
  assert.strictEqual(env.tapAt(b.x - 40, b.y - 40), p.closeNode, 'a tap 40 px off the X centre still closes');
  var x = node(env, 'X', 32, 32, 200, 500);
  env.Kit.button(x, function () {}, {close: true});
  assert.ok(x.width >= 104 && x.height >= 104, 'UI.button close:true widens a 32 px X');
  var env2 = fresh(), hx = node(env2, 'HandX', 32, 32, 200, 500), hit = 0;
  hx.on('touch-end', function () { hit++; });
  env2.tapAt(240, 540);
  assert.strictEqual(hit, 0, 'OLD WAY BUG: a 32 px X misses a finger 40 px off');
});

test('7 press keeps the hit area: no press scale, animation frames do not resize the button', function () {
  var env = fresh(), n = node(env, 'Play', 300, 120, 0, 0), calls = 0;
  n.addComponent(env.cc.Sprite).sizeMode = env.cc.Sprite.SizeMode.TRIMMED;
  env.Kit.button(n, function () { calls++; });
  var before = env.worldBox(n);
  n.emit('touch-start');
  assert.ok(env.hitNode(145, 0) === n, 'edge of the button still hit while pressed');
  env.tapAt(0, 0);
  assert.strictEqual(n.scale, 1, 'no scale on press');
  playFrame(env, n, env.frame(420, 260));                 // glow frame of the idle animation
  assert.deepStrictEqual(env.worldBox(n), before, 'hit area unchanged by the animation frame');
  assert.strictEqual(calls, 1);
  var env2 = fresh(), m = node(env2, 'HandPlay', 300, 120, 0, 0);
  m.addComponent(env2.cc.Sprite).sizeMode = env2.cc.Sprite.SizeMode.TRIMMED;
  engineButton(env2, m, [function () {}], true);
  m.emit('touch-start');
  assert.strictEqual(env2.hitNode(145, 0), null, 'OLD WAY BUG: SCALE transition shrinks the button under the finger');
  playFrame(env2, m, env2.frame(420, 260));
  assert.notDeepStrictEqual(env2.worldBox(m), {x: 0, y: 0, width: 300, height: 120}, 'OLD WAY BUG: animation frame resizes the hit area');
});

test('8 popup.guard drops a late callback after close and after reopen (a plain callback writes into the closed page)', function () {
  var env = fresh();
  var p = popup(env, {keep: true}), ran = [];
  var late = p.guard(function () { ran.push('first'); });
  p.close(); env.flush();
  late();
  assert.deepStrictEqual(ran, [], 'dropped after close');
  p.open(); env.flush();
  late();
  assert.deepStrictEqual(ran, [], 'still dropped after reopen (belongs to the earlier opening)');
  p.guard(function () { ran.push('second'); })();
  assert.deepStrictEqual(ran, ['second'], 'a callback of the current opening runs');
  var env2 = fresh(), h = handPopup(env2, true), wrote = 0;
  var plain = function () { wrote++; };
  h.close(); env2.flush(); plain();
  assert.strictEqual(wrote, 1, 'OLD WAY BUG: the late callback still runs on the closed popup');
});

test('9 a disabled button explains itself (hand interactable=false does nothing)', function () {
  var env = fresh(), n = node(env, 'Claim', 260, 100, 0, 100), calls = 0, told = 0;
  var b = env.Kit.button(n, function () { calls++; }, {disabledText: 'Come back tomorrow', onDisabledTap: function () { told++; }});
  b.setEnabled(false);
  env.tapAt(0, 100);
  assert.strictEqual(calls, 0);
  assert.strictEqual(told, 1);
  assert.strictEqual(env.Kit.toastText(), 'Come back tomorrow');
  b.setEnabled(true); env.clock.advance(600); env.tapAt(0, 100);
  assert.strictEqual(calls, 1);
});

test('10 wrapExisting: an original cc.Button runs once, SCALE becomes COLOR (adding node.on beside it pays twice)', function () {
  var env = fresh(), n = node(env, 'OrigShop', 220, 90, 0, -100), old = 0, now = 0;
  n.addComponent(env.cc.Sprite).spriteFrame = env.frame(260, 110);
  var btn = engineButton(env, n, [function () { old++; }], true);
  var h = env.Kit.wrapExisting(n, function () { now++; });
  env.tapAt(0, -100);
  assert.strictEqual(now, 1); assert.strictEqual(old, 0, 'old click events are off');
  assert.strictEqual(h.oldClickEvents.length, 1, 'kept for the record');
  assert.strictEqual(btn.transition, env.cc.Button.Transition.COLOR);
  assert.ok(n.width >= 260 && n.height >= 110, 'hit area grew to the visible picture');
  var env2 = fresh(), m = node(env2, 'HandShop', 220, 90, 0, -100), paid = 0;
  engineButton(env2, m, [function () { paid++; }], true);
  m.on('touch-end', function () { paid++; });
  env2.tapAt(0, -100);
  assert.strictEqual(paid, 2, 'OLD WAY BUG: original click event plus the new listener');
});

var failed = 0;
KINDS.forEach(function (k) {
  KIND = k;
  cases.forEach(function (c) {
    try { c.fn(); console.log('PASS [' + k + '] ' + c.name); } catch (e) { failed++; console.log('FAIL [' + k + '] ' + c.name + '\n     ' + (e && e.message)); }
  });
});
console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit ' + KINDS.join(' + ') + ', Node stand-in; 待真机复测)');
if (failed) process.exitCode = 1;
