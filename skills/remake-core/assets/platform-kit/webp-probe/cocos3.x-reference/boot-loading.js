"use strict";
// Startup loading page for Luna's Jade Junction (Cocos Creator 3.8.8, TikTok native).
//
// Before: game.js downloaded the 21.5 MB "resources" subpackage BEFORE starting the
// engine, so a first launch on a slow network showed nothing but the TikTok launch
// screen (about 19 s at 1.5 MB/s), and the engine splash then waited on img.onload.
//
// Now: the engine starts from the main package only and right away draws the Cocos
// loading page (the official default Cocos logo from settings, the default splash
// background, a progress bar driven by real download/decode progress). Then it:
//   1. downloads the resources subpackage (native-recovery.js still fails a request
//      after 8 s with no progress, background time excluded),
//   2. checks that the SDK image object really decodes lossless WebP (webp-probe.js)
//      and tells the engine so before any image asset is read,
//   3. loads the resources bundle and preloads the art, config and fonts the game
//      scene reads first,
//   4. opens the game scene.
// Any failure shows Retry (TikTok modal plus an on-page button); every Retry starts a
// new attempt and results from older attempts are ignored.
// No gameplay, reward or storage changes.
var webp = require('./webp-probe');

var WEBP_TIMEOUT_MS = 2500;
var BAR_W = 360, BAR_H = 10;
var bg = [4, 9, 10];
var state = { cc: null, launchScene: '', logoData: '', generation: 0, webpOk: false, page: null, tickOn: false };
var progress = { known: false, download: 0, bundle: 0, assets: 0 };

function log(text) { try { console.log('[boot] ' + text); } catch (e) {} }

// Called from cc.game.onPostBaseInitDelegate: settings are loaded, nothing else yet.
exports.configure = function (cc) {
  var s = cc.settings;
  var launchScene = s.querySettings('launch', 'launchScene');
  if (!launchScene) { log('no launch scene; keeping the default start'); return; }
  state.cc = cc;
  state.launchScene = launchScene;
  var logo = s.querySettings('splashScreen', 'logo');
  state.logoData = logo && logo.type !== 'none' && typeof logo.base64 === 'string' ? logo.base64 : '';
  var background = s.querySettings('splashScreen', 'background');
  if (background && background.color) bg = [background.color.x, background.color.y, background.color.z].map(function (v) { return Math.round(v * 255); });
  var bundles = s.querySettings('assets', 'preloadBundles') || [];
  s.overrideSettings('assets', 'preloadBundles', bundles.filter(function (b) { return b && b.bundle !== 'resources'; }));
  s.overrideSettings('splashScreen', 'totalTime', 0); // the loading page shows the Cocos logo instead
  s.overrideSettings('launch', 'launchScene', '');    // the engine calls onStart; we open the scene
  cc.game.onStart = start;
};

function start() {
  var cc = state.cc;
  try { buildPage(cc); } catch (e) { console.error('[boot] loading page', e); }
  attempt();
}

function sdk() { return typeof tt === 'object' && tt ? tt : null; }
function live(token) { return token === state.generation; }

function attempt() {
  var cc = state.cc, token = ++state.generation;
  var downloaded = false, imagesOk = state.webpOk;
  progress.known = false; progress.download = 0; progress.bundle = 0; progress.assets = 0;
  showLoading();
  log('attempt ' + token);

  function fail(kind, detail) {
    if (!live(token)) return;
    state.generation++; // late results of this attempt are ignored from now on
    console.error('[boot] startup load failed: ' + kind, detail && (detail.errMsg || detail.message) || detail || '');
    showRetry(kind);
  }
  function next() {
    if (!live(token) || !downloaded || !imagesOk) return;
    cc.assetManager.loadBundle('resources', function (error, bundle) {
      if (!live(token)) return;
      if (error) { fail('bundle', error); return; }
      progress.bundle = 1;
      preload(bundle, token, function () {
        if (!live(token)) return;
        progress.assets = 1;
        log('opening ' + state.launchScene);
        var found = cc.director.loadScene(state.launchScene, function (error) {
          if (!live(token)) return;
          if (error) { fail('scene', error); return; }
          stopTick();
          state.page = null;
        });
        if (found === false) fail('scene', 'scene not found');
      });
    });
  }

  downloadResources(token, function (error) {
    if (!live(token)) return;
    if (error) { fail('download', error); return; }
    progress.download = 1; downloaded = true; log('resources downloaded');
    next();
  });

  if (!imagesOk) {
    webp.check(cc, sdk(), WEBP_TIMEOUT_MS, function (ok, reason) {
      if (!live(token)) return;
      var engineSees = webp.apply(cc, ok);
      log('webp decodes=' + ok + ' (' + reason + ') engine=' + engineSees);
      if (!ok) { fail('images', reason); return; }
      state.webpOk = true; imagesOk = true;
      next();
    });
  }
}

function downloadResources(token, done) {
  var platform = sdk(), settled = false;
  function end(error) { if (settled) return; settled = true; done(error); }
  if (!platform || typeof platform.loadSubpackage !== 'function') { end(null); return; } // engine reads the files itself
  try {
    var task = platform.loadSubpackage({
      name: 'resources',
      success: function () { end(null); },
      fail: function (error) { end(error || { errMsg: 'loadSubpackage:fail' }); }
    });
    if (task && typeof task.onProgressUpdate === 'function') task.onProgressUpdate(function (res) {
      if (!live(token) || !res) return;
      var p = typeof res.progress === 'number' ? res.progress / 100
        : res.totalBytesExpectedToWrite > 0 ? res.totalBytesWritten / res.totalBytesExpectedToWrite : NaN;
      if (isFinite(p)) { progress.known = true; progress.download = Math.max(progress.download, Math.min(1, Math.max(0, p))); }
    });
  } catch (error) { end(error); }
}

// Best effort: what the game scene reads first. A failure here is not fatal; the
// game loads the same assets again and shows its own Retry if they really fail.
function preload(bundle, token, done) {
  var cc = state.cc;
  var jobs = [
    function (p, c) { bundle.loadDir('art', cc.ImageAsset, p, c); },
    function (p, c) { bundle.load('art/layout', cc.JsonAsset, p, c); },
    function (p, c) { bundle.loadDir('config', cc.JsonAsset, p, c); },
    function (p, c) { bundle.loadDir('fonts', cc.Font, p, c); }
  ];
  var parts = jobs.map(function () { return { f: 0, t: 1 }; }), left = jobs.length;
  function update() {
    var f = 0, t = 0;
    parts.forEach(function (x) { f += x.f; t += x.t; });
    progress.assets = t > 0 ? f / t : 0;
  }
  jobs.forEach(function (job, i) {
    var finished = false;
    function complete(error) {
      if (finished) return; finished = true;
      if (error) log('preload ' + i + ' failed; the game will load it again');
      parts[i].f = parts[i].t; update();
      if (--left === 0 && live(token)) done();
    }
    try {
      job(function (f, t) { if (t > 0) { parts[i].f = f; parts[i].t = t; update(); } }, complete);
    } catch (error) { complete(error); }
  });
}

// ---------- page ----------
function makeNode(cc, name, parent, x, y, w, h) {
  var n = new cc.Node(name);
  n.layer = cc.Layers.Enum.UI_2D;
  parent.addChild(n);
  n.setPosition(x, y, 0);
  n.addComponent(cc.UITransform).setContentSize(w, h);
  return n;
}
function makeLabel(cc, name, parent, y, size, alpha) {
  var n = makeNode(cc, name, parent, 0, y, 640, size * 2.6);
  var l = n.addComponent(cc.Label);
  l.fontSize = size; l.lineHeight = Math.round(size * 1.3); l.string = '';
  l.horizontalAlign = cc.Label.HorizontalAlign.CENTER; l.verticalAlign = cc.Label.VerticalAlign.CENTER;
  l.overflow = cc.Label.Overflow.SHRINK;
  l.color = new cc.Color(255, 255, 255, alpha);
  return l;
}

function buildPage(cc) {
  cc.view.setDesignResolutionSize(720, 1280, cc.ResolutionPolicy.FIXED_WIDTH);
  var height = Math.max(1280, cc.view.getVisibleSize().height);
  var scene = new cc.Scene('BootLoading');
  var root = new cc.Node('Boot'); scene.addChild(root);
  var ui = new cc.Node('BootUI'); ui.layer = cc.Layers.Enum.UI_2D; root.addChild(ui);
  ui.addComponent(cc.UITransform).setContentSize(720, 1280);
  var canvas = ui.addComponent(cc.Canvas);
  var camNode = new cc.Node('BootCamera'); root.addChild(camNode); camNode.setPosition(0, 0, 1000);
  var cam = camNode.addComponent(cc.Camera);
  cam.projection = cc.Camera.ProjectionType.ORTHO; cam.orthoHeight = 640; cam.near = 0.1; cam.far = 2000;
  cam.visibility = cc.Layers.Enum.UI_2D; cam.clearColor = new cc.Color(bg[0], bg[1], bg[2], 255);
  canvas.cameraComponent = cam;

  var back = makeNode(cc, 'Background', ui, 0, 0, 720, height).addComponent(cc.Graphics);
  back.fillColor = new cc.Color(bg[0], bg[1], bg[2], 255); back.rect(-360, -height / 2, 720, height); back.fill();
  var logo = makeNode(cc, 'CocosLogo', ui, 0, 110, 140, 200);
  var bar = makeNode(cc, 'Progress', ui, 0, -100, BAR_W, BAR_H).addComponent(cc.Graphics);
  var status = makeLabel(cc, 'Status', ui, -150, 28, 220);
  var detail = makeLabel(cc, 'Detail', ui, -215, 22, 170);
  var retry = makeNode(cc, 'Retry', ui, 0, -330, 300, 96);
  var rg = retry.addComponent(cc.Graphics);
  rg.fillColor = new cc.Color(255, 255, 255, 235); rg.roundRect(-150, -48, 300, 96, 48); rg.fill();
  var rl = makeNode(cc, 'RetryText', retry, 0, 0, 300, 96).addComponent(cc.Label);
  rl.string = 'RETRY'; rl.fontSize = 34; rl.lineHeight = 40; rl.isBold = true;
  rl.horizontalAlign = cc.Label.HorizontalAlign.CENTER; rl.verticalAlign = cc.Label.VerticalAlign.CENTER;
  rl.color = new cc.Color(bg[0], bg[1], bg[2], 255);
  retry.active = false;

  state.page = { scene: scene, logo: logo, bar: bar, status: status, detail: detail, retry: retry, mode: 'loading', shownPct: -1, onRetry: null };
  retry.on(cc.Node.EventType.TOUCH_END, function () { var p = state.page; if (p && p.onRetry) p.onRetry(); });
  cc.director.runScene(scene);
  loadLogo(cc, logo);
  startTick(cc);
}

function loadLogo(cc, slot) {
  if (!state.logoData) return;
  webp.decode(sdk(), state.logoData, 3000, function (ok, reason, img) {
    if (!ok || !slot.isValid) { if (!ok) log('logo image ' + reason); return; }
    try {
      var w = img.width, h = img.height; // read before upload; the native image may drop its size later
      var asset = new cc.ImageAsset(img);
      var texture = new cc.Texture2D(); texture.image = asset;
      var frame = new cc.SpriteFrame(); frame.texture = texture;
      var scale = Math.min(140 / w, 200 / h);
      slot.getComponent(cc.UITransform).setContentSize(w * scale, h * scale);
      var sprite = slot.addComponent(cc.Sprite);
      sprite.sizeMode = cc.Sprite.SizeMode.CUSTOM; sprite.spriteFrame = frame;
    } catch (e) { log('logo ' + e); }
  });
}

function percent() {
  return Math.floor(progress.download * 85 + progress.bundle * 3 + progress.assets * 12);
}

function showLoading() {
  var p = state.page; if (!p || !p.bar.isValid) return;
  p.mode = 'loading'; p.onRetry = null; p.shownPct = -1;
  p.retry.active = false; p.detail.string = ''; p.status.string = 'Loading…';
}

function showRetry(kind) {
  var images = kind === 'images';
  var title = images ? 'Could not show the game images' : 'Could not load the game';
  var text = images ? 'Tap Retry to try again.' : 'Check your connection, then tap Retry.\nYour progress is kept.';
  var used = false;
  function go() { if (used) return; used = true; var p = state.page; if (p) p.onRetry = null; attempt(); }
  var p = state.page;
  if (p && p.bar.isValid) {
    p.mode = 'retry'; p.status.string = title; p.detail.string = text; p.retry.active = true; p.onRetry = go;
  }
  var platform = sdk();
  if (platform && typeof platform.showModal === 'function') {
    try {
      platform.showModal({ title: title, content: text.replace('\n', ' '), confirmText: 'Retry', showCancel: false,
        success: function (res) { if (res && res.confirm) go(); } });
    } catch (e) {}
  }
}

// ---------- animation ----------
function draw() {
  var p = state.page; if (!p || !p.bar.isValid) return;
  var g = p.bar, now = Date.now(), x = -BAR_W / 2, y = -BAR_H / 2, r = BAR_H / 2;
  g.clear();
  g.fillColor = new state.cc.Color(255, 255, 255, 46); g.roundRect(x, y, BAR_W, BAR_H, r); g.fill();
  if (p.mode !== 'loading') return;
  var pct = percent();
  if (pct !== p.shownPct && progress.known) { p.shownPct = pct; p.status.string = 'Loading ' + pct + '%'; }
  if (progress.known) {
    var fw = Math.max(BAR_H, BAR_W * pct / 100);
    g.fillColor = new state.cc.Color(255, 255, 255, 230); g.roundRect(x, y, fw, BAR_H, r); g.fill();
    // a light sweep inside the filled part shows the page is alive between progress events
    var sw = 28, t = (now % 1100) / 1100, sx = x + (fw + sw) * t - sw;
    var a = Math.max(x, sx), b = Math.min(x + fw, sx + sw);
    if (b > a) { g.fillColor = new state.cc.Color(bg[0], bg[1], bg[2], 70); g.rect(a, y, b - a, BAR_H); g.fill(); }
  } else {
    // no numbers yet: a segment slides across the track (indeterminate)
    var seg = 90, u = (now % 1300) / 1300, s0 = x - seg + (BAR_W + seg) * u;
    var c = Math.max(x, s0), d = Math.min(x + BAR_W, s0 + seg);
    if (d > c) { g.fillColor = new state.cc.Color(255, 255, 255, 200); g.roundRect(c, y, d - c, BAR_H, r); g.fill(); }
  }
}
function startTick(cc) {
  if (state.tickOn) return; state.tickOn = true;
  cc.director.on(cc.Director.EVENT_AFTER_UPDATE, draw);
}
function stopTick() {
  if (!state.tickOn) return; state.tickOn = false;
  state.cc.director.off(state.cc.Director.EVENT_AFTER_UPDATE, draw);
}
