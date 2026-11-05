/* Audio service for Cocos Creator 2.4 and 3.x (platform kit part, 简化.11.x, 生成时预防方案 P15).
 * One file for both engines. 2.4: copy it into assets/ (e.g. assets/tiktok-platform/AudioService.js) and
 *   var AudioService = require('AudioService');
 * 3.x: import it as a plugin script (it also sets the global TikTokAudioService).
 *
 * Why (问题普查 2026-11-04: 音频来源没登记 18、没声音 17、静音逻辑错 15、声音检查不过 17 款): every game wrote its own
 * audio manager and got the same things wrong. Music and sound effects shared one switch; opening the music panel
 * switched muted music back on and a sound effect that finished loading played over the mute (搭桥小能手); the BGM was
 * downloaded before the home screen (slow start); the ad video played over the game music; one tap sound fired 10 times
 * in a frame. This part makes the right behaviour the only one there is:
 *   - two channels, music and sfx, each with its own on/off and volume, saved in the game's SaveStore (key `audio`,
 *     only SaveStore.get() / update() are used);
 *   - playSfx() checks the switch BEFORE it loads or plays anything, and checks it again when a load finishes;
 *   - nothing is loaded before the home screen's first frame is drawn: playMusic() only remembers the track, and it
 *     starts after firstFrameDrawn() (bindFirstFrame() hooks EVENT_AFTER_DRAW for you);
 *   - an ad (wrapRewarded(service).request(...) or adBegin()/adEnd()) silences both channels and restores the
 *     player's own volumes afterwards; nothing here turns a channel on except setMusicOn(true) / setSfxOn(true);
 *   - the same sound effect is not replayed within its throttle_ms (default 80 ms).
 *
 *   var audio = AudioService.create({store: saveStore, backend: AudioService.backend24(cc)});      // 2.4
 *   var audio = AudioService.create({store: saveStore, backend: AudioService.backend3x(ccModule, node)}); // 3.x
 *   audio.register({bgm_home: {file: 'audio/bgm_home', kind: 'music', volume: 0.7},
 *                   click: {file: 'audio/click', volume: 1, throttle_ms: 80}});
 *   audio.register(adBoostManifest.events);   // docs/audio/ad-boost-sfx.json "events" works as it is
 *   audio.bindFirstFrame(cc.director, cc.Director);   // in the home scene's start()
 *   audio.playMusic('bgm_home');               // safe at any time; plays after the first frame
 *   audio.playSfx('click');                    // ad-boost panels: onSfx: function (id) { audio.playSfx(id); }
 *   audio.setMusicOn(false); audio.setSfxVolume(0.5); audio.settings();   // for the settings page
 *   var ads = audio.wrapRewarded(rewardedService); ads.request({placementKey: 'revive'}).then(...);
 *
 * Setters change the sound at once and return {ok, saved}: saved false means SaveStore.update() failed (the setting
 * holds for this session; the settings page may show "Could not save").
 * Files: `file` is a resources path; "assets/resources/" and the extension are stripped (ad-boost manifests give
 * assets/resources/adboost/sfx/x.mp3). 1.1: the clip is loaded through the game's generated ResKeys table (global
 * ResKeys, or options.keys; register({click: {key: ResKeys.audio_click}}) also works), never by a load call in this
 * file; a file missing from the table is not loaded (not_in_res_keys). Run make_res_keys.py after adding a sound. Proof: tests/audio-service.test.js (with the old hand-written shapes as
 * negative controls). Node simulation only, 待真机复测.
 */
(function (root, factory) {
  var api = factory(root);
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  if (root) root.TikTokAudioService = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this), function (root) {
  'use strict';
  var VERSION = '1.1';
  var DEFAULTS = {music: {on: true, volume: 0.7}, sfx: {on: true, volume: 1}};
  var SAVE_KEY = 'audio';
  var THROTTLE_MS = 80;
  var LATE_SFX_MS = 800;   // a sound effect whose load took longer than this is dropped, not played late

  function isKey(k) {
    return !!k && typeof k === 'object' && k.__resKey === 1 && typeof k.path === 'string' && typeof k.request === 'function';
  }
  function clamp(v, d) { v = Number(v); return isFinite(v) ? Math.max(0, Math.min(1, v)) : d; }
  function safely(fn) { try { return fn(); } catch (e) { return undefined; } }
  function channel(saved, d) {
    saved = saved && typeof saved === 'object' ? saved : {};
    return {on: typeof saved.on === 'boolean' ? saved.on : d.on, volume: clamp(saved.volume, d.volume)};
  }
  function resourcePath(file) {
    var p = String(file || '').replace(/\\/g, '/').replace(/^\.?\//, '');
    p = p.replace(/^assets\/resources\//, '').replace(/^resources\//, '');
    return p.replace(/\.(mp3|ogg|wav|m4a|aac)$/i, '');
  }

  function AudioService(options) {
    options = options || {};
    if (!options.backend) throw new Error('AudioService: backend is required (backend24(cc) or backend3x(cc, node))');
    this.backend = options.backend;
    this.keys = options.keys || null;       // ResKeys table; default: the global ResKeys (make_res_keys.py)
    this.loader = typeof options.loader === 'function' ? options.loader : null;   // tests / a game's own loader
    this.store = options.store || null;
    this.now = options.now || Date.now;
    this.defaultThrottle = options.throttleMs >= 0 ? options.throttleMs : THROTTLE_MS;
    this.lateSfxMs = options.lateSfxMs >= 0 ? options.lateSfxMs : LATE_SFX_MS;
    var d = options.defaults || DEFAULTS;
    var saved = this.store ? safely(function () { return options.store.get(); }) : null;
    var a = saved && saved[SAVE_KEY];
    this.music = channel(a && a.music, channel(d.music, DEFAULTS.music));
    this.sfx = channel(a && a.sfx, channel(d.sfx, DEFAULTS.sfx));
    this.entries = {};
    this.clips = {};          // id -> clip
    this.loading = {};        // id -> [callbacks]
    this.lastPlay = {};       // id -> time
    this.ready = false;       // home screen's first frame drawn
    this.adDepth = 0;
    this.wantedMusic = null;  // id the game asked for
    this.playingMusic = null; // id the backend is playing
  }

  AudioService.prototype.register = function (map) {
    var self = this;
    Object.keys(map || {}).forEach(function (id) {
      var e = map[id] || {};
      var key = isKey(e.key) ? e.key : null;
      self.entries[id] = {key: key, file: key ? key.path : resourcePath(e.file || e.path || id), kind: e.kind === 'music' || e.loop === true ? 'music' : 'sfx',
        volume: clamp(e.volume, 1), throttle: e.throttle_ms >= 0 ? Number(e.throttle_ms) : self.defaultThrottle,
        loop: e.loop !== false};
    });
    return this;
  };

  AudioService.prototype._load = function (id, cb) {
    var self = this, e = this.entries[id];
    if (!e) return cb(new Error('unknown sound ' + id));
    if (this.clips[id]) return cb(null, this.clips[id]);
    if (this.loading[id]) { this.loading[id].push(cb); return; }
    this.loading[id] = [cb];
    var done = function (err, clip) {
      var waiting = self.loading[id] || [];
      delete self.loading[id];
      if (!err && clip) self.clips[id] = clip;
      waiting.forEach(function (fn) { safely(function () { fn(err, clip); }); });
    };
    try { this._fetch(e, done); } catch (err) { done(err); }
  };

  // F2 (发版自检 C4): this file has no engine load call. A clip is loaded by its ResKeys entry's request(cb), whose
  // literal bundle/path/type make_res_keys.py writes into the game's own table, so the package resource check lists
  // every sound. A file that is not in the table is not loaded (error not_in_res_keys): run make_res_keys.py.
  AudioService.prototype._fetch = function (e, cb) {
    if (e.key) return e.key.request(cb);
    if (this.loader) return this.loader(e.file, cb);
    var table = this.keys || (root && root.ResKeys) || null, found = null;
    if (table) Object.keys(table).some(function (name) {
      var k = table[name];
      if (isKey(k) && k.type === 'AudioClip' && k.bundle === 'resources' && k.path === e.file) found = k;
      return !!found;
    });
    if (!found) {
      var err = new Error('AudioService: ' + e.file + ' is not in ResKeys (run make_res_keys.py after adding the file)');
      err.code = 'not_in_res_keys';
      return cb(err);
    }
    found.request(cb);
  };

  AudioService.prototype._musicVolume = function () {
    var e = this.entries[this.playingMusic || this.wantedMusic];
    return this.adDepth > 0 || !this.music.on ? 0 : this.music.volume * (e ? e.volume : 1);
  };

  // Starts, stops or re-levels the backend music so it matches the state. The only place that touches backend music.
  AudioService.prototype._syncMusic = function () {
    var self = this, b = this.backend, id = this.wantedMusic;
    if (!id || !this.music.on) {
      if (this.playingMusic) { safely(function () { b.stopMusic(); }); this.playingMusic = null; }
      return;
    }
    if (!this.ready) return;
    if (this.playingMusic === id) { safely(function () { b.setMusicVolume(self._musicVolume()); }); return; }
    if (this.adDepth > 0) return;            // starts when the ad ends
    this._load(id, function (err, clip) {
      if (err || !clip) return;
      if (self.wantedMusic !== id || !self.music.on || !self.ready || self.adDepth > 0 || self.playingMusic === id) return;
      if (self.playingMusic) safely(function () { b.stopMusic(); });
      var e = self.entries[id];
      safely(function () { b.playMusic(clip, e.loop, self._musicVolume()); });
      self.playingMusic = id;
    });
  };

  AudioService.prototype.firstFrameDrawn = function () {
    if (this.ready) return;
    this.ready = true;
    this._syncMusic();
  };

  // director.once(Director.EVENT_AFTER_DRAW): 2.4 cc.director / cc.Director, 3.x director / Director.
  AudioService.prototype.bindFirstFrame = function (director, Director) {
    var self = this, ev = Director && Director.EVENT_AFTER_DRAW;
    if (!director || typeof director.once !== 'function' || !ev) { this.firstFrameDrawn(); return false; }
    director.once(ev, function () { self.firstFrameDrawn(); });
    return true;
  };

  AudioService.prototype.playMusic = function (id) {
    if (!this.entries[id]) return 'unknown';
    this.wantedMusic = id;
    this._syncMusic();
    if (!this.music.on) return 'off';
    return this.ready ? 'ok' : 'after_first_frame';
  };

  AudioService.prototype.stopMusic = function () {
    this.wantedMusic = null;
    this._syncMusic();
  };

  // -> 'ok' | 'off' | 'ad' | 'not_ready' | 'throttled' | 'loading' | 'unknown'
  AudioService.prototype.playSfx = function (id) {
    var self = this, e = this.entries[id];
    if (!e) return 'unknown';
    if (!this.sfx.on) return 'off';             // checked before any load or play
    if (this.adDepth > 0) return 'ad';
    if (!this.ready) return 'not_ready';        // no download before the home screen is drawn
    var t = this.now();
    if (this.lastPlay[id] !== undefined && t - this.lastPlay[id] < e.throttle) return 'throttled';
    this.lastPlay[id] = t;
    var play = function (clip) {
      if (!self.sfx.on || self.adDepth > 0) return false;   // checked again: the switch may have changed meanwhile
      safely(function () { self.backend.playEffect(clip, self.sfx.volume * e.volume); });
      return true;
    };
    if (this.clips[id]) return play(this.clips[id]) ? 'ok' : 'off';
    this._load(id, function (err, clip) {
      if (!err && clip && self.now() - t <= self.lateSfxMs) play(clip);
    });
    return 'loading';
  };

  AudioService.prototype._save = function () {
    if (!this.store) return false;
    var value = {music: {on: this.music.on, volume: this.music.volume}, sfx: {on: this.sfx.on, volume: this.sfx.volume}};
    var r = safely(function () { return this.store.update(function (draft) { draft[SAVE_KEY] = value; }); }.bind(this));
    return !!(r && r.ok);
  };
  AudioService.prototype._set = function (name, field, value) {
    this[name][field] = field === 'on' ? value === true : clamp(value, this[name].volume);
    if (name === 'music') this._syncMusic();
    return {ok: true, saved: this._save()};
  };
  AudioService.prototype.setMusicOn = function (on) { return this._set('music', 'on', on); };
  AudioService.prototype.setSfxOn = function (on) { return this._set('sfx', 'on', on); };
  AudioService.prototype.setMusicVolume = function (v) { return this._set('music', 'volume', v); };
  AudioService.prototype.setSfxVolume = function (v) { return this._set('sfx', 'volume', v); };
  // Read-only copy for the settings page. Opening a panel never changes a channel.
  AudioService.prototype.settings = function () {
    return {music: {on: this.music.on, volume: this.music.volume}, sfx: {on: this.sfx.on, volume: this.sfx.volume},
      ad: this.adDepth > 0, ready: this.ready};
  };

  AudioService.prototype.adBegin = function () {
    this.adDepth += 1;
    var b = this.backend;
    if (this.adDepth === 1) {
      if (this.playingMusic) safely(function () { b.setMusicVolume(0); });
      if (typeof b.stopAllEffects === 'function') safely(function () { b.stopAllEffects(); });
    }
  };
  AudioService.prototype.adEnd = function () {
    if (this.adDepth === 0) return;
    this.adDepth -= 1;
    if (this.adDepth === 0) this._syncMusic();
  };
  // A RewardedService (or anything with request(options) -> Promise) whose ads silence the game while they run.
  AudioService.prototype.wrapRewarded = function (service) {
    var self = this;
    var wrapped = Object.create(service);
    wrapped.request = function (options) {
      self.adBegin();
      var ended = false;
      var end = function () { if (!ended) { ended = true; self.adEnd(); } };
      var p;
      try { p = service.request(options); } catch (e) { end(); throw e; }
      return Promise.resolve(p).then(function (r) { end(); return r; }, function (e) { end(); throw e; });
    };
    return wrapped;
  };

  // ------------------------------------------------------------------ engine backends
  function backend24(cc) {
    var ae = cc.audioEngine;
    return {   // loading goes through ResKeys (see _fetch), the backend only plays
      playMusic: function (clip, loop, volume) { ae.playMusic(clip, loop); ae.setMusicVolume(volume); },
      setMusicVolume: function (v) { ae.setMusicVolume(v); },
      stopMusic: function () { ae.stopMusic(); },
      playEffect: function (clip, volume) { var id = ae.playEffect(clip, false); ae.setVolume(id, volume); return id; },
      stopAllEffects: function () { ae.stopAllEffects(); }
    };
  }
  // cc = the 3.x 'cc' module (AudioSource, AudioClip, resources); node = a node kept across scenes (director.addPersistRootNode).
  function backend3x(cc, node) {
    var music = node.addComponent(cc.AudioSource), fx = node.addComponent(cc.AudioSource);
    music.playOnAwake = false; fx.playOnAwake = false;
    return {   // loading goes through ResKeys (see _fetch), the backend only plays
      playMusic: function (clip, loop, volume) { music.stop(); music.clip = clip; music.loop = loop; music.volume = volume; music.play(); },
      setMusicVolume: function (v) { music.volume = v; },
      stopMusic: function () { music.stop(); },
      playEffect: function (clip, volume) { fx.playOneShot(clip, volume); },
      stopAllEffects: function () { fx.stop(); }
    };
  }

  return {
    VERSION: VERSION, SAVE_KEY: SAVE_KEY, DEFAULTS: DEFAULTS,
    create: function (options) { return new AudioService(options); },
    AudioService: AudioService, backend24: backend24, backend3x: backend3x, resourcePath: resourcePath
  };
});
