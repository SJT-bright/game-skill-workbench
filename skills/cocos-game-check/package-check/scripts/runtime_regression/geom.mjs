// In-page geometry for the v7.8 layout / button-sweep / ad-entry / trial-link suites (总表 B30), Cocos 2.4 and 3.x.
// From the 全民飞车门禁 prototype lib/geom.mjs (2026-10-30). Paste GEOM_JS at the top of a page.evaluate string:
// "(function(){" + GEOM_JS + body + "})()". It defines:
//   cc, V3                 the engine namespace; V3 = Cocos Creator 3.x (it has cc.UITransform)
//   pathOf(n), walkScene(fn)
//   worldBox(n)            world rect (2.x node box, 3.x UITransform box); null for a 3.x node without UITransform (3D)
//   shownChain(n)          no opacity 0 / scale 0 on the node or an ancestor (2.x node.opacity, 3.x UIOpacity)
//   cssBox(n)              {x0,y0,x1,y1} in page CSS px (= phone points), or null
//                            2.x: through cc.view's real viewport (getViewportRect + getScaleX()/dpr): letterboxed
//                                 SHOW_ALL games have bars (MergeShot2048 75 pt top and bottom)
//                            3.x: the cam-point block (the camera of the node's Canvas, identical text in
//                                 ad_regression/cases.mjs and lib.mjs) and the css-point block, corner by corner
//   frameCss()             the game canvas in page CSS px {left, top, w, h}
//   hideNode(n)            make one node and its children invisible; returns restore()
//   hasTouch(n), ownTouchEnd(n), coverOf(n), glContext(), readFrame(gl, W, H), meshRenderers()
// Keep this text free of backquotes and dollar-brace: it is pasted into template strings.
export const GEOM_JS = `
  var cc = window.cc;
  var V3 = !!cc.UITransform;
  function pathOf(n) { var p = []; while (n && n.parent) { p.unshift(n.name); n = n.parent; } return p.join('/'); }
  // 3.x: walk the scene's children, not the Scene itself (Scene.activeInHierarchy logs an engine error, lib.mjs)
  function walkScene(fn) {
    var s = cc.director.getScene(); if (!s) return;
    if (!V3) { s.walk(fn); return; }
    (s.children || []).forEach(function (c) { c.walk(fn); });
  }
  function worldBox(n) {
    if (!V3) return n.getBoundingBoxToWorld();
    var t = n.getComponent(cc.UITransform); return t ? t.getBoundingBoxToWorld() : null;
  }
  function shownChain(n) {
    for (var x = n; x; x = x.parent) {
      if (!V3) { if (x.opacity === 0 || x.scaleX === 0 || x.scaleY === 0) return false; continue; }
      var u = x.getComponent && cc.UIOpacity && x.getComponent(cc.UIOpacity);
      if (u && u.enabled !== false && u.opacity === 0) return false;
      var s = x.scale; if (s && typeof s === 'object' && (s.x === 0 || s.y === 0)) return false;
    }
    return true;
  }
  function frameCss() {
    var cv = cc.game && cc.game.canvas;
    if (cv) { try { var r = Element.prototype.getBoundingClientRect.call(cv); if (r.width > 0 && r.height > 0) return { left: r.left, top: r.top, w: r.width, h: r.height }; } catch (e) {} }
    var fs = cc.view.getFrameSize(); return { left: 0, top: 0, w: fs.width, h: fs.height };
  }
  var GM2 = null;
  function map2() {
    if (GM2) return GM2;
    var v = cc.view, fs = v.getFrameSize(), vs = v.getVisibleSize(), o = v.getVisibleOrigin();
    var vp = v.getViewportRect ? v.getViewportRect() : null;
    var dpr = (v.getDevicePixelRatio && v.getDevicePixelRatio()) || (cc.screen && cc.screen.devicePixelRatio) || 1;
    var real = !!(vp && vp.width > 0 && v.getScaleX && v.getScaleX() > 0);
    var kx = real ? v.getScaleX() / dpr : fs.width / vs.width, ky = real ? v.getScaleY() / dpr : fs.height / vs.height;
    var ox = real ? vp.x / dpr : -o.x * kx, oy = real ? vp.y / dpr : -o.y * ky;
    GM2 = { fw: fs.width, fh: fs.height, kx: kx, ky: ky, ox: ox, oy: oy };
    return GM2;
  }
  // 3.x world point -> page CSS point: the shared cam-point and css-point blocks (test_tap_point.py runs every copy)
  function camPoint3(n, w) {
    var v2api = false, p;
        // cam-point:begin (v7.8, 总表 A13 补) world point -> camera screen point; identical in ad_regression/cases.mjs and runtime_regression/lib.mjs.
        // 2.x: the node's own camera. 3.x: the cameraComponent of the Canvas the node sits under (walk up the parents);
        // only when there is none, the first camera of the scene. cams[0] alone is the 3D world camera in a 3D game
        // (企鹅雪道 v4: the X came out at (818, -918) and nocallback failed a game whose ad was fine).
        if (v2api) p = cc.Camera.findCamera(n).getWorldToScreenPoint(w);
        else {
          let cam = null;
          for (let a = n; a && !cam; a = a.parent) {
            const cv = a.getComponent && a.getComponent(cc.Canvas);
            cam = (cv && (cv.cameraComponent || cv._cameraComponent)) || null;
          }
          if (!cam) cam = cc.director.getScene().getComponentsInChildren(cc.Camera)[0];
          p = new cc.Vec3(); cam.worldToScreen(w, p);
        }
        // cam-point:end
    return p;
  }
  function cssPoint3(p) {
    var v2api = false, canvas = cc.game.canvas, f = frameCss(), rect = { left: f.left, top: f.top, width: f.w, height: f.h };
    // css-point:begin (v7.7.5, 总表 A13) the same conversion as ad_regression/cases.mjs (A5): Cocos 2.x
    // getWorldToScreenPoint works in cc.visibleRect units, 3.x worldToScreen in canvas pixels.
    const vis = (v2api && cc.visibleRect) ? { w: cc.visibleRect.width, h: cc.visibleRect.height } : { w: canvas.width, h: canvas.height };
    return { x: rect.left + p.x * rect.width / vis.w, y: rect.top + rect.height - p.y * rect.height / vis.h };
    // css-point:end
  }
  function cssBox(n) {
    var r = worldBox(n); if (!r) return null;
    if (!V3) { var m = map2(); return { x0: m.ox + r.x * m.kx, x1: m.ox + (r.x + r.width) * m.kx, y0: m.fh - (m.oy + (r.y + r.height) * m.ky), y1: m.fh - (m.oy + r.y * m.ky) }; }
    var z = n.worldPosition ? n.worldPosition.z : 0;
    var a = cssPoint3(camPoint3(n, new cc.Vec3(r.x, r.y, z))), b = cssPoint3(camPoint3(n, new cc.Vec3(r.x + r.width, r.y + r.height, z)));
    return { x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), y0: Math.min(a.y, b.y), y1: Math.max(a.y, b.y) };
  }
  function hideNode(n) {
    if (!V3) { var op = n.opacity; n.opacity = 0; return function () { n.opacity = op; }; }
    var u = n.getComponent(cc.UIOpacity), added = false;
    if (!u) { u = n.addComponent(cc.UIOpacity); added = true; }
    var o3 = u.opacity; u.opacity = 0;
    return function () { u.opacity = o3; if (added) { try { u.destroy(); } catch (e) {} } };
  }
  var TOUCH_START = V3 ? 'touch-start' : 'touchstart', TOUCH_END = V3 ? 'touch-end' : 'touchend';
  function hasTouch(n) {
    try { if (!V3 && !n._touchListener) return false; return !!(n.hasEventListener(TOUCH_END) || n.hasEventListener(TOUCH_START)); } catch (e) { return false; }
  }
  function ownTouchEnd(n) {
    try {
      if (!V3) { var tbl = n._bubblingListeners && n._bubblingListeners._callbackTable, te = tbl && tbl.touchend; return te ? Math.max(0, (te.callbackInfos || te.callbacks || []).filter(Boolean).length - 1) : 0; }
      var ep = n.eventProcessor || n._eventProcessor, bt = ep && ep.bubblingTarget, tb = bt && bt._callbackTable, t3 = tb && tb[TOUCH_END];
      return t3 ? Math.max(0, (t3.callbackInfos || []).filter(Boolean).length - 1) : 0;
    } catch (e) { return 0; }
  }
  function glContext() {
    if (!V3) return (cc.game && cc.game._renderContext) || (cc.renderer && cc.renderer.device && cc.renderer.device._gl) || null;
    try { var d = cc.director.root && cc.director.root.device; if (d && d.gl && d.gl.readPixels) return d.gl; } catch (e) {}
    var cv = cc.game && cc.game.canvas; if (!cv || !cv.getContext) return null;
    try { return cv.getContext('webgl2') || cv.getContext('webgl'); } catch (e) { return null; }
  }
  function readFrame(gl, W, H) {
    var buf = new Uint8Array(W * H * 4);
    var gl2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
    var fb = gl.getParameter(gl.FRAMEBUFFER_BINDING), rfb = gl2 ? gl.getParameter(gl.READ_FRAMEBUFFER_BINDING) : null;
    var pbo = gl2 ? gl.getParameter(gl.PIXEL_PACK_BUFFER_BINDING) : null;
    if (pbo) gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    if (gl2) { if (rfb) gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null); } else if (fb) gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    if (gl2) { if (rfb) gl.bindFramebuffer(gl.READ_FRAMEBUFFER, rfb); } else if (fb) gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    if (pbo) gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
    return buf;
  }
  // a later-drawn active node with Button / BlockInputEvents over n's centre takes the touch: its path, else null
  function coverOf(n) {
    var r = worldBox(n); if (!r) return null;
    var cx = r.x + r.width / 2, cy = r.y + r.height / 2, after = false, cover = null;
    function within(a, d) { for (var x = d; x; x = x.parent) if (x === a) return true; return false; }
    walkScene(function (x) {
      if (x === n) { after = true; return; }
      if (!after || cover || !x.activeInHierarchy || within(n, x) || within(x, n) || x.is3DNode) return;
      if (!x.getComponent(cc.Button) && !(cc.BlockInputEvents && x.getComponent(cc.BlockInputEvents))) return;
      for (var y = x; y; y = y.parent) {
        if (!V3) { if (y.opacity === 0) return; continue; }
        var u = y.getComponent && cc.UIOpacity && y.getComponent(cc.UIOpacity); if (u && u.opacity === 0) return;
      }
      var q = worldBox(x); if (!q) return;
      if (q.width > 0 && q.height > 0 && cx >= q.x && cx <= q.x + q.width && cy >= q.y && cy <= q.y + q.height) cover = pathOf(x);
    });
    return cover;
  }
  function meshRenderers() {
    var out = [], kinds = [cc.MeshRenderer, cc.SkinnedMeshRenderer, cc.SkinnedMeshBatchRenderer].filter(Boolean);
    walkScene(function (n) { if (!n.activeInHierarchy) return; kinds.forEach(function (K) { var c = n.getComponent(K); if (c && c.enabled && out.indexOf(c) < 0) out.push(c); }); });
    return out;
  }
`;
