/* One run (一局) of a game: state, pause, timers and late callbacks, for Cocos Creator 2.4 and 3.x (platform kit 2.0,
 * 生成时预防 P11 + P18). One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/RunSession.js) and
 *   var RunSession = require('RunSession');
 * 3.x: import it as a plugin script (it also sets the global TikTokRunSession).
 *
 * Why (问题普查 20261104, 23 games had "state not reset on retry / next level"):
 *   割草: the run score and the saved total were one variable, RETRY kept the old score.
 *   Pinecone: the revive count lived across runs, the second run had no revive button.
 *   大西瓜之见缝插针: an old level's collision callback marked the new level as hit (IsHit), level 2 locked up;
 *     a setInterval was opened on every scene entry and never cleared.
 *   甜点消消乐 / 密室消除: closing the pause popup restored a stale "paused" boolean; Resume froze the board.
 *   谁也拦不住我: an async texture callback touched UI that was already destroyed.
 * Every one of these is the same shape: per-run data, timers and callbacks that outlive the run they belong to, and a
 * single pause flag shared by several reasons. This part makes the right shape the easy one.
 *
 *   var session = RunSession.create(cc, {owner: this.node});   // once, in the game scene's onLoad
 *   session.newRun(function () { return {score: 0, revives: 1, hit: false}; });  // start AND every retry / next level
 *   session.state.score += 10;                                 // all per-run data lives in session.state only
 *   update(dt) { var d = session.tick(dt); if (!d) return; session.move(this.hero, 300, 0, d); }
 *   session.every(1000, function () { session.state.time -= 1; });   // instead of setInterval / this.schedule
 *   session.after(500, fn);                                    // instead of setTimeout / scheduleOnce
 *   collider.onHit = session.guard(function () { session.state.hit = true; });  // dropped after newRun
 *   var release = session.pause('popup');  ...  release();     // pause by reason; release() is safe to call twice
 *   onDestroy() { session.dispose(); }
 *
 * API
 *   RunSession.create(cc, opts)  opts: {owner (node: guarded callbacks are dropped once it is destroyed),
 *                                 autoHide (default true: cc.game EVENT_HIDE -> pause('hide'), EVENT_SHOW -> resume('hide')),
 *                                 sceneBound (default true: a scene launch disposes the session's timers and callbacks),
 *                                 maxDt (default 0.1 s: one frame never moves more than this, e.g. after a long hitch),
 *                                 onPause(reasons), onResume() (called on the paused/running edge only), warn(msg)}
 *   session.newRun(init)         new run: run id + 1, every timer and guarded callback of the old run is dropped, and
 *                                session.state = init() (a fresh object every time; init gets {run} and may return
 *                                nothing to use that object). Pause reasons are NOT cleared: they belong to the screen
 *                                (a popup that is still open, an ad still playing, the app in the background).
 *   session.state / session.run  the current run's data / its id (1, 2, ...)
 *   session.guard(fn, ctx)       fn wrapped so it only runs while its run is current, the session is alive and the owner
 *                                node is valid; otherwise it returns undefined and does nothing (for collision callbacks,
 *                                tween ends, load callbacks, ad results, network replies)
 *   session.once(fn, ctx)        guard + only the first call runs (double taps, a callback the SDK fires twice)
 *   session.after(ms, fn)        one-shot timer;  session.every(ms, fn) repeating timer;  session.timer(fn, ms, repeat)
 *                                Timers advance in session.tick only while not paused, and die with newRun / dispose /
 *                                a scene launch. Each returns {cancel()}.
 *   session.tick(dt)             call once per frame from the game's update(dt); returns the dt to use (0 when paused,
 *                                at most maxDt) and runs due timers. Nothing in the run should move without it.
 *   session.pause(reason)        +1 for that reason (default 'game'); returns release(), which undoes exactly this one
 *   session.resume(reason)       -1 for that reason (never below 0; an unknown reason is ignored)
 *   session.isPaused()           true while any reason is held;  session.reasons() -> ['ad', 'popup', ...]
 *   session.resumeAll()          drop every reason except 'hide' (only for "quit to home")
 *   session.adHooks()            {pauseGame, resumeGame} for ad-boost AdBoostKit.setup / runAd: reason 'ad', each
 *                                pauseGame is matched by one resumeGame
 *   session.move(node, vx, vy, dt)   node position += (vx, vy) * dt (units per SECOND), 2.4 and 3.x
 *   RunSession.step(value, perSecond, dt)   value + perSecond * dt  (for angles, scales, scroll offsets)
 *   session.dispose()            drop everything, stop listening (onDestroy of the scene's main component)
 *
 * English (英化) games keep the original gameplay code; use this only in the pause / revive / ad entries the AI adds.
 * Proof: tests/run-session.test.js (with a single-boolean pause, a stale-callback and a setInterval negative control).
 * 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokRunSession = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', MAX_DT = 0.1, HIDE = 'hide';

  function isValid(cc, node) {
    if (!node) return true;
    if (cc && typeof cc.isValid === 'function') return cc.isValid(node, true);
    return node.isValid !== false;
  }
  function hideEvents(cc) {
    var g = cc && cc.game, G = cc && cc.Game;
    return {
      hide: (g && g.EVENT_HIDE) || (G && G.EVENT_HIDE) || 'game_on_hide',
      show: (g && g.EVENT_SHOW) || (G && G.EVENT_SHOW) || 'game_on_show'
    };
  }
  function sceneLaunchEvent(cc) {
    var D = cc && cc.Director;
    return (D && (D.EVENT_BEFORE_SCENE_LAUNCH || D.EVENT_BEFORE_SCENE_LOADING)) || null;
  }

  function create(cc, opts) {
    opts = opts || {};
    var maxDt = typeof opts.maxDt === 'number' && opts.maxDt > 0 ? opts.maxDt : MAX_DT;
    var warn = typeof opts.warn === 'function' ? opts.warn
      : function (m) { if (typeof console !== 'undefined') console.warn('[RunSession] ' + m); };
    var counts = {}, timers = [], alive = true, epoch = 0, nextTimerId = 1;
    var listeners = [];
    var s = { VERSION: VERSION, state: null, run: 0 };

    function held() { for (var k in counts) if (counts[k] > 0) return true; return false; }
    function edge(was) {
      var now = held();
      if (was === now) return;
      try {
        if (now && typeof opts.onPause === 'function') opts.onPause(s.reasons());
        if (!now && typeof opts.onResume === 'function') opts.onResume();
      } catch (e) { warn('onPause/onResume threw: ' + (e && e.message)); }
    }
    function dropTimers() { for (var i = 0; i < timers.length; i++) timers[i].dead = true; timers = []; }
    // epoch changes on newRun, dispose and a scene launch: everything bound to the old epoch is dropped.
    function bump() { epoch += 1; dropTimers(); }

    s.newRun = function (init) {
      if (!alive) { warn('newRun after dispose'); return null; }
      bump();
      s.run += 1;
      var fresh = { run: s.run };
      var out = typeof init === 'function' ? init(fresh) : null;
      s.state = out && typeof out === 'object' ? out : fresh;
      return s.state;
    };

    function current(myEpoch) { return alive && myEpoch === epoch && isValid(cc, opts.owner); }
    s.guard = function (fn, ctx) {
      if (typeof fn !== 'function') throw new Error('RunSession.guard: fn is not a function');
      var mine = epoch;
      return function () { if (!current(mine)) return undefined; return fn.apply(ctx || this, arguments); };
    };
    s.once = function (fn, ctx) {
      if (typeof fn !== 'function') throw new Error('RunSession.once: fn is not a function');
      var mine = epoch, used = false;
      return function () {
        if (used || !current(mine)) return undefined;
        used = true;
        return fn.apply(ctx || this, arguments);
      };
    };

    s.timer = function (fn, ms, repeat) {
      if (typeof fn !== 'function') throw new Error('RunSession.timer: fn is not a function');
      var sec = Math.max(0, (Number(ms) || 0) / 1000);
      if (repeat && sec <= 0) throw new Error('RunSession.every: interval must be > 0 ms');
      var t = { id: nextTimerId++, fn: fn, left: sec, every: repeat ? sec : 0, dead: !alive };
      if (alive) timers.push(t);
      return { cancel: function () { t.dead = true; } };
    };
    s.after = function (ms, fn) { return s.timer(fn, ms, false); };
    s.every = function (ms, fn) { return s.timer(fn, ms, true); };

    s.tick = function (dt) {
      if (!alive) return 0;
      if (held()) return 0;
      var d = typeof dt === 'number' && isFinite(dt) && dt > 0 ? Math.min(dt, maxDt) : 0;
      if (!d || !timers.length) return d;
      var mine = epoch, list = timers.slice();
      for (var i = 0; i < list.length; i++) {
        var t = list[i];
        if (t.dead) continue;
        t.left -= d;
        // a repeating timer fires at most once per frame (a long frame does not replay missed ticks in one go)
        if (t.left <= 1e-9) {
          if (t.every) t.left += t.every; if (t.every && t.left <= 0) t.left = t.every;
          if (!t.every) t.dead = true;
          try { t.fn(); } catch (e) { warn('timer threw: ' + (e && e.message)); }
          if (mine !== epoch || !alive || held()) break;   // the callback started a new run or paused
        }
      }
      timers = timers.filter(function (t) { return !t.dead; });
      return d;
    };

    s.pause = function (reason) {
      var r = reason ? String(reason) : 'game', was = held(), done = false;
      counts[r] = (counts[r] || 0) + 1;
      edge(was);
      return function release() { if (done) return; done = true; s.resume(r); };
    };
    s.resume = function (reason) {
      var r = reason ? String(reason) : 'game';
      if (!counts[r]) return;
      var was = held();
      counts[r] -= 1;
      if (!counts[r]) delete counts[r];
      edge(was);
    };
    s.isPaused = function () { return held(); };
    s.reasons = function () { var out = []; for (var k in counts) if (counts[k] > 0) out.push(k); return out.sort(); };
    s.resumeAll = function () {
      var was = held();
      for (var k in counts) if (k !== HIDE) delete counts[k];
      edge(was);
    };
    s.adHooks = function () {
      var releases = [];
      return {
        pauseGame: function () { releases.push(s.pause('ad')); },
        resumeGame: function () { var r = releases.shift(); if (r) r(); }
      };
    };

    s.move = function (node, vx, vy, dt) {
      if (!node) return;
      var d = typeof dt === 'number' && isFinite(dt) && dt > 0 ? dt : 0;
      if (!d) return;
      var dx = (Number(vx) || 0) * d, dy = (Number(vy) || 0) * d;
      if (cc && cc.UITransform) {                                 // 3.x: node.position is a read-only Vec3
        var p = node.position;
        node.setPosition(p.x + dx, p.y + dy, p.z || 0);
      } else {
        node.x += dx; node.y += dy;
      }
    };

    s.dispose = function () {
      if (!alive) return;
      bump();
      alive = false;
      for (var i = 0; i < listeners.length; i++) {
        var L = listeners[i];
        try { L.target.off(L.event, L.fn); } catch (e) { /* engine already torn down */ }
      }
      listeners = [];
    };

    function listen(target, event, fn) {
      if (!target || !event || typeof target.on !== 'function') return;
      target.on(event, fn);
      listeners.push({ target: target, event: event, fn: fn });
    }
    if (opts.autoHide !== false && cc && cc.game) {
      var ev = hideEvents(cc);
      listen(cc.game, ev.hide, function () { if (!counts[HIDE]) s.pause(HIDE); });
      listen(cc.game, ev.show, function () { while (counts[HIDE]) s.resume(HIDE); });
    }
    if (opts.sceneBound !== false && cc && cc.director) {
      var launch = sceneLaunchEvent(cc);
      if (launch) listen(cc.director, launch, function () { s.dispose(); });
    }
    return s;
  }

  function step(value, perSecond, dt) {
    var d = typeof dt === 'number' && isFinite(dt) && dt > 0 ? dt : 0;
    return (Number(value) || 0) + (Number(perSecond) || 0) * d;
  }

  return { VERSION: VERSION, MAX_DT: MAX_DT, create: create, step: step };
});
