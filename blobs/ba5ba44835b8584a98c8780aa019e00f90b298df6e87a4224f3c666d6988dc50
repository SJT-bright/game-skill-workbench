/* TikTok capsule position for Cocos Creator 2.4 and 3.x (platform kit 2.0, v7.8, 总表 U1 / B30).
 * One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/CapsuleLayout.js) and
 *   var Capsule = require('CapsuleLayout');
 * 3.x: import it as a plugin script (it also sets the global TikTokCapsuleLayout).
 *
 * Why: tt.getMenuButtonBoundingClientRect() came back in PIXELS on Saul's iPhone 14 (2026-10-29: every value times
 * pixelRatio 3) while the docs and the simulators give POINTS. Three games placed their top bar with the raw value and
 * the bar fell 166 px into the game on the phone (全民飞车漂移 v2; SpiderSwing, Hollys, FoxDenDash the same class). This
 * part decides points vs pixels itself and converts to UI world (design) coordinates, letterbox bars included.
 *
 *   Capsule.screenRect()            {left, top, right, bottom, width, height} in screen POINTS (y down),
 *                                   + unit 'pt' | 'px' (what the SDK gave), source 'sdk' | 'default', raw
 *   Capsule.designRect(cc)          the same rectangle in UI world coordinates (y up): {left, right, top, bottom}
 *   Capsule.safeTopY(cc, margin)    UI world y just below the capsule (bottom - margin): keep tops of nodes under it
 *   Capsule.placeBelow(cc, node, margin)   moves `node` down only when its top edge is above safeTopY; returns the
 *                                   world dy applied (0 when it already fits). For the top bar / a settings button.
 *   Capsule.alignBelow(cc, node, margin)   puts the top edge exactly on safeTopY (up or down): a bar anchored to the capsule.
 * Every function takes an optional sdk (tt / TTMinis.game) as last argument; default: TTMinis.game, then tt.
 * No SDK or a rect without size: a default capsule (87 x 32, 10 pt from the right, 4 pt below the status bar).
 * Proof: tests/capsule-layout.test.js (pt and px give the same design rect, letterbox, 2.4 and 3.x APIs) and the
 * runtime suite layout_state (unit_shift: a still node may not move between the pt and the px pass). 待真机复测.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokCapsuleLayout = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function () {
  'use strict';
  var VERSION = '1.0';

  function sdkOf(sdk) {
    if (sdk) return sdk;
    var g = typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : {});
    if (g.TTMinis && g.TTMinis.game && typeof g.TTMinis.game.getMenuButtonBoundingClientRect === 'function') return g.TTMinis.game;
    if (g.tt && typeof g.tt.getMenuButtonBoundingClientRect === 'function') return g.tt;
    return null;
  }
  function num(v) { return typeof v === 'number' && isFinite(v) ? v : NaN; }

  function systemInfo(api) {
    try { if (api && typeof api.getSystemInfoSync === 'function') return api.getSystemInfoSync() || {}; } catch (e) {}
    return {};
  }

  // Screen rectangle in points. Pixels are recognised when the rect does not fit the window in points: its right edge
  // beyond the window width, or its height more than 2.5x the normal 32 pt capsule (a 3x phone gives 96 / 252..1140).
  function screenRect(sdk) {
    var api = sdkOf(sdk), sys = systemInfo(api);
    var W = num(sys.windowWidth) || num(sys.screenWidth) || 375, pr = num(sys.pixelRatio) || num(sys.devicePixelRatio) || 1;
    var sb = num(sys.statusBarHeight); if (!(sb >= 0)) sb = 20;
    var raw = null;
    try { if (api && typeof api.getMenuButtonBoundingClientRect === 'function') raw = api.getMenuButtonBoundingClientRect(); } catch (e) { raw = null; }
    var r = raw ? { left: num(raw.left), top: num(raw.top), right: num(raw.right), bottom: num(raw.bottom) } : null;
    if (r) {
      if (!(r.right > r.left) && num(raw.width) > 0) r.right = r.left + raw.width;
      if (!(r.bottom > r.top) && num(raw.height) > 0) r.bottom = r.top + raw.height;
    }
    var ok = r && r.right > r.left && r.bottom > r.top && isFinite(r.left + r.top + r.right + r.bottom);
    if (!ok) {
      var d = { left: W - 97, right: W - 10, top: sb + 4, bottom: sb + 36 };
      return { left: d.left, top: d.top, right: d.right, bottom: d.bottom, width: 87, height: 32, unit: 'pt', scale: 1, source: 'default', raw: raw };
    }
    var px = pr > 1 && (r.right > W * 1.02 || (r.bottom - r.top) > 80);
    var k = px ? 1 / pr : 1;
    return { left: r.left * k, top: r.top * k, right: r.right * k, bottom: r.bottom * k, width: (r.right - r.left) * k,
      height: (r.bottom - r.top) * k, unit: px ? 'px' : 'pt', scale: k, source: 'sdk', raw: raw };
  }

  // Screen points (y down) -> UI world coordinates (y up), through the engine's real viewport (2.4 and 3.x):
  // worldX = (x - vpX / dpr) / (scaleX / dpr), worldY = (frameH - y - vpY / dpr) / (scaleY / dpr).
  function mapper(cc) {
    var v = cc && cc.view;
    if (!v) throw new Error('CapsuleLayout: cc.view missing (pass the engine namespace cc)');
    var dpr = (v.getDevicePixelRatio && v.getDevicePixelRatio()) || (cc.screen && cc.screen.devicePixelRatio) || 1;
    // frame height in points: 3.x screen.windowSize is in physical pixels; 2.4 view.getFrameSize() in points
    var fh;
    if (cc.UITransform && cc.screen && cc.screen.windowSize) fh = cc.screen.windowSize.height / dpr;
    else if (v.getFrameSize) fh = v.getFrameSize().height;
    var vp = v.getViewportRect ? v.getViewportRect() : null;
    var sx = v.getScaleX ? v.getScaleX() : 0, sy = v.getScaleY ? v.getScaleY() : 0;
    if (vp && vp.width > 0 && sx > 0 && sy > 0 && fh > 0) {
      var kx = sx / dpr, ky = sy / dpr, ox = vp.x / dpr, oy = vp.y / dpr;
      return function (x, y) { return { x: (x - ox) / kx, y: (fh - y - oy) / ky }; };
    }
    // no viewport API: the visible area fills the frame
    var vs = v.getVisibleSize(), o = v.getVisibleOrigin ? v.getVisibleOrigin() : { x: 0, y: 0 }, fs = v.getFrameSize ? v.getFrameSize() : vs;
    var k2x = fs.width / vs.width, k2y = fs.height / vs.height;
    return function (x, y) { return { x: o.x + x / k2x, y: o.y + (fs.height - y) / k2y }; };
  }

  function designRect(cc, sdk) {
    var s = screenRect(sdk), m = mapper(cc), a = m(s.left, s.top), b = m(s.right, s.bottom);
    return { left: a.x, right: b.x, top: a.y, bottom: b.y, screen: s };
  }

  function safeTopY(cc, margin, sdk) {
    return designRect(cc, sdk).bottom - (typeof margin === 'number' ? margin : 8);
  }

  function worldTop(cc, node) {
    if (cc.UITransform) { var t = node.getComponent(cc.UITransform); var b = t.getBoundingBoxToWorld(); return b.y + b.height; }
    var r = node.getBoundingBoxToWorld(); return r.y + r.height;
  }

  function placeBelow(cc, node, margin, sdk) {
    var dy = worldTop(cc, node) - safeTopY(cc, margin, sdk);
    if (!(dy > 0)) return 0;
    return moveDown(cc, node, dy);
  }

  // the node's top edge exactly on safeTopY (up or down): for a top bar that is anchored to the capsule
  function alignBelow(cc, node, margin, sdk) {
    return moveDown(cc, node, worldTop(cc, node) - safeTopY(cc, margin, sdk));
  }

  function moveDown(cc, node, dy) {
    if (!dy) return 0;
    if (cc.UITransform) {
      var wp = node.worldPosition;
      node.setWorldPosition(wp.x, wp.y - dy, wp.z);
    } else {
      var w = node.convertToWorldSpaceAR(cc.v2(0, 0));
      var local = node.parent ? node.parent.convertToNodeSpaceAR(cc.v2(w.x, w.y - dy)) : cc.v2(w.x, w.y - dy);
      node.setPosition(local);
    }
    return dy;
  }

  return { VERSION: VERSION, screenRect: screenRect, designRect: designRect, safeTopY: safeTopY, placeBelow: placeBelow,
    alignBelow: alignBelow, _mapper: mapper };
});
