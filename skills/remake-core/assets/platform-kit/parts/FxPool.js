/* Pool for short-lived nodes (effects, bullets, floating score text) for Cocos Creator 2.4 and 3.x (platform kit 2.0,
 * 生成时预防 P18). One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/FxPool.js) and
 *   var FxPool = require('FxPool');
 * 3.x: import it as a plugin script (it also sets the global TikTokFxPool).
 *
 * Why (问题普查 20261104, "卡顿" 30 times): 方块迷阵 left every merge particle in the scene (86 empty effects after 120
 * merges); 猫咪毛球 made a new Sprite node in update(); HazelsShelfScramble rebuilt the whole board each move. A node
 * made per effect and never removed makes every later frame slower. With this pool the number of nodes is fixed by
 * `max`, whatever the game does.
 *
 *   var pool = FxPool.create(cc, {
 *     parent: this.fxLayer,                                   // the node the effects sit in
 *     make: function () { return cc.instantiate(this.sparkPrefab); }.bind(this),   // only when no free node is left
 *     reset: function (node) { node.opacity = 255; node.scale = 1; },              // optional, before every reuse
 *     max: 32,                                                // hard cap: all busy -> the oldest is taken back
 *     life: 0.6                                               // seconds until it goes back by itself
 *   });
 *   var n = pool.spawn(x, y);                                 // play: the node is active at (x, y) in parent space
 *   pool.spawn(x, y, {life: 1.2, onDone: fn});                // own life; onDone when it goes back (also when taken back)
 *   pool.release(bullet);                                     // early return (a bullet hit something); safe twice
 *   update(dt) { pool.tick(d); }                              // d = session.tick(dt) from RunSession: paused = frozen
 *   pool.releaseAll();                                        // on newRun / leaving the level
 *   pool.destroy();                                           // onDestroy: destroys the pooled nodes
 * A returned node stays a child of parent with active = false (no add/remove churn). Tweens on it are stopped.
 * Particle systems: in reset call ps.resetSystem(); do not set autoRemoveOnFinish (that destroys a pooled node).
 * life: 0 = no auto return (bullets): release() yourself.
 *
 *   FxPool.devWatch(cc, opts)   development builds only (CC_DEBUG, or opts.force): warns when the game makes nodes
 *                               inside the frame update (2.4 `new cc.Node` / cc.instantiate between the director's
 *                               before-update and after-update events), and when the scene's node count keeps growing
 *                               (opts.samples, default 5 samples of opts.everyFrames = 120 frames in a row). Returns
 *                               {stop(), report()}. In release builds it does nothing.
 *
 * Proof: tests/fx-pool.test.js (120 spawns: the node count does not grow; negative control: the 方块迷阵 shape grows to 120).
 * 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokFxPool = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', DEFAULT_MAX = 32;

  function alive(cc, node) {
    if (!node) return false;
    if (cc && typeof cc.isValid === 'function') return cc.isValid(node, true);
    return node.isValid !== false;
  }
  function stopTweens(cc, node) {
    try { if (cc && cc.Tween && typeof cc.Tween.stopAllByTarget === 'function') cc.Tween.stopAllByTarget(node); } catch (e) { /* ok */ }
  }
  function place(node, x, y) {
    if (typeof x !== 'number' || typeof y !== 'number') return;
    if (typeof node.setPosition === 'function') node.setPosition(x, y);   // 3.x keeps z when only x, y are given
    else { node.x = x; node.y = y; }
  }

  function create(cc, opts) {
    opts = opts || {};
    if (typeof opts.make !== 'function') throw new Error('FxPool.create: opts.make must be a function that returns a node');
    if (!opts.parent) throw new Error('FxPool.create: opts.parent is required');
    var max = opts.max > 0 ? Math.floor(opts.max) : DEFAULT_MAX;
    var defaultLife = typeof opts.life === 'number' && opts.life >= 0 ? opts.life : 0;
    var warn = typeof opts.warn === 'function' ? opts.warn
      : function (m) { if (typeof console !== 'undefined') console.warn('[FxPool] ' + m); };
    var free = [], busy = [], all = [], made = 0, dead = false;

    function entryOf(node) { for (var i = 0; i < busy.length; i++) if (busy[i].node === node) return i; return -1; }
    function forget(node) { var i = all.indexOf(node); if (i >= 0) all.splice(i, 1); }
    function finish(index) {
      var e = busy.splice(index, 1)[0];
      stopTweens(cc, e.node);
      if (alive(cc, e.node)) { e.node.active = false; free.push(e.node); } else forget(e.node);
      if (typeof e.onDone === 'function') { try { e.onDone(e.node); } catch (err) { warn('onDone threw: ' + (err && err.message)); } }
    }
    function take() {
      while (free.length) { var n = free.pop(); if (alive(cc, n)) return n; forget(n); }
      // drop nodes someone else destroyed, then make one if under the cap
      for (var i = busy.length - 1; i >= 0; i--) if (!alive(cc, busy[i].node)) { forget(busy[i].node); busy.splice(i, 1); }
      if (all.length < max) {
        var node = opts.make();
        if (!node) throw new Error('FxPool: make() returned nothing');
        made += 1; all.push(node);
        if (node.parent !== opts.parent) opts.parent.addChild(node);
        return node;
      }
      finish(0);                                       // all busy at the cap: take back the oldest
      return free.pop();
    }

    var pool = {
      spawn: function (x, y, o) {
        if (dead) return null;
        o = o || {};
        var node = take();
        if (node.parent !== opts.parent) opts.parent.addChild(node);
        if (typeof opts.reset === 'function') opts.reset(node);
        place(node, x, y);
        node.active = true;
        var life = typeof o.life === 'number' && o.life >= 0 ? o.life : defaultLife;
        busy.push({ node: node, left: life, onDone: o.onDone });
        return node;
      },
      release: function (node) {
        var i = entryOf(node);
        if (i >= 0) finish(i);
        return i >= 0;
      },
      releaseAll: function () { while (busy.length) finish(0); },
      tick: function (dt) {
        var d = typeof dt === 'number' && isFinite(dt) && dt > 0 ? dt : 0;
        if (!d || dead) return;
        for (var i = busy.length - 1; i >= 0; i--) {
          var e = busy[i];
          if (!e.left) continue;                      // life 0: manual release only
          e.left -= d;
          if (e.left <= 1e-9) finish(i);
        }
      },
      destroy: function () {
        if (dead) return;
        pool.releaseAll(); dead = true;
        all.forEach(function (n) { try { if (alive(cc, n) && typeof n.destroy === 'function') n.destroy(); } catch (e) { /* ok */ } });
        all = []; free = [];
      },
      stats: function () { return { made: made, total: all.length, busy: busy.length, free: free.length, max: max }; }
    };
    return pool;
  }

  function isDev(opts) {
    if (opts && opts.force) return true;
    try { return typeof CC_DEBUG !== 'undefined' && !!CC_DEBUG; } catch (e) { return false; }   // eslint-disable-line no-undef
  }
  function countNodes(node) {
    if (!node) return 0;
    var n = 1, kids = node.children || [];
    for (var i = 0; i < kids.length; i++) n += countNodes(kids[i]);
    return n;
  }

  function devWatch(cc, opts) {
    opts = opts || {};
    var noop = { stop: function () {}, report: function () { return { active: false }; } };
    if (!isDev(opts) || !cc || !cc.director || typeof cc.director.on !== 'function') return noop;
    var warn = typeof opts.warn === 'function' ? opts.warn
      : function (m) { if (typeof console !== 'undefined') console.warn('[FxPool.devWatch] ' + m); };
    var D = cc.Director || {};
    var BEFORE = D.EVENT_BEFORE_UPDATE || 'director_before_update', AFTER = D.EVENT_AFTER_UPDATE || 'director_after_update';
    var everyFrames = opts.everyFrames > 0 ? opts.everyFrames : 120, samples = opts.samples > 0 ? opts.samples : 5;
    var inUpdate = false, madeInUpdate = 0, warnedMake = false, warnedGrowth = false, frame = 0, last = -1, rising = 0;
    var origNode = cc.Node, origInstantiate = cc.instantiate, patchedNode = false, patchedInst = false;

    function noteMake(what) {
      if (!inUpdate) return;
      madeInUpdate += 1;
      if (!warnedMake) { warnedMake = true; warn(what + ' inside update(): use FxPool (or make the nodes once in onLoad)'); }
    }
    // 2.4 game code reads cc.Node / cc.instantiate at call time; 3.x imports them, so there only the growth check works.
    if (typeof origNode === 'function' && typeof Proxy === 'function' && !cc.UITransform) {
      try {
        cc.Node = new Proxy(origNode, { construct: function (t, args, nt) { noteMake('new cc.Node'); return Reflect.construct(t, args, nt); } });
        patchedNode = true;
      } catch (e) { /* read-only */ }
    }
    if (typeof origInstantiate === 'function') {
      try {
        cc.instantiate = function () { noteMake('cc.instantiate'); return origInstantiate.apply(this, arguments); };
        patchedInst = true;
      } catch (e) { /* read-only */ }
    }
    function before() { inUpdate = true; }
    function after() {
      inUpdate = false;
      frame += 1;
      if (frame % everyFrames) return;
      var scene = cc.director.getScene ? cc.director.getScene() : null;
      var n = countNodes(scene);
      rising = last >= 0 && n > last ? rising + 1 : 0;
      last = n;
      if (rising >= samples && !warnedGrowth) {
        warnedGrowth = true;
        warn('scene node count grew for ' + samples + ' samples in a row (now ' + n + '): effects or bullets are not returned');
      }
    }
    cc.director.on(BEFORE, before);
    cc.director.on(AFTER, after);
    return {
      stop: function () {
        if (cc.director.off) { cc.director.off(BEFORE, before); cc.director.off(AFTER, after); }
        if (patchedNode) cc.Node = origNode;
        if (patchedInst) cc.instantiate = origInstantiate;
      },
      report: function () { return { active: true, madeInUpdate: madeInUpdate, growing: warnedGrowth, nodes: last }; }
    };
  }

  return { VERSION: VERSION, DEFAULT_MAX: DEFAULT_MAX, create: create, devWatch: devWatch };
});
