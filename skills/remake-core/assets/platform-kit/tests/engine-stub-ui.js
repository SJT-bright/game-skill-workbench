'use strict';
// Copy of ad-boost/ui-kit/test/engine-stub.js (AdBoostKit 1.2.0) for platform-kit parts/GameUIKit.js (生成时预防 P05).
// Added for GameUIKit: cc.Button (clickEvents, transition), env.tapAt(x, y) - a hit test like Cocos 2.4's touch
// dispatch (the topmost ACTIVE node under the point that listens for touches or has BlockInputEvents takes it;
// opacity does not matter, as in the engine) - and loadKit('24') loading parts/GameUIKit.js (GAMEUI_KIT_FILE
// overrides the file, e.g. to run the cases on a hand-written copy).
// Minimal Cocos engine stand-ins (2.4 and 3.x) for node tests. Only what AdBoostKit touches.
// Tweens do not run by themselves: call env.flush() to finish every pending tween (in order).
// A node that holds more than one render component (Sprite / Label / Graphics) throws, which is
// the Cocos 2.4 "one render component per node" rule made loud.
var fs = require('fs');
var path = require('path');
var vm = require('vm');

var RENDER = {Sprite: 1, Label: 1, Graphics: 1};

function makeClock() {
  var c = {t: 100000, timers: [], seq: 0};
  c.now = function () { return c.t; };
  c.setTimeout = function (fn, ms) { var id = ++c.seq; c.timers.push({id: id, at: c.t + (ms || 0), fn: fn}); return id; };
  c.clearTimeout = function (id) { c.timers = c.timers.filter(function (x) { return x.id !== id; }); };
  c.advance = function (ms) {
    var end = c.t + ms;
    for (;;) {
      c.timers.sort(function (a, b) { return a.at - b.at; });
      var next = c.timers[0];
      if (!next || next.at > end) break;
      c.timers.shift();
      c.t = next.at;
      next.fn();
    }
    c.t = end;
  };
  return c;
}

function makeEngine(kind) {
  var pending = [];
  var stats = {destroyed: 0, created: 0};
  function Color(r, g, b, a) { this.r = r; this.g = g; this.b = b; this.a = a === undefined ? 255 : a; }
  function Vec3(x, y, z) { this.x = x; this.y = y; this.z = z || 0; }
  function comp(name) {
    var C = function () { this.node = null; this.enabled = true; };
    C.__name = name;
    return C;
  }
  var cc = {Color: Color, Vec3: Vec3};
  ['Sprite', 'Label', 'LabelOutline', 'Graphics', 'BlockInputEvents', 'Canvas', 'UITransform', 'UIOpacity', 'Button'].forEach(function (n) { cc[n] = comp(n); });
  cc.Button.Transition = {NONE: 0, COLOR: 1, SPRITE: 2, SCALE: 3};
  cc.Sprite.SizeMode = {CUSTOM: 0, TRIMMED: 1, RAW: 2};
  cc.Sprite.Type = {SIMPLE: 0, SLICED: 1};
  cc.Label.HorizontalAlign = {CENTER: 1};
  cc.Label.VerticalAlign = {CENTER: 1};
  cc.Label.Overflow = {NONE: 0, CLAMP: 1, SHRINK: 2, RESIZE_HEIGHT: 3};
  cc.Graphics.LineCap = {ROUND: 1};
  cc.Graphics.prototype.clear = function () { this.ops = []; };
  ['rect', 'roundRect', 'arc', 'fill', 'stroke'].forEach(function (m) { cc.Graphics.prototype[m] = function () { (this.ops = this.ops || []).push(m); }; });
  cc.Layers = {Enum: {UI_2D: 1 << 25}};

  function Node(name) {
    this.name = name || 'Node'; this.children = []; this.parent = null; this._comps = [];
    this._valid = true; this.active = true; this._handlers = {}; this.zIndex = 0; this.angle = 0;
    this.x = 0; this.y = 0; this.width = 0; this.height = 0; this.opacity = 255; this.scale = 1;
    this.color = new Color(255, 255, 255); this.layer = 1;
    stats.created++;
  }
  Node.EventType = {TOUCH_END: 'touch-end'};
  Node.prototype.addChild = function (c) { c.parent = this; this.children.push(c); };
  Node.prototype.setContentSize = function (w, h) {
    if (typeof w === 'object') { h = w.height; w = w.width; }
    this.width = w; this.height = h;
  };
  Node.prototype.setPosition = function (x, y) { this.x = x; this.y = y; };
  Node.prototype.setScale = function (s) { this.scale = s; };
  Node.prototype.addComponent = function (C) {
    if (RENDER[C.__name] && this._comps.some(function (c) { return RENDER[c.constructor.__name]; })) {
      throw new Error('two render components on node ' + this.name + ': ' + C.__name);
    }
    var c = new C(); c.node = this; this._comps.push(c);
    if (C.__name === 'Label') { c.string = ''; c.fontSize = 20; c.lineHeight = 24; c.color = new Color(255, 255, 255); }
    if (C.__name === 'Sprite') { c.color = new Color(255, 255, 255); c.trim = true; c.type = 0; }   // engine defaults
    if (C.__name === 'UIOpacity') c.opacity = 255;
    if (C.__name === 'UITransform') {
      var node = this;
      c.setContentSize = function (w, h) { node.setContentSize(w, h); };
      Object.defineProperty(c, 'contentSize', {get: function () { return {width: node.width, height: node.height}; }});
      Object.defineProperty(c, 'width', {get: function () { return node.width; }, set: function (v) { node.width = v; }});
      Object.defineProperty(c, 'height', {get: function () { return node.height; }, set: function (v) { node.height = v; }});
    }
    return c;
  };
  Node.prototype.getComponent = function (C) {
    for (var i = 0; i < this._comps.length; i++) if (this._comps[i] instanceof C) return this._comps[i];
    return null;
  };
  Node.prototype.getComponentInChildren = function (C) {
    var c = this.getComponent(C); if (c) return c;
    for (var i = 0; i < this.children.length; i++) { var r = this.children[i].getComponentInChildren(C); if (r) return r; }
    return null;
  };
  Node.prototype.getChildByName = function (n) { return this.children.filter(function (c) { return c.name === n; })[0] || null; };
  Node.prototype.on = function (ev, fn) { (this._handlers[ev] = this._handlers[ev] || []).push(fn); };
  Node.prototype.emit = function (ev, arg) { (this._handlers[ev] || []).slice().forEach(function (f) { f(arg); }); };
  Node.prototype.setSiblingIndex = function (i) {
    var p = this.parent; if (!p) return;
    p.children.splice(p.children.indexOf(this), 1); p.children.splice(i, 0, this);
  };
  Node.prototype.destroy = function () {
    if (!this._valid) return;
    (function kill(n) { n._valid = false; stats.destroyed++; n.children.forEach(kill); })(this);
    if (this.parent) this.parent.children.splice(this.parent.children.indexOf(this), 1);
  };
  Object.defineProperty(Node.prototype, 'position', {get: function () { return {x: this.x, y: this.y, z: 0}; }});
  cc.Node = Node;
  cc.isValid = function (n) { return !!n && n._valid !== false; };
  cc.warn = function (m) { cc.warnings.push(m); };
  cc.warnings = [];

  function Tween(target) { this.target = target; this.steps = []; this.stopped = false; this.forever = false; }
  Tween.prototype.to = function (d, props) { this.steps.push({props: props}); return this; };
  Tween.prototype.by = function (d, props) { this.steps.push({by: props}); return this; };
  Tween.prototype.delay = function () { return this; };
  Tween.prototype.call = function (fn) { this.steps.push({fn: fn}); return this; };
  Tween.prototype.union = function () { return this; };
  Tween.prototype.repeatForever = function () { this.forever = true; return this; };
  Tween.prototype.start = function () { if (!this.forever) pending.push(this); return this; };
  Tween.prototype.stop = function () { this.stopped = true; return this; };
  cc.tween = function (target) { return new Tween(target); };

  var scene = new Node('Scene');
  var canvas = new Node('Canvas');
  canvas.addComponent(cc.Canvas);
  if (kind === '3x') canvas.addComponent(cc.UITransform);
  canvas.setContentSize(720, 1280);
  scene.addChild(canvas);
  // director.once(EVENT_BEFORE_DRAW): env.draw() stands for "the engine draws the next frame".
  var beforeDraw = [];
  cc.Director = {EVENT_BEFORE_DRAW: 'director_before_draw'};
  cc.director = {getScene: function () { return scene; },
    once: function (ev, fn) { if (ev === cc.Director.EVENT_BEFORE_DRAW) beforeDraw.push(fn); }};
  function draw() { var list = beforeDraw; beforeDraw = []; list.forEach(function (f) { f(); }); }
  cc.winSize = {width: 720, height: 1280};
  cc.view = {getVisibleSize: function () { return {width: 720, height: 1280}; }};

  function flush() {
    var guard = 0;
    while (pending.length && guard++ < 10000) {
      var t = pending.shift();
      if (t.stopped) continue;
      for (var i = 0; i < t.steps.length && !t.stopped; i++) {
        var s = t.steps[i];
        if (s.props) for (var k in s.props) {
          var v = s.props[k];
          if (k === 'scale' && v instanceof Vec3) t.target.setScale(v.x, v.y, v.z); else t.target[k] = v;
        }
        if (s.fn) s.fn();
      }
    }
  }
  function frame(w, h, name) { return {name: name || 'frame', getOriginalSize: function () { return {width: w, height: h}; }, getRect: function () { return {width: w, height: h}; }, originalSize: {width: w, height: h}, rect: {width: w, height: h}}; }

  // Real SpriteFrame behaviour that bit the trials:
  //  - a frame made without originalSize reports the WHOLE texture size (2.4 constructor and 3.x object);
  //  - an imported PNG is trimmed: rect = visible part, offset/originalSize = where it sat;
  //  - 2.4.15 BitmapFont keeps the parsed .fnt in _fntConfig (fntConfig is undefined).
  cc.Rect = function (x, y, w, h) { this.x = x; this.y = y; this.width = w; this.height = h; };
  cc.Vec2 = function (x, y) { this.x = x; this.y = y; };
  cc.Size = function (w, h) { this.width = w; this.height = h; };
  cc.Texture2D = function (w, h) { this.width = w; this.height = h; };
  if (kind === '24') {
    cc.SpriteFrame = function (tex, rect, rotated, offset, originalSize) {
      this._texture = tex; this._rect = rect; this._rotated = !!rotated;
      this._offset = offset || new cc.Vec2(0, 0);
      this._originalSize = originalSize || new cc.Size(tex.width, tex.height);
    };
    cc.SpriteFrame.prototype.getRect = function () { return this._rect; };
    cc.SpriteFrame.prototype.getOffset = function () { return this._offset; };
    cc.SpriteFrame.prototype.getOriginalSize = function () { return this._originalSize; };
    cc.SpriteFrame.prototype.getTexture = function () { return this._texture; };
    cc.SpriteFrame.prototype.isRotated = function () { return this._rotated; };
  } else {
    cc.SpriteFrame = function () { this.texture = null; this.rect = null; this.offset = new cc.Vec2(0, 0); this._orig = null; this.rotated = false; };
    Object.defineProperty(cc.SpriteFrame.prototype, 'originalSize', {
      get: function () { return this._orig || (this.texture ? new cc.Size(this.texture.width, this.texture.height) : null); },
      set: function (v) { this._orig = v; }});
    cc.SpriteFrame.prototype.reset = function (i) {
      if (i.texture) this.texture = i.texture;
      if (i.rect) this.rect = i.rect;
      if (i.offset) this.offset = i.offset;
      if (i.originalSize) this._orig = i.originalSize;
      if (i.isRotate !== undefined) this.rotated = i.isRotate;
    };
  }
  // A PNG of origW x origH whose visible content is the box [left, top, w, h], as the importer trims it:
  // the texture holds only the visible part.
  function trimmedFrame(origW, origH, left, top, w, h) {
    var tex = new cc.Texture2D(w, h);
    var off = new cc.Vec2(left + w / 2 - origW / 2, -(top + h / 2 - origH / 2));
    if (kind === '24') return new cc.SpriteFrame(tex, new cc.Rect(0, 0, w, h), false, off, new cc.Size(origW, origH));
    var f = new cc.SpriteFrame();
    f.reset({texture: tex, rect: new cc.Rect(0, 0, w, h), offset: off, originalSize: new cc.Size(origW, origH)});
    return f;
  }
  // What Creator 2.4 / 3.x actually load for a PNG imported with trimType auto: the texture is the WHOLE
  // picture, rect is the visible part inside it, offset / originalSize say where it sat.
  function importedFrame(origW, origH, left, top, w, h) {
    var tex = new cc.Texture2D(origW, origH);
    var off = new cc.Vec2(left + w / 2 - origW / 2, -(top + h / 2 - origH / 2));
    if (kind === '24') return new cc.SpriteFrame(tex, new cc.Rect(left, top, w, h), false, off, new cc.Size(origW, origH));
    var f = new cc.SpriteFrame();
    f.reset({texture: tex, rect: new cc.Rect(left, top, w, h), offset: off, originalSize: new cc.Size(origW, origH)});
    return f;
  }
  // The quad the engine draws for a SIMPLE sprite (copied from engine 2.4.15 assemblers/sprite/2d/simple.js
  // updateVerts; 3.8 2d/assembler/sprite/simple.ts is the same). The rect's pixels fill this box, so its
  // width / height against rect width / height is the "drawn ratio vs the picture's own ratio".
  function drawnBox(node) {
    var s = node.getComponent(cc.Sprite), f = s && s.spriteFrame;
    if (!f) return null;
    var cw = node.width, ch = node.height;
    if (s.trim) return {width: cw, height: ch};
    var o = kind === '24' ? f.getOriginalSize() : f.originalSize, r = kind === '24' ? f.getRect() : f.rect;
    return {width: cw * r.width / o.width, height: ch * r.height / o.height};
  }
  function drawnRatioErr(node) {
    var b = drawnBox(node), s = node.getComponent(cc.Sprite), f = s.spriteFrame, r = kind === '24' ? f.getRect() : f.rect;
    return Math.abs((b.width / b.height) / (r.width / r.height) - 1);
  }
  function bitmapFont(defs, pictureFrame) {
    var cfgF = {fontDefDictionary: defs};
    return kind === '24' ? {_fntConfig: cfgF, spriteFrame: pictureFrame} : {fntConfig: cfgF, spriteFrame: pictureFrame};
  }
  // ---- GameUIKit: touch dispatch. World box = parent positions and scales (anchor 0.5, no rotation).
  function activeIn(n) { for (var x = n; x; x = x.parent) if (!x.active || x._valid === false) return false; return true; }
  function worldScale(n) { return (n.parent ? worldScale(n.parent) : 1) * (typeof n.scale === 'number' ? n.scale : 1); }
  function worldPos(n) {
    if (!n.parent) return {x: n.x, y: n.y};
    var p = worldPos(n.parent), k = worldScale(n.parent);
    return {x: p.x + n.x * k, y: p.y + n.y * k};
  }
  function worldBox(n) {
    var p = worldPos(n), k = worldScale(n);
    return {x: p.x, y: p.y, width: n.width * k, height: n.height * k};
  }
  function drawOrder(n, out) {
    out.push(n);
    n.children.map(function (c, i) { return {c: c, i: i}; })
      .sort(function (a, b) { return (a.c.zIndex - b.c.zIndex) || (a.i - b.i); })
      .forEach(function (e) { drawOrder(e.c, out); });
    return out;
  }
  function hitNode(x, y) {
    var list = drawOrder(scene, []).filter(function (n) {
      if (!activeIn(n)) return false;
      if (!((n._handlers['touch-end'] || []).length || n.getComponent(cc.BlockInputEvents))) return false;
      var b = worldBox(n);
      return Math.abs(x - b.x) <= b.width / 2 && Math.abs(y - b.y) <= b.height / 2;
    });
    return list.length ? list[list.length - 1] : null;
  }
  function tapAt(x, y) { var n = hitNode(x, y); if (n) n.emit('touch-end'); return n; }
  function tapNode(n) { var b = worldBox(n); return tapAt(b.x, b.y); }
  return {cc: cc, canvas: canvas, scene: scene, flush: flush, frame: frame, trimmedFrame: trimmedFrame, bitmapFont: bitmapFont,
    tapAt: tapAt, tapNode: tapNode, hitNode: hitNode, worldBox: worldBox,
    importedFrame: importedFrame, drawnBox: drawnBox, drawnRatioErr: drawnRatioErr, draw: draw,
    stats: stats, pendingTweens: function () { return pending.length; }};
}

// ADB_KIT_DIR: run the same cases against another copy of the generated files (e.g. the pre-fix kit).
var KIT_DIR = process.env.ADB_KIT_DIR ? path.resolve(process.env.ADB_KIT_DIR) : path.resolve(__dirname, '..');
// Loads the GENERATED kit file into a fresh sandbox with a fake clock.
function loadKit(kind) {
  var env = makeEngine(kind);
  var clock = makeClock();
  var FakeDate = function () { return new Date(clock.now()); };
  FakeDate.now = clock.now;
  var sandbox = {console: console, Promise: Promise, Date: FakeDate, Math: Math, Object: Object, Array: Array,
    String: String, Error: Error, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, Infinity: Infinity};
  var src;
  if (kind === '24') {
    src = fs.readFileSync(process.env.GAMEUI_KIT_FILE ? path.resolve(process.env.GAMEUI_KIT_FILE)
      : path.join(__dirname, '..', 'parts', 'GameUIKit.js'), 'utf8');
    sandbox.cc = env.cc;
    sandbox.module = {exports: {}};
    vm.runInNewContext(src, sandbox, {filename: 'AdBoostKit.js'});
    env.Kit = sandbox.module.exports;
  } else {
    src = fs.readFileSync(path.join(KIT_DIR, 'cocos3x', 'AdBoostKit.ts'), 'utf8');
    // Strip the TypeScript-only lines; the body is plain ES5 by construction.
    src = src.replace(/^import \* as cc from 'cc';$/m, '')
      .replace(/^export .*$/gm, '')
      .replace(/\(globalThis as any\)/g, 'globalThis');
    if (/ as any|: any/.test(src)) throw new Error('unexpected TypeScript syntax in AdBoostKit.ts body');
    sandbox.cc = env.cc;
    sandbox.globalThis = sandbox;
    vm.runInNewContext(src, sandbox, {filename: 'AdBoostKit.ts'});
    env.Kit = sandbox.AdBoostKit;
  }
  env.clock = clock;
  // Resolves pending promise callbacks, then finishes tweens.
  env.settle = function () { return new Promise(function (r) { setImmediate(r); }).then(function () { env.flush(); }); };
  return env;
}

function find(node, name) {
  if (node.name === name) return node;
  for (var i = 0; i < node.children.length; i++) { var r = find(node.children[i], name); if (r) return r; }
  return null;
}
function renderCount(n) { return n._comps.filter(function (c) { return RENDER[c.constructor.__name]; }).length; }
function walk(n, fn) { fn(n); n.children.forEach(function (c) { walk(c, fn); }); }

module.exports = {loadKit: loadKit, find: find, renderCount: renderCount, walk: walk};
