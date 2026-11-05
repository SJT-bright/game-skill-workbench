/* One finger per control, one swipe rule, camera-correct touch points, for Cocos Creator 2.4 and 3.x
 * (platform kit 2.0, v7.9, 生成时预防 P13). One file for both engines. 2.4: copy it into assets/ (e.g.
 * assets/tiktok-platform/TouchOwner.js) and
 *   var Touch = require('TouchOwner');
 * 3.x: import it as a plugin script (it also sets the global TikTokTouchOwner).
 *
 * Why (问题普查 2026-11-04, 点击失效 152 次 / 83 个游戏): a joystick or drag that did not remember which finger pressed
 * it was taken over by a second finger (我出枪贼快, TooLit 双指误触, SockDrawerShowdown 多指误落子, 蚂蚁隧道 主指归属);
 * a control that kept "touching = true" until touchend never released when the end did not come (甜点消消乐 R47: the
 * first tap after returning was lost); touch points were turned into world points by hand and missed after the game
 * moved its camera (SockDrawerShowdown long-screen camera, 激光宝库, SorensRivet); swipe code dropped pure horizontal or
 * pure vertical swipes (立方体数字, 懒猫跑酷).
 *
 *   Touch.claim(cc, node, {onStart, onMove, onEnd}, opts)
 *        only the finger that pressed first owns the control until it lifts (touchend) or is cancelled (touchcancel,
 *        or cc.game EVENT_HIDE). Other fingers never reach the handlers. No time limit: a 6 s hold still drags.
 *        A touchstart with the owner's own id (its end never came) ends the old touch as cancelled and starts again.
 *        Handlers get (event, info): info {id, start, pos, prev, delta, total: {x, y}, startedAt, duration, cancelled,
 *        world (only with opts.world: true or opts.camera)}. pos / start are UI points (3.x getUILocation, 2.4
 *        getLocation). Returns {owner(), release(), off()}.
 *        opts: {camera, world, stopPropagation, now}.
 *   Touch.swipe(cc, node, {minDist, onSwipe(dir, info), onTap(info), early}, opts)
 *        claim() + direction(): 'left' | 'right' | 'up' | 'down' on touchend (early: true -> as soon as the finger
 *        has moved minDist, once per touch). Shorter than minDist (default 40) -> onTap. Cancelled -> nothing.
 *   Touch.direction(dx, dy, minDist)   the one rule: longer axis wins, ties go horizontal, y up. null below minDist.
 *   Touch.cameraFor(cc, node)          2.4 cc.Camera.findCamera(node); 3.x the Canvas cameraComponent above the node,
 *                                      else the camera whose visibility has the node's layer with the highest priority
 *                                      (never simply the first camera in the scene)
 *   Touch.toWorld(cc, event, camera, node)   world point of the touch through that camera (camera null -> cameraFor(node))
 *   Touch.toLocal(cc, event, node, camera)   the same point in node space
 *   Touch.hit(cc, event, node, camera)       true when the point is inside node's own rect (for "release inside to act")
 *
 * Works with the platform kit touch parts, does not replace them: touch-coordinates.js (2.4) / tiktok-touch-3x.js (3.x)
 * still fix the coordinates and send TOUCH_CANCEL for fingers held when TikTok takes the game away; claim() releases
 * on that cancel (and on EVENT_HIDE itself when the kit part is missing), and a second cancel for the same finger is
 * ignored, so onEnd runs once.
 * Proof: tests/touch-owner.test.js (two fingers, touchcancel, kit cancel on return, stale same id, 6 s hold, four
 * swipe directions, moved camera; negative controls: last-touch-wins joystick, touching flag, both-axis swipe threshold,
 * hand-made world point, first camera in the scene). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokTouchOwner = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', MIN_DIST = 40;

  function v3(cc) { return !!(cc && cc.UITransform); }
  function o(x) { return x || {}; }
  function fin(v) { return typeof v === 'number' && isFinite(v); }

  function types(cc) {
    var T = cc && cc.Node && cc.Node.EventType;
    if (T && T.TOUCH_START) return { start: T.TOUCH_START, move: T.TOUCH_MOVE, end: T.TOUCH_END, cancel: T.TOUCH_CANCEL };
    return v3(cc) ? { start: 'touch-start', move: 'touch-move', end: 'touch-end', cancel: 'touch-cancel' }
      : { start: 'touchstart', move: 'touchmove', end: 'touchend', cancel: 'touchcancel' };
  }
  function idOf(e) {
    try {
      if (e && typeof e.getID === 'function') { var a = e.getID(); if (a != null) return a; }
      var t = e && e.touch;
      if (t && typeof t.getID === 'function') { var b = t.getID(); if (b != null) return b; }
      if (t && t._id != null) return t._id;
    } catch (err) {}
    return 0;
  }
  function pt(p) { return p ? { x: p.x, y: p.y } : { x: NaN, y: NaN }; }
  function uiPoint(e) {
    if (e && typeof e.getUILocation === 'function') return pt(e.getUILocation());
    if (e && typeof e.getLocation === 'function') return pt(e.getLocation());
    return pt(e && e.touch && e.touch.getLocation ? e.touch.getLocation() : null);
  }
  function nowFn(opts) { return typeof opts.now === 'function' ? opts.now : function () { return Date.now(); }; }

  // ---- cameras and points ----
  function cameraFor(cc, node) {
    if (!node) return null;
    if (!v3(cc)) return cc.Camera && typeof cc.Camera.findCamera === 'function' ? cc.Camera.findCamera(node) : null;
    for (var n = node; n; n = n.parent) {
      var cv = cc.Canvas && n.getComponent ? n.getComponent(cc.Canvas) : null;
      if (cv && cv.cameraComponent) return cv.cameraComponent;
    }
    var scene = cc.director && typeof cc.director.getScene === 'function' ? cc.director.getScene() : null;
    var cams = scene && typeof scene.getComponentsInChildren === 'function' && cc.Camera ? scene.getComponentsInChildren(cc.Camera) : [];
    var layer = node.layer, best = null;
    (cams || []).forEach(function (c) {
      if (!c || c.enabledInHierarchy === false) return;
      if (fin(layer) && fin(c.visibility) && !(c.visibility & layer)) return;
      if (!best || (c.priority || 0) > (best.priority || 0)) best = c;
    });
    return best;
  }

  function toWorld(cc, event, camera, node) {
    var cam = camera || cameraFor(cc, node);
    if (v3(cc)) {
      if (cam && typeof cam.screenToWorld === 'function' && event && typeof event.getLocation === 'function') {
        var s = event.getLocation(), out = cc.Vec3 ? new cc.Vec3(0, 0, 0) : { x: 0, y: 0, z: 0 };
        var r = cam.screenToWorld(cc.Vec3 ? new cc.Vec3(s.x, s.y, 0) : { x: s.x, y: s.y, z: 0 }, out) || out;
        return { x: r.x, y: r.y };
      }
      return uiPoint(event);
    }
    var loc = event && typeof event.getLocation === 'function' ? event.getLocation() : uiPoint(event);
    if (cam && typeof cam.getScreenToWorldPoint === 'function') { var w = cam.getScreenToWorldPoint(loc); return { x: w.x, y: w.y }; }
    return pt(loc);
  }

  function toLocal(cc, event, node, camera) {
    var w = toWorld(cc, event, camera, node);
    if (v3(cc)) {
      var t = node.getComponent(cc.UITransform);
      var q = t.convertToNodeSpaceAR(cc.Vec3 ? new cc.Vec3(w.x, w.y, 0) : { x: w.x, y: w.y, z: 0 });
      return { x: q.x, y: q.y };
    }
    var r = node.convertToNodeSpaceAR(cc.v2 ? cc.v2(w.x, w.y) : { x: w.x, y: w.y });
    return { x: r.x, y: r.y };
  }

  function hit(cc, event, node, camera) {
    var p = toLocal(cc, event, node, camera), t = v3(cc) ? node.getComponent(cc.UITransform) : node;
    var w = t.width, h = t.height, ax = fin(t.anchorX) ? t.anchorX : 0.5, ay = fin(t.anchorY) ? t.anchorY : 0.5;
    return p.x >= -ax * w && p.x <= (1 - ax) * w && p.y >= -ay * h && p.y <= (1 - ay) * h;
  }

  // ---- ownership ----
  function claim(cc, node, handlers, opts) {
    handlers = o(handlers); opts = o(opts);
    if (!node || typeof node.on !== 'function') throw new Error('TouchOwner.claim: node with on/off is required');
    var T = types(cc), now = nowFn(opts), cur = null;
    var wantWorld = !!(opts.world || opts.camera);

    function info(e, ended, cancelled) {
      var p = e ? uiPoint(e) : cur.pos, prev = cur.pos;
      cur.prev = prev; cur.pos = p;
      var i = { id: cur.id, start: cur.start, pos: p, prev: prev, delta: { x: p.x - prev.x, y: p.y - prev.y },
        total: { x: p.x - cur.start.x, y: p.y - cur.start.y }, startedAt: cur.startedAt, duration: now() - cur.startedAt,
        cancelled: !!cancelled, ended: !!ended };
      if (wantWorld && e) i.world = toWorld(cc, e, opts.camera, node);
      return i;
    }
    function call(fn, e, i) {
      if (typeof fn !== 'function') return;
      try { fn(e, i); } catch (err) { try { console.error('[TouchOwner] handler threw', err); } catch (_) {} }
    }
    function finish(e, cancelled) {
      if (!cur) return;
      var i = info(e, true, cancelled); cur = null;
      call(handlers.onEnd, e, i);
    }
    function onStart(e) {
      var id = idOf(e);
      if (cur && cur.id !== id) return;                 // another finger owns this control
      if (cur) finish(null, true);                      // same id again: its end never came
      var p = uiPoint(e);
      cur = { id: id, start: p, pos: p, prev: p, startedAt: now() };
      if (opts.stopPropagation && e && e.stopPropagation) e.stopPropagation();
      var i = info(e, false, false); call(handlers.onStart, e, i);
    }
    function onMove(e) {
      if (!cur || idOf(e) !== cur.id) return;
      if (opts.stopPropagation && e && e.stopPropagation) e.stopPropagation();
      call(handlers.onMove, e, info(e, false, false));
    }
    function onEnd(e) { if (cur && idOf(e) === cur.id) finish(e, false); }
    function onCancel(e) { if (cur && idOf(e) === cur.id) finish(e, true); }
    function onHide() { if (cur) finish(null, true); }

    node.on(T.start, onStart); node.on(T.move, onMove); node.on(T.end, onEnd); node.on(T.cancel, onCancel);
    var game = cc.game, HIDE = game && (game.EVENT_HIDE || 'game_on_hide');
    if (game && typeof game.on === 'function') game.on(HIDE, onHide);
    return {
      owner: function () { return cur ? cur.id : null; },
      release: function () { finish(null, true); },
      off: function () {
        cur = null;
        if (typeof node.off === 'function') { node.off(T.start, onStart); node.off(T.move, onMove); node.off(T.end, onEnd); node.off(T.cancel, onCancel); }
        if (game && typeof game.off === 'function') game.off(HIDE, onHide);
      }
    };
  }

  function direction(dx, dy, minDist) {
    var m = fin(minDist) && minDist > 0 ? minDist : MIN_DIST;
    if (!fin(dx) || !fin(dy)) return null;
    var ax = Math.abs(dx), ay = Math.abs(dy);
    if (Math.max(ax, ay) < m) return null;
    if (ax >= ay) return dx > 0 ? 'right' : 'left';
    return dy > 0 ? 'up' : 'down';
  }

  function swipe(cc, node, s, opts) {
    s = o(s);
    var m = fin(s.minDist) && s.minDist > 0 ? s.minDist : MIN_DIST, fired = false;
    return claim(cc, node, {
      onStart: function () { fired = false; },
      onMove: function (e, i) {
        if (!s.early || fired) return;
        var d = direction(i.total.x, i.total.y, m);
        if (d) { fired = true; if (typeof s.onSwipe === 'function') s.onSwipe(d, i); }
      },
      onEnd: function (e, i) {
        if (i.cancelled || fired) return;
        var d = direction(i.total.x, i.total.y, m);
        if (d) { if (typeof s.onSwipe === 'function') s.onSwipe(d, i); }
        else if (typeof s.onTap === 'function') s.onTap(i);
      }
    }, opts);
  }

  return { VERSION: VERSION, MIN_DIST: MIN_DIST, claim: claim, swipe: swipe, direction: direction,
    cameraFor: cameraFor, toWorld: toWorld, toLocal: toLocal, hit: hit, eventTypes: types };
});
