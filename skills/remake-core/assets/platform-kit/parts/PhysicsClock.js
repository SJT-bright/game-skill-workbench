/* Physics clock for Cocos Creator 2.4 (platform kit 2.0, v7.8, 总表 P16).
 * Installed by `tiktok_finalize.py source` (step physics_clock) as assets/tiktok-platform/PhysicsClock.js, only for a NEW
 * game whose scripts switch 2.4 physics on and do not set enabledAccumulator themselves. Legacy games are never given it
 * (their feel was tuned and tested the old way). Cocos 3.x physics already steps on a fixed clock: not used there.
 *
 * Why: without enabledAccumulator the 2.4 PhysicsManager steps 1/60 s on EVERY frame. On a 120 Hz screen (Saul's Mac, the
 * test browser) the whole physics world runs twice as fast; a push applied once per frame (or by a 0.01 s schedule, which
 * fires at most once per frame) also changes with the screen. 全民飞车漂移 v3.1 (pysTouchEvent.ts:91,
 * schedule(run_time, 0.01), applyForceToCenter 65 per call, RunUI.ts:145 enabled = true only): at 1 s after the start the
 * car is 19.9 % farther on a 120 Hz screen; Pizza Drift (same base) fell off at the first corner of levels 1-5.
 *
 * What it does: at load (every 2.4 script runs when the game starts) and before every scene launch it sets
 *   cc.director.getPhysicsManager().enabledAccumulator = true
 * so physics steps a fixed 1/60 s as many times as REAL time needs (0 or 1 step per frame at 120 Hz, 1 at 60 Hz).
 * The pushes are the game's code; scale each per-call push by the time it covers:
 *   var Clock = require('PhysicsClock');
 *   body.applyForceToCenter(Clock.force(cc.v2(fx, fy), dt), true);   // a force tuned at 60 fps, per call
 *   body.applyTorque(Clock.scale(dt) * 10, true);
 *   node.x += speed * dt;                                             // movement: always per second x dt
 * dt = the callback's own dt (update(dt), schedule(cb, interval) passes the elapsed time). A schedule interval below 1/60
 * runs at most once per frame: use update(dt) or an interval >= 1/60.
 *   Clock.install(cc)    set the accumulator now; true when it is on (called for you at load and per scene)
 *   Clock.scale(dt)      dt * 60 (1 at 60 fps, 0.5 per frame at 120 fps); no dt = 1
 *   Clock.force(v, dt)   cc.v2(v.x * scale, v.y * scale)
 *   Clock.FIXED_STEP     1/60
 * The final judge is the runtime suite frame_rate (cocos-game-check): the same operation at 60 Hz and 120 Hz, positions
 * at the same real time within 5 %. Proof: tests/physics-clock.test.js; DriftRacer3D v3.1 with the accumulator on and
 * every push in run_time scaled like Clock.force passes frame_rate (1.05 %), as shipped it fails (19.9 %)
 * (briefs/out/W92/RESULT.md). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokPhysicsClock = api;
  var engine = root && root.cc;
  if (engine) api.autoInstall(engine);
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', FIXED_STEP = 1 / 60;

  function manager(cc) {
    try { return cc && cc.director && cc.director.getPhysicsManager ? cc.director.getPhysicsManager() : null; } catch (e) { return null; }
  }
  function install(cc) {
    var pm = manager(cc);
    if (!pm) return false;
    pm.enabledAccumulator = true;
    return pm.enabledAccumulator === true;
  }
  function scale(dt) {
    return typeof dt === 'number' && dt > 0 && isFinite(dt) ? dt / FIXED_STEP : 1;
  }
  function force(v, dt, cc) {
    var k = scale(dt), lib = cc || (typeof globalThis !== 'undefined' && globalThis.cc);
    var x = (v && v.x) || 0, y = (v && v.y) || 0;
    return lib && lib.v2 ? lib.v2(x * k, y * k) : { x: x * k, y: y * k };
  }
  var hooked = false;
  function autoInstall(cc) {
    var on = install(cc);
    if (!hooked && cc && cc.director && cc.director.on && cc.Director && cc.Director.EVENT_BEFORE_SCENE_LAUNCH) {
      cc.director.on(cc.Director.EVENT_BEFORE_SCENE_LAUNCH, function () { install(cc); });
      hooked = true;
    }
    if (!on && cc && cc.game && cc.game.once && cc.game.EVENT_GAME_INITED) cc.game.once(cc.game.EVENT_GAME_INITED, function () { install(cc); });
    return on;
  }
  return { VERSION: VERSION, FIXED_STEP: FIXED_STEP, install: install, scale: scale, force: force, autoInstall: autoInstall };
});
