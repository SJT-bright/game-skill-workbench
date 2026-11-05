/* Background cover, safe-area groups and one canvas fit, for Cocos Creator 2.4 and 3.x (platform kit 2.0, v7.9,
 * 生成时预防 P07). One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/ScreenFit.js) and
 *   var Fit = require('ScreenFit');
 * 3.x: import it as a plugin script (it also sets the global TikTokScreenFit).
 *
 * Why (问题普查 2026-11-04, screen_fit_wrong 28 次): backgrounds and ground were sized to the design width, so wide or
 * long screens showed black or white edges (RerackYourPlates 短屏黑边, 王者打砖块 长屏横向被压到 82%); a base game had
 * fitWidth AND fitHeight on, so long screens squashed everything; top bars built children at fixed negative offsets
 * and were pushed off screen (Bus Queue, 挪车冲冲冲, GooglyEyeRecall 卡车超出长屏安全区). Every number here comes from
 * the engine's REAL visible rect (cc.view visible size / origin, or the camera that draws the node), the same
 * calculation as CourseLane.js, never from the design resolution.
 *
 *   Fit.visibleRect(cc, opts)        {left, right, bottom, top, width, height} the player sees, world coordinates
 *                                    (opts.camera: a 2.4 cc.Camera / 3.x Camera that follows the scene)
 *   Fit.cover(cc, bgNode, opts)      scales bgNode uniformly (picture ratio kept) so it covers the whole visible rect
 *                                    (+ opts.bleed, default 2) and centres it there. Returns {scale, x, y, covered, visible}.
 *                                    opts.watch: true re-runs it on every canvas resize (returns .off() to stop).
 *                                    opts.width / opts.height: the picture size when the node size is not it.
 *   Fit.safeRect(cc, opts)           visible rect ∩ cc.sys.getSafeAreaRect(), top lowered under the TikTok capsule when
 *                                    TikTokCapsuleLayout is loaded (opts.capsule: false to skip; opts.sdk passed on)
 *   Fit.safeTop(cc, nodes, opts)     moves one node or a group (same world dx/dy for all) so the group's COMBINED
 *                                    bounding box (children included) is inside the safe rect, under its top edge.
 *                                    opts.align 'top': put the top edge exactly on it. opts.margin default 8.
 *   Fit.safeBottom(cc, nodes, opts)  the same against the bottom edge (opts.align 'bottom' to stick to it).
 *                                    Both return {dx, dy, box, rect, fits}; fits=false when the group is wider or
 *                                    taller than the safe rect (then it is centred and the caller must shrink it).
 *   Fit.canvasPolicy(cc, canvas, opts)   exactly ONE fit: portrait -> fitWidth, landscape -> fitHeight (opts.orientation
 *                                    or design w > h). 2.4: cc.Canvas fitWidth / fitHeight; 3.x:
 *                                    view.setDesignResolutionSize(w, h, ResolutionPolicy.FIXED_WIDTH / FIXED_HEIGHT).
 *                                    Returns {orientation, policy, before, changed}.
 *   Fit.checkCanvas(cc, canvas, opts)    problems (strings) without changing anything: both fits on, none on, the
 *                                    wrong one for the orientation. [] = fine.
 * Pass sibling nodes to safeTop / safeBottom, not a parent and its own child (the child would move twice).
 * Proof: tests/screen-fit.test.js (720x1280, 720x1560, 900x1200 and a 1880x1334 desktop window, 2.4 and 3.x APIs;
 * negative controls: design-size background, both fits on, top bar with an icon at -80). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokScreenFit = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0', BLEED = 2, MARGIN = 8;

  function v3(cc) { return !!(cc && cc.UITransform); }
  function o(opts) { return opts || {}; }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function gl() { return typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : {}); }

  // ---- engine helpers (2.4 node API vs 3.x UITransform) ----
  function ut(cc, node) { return node && node.getComponent ? node.getComponent(cc.UITransform) : null; }
  function toWorld(cc, node, x, y) {
    if (!node) return { x: x, y: y };
    if (v3(cc)) { var t = ut(cc, node); if (!t) { var p = node.worldPosition || { x: 0, y: 0 }; return { x: p.x + x, y: p.y + y }; }
      var q = t.convertToWorldSpaceAR(new cc.Vec3(x, y, 0)); return { x: q.x, y: q.y }; }
    var w = node.convertToWorldSpaceAR(cc.v2(x, y)); return { x: w.x, y: w.y };
  }
  function toLocal(cc, node, x, y) {
    if (!node) return { x: x, y: y };
    if (v3(cc)) { var t = ut(cc, node); if (!t) { var p = node.worldPosition || { x: 0, y: 0 }; return { x: x - p.x, y: y - p.y }; }
      var q = t.convertToNodeSpaceAR(new cc.Vec3(x, y, 0)); return { x: q.x, y: q.y }; }
    var r = node.convertToNodeSpaceAR(cc.v2(x, y)); return { x: r.x, y: r.y };
  }
  // world length of one local unit of `node` along x and y (parent scale chain)
  function worldScale(cc, node) {
    if (!node) return { x: 1, y: 1 };
    var a = toWorld(cc, node, 0, 0), bx = toWorld(cc, node, 1, 0), by = toWorld(cc, node, 0, 1);
    return { x: Math.sqrt(Math.pow(bx.x - a.x, 2) + Math.pow(bx.y - a.y, 2)) || 1,
      y: Math.sqrt(Math.pow(by.x - a.x, 2) + Math.pow(by.y - a.y, 2)) || 1 };
  }
  function sizeOf(cc, node, opts) {
    var t = v3(cc) ? ut(cc, node) : node;
    var w = num(opts.width, t ? num(t.width, 0) : 0), h = num(opts.height, t ? num(t.height, 0) : 0);
    var ax = t ? num(t.anchorX, 0.5) : 0.5, ay = t ? num(t.anchorY, 0.5) : 0.5;
    return { w: w, h: h, ax: ax, ay: ay };
  }
  function setScale(cc, node, sx, sy) {
    if (v3(cc)) { var z = node.scale ? num(node.scale.z, 1) : 1; node.setScale(sx, sy, z); return; }
    node.scaleX = sx; node.scaleY = sy;
  }
  function setLocalPos(cc, node, x, y) {
    if (v3(cc)) { var z = node.position ? num(node.position.z, 0) : 0; node.setPosition(x, y, z); return; }
    if (typeof node.setPosition === 'function') node.setPosition(x, y); else { node.x = x; node.y = y; }
  }
  function worldBox(cc, node) {
    var b = v3(cc) ? ut(cc, node).getBoundingBoxToWorld() : node.getBoundingBoxToWorld();
    return { left: b.x, bottom: b.y, right: b.x + b.width, top: b.y + b.height };
  }
  function anchorWorld(cc, node) {
    if (v3(cc)) { var p = node.worldPosition; return { x: p.x, y: p.y }; }
    return toWorld(cc, node, 0, 0);
  }
  function moveWorld(cc, node, dx, dy) {
    if (!dx && !dy) return;
    var w = anchorWorld(cc, node);
    if (v3(cc) && typeof node.setWorldPosition === 'function') {
      var z = node.worldPosition ? num(node.worldPosition.z, 0) : 0; node.setWorldPosition(w.x + dx, w.y + dy, z); return;
    }
    var l = toLocal(cc, node.parent, w.x + dx, w.y + dy); setLocalPos(cc, node, l.x, l.y);
  }

  // ---- visible rect: same calculation as CourseLane.js ----
  function visibleRect(cc, opts) {
    opts = o(opts);
    var v = cc.view, vs = v.getVisibleSize(), vo = v.getVisibleOrigin ? v.getVisibleOrigin() : { x: 0, y: 0 };
    var w = vs.width, h = vs.height, l = vo.x, b = vo.y, camera = opts.camera;
    if (camera && camera.node) {
      var c = anchorWorld(cc, camera.node);
      if (v3(cc) && camera.orthoHeight > 0) { h = camera.orthoHeight * 2; w = h * vs.width / vs.height; }
      else if (camera.zoomRatio > 0) { w = vs.width / camera.zoomRatio; h = vs.height / camera.zoomRatio; }
      l = c.x - w / 2; b = c.y - h / 2;
    }
    return { left: l, right: l + w, bottom: b, top: b + h, width: w, height: h };
  }

  // ---- cover ----
  function coverOnce(cc, node, opts) {
    var vis = visibleRect(cc, opts), bleed = Math.max(0, num(opts.bleed, BLEED));
    var sz = sizeOf(cc, node, opts);
    if (!(sz.w > 0 && sz.h > 0)) throw new Error('ScreenFit.cover: the node has no size (give opts.width / opts.height)');
    var ps = worldScale(cc, node.parent);
    var s = Math.max((vis.width + 2 * bleed) / (sz.w * ps.x), (vis.height + 2 * bleed) / (sz.h * ps.y));
    var oldX = v3(cc) ? (node.scale ? node.scale.x : 1) : num(node.scaleX, 1);
    var oldY = v3(cc) ? (node.scale ? node.scale.y : 1) : num(node.scaleY, 1);
    var sx = oldX < 0 ? -s : s, sy = oldY < 0 ? -s : s;           // keep a mirrored background mirrored
    setScale(cc, node, sx, sy);
    var cx = vis.left + vis.width / 2, cy = vis.bottom + vis.height / 2;
    var c = toLocal(cc, node.parent, cx, cy);
    var ax = sx < 0 ? 1 - sz.ax : sz.ax, ay = sy < 0 ? 1 - sz.ay : sz.ay;
    var x = c.x + (ax - 0.5) * sz.w * s, y = c.y + (ay - 0.5) * sz.h * s;
    setLocalPos(cc, node, x, y);
    var hw = sz.w * s * ps.x / 2, hh = sz.h * s * ps.y / 2;
    return { scale: s, x: x, y: y, visible: vis,
      covered: { left: cx - hw, right: cx + hw, bottom: cy - hh, top: cy + hh } };
  }

  function cover(cc, node, opts) {
    opts = o(opts);
    var res = coverOnce(cc, node, opts);
    if (opts.watch) {
      var v = cc.view, fn = function () { try { coverOnce(cc, node, opts); } catch (e) { try { console.warn('[ScreenFit] cover', e); } catch (_) {} } };
      var evs = ['canvas-resize', 'design-resolution-changed'];
      if (v && typeof v.on === 'function') evs.forEach(function (e) { v.on(e, fn); });
      res.off = function () { if (v && typeof v.off === 'function') evs.forEach(function (e) { v.off(e, fn); }); };
    }
    return res;
  }

  // ---- safe area ----
  function safeRect(cc, opts) {
    opts = o(opts);
    var r = visibleRect(cc, {});
    try {
      if (cc.sys && typeof cc.sys.getSafeAreaRect === 'function') {
        var s = cc.sys.getSafeAreaRect();
        if (s && s.width > 0 && s.height > 0) {
          var l = Math.max(r.left, s.x), b = Math.max(r.bottom, s.y);
          var rr = Math.min(r.right, s.x + s.width), t = Math.min(r.top, s.y + s.height);
          if (rr > l && t > b) r = { left: l, right: rr, bottom: b, top: t, width: rr - l, height: t - b };
        }
      }
    } catch (e) {}
    var Cap = opts.capsuleLayout || gl().TikTokCapsuleLayout;
    if (opts.capsule !== false && Cap && typeof Cap.safeTopY === 'function') {
      try { var y = Cap.safeTopY(cc, 0, opts.sdk); if (isFinite(y) && y < r.top && y > r.bottom) { r.top = y; r.height = r.top - r.bottom; } } catch (e) {}
    }
    return r;
  }

  function list(nodes) { return Array.isArray(nodes) ? nodes.filter(Boolean) : (nodes ? [nodes] : []); }
  function unionBox(cc, ns) {
    var u = null;
    ns.forEach(function (n) {
      var b = worldBox(cc, n);
      u = u ? { left: Math.min(u.left, b.left), bottom: Math.min(u.bottom, b.bottom), right: Math.max(u.right, b.right), top: Math.max(u.top, b.top) } : b;
    });
    return u;
  }
  function placeIn(cc, nodes, opts, edge) {
    opts = o(opts);
    var ns = list(nodes);
    if (!ns.length) throw new Error('ScreenFit.safe' + edge + ': no nodes');
    var m = Math.max(0, num(opts.margin, MARGIN)), rect = safeRect(cc, opts), box = unionBox(cc, ns);
    var bw = box.right - box.left, bh = box.top - box.bottom, fits = true, dx = 0, dy = 0;
    var L = rect.left + m, R = rect.right - m, B = rect.bottom + m, T = rect.top - m;
    if (bw > R - L) { fits = false; dx = (L + R) / 2 - (box.left + box.right) / 2; }
    else if (box.left < L) dx = L - box.left;
    else if (box.right > R) dx = R - box.right;
    if (bh > T - B) { fits = false; dy = edge === 'Top' ? T - box.top : B - box.bottom; }
    else if (edge === 'Top') { if (opts.align === 'top' || box.top > T) dy = T - box.top; else if (box.bottom < B) dy = B - box.bottom; }
    else { if (opts.align === 'bottom' || box.bottom < B) dy = B - box.bottom; else if (box.top > T) dy = T - box.top; }
    ns.forEach(function (n) { moveWorld(cc, n, dx, dy); });
    return { dx: dx, dy: dy, fits: fits, rect: rect,
      box: { left: box.left + dx, right: box.right + dx, bottom: box.bottom + dy, top: box.top + dy } };
  }
  function safeTop(cc, nodes, opts) { return placeIn(cc, nodes, opts, 'Top'); }
  function safeBottom(cc, nodes, opts) { return placeIn(cc, nodes, opts, 'Bottom'); }

  // ---- canvas fit ----
  function designSize(cc, canvas) {
    var d = cc.view && typeof cc.view.getDesignResolutionSize === 'function' ? cc.view.getDesignResolutionSize() : null;
    if ((!d || !(d.width > 0)) && canvas && canvas.designResolution) d = canvas.designResolution;
    return d && d.width > 0 ? { width: d.width, height: d.height } : { width: 750, height: 1334 };
  }
  function orientationOf(cc, canvas, opts) {
    if (opts.orientation === 'portrait' || opts.orientation === 'landscape') return opts.orientation;
    var d = designSize(cc, canvas); return d.width > d.height ? 'landscape' : 'portrait';
  }
  function has24Fit(canvas) { return !!canvas && ('fitWidth' in canvas || 'fitHeight' in canvas); }
  function policy3(cc) {
    var v = cc.view; if (!v || typeof v.getResolutionPolicy !== 'function') return null;
    var p = v.getResolutionPolicy();
    if (p && v._rpFixedWidth && p === v._rpFixedWidth) return 'fitWidth';
    if (p && v._rpFixedHeight && p === v._rpFixedHeight) return 'fitHeight';
    if (p && typeof p.name === 'string') return p.name === 'FIXED_WIDTH' ? 'fitWidth' : p.name === 'FIXED_HEIGHT' ? 'fitHeight' : 'other';
    return p == null ? null : 'other';
  }

  function checkCanvas(cc, canvas, opts) {
    opts = o(opts);
    var want = orientationOf(cc, canvas, opts) === 'landscape' ? 'fitHeight' : 'fitWidth', out = [];
    if (has24Fit(canvas)) {
      var fw = !!canvas.fitWidth, fh = !!canvas.fitHeight;
      if (fw && fh) out.push('both fitWidth and fitHeight are on (long screens get squashed / letterboxed): keep only ' + want);
      else if (!fw && !fh) out.push('neither fitWidth nor fitHeight is on (SHOW_ALL letterbox bars): turn on ' + want);
      else if ((want === 'fitWidth') !== fw) out.push((fw ? 'fitWidth' : 'fitHeight') + ' is on but this ' + (want === 'fitWidth' ? 'portrait' : 'landscape') + ' game needs ' + want);
      return out;
    }
    var p = policy3(cc);
    if (p && p !== 'other' && p !== want && (p === 'fitWidth' || p === 'fitHeight')) out.push('resolution policy is ' + p + ', this game needs ' + want);
    else if (p === 'other') out.push('resolution policy is not FIXED_WIDTH / FIXED_HEIGHT: use ' + want);
    return out;
  }

  function canvasPolicy(cc, canvas, opts) {
    opts = o(opts);
    var orientation = orientationOf(cc, canvas, opts), policy = orientation === 'landscape' ? 'fitHeight' : 'fitWidth';
    var before, changed = false;
    if (has24Fit(canvas)) {
      before = { fitWidth: !!canvas.fitWidth, fitHeight: !!canvas.fitHeight };
      var fw = policy === 'fitWidth';
      if (before.fitWidth !== fw) { canvas.fitWidth = fw; changed = true; }
      if (before.fitHeight !== !fw) { canvas.fitHeight = !fw; changed = true; }
    } else {
      before = { policy: policy3(cc) };
      var d = designSize(cc, canvas), RP = cc.ResolutionPolicy;
      if (before.policy !== policy && cc.view && typeof cc.view.setDesignResolutionSize === 'function' && RP) {
        cc.view.setDesignResolutionSize(d.width, d.height, policy === 'fitWidth' ? RP.FIXED_WIDTH : RP.FIXED_HEIGHT);
        changed = true;
      }
    }
    return { orientation: orientation, policy: policy, before: before, changed: changed };
  }

  return { VERSION: VERSION, BLEED: BLEED, MARGIN: MARGIN, visibleRect: visibleRect, cover: cover, safeRect: safeRect,
    safeTop: safeTop, safeBottom: safeBottom, canvasPolicy: canvasPolicy, checkCanvas: checkCanvas };
});
