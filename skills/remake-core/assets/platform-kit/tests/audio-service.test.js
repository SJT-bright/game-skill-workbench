'use strict';
// node tests/audio-service.test.js  -- parts/AudioService.js (生成时预防方案 P15).
// One set of checks runs on the part (all must pass) and on seven old hand-written shapes from the 2026-11-04 census
// (each must fail the check named for it): one shared switch, playSfx without a switch check, BGM loaded before the
// home screen, 搭桥小能手「打开音乐面板自动解除静音」and「音效加载完越过静音」, ad end restoring the default volume, no
// throttle. The save is the real SaveStore on a memory storage; the engine is a fake backend whose loads finish only
// when the test calls flush(). Also: the 2.4 and 3.x backends against fake engines, the ad-boost manifest path, and a
// failed save. Node simulation only.
var assert = require('assert');
var path = require('path');
var AudioService = require(path.join(__dirname, '..', 'parts', 'AudioService.js'));
var SaveStore = require(path.join(__dirname, '..', 'assets', 'tiktok-platform', 'SaveStore.js'));

function memoryStorage() {
  var m = {};
  return {getItem: function (k) { return Object.prototype.hasOwnProperty.call(m, k) ? m[k] : null; },
    setItem: function (k, v) { m[k] = String(v); }, removeItem: function (k) { delete m[k]; }, _m: m};
}
function fakeBackend() {
  var b = {loads: [], pending: [], effects: [], music: null, musicVolume: null, musicPlays: 0, stops: 0};
  b.load = function (p, cb) { b.loads.push(p); b.pending.push(function () { cb(null, {clip: p}); }); };
  b.flush = function () { var q = b.pending; b.pending = []; q.forEach(function (f) { f(); }); };
  b.playMusic = function (clip, loop, v) { b.music = clip.clip; b.musicVolume = v; b.musicPlays += 1; };
  b.setMusicVolume = function (v) { b.musicVolume = v; };
  b.stopMusic = function () { b.music = null; b.stops += 1; };
  b.playEffect = function (clip, v) { b.effects.push({file: clip.clip, volume: v}); };
  b.stopAllEffects = function () {};
  return b;
}
var SOUNDS = {bgm: {file: 'audio/bgm_home', kind: 'music', volume: 1}, click: {file: 'audio/click', volume: 1, throttle_ms: 80},
  win: {file: 'audio/win', volume: 1}};

function world(Impl, storage) {
  var t = {now: 1000, timers: []};
  // R4E: a fake timer on the same clock; t.advance(ms) moves time and runs the timers that are due.
  t.advance = function (ms) {
    t.now += ms;
    t.timers.filter(function (x) { return !x.done && x.at <= t.now; }).forEach(function (x) { x.done = true; x.fn(); });
  };
  var store = new SaveStore({coins: 0}, {storage: storage || memoryStorage(), key: 'audio:test', login: false});
  store.load();
  var backend = fakeBackend();
  var svc = new Impl({store: store, backend: backend, loader: backend.load, now: function () { return t.now; },
    setTimer: function (fn, ms) { var x = {fn: fn, at: t.now + ms, done: false}; t.timers.push(x); return x; },
    clearTimer: function (x) { if (x) x.done = true; }});
  svc.register(SOUNDS);
  return {svc: svc, b: backend, t: t, store: store};
}
function started(Impl) {               // home drawn, music playing, click cached
  var w = world(Impl);
  w.svc.firstFrameDrawn(); w.svc.playMusic('bgm'); w.b.flush();
  w.svc.playSfx('click'); w.b.flush(); w.t.now += 1000;
  w.b.effects = [];
  return w;
}
function fakeRewarded() {
  var r = {resolve: null};
  r.request = function () { return new Promise(function (res) { r.resolve = res; }); };
  return r;
}

var CHECKS = {
  sfx_off_no_playEffect: function (Impl) {
    var w = started(Impl);
    w.svc.setSfxOn(false);
    var loadsBefore = w.b.loads.length;
    w.svc.playSfx('click'); w.svc.playSfx('win'); w.b.flush();
    assert.strictEqual(w.b.effects.length, 0, 'playEffect called with sfx off');
    assert.strictEqual(w.b.loads.length, loadsBefore, 'a sound effect was loaded with sfx off');
  },
  separate_channels: function (Impl) {
    var w = started(Impl);
    w.svc.setSfxOn(false);
    assert.strictEqual(w.b.music, 'audio/bgm_home', 'turning sound effects off stopped the music');
    assert.ok(w.b.musicVolume > 0, 'turning sound effects off silenced the music');
    w.svc.setSfxOn(true); w.svc.setMusicOn(false);
    w.svc.playSfx('click');
    assert.strictEqual(w.b.effects.length, 1, 'turning music off silenced the sound effects');
    assert.strictEqual(w.b.music, null, 'music still playing after setMusicOn(false)');
  },
  no_load_before_first_frame: function (Impl) {
    var w = world(Impl);
    w.svc.playMusic('bgm'); w.svc.playSfx('click');
    assert.strictEqual(w.b.loads.length, 0, 'audio loaded before the home screen was drawn: ' + w.b.loads.join(','));
    w.svc.firstFrameDrawn(); w.b.flush();
    assert.strictEqual(w.b.music, 'audio/bgm_home', 'the remembered BGM did not start after the first frame');
  },
  ad_mutes_and_restores_own_volume: function (Impl) {
    var w = started(Impl);
    w.svc.setMusicVolume(0.4);
    var rs = fakeRewarded(), ads = w.svc.wrapRewarded(rs);
    var p = ads.request({placementKey: 'revive'});
    assert.strictEqual(w.b.musicVolume, 0, 'music not silenced while the ad plays');
    w.svc.playSfx('win'); w.b.flush();
    assert.strictEqual(w.b.effects.length, 0, 'a sound effect played during the ad');
    rs.resolve({status: 'completed', rewarded: true});
    return p.then(function (r) {
      assert.strictEqual(r.status, 'completed');
      assert.strictEqual(w.b.musicVolume, 0.4, 'after the ad the music came back at ' + w.b.musicVolume + ', not the player\'s 0.4');
      assert.strictEqual(w.b.music, 'audio/bgm_home');
    });
  },
  panel_open_keeps_mute: function (Impl) {
    var w = started(Impl);
    w.svc.setMusicOn(false);
    var plays = w.b.musicPlays;
    var s = w.svc.settings();               // the settings / music panel opens and reads the state
    w.b.flush();
    assert.strictEqual(s.music.on, false, 'opening the panel switched music on');
    assert.strictEqual(w.b.music, null, 'opening the panel started the music');
    assert.strictEqual(w.b.musicPlays, plays, 'opening the panel called playMusic');
  },
  late_load_respects_mute: function (Impl) {
    var w = started(Impl);
    w.svc.playSfx('win');                    // not cached: loading
    w.svc.setSfxOn(false);                   // player mutes while it loads
    w.b.flush();
    assert.strictEqual(w.b.effects.length, 0, 'a sound effect that finished loading played over the mute');
  },
  throttle_same_sfx: function (Impl) {
    var w = started(Impl);
    for (var i = 0; i < 10; i++) { w.svc.playSfx('click'); w.t.now += 5; }
    assert.strictEqual(w.b.effects.length, 1, 'the same sound played ' + w.b.effects.length + ' times in 50 ms');
    w.t.now += 100; w.svc.playSfx('click');
    assert.strictEqual(w.b.effects.length, 2, 'the sound did not play again after its throttle time');
  },
  // R4E (没声音 15 款): the game registered sounds and called playMusic in the home scene but never bindFirstFrame.
  fallback_without_bindFirstFrame: function (Impl) {
    var w = world(Impl);
    w.svc.playMusic('bgm'); w.svc.playSfx('click');
    var warned = [], keep = console.warn;
    console.warn = function (m) { warned.push(String(m)); };
    try {
      w.t.advance(4900); w.b.flush();
      assert.strictEqual(w.b.loads.length, 0, 'sound loaded before the 5 s fallback: ' + w.b.loads.join(','));
      w.t.advance(200); w.b.flush();
    } finally { console.warn = keep; }
    assert.strictEqual(w.b.music, 'audio/bgm_home', 'no bindFirstFrame: the music never started (5.1 s after playMusic)');
    assert.strictEqual(w.svc.settings().startedBy, 'fallback');
    assert.strictEqual(warned.length, 1, 'the fallback must log one warning, got ' + warned.length);
    w.t.now += 1000; w.svc.playSfx('click'); w.b.flush();
    assert.strictEqual(w.b.effects.length, 1, 'sound effects still not_ready after the fallback');
  },
  fallback_not_used_when_bound: function (Impl) {
    var w = world(Impl);
    w.svc.playMusic('bgm');
    var after = null;
    w.svc.bindFirstFrame({once: function (ev, fn) { after = fn; }}, {EVENT_AFTER_DRAW: 'd'});
    w.t.advance(300); after(); w.b.flush();
    assert.strictEqual(w.b.musicPlays, 1);
    w.t.advance(6000); w.b.flush();
    assert.strictEqual(w.b.musicPlays, 1, 'the fallback started the music a second time');
    assert.strictEqual(w.svc.settings().startedBy, 'first_frame');
  },
  saved_in_savestore: function (Impl) {
    var st = memoryStorage(), w = world(Impl, st);
    w.svc.setMusicOn(false); w.svc.setSfxVolume(0.3);
    assert.deepStrictEqual(w.store.get().audio, {music: {on: false, volume: 0.7}, sfx: {on: true, volume: 0.3}});
    var again = world(Impl, st).svc.settings();
    assert.strictEqual(again.music.on, false); assert.strictEqual(again.sfx.volume, 0.3); assert.strictEqual(again.sfx.on, true);
  }
};

// ---------------------------------------------------------------- old shapes (each overrides one method of the part)
function variant(patch) {
  function V(o) { AudioService.AudioService.call(this, o); }
  V.prototype = Object.create(AudioService.AudioService.prototype);
  patch(V.prototype, AudioService.AudioService.prototype);
  return V;
}
var LEGACY = {
  '共用一个开关（Germ2048 一个 Sound 开关管两样）': ['separate_channels', variant(function (p, base) {
    p.setSfxOn = function (on) { var r = base.setSfxOn.call(this, on); base.setMusicOn.call(this, on); return r; };
    p.setMusicOn = function (on) { var r = base.setMusicOn.call(this, on); this.sfx.on = on === true; return r; };
  })],
  'playSfx 不查开关（播放前没看开关）': ['sfx_off_no_playEffect', variant(function (p, base) {
    p.playSfx = function (id) { var s = this.sfx.on; this.sfx.on = true; var r = base.playSfx.call(this, id); this.sfx.on = s; return r; };
  })],
  'BGM 在首页前下载（playMusic 立刻加载）': ['no_load_before_first_frame', variant(function (p, base) {
    p.playMusic = function (id) { var r = base.playMusic.call(this, id); if (!this.ready) this._load(id, function () {}); return r; };
  })],
  '搭桥小能手：打开音乐面板自动解除静音': ['panel_open_keeps_mute', variant(function (p, base) {
    p.settings = function () { this.setMusicOn(true); return base.settings.call(this); };
  })],
  '搭桥小能手：音效加载完越过静音': ['late_load_respects_mute', variant(function (p) {
    p.playSfx = function (id) {
      var self = this, e = this.entries[id];
      if (!this.sfx.on || !this.ready) return 'off';
      if (this.clips[id]) { this.backend.playEffect(this.clips[id], this.sfx.volume * e.volume); return 'ok'; }
      this._load(id, function (err, clip) { if (clip) self.backend.playEffect(clip, self.sfx.volume * e.volume); });
      return 'loading';
    };
  })],
  '广告结束恢复成默认音量': ['ad_mutes_and_restores_own_volume', variant(function (p, base) {
    p.adEnd = function () { base.adEnd.call(this); if (this.adDepth === 0) this.backend.setMusicVolume(1); };
  })],
  '同一音效不节流（一帧响 10 次）': ['throttle_same_sfx', variant(function (p, base) {
    p.playSfx = function (id) { delete this.lastPlay[id]; return base.playSfx.call(this, id); };
  })],
  'AudioService 1.1：没调 bindFirstFrame 永远不响（R4E，没声音 15 款）': ['fallback_without_bindFirstFrame', variant(function (p) {
    p._armFallback = function () {};
  })]
};

function run(name, fn, Impl) {
  return Promise.resolve().then(function () { return fn(Impl); }).then(function () { return null; }, function (e) { return e; });
}

function engineChecks() {
  // 2.4 backend
  var calls = [];
  var cc = {AudioClip: function () {}, resources: {load: function (p, T, cb) { calls.push(['load', p, T === cc.AudioClip]); cb(null, {p: p}); }},
    audioEngine: {playMusic: function (c, loop) { calls.push(['playMusic', c.p, loop]); return 1; },
      setMusicVolume: function (v) { calls.push(['musicVol', v]); }, stopMusic: function () { calls.push(['stopMusic']); },
      playEffect: function (c, loop) { calls.push(['playEffect', c.p, loop]); return 7; },
      setVolume: function (id, v) { calls.push(['setVolume', id, v]); }, stopAllEffects: function () { calls.push(['stopAll']); }}};
  // F2: loads go through the game's ResKeys table (entries as make_res_keys.py writes them: literal path, cc.AudioClip)
  function audioKey(p, engine) {
    return Object.freeze({__resKey: 1, id: p.replace(/\W/g, '_'), path: p, type: 'AudioClip', bundle: 'resources',
      request: function (cb) { engine.resources.load(p, engine.AudioClip, cb); }});
  }
  function table(engine, paths) { var t = {}; paths.forEach(function (p) { var k = audioKey(p, engine); t[k.id] = k; }); return Object.freeze(t); }
  var a = AudioService.create({backend: AudioService.backend24(cc), keys: table(cc, ['audio/bgm', 'audio/tap'])});
  a.register({bgm: {file: 'assets/resources/audio/bgm.mp3', kind: 'music', volume: 0.5}, tap: {file: 'audio/tap.mp3', volume: 0.8}});
  a.playMusic('bgm');
  assert.strictEqual(calls.length, 0, '2.4: loaded before the first frame');
  var after = null, director = {once: function (ev, fn) { after = [ev, fn]; }};
  assert.strictEqual(a.bindFirstFrame(director, {EVENT_AFTER_DRAW: 'director_after_draw'}), true);
  assert.strictEqual(after[0], 'director_after_draw'); after[1]();
  a.playSfx('tap');
  assert.deepStrictEqual(calls, [['load', 'audio/bgm', true], ['playMusic', 'audio/bgm', true], ['musicVol', 0.35],
    ['load', 'audio/tap', true], ['playEffect', 'audio/tap', false], ['setVolume', 7, 0.8]]);
  // F2: a file missing from ResKeys is not loaded and not played; a registered key object loads by itself
  calls = [];
  var o = AudioService.create({backend: AudioService.backend24(cc), keys: table(cc, ['audio/tap'])});
  o.register({miss: {file: 'audio/missing'}, tap2: {key: audioKey('audio/tap', cc)}});
  o.firstFrameDrawn(); o.playSfx('miss');
  assert.deepStrictEqual(calls, [], 'a sound not in ResKeys was loaded');
  o.playSfx('tap2');
  assert.deepStrictEqual(calls[0], ['load', 'audio/tap', true]);
  // 3.x backend
  var sources = [];
  function AudioSource() { this.played = []; sources.push(this); }
  AudioSource.prototype.play = function () { this.played.push(['play', this.clip.p, this.loop, this.volume]); };
  AudioSource.prototype.stop = function () { this.played.push(['stop']); };
  AudioSource.prototype.playOneShot = function (c, v) { this.played.push(['oneShot', c.p, v]); };
  var c3 = {AudioSource: AudioSource, AudioClip: function () {},
    resources: {load: function (p, T, cb) { cb(null, {p: p}); }}};
  var node = {addComponent: function (T) { return new T(); }};
  var b3 = AudioService.create({backend: AudioService.backend3x(c3, node), keys: table(c3, ['audio/bgm', 'audio/tap'])});
  b3.register({bgm: {file: 'audio/bgm', kind: 'music', volume: 1}, tap: {file: 'audio/tap', volume: 1}});
  b3.firstFrameDrawn(); b3.playMusic('bgm'); b3.setSfxVolume(0.5); b3.playSfx('tap');
  assert.strictEqual(sources.length, 2);
  assert.deepStrictEqual(sources[0].played, [['stop'], ['play', 'audio/bgm', true, 0.7]]);
  assert.deepStrictEqual(sources[1].played, [['oneShot', 'audio/tap', 0.5]]);
  assert.strictEqual(sources[0].playOnAwake, false);
  // ad-boost manifest (docs/audio/ad-boost-sfx.json "events") registers as it is
  var w = world(AudioService.AudioService);
  w.svc.register({wheel_spin: {file: 'assets/resources/adboost/sfx/wheel_spin.mp3', module: 'wheel', kind: 'sfx', volume: 0.9, throttle_ms: 120}});
  w.svc.firstFrameDrawn(); w.svc.playSfx('wheel_spin'); w.b.flush();
  assert.deepStrictEqual(w.b.effects, [{file: 'adboost/sfx/wheel_spin', volume: 0.9}]);
  // a failed save still changes the sound, and says it was not saved
  var bad = memoryStorage(), ws = world(AudioService.AudioService, bad);
  bad.setItem = function () { throw new Error('quota'); };
  var r = ws.svc.setSfxOn(false);
  assert.deepStrictEqual(r, {ok: true, saved: false});
  ws.svc.firstFrameDrawn(); ws.svc.playSfx('click'); ws.b.flush();
  assert.strictEqual(ws.b.effects.length, 0);
  // unknown ids never throw
  assert.strictEqual(w.svc.playSfx('nope'), 'unknown'); assert.strictEqual(w.svc.playMusic('nope'), 'unknown');
  // the request that throws still ends the ad mute
  var thrower = {request: function () { throw new Error('sdk'); }};
  assert.throws(function () { w.svc.wrapRewarded(thrower).request({}); });
  assert.strictEqual(w.svc.settings().ad, false);
}

(async function main() {
  var failures = 0;
  var names = Object.keys(CHECKS);
  for (var i = 0; i < names.length; i++) {
    var err = await run(names[i], CHECKS[names[i]], AudioService.AudioService);
    console.log((err ? 'FAIL ' : 'ok   ') + 'AudioService ' + names[i] + (err ? ': ' + err.message : ''));
    if (err) failures += 1;
  }
  try { engineChecks(); console.log('ok   2.4 / 3.x backends, ad-boost manifest, failed save, thrown request'); }
  catch (e) { failures += 1; console.log('FAIL backends: ' + (e && e.stack)); }
  var labels = Object.keys(LEGACY);
  for (var j = 0; j < labels.length; j++) {
    var want = LEGACY[labels[j]][0], Impl = LEGACY[labels[j]][1];
    var caught = await run(want, CHECKS[want], Impl);
    console.log((caught ? 'ok   反例被抓到 ' : 'FAIL 反例没被抓到 ') + labels[j] + ' -> ' + want + (caught ? ' (' + String(caught.message).split('\n')[0] + ')' : ''));
    if (!caught) failures += 1;
  }
  console.log(failures ? '\n' + failures + ' 项失败' : '\n全部通过：' + names.length + ' 项检查 + 引擎接法，' + labels.length + ' 个旧写法反例都被抓到');
  if (failures) process.exitCode = 1;
})();
