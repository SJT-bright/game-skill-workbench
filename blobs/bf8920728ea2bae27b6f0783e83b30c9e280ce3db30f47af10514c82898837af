/* TikTok Minis native-runtime substitute for the pre-package rewarded-ad regression.
 * Engine-generic: runs the package's REAL game.js -> adapter -> engine chain.
 * Based on the Basil TikTok ad-timing host (2026-10-28) and the Marlows r5 host.
 * Disclosed substitutions: platform 'devtools' adapter path, sync-XHR require,
 * in-memory USER_DATA_PATH, simulated rewarded ads, Date.now warp. Not a phone pass.
 * Regression probes: __adPendingListeners() counts shown ads that never got a terminal
 * callback but still have onClose/onError listeners bound; __musicState() reports
 * what the game asked looped audio to do (play/pause intent), independent of the
 * browser's autoplay policy.
 *
 * v7.5: the ONE official strict host (runtime_regression.py and ad_regression.py both serve it).
 * Merged from Mabel r8 (startup/mission QA), MergeShot2048 v82-v84 (file/storage/SDK faults),
 * MusicSlice v30 (legacyads, network log), Germ2048 v3 (real body, screen-only touch, audio src
 * cleared, never-answering ad) and Basil (canvas cannot encode WebP). Every fault is opt-in by URL
 * query; the full list with sources is in references/runtime-regression.md. Defaults that differ
 * from a browser: touches carry ONLY identifier/screenX/screenY/force (touch=full restores
 * clientX/pageX), no createBannerAd/createInterstitialAd (legacyads=1 adds no-fill stubs), the
 * capsule rect is the measured 87x32, 10 from the right, 4 below the status bar. */
(function () {
  'use strict';
  var Q = new URLSearchParams(location.search);
  // Test clock warp: __warp(ms) moves Date.now forward so 60 s / 200 s ad cases run instantly.
  var RealNow = Date.now.bind(Date), warpOff = 0;
  Date.now = function () { return RealNow() + warpOff; };
  window.__warp = function (ms) { warpOff += ms; return warpOff; };
  // TikTok has no page lifecycle and draws no DOM (Finger Mahjong v57, 10-30): document.hidden stays
  // false, visibilitychange/pagehide never fire, only canvases are drawn. A loading watchdog that timed
  // "foreground" with document.hidden counted lock-screen time as a stall, and its DOM Retry was
  // invisible, so the home page stayed locked. Background reaches the game only through tt.onHide /
  // onShow. realdoc=1 restores browser behaviour (diagnosis only).
  var nVis = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
  var nAddListener = EventTarget.prototype.addEventListener;
  window.__hostVisible = function () { return !nVis || nVis.get.call(document) !== 'hidden'; };
  window.__hostListen = function (target, type, fn, opt) { return nAddListener.call(target, type, fn, opt); };
  if (Q.get('realdoc') !== '1') {
    Object.defineProperty(Document.prototype, 'hidden', { configurable: true, get: function () { return false; } });
    Object.defineProperty(Document.prototype, 'visibilityState', { configurable: true, get: function () { return 'visible'; } });
    EventTarget.prototype.addEventListener = function (type) {
      if (type === 'visibilitychange' || type === 'pagehide' || type === 'pageshow') return;
      return nAddListener.apply(this, arguments);
    };
    var domHidden = window.__domHidden = [];
    var hostNode = function (el) { return el.tagName === 'CANVAS' || /^(SCRIPT|STYLE|LINK|META)$/.test(el.tagName) || (el.closest && el.closest('#__hostModal,#__adOverlay')); };
    new MutationObserver(function (records) {
      records.forEach(function (r) {
        Array.prototype.forEach.call(r.addedNodes, function (el) {
          if (el.nodeType !== 1 || hostNode(el)) return;
          el.style.setProperty('display', 'none', 'important');
          el.setAttribute('data-tiktok-hidden', '1');
          if (domHidden.length < 40) domHidden.push({ tag: el.tagName, id: el.id || '', text: String(el.textContent || '').trim().slice(0, 80) });
        });
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  // webpenc=png (alias webp=encoder_png): the canvas cannot ENCODE WebP (toDataURL falls back to
  // PNG) while images still DECODE WebP - the Basil / Mabel phone case.
  if (Q.get('webpenc') === 'png' || Q.get('webp') === 'encoder_png') {
    var nToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function (type) { if (/webp/i.test(String(type || ''))) return nToDataURL.call(this, 'image/png'); return nToDataURL.apply(this, arguments); };
  }
  // Canvas-drawn text (2D fillText/strokeText): startup screens drawn before the engine (a
  // "Tap to Retry" from a native load guard) have no cc.Label or DOM node. __canvasText(rx, after)
  // returns the newest matching draw after host time `after` as a CSS point, or null.
  var CTEXT = [];
  ['fillText', 'strokeText'].forEach(function (fn) {
    var orig = CanvasRenderingContext2D.prototype[fn];
    CanvasRenderingContext2D.prototype[fn] = function (text, x, y) {
      try {
        var m = this.getTransform ? this.getTransform() : { a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 };
        CTEXT.push({ text: String(text).slice(0, 80), cx: m.a * x + m.c * y + m.e, cy: m.b * x + m.d * y + m.f, canvas: this.canvas, t: now() });
        if (CTEXT.length > 400) CTEXT.splice(0, 200);
      } catch (_) {}
      return orig.apply(this, arguments);
    };
  });
  window.__canvasText = function (pattern, after) {
    var rx = new RegExp(pattern, 'i');
    for (var i = CTEXT.length - 1; i >= 0; i--) {
      var e = CTEXT[i];
      if (e.t <= (after || -1) || !rx.test(e.text)) continue;
      var c = e.canvas, r = c && c.getBoundingClientRect ? c.getBoundingClientRect() : null;
      if (!r || !r.width) r = { left: 0, top: 0, width: innerWidth, height: innerHeight };
      return { text: e.text, t: e.t, x: r.left + e.cx * r.width / (c.width || r.width), y: r.top + e.cy * r.height / (c.height || r.height) };
    }
    return null;
  };
  var NXHR = window.XMLHttpRequest, NImage = window.Image, NAudio = window.Audio;
  var nCreate = document.createElement.bind(document);
  // The adapter swaps document/body for fakes; host overlays (ads, modals) must use the real ones.
  var NDOC = window.document, NBODY = document.body || document.documentElement;
  window.__NDoc = NDOC; window.__NBody = NBODY;
  var IMG_SRC = Object.getOwnPropertyDescriptor(window.HTMLImageElement.prototype, 'src');
  // The TikTok adapter replaces window.performance with {now: Date.now}; host times keep the native clock.
  var PNow = window.performance.now.bind(window.performance);
  var t0 = PNow();
  var LOG = window.__hostLog = [];
  function now() { return Math.round(PNow() - t0); }
  function beacon(kind, data) {
    var row = { t: now(), kind: kind, data: data };
    LOG.push(row);
    try { var x = new NXHR(); x.open('POST', '/__log', true); x.setRequestHeader('Content-Type', 'application/json'); x.send(JSON.stringify(row)); } catch (_) {}
  }
  window.__beacon = beacon;
  window.addEventListener('error', function (e) { beacon('error', { msg: String(e.message), src: e.filename, line: e.lineno, stack: e.error && e.error.stack && String(e.error.stack).slice(0, 1500) }); });
  window.addEventListener('unhandledrejection', function (e) { var r = e.reason; beacon('rejection', { msg: String(r && r.message || r), stack: r && r.stack && String(r.stack).slice(0, 1500) }); });
  var cerr = console.error.bind(console);
  console.error = function () { try { beacon('console.error', Array.prototype.map.call(arguments, function (a) { return a && a.stack ? String(a.stack).slice(0, 800) : String(a).slice(0, 800); }).join(' ')); } catch (_) {} cerr.apply(null, arguments); };
  var cwarn = console.warn.bind(console);
  console.warn = function () { try { var s = Array.prototype.map.call(arguments, String).join(' '); if (/fail|error|cannot|not |unavailable|unexpected/i.test(s)) beacon('console.warn', s.slice(0, 600)); } catch (_) {} cwarn.apply(null, arguments); };

  // ---------- fault switches (all opt-in; see references/runtime-regression.md) ----------
  // A switch value is one or more path substrings separated by '|'. <name>_n=K limits it to K hits.
  var FAULT = window.__faults = { access: 0, failfile: 0, hangfile: 0, imghang: 0, pkg: {}, hits: [] };
  var pkgLoaded = {};
  window.__pkgTries = FAULT.pkg; // subpackage attempts by name (Mabel r8 tests read this)
  function quota(name, dflt) { var v = Q.get(name + '_n'); return v === null ? dflt : +v; }
  function matches(param, path) { var s = Q.get(param); return !!s && s.split('|').some(function (p) { return p && String(path).indexOf(p) >= 0; }); }
  function hit(kind, what) { FAULT.hits.push({ kind: kind, what: String(what).slice(-120), t: now() }); if (FAULT.hits.length <= 40) beacon('fault-' + kind, String(what).slice(-160)); }
  window.__setFault = function (name, value) { Q.set(name, value); return Q.toString(); };

  // ---------- network log: every request the game sends off the package (D5 4.2) ----------
  var NET = window.__net = [];
  function external(u) { try { var x = new URL(String(u), location.href); return /^(https?|wss?):$/.test(x.protocol) && x.origin !== location.origin; } catch (_) { return false; } }
  function netLog(kind, url, extra) { var row = { kind: kind, url: String(url).slice(0, 500), t: now() }; if (extra) row.extra = extra; NET.push(row); beacon('net-' + kind, row); }
  // External requests are logged and never leave the machine (unlisted domains fail on TikTok too).
  var xOpen = NXHR.prototype.open;
  NXHR.prototype.open = function (m, u) { if (external(u)) { netLog('xhr', u, { method: m }); arguments[1] = '/__net_blocked'; } return xOpen.apply(this, arguments); };
  if (window.fetch) { var nFetch = window.fetch.bind(window); window.fetch = function (u) { var s = u && u.url ? u.url : u; if (external(s)) { netLog('fetch', s); return Promise.reject(new TypeError('fetch blocked in QA host')); } return nFetch.apply(null, arguments); }; }
  if (window.WebSocket) { var NWS = window.WebSocket; window.WebSocket = function (u) { netLog('websocket', u); var s = { readyState: 3, send: function () {}, close: function () {}, addEventListener: function () {}, removeEventListener: function () {} }; setTimeout(function () { s.onerror && s.onerror({ type: 'error' }); s.onclose && s.onclose({ code: 1006 }); }, 50); return s; }; window.WebSocket.prototype = NWS.prototype; }
  if (navigator.sendBeacon) { var nSB = navigator.sendBeacon.bind(navigator); navigator.sendBeacon = function (u) { if (external(u)) { netLog('sendbeacon', u); return false; } return nSB.apply(null, arguments); }; }

  // ---------- files ----------
  var memFiles = Object.create(null);
  var USER = 'ttfile://user';
  function norm(p) {
    p = String(p).replace(/^https?:\/\/[^/]+/, '');
    var out = [];
    p.split('/').forEach(function (seg) { if (!seg || seg === '.') return; if (seg === '..') out.pop(); else out.push(seg); });
    return '/' + out.join('/');
  }
  function syncGet(path, binary) {
    var x = new NXHR();
    x.open('GET', norm(path), false);
    if (binary) x.overrideMimeType('text/plain; charset=x-user-defined');
    x.send();
    if (x.status !== 200) { var e = new Error('no such file or directory ' + path); e.status = x.status; throw e; }
    if (!binary) return x.responseText;
    var s = x.responseText, buf = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) buf[i] = s.charCodeAt(i) & 0xff;
    return buf.buffer;
  }
  function asyncGet(path, binary, ok, bad) {
    var x = new NXHR();
    x.open('GET', norm(path), true);
    if (binary) x.responseType = 'arraybuffer';
    x.onload = function () { if (x.status === 200) ok(binary ? x.response : x.responseText); else bad({ errMsg: 'readFile:fail no such file ' + path, errCode: x.status }); };
    x.onerror = function () { bad({ errMsg: 'readFile:fail network ' + path }); };
    x.send();
  }
  function exists(path) {
    if (String(path).indexOf(USER) === 0) return Object.keys(memFiles).some(function (k) { return k === path || k.indexOf(path + '/') === 0; }) || path === USER;
    var x = new NXHR(); x.open('HEAD', norm(path), false); x.send(); return x.status === 200;
  }

  // ---------- require ----------
  var cache = Object.create(null);
  function resolve(from, id) {
    var p = id.charAt(0) === '/' ? id : (from.replace(/[^/]*$/, '') + id);
    p = norm(p);
    if (!/\.js$/.test(p)) p += '.js';
    return p;
  }
  function makeRequire(from) {
    return function require(id) {
      var p = resolve(from, id);
      if (cache[p]) return cache[p].exports;
      var mod = { exports: {} };
      cache[p] = mod;
      var code = syncGet(p, false);
      beacon('require', p);
      // failrequire=SUBSTR: that script throws on load (MergeShot2048 v82).
      if (matches('failrequire', p)) { delete cache[p]; hit('failrequire', p); throw new Error('simulated script failure ' + p); }
      var fn = new Function('require', 'module', 'exports', code + '\n//# sourceURL=' + location.origin + p);
      fn.call(window, makeRequire(p), mod, mod.exports);
      return mod.exports;
    };
  }
  window.require = makeRequire('/game.js');

  // ---------- canvas / system info ----------
  var W = window.innerWidth, H = window.innerHeight, DPR = window.devicePixelRatio || 1;
  var main = nCreate('canvas');
  main.id = 'GameCanvas';
  main.width = W; main.height = H;
  main.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;display:block;touch-action:none;';
  NBODY.appendChild(main);
  var firstCanvas = true;
  // sdk=missing: no SDKVersion field at all (MergeShot2048 v83/v84, MusicSlice adapter case); sdk=<x.y.z> sets it.
  var sdkQ = Q.get('sdk');
  var sys = {
    brand: 'Apple', model: 'iPhone 15', pixelRatio: DPR, devicePixelRatio: DPR,
    screenWidth: W, screenHeight: H, windowWidth: W, windowHeight: H, statusBarHeight: 47,
    safeArea: { left: 0, right: W, top: 47, bottom: H - 34, width: W, height: H - 81 },
    language: 'en', version: '37.0.0', SDKVersion: sdkQ || '3.60.0', system: 'iOS 17.5',
    platform: Q.get('platform') || 'devtools', appName: 'TikTok', benchmarkLevel: 30
  };
  if (sdkQ === 'missing') delete sys.SDKVersion;

  // ---------- events ----------
  function hub() { var list = []; return { on: function (f) { if (typeof f === 'function' && list.indexOf(f) < 0) list.push(f); }, off: function (f) { if (!f) list.length = 0; else { var i = list.indexOf(f); if (i >= 0) list.splice(i, 1); } }, emit: function (v) { list.slice().forEach(function (f) { try { f(v); } catch (e) { beacon('error', { msg: 'listener: ' + e.message, stack: String(e.stack).slice(0, 800) }); } }); }, size: function () { return list.length; } }; }
  var H_ = { touchstart: hub(), touchmove: hub(), touchend: hub(), touchcancel: hub(), show: hub(), hide: hub(), error: hub(), audioBegin: hub(), audioEnd: hub(), resize: hub() };
  // Default: only the fields TikTok documents for touch points (identifier, screenX, screenY, force),
  // as on a phone (Germ2048 v3 / MergeShot2048 v82). screenX/screenY are canvas-relative, as on a phone
  // where the game fills the screen. touch=full adds clientX/pageX (browser shape) for diagnosis only.
  var screenOnly = Q.get('touch') !== 'full';
  function shape(id, cx, cy, force) {
    if (screenOnly) return { identifier: id, screenX: cx, screenY: cy, force: force || 1 };
    return { identifier: id, clientX: cx, clientY: cy, pageX: cx, pageY: cy, screenX: cx, screenY: cy, force: force || 1 };
  }
  function tlist(list) { return Array.prototype.map.call(list, function (t) { return shape(t.identifier, t.clientX, t.clientY, t.force); }); }
  var touchCount = { touchstart: 0, touchmove: 0, touchend: 0, touchcancel: 0 };
  ['touchstart', 'touchmove', 'touchend', 'touchcancel'].forEach(function (type) {
    main.addEventListener(type, function (e) {
      e.preventDefault(); touchCount[type]++;
      H_[type].emit({ touches: tlist(e.touches), changedTouches: tlist(e.changedTouches), timeStamp: e.timeStamp });
    }, { passive: false });
  });
  // Mouse -> single touch for desktop preview only (?mouse=1).
  if (Q.get('mouse') === '1') {
    var down = false;
    function mt(e) { return [shape(0, e.clientX, e.clientY, 1)]; }
    main.addEventListener('mousedown', function (e) { down = true; H_.touchstart.emit({ touches: mt(e), changedTouches: mt(e), timeStamp: e.timeStamp }); });
    window.addEventListener('mousemove', function (e) { if (down) H_.touchmove.emit({ touches: mt(e), changedTouches: mt(e), timeStamp: e.timeStamp }); });
    window.addEventListener('mouseup', function (e) { if (!down) return; down = false; H_.touchend.emit({ touches: [], changedTouches: mt(e), timeStamp: e.timeStamp }); });
  }
  var hidden = false;
  function setHidden(h) { if (h === hidden) return; hidden = h; beacon('lifecycle', h ? 'hide' : 'show'); (h ? H_.hide : H_.show).emit(h ? {} : { scene: '1001', query: {} }); }
  window.__hostListen(document, 'visibilitychange', function () { setHidden(!window.__hostVisible()); });
  window.__simHide = function () { setHidden(true); };
  window.__simShow = function () { setHidden(false); };

  // ---------- audio ----------
  var audioLive = 0, innerAudios = [], audioCleared = 0, sfxPlays = 0;
  window.__musicState = function () {
    return innerAudios.filter(function (x) { return !x._destroyed && x.loop && x.src; })
      .map(function (x) { return { src: String(x.src).slice(-80), playing: !!x._intent, volume: x.volume }; });
  };
  // D7 item 9 (Germ2048): what is audible while a rewarded video plays. bgm = looped tracks the game
  // wants playing at volume > 0; sfxLive = one-shot sounds still playing; sfxPlays = one-shot play()
  // calls so far; sfxPaused = one-shot sounds the game paused and has not resumed or stopped;
  // engine = cc.audioEngine music/effects volume when the engine exposes them (2.x).
  window.__audioSnapshot = function () {
    var live = innerAudios.filter(function (x) { return !x._destroyed && x.src; });
    var eng = null;
    try { var e = window.cc && cc.audioEngine; if (e && e.getMusicVolume) eng = { music: e.getMusicVolume(), effects: e.getEffectsVolume ? e.getEffectsVolume() : null }; } catch (_) {}
    return {
      bgm: live.filter(function (x) { return x.loop && x._intent && x.volume > 0; }).map(function (x) { return String(x.src).slice(-80); }),
      sfxLive: live.filter(function (x) { return !x.loop && x._intent && x.volume > 0; }).length,
      sfxPlays: sfxPlays,
      sfxPaused: live.filter(function (x) { return !x.loop && x._pausedByGame; }).length,
      engine: eng
    };
  };
  function InnerAudio() {
    var a = new NAudio(), self = this, hs = {};
    audioLive++;
    ['Canplay', 'Play', 'Pause', 'Stop', 'Ended', 'Error', 'TimeUpdate', 'Waiting', 'Seeking', 'Seeked'].forEach(function (n) {
      hs[n] = hub(); self['on' + n] = hs[n].on; self['off' + n] = hs[n].off;
    });
    a.addEventListener('canplay', function () { hs.Canplay.emit(); });
    a.addEventListener('play', function () { hs.Play.emit(); });
    a.addEventListener('pause', function () { if (!self._stopping) hs.Pause.emit(); });
    a.addEventListener('ended', function () { hs.Ended.emit(); });
    // The engine recycles players with src = null/'' (cocos2d-js-min: this._element.src=""). That is
    // recorded as "src cleared", never as an audio error (Germ2048 v3), so real errors stay visible.
    a.addEventListener('error', function () { if (!a.getAttribute('src')) return; beacon('audio-error', a.src); hs.Error.emit({ errMsg: 'audio error', errCode: 10001 }); });
    a.addEventListener('timeupdate', function () { hs.TimeUpdate.emit(); });
    a.addEventListener('waiting', function () { hs.Waiting.emit(); });
    a.addEventListener('seeked', function () { hs.Seeked.emit(); });
    Object.defineProperties(this, {
      src: { get: function () { return a.src; }, set: function (v) { if (v) { a.src = norm(v); return; } if (a.getAttribute('src')) { audioCleared++; if (audioCleared <= 3) beacon('audio-src-cleared', audioCleared); } a.removeAttribute('src'); } },
      loop: { get: function () { return a.loop; }, set: function (v) { a.loop = !!v; } },
      volume: { get: function () { return a.volume; }, set: function (v) { a.volume = Math.max(0, Math.min(1, +v || 0)); } },
      autoplay: { get: function () { return a.autoplay; }, set: function (v) { a.autoplay = !!v; } },
      startTime: { get: function () { return self._st || 0; }, set: function (v) { self._st = +v || 0; } },
      currentTime: { get: function () { return a.currentTime; } },
      duration: { get: function () { return isFinite(a.duration) ? a.duration : 0; } },
      paused: { get: function () { return a.paused; } },
      buffered: { get: function () { return a.buffered.length ? a.buffered.end(0) : 0; } }
    });
    this.obeyMuteSwitch = true;
    // _intent records what the game asked for, so autoplay blocking cannot hide a missing resume.
    self._intent = false;
    this.play = function () { self._intent = true; self._pausedByGame = false; if (!a.loop) sfxPlays++; var p = a.play(); if (p && p.catch) p.catch(function (e) { beacon('audio-play-blocked', String(e && e.name)); }); };
    this.pause = function () { self._intent = false; self._pausedByGame = true; a.pause(); };
    this.stop = function () { self._intent = false; self._pausedByGame = false; self._stopping = true; a.pause(); try { a.currentTime = 0; } catch (_) {} self._stopping = false; hs.Stop.emit(); };
    this.seek = function (t) { try { a.currentTime = t; } catch (_) {} };
    this.destroy = function () { self._intent = false; self._pausedByGame = false; self._destroyed = true; a.pause(); a.removeAttribute('src'); audioLive--; };
    a.addEventListener('ended', function () { if (!a.loop) { self._intent = false; self._pausedByGame = false; } });
    window.__audios = window.__audios || []; window.__audios.push(a);
    innerAudios.push(self);
  }

  // ---------- file system manager ----------
  function cb(o, ok, v) { try { if (ok) o.success && o.success(v); else o.fail && o.fail(v); } finally { o.complete && o.complete(v); } }
  function decode(buf, enc) { if (!enc || enc === 'binary') return buf; return new TextDecoder(enc === 'utf-8' ? 'utf8' : enc).decode(buf); }
  var fsm = {
    readFile: function (o) {
      var p = o.filePath;
      // failfile / hangfile = SUBSTR[|SUBSTR] (+ failfile_n / hangfile_n = K hits; Mabel's filetimes=K also works).
      var fq = function (n) { return quota(n, Q.get('filetimes') !== null ? +Q.get('filetimes') : 1e9); };
      if (matches('failfile', p) && FAULT.failfile < fq('failfile')) { FAULT.failfile++; hit('failfile', p); setTimeout(function () { cb(o, false, { errMsg: 'readFile:fail simulated ' + p }); }, 50); return; }
      if (matches('hangfile', p) && FAULT.hangfile < fq('hangfile')) { FAULT.hangfile++; hit('hangfile', p); return; }
      if (p in memFiles) { var d = memFiles[p]; setTimeout(function () { cb(o, true, { data: o.encoding ? (typeof d === 'string' ? d : decode(d, o.encoding)) : d }); }); return; }
      asyncGet(p, !o.encoding, function (data) { cb(o, true, { data: data }); }, function (err) { cb(o, false, err); });
    },
    readFileSync: function (p, enc) { if (p in memFiles) return memFiles[p]; return enc ? syncGet(p, false) : syncGet(p, true); },
    writeFile: function (o) { memFiles[o.filePath] = o.data; setTimeout(function () { cb(o, true, {}); }); },
    writeFileSync: function (p, d) { memFiles[p] = d; },
    appendFile: function (o) { memFiles[o.filePath] = (memFiles[o.filePath] || '') + o.data; setTimeout(function () { cb(o, true, {}); }); },
    // accesshang=SUBSTR: fs.access on matching paths never answers (real iPhone vConsole, MergeShot2048 v81).
    access: function (o) { FAULT.accessCalls = (FAULT.accessCalls || 0) + 1; if (matches('accesshang', o.path)) { FAULT.access++; hit('accesshang', o.path); return; } var ok = exists(o.path); setTimeout(function () { cb(o, ok, ok ? {} : { errMsg: 'access:fail no such file or directory ' + o.path }); }); },
    accessSync: function (p) { FAULT.accessCalls = (FAULT.accessCalls || 0) + 1; if (!exists(p)) throw new Error('access:fail no such file or directory ' + p); },
    mkdir: function (o) { setTimeout(function () { cb(o, true, {}); }); },
    mkdirSync: function () {},
    rmdir: function (o) { setTimeout(function () { cb(o, true, {}); }); },
    rmdirSync: function () {},
    readdir: function (o) { var pre = o.dirPath.replace(/\/$/, '') + '/'; var files = Object.keys(memFiles).filter(function (k) { return k.indexOf(pre) === 0; }).map(function (k) { return k.slice(pre.length).split('/')[0]; }); setTimeout(function () { cb(o, true, { files: files }); }); },
    readdirSync: function () { return []; },
    unlink: function (o) { delete memFiles[o.filePath]; setTimeout(function () { cb(o, true, {}); }); },
    unlinkSync: function (p) { delete memFiles[p]; },
    copyFile: function (o) { try { memFiles[o.destPath] = memFiles[o.srcPath] !== undefined ? memFiles[o.srcPath] : syncGet(o.srcPath, true); setTimeout(function () { cb(o, true, {}); }); } catch (e) { setTimeout(function () { cb(o, false, { errMsg: e.message }); }); } },
    copyFileSync: function (s, d) { memFiles[d] = memFiles[s] !== undefined ? memFiles[s] : syncGet(s, true); },
    stat: function (o) { var ok = exists(o.path); setTimeout(function () { cb(o, ok, ok ? { stats: { size: 0, isFile: function () { return true; }, isDirectory: function () { return false; } } } : { errMsg: 'stat:fail' }); }); },
    statSync: function (p) { if (!exists(p)) throw new Error('stat:fail ' + p); return { size: 0, isFile: function () { return true; }, isDirectory: function () { return false; } }; },
    getFileInfo: function (o) { setTimeout(function () { cb(o, true, { size: 0 }); }); },
    unzip: function (o) { beacon('fs-unzip', o.zipFilePath); setTimeout(function () { cb(o, false, { errMsg: 'unzip:fail not supported in browser host' }); }); },
    saveFile: function (o) { var d = o.filePath || (USER + '/saved_' + Date.now()); setTimeout(function () { cb(o, true, { savedFilePath: d }); }); },
    removeSavedFile: function (o) { setTimeout(function () { cb(o, true, {}); }); },
    getSavedFileList: function (o) { setTimeout(function () { cb(o, true, { fileList: [] }); }); }
  };

  // ---------- storage ----------
  var SP = 'ttstore:'; var NLS = window.localStorage;
  function sKeys() { var k = []; for (var i = 0; i < NLS.length; i++) { var n = NLS.key(i); if (n.indexOf(SP) === 0) k.push(n.slice(SP.length)); } return k; }
  var storageWrites = 0;
  // reset=1 (alias fresh=1): start from an empty save. __storeRaw(key, rawJsonText) plants a raw
  // (possibly corrupt) stored value; __storeDump() returns every stored raw value.
  if (Q.get('reset') === '1' || Q.get('fresh') === '1') sKeys().forEach(function (k) { NLS.removeItem(SP + k); });
  window.__storeRaw = function (k, raw) { if (raw === null || raw === undefined) NLS.removeItem(SP + k); else NLS.setItem(SP + k, String(raw)); };
  window.__storeDump = function () { var o = {}; sKeys().forEach(function (k) { o[k] = NLS.getItem(SP + k); }); return o; };
  // missing=true|false|undefined|null|throw: what getStorageSync returns for a key never written
  // (real TikTok can return true; MergeShot2048 v81). numbool=01|all: a stored number reads back as a Boolean.
  function missingValue(k) {
    var m = Q.get('missing');
    if (m === null) return '';
    hit('missing', k);
    if (m === 'throw') throw new Error('getStorageSync:fail data not found');
    return m === 'true' ? true : m === 'false' ? false : m === 'null' ? null : undefined;
  }

  // ---------- rewarded ads (simulated) ----------
  var adStats = window.__adStats = { created: 0, shown: 0, closedEnded: 0, closedEarly: 0, errors: 0, live: 0, units: {} };
  var adRecords = [];
  window.__adPendingListeners = function () {
    return adRecords.filter(function (r) { return r.shown && !r.finished && (r.close.size() + r.err.size()) > 0; }).length;
  };
  var adPolicy = Q.get('ad') || 'ask'; // ask | complete | cancel | error | showfail | hang | pending (show() never settles, no callback ever; alias never)
  function overlay(unit, done) {
    var box = nCreate('div');
    box.id = '__adOverlay';
    box.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(10,14,30,.88);color:#fff;font:16px -apple-system,Helvetica,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center;padding:24px';
    box.innerHTML = '<div style="font-size:20px;font-weight:700">模拟激励视频广告</div><div style="opacity:.8;font-size:13px">' + unit + '</div>' +
      '<button data-r="complete" style="font-size:17px;padding:12px 22px;border-radius:12px;border:0;background:#2fd17a;color:#062">看完（发奖励）</button>' +
      '<button data-r="cancel" style="font-size:17px;padding:12px 22px;border-radius:12px;border:0;background:#ffcf4a;color:#420">中途关闭（不发奖励）</button>' +
      '<button data-r="error" style="font-size:17px;padding:12px 22px;border-radius:12px;border:0;background:#ff6b6b;color:#400">广告报错</button>';
    box.addEventListener('click', function (e) { var r = e.target.getAttribute && e.target.getAttribute('data-r'); if (r) { box.remove(); done(r); } });
    ['touchstart', 'touchend'].forEach(function (t) { box.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true }); });
    NBODY.appendChild(box);
  }
  function createRewardedVideoAd(opt) {
    opt = opt || {};
    var unit = String(opt.adUnitId || ''), close = hub(), err = hub(), load = hub(), used = false;
    var rec = { unit: unit, shown: false, finished: false, close: close, err: err };
    adRecords.push(rec);
    adStats.created++; adStats.units[unit] = (adStats.units[unit] || 0) + 1;
    beacon('ad-create', unit);
    function finish(r) {
      rec.finished = true;
      adStats.live = Math.max(0, adStats.live - 1);
      beacon('ad-result', { unit: unit, result: r });
      if (r === 'complete') { adStats.closedEnded++; close.emit({ isEnded: true }); }
      else if (r === 'cancel') { adStats.closedEarly++; close.emit({ isEnded: false }); }
      else { adStats.errors++; err.emit({ errCode: 1004, errorCode: 1004, errMsg: 'no ad fill (simulated)' }); }
    }
    return {
      adUnitId: unit,
      onClose: close.on, offClose: close.off, onError: err.on, offError: err.off, onLoad: load.on, offLoad: load.off,
      load: function () { return Promise.resolve(); },
      destroy: function () {},
      show: function () {
        if (used) return Promise.reject({ errorCode: 1003, errMsg: 'instance already shown' });
        used = true; rec.shown = true; adStats.shown++; adStats.live++;
        beacon('ad-show', { unit: unit, policy: adPolicy });
        if (adPolicy === 'showfail') { rec.finished = true; adStats.live--; adStats.errors++; return Promise.reject({ errorCode: 1000, errMsg: 'show fail (simulated)' }); }
        if (adPolicy === 'hang') return Promise.resolve();
        if (adPolicy === 'pending' || adPolicy === 'never') return new Promise(function () {});
        if (adPolicy === 'manual') {
          // Test script drives it: __adCtl.start() resolves show(), close(ended) / error() end it.
          var ctl = window.__adCtl = { unit: unit, started: false };
          return new Promise(function (res, rej) {
            ctl.start = function () { ctl.started = true; res(); };
            ctl.rejectShow = function () { rec.finished = true; adStats.live--; adStats.errors++; rej({ errorCode: 1000, errMsg: 'show fail (simulated)' }); };
            ctl.close = function (ended) { finish(ended ? 'complete' : 'cancel'); };
            ctl.error = function () { finish('error'); };
          });
        }
        var pick = adPolicy === 'ask' ? null : adPolicy;
        setHidden(false);
        if (pick) setTimeout(function () { finish(pick); }, +(Q.get('adms') || 600));
        else overlay(unit, finish);
        return Promise.resolve();
      }
    };
  }
  window.__setAdPolicy = function (p) { adPolicy = p; };

  // ---------- modal / toast / loading / missions / login ----------
  var missionMode = Q.get('mission') || 'none'; // none | reward | fail
  window.__setMission = function (m) { missionMode = m; beacon('mission-mode', m); return missionMode; };
  var missionCalls = { addShortcut: 0, getShortcutMissionReward: 0, startEntranceMission: 0, getEntranceMissionReward: 0 };
  var loginCalls = 0, toasts = [], loadingShown = false, loadingTitle = '';
  // tt.showModal draws a real DOM dialog on the REAL body; __modalOpen describes it, its buttons are
  // tapped with real pointer input (window.__modalRect(which) gives their CSS rect).
  window.__modalOpen = null;
  function showModal(o) {
    o = o || {};
    beacon('modal', { title: o.title, content: o.content, confirmText: o.confirmText });
    var box = nCreate('div');
    box.id = '__hostModal';
    box.style.cssText = 'position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;font:16px -apple-system,Helvetica,sans-serif';
    var cancel = o.showCancel !== false;
    box.innerHTML = '<div style="background:#fff;color:#111;border-radius:14px;width:270px;padding:18px;text-align:center"><div id="__modalTitle" style="font-weight:700;margin-bottom:8px"></div><div id="__modalBody" style="font-size:14px;margin-bottom:16px"></div>' +
      (cancel ? '<button id="__modalCancel" style="font-size:16px;padding:10px 20px;border:0;border-radius:10px;background:#ddd;color:#111;margin-right:10px"></button>' : '') +
      '<button id="__modalOk" style="font-size:16px;padding:10px 26px;border:0;border-radius:10px;background:#fe2c55;color:#fff"></button></div>';
    // v7.7 (W-D3): ids, not 'div > div' (that selected the whole card and replaced the buttons, so the next lookup
    // was null and showModal threw; the kit Retry dialog never appeared in the host)
    box.querySelector('#__modalTitle').textContent = o.title || '';
    box.querySelector('#__modalBody').textContent = o.content || '';
    box.querySelector('#__modalOk').textContent = o.confirmText || 'OK';
    if (cancel) box.querySelector('#__modalCancel').textContent = o.cancelText || 'Cancel';
    function done(ok) { box.remove(); window.__modalOpen = null; beacon('modal-' + (ok ? 'confirm' : 'cancel'), o.title); cb(o, true, { confirm: ok, cancel: !ok }); }
    box.querySelector('#__modalOk').addEventListener('click', function () { done(true); });
    if (cancel) box.querySelector('#__modalCancel').addEventListener('click', function () { done(false); });
    ['touchstart', 'touchend'].forEach(function (t) { box.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: true }); });
    window.__modalOpen = { title: o.title || '', content: o.content || '', confirmText: o.confirmText || 'OK', at: now() };
    NBODY.appendChild(box);
  }
  // NBODY.querySelector: once the game runs, NDOC.getElementById no longer finds the buttons hung on NBODY (W-D3)
  window.__modalRect = function (which) { var b = NBODY.querySelector(which === 'cancel' ? '#__modalCancel' : '#__modalOk'); if (!b) return null; var r = b.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height }; };

  // ---------- tt ----------
  var IMG_PENDING = 0;
  window.__hostPending = function () { return { images: IMG_PENDING }; };
  var missionsOn = Q.get('missions') !== '0';
  var tt = {
    env: { USER_DATA_PATH: USER, VERSION: 'release' },
    getSystemInfoSync: function () { return Object.assign({}, sys); },
    getSystemInfo: function (o) { setTimeout(function () { cb(o || {}, true, Object.assign({}, sys)); }); },
    getWindowInfo: function () { return Object.assign({}, sys); },
    getDeviceInfo: function () { return Object.assign({}, sys); },
    createCanvas: function () { if (firstCanvas) { firstCanvas = false; return main; } return nCreate('canvas'); },
    createImage: function () {
      var i = new NImage(); i.crossOrigin = 'anonymous';
      // Package paths are relative to the package root, not to /__host/play.html.
      // imghang (alias hangimg) = SUBSTR: that image never fires load/error (default once; imghang_n / imgtimes = K).
      // datauri=error|hang: data: URIs fail (error) or never answer (hang) - Mabel r7 WebP probe.
      var desc = IMG_SRC;
      Object.defineProperty(i, 'src', { configurable: true, get: function () { return desc.get.call(i); },
        set: function (v) {
          v = String(v);
          var hq = Q.get('imghang_n') !== null ? +Q.get('imghang_n') : +(Q.get('imgtimes') || 1);
          if ((matches('imghang', v) || matches('hangimg', v)) && FAULT.imghang < hq) { FAULT.imghang++; hit('imghang', v); return; }
          var du = Q.get('datauri');
          if (/^data:/.test(v) && (du === 'error' || du === 'hang')) {
            hit('datauri', du);
            if (du === 'error') setTimeout(function () { try { i.dispatchEvent(new Event('error')); } catch (_) {} }, 30);
            return;
          }
          if (external(v)) { netLog('image', v); v = '/__net_blocked'; }
          // In-flight count for the startup lifecycle cases (strike while the game is really loading).
          if (!i.__hostCounted) {
            i.__hostCounted = true; IMG_PENDING++;
            var settle = function () { if (i.__hostCounted) { i.__hostCounted = false; IMG_PENDING--; } };
            i.addEventListener('load', settle); i.addEventListener('error', settle);
          }
          desc.set.call(i, /^(data:|blob:)/.test(v) ? v : norm(v));
        } });
      return i;
    },
    createInnerAudioContext: function () { return new InnerAudio(); },
    getFileSystemManager: function () { return fsm; },
    downloadFile: function (o) {
      var u = o.url;
      if (external(u)) { netLog('download', u); setTimeout(function () { cb(o, false, { errMsg: 'downloadFile:fail domain not in allowlist (QA host)' }); }); }
      else { beacon('download-local', String(u).slice(-160)); setTimeout(function () { cb(o, true, { statusCode: 200, tempFilePath: u }); }); }
      return { abort: function () {}, onProgressUpdate: function () {}, offProgressUpdate: function () {} };
    },
    loadSubpackage: function (o) {
      var name = o.name, prog = hub(), t = now();
      // Subpackage faults (attempt = how many times the game asked for this name):
      //   failpkg=NAME fails the first pkgtimes (default 1; 'always') attempts - one RETRY must recover (Mabel r8).
      //   hangpkg=NAME never answers for the first pkgtimes attempts.
      //   nthpkg=NAME:N&nthmode=fail|hang: only the Nth attempt fails / never answers (MergeShot2048 v82).
      //   pkgms=MS download time; pkgprog=1 reports bytes every 500 ms like TikTok's LoadSubpackageTask;
      //   stallpkg=F (0..1) stops reporting at fraction F and never completes (first pkgtimes attempts).
      var tries = FAULT.pkg[name] = (FAULT.pkg[name] || 0) + 1;
      var times = Q.get('pkgtimes') === 'always' ? 1e9 : +(Q.get('pkgtimes') || 1);
      var nth = (Q.get('nthpkg') || '').split(':'), nthHit = nth[0] === name && +nth[1] === tries;
      var nthMode = nthHit ? (Q.get('nthmode') || 'fail') : null;
      beacon('subpackage', { name: name, attempt: tries, fault: nthMode });
      var task = { onProgressUpdate: prog.on, offProgressUpdate: prog.off, abort: function () {} };
      if ((Q.get('hangpkg') === name && tries <= times && !pkgLoaded[name]) || nthMode === 'hang') { hit('pkghang', name + '#' + tries); return task; }
      // A subpackage that already loaded is on disk: like TikTok, a later request answers at once and
      // download faults (pkgms/pkgprog/stallpkg/failpkg/hangpkg) no longer apply; nthpkg still does.
      var cached = !!pkgLoaded[name];
      var dur = cached ? 30 : +(Q.get('pkgms') || 30), TOTAL = +(Q.get('pkgbytes') || 18001718);
      if (Q.get('pkgprog') === '1' && !cached) {
        var stallAt = Q.get('stallpkg') !== null && tries <= times ? +Q.get('stallpkg') : 2, tp = now();
        var ticker = setInterval(function () {
          var f = Math.min(1, (now() - tp) / dur);
          if (f >= stallAt) { clearInterval(ticker); hit('pkgstall', name + '#' + tries + '@' + stallAt); return; }
          prog.emit({ progress: Math.floor(f * 100), totalBytesWritten: Math.floor(f * TOTAL), totalBytesExpectedToWrite: TOTAL });
          if (f >= 1) clearInterval(ticker);
        }, 500);
        if (stallAt <= 1) return task;
      }
      setTimeout(function () {
        try {
          if (nthMode === 'fail') { hit('pkgfail', name + '#' + tries); throw new Error('simulated subpackage failure on attempt ' + tries); }
          if (!cached && Q.get('failpkg') === name && tries <= times && !(Q.get('failonce') === '1' && window.__pkgFailedOnce)) { window.__pkgFailedOnce = true; hit('pkgfail', name + '#' + tries); throw new Error('simulated subpackage failure'); }
          window.require('/subpackages/' + name + '/game.js');
          prog.emit({ progress: 100, totalBytesWritten: TOTAL, totalBytesExpectedToWrite: TOTAL });
          pkgLoaded[name] = true;
          beacon('subpackage-ok', { name: name, ms: now() - t, attempt: tries, cached: cached });
          cb(o, true, {});
        } catch (e) { beacon('subpackage-fail', { name: name, msg: e.message, attempt: tries }); cb(o, false, { errMsg: 'loadSubpackage:fail ' + e.message }); }
      }, dur);
      return task;
    },
    getStorageSync: function (k) {
      var v = NLS.getItem(SP + k); if (v === null) return missingValue(k);
      var r; try { r = JSON.parse(v); } catch (_) { return v; }
      var nb = Q.get('numbool'); if (nb && typeof r === 'number' && (nb === 'all' || r === 0 || r === 1)) { hit('numbool', k + '=' + r); return r !== 0; }
      return r;
    },
    setStorageSync: function (k, v) { storageWrites++; NLS.setItem(SP + k, JSON.stringify(v)); },
    removeStorageSync: function (k) { NLS.removeItem(SP + k); },
    clearStorageSync: function () { sKeys().forEach(function (k) { NLS.removeItem(SP + k); }); },
    getStorageInfoSync: function () { return { keys: sKeys(), currentSize: 0, limitSize: 10240 }; },
    getStorage: function (o) { var v = tt.getStorageSync(o.key); setTimeout(function () { cb(o, true, { data: v }); }); },
    setStorage: function (o) { tt.setStorageSync(o.key, o.data); setTimeout(function () { cb(o, true, {}); }); },
    onTouchStart: H_.touchstart.on, offTouchStart: H_.touchstart.off,
    onTouchMove: H_.touchmove.on, offTouchMove: H_.touchmove.off,
    onTouchEnd: H_.touchend.on, offTouchEnd: H_.touchend.off,
    onTouchCancel: H_.touchcancel.on, offTouchCancel: H_.touchcancel.off,
    onShow: H_.show.on, offShow: H_.show.off, onHide: H_.hide.on, offHide: H_.hide.off,
    onError: H_.error.on, offError: H_.error.off,
    onAudioInterruptionBegin: H_.audioBegin.on, offAudioInterruptionBegin: H_.audioBegin.off,
    onAudioInterruptionEnd: H_.audioEnd.on, offAudioInterruptionEnd: H_.audioEnd.off,
    onWindowResize: H_.resize.on, offWindowResize: H_.resize.off,
    getLaunchOptionsSync: function () { return { scene: '1001', query: {}, extra: {} }; },
    getEnterOptionsSync: function () { return { scene: '1001', query: {} }; },
    getPerformance: function () { return performance; },
    triggerGC: function () {},
    setPreferredFramesPerSecond: function (f) { beacon('fps', f); },
    setKeepScreenOn: function (o) { o && setTimeout(function () { cb(o, true, {}); }); },
    vibrateShort: function (o) { beacon('vibrate', 'short'); o && setTimeout(function () { cb(o, true, {}); }); },
    vibrateLong: function (o) { beacon('vibrate', 'long'); o && setTimeout(function () { cb(o, true, {}); }); },
    getMenuButtonBoundingClientRect: function () { return { left: W - 97, right: W - 10, top: 51, bottom: 83, width: 87, height: 32 }; },
    getUpdateManager: function () { return { onCheckForUpdate: function () {}, onUpdateReady: function () {}, onUpdateFailed: function () {}, applyUpdate: function () {} }; },
    getOpenDataContext: function () { return { postMessage: function () {}, canvas: nCreate('canvas') }; },
    onNetworkStatusChange: function () {}, offNetworkStatusChange: function () {},
    getNetworkType: function (o) { setTimeout(function () { cb(o, true, { networkType: 'wifi' }); }); },
    onDeviceOrientationChange: function () {}, offDeviceOrientationChange: function () {},
    startAccelerometer: function (o) { o && setTimeout(function () { cb(o, true, {}); }); },
    stopAccelerometer: function (o) { o && setTimeout(function () { cb(o, true, {}); }); },
    onAccelerometerChange: function () {}, offAccelerometerChange: function () {},
    request: function (o) { netLog('request', o && o.url, { method: o && o.method }); setTimeout(function () { cb(o, false, { errMsg: 'request:fail blocked in QA host' }); }); return { abort: function () {} }; },
    connectSocket: function (o) { netLog('socket', o && o.url); return { onOpen: function () {}, onClose: function () {}, onError: function () {}, onMessage: function () {}, send: function () {}, close: function () {} }; },
    createVideo: function () { return null; },
    createOffscreenVideo: function () { return null; },
    showKeyboard: function () {}, hideKeyboard: function () {}, updateKeyboard: function () {},
    onKeyboardInput: function () {}, offKeyboardInput: function () {}, onKeyboardConfirm: function () {}, offKeyboardConfirm: function () {}, onKeyboardComplete: function () {}, offKeyboardComplete: function () {},
    loadFont: function (path) {
      var fam = 'ttfont_' + Object.keys(cache).length + '_' + Math.random().toString(36).slice(2, 6);
      try { var ff = new FontFace(fam, 'url(' + norm(path) + ')'); document.fonts.add(ff); ff.load().then(function () { beacon('font-ok', path); }, function () { beacon('font-fail', path); }); } catch (_) { return null; }
      return fam;
    },
    createRewardedVideoAd: createRewardedVideoAd,
    canIUse: function (name) { if (/Mission|Shortcut/.test(name)) return missionsOn; return typeof tt[name] === 'function'; },
    // Missions: mission=none|reward|fail at load; __setMission(mode) switches it while the game runs (Mabel r8).
    addShortcut: function (o) { missionCalls.addShortcut++; beacon('mission', 'addShortcut'); setTimeout(function () { cb(o, missionMode !== 'fail', missionMode === 'fail' ? { errMsg: 'addShortcut:fail' } : {}); }, 300); },
    getShortcutMissionReward: function (o) { missionCalls.getShortcutMissionReward++; beacon('mission', 'getShortcutMissionReward'); setTimeout(function () { cb(o, missionMode !== 'fail', missionMode === 'fail' ? { errMsg: 'getShortcutMissionReward:fail' } : { canReceiveReward: missionMode === 'reward' }); }, 200); },
    startEntranceMission: function (o) { missionCalls.startEntranceMission++; beacon('mission', 'startEntranceMission'); setTimeout(function () { cb(o, missionMode !== 'fail', missionMode === 'fail' ? { errMsg: 'startEntranceMission:fail' } : {}); }, 300); },
    getEntranceMissionReward: function (o) { missionCalls.getEntranceMissionReward++; beacon('mission', 'getEntranceMissionReward'); setTimeout(function () { cb(o, missionMode !== 'fail', missionMode === 'fail' ? { errMsg: 'getEntranceMissionReward:fail' } : { canReceiveReward: missionMode === 'reward' }); }, 200); },
    // login is counted; login=fail makes it fail. The game must never wait on it (Mabel W2_login).
    login: function (o) { o = o || {}; loginCalls++; window.__loginCalls = loginCalls; beacon('login', loginCalls); setTimeout(function () { cb(o, Q.get('login') !== 'fail', Q.get('login') === 'fail' ? { errMsg: 'login:fail' } : { code: 'qa-code', anonymousCode: 'qa-anon' }); }, 200); },
    showModal: showModal,
    showToast: function (o) { o = o || {}; toasts.push({ title: o.title, t: now() }); beacon('toast', o.title); if (o.success) setTimeout(function () { cb(o, true, {}); }); },
    hideToast: function (o) { o && setTimeout(function () { cb(o, true, {}); }); },
    showLoading: function (o) { o = o || {}; loadingTitle = String(o.title || ''); loadingShown = true; o.success && setTimeout(function () { cb(o, true, {}); }); },
    hideLoading: function (o) { loadingShown = false; o && setTimeout(function () { cb(o, true, {}); }); }
  };
  // opendata=missing: no getOpenDataContext (MusicSlice adapter case; 2.4 adapter-min reads it at load).
  if (Q.get('opendata') === 'missing') delete tt.getOpenDataContext;
  // legacyads=1: TikTok has no banner / interstitial; only then add no-fill stubs (MusicSlice v29b).
  if (Q.get('legacyads') === '1') {
    var legacy = function (kind) { return function (o) { beacon('legacy-ad-create', kind + ':' + (o && o.adUnitId)); var h = { style: Object.assign({ realWidth: 300, realHeight: 100 }, (o && o.style) || {}) }; ['onResize', 'offResize', 'onLoad', 'offLoad', 'onError', 'offError', 'onClose', 'offClose'].forEach(function (k) { h[k] = function () {}; }); h.show = function () { return Promise.reject({ errCode: 1004, errMsg: 'no fill (legacy stub)' }); }; h.load = function () { return Promise.reject({ errCode: 1004 }); }; h.hide = function () {}; h.destroy = function () {}; return h; }; };
    tt.createBannerAd = legacy('banner'); tt.createInterstitialAd = legacy('interstitial');
  }
  window.tt = tt;
  window.TTMinis = { game: tt };
  window.GameGlobal = window;
  // Like the native runtime: GameGlobal.canvas is undefined until the adapter creates it.

  // TikTok WebAssembly: instantiate(path, imports) reads a package file.
  if (Q.get('nowasm') !== '1') {
    var TW = Object.create(WebAssembly);
    TW.instantiate = function (src, imports) {
      if (typeof src === 'string') { beacon('wasm', src); return fetch(norm(src)).then(function (r) { if (!r.ok) throw new Error('wasm fetch ' + r.status + ' ' + src); return r.arrayBuffer(); }).then(function (b) { return WebAssembly.instantiate(b, imports); }); }
      return WebAssembly.instantiate(src, imports);
    };
    window.TTWebAssembly = TW;
  }

  window.__hostState = function () {
    return { t: now(), touches: touchCount, touchListeners: { start: H_.touchstart.size(), move: H_.touchmove.size(), end: H_.touchend.size() }, showListeners: H_.show.size(), hideListeners: H_.hide.size(), ads: adStats, audioLive: audioLive, audioCleared: audioCleared, storageWrites: storageWrites, storageKeys: sKeys(), modules: Object.keys(cache).length, hidden: hidden,
      faults: { hits: FAULT.hits.length, accessCalls: FAULT.accessCalls || 0, pkg: FAULT.pkg }, missions: missionCalls, missionMode: missionMode, login: loginCalls,
      modal: window.__modalOpen, toasts: toasts.slice(-5), loading: loadingShown ? loadingTitle : null, net: NET.length };
  };
  beacon('host-ready', { W: W, H: H, DPR: DPR, platform: sys.platform });
})();
