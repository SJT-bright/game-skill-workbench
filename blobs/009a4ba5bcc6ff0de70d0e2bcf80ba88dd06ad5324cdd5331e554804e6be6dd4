// GameUIKit engine adapter for Cocos Creator 3.x (namespace from `import * as cc from 'cc'`), 生成时预防 A2 批.
// Source file: tools/make_gameuikit_3x.py puts the core of parts/GameUIKit.js and this adapter into parts-3x/GameUIKit.ts.
// Taken from ad-boost/ui-kit/src/adapter-3x.js (AdBoostKit 1.2.0) plus the GameUIKit-only functions at the end of E
// (button, wrapExisting, valueLabel, beforeDraw). One render component per node; opacity on UIOpacity, size on UITransform.
function makeGameUIAdapter3x(cc) {
  function rgb(c, a) { return new cc.Color(c[0], c[1], c[2], a === undefined ? 255 : a); }
  function ui(n) { return n.getComponent(cc.UITransform) || n.addComponent(cc.UITransform); }
  function op(n) { return n.getComponent(cc.UIOpacity) || n.addComponent(cc.UIOpacity); }
  function tw(n, key, t) {
    var bag = n.__uiTw || (n.__uiTw = {});
    if (bag[key]) { try { bag[key].stop(); } catch (_) {} }
    bag[key] = t;
    return t;
  }
  function walk(n, fn) { fn(n); var c = n.children || []; for (var i = 0; i < c.length; i++) walk(c[i], fn); }
  function measure(n, label) {
    try { if (typeof label.updateRenderData === 'function') label.updateRenderData(true); } catch (_) {}
    var s = ui(n).contentSize;
    return {width: s.width, height: s.height};
  }
  function canvasNode() {
    var s = cc.director.getScene();
    var c = s && s.getComponentInChildren ? s.getComponentInChildren(cc.Canvas) : null;
    return c ? c.node : s;
  }
  var E = {
    now: function () { return Date.now(); },
    later: function (ms, fn) { var id = setTimeout(fn, ms); return function () { clearTimeout(id); }; },
    warn: function (m) { if (cc.warn) cc.warn(m); else if (typeof console !== 'undefined') console.warn(m); },
    node: function (name, parent) {
      var n = new cc.Node(name);
      n.layer = parent && typeof parent.layer === 'number' ? parent.layer : cc.Layers.Enum.UI_2D;
      ui(n);
      if (parent) parent.addChild(n);
      return n;
    },
    size: function (n, w, h) { ui(n).setContentSize(w, h); },
    getSize: function (n) { var s = ui(n).contentSize; return {width: s.width, height: s.height}; },
    pos: function (n, x, y) { n.setPosition(x, y, 0); },
    getPos: function (n) { return {x: n.position.x, y: n.position.y}; },
    // SpriteFrame geometry (3.x API). makeFrame always sets offset and originalSize.
    frameInfo: function (f) {
      if (!f || !f.rect) return null;
      var r = f.rect, o = f.offset || {x: 0, y: 0}, s = f.originalSize || r;
      return {texture: f.texture, rect: {x: r.x, y: r.y, width: r.width, height: r.height},
        offset: {x: o.x, y: o.y}, orig: {width: s.width, height: s.height}, rotated: !!f.rotated};
    },
    makeFrame: function (tex, r, off, size) {
      var sf = new cc.SpriteFrame();
      var info = {texture: tex, rect: new cc.Rect(r.x, r.y, r.width, r.height), offset: new cc.Vec2(off.x, off.y),
        originalSize: new cc.Size(size.width, size.height), isRotate: false};
      if (typeof sf.reset === 'function') sf.reset(info);
      else { sf.texture = tex; sf.rect = info.rect; sf.offset = info.offset; sf.originalSize = info.originalSize; }
      return sf;
    },
    getInsets: function (f) { return [f.insetLeft || 0, f.insetTop || 0, f.insetRight || 0, f.insetBottom || 0]; },
    setInsets: function (f, i) { f.insetLeft = i[0]; f.insetTop = i[1]; f.insetRight = i[2]; f.insetBottom = i[3]; },
    isActive: function (n) { return !!n.active; },
    // Same rule as 2.4: rect is the truth; originalSize only when smaller than the texture (set on purpose).
    frameSize: function (f) {
      var r = f.rect, o = f.originalSize, tex = f.texture;
      if (!r || !r.width) return o ? {width: o.width, height: o.height} : {width: 0, height: 0};
      var whole = !!(tex && o && o.width >= tex.width && o.height >= tex.height && (r.width < o.width || r.height < o.height));
      var s = (!o || whole) ? r : o;
      return {width: s.width, height: s.height};
    },
    sprite: function (n, frame, sliced) {
      var s = n.addComponent(cc.Sprite);
      s.sizeMode = cc.Sprite.SizeMode.CUSTOM;
      if (sliced) s.type = cc.Sprite.Type.SLICED;
      s.spriteFrame = frame;
      return s;
    },
    setFrame: function (n, frame) { var s = n.getComponent(cc.Sprite); if (s) s.spriteFrame = frame; },
    children: function (n) { return n.children || []; },
    // Kit.fitTrim (only when a panel calls it; sprite() above does not set trim on 3.x yet - not engine-tested):
    // trim on stretches the rect over the node, trim off treats the node as originalSize (2d/assembler/sprite/simple.ts).
    fitTrim: function (n) {
      var s = n.getComponent && n.getComponent(cc.Sprite), f = s && s.spriteFrame, t = n.getComponent && n.getComponent(cc.UITransform);
      if (!f || !t || (s.type && s.type !== cc.Sprite.Type.SIMPLE) || !(t.width > 0) || !(t.height > 0)) return false;
      var r = f.rect, o = f.originalSize;
      if (!r || !o || !r.height || !o.height || (Math.abs(r.width - o.width) < 0.5 && Math.abs(r.height - o.height) < 0.5)) return false;
      var nr = t.width / t.height;
      var er = Math.abs(Math.log(nr / (r.width / r.height))), eo = Math.abs(Math.log(nr / (o.width / o.height)));
      if (Math.min(er, eo) > 0.1 || Math.abs(er - eo) < 0.01) return false;
      var want = er < eo;
      if (s.trim === want) return false;
      s.trim = want;
      return true;
    },
    label: function (n, fontSize, color, outline) {
      var l = n.addComponent(cc.Label);
      l.fontSize = fontSize; l.lineHeight = Math.round(fontSize * 1.25);
      l.horizontalAlign = cc.Label.HorizontalAlign.CENTER;
      l.verticalAlign = cc.Label.VerticalAlign.CENTER;
      l.color = rgb(color);
      if (outline) {
        if ('enableOutline' in l) { l.enableOutline = true; l.outlineColor = rgb(outline); l.outlineWidth = 3; }
        else if (cc.LabelOutline) { var o = n.addComponent(cc.LabelOutline); o.color = rgb(outline); o.width = 3; }
      }
      return l;
    },
    setLabel: function (n, label, text, maxW) {
      label.overflow = cc.Label.Overflow.NONE;
      label.string = text;
      var s = measure(n, label);
      if (s.width > maxW) {
        label.overflow = cc.Label.Overflow.RESIZE_HEIGHT;
        ui(n).width = maxW;
        s = measure(n, label);
      }
      if (!s.width) s = {width: Math.min(maxW, text.length * label.fontSize * 0.55), height: label.lineHeight};
      return s;
    },
    rect: function (n, w, h, color, alpha) {
      var g = n.getComponent(cc.Graphics) || n.addComponent(cc.Graphics);
      g.clear(); g.fillColor = rgb(color, alpha); g.rect(-w / 2, -h / 2, w, h); g.fill();
      ui(n).setContentSize(w, h);
    },
    roundRect: function (n, w, h, r, color, opacity) {
      var g = n.getComponent(cc.Graphics) || n.addComponent(cc.Graphics);
      g.clear(); g.fillColor = rgb(color, opacity); g.roundRect(-w / 2, -h / 2, w, h, r); g.fill();
      ui(n).setContentSize(w, h);
    },
    ring: function (n, r, lw, color) {
      var g = n.addComponent(cc.Graphics);
      g.lineWidth = lw; g.strokeColor = rgb(color); g.lineCap = cc.Graphics.LineCap.ROUND;
      g.arc(0, 0, r - lw / 2, 0, Math.PI * 1.5, true); g.stroke();
      ui(n).setContentSize(r * 2, r * 2);
    },
    blockInput: function (n) { n.addComponent(cc.BlockInputEvents); },
    onTap: function (n, fn) { n.on(cc.Node.EventType.TOUCH_END, fn); },
    setOpacity: function (n, v) { tw(n, 'opacity', null); op(n).opacity = v; },
    tweenOpacity: function (n, to, ms, cb) {
      tw(n, 'opacity', cc.tween(op(n)).to(ms / 1000, {opacity: to}).call(function () { if (cb) cb(); }).start());
    },
    setScale: function (n, s) { tw(n, 'scale', null); n.setScale(s, s, 1); },
    tweenScale: function (n, to, ms, cb) {
      tw(n, 'scale', cc.tween(n).to(ms / 1000, {scale: new cc.Vec3(to, to, 1)}).call(function () { if (cb) cb(); }).start());
    },
    tint: function (n, c) {
      walk(n, function (x) {
        if (x.name === 'Spinner') return;
        var r = x.getComponent(cc.Sprite) || x.getComponent(cc.Label);
        if (r) r.color = rgb(c, r.color ? r.color.a : 255);
      });
    },
    setActive: function (n, b) { n.active = !!b; },
    isValid: function (n) { return !!n && cc.isValid(n, true); },
    destroy: function (n) { if (cc.isValid(n, true)) n.destroy(); },
    toTop: function (n) { if (n.parent) n.setSiblingIndex(n.parent.children.length - 1); },
    spin: function (n) {
      if (n.__uiSpin) return;
      n.__uiSpin = cc.tween(n).by(0.9, {angle: -360}).union().repeatForever().start();
    },
    stopSpin: function (n) { if (n.__uiSpin) { try { n.__uiSpin.stop(); } catch (_) {} n.__uiSpin = null; n.angle = 0; } },
    sceneRoot: canvasNode,
    // ---- GameUIKit-only (same meaning as the 2.4 adapter)
    beforeDraw: function (fn) {
      if (cc.director && typeof cc.director.once === 'function' && cc.Director && cc.Director.EVENT_BEFORE_DRAW) cc.director.once(cc.Director.EVENT_BEFORE_DRAW, fn);
    },
    nameOf: function (n) { return (n && n.name) || 'node'; },
    isActiveInHierarchy: function (n) {
      if (typeof n.activeInHierarchy === 'boolean') return n.activeInHierarchy;
      for (var x = n; x; x = x.parent) if (x.active === false) return false;
      return true;
    },
    spriteFrameOf: function (n) { var s = n && n.getComponent && n.getComponent(cc.Sprite); return s ? s.spriteFrame || null : null; },
    // a Sprite on the button node itself (RAW / TRIMMED size mode) resizes the node with every animation frame
    lockSize: function (n) {
      var s = n.getComponent && n.getComponent(cc.Sprite);
      if (s && cc.Sprite.SizeMode && s.sizeMode !== cc.Sprite.SizeMode.CUSTOM) s.sizeMode = cc.Sprite.SizeMode.CUSTOM;
    },
    // original cc.Button: take its click events off (the kit handler is the only one) and turn SCALE into COLOR
    takeButton: function (n) {
      var b = cc.Button && n.getComponent && n.getComponent(cc.Button);
      if (!b) return [];
      var old = (b.clickEvents || []).slice();
      b.clickEvents = [];
      var T = cc.Button.Transition;
      if (T && b.transition === T.SCALE) b.transition = T.COLOR;
      return old;
    },
    labelOf: function (n) { return (n && n.getComponent && n.getComponent(cc.Label)) || null; },
    textWidth: function (n, label, text) {
      var t = ui(n), keep = {string: label.string, overflow: label.overflow, w: t.width, h: t.height};
      label.overflow = cc.Label.Overflow.NONE;
      label.string = text;
      var s = measure(n, label);
      label.string = keep.string; label.overflow = keep.overflow; t.setContentSize(keep.w, keep.h);
      return s.width;
    },
    fixLabel: function (n, label, w, h) {
      label.enableWrapText = false;
      label.overflow = cc.Label.Overflow.SHRINK;
      ui(n).setContentSize(w, h);
    },
    winSize: function () {
      var c = canvasNode();
      var t = c && c.getComponent ? c.getComponent(cc.UITransform) : null;
      if (t && t.width > 0) return {width: t.width, height: t.height};
      var v = cc.view.getVisibleSize();
      return {width: v.width, height: v.height};
    }
  };
  return E;
}
