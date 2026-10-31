/* Scrolling-course lanes for Cocos Creator 2.4 and 3.x (platform kit 2.0, v7.8, 总表 P2 补).
 * One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/CourseLane.js) and
 *   var Lane = require('CourseLane');
 * 3.x: import it as a plugin script (it also sets the global TikTokCourseLane).
 *
 * Why: BreezyBalloon v2.1 (潜艇冲冲 base) recycled pillars at a design-width position (x 816 of a 750 design). On a wide
 * screen (768x1024, 1115x791) the real visible width is 1000..1880, so recycled pillars jumped into the middle of the
 * screen 39 times in 18 s, and the revive moved visible pillars 796 to the right in one frame. Every number here comes
 * from the engine's REAL visible rect (cc.view visible size / origin, or the camera that draws the course), never from
 * the design width, so wide screens and letterbox bars are right.
 *
 *   Lane.visibleRect(cc, opts)          {left, right, bottom, top, width, height} of what the player sees, in world
 *                                       coordinates, or in opts.space (the node the obstacles sit in) when given
 *   Lane.spawnX(cc, opts)               x for a new obstacle: right edge + opts.halfWidth + margin (>= 100), and at least
 *                                       opts.lastX + opts.gap (the spacing after the last obstacle)
 *   Lane.recycleX(cc, opts)             an obstacle with x < recycleX has fully left the left edge (x + halfWidth < left)
 *   Lane.isGone(cc, x, opts)            x < recycleX(cc, opts)
 *   Lane.lanesNeeded(cc, opts)          obstacle groups to keep alive (opts.gap apart) so a recycled group always lands
 *                                       beyond the right edge; wider screen = more groups. opts.screens: course length
 *                                       to fill at the start (3 = generate 3 screen widths ahead in one go)
 *   Lane.clearForRevive(cc, items, opts) split obstacles for a revive: {offscreen, fade, keep}. offscreen may be moved
 *                                       freely; fade = visible and in the danger zone in front of the player (from the
 *                                       left edge to opts.playerX + opts.clearAhead, default 300): fade them out
 *                                       (>= 0.3 s) before moving; keep = visible and farther ahead: do not touch.
 *                                       opts.apply: run the fades (cc.tween) and call opts.onFaded(item) when each is done
 *   Lane.fadeOut(cc, nodes, seconds, done)   opacity to 0 over max(seconds, 0.3) s (2.4 node.opacity, 3.x UIOpacity)
 * opts: {halfWidth, margin, space, camera, lastX, gap, screens, playerX, clearAhead, fadeSeconds, apply, onFaded}.
 * An item for clearForRevive: {node} or {nodes: [...]} (all faded together), with optional x (world x of its centre,
 * default: the first node's world x) and halfWidth (default: half the first node's world width).
 * The runtime suite popin (cocos-game-check, written into every package) refuses the bug itself, whatever the fix.
 * Proof: tests/course-lane.test.js, and BreezyBalloon v2.1 with its recycle and revive replaced by this file at runtime
 * passes popin on all four screens (briefs/out/W89/RESULT.md). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokCourseLane = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', MIN_MARGIN = 100, MIN_FADE = 0.3, CLEAR_AHEAD = 300;

  function v3(cc) { return !!(cc && cc.UITransform); }
  function o(opts) { return opts || {}; }

  // World point of a node's anchor.
  function worldOf(cc, node) {
    if (v3(cc)) { var p = node.worldPosition; return { x: p.x, y: p.y }; }
    var w = node.convertToWorldSpaceAR(cc.v2(0, 0)); return { x: w.x, y: w.y };
  }
  function toSpace(cc, space, x, y) {
    if (!space) return { x: x, y: y };
    if (v3(cc)) { var t = space.getComponent(cc.UITransform); var q = t.convertToNodeSpaceAR(new cc.Vec3(x, y, 0)); return { x: q.x, y: q.y }; }
    var r = space.convertToNodeSpaceAR(cc.v2(x, y)); return { x: r.x, y: r.y };
  }
  function worldHalfWidth(cc, node) {
    if (v3(cc)) { var t = node.getComponent(cc.UITransform); return t ? t.getBoundingBoxToWorld().width / 2 : 0; }
    return node.getBoundingBoxToWorld().width / 2;
  }

  // What the player sees, in world coordinates. Without a camera: cc.view's visible origin + size (the drawn area:
  // fit-width / fit-height give the extra width or height, SHOW_ALL letterbox bars are outside it). With a camera that
  // follows the course (opts.camera, a 2.4 cc.Camera or 3.x Camera component): centred on the camera, divided by its zoom
  // (2.4 zoomRatio; 3.x orthoHeight is half the visible height).
  function visibleWorld(cc, camera) {
    var v = cc.view, vs = v.getVisibleSize(), vo = v.getVisibleOrigin ? v.getVisibleOrigin() : { x: 0, y: 0 };
    var w = vs.width, h = vs.height, l = vo.x, b = vo.y;
    if (camera && camera.node) {
      var c = worldOf(cc, camera.node);
      if (v3(cc) && camera.orthoHeight > 0) { h = camera.orthoHeight * 2; w = h * vs.width / vs.height; }
      else if (camera.zoomRatio > 0) { w = vs.width / camera.zoomRatio; h = vs.height / camera.zoomRatio; }
      l = c.x - w / 2; b = c.y - h / 2;
    }
    return { left: l, right: l + w, bottom: b, top: b + h, width: w, height: h };
  }

  function visibleRect(cc, opts) {
    opts = o(opts);
    var r = visibleWorld(cc, opts.camera);
    if (!opts.space) return r;
    var a = toSpace(cc, opts.space, r.left, r.bottom), c = toSpace(cc, opts.space, r.right, r.top);
    var l = Math.min(a.x, c.x), rr = Math.max(a.x, c.x), b = Math.min(a.y, c.y), t = Math.max(a.y, c.y);
    return { left: l, right: rr, bottom: b, top: t, width: rr - l, height: t - b };
  }

  function margin(opts) { return Math.max(MIN_MARGIN, typeof opts.margin === 'number' ? opts.margin : MIN_MARGIN); }
  function half(opts) { return typeof opts.halfWidth === 'number' && opts.halfWidth > 0 ? opts.halfWidth : 0; }

  function spawnX(cc, opts) {
    opts = o(opts);
    var x = visibleRect(cc, opts).right + half(opts) + margin(opts);
    if (typeof opts.lastX === 'number' && isFinite(opts.lastX) && typeof opts.gap === 'number') x = Math.max(x, opts.lastX + opts.gap);
    return x;
  }

  function recycleX(cc, opts) {
    opts = o(opts);
    return visibleRect(cc, opts).left - half(opts) - (typeof opts.margin === 'number' && opts.margin > 0 ? opts.margin : 0);
  }

  function isGone(cc, x, opts) { return x < recycleX(cc, opts); }

  function lanesNeeded(cc, opts) {
    opts = o(opts);
    var gap = opts.gap;
    if (!(gap > 0)) throw new Error('CourseLane.lanesNeeded: opts.gap (distance between obstacle groups) must be > 0');
    var screens = opts.screens > 0 ? opts.screens : 1;
    var span = visibleRect(cc, opts).width * screens + 2 * half(opts) + margin(opts);
    return Math.max(2, Math.ceil(span / gap) + 1);
  }

  function itemNodes(it) { return it.nodes && it.nodes.length ? it.nodes : (it.node ? [it.node] : []); }

  function clearForRevive(cc, items, opts) {
    opts = o(opts);
    var vr = visibleWorld(cc, opts.camera), ahead = typeof opts.clearAhead === 'number' ? opts.clearAhead : CLEAR_AHEAD;
    var player = typeof opts.playerX === 'number' ? opts.playerX : vr.left + vr.width / 2;
    var out = { offscreen: [], fade: [], keep: [] };
    (items || []).forEach(function (it) {
      var ns = itemNodes(it), first = ns[0];
      var x = typeof it.x === 'number' ? it.x : (first ? worldOf(cc, first).x : NaN);
      var hw = typeof it.halfWidth === 'number' ? it.halfWidth : (first ? worldHalfWidth(cc, first) : 0);
      if (!isFinite(x)) { out.keep.push(it); return; }
      var shown = ns.some(function (n) { return n.activeInHierarchy !== false; });
      if (!shown || x + hw < vr.left || x - hw > vr.right) out.offscreen.push(it);
      else if (x - hw <= player + ahead) out.fade.push(it);
      else out.keep.push(it);
    });
    if (opts.apply) {
      out.fade.forEach(function (it) {
        fadeOut(cc, itemNodes(it), opts.fadeSeconds, function () { if (typeof opts.onFaded === 'function') opts.onFaded(it); });
      });
    }
    return out;
  }

  function fadeOut(cc, nodes, seconds, done) {
    var s = Math.max(MIN_FADE, typeof seconds === 'number' ? seconds : 0.35);
    var left = nodes.length;
    var finish = function () { if (--left === 0 && typeof done === 'function') done(); };
    if (!left) { if (typeof done === 'function') done(); return s; }
    nodes.forEach(function (n) {
      var target = n;
      if (v3(cc)) { target = n.getComponent(cc.UIOpacity) || n.addComponent(cc.UIOpacity); }
      if (cc.tween) cc.tween(target).to(s, { opacity: 0 }).call(finish).start();
      else { target.opacity = 0; finish(); }
    });
    return s;
  }

  return { VERSION: VERSION, MIN_MARGIN: MIN_MARGIN, MIN_FADE: MIN_FADE, visibleRect: visibleRect, spawnX: spawnX,
    recycleX: recycleX, isGone: isGone, lanesNeeded: lanesNeeded, clearForRevive: clearForRevive, fadeOut: fadeOut };
});
