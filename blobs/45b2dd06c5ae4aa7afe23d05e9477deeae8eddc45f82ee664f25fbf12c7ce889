'use strict';
// node tests/physics-clock.test.js  -- parts/PhysicsClock.js (v7.8, 总表 P16): the 2.4 accumulator goes on at load and
// before every scene launch, and pushes scaled by Clock.scale(dt) move a body the same distance per REAL second at
// 60 Hz and 120 Hz. Fake engine: a 2.4-like PhysicsManager (no accumulator: one 1/60 s step per frame; accumulator:
// fixed 1/60 s steps as real time needs) and a body whose forces stay until the next step (Box2D clears them after a
// step). Negative controls: the DriftRacer3D v3.1 shape (push per call, no accumulator) and "accumulator only" (pushes not
// scaled) both differ by far more than 5 %.
var assert = require('assert');
var path = require('path');
var FILE = path.join(__dirname, '..', 'parts', 'PhysicsClock.js');

function fakeCc() {
  var handlers = {}, once = {};
  var pm = { enabled: false, enabledAccumulator: false };
  return {
    pm: pm,
    v2: function (x, y) { return { x: x, y: y }; },
    Director: { EVENT_BEFORE_SCENE_LAUNCH: 'before-launch' },
    director: { getPhysicsManager: function () { return pm; },
      on: function (e, f) { (handlers[e] = handlers[e] || []).push(f); } },
    game: { EVENT_GAME_INITED: 'inited', once: function (e, f) { (once[e] = once[e] || []).push(f); } },
    emit: function (e) { (handlers[e] || []).forEach(function (f) { f(); }); (once[e] || []).splice(0).forEach(function (f) { f(); }); }
  };
}
function load(cc) {
  delete require.cache[require.resolve(FILE)];
  global.cc = cc;
  try { return require(FILE); } finally { delete global.cc; }
}

// 1. at load the accumulator goes on; a scene launch puts it back on if something turned it off
var cc = fakeCc();
var Clock = load(cc);
assert.strictEqual(cc.pm.enabledAccumulator, true, 'enabledAccumulator on at load');
cc.pm.enabledAccumulator = false;
cc.emit('before-launch');
assert.strictEqual(cc.pm.enabledAccumulator, true, 'on again before a scene launch');
assert.strictEqual(Clock.FIXED_STEP, 1 / 60);
assert.strictEqual(Clock.scale(1 / 60), 1);
assert.ok(Math.abs(Clock.scale(1 / 120) - 0.5) < 1e-12);
assert.strictEqual(Clock.scale(undefined), 1);
assert.strictEqual(Clock.scale(-1), 1);
assert.deepStrictEqual(Clock.force({ x: 2, y: -4 }, 1 / 120, cc), { x: 1, y: -2 });

// 2. no physics manager yet: installs when the game is initialised
var late = fakeCc();
var pmLate = late.pm;
late.director.getPhysicsManager = function () { return null; };
load(late);
late.director.getPhysicsManager = function () { return pmLate; };
late.emit('inited');
assert.strictEqual(pmLate.enabledAccumulator, true, 'installed at EVENT_GAME_INITED');

// 3. distance per real second, 60 Hz vs 120 Hz (2.4 PhysicsManager.update shape)
function simulate(hz, opt) {
  var pm = { enabledAccumulator: false, acc: 0 }, STEP = 1 / 60, F = 65, body = { v: 0, x: 0, f: 0 };
  if (opt.clock) Clock.install({ director: { getPhysicsManager: function () { return pm; } } });
  function step(h) { body.v = (body.v + body.f * h) * Math.pow(0.97, h * 60); body.x += body.v * h; body.f = 0; }
  var dt = 1 / hz, frames = Math.round(2 * hz);
  for (var i = 0; i < frames; i++) {
    body.f += F * (opt.scaled ? Clock.scale(dt) : 1);          // the game's push, once per frame
    if (pm.enabledAccumulator) { pm.acc += dt; while (pm.acc >= STEP - 1e-9) { step(STEP); pm.acc -= STEP; } }
    else step(STEP);                                          // 2.4 without accumulator: 1/60 s every frame
  }
  return body.x;
}
function rel(a, b) { return Math.abs(a - b) / Math.max(a, b); }
var fixed = rel(simulate(60, { clock: true, scaled: true }), simulate(120, { clock: true, scaled: true }));
var broken = rel(simulate(60, {}), simulate(120, {}));
var accumulatorOnly = rel(simulate(60, { clock: true }), simulate(120, { clock: true }));
assert.ok(fixed <= 0.01, 'accumulator + scaled pushes: same distance (' + fixed + ')');
assert.ok(broken > 0.3, 'negative control, DriftRacer3D v3.1 shape: must differ (' + broken + ')');
assert.ok(accumulatorOnly > 0.3, 'negative control, accumulator without scaled pushes: must differ (' + accumulatorOnly + ')');

// 4. the module carries no game names and one wiring line only
var text = require('fs').readFileSync(FILE, 'utf8');
var code = text.replace(/\/\*[\s\S]*?\*\//g, '');
['RunUI', 'pysTouchEvent', 'carBody'].forEach(function (n) { assert.ok(code.indexOf(n) < 0, n); });
assert.strictEqual((code.match(/enabledAccumulator = true/g) || []).length, 1);
console.log('physics-clock: 4 groups passed (fixed ' + (fixed * 100).toFixed(2) + ' %, v3.1 shape ' + (broken * 100).toFixed(1) +
            ' %, accumulator only ' + (accumulatorOnly * 100).toFixed(1) + ' %)');
