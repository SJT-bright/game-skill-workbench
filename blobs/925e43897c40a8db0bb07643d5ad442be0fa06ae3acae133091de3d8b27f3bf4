'use strict';
// node tests/touch-owner.test.js  -- parts/TouchOwner.js (v7.9, 生成时预防 P13): one finger per control, one swipe rule,
// camera-correct touch points. Fake engines: Cocos 2.4 (cc.Node.EventType touchstart..., event.getID / getLocation,
// cc.Camera.findCamera + getScreenToWorldPoint, cc.game EVENT_HIDE) and 3.x ('touch-start'..., getUILocation /
// getLocation, Camera.screenToWorld, Canvas.cameraComponent, visibility / layer / priority).
// Negative controls are the old ways the 问题普查 found: last-touch-wins joystick (我出枪贼快, TooLit), a "touching" flag
// reset only on touchend (甜点消消乐 R47), a swipe that needs both axes past the threshold (立方体数字), a world point
// made by hand from getLocation (SockDrawerShowdown, 激光宝库), and the first camera in the scene (飞车 3D camera first).
var assert = require('assert');
var path = require('path');
var Touch = require(path.join(__dirname, '..', 'parts', 'TouchOwner.js'));

function emitter() {
  var h = {};
  return {
    on: function (t, fn) { (h[t] = h[t] || []).push(fn); },
    off: function (t, fn) { h[t] = (h[t] || []).filter(function (f) { return f !== fn; }); },
    emit: function (t, e) { (h[t] || []).slice().forEach(function (f) { f(e); }); },
    count: function (t) { return (h[t] || []).length; }
  };
}
function cc24() {
  var game = emitter(); game.EVENT_HIDE = 'game_on_hide'; game.EVENT_SHOW = 'game_on_show';
  return { v2: function (x, y) { return { x: x, y: y }; }, game: game,
    Node: { EventType: { TOUCH_START: 'touchstart', TOUCH_MOVE: 'touchmove', TOUCH_END: 'touchend', TOUCH_CANCEL: 'touchcancel' } } };
}
function cc3() {
  var cc = cc24();
  cc.Node.EventType = { TOUCH_START: 'touch-start', TOUCH_MOVE: 'touch-move', TOUCH_END: 'touch-end', TOUCH_CANCEL: 'touch-cancel' };
  cc.UITransform = function () {}; cc.Canvas = function () {}; cc.Camera = function () {};
  cc.Vec3 = function (x, y, z) { this.x = x; this.y = y; this.z = z; };
  return cc;
}
function ev(id, x, y) {
  return { getID: function () { return id; }, getLocation: function () { return { x: x, y: y }; },
    getUILocation: function () { return { x: x, y: y }; }, stopped: false, stopPropagation: function () { this.stopped = true; } };
}
function T24(cc) { return cc.Node.EventType; }

var results = [];
function test(name, fn) {
  try { fn(); results.push(['PASS', name]); } catch (e) { results.push(['FAIL', name + ': ' + (e && e.stack || e)]); }
}

// joystick direction from a centre, as games write it
function dirOf(c, p) { return Math.atan2(p.y - c.y, p.x - c.x); }

[['2.4', cc24], ['3.x', cc3]].forEach(function (E) {
  test(E[0] + ' claim: two fingers at once, only the first moves the joystick; the second never reaches the handlers', function () {
    var cc = E[1](), node = emitter(), T = cc.Node.EventType, seen = [], angle = null, C = { x: 200, y: 200 };
    var h = Touch.claim(cc, node, {
      onStart: function (e, i) { seen.push(['start', i.id]); },
      onMove: function (e, i) { seen.push(['move', i.id]); angle = dirOf(C, i.pos); },
      onEnd: function (e, i) { seen.push(['end', i.id, i.cancelled]); }
    });
    node.emit(T.TOUCH_START, ev(0, 200, 200));
    node.emit(T.TOUCH_MOVE, ev(0, 300, 200));          // right
    node.emit(T.TOUCH_START, ev(1, 200, 50));
    node.emit(T.TOUCH_MOVE, ev(1, 200, 0));            // second finger pulls down
    node.emit(T.TOUCH_END, ev(1, 200, 0));
    assert.strictEqual(angle, 0, 'still pointing right');
    assert.strictEqual(h.owner(), 0);
    node.emit(T.TOUCH_END, ev(0, 300, 200));
    assert.deepStrictEqual(seen, [['start', 0], ['move', 0], ['end', 0, false]]);
    assert.strictEqual(h.owner(), null);
    node.emit(T.TOUCH_START, ev(1, 10, 10));           // free again: the next finger owns it
    assert.strictEqual(h.owner(), 1);
    h.off(); assert.strictEqual(node.count(T.TOUCH_START), 0);
  });
});

test('negative control: last-touch-wins joystick (no id kept) is turned by the second finger', function () {
  var node = emitter(), angle = null, C = { x: 200, y: 200 };
  node.on('touchmove', function (e) { angle = dirOf(C, e.getLocation()); });
  node.emit('touchmove', ev(0, 300, 200));
  node.emit('touchmove', ev(1, 200, 0));
  assert.notStrictEqual(angle, 0, 'old joystick follows finger 2');
});

test('touchcancel releases the owner (onEnd cancelled, once); the next tap works', function () {
  var cc = cc24(), node = emitter(), T = T24(cc), ends = [], starts = 0;
  var h = Touch.claim(cc, node, { onStart: function () { starts++; }, onEnd: function (e, i) { ends.push(i.cancelled); } });
  node.emit(T.TOUCH_START, ev(3, 10, 10));
  node.emit(T.TOUCH_CANCEL, ev(3, 10, 10));
  node.emit(T.TOUCH_CANCEL, ev(3, 10, 10));          // a second cancel for the same finger is ignored
  assert.deepStrictEqual(ends, [true]);
  assert.strictEqual(h.owner(), null);
  node.emit(T.TOUCH_START, ev(4, 10, 10));
  assert.strictEqual(starts, 2);
});

test('negative control: a "touching" flag reset only on touchend ignores every tap after a cancel', function () {
  var node = emitter(), touching = false, taps = 0;
  node.on('touchstart', function () { if (touching) return; touching = true; taps++; });
  node.on('touchend', function () { touching = false; });
  node.emit('touchstart', ev(0)); node.emit('touchcancel', ev(0)); node.emit('touchstart', ev(1));
  assert.strictEqual(taps, 1, 'the tap after the cancel is lost');
});

test('EVENT_HIDE releases a held finger; the kit TOUCH_CANCEL sent afterwards does not end it twice', function () {
  var cc = cc24(), node = emitter(), T = T24(cc), ends = [];
  Touch.claim(cc, node, { onEnd: function (e, i) { ends.push([i.id, i.cancelled]); } });
  node.emit(T.TOUCH_START, ev(0, 5, 5));
  cc.game.emit(cc.game.EVENT_HIDE);                   // TikTok takes the game away
  node.emit(T.TOUCH_CANCEL, ev(0, 5, 5));             // touch-coordinates.js cancelStale on EVENT_SHOW
  assert.deepStrictEqual(ends, [[0, true]]);
  node.emit(T.TOUCH_START, ev(0, 6, 6));              // same id after return: a clean new touch
  node.emit(T.TOUCH_END, ev(0, 6, 6));
  assert.deepStrictEqual(ends, [[0, true], [0, false]]);
  // without the kit touch part (no TOUCH_CANCEL ever comes): EVENT_HIDE alone frees the control for another finger
  var cc2 = cc24(), bare = emitter(), log = [];
  var h = Touch.claim(cc2, bare, { onStart: function (e, i) { log.push('s' + i.id); }, onEnd: function (e, i) { log.push('e' + i.id + (i.cancelled ? 'c' : '')); } });
  bare.emit(T.TOUCH_START, ev(5, 1, 1));
  cc2.game.emit(cc2.game.EVENT_HIDE);
  assert.strictEqual(h.owner(), null);
  bare.emit(T.TOUCH_START, ev(6, 2, 2));
  assert.deepStrictEqual(log, ['s5', 'e5c', 's6']);
});

test('same id again while owned (its end never came): the old touch ends cancelled and a new one starts', function () {
  var cc = cc3(), node = emitter(), T = cc.Node.EventType, log = [];
  Touch.claim(cc, node, { onStart: function (e, i) { log.push(['s', i.start.x]); }, onEnd: function (e, i) { log.push(['e', i.cancelled]); } });
  node.emit(T.TOUCH_START, ev(0, 1, 1));
  node.emit(T.TOUCH_START, ev(0, 50, 1));
  assert.deepStrictEqual(log, [['s', 1], ['e', true], ['s', 50]]);
});

test('no time limit: a 6 s hold still drags, duration reported', function () {
  var cc = cc24(), node = emitter(), T = T24(cc), t = 0, moves = [];
  Touch.claim(cc, node, { onMove: function (e, i) { moves.push([i.duration, i.delta.x, i.total.x]); } }, { now: function () { return t; } });
  node.emit(T.TOUCH_START, ev(0, 100, 100));
  t = 6000; node.emit(T.TOUCH_MOVE, ev(0, 130, 100));
  t = 6016; node.emit(T.TOUCH_MOVE, ev(0, 150, 100));
  assert.deepStrictEqual(moves, [[6000, 30, 30], [6016, 20, 50]]);
});

test('direction(): pure horizontal / vertical, diagonal, ties, below minDist', function () {
  assert.strictEqual(Touch.direction(100, 0, 40), 'right');
  assert.strictEqual(Touch.direction(-100, 0, 40), 'left');
  assert.strictEqual(Touch.direction(0, 100, 40), 'up');
  assert.strictEqual(Touch.direction(0, -100, 40), 'down');
  assert.strictEqual(Touch.direction(60, -80, 40), 'down');
  assert.strictEqual(Touch.direction(50, 50, 40), 'right');
  assert.strictEqual(Touch.direction(30, 20, 40), null);
  assert.strictEqual(Touch.direction(NaN, 0, 40), null);
});

test('swipe(): the four directions on touchend, short = tap, cancelled = nothing, early fires once', function () {
  var cc = cc3(), T = cc.Node.EventType, got = [];
  var node = emitter();
  Touch.swipe(cc, node, { minDist: 40, onSwipe: function (d) { got.push(d); }, onTap: function () { got.push('tap'); } });
  function go(id, x2, y2, end) { node.emit(T.TOUCH_START, ev(id, 200, 200)); node.emit(T.TOUCH_MOVE, ev(id, x2, y2)); node.emit(end || T.TOUCH_END, ev(id, x2, y2)); }
  go(0, 300, 200); go(1, 100, 200); go(2, 200, 300); go(3, 200, 100); go(4, 210, 205); go(5, 400, 200, T.TOUCH_CANCEL);
  assert.deepStrictEqual(got, ['right', 'left', 'up', 'down', 'tap']);
  var early = emitter(), e2 = [];
  Touch.swipe(cc, early, { early: true, onSwipe: function (d) { e2.push(d); } });
  early.emit(T.TOUCH_START, ev(0, 0, 0)); early.emit(T.TOUCH_MOVE, ev(0, 50, 0)); early.emit(T.TOUCH_MOVE, ev(0, 150, 0)); early.emit(T.TOUCH_END, ev(0, 150, 0));
  assert.deepStrictEqual(e2, ['right']);
});

test('negative control: the old swipe that needs both axes past the threshold drops pure horizontal / vertical', function () {
  function old(dx, dy) { if (Math.abs(dx) > 40 && Math.abs(dy) > 40) return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'up' : 'down'); return null; }
  assert.strictEqual(old(100, 0), null);
  assert.strictEqual(old(0, -100), null);
});

test('toWorld (2.4): camera moved by (100, 0) -> point through the camera; hand-made getLocation is 100 off', function () {
  var cc = cc24(), cam = { getScreenToWorldPoint: function (p) { return { x: p.x + 100, y: p.y }; } };
  cc.Camera = { findCamera: function () { return cam; } };
  var e = ev(0, 50, 60), node = {};
  assert.deepStrictEqual(Touch.toWorld(cc, e, null, node), { x: 150, y: 60 });
  assert.deepStrictEqual(Touch.toWorld(cc, e, cam), { x: 150, y: 60 });
  var hand = e.getLocation();
  assert.strictEqual(150 - hand.x, 100, 'old hand conversion misses by the camera offset');
  // hit(): node at world x 150 (convertToNodeSpaceAR subtracts its world position), 40 x 40
  var btn = { width: 40, height: 40, anchorX: 0.5, anchorY: 0.5, convertToNodeSpaceAR: function (p) { return { x: p.x - 150, y: p.y - 60 }; } };
  assert.strictEqual(Touch.hit(cc, e, btn, cam), true);
  assert.strictEqual(Touch.hit(cc, ev(0, 150, 60), btn, cam), false, 'the hand-made point (150 screen = 250 world) misses');
});

test('toWorld / cameraFor (3.x): Canvas camera above the node, else layer + priority, never cams[0]', function () {
  var cc = cc3();
  function camera(dx, prio, vis) { var c = new cc.Camera(); c.priority = prio; c.visibility = vis; c.enabledInHierarchy = true;
    c.screenToWorld = function (s, out) { out.x = s.x + dx; out.y = s.y; return out; }; return c; }
  var cam3d = camera(-999, 0, 1), uiLow = camera(10, 1, 1 << 25), uiCam = camera(100, 5, 1 << 25);
  var scene = { getComponentsInChildren: function () { return [cam3d, uiLow, uiCam]; } };
  cc.director = { getScene: function () { return scene; } };
  var node = { layer: 1 << 25, parent: null, getComponent: function () { return null; } };
  assert.strictEqual(Touch.cameraFor(cc, node), uiCam);
  var e = ev(0, 50, 60);
  assert.deepStrictEqual(Touch.toWorld(cc, e, null, node), { x: 150, y: 60 });
  var first = scene.getComponentsInChildren()[0], w = first.screenToWorld(new cc.Vec3(50, 60, 0), new cc.Vec3());
  assert.notStrictEqual(w.x, 150, 'negative control: cams[0] (the 3D camera) gives the wrong point');
  var canvasCam = camera(7, 0, 1 << 25), canvas = new cc.Canvas(); canvas.cameraComponent = canvasCam;
  var root = { getComponent: function (K) { return K === cc.Canvas ? canvas : null; } };
  var child = { layer: 1 << 25, parent: root, getComponent: function () { return null; } };
  assert.strictEqual(Touch.cameraFor(cc, child), canvasCam);
  // claim with opts.camera reports info.world
  var n = emitter(), worlds = [];
  Touch.claim(cc, n, { onStart: function (ev2, i) { worlds.push(i.world); } }, { camera: uiCam });
  n.emit('touch-start', ev(0, 1, 2));
  assert.deepStrictEqual(worlds, [{ x: 101, y: 2 }]);
});

test('a handler that throws does not leave the control owned', function () {
  var cc = cc24(), node = emitter(), T = T24(cc), orig = console.error;
  console.error = function () {};
  try {
    var h = Touch.claim(cc, node, { onEnd: function () { throw new Error('game bug'); } });
    node.emit(T.TOUCH_START, ev(0, 1, 1)); node.emit(T.TOUCH_END, ev(0, 1, 1));
    assert.strictEqual(h.owner(), null);
  } finally { console.error = orig; }
});

var failed = results.filter(function (r) { return r[0] !== 'PASS'; });
results.forEach(function (r) { console.log(r[0] + ' ' + r[1]); });
console.log('\n' + (results.length - failed.length) + '/' + results.length + ' passed');
if (failed.length) process.exitCode = 1;
