// GameUIKit 1.0.0 (Cocos Creator 2.4) - platform-kit standard part, 生成时预防 P05.
// Every NEW or CHANGED popup, button, toast and bitmap number goes through this file; do not hand-write them.
// Copy unchanged to assets/tiktok-platform/GameUIKit.js (tiktok_finalize.py sync does it for new games):
//   var UI = require('GameUIKit');
//   var p = UI.popup(canvas, {panelFrame, titleFrame, closeFrame, keep: true});   // mask swallows taps, X >= 104 px
//   UI.button(node, this.onRevive.bind(this), {name: 'Revive'});                   // throws when the handler is missing
//   UI.wrapExisting(originalButtonNode, handler);                                   // English games: original buttons
//   setTimeout(p.guard(function () { ... }), 800);                                 // dropped once p closes / reopens
// Made from AdBoostKit 1.2.0 (ad-boost/ui-kit/src/kit-core.js + adapter-24.js): same popup, toast, digits, strips and
// fitTrim; without the ad parts (adButton, doubleCheckbox, runAd stay in AdBoostKit). New here: button, wrapExisting,
// popup.guard, close() always ends with the popup inactive, press feedback darkens instead of scaling.
'use strict';


// Core: engine-neutral (taken from AdBoostKit kit-core.js 1.2.0). E is the engine adapter at the end of this
// file. Every node draws at most one render component: pictures and text always sit on their own child nodes.
function createGameUIKit(E) {
  var Kit = {version: '1.0.0', kit: 'GameUIKit'};
  var cfg = {
    tapGuardMs: 500,          // repeated taps inside this window are ignored
    closeMinSize: 104,        // close button hit area is at least this many design pixels
    maskColor: [24, 22, 32],  // dim layer colour; set it from style.json (line colour)
    maskOpacity: 130,         // 0-255 alpha of the dim layer (about 51 %): the game underneath stays visible, not dull
    fadeMs: 160,
    toastMs: 2200,
    toastTop: 0.22,           // toast centre sits this fraction of the screen height below the top
    toastFontSize: 30,
    toastTextColor: [255, 255, 255],
    toastOutlineColor: [70, 52, 40],
    toastBgColor: [48, 40, 52],
    toastBgOpacity: 210,
    closeFrame: null,         // default close picture for popups
    toastFrame: null,         // optional toast background picture
    allowStretch: false,      // false: a picture given a box of another shape is fitted, not squashed
    sfx: null,                // optional function (eventId): the game's sound player (ui_popup_open, ui_popup_close, ui_button_tap)
    digitFrames: null,        // optional {light: {...}, dark: {...}} glyph maps for Kit.digits({tone})
    stackPopups: true,        // a popup opened over another one hides the lower mask and close button
    disabledText: 'Not available yet'   // toast for a tap on a disabled UI.button (opts.disabledText overrides)
  };
  var OFF_TINT = [110, 110, 110];
  var WHITE = [255, 255, 255];

  Kit.setup = function (o) {
    o = o || {};
    for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) cfg[k] = o[k];
    return Kit;
  };
  Kit.config = function () { return cfg; };

  function safeCall(fn, a, b) {
    if (typeof fn !== 'function') return undefined;
    try { return fn(a, b); } catch (e) { E.warn('GameUIKit callback failed: ' + (e && e.message)); }
    return undefined;
  }
  // Sound hook: does nothing without Kit.setup({sfx}); a throwing player never breaks the UI.
  function sfx(id) {
    if (typeof cfg.sfx !== 'function') return;
    try { cfg.sfx(id); } catch (e) { E.warn('GameUIKit sfx "' + id + '" failed: ' + (e && e.message)); }
  }
  Kit._sfx = sfx;
  function isThenable(v) { return !!v && typeof v.then === 'function'; }
  // Returns a wrapper that drops calls arriving within ms of the last accepted one.
  function guard(ms, fn) {
    var last = -Infinity;
    return function (ev) {
      var t = E.now();
      if (t - last < ms) return;
      last = t;
      fn(ev);
    };
  }
  Kit._guard = guard;
  // Box for a picture. Only one side given: the other follows the picture's own ratio (1.2.0; it used to
  // take the picture's own length, which squashed a caption given only a width - E2b/E3 check_label_x2).
  function frameSize(frame, w, h) {
    var s = frame ? E.frameSize(frame) : {width: 0, height: 0};
    if (w && !h && s.width > 0) return {width: w, height: Math.round(s.height * w / s.width)};
    if (h && !w && s.height > 0) return {width: Math.round(s.width * h / s.height), height: h};
    return {width: w || s.width, height: h || s.height};
  }
  // Kit.fitTrim(root): every SIMPLE sprite under root whose frame was trimmed by the importer gets the
  // Sprite.trim mode that matches its node's shape, so it draws at the picture's own ratio. Pictures the
  // kit makes are already right; this is for nodes a panel built itself (sized by getOriginalSize or
  // getRect). Kit.popup runs it once before the popup is first drawn (2.4). Returns how many it changed.
  Kit.fitTrim = function (root) {
    if (!root || typeof E.fitTrim !== 'function' || !E.isValid(root)) return 0;
    var changed = 0;
    (function visit(n) {
      if (E.fitTrim(n)) changed++;
      var c = E.children(n);
      for (var i = 0; i < c.length; i++) visit(c[i]);
    })(root);
    return changed;
  };
  function fitTrimSoon(root) {
    if (typeof E.beforeDraw === 'function') E.beforeDraw(function () { Kit.fitTrim(root); });
  }
  // Picture on its own child node. Returns the child. When both w and h are given and the picture
  // has another shape, it is fitted inside w x h keeping its own ratio (never squashed).
  function pictureChild(parent, name, frame, w, h) {
    var n = E.node(name, parent);
    var s = frameSize(frame, w, h);
    if (frame && w && h && !cfg.allowStretch) {
      var fs = E.frameSize(frame);
      if (fs.width > 0 && fs.height > 0) {
        var k = Math.min(w / fs.width, h / fs.height);
        if (Math.abs((fs.width / fs.height) / (w / h) - 1) > 0.02) s = {width: Math.round(fs.width * k), height: Math.round(fs.height * k)};
      }
    }
    if (frame) E.sprite(n, frame);
    E.size(n, s.width, s.height);
    return n;
  }
  // GameUIKit: press feedback darkens the picture for 90 ms and never scales, so the hit area under the finger
  // stays the same (AdBoostKit scales to 0.94).
  function pressFeedback(target) { pressTint(target); }

  // ---------------------------------------------------------------- popup
  Kit.popup = function (parent, o) {
    o = o || {};
    parent = parent || E.sceneRoot();
    var win = E.winSize();
    var state = 'open';
    var gen = 1;          // opening number: popup.guard() callbacks of an earlier opening are dropped
    var listeners = [];
    var root = E.node(o.name || 'GameUIPopup', parent);
    E.size(root, win.width, win.height);
    E.toTop(root);
    var mask = E.node('Mask', root);
    var maskAlpha = typeof o.maskOpacity === 'number' ? o.maskOpacity : cfg.maskOpacity;
    // The dim level lives in the fill colour's alpha; the node fades 0 -> 255 on top of it.
    // (Graphics does not follow node opacity the same way in every engine version.)
    E.rect(mask, win.width * 3, win.height * 3, o.maskColor || cfg.maskColor, maskAlpha);
    E.blockInput(mask);
    var maskTarget = 255;
    var panel;
    if (o.panelFrame && (o.panelSliced || o.panelInsets)) {
      // nine-slice: the game's own panel stretched to width x height without squashing its corners.
      // panelInsets [left, top, right, bottom] in picture pixels (default: the frame's own insets, or 30 %).
      var pf = E.frameSize(o.panelFrame);
      var ins = o.panelInsets || E.getInsets(o.panelFrame);
      if (!ins || !(ins[0] || ins[1] || ins[2] || ins[3])) {
        ins = [Math.round(pf.width * 0.3), Math.round(pf.height * 0.3), Math.round(pf.width * 0.3), Math.round(pf.height * 0.3)];
      }
      E.setInsets(o.panelFrame, ins);
      panel = E.node('Panel', root);
      E.sprite(panel, o.panelFrame, true);
      E.size(panel, o.width || pf.width, o.height || pf.height);
    } else {
      panel = pictureChild(root, 'Panel', o.panelFrame, o.width, o.height);
    }
    var ps = E.getSize(panel);
    var body = E.node('Body', panel);
    E.size(body, ps.width, ps.height);
    var titleNode = null;
    var closeFrameT = o.closeFrame === false ? null : (o.closeFrame || cfg.closeFrame);
    if (o.titleFrame) {
      var tw0 = o.titleWidth, th0 = o.titleHeight;
      if (!tw0 && !th0 && closeFrameT && o.titleFit !== false) {
        // keep the title clear of the close button's hit area on both sides (was titleFit() in every panel)
        var tfs = E.frameSize(o.titleFrame), cfs = E.frameSize(closeFrameT);
        var cHit = Math.max(cfg.closeMinSize, o.closeSize || cfs.width, o.closeSize || cfs.height);
        var ci0 = typeof o.closeInset === 'number' ? o.closeInset : 6;
        var maxTW = ps.width - 2 * (cHit + ci0) - 8;
        if (maxTW > 0 && tfs.width > maxTW) { tw0 = Math.round(maxTW); th0 = Math.round(tfs.height * maxTW / tfs.width); }
      }
      titleNode = pictureChild(panel, 'Title', o.titleFrame, tw0, th0);
      var ts = E.getSize(titleNode);
      var inset = typeof o.titleInset === 'number' ? o.titleInset : Math.round(ps.height * 0.05);
      E.pos(titleNode, 0, ps.height / 2 - ts.height / 2 - inset + (o.titleOffsetY || 0));
    }
    var closeNode = null;
    var closeFrame = o.closeFrame === false ? null : (o.closeFrame || cfg.closeFrame);
    if (closeFrame) {
      var cs = frameSize(closeFrame, o.closeSize, o.closeSize);
      var hit = Math.max(cfg.closeMinSize, cs.width, cs.height);
      closeNode = E.node('Close', panel);
      E.size(closeNode, hit, hit);
      pictureChild(closeNode, 'Icon', closeFrame, cs.width, cs.height);
      var ci = typeof o.closeInset === 'number' ? o.closeInset : 6;
      E.pos(closeNode, ps.width / 2 - hit / 2 - ci, ps.height / 2 - hit / 2 - ci);
      E.onTap(closeNode, guard(cfg.tapGuardMs, function () {
        if (state !== 'open') return;
        pressFeedback(closeNode);
        tapClose();
      }));
    }
    // X (and mask, when closeOnMask) tap: the owner's handler from close(fn) if one was set,
    // otherwise the popup closes itself.
    var closeHandler = typeof o.onCloseTap === 'function' ? o.onCloseTap : null;
    function tapClose() { if (closeHandler) safeCall(closeHandler, handle); else handle.close(); }
    if (o.closeOnMask) E.onTap(mask, guard(cfg.tapGuardMs, function () { if (state === 'open') tapClose(); }));

    function playIn() {
      sfx('ui_popup_open');
      E.setOpacity(mask, 0);
      E.tweenOpacity(mask, maskTarget, cfg.fadeMs);
      E.setScale(panel, 0.92);
      E.setOpacity(panel, 0);
      E.tweenOpacity(panel, 255, cfg.fadeMs);
      E.tweenScale(panel, 1, cfg.fadeMs);
    }
    var handle = {
      root: root, body: body, panel: panel, mask: mask, titleNode: titleNode, closeNode: closeNode, maskAlpha: maskAlpha,
      isOpen: function () { return state === 'open' && E.isValid(root); },
      onClose: function (fn) { if (typeof fn === 'function') listeners.push(fn); return handle; },
      // guard(cb): wrap a timer / network / ad callback that belongs to this popup. It runs only while this
      // same opening of the popup is still open; after close() or a reopen it is dropped (a late callback
      // never writes into a closed or rebuilt page).
      guard: function (cb) {
        if (typeof cb !== 'function') throw new Error('GameUIKit popup.guard: not a function');
        var mine = gen;
        return function (a, b, c) {
          if (mine !== gen || state !== 'open' || !E.isValid(root)) return undefined;
          return cb(a, b, c);
        };
      },
      // close()   : closes once - fades out, then removes only this popup (hides it when keep:true).
      // close(fn) : sets what the X does. fn(handle) runs on X tap instead of the self-close, so the
      //             owner's controller decides (it may refuse while an ad runs). Does not close now.
      close: function (fn) {
        if (typeof fn === 'function') { closeHandler = fn; return handle; }
        if (state !== 'open') return false;
        state = 'closing';
        unstack(handle);
        sfx('ui_popup_close');
        E.tweenOpacity(mask, 0, cfg.fadeMs);
        E.tweenOpacity(panel, 0, cfg.fadeMs);
        gen++;   // every guard() callback made while it was open is dropped from now on
        E.tweenScale(panel, 0.92, cfg.fadeMs, function () {
          state = 'closed';
          // GameUIKit: always inactive at the end of the fade, so a transparent popup never keeps taking taps
          // (花园守卫者: faded to opacity 0 but still active, the page underneath could not be tapped)
          E.setActive(root, false);
          if (!o.keep) E.destroy(root);
          var list = listeners; listeners = [];
          for (var i = 0; i < list.length; i++) safeCall(list[i], handle);
        });
        return true;
      },
      // Only for keep:true popups: show the same nodes again instead of rebuilding them.
      open: function () {
        if (!o.keep || state === 'open' || !E.isValid(root)) return false;
        state = 'open';
        gen++;
        E.setActive(root, true);
        E.toTop(root);
        playIn();
        stack(handle, o);
        fitTrimSoon(root);
        return true;
      }
    };
    playIn();
    stack(handle, o);
    fitTrimSoon(root);   // after the panel has built its content, before the first frame shows it
    return handle;
  };

  // Popup over popup: only the top one shows its dim layer and close button (two masks look much
  // darker, and a lower X stays visible but cannot be tapped). Only what the stack hid is restored.
  var popupStack = [];
  function stack(h, o) {
    if (!cfg.stackPopups || o.stack === false) return;
    popupStack.push(h);
    restack();
  }
  function unstack(h) {
    var i = popupStack.indexOf(h);
    if (i < 0) return;
    popupStack.splice(i, 1);
    restack();
  }
  function restack() {
    popupStack = popupStack.filter(function (h) { return h.isOpen(); });
    for (var i = 0; i < popupStack.length; i++) {
      var h = popupStack[i], top = i === popupStack.length - 1;
      [['mask', h.mask], ['close', h.closeNode]].forEach(function (pair) {
        var n = pair[1], key = '__uiStackHid_' + pair[0];
        if (!n || !E.isValid(n)) return;
        if (!top && E.isActive(n)) { E.setActive(n, false); h[key] = true; }
        else if (top && h[key]) { E.setActive(n, true); h[key] = false; }
      });
    }
  }
  Kit.openPopups = function () { restack(); return popupStack.slice(); };

  // ---------------------------------------------------------------- strips, atlases, bitmap fonts
  // Real-engine traps handled here (all seen in trials):
  //  1. the engine trims transparent borders of a PNG: the frame's rect covers only the visible part
  //     and offset/originalSize describe where it sat, so cells must be mapped back, not cut from getRect();
  //  2. new SpriteFrame(tex, rect) without originalSize reports the WHOLE picture size: every cell gets an
  //     explicit originalSize (and offset) here;
  //  3. Cocos 2.4.15 keeps the parsed BitmapFont in _fntConfig, not fntConfig.
  // Cell boxes are in pixels of the ORIGINAL picture, x from the left, y from the top.
  function cellFrame(info, cx, cy, cw, ch) {
    var tl = (info.orig.width - info.rect.width) / 2 + info.offset.x;
    var tt = (info.orig.height - info.rect.height) / 2 - info.offset.y;
    var x0 = Math.max(cx, tl), x1 = Math.min(cx + cw, tl + info.rect.width);
    var y0 = Math.max(cy, tt), y1 = Math.min(cy + ch, tt + info.rect.height);
    if (x1 <= x0 || y1 <= y0) { x0 = tl; x1 = tl + 1; y0 = tt; y1 = tt + 1; }   // fully trimmed cell: 1 px, still cw x ch
    return E.makeFrame(info.texture,
      {x: info.rect.x + (x0 - tl), y: info.rect.y + (y0 - tt), width: x1 - x0, height: y1 - y0},
      {x: (x0 + x1) / 2 - (cx + cw / 2), y: -((y0 + y1) / 2 - (cy + ch / 2))},
      {width: cw, height: ch});
  }
  // Kit.stripFrames(frame, {count | chars, rects, rows})
  //   count n          : n equal cells side by side -> [frame, ...]
  //   chars 'abc'      : one equal cell per character -> {'a': frame, ...}
  //   rects [[x,y,w,h]]: explicit cells (e.g. from scripts/art/cut_strip.py for glyphs of different widths)
  //   rows r           : the strip has r rows of equal height (a 6-frame chest strip is 1 row)
  //   narrow ':/'      : (1.2.0, off by default) with chars, these equal cells are cut narrower around their
  //                      centre so the clock reads "05:00", not "05 :00". A string uses NARROW widths
  //                      (fraction of the cell); {':': 0.5} sets them. Not used with explicit rects.
  var NARROW = {':': 0.5, '/': 0.72, '.': 0.45, ',': 0.45, '-': 0.7};
  Kit.stripFrames = function (frame, o) {
    o = o || {};
    var info = E.frameInfo(frame);
    if (!info) { E.warn('GameUIKit.stripFrames: not a SpriteFrame'); return o.chars ? {} : []; }
    if (info.rotated) E.warn('GameUIKit.stripFrames: rotated atlas frames are not supported, export the strip as its own PNG');
    var chars = o.chars ? String(o.chars) : null;
    var rects = o.rects;
    if (!rects) {
      var n = chars ? chars.length : (o.count || 1);
      var rows = o.rows || 1, perRow = Math.ceil(n / rows);
      var cw = info.orig.width / perRow, ch = info.orig.height / rows;
      rects = [];
      var narrow = chars && o.narrow ? o.narrow : null;
      for (var i = 0; i < n; i++) {
        var cx = (i % perRow) * cw, k = 1;
        if (narrow) {
          var c0 = chars.charAt(i);
          if (typeof narrow === 'string') k = narrow.indexOf(c0) >= 0 ? (NARROW[c0] || 0.6) : 1;
          else if (typeof narrow[c0] === 'number') k = narrow[c0];
          if (!(k > 0 && k <= 1)) k = 1;
        }
        rects.push([cx + cw * (1 - k) / 2, Math.floor(i / perRow) * ch, cw * k, ch]);
      }
    }
    var out = chars ? {} : [];
    for (var k = 0; k < rects.length; k++) {
      var r = rects[k];
      var f = cellFrame(info, r[0], r[1], r[2], r[3]);
      if (chars) out[chars.charAt(k)] = f; else out.push(f);
    }
    return out;
  };
  // Kit.fontFrames(bitmapFont[, chars]) -> {'0': frame, ...} from a .fnt BitmapFont asset (2.4 and 3.x).
  Kit.fontFrames = function (font, chars) {
    var cfgF = font && (font._fntConfig || font.fntConfig);
    var frame = font && (font.spriteFrame || font._spriteFrame);
    if (!cfgF || !cfgF.fontDefDictionary || !frame) { E.warn('GameUIKit.fontFrames: font has no parsed config or picture'); return {}; }
    var info = E.frameInfo(frame);
    var defs = cfgF.fontDefDictionary, out = {};
    for (var code in defs) {
      if (!Object.prototype.hasOwnProperty.call(defs, code)) continue;
      var ch = String.fromCharCode(+code);
      if (chars && String(chars).indexOf(ch) < 0) continue;
      var r = defs[code].rect;
      if (!r || !r.width || !r.height) continue;
      out[ch] = cellFrame(info, r.x, r.y, r.width, r.height);
    }
    return out;
  };
  // Light / dark digit sets: Kit.setup({digitFrames: {light: {...}, dark: {...}}}), Kit.digits(p, {tone: 'dark'}).
  // Kit.toneFor([r,g,b]) -> 'dark' on light backgrounds, 'light' on dark ones.
  Kit.toneFor = function (rgb) {
    var l = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255;
    return l > 0.6 ? 'dark' : 'light';
  };

  // ---------------------------------------------------------------- toast
  var toastState = {node: null, bg: null, label: null, timer: null, text: ''};
  function ensureToast() {
    var t = toastState;
    if (t.node && E.isValid(t.node)) return t;
    var root = E.sceneRoot();
    t.node = E.node('GameUIToast', root);
    t.bg = E.node('Bg', t.node);
    if (cfg.toastFrame) E.sprite(t.bg, cfg.toastFrame, true);
    t.labelNode = E.node('Text', t.node);
    t.label = E.label(t.labelNode, cfg.toastFontSize, cfg.toastTextColor, cfg.toastOutlineColor);
    return t;
  }
  // One toast at a time; a new text replaces the old one and restarts the timer.
  // Toasts never take touches. Show sentences only: numbers belong in Kit.digits.
  Kit.toast = function (text, o) {
    if (!text) return null;
    o = o || {};
    text = String(text);
    if (/[^\x00-\x7F]/.test(text)) E.warn('GameUIKit.toast: non-ASCII text shown in game: ' + text);
    var t = ensureToast();
    var win = E.winSize();
    var maxW = Math.min(win.width * 0.84, 640);
    E.setActive(t.node, true);
    E.toTop(t.node);
    var sz = E.setLabel(t.labelNode, t.label, text, maxW);
    var bw = sz.width + 56, bh = sz.height + 30;
    E.size(t.node, bw, bh);
    if (cfg.toastFrame) E.size(t.bg, bw, bh);
    else E.roundRect(t.bg, bw, bh, Math.min(bh / 2, 28), cfg.toastBgColor, cfg.toastBgOpacity);
    E.pos(t.node, 0, win.height * (0.5 - cfg.toastTop));
    if (t.timer) t.timer();
    E.setOpacity(t.node, 0);
    E.tweenOpacity(t.node, 255, 120);
    t.text = text;
    var ms = typeof o.ms === 'number' ? o.ms : cfg.toastMs;
    t.timer = E.later(ms, function () {
      t.timer = null;
      if (!E.isValid(t.node)) return;
      E.tweenOpacity(t.node, 0, 200, function () { if (E.isValid(t.node)) E.setActive(t.node, false); t.text = ''; });
    });
    return t.node;
  };
  Kit.toastText = function () { return toastState.node && E.isValid(toastState.node) ? toastState.text : ''; };

  // ---------------------------------------------------------------- bitmap digits
  Kit.digits = function (parent, o) {
    o = o || {};
    var sets = cfg.digitFrames || {};
    var frames = o.atlasFrames || sets[o.tone || 'light'] || sets.light || sets.dark || {};
    var n = E.node(o.name || 'Digits', parent);
    var glyphs = [];
    var value = '';
    var spacing0 = o.spacing || 0, spacing = spacing0;
    var align = o.align || 'center';
    function frameFor(ch) {
      if (Array.isArray(frames)) return /[0-9]/.test(ch) ? frames[+ch] : null;
      return frames[ch] || null;
    }
    // Reuses glyph nodes: changing the value never rebuilds the whole number.
    function set(v) {
      value = String(v);
      spacing = spacing0;
      var x = 0, used = 0, maxH = 0, placed = [];
      for (var i = 0; i < value.length; i++) {
        var f = frameFor(value.charAt(i));
        if (!f) { E.warn('GameUIKit.digits: no picture for "' + value.charAt(i) + '"'); continue; }
        var g = glyphs[used];
        if (!g) { g = E.node('G' + used, n); E.sprite(g, f); glyphs.push(g); }
        else { E.setFrame(g, f); E.setActive(g, true); }
        var fs = E.frameSize(f);
        var h = o.height || fs.height;
        var w = fs.width * (h / (fs.height || 1));
        E.size(g, w, h);
        placed.push({node: g, w: w, h: h});
        x += w + (placed.length > 1 ? spacing : 0);
        if (h > maxH) maxH = h;
        used++;
      }
      for (var j = used; j < glyphs.length; j++) E.setActive(glyphs[j], false);
      var total = x;
      // maxWidth: a long number shrinks evenly (glyph sizes, gaps) instead of running out of its box
      if (o.maxWidth && total > o.maxWidth) {
        var k = o.maxWidth / total, sp = spacing * k;
        total = 0; maxH = 0;
        for (var q = 0; q < placed.length; q++) {
          placed[q].w *= k; placed[q].h *= k;
          E.size(placed[q].node, placed[q].w, placed[q].h);
          total += placed[q].w + (q > 0 ? sp : 0);
          if (placed[q].h > maxH) maxH = placed[q].h;
        }
        spacing = sp;
      }
      var start = align === 'left' ? 0 : (align === 'right' ? -total : -total / 2);
      var cur = start;
      for (var k = 0; k < placed.length; k++) {
        E.pos(placed[k].node, cur + placed[k].w / 2, 0);
        cur += placed[k].w + spacing;
      }
      E.size(n, total, maxH);
      return handle;
    }
    var handle = {node: n, set: set, value: function () { return value; }, glyphCount: function () { return glyphs.length; }};
    set(o.value === undefined ? 0 : o.value);
    return handle;
  };


  // ---------------------------------------------------------------- buttons (GameUIKit only)
  // UI.button(node, handler, opts) turns an existing node into a button that cannot go wrong in the usual ways:
  //  - handler must be a function: a missing or misspelt handler throws HERE, when the page is first built,
  //    instead of a button that silently does nothing (割草 revive button bound to a function that did not exist);
  //  - the hit area is the node's own box, fixed when the button is made: opts.width/height, else the node size,
  //    else the visible picture of opts.art / the node's Sprite. Animated children (glow, sparkle, idle bounce) never
  //    change it, and press feedback only darkens the picture, it never scales (挪车冲冲冲: an animated frame on the
  //    button node grew the hit area; a press-scale shrank it under the finger);
  //  - taps within opts.guardMs (default 500 ms) of the last accepted one are ignored (double rewards, two popups);
  //  - setEnabled(false): a tap shows opts.disabledText as a toast (and calls opts.onDisabledTap), never nothing;
  //  - opts.close: true makes the hit area at least closeMinSize (104) on both sides (最强推球: a 32 x 32 close X).
  // Returns {node, art, tap, setEnabled, isEnabled, setHandler, dispose}.
  var PRESS_TINT = [200, 200, 200];
  function boxOf(node, art) {
    var s = E.getSize(node);
    if (s.width > 0 && s.height > 0) return s;
    var a = art || node;
    var f = E.spriteFrameOf(a);
    if (f) { var fs = E.frameSize(f); if (fs.width > 0 && fs.height > 0) return fs; }
    return E.getSize(a);
  }
  function pressTint(target) {
    if (!target || !E.isValid(target)) return;
    E.tint(target, PRESS_TINT);
    E.later(90, function () { if (E.isValid(target)) E.tint(target, WHITE); });
  }
  Kit.button = function (node, handler, o) {
    o = o || {};
    if (!node || !E.isValid(node)) throw new Error('GameUIKit.button: no valid node' + (o.name ? ' for ' + o.name : ''));
    if (typeof handler !== 'function') {
      throw new Error('GameUIKit.button: handler of "' + (o.name || E.nameOf(node)) + '" is ' + (handler === null ? 'null' : typeof handler) +
        ' - pass the function itself (this.onRevive.bind(this)), not a name or an undefined method');
    }
    var art = o.art || null;
    var box = {width: o.width || 0, height: o.height || 0};
    if (!box.width || !box.height) { var b0 = boxOf(node, art); box.width = box.width || b0.width; box.height = box.height || b0.height; }
    if (o.close) { box.width = Math.max(box.width, cfg.closeMinSize); box.height = Math.max(box.height, cfg.closeMinSize); }
    E.size(node, box.width, box.height);
    E.setScale(node, 1);
    var enabled = o.enabled !== false, fn = handler, disposed = false;
    var feedback = art || node;
    function paint() { if (E.isValid(feedback)) E.tint(feedback, enabled ? WHITE : OFF_TINT); }
    var handle = {
      node: node, art: art,
      isEnabled: function () { return enabled; },
      setEnabled: function (b) { enabled = !!b; paint(); return handle; },
      setHandler: function (f) {
        if (typeof f !== 'function') throw new Error('GameUIKit.button.setHandler: not a function');
        fn = f; return handle;
      },
      tap: function () { onTap(); },
      dispose: function () { disposed = true; }
    };
    var onTap = guard(typeof o.guardMs === 'number' ? o.guardMs : cfg.tapGuardMs, function () {
      if (disposed || !E.isValid(node) || !E.isActiveInHierarchy(node)) return;
      if (!enabled) {
        if (o.disabledText !== '') Kit.toast(o.disabledText || cfg.disabledText);
        safeCall(o.onDisabledTap, handle);
        return;
      }
      pressTint(feedback);
      sfx(o.sfx || 'ui_button_tap');
      try { fn(handle); } catch (e) { E.warn('GameUIKit.button "' + (o.name || E.nameOf(node)) + '" handler failed: ' + (e && e.message)); }
    });
    E.onTap(node, onTap);
    // a Sprite on the button node itself stops resizing the node with each animation frame (sizeMode CUSTOM)
    E.lockSize(node);
    paint();
    return handle;
  };
  // UI.wrapExisting(node, handler, opts): the same guarantees for a button that came with the original game (a prefab
  // or scene node with cc.Button). Its old click events are taken off (stored on handle.oldClickEvents) so the tap runs
  // exactly once, a SCALE transition becomes COLOR, and the hit area becomes at least the visible picture. The
  // prefab is not rebuilt. English games: every original button the AI touches goes through this.
  Kit.wrapExisting = function (node, handler, o) {
    o = o || {};
    if (typeof handler !== 'function') {
      throw new Error('GameUIKit.wrapExisting: handler of "' + (o.name || (node && E.nameOf(node))) + '" is ' + typeof handler);
    }
    if (!node || !E.isValid(node)) throw new Error('GameUIKit.wrapExisting: no valid node');
    var old = E.takeButton(node);
    var opts = {};
    for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) opts[k] = o[k];
    if (!opts.width && !opts.height) {
      var own = E.getSize(node);
      var f = E.spriteFrameOf(opts.art || node);
      var fs = f ? E.frameSize(f) : {width: 0, height: 0};
      opts.width = Math.max(own.width, fs.width);
      opts.height = Math.max(own.height, fs.height);
    }
    var h = Kit.button(node, handler, opts);
    h.oldClickEvents = old;
    return h;
  };
  Kit._reset = function () { popupStack = []; toastState = {node: null, bg: null, label: null, timer: null, text: ''}; };
  return Kit;
}

// Engine adapter for Cocos Creator 2.4 (global cc). One render component per node.
function makeGameUIAdapter24(cc) {
  var zCounter = 20000;
  function rgb(c, a) { return new cc.Color(c[0], c[1], c[2], a === undefined ? 255 : a); }
  function tw(n, key, t) {
    var bag = n.__uiTw || (n.__uiTw = {});
    if (bag[key]) { try { bag[key].stop(); } catch (_) {} }
    bag[key] = t;
    return t;
  }
  function walk(n, fn) { fn(n); var c = n.children || []; for (var i = 0; i < c.length; i++) walk(c[i], fn); }
  // Which box a frame's node stands for (see frameSize): its rect, or its originalSize (atlas / strip cell).
  function sizeOf(f) {
    var r = f.getRect ? f.getRect() : null, o = f.getOriginalSize ? f.getOriginalSize() : null;
    var tex = f.getTexture ? f.getTexture() : f._texture;
    if (!r || !r.width) return o ? {width: o.width, height: o.height, byRect: false} : {width: 0, height: 0, byRect: true};
    var whole = !!(tex && o && o.width >= tex.width && o.height >= tex.height && (r.width < o.width || r.height < o.height));
    var byRect = !o || whole;
    var s = byRect ? r : o;
    return {width: s.width, height: s.height, byRect: byRect};
  }
  // Cocos 2.4 Sprite.trim (engine assembler sprite/2d/simple.js, the same in 3.8):
  //   trim on  - the rect (visible part) is stretched over the whole node;
  //   trim off - the node stands for originalSize and the rect sits inside it at its offset.
  // So a node sized to the rect needs trim on, and a node sized to originalSize needs trim off. With
  // trim on and an originalSize-sized node, a trimmed picture is stretched (strip glyphs, E2a/E2b);
  // with trim off and a rect-sized node it is squashed (E1 fitTrim). trimFor picks the matching mode.
  function trimFor(f) { return !f || sizeOf(f).byRect; }
  function simple(s) { return !s.type || s.type === cc.Sprite.Type.SIMPLE; }
  function measure(n, label) {
    try {
      if (typeof label._forceUpdateRenderData === 'function') label._forceUpdateRenderData(true);
      else if (typeof label._updateRenderData === 'function') label._updateRenderData(true);
    } catch (_) {}
    return {width: n.width, height: n.height};
  }
  var E = {
    now: function () { return Date.now(); },
    later: function (ms, fn) { var id = setTimeout(fn, ms); return function () { clearTimeout(id); }; },
    warn: function (m) { if (cc.warn) cc.warn(m); else if (typeof console !== 'undefined') console.warn(m); },
    node: function (name, parent) { var n = new cc.Node(name); if (parent) parent.addChild(n); return n; },
    size: function (n, w, h) { n.setContentSize(w, h); },
    getSize: function (n) { return {width: n.width, height: n.height}; },
    pos: function (n, x, y) { n.setPosition(x, y); },
    getPos: function (n) { return {x: n.x, y: n.y}; },
    // SpriteFrame geometry (2.4 API). makeFrame always passes offset and originalSize.
    frameInfo: function (f) {
      if (!f || typeof f.getRect !== 'function') return null;
      var r = f.getRect(), o = f.getOffset ? f.getOffset() : {x: 0, y: 0}, s = f.getOriginalSize ? f.getOriginalSize() : r;
      return {texture: f.getTexture ? f.getTexture() : f._texture, rect: {x: r.x, y: r.y, width: r.width, height: r.height},
        offset: {x: o.x, y: o.y}, orig: {width: s.width, height: s.height}, rotated: !!(f.isRotated && f.isRotated())};
    },
    makeFrame: function (tex, r, off, size) {
      return new cc.SpriteFrame(tex, new cc.Rect(r.x, r.y, r.width, r.height), false, new cc.Vec2(off.x, off.y), new cc.Size(size.width, size.height));
    },
    getInsets: function (f) { return [f.insetLeft || 0, f.insetTop || 0, f.insetRight || 0, f.insetBottom || 0]; },
    setInsets: function (f, i) { f.insetLeft = i[0]; f.insetTop = i[1]; f.insetRight = i[2]; f.insetBottom = i[3]; },
    isActive: function (n) { return !!n.active; },
    // Size a frame is drawn at. getRect() is the truth; getOriginalSize() only when it was set on
    // purpose (atlas / trimmed cell, smaller than the texture). A frame cut with new SpriteFrame(tex, rect)
    // reports the WHOLE texture as original size, which drew digits and close buttons many times too big.
    frameSize: function (f) {
      var s = sizeOf(f);
      return {width: s.width, height: s.height};
    },
    // trim follows frameSize: the kit sizes every node from frameSize, so the picture keeps its shape.
    sprite: function (n, frame, sliced) {
      var s = n.addComponent(cc.Sprite);
      s.sizeMode = cc.Sprite.SizeMode.CUSTOM;
      if (sliced) s.type = cc.Sprite.Type.SLICED;
      s.spriteFrame = frame;
      if (!sliced) s.trim = trimFor(frame);
      return s;
    },
    setFrame: function (n, frame) {
      var s = n.getComponent(cc.Sprite);
      if (!s) return;
      s.spriteFrame = frame;
      if (frame && simple(s)) s.trim = trimFor(frame);
    },
    children: function (n) { return n.children || []; },
    // Kit.fitTrim: a SIMPLE sprite with a trimmed frame gets the trim mode that matches its node's shape
    // (rect-shaped node -> on, originalSize-shaped node -> off). Returns true when it changed something.
    fitTrim: function (n) {
      var s = n.getComponent && n.getComponent(cc.Sprite), f = s && s.spriteFrame;
      if (!f || !simple(s) || !(n.width > 0) || !(n.height > 0) || !f.getRect || !f.getOriginalSize) return false;
      var r = f.getRect(), o = f.getOriginalSize();
      if (!r || !o || !r.height || !o.height || (Math.abs(r.width - o.width) < 0.5 && Math.abs(r.height - o.height) < 0.5)) return false;
      var nr = n.width / n.height;
      var er = Math.abs(Math.log(nr / (r.width / r.height))), eo = Math.abs(Math.log(nr / (o.width / o.height)));
      if (Math.min(er, eo) > 0.1 || Math.abs(er - eo) < 0.01) return false;   // stretched on purpose, or both modes look the same
      var want = er < eo;
      if (s.trim === want) return false;
      s.trim = want;
      return true;
    },
    // fn runs once right before the next frame is drawn (after the code that built a popup has finished).
    beforeDraw: function (fn) {
      if (cc.director && typeof cc.director.once === 'function' && cc.Director && cc.Director.EVENT_BEFORE_DRAW) cc.director.once(cc.Director.EVENT_BEFORE_DRAW, fn);
    },
    label: function (n, fontSize, color, outline) {
      var l = n.addComponent(cc.Label);
      l.fontSize = fontSize; l.lineHeight = Math.round(fontSize * 1.25);
      l.horizontalAlign = cc.Label.HorizontalAlign.CENTER;
      l.verticalAlign = cc.Label.VerticalAlign.CENTER;
      n.color = rgb(color);
      if (outline) { var o = n.addComponent(cc.LabelOutline); o.color = rgb(outline); o.width = 3; }
      return l;
    },
    setLabel: function (n, label, text, maxW) {
      label.overflow = cc.Label.Overflow.NONE;
      label.string = text;
      var s = measure(n, label);
      if (s.width > maxW) {
        label.overflow = cc.Label.Overflow.RESIZE_HEIGHT;
        n.width = maxW;
        s = measure(n, label);
      }
      if (!s.width) s = {width: Math.min(maxW, text.length * label.fontSize * 0.55), height: label.lineHeight};
      return s;
    },
    rect: function (n, w, h, color, alpha) {
      var g = n.getComponent(cc.Graphics) || n.addComponent(cc.Graphics);
      g.clear(); g.fillColor = rgb(color, alpha); g.rect(-w / 2, -h / 2, w, h); g.fill();
      n.setContentSize(w, h);
    },
    roundRect: function (n, w, h, r, color, opacity) {
      var g = n.getComponent(cc.Graphics) || n.addComponent(cc.Graphics);
      g.clear(); g.fillColor = rgb(color, opacity); g.roundRect(-w / 2, -h / 2, w, h, r); g.fill();
      n.setContentSize(w, h);
    },
    ring: function (n, r, lw, color) {
      var g = n.addComponent(cc.Graphics);
      g.lineWidth = lw; g.strokeColor = rgb(color); g.lineCap = cc.Graphics.LineCap.ROUND;
      g.arc(0, 0, r - lw / 2, 0, Math.PI * 1.5, true); g.stroke();
      n.setContentSize(r * 2, r * 2);
    },
    blockInput: function (n) { n.addComponent(cc.BlockInputEvents); },
    onTap: function (n, fn) { n.on(cc.Node.EventType.TOUCH_END, fn); },
    setOpacity: function (n, v) { tw(n, 'opacity', null); n.opacity = v; },
    tweenOpacity: function (n, to, ms, cb) {
      tw(n, 'opacity', cc.tween(n).to(ms / 1000, {opacity: to}).call(function () { if (cb) cb(); }).start());
    },
    setScale: function (n, s) { tw(n, 'scale', null); n.scale = s; },
    tweenScale: function (n, to, ms, cb) {
      tw(n, 'scale', cc.tween(n).to(ms / 1000, {scale: to}).call(function () { if (cb) cb(); }).start());
    },
    tint: function (n, c) { walk(n, function (x) { if (x.name !== 'Spinner') x.color = rgb(c); }); },
    setActive: function (n, b) { n.active = !!b; },
    isValid: function (n) { return !!n && cc.isValid(n); },
    // GameUIKit button helpers
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
    destroy: function (n) { if (cc.isValid(n)) n.destroy(); },
    toTop: function (n) { n.zIndex = ++zCounter; },
    spin: function (n) {
      if (n.__uiSpin) return;
      n.__uiSpin = cc.tween(n).repeatForever(cc.tween().by(0.9, {angle: -360})).start();
    },
    stopSpin: function (n) { if (n.__uiSpin) { try { n.__uiSpin.stop(); } catch (_) {} n.__uiSpin = null; n.angle = 0; } },
    sceneRoot: function () {
      var s = cc.director.getScene();
      var c = s && s.getComponentInChildren ? s.getComponentInChildren(cc.Canvas) : null;
      return c ? c.node : s;
    },
    winSize: function () { return {width: cc.winSize.width, height: cc.winSize.height}; }
  };
  return E;
}


var GameUIKit = createGameUIKit(makeGameUIAdapter24(cc));
module.exports = GameUIKit;
