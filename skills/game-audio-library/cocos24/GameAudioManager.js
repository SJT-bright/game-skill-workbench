// GameAudioManager.js —— 全局音频管理（Cocos Creator 2.4，JavaScript）
// 放在 assets/scripts/audio/，和自动生成的 GameAudioConfig.js 同目录。
// 游戏逻辑只调用这里的方法，不要自己调用 cc.audioEngine 播放声音。
// 功能与 3.x 版一致：两个独立开关、两个 11 档音量（0–10）、设置自动保存、
// 按原因暂停（广告/切后台）、BGM 淡入淡出、音效多版本随机、防刷屏、连击升调、jingle。
//
// 用法：
//   var GameAudio = require('GameAudioManager');
//   GameAudio.init();                       // 启动场景调用一次
//   GameAudio.instance.preload();
//   GameAudio.instance.playBGM('bgm_menu');

var CONFIG = require('GameAudioConfig');
var BGM = CONFIG.BGM || {};
var SFX = CONFIG.SFX || {};

var KEY = 'game_audio_settings_v1';
var BGM_BASE = 0.5;            // BGM 一定要比音效小
var SFX_BASE = 0.8;
var JINGLE_BASE = 0.8;         // 过关/失败短音乐属于"音乐"，跟音乐开关和音乐音量
var SFX_MIN_INTERVAL = 50;     // 毫秒
var SFX_MAX_CONCURRENT = 6;
var DUCK_LEVEL = 0.25;

var FALLBACK = {
    sfx_ui_back: 'sfx_ui_click', sfx_ui_toggle: 'sfx_ui_click', sfx_ui_locked: 'sfx_invalid',
    sfx_ui_popup_close: 'sfx_ui_popup_open', sfx_ui_popup_open: 'sfx_ui_click',
    sfx_swap: 'sfx_select', sfx_hint: 'sfx_reward', sfx_shuffle: 'sfx_swap',
    sfx_booster: 'sfx_reward', sfx_clear_big: 'sfx_match', sfx_reward_ad: 'sfx_reward',
    sfx_unlock: 'sfx_reward', sfx_time_up: 'sfx_invalid', sfx_heart_lose: 'sfx_invalid',
    sfx_level_start: 'sfx_ui_popup_open', sfx_spin: 'sfx_coin', sfx_select: 'sfx_ui_click',
    sfx_place: 'sfx_select'
};

function clampLevel(v, def) {
    var n = Math.round(Number(v));
    return isFinite(n) ? Math.max(0, Math.min(10, n)) : def;
}

var GameAudioManager = cc.Class({
    extends: cc.Component,

    statics: {
        instance: null,
        /** 在启动场景调用一次；自动创建常驻节点 */
        init: function () {
            if (GameAudioManager.instance) return GameAudioManager.instance;
            var node = new cc.Node('GameAudioManager');
            cc.director.getScene().addChild(node);
            return node.addComponent(GameAudioManager);
        }
    },

    onLoad: function () {
        if (GameAudioManager.instance && GameAudioManager.instance !== this) { this.node.destroy(); return; }
        GameAudioManager.instance = this;
        cc.game.addPersistRootNode(this.node);

        this._clips = {};
        this._lastPlay = {};
        this._lastVariant = {};
        this._activeSfx = 0;
        this._transients = [];
        this._musicEpoch = 0;
        this._jingleEpoch = 0;
        this._sfxEpoch = 0;
        this._alive = true;
        this._settingsSaved = true;
        this._loadedBgm = '';
        this._currentBgm = '';
        this._pendingBgm = '';
        this._bgmAudioId = -1;
        this._bgmVolume = 0;
        this._fadeTask = null;
        this._pauseReasons = {};
        this._settings = { musicOn: true, sfxOn: true, musicLevel: 10, sfxLevel: 10, lastMusicLevel: 10, lastSFXLevel: 10 };
        this._loadSettings();

        // 浏览器要求第一次点击后才能出声；TikTok/原生环境可以直接播
        this._unlocked = !cc.sys.isBrowser;
        cc.game.on(cc.game.EVENT_HIDE, this._onHide, this);
        cc.game.on(cc.game.EVENT_SHOW, this._onShow, this);
        // 2.4 没有全局触摸事件：每次进新场景都在 Canvas 上挂一次"第一次点击"监听
        cc.director.on(cc.Director.EVENT_AFTER_SCENE_LAUNCH, this._hookFirstTouch, this);
        this._hookFirstTouch();
    },

    onDestroy: function () {
        if (!this._alive) return;
        this._alive = false; this._musicEpoch++; this._jingleEpoch++; this._sfxEpoch++;
        this._stopFade(); this._stopBgmAudio(); this._stopTransients();
        if (GameAudioManager.instance === this) GameAudioManager.instance = null;
        cc.game.off(cc.game.EVENT_HIDE, this._onHide, this);
        cc.game.off(cc.game.EVENT_SHOW, this._onShow, this);
        cc.director.off(cc.Director.EVENT_AFTER_SCENE_LAUNCH, this._hookFirstTouch, this);
    },

    _hookFirstTouch: function () {
        if (this._unlocked) return;
        var canvas = cc.Canvas.instance;
        if (canvas && canvas.node) canvas.node.once(cc.Node.EventType.TOUCH_START, this.unlock, this);
    },

    /** 第一次点击时自动调用；按钮音组件也会调用 */
    unlock: function () {
        if (this._unlocked) return;
        this._unlocked = true;
        if (this._pendingBgm) { var id = this._pendingBgm; this._pendingBgm = ''; this.playBGM(id); }
    },

    // ---------------------------------------------------------- 设置

    _loadSettings: function () {
        try {
            var raw = cc.sys.localStorage.getItem(KEY);
            if (raw) {
                var s = JSON.parse(raw);
                var music = clampLevel(s.musicLevel, 10), sfx = clampLevel(s.sfxLevel, 10);
                this._settings.lastMusicLevel = clampLevel(s.lastMusicLevel, music || 10) || music || 10;
                this._settings.lastSFXLevel = clampLevel(s.lastSFXLevel, sfx || 10) || sfx || 10;
                this._settings.musicOn = s.musicOn !== false && music > 0;
                this._settings.sfxOn = s.sfxOn !== false && sfx > 0;
                this._settings.musicLevel = this._settings.musicOn ? music : 0;
                this._settings.sfxLevel = this._settings.sfxOn ? sfx : 0;
            }
        } catch (e) { cc.warn('[Audio] 设置读取失败，使用默认值', e); }
    },

    _saveSettings: function () {
        try { cc.sys.localStorage.setItem(KEY, JSON.stringify(this._settings)); this._settingsSaved = true; return true; }
        catch (e) { this._settingsSaved = false; cc.warn('[Audio] 设置保存失败；当前设置仅本次运行有效，可重试保存', e); return false; }
    },

    isSettingsSaved: function () { return this._settingsSaved; },
    retrySaveSettings: function () { return this._saveSettings(); },

    isMusicOn: function () { return this._settings.musicOn; },
    isSFXOn: function () { return this._settings.sfxOn; },
    getMusicLevel: function () { return this._settings.musicLevel; },   // 0–10
    getSFXLevel: function () { return this._settings.sfxLevel; },

    setMusic: function (on) {
        this._settings.musicOn = !!on;
        this._settings.musicLevel = on ? this._settings.lastMusicLevel : 0;
        this._applyMusicSettings();
    },

    setSFX: function (on) {
        this._settings.sfxOn = !!on;
        this._settings.sfxLevel = on ? this._settings.lastSFXLevel : 0;
        this._applySFXSettings();
    },

    /** 绝对档位（点格）；正档开启，0 档静音并保留上次非零档。 */
    setMusicLevel: function (level) {
        var value = clampLevel(level, this._settings.musicLevel);
        this._settings.musicLevel = value; this._settings.musicOn = value > 0;
        if (value > 0) this._settings.lastMusicLevel = value;
        this._applyMusicSettings();
    },

    setSFXLevel: function (level) {
        var value = clampLevel(level, this._settings.sfxLevel);
        this._settings.sfxLevel = value; this._settings.sfxOn = value > 0;
        if (value > 0) this._settings.lastSFXLevel = value;
        this._applySFXSettings();
    },

    increaseMusicLevel: function () { this.setMusicLevel(this.getMusicLevel() + 1); },
    decreaseMusicLevel: function () { this.setMusicLevel(this.getMusicLevel() - 1); },
    increaseSFXLevel: function () { this.setSFXLevel(this.getSFXLevel() + 1); },
    decreaseSFXLevel: function () { this.setSFXLevel(this.getSFXLevel() - 1); },

    _applyMusicSettings: function () {
        this._saveSettings(); this._musicEpoch++; this._stopFade();
        this._refreshTransients('music');
        if (!this._musicScale()) { this._jingleEpoch++; this._setBgmVolume(0); this._stopBgmAudio(); return; }
        if (this._paused()) { this._currentBgm = this._currentBgm || this._pendingBgm || 'bgm_menu'; return; }
        if (this._bgmPlaying() && this._loadedBgm === this._currentBgm) this._setBgmVolume(this._bgmTarget(BGM[this._currentBgm]));
        else this.playBGM(this._currentBgm || this._pendingBgm || 'bgm_menu');
    },

    _applySFXSettings: function () {
        this._saveSettings(); this._sfxEpoch++; this._refreshTransients('sfx');
    },

    _musicScale: function () { return this._settings.musicOn ? this._settings.musicLevel / 10 : 0; },
    _sfxScale: function () { return this._settings.sfxOn ? this._settings.sfxLevel / 10 : 0; },
    _paused: function () { return Object.keys(this._pauseReasons).length > 0; },

    // ---------------------------------------------------------- 加载

    _pathsOf: function (e) {
        if (e.variants && e.variants > 1) {
            var list = [];
            for (var i = 1; i <= e.variants; i++) list.push(e.path + '_' + i);
            return list;
        }
        return [e.path];
    },

    /** 预加载全部音效，BGM 只预加载 bgm_menu */
    preload: function (onDone) {
        var self = this, paths = [];
        Object.keys(SFX).forEach(function (k) { paths = paths.concat(self._pathsOf(SFX[k])); });
        if (BGM.bgm_menu) paths.push(BGM.bgm_menu.path);
        if (!paths.length) { if (onDone) onDone(); return; }
        cc.resources.load(paths, cc.AudioClip, function (err, list) {
            if (err) cc.warn('[Audio] 预加载有失败项', err);
            (list || []).forEach(function (c, i) { if (c) self._clips[paths[i]] = c; });
            if (onDone) onDone();
        });
    },

    _getClip: function (path, cb) {
        var self = this;
        if (this._clips[path]) { cb(this._clips[path]); return; }
        cc.resources.load(path, cc.AudioClip, function (err, clip) {
            if (err || !clip) { cc.warn('[Audio] 加载失败', path); cb(null); return; }
            self._clips[path] = clip;
            cb(clip);
        });
    },

    _pickVariant: function (id, e) {
        if (!e.variants || e.variants <= 1) return e.path;
        var i = 1 + Math.floor(Math.random() * e.variants);
        if (i === this._lastVariant[id]) i = (i % e.variants) + 1;
        this._lastVariant[id] = i;
        return e.path + '_' + i;
    },

    // ---------------------------------------------------------- BGM（用 cc.audioEngine.play 以便单独控制音量与淡入淡出）

    _setBgmVolume: function (v) {
        v = this._musicScale() ? v : 0;
        this._bgmVolume = v;
        if (this._bgmAudioId >= 0) cc.audioEngine.setVolume(this._bgmAudioId, v);
    },

    _stopBgmAudio: function () {
        if (this._bgmAudioId >= 0) cc.audioEngine.stop(this._bgmAudioId);
        this._bgmAudioId = -1;
    },

    _bgmPlaying: function () {
        return this._bgmAudioId >= 0 && cc.audioEngine.getState(this._bgmAudioId) === cc.audioEngine.AudioState.PLAYING;
    },

    _bgmTarget: function (e) { return BGM_BASE * this._musicScale() * ((e && e.volume) || 1); },

    _stopFade: function () {
        if (this._fadeTask) { this.unschedule(this._fadeTask); this._fadeTask = null; }
    },

    _fadeTo: function (to, duration, done) {
        var self = this;
        this._stopFade();
        var from = this._bgmVolume, t = 0;
        if (duration <= 0) { this._setBgmVolume(to); if (done) done(); return; }
        this._fadeTask = function (dt) {
            t += dt;
            var k = Math.min(t / duration, 1);
            self._setBgmVolume(from + (to - from) * k);
            if (k >= 1) { self._stopFade(); if (done) done(); }
        };
        this.schedule(this._fadeTask, 0);
    },

    playBGM: function (id, fadeIn) {
        var self = this, e = BGM[id];
        if (fadeIn === undefined) fadeIn = 0.5;
        if (!e) { cc.warn('[Audio] 未知 BGM', id); return; }
        if (!this._unlocked) { this._pendingBgm = id; return; }
        var ticket = ++this._musicEpoch; this._jingleEpoch++;
        if (!this._musicScale() || this._paused()) { this._currentBgm = id; return; }
        if (this._currentBgm === id && this._loadedBgm === id && this._bgmPlaying()) { this._fadeTo(this._bgmTarget(e), 0.3); return; }
        this._currentBgm = id;
        if (!this._settings.musicOn || this._paused()) return;
        var start = function () {
            self._getClip(e.path, function (clip) {
                if (!clip || !self._alive || ticket !== self._musicEpoch || self._currentBgm !== id || !self._musicScale() || self._paused()) return;
                self._stopBgmAudio();
                self._loadedBgm = id;
                self._bgmVolume = 0;
                self._bgmAudioId = cc.audioEngine.play(clip, true, 0);
                self._fadeTo(self._bgmTarget(e), fadeIn);
            });
        };
        if (this._bgmPlaying()) this._fadeTo(0, 0.3, start); else start();
    },

    playLevelBGM: function (level) {
        var id = BGM.bgm_game_2 && level % 2 === 0 ? 'bgm_game_2' : 'bgm_game';
        this.playBGM(BGM[id] ? id : 'bgm_menu');
    },

    stopBGM: function (fadeOut) {
        var self = this;
        this._musicEpoch++; this._jingleEpoch++; this._currentBgm = ''; this._pendingBgm = '';
        this._fadeTo(0, fadeOut === undefined ? 0.3 : fadeOut, function () { self._stopBgmAudio(); });
    },

    /** 胜利/失败短音乐：BGM 压低后停下；结算界面出现后再调用 playBGM('bgm_menu') */
    playJingle: function (id) {
        var self = this, e = BGM[id];
        if (!e) { cc.warn('[Audio] 未知 jingle', id); return; }
        if (!this._musicScale() || this._paused() || !this._unlocked) return;
        var ticket = ++this._musicEpoch, jingleTicket = ++this._jingleEpoch;
        this._fadeTo(this._bgmTarget(BGM[this._currentBgm]) * DUCK_LEVEL, 0.15);
        this._getClip(e.path, function (clip) {
            if (!clip || !self._alive || ticket !== self._musicEpoch || !self._musicScale() || self._paused()) return;
            self._playTransient(clip, 'music', JINGLE_BASE * (e.volume || 1));
            self.scheduleOnce(function () {
                if (!self._alive || jingleTicket !== self._jingleEpoch || !self._musicScale() || self._paused()) return;
                self._fadeTo(0, 0.4, function () { self._stopBgmAudio(); self._currentBgm = ''; });
            }, (clip.duration || 1) * 0.6);
        });
    },

    // 短音保留独立句柄：开关、音量和暂停可立即作用于已播放的同类声音。
    _removeTransient: function (entry) {
        var index = this._transients.indexOf(entry);
        if (index < 0) return;
        cc.audioEngine.setVolume(entry.id, 0); cc.audioEngine.stop(entry.id);
        this.unschedule(entry.cleanup); this._transients.splice(index, 1);
        if (entry.kind === 'sfx') this._activeSfx--;
    },

    _stopTransients: function (kind) {
        var self = this;
        this._transients.slice().forEach(function (entry) { if (!kind || entry.kind === kind) self._removeTransient(entry); });
    },

    _refreshTransients: function (kind) {
        var scale = kind === 'music' ? this._musicScale() : this._sfxScale();
        if (!scale) { this._stopTransients(kind); return; }
        this._transients.forEach(function (entry) { if (entry.kind === kind) cc.audioEngine.setVolume(entry.id, entry.gain * scale); });
    },

    _playTransient: function (clip, kind, gain) {
        var self = this, scale = kind === 'music' ? this._musicScale() : this._sfxScale();
        if (!this._alive || !scale || this._paused()) return;
        var entry = { id: cc.audioEngine.play(clip, false, gain * scale), kind: kind, gain: gain };
        entry.cleanup = function () { self._removeTransient(entry); };
        this._transients.push(entry);
        if (kind === 'sfx') this._activeSfx++;
        this.scheduleOnce(entry.cleanup, Math.max(clip.duration || 0.1, 0.1));
    },

    // ---------------------------------------------------------- 音效

    playSFX: function (id, volumeScale) {
        var self = this;
        if (volumeScale === undefined) volumeScale = 1;
        if (!this._sfxScale() || !this._unlocked || this._paused()) return;
        var ticket = this._sfxEpoch;
        var guard = 0;
        while (!SFX[id] && FALLBACK[id] && guard++ < 4) id = FALLBACK[id];
        var e = SFX[id];
        if (!e) { cc.warn('[Audio] 未知音效', id); return; }
        var now = Date.now();
        if (now - (this._lastPlay[id] || 0) < SFX_MIN_INTERVAL) return;
        if (this._activeSfx >= SFX_MAX_CONCURRENT) return;
        this._lastPlay[id] = now;
        this._getClip(this._pickVariant(id, e), function (clip) {
            if (!clip || !self._alive || ticket !== self._sfxEpoch || !self._sfxScale() || self._paused() || self._activeSfx >= SFX_MAX_CONCURRENT) return;
            self._playTransient(clip, 'sfx', SFX_BASE * (e.volume || 1) * volumeScale);
        });
    },

    playCombo: function (level) {
        var max = 0;
        while (SFX['sfx_combo_' + (max + 1)]) max++;
        if (max === 0) { this.playSFX('sfx_match'); return; }
        this.playSFX('sfx_combo_' + Math.min(Math.max(level, 1), max));
    },

    playStar: function (index) {
        this.playSFX(SFX['sfx_star_' + index] ? 'sfx_star_' + index : 'sfx_star_1');
    },

    playCoins: function (count) {
        var self = this, n = Math.min(count, 8), ticket = this._sfxEpoch;
        for (var i = 0; i < n; i++) {
            (function (k) { self.scheduleOnce(function () { if (self._alive && ticket === self._sfxEpoch) self.playSFX('sfx_coin', 1 - k * 0.05); }, k * 0.06); })(i);
        }
    },

    // ---------------------------------------------------------- 暂停（按原因记录）

    /** 激励视频播放前 pause('ad')，关闭后 resume('ad')；切后台由本组件自动处理 */
    pause: function (reason) {
        this._pauseReasons[reason] = true;
        this._musicEpoch++; this._jingleEpoch++; this._sfxEpoch++; this._stopFade(); this._stopTransients();
        this._setBgmVolume(0);
        if (this._bgmAudioId >= 0) cc.audioEngine.pause(this._bgmAudioId);
    },

    resume: function (reason) {
        delete this._pauseReasons[reason];
        if (this._paused()) return;
        if (this._musicScale() && this._currentBgm && this._unlocked) {
            if (this._bgmAudioId < 0 || this._loadedBgm !== this._currentBgm) { var id = this._currentBgm; this._currentBgm = ''; this.playBGM(id); return; }
            cc.audioEngine.resume(this._bgmAudioId);
            this._fadeTo(this._bgmTarget(BGM[this._currentBgm]), 0.3);
        }
    },

    pauseAll: function () { this.pause('ad'); },
    resumeAll: function () { this.resume('ad'); },
    _onHide: function () { this.pause('hide'); },
    _onShow: function () { this.resume('hide'); }
});

module.exports = GameAudioManager;
