/* Top bar out from under the TikTok capsule, with nothing to call (platform kit, 生成时预防 P06 第 4 点, Cocos 2.4).
 * `tiktok_finalize.py source` (step capsule_auto) copies this file and CapsuleLayout.js into assets/tiktok-platform/
 * for NEW games; English (localize) and legacy games only get a warning listing their top-bar nodes.
 * Why: CapsuleLayout.js was opt-in, so most top bars never used it: the census found 99 overlaps in 64 games (first
 * place) and 16 top bars / coin counters under the capsule.
 *
 * What it does: every Cocos 2.4 script in the bundle runs when the bundle loads, so this file only listens. After each
 * scene launch (and a few times in the first 10 s of the scene, for pages that are switched on later) it walks the
 * nodes up to depth 4 under the Canvas. A node counts as a top-bar node when its name contains top / hud / coin, or
 * when it is a direct child of the Canvas (or of a page root under it) whose top edge lies in the top 15% of the
 * visible area; either way it must be at most 25% of the visible height tall (a full-screen page root, background or
 * HUD container is not a bar: the walk goes into it instead). Such a node is moved down ONLY when its world box really overlaps the capsule (horizontally, and its
 * top edge above CapsuleLayout.safeTopY): a coin counter on the left, or a node already below the capsule, never moves.
 * A cc.Widget aligned to the top gets widget.top += dy (so it does not snap back); otherwise the node moves.
 * Parents are handled before children, so a moved bar does not move its children twice.
 *   TikTokCapsuleAuto.off = true      switch it off (a game that places its bar itself with CapsuleLayout)
 *   a node whose name contains 'nocapsule' is never moved
 *   TikTokCapsuleAuto.pass(cc, root)  one pass by hand (tests, a page built by code) -> [{name, dy}]
 * Proof: tests/capsule-auto.test.js (fake 2.4 engine). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokCapsuleAuto = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0';
  var NAME = /top|hud|coin/i;
  var TOP_SHARE = 0.15, BAR_SHARE = 0.25, MAX_DEPTH = 4, MARGIN = 8;
  var api = { VERSION: VERSION, off: false, NAME: NAME, TOP_SHARE: TOP_SHARE };

  function capsuleLib() {
    try { if (typeof require === 'function') return require('CapsuleLayout'); } catch (e) {}
    var g = typeof globalThis !== 'undefined' ? globalThis : {};
    return g.TikTokCapsuleLayout || null;
  }

  function box(node) {
    var r = node.getBoundingBoxToWorld();
    return { left: r.x, right: r.x + r.width, bottom: r.y, top: r.y + r.height };
  }

  function visibleTop(cc) {
    var o = cc.view.getVisibleOrigin ? cc.view.getVisibleOrigin() : { x: 0, y: 0 };
    var s = cc.view.getVisibleSize();
    return { top: o.y + s.height, height: s.height };
  }

  function candidates(cc, canvas) {
    var out = [], v = visibleTop(cc), line = v.top - v.height * TOP_SHARE;
    function walk(node, depth, pageLevel) {
      var kids = node.children || [];
      for (var i = 0; i < kids.length; i++) {
        var n = kids[i];
        if (!n.activeInHierarchy || /nocapsule/i.test(n.name || '')) continue;
        var b = box(n), bar = b.top - b.bottom <= v.height * BAR_SHARE;   // a page root or background is not a bar
        var byName = bar && NAME.test(n.name || '');
        var byPlace = bar && pageLevel && b.top > line;
        if (byName || byPlace) out.push(n);
        else if (depth < MAX_DEPTH) walk(n, depth + 1, depth === 0);
      }
    }
    walk(canvas, 0, true);
    return out;
  }

  function moveDown(cc, Capsule, node, dy) {
    var W = cc.Widget, w = W && node.getComponent ? node.getComponent(W) : null;
    if (w && w.enabled && w.isAlignTop) {
      w.top += dy;
      if (w.updateAlignment) w.updateAlignment();
      return dy;
    }
    if (w && w.enabled && w.isAlignBottom && !w.isAlignTop) {
      w.bottom -= dy;
      if (w.updateAlignment) w.updateAlignment();
      return dy;
    }
    var p = node.parent, wp = node.convertToWorldSpaceAR(cc.v2(0, 0));
    node.setPosition(p ? p.convertToNodeSpaceAR(cc.v2(wp.x, wp.y - dy)) : cc.v2(wp.x, wp.y - dy));
    return dy;
  }

  // one pass: every top-bar node that overlaps the capsule moves just below it -> [{name, dy}]
  function pass(cc, canvas, sdk) {
    var Capsule = capsuleLib();
    if (api.off || !Capsule || !canvas) return [];
    var cap = Capsule.designRect(cc, sdk), safe = Capsule.safeTopY(cc, MARGIN, sdk), moved = [];
    var list = candidates(cc, canvas);
    for (var i = 0; i < list.length; i++) {
      var b = box(list[i]);
      if (b.right <= cap.left || b.left >= cap.right) continue;       // beside the capsule, not under it
      var dy = b.top - safe;
      if (!(dy > 0.5)) continue;
      moved.push({ name: list[i].name, dy: moveDown(cc, Capsule, list[i], dy) });
    }
    return moved;
  }
  api.pass = pass;
  api.candidates = candidates;

  function canvasNode(cc) {
    var scene = cc.director.getScene && cc.director.getScene();
    var c = scene && cc.Canvas && scene.getComponentInChildren ? scene.getComponentInChildren(cc.Canvas) : null;
    return c ? c.node : null;
  }

  function install(cc) {
    if (!cc || !cc.director || !cc.Director || install.done) return false;
    install.done = true;
    var timer = null;
    cc.director.on(cc.Director.EVENT_AFTER_SCENE_LAUNCH, function () {
      var frames = 0;
      if (timer) cc.director.off(cc.Director.EVENT_AFTER_UPDATE, timer);
      // after the widgets of that frame aligned; then every 30 frames for about 10 s (pages switched on later)
      timer = function () {
        if (frames === 1 || (frames > 1 && frames % 30 === 0)) {
          try { pass(cc, canvasNode(cc)); } catch (e) { if (cc.warn) cc.warn('CapsuleAuto: ' + e); }
        }
        if (++frames > 600) { cc.director.off(cc.Director.EVENT_AFTER_UPDATE, timer); timer = null; }
      };
      cc.director.on(cc.Director.EVENT_AFTER_UPDATE, timer);
    });
    return true;
  }
  api.install = install;
  if (typeof cc !== 'undefined' && cc && cc.director) install(cc);
  return api;
});
