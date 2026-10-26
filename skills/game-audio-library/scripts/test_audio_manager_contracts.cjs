/* Isolated contracts for the actual shipped templates. No Cocos/game/browser starts. */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const args = process.argv.slice(2);
const option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const root = option('--skill-root', path.resolve(__dirname, '..'));
const tsPath = option('--typescript', process.env.AUDIO_TYPESCRIPT);
const ts = tsPath ? require(tsPath) : null;
const config = {
  BGM: { bgm_menu: { path: 'menu' }, bgm_game: { path: 'game' }, jingle_win: { path: 'win' } },
  SFX: { sfx_ui_click: { path: 'click' }, sfx_coin: { path: 'coin' } },
};

function load(engine, initial, browser = false) {
  const storage = { raw: initial === undefined ? null : JSON.stringify(initial), fail: false,
    getItem() { return this.raw; }, setItem(k, v) { if (this.fail) throw Error('storage denied'); this.raw = v; } };
  const pending = [], live = [], sources = [], warnings = [], tweens = [];
  class Component {
    constructor() { this.tasks = []; this.node = new Node(); }
    schedule(fn) { this.tasks.push({ fn, repeat: true }); }
    scheduleOnce(fn, delay) { this.tasks.push({ fn, delay, repeat: false }); }
    unschedule(fn) { this.tasks = this.tasks.filter(t => t.fn !== fn); }
  }
  class Node {
    constructor() { this.destroyed = false; this.events = new Map(); }
    addComponent(C) { const c = new C(); c.node = this; return c; }
    destroy() { this.destroyed = true; }
    on(name, fn) { const list=this.events.get(name)||[]; list.push(fn); this.events.set(name,list); }
    off(name, fn) { this.events.set(name,(this.events.get(name)||[]).filter(x=>x!==fn)); }
    emit(name, arg) { for(const fn of (this.events.get(name)||[]).slice()) fn(arg); }
    once() {} addChild() {}
  }
  Node.EventType = { TOUCH_START: 'touch' };
  class AudioSource {
    constructor() { this.volume = 1; this.loop = false; this.clip = null; this.playing = false; sources.push(this); }
    play() { this.playing = true; this.stopped = false; if (!live.includes(this)) live.push(this); this.node.emit('started',this); }
    stop() { this.playing = false; this.stopped = true; }
    pause() { this.playing = false; }
    destroy() { this.stop(); this.destroyed = true; }
    // Engine 3.x one-shots cannot be stopped by AudioSource.stop/volume changes.
    playOneShot(clip, scale) { live.push({ clip, volume: this.volume * scale, playing: true, oneShot: true }); }
  }
  AudioSource.EventType = { STARTED: 'started', ENDED: 'ended' };
  const clip = p => ({ path: p, duration: 1, getDuration() { return this.duration; } });
  const audioEngine = { AudioState: { PLAYING: 1 },
    play(c, loop, volume) { const s = { clip: c, loop, volume, playing: true }; live.push(s); return live.length - 1; },
    stop(i) { if (live[i]) live[i].playing = false; }, pause(i) { if (live[i]) live[i].playing = false; },
    resume(i) { if (live[i]) live[i].playing = true; },
    setVolume(i, v) { if (live[i]) live[i].volume = v; },
    getState(i) { return live[i] && live[i].playing ? 1 : 0; },
  };
  const resources = { load(p, type, cb) { pending.push({ p, cb }); } };
  const director = { getScene() { return new Node(); }, on() {}, off() {}, addPersistRootNode() {} };
  const game = { on() {}, off() {}, addPersistRootNode() {}, EVENT_HIDE: 'hide', EVENT_SHOW: 'show' };
  const cc = { Component, Node, resources, audioEngine, AudioClip: class {}, sys: { localStorage: storage, isBrowser: browser },
    director, game, Director: { EVENT_AFTER_SCENE_LAUNCH: 'scene' }, Canvas: { instance: null },
    warn(...v) { warnings.push(v); },
    Class(def) { class C extends Component {} Object.assign(C.prototype, def); Object.assign(C, def.statics); return C; },
  };
  const Tween = { stopAllByTarget(target) { for (const t of tweens) if (t.target === target) t.cancelled = true; } };
  const tween = target => {
    const t = { target, to(d, values, opts) { this.values = values; this.opts = opts; return this; },
      call(fn) { this.done = fn; return this; }, start() { tweens.push(this); return this; } };
    return t;
  };
  const filename = path.join(root, engine === '2.4' ? 'cocos24/GameAudioManager.js' : 'cocos3x/GameAudioManager.ts');
  let code = fs.readFileSync(filename, 'utf8');
  if (engine === '3.x') {
    if (!ts) throw Error('Pass --typescript <installed typescript/lib/typescript.js>');
    const result = ts.transpileModule(code, { fileName: filename, reportDiagnostics: true,
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2018, experimentalDecorators: true } });
    const errors = (result.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error);
    assert.deepStrictEqual(errors.map(d => ts.flattenDiagnosticMessageText(d.messageText, '\n')), []);
    code = result.outputText;
  }
  const module = { exports: {} };
  const ccmodule = { ...cc, AudioSource, Tween, tween, _decorator: { ccclass() { return C => C; } },
    input: { once() {} }, Input: { EventType: { TOUCH_START: 'touch' } }, Game: game };
  const context = { module, exports: module.exports, cc, Map, Set, Date, Math, console: { warn: (...v) => warnings.push(v) },
    require(name) { if (name === 'cc') return ccmodule; if (/GameAudioConfig$/.test(name)) return config; throw Error(name); } };
  vm.runInNewContext(code, context, { filename });
  const Manager = engine === '2.4' ? module.exports : module.exports.GameAudioManager;
  const manager = new Manager(); manager.onLoad();
  return { engine, manager, storage, pending, live, warnings, sources,
    level(kind) { return engine === '2.4' ? manager[kind === 'music' ? 'getMusicLevel' : 'getSFXLevel']() : manager[kind + 'Level']; },
    on(kind) { return engine === '2.4' ? manager[kind === 'music' ? 'isMusicOn' : 'isSFXOn']() : manager[kind + 'On']; },
    resolve(p, fail = false) { const i = pending.findIndex(x => x.p === p); assert(i >= 0, 'pending clip ' + p);
      const task = pending.splice(i, 1)[0]; task.cb(fail ? Error('load failed') : null, fail ? null : clip(p)); },
    fades() { for (const task of manager.tasks.slice()) if (task.repeat) task.fn(1);
      for (const t of tweens.splice(0)) if (!t.cancelled) { Object.assign(t.target, t.values); t.opts && t.opts.onUpdate(); t.done && t.done(); } },
    once() { const tasks = manager.tasks.filter(t => !t.repeat); manager.tasks = manager.tasks.filter(t => t.repeat); for (const t of tasks) t.fn(); },
    finish(p) { for(const s of live.filter(x=>x.clip && !x.loop && (!p || x.clip.path===p))) {s.playing=false;if(s.node)s.node.emit('ended',s);} },
    sounding(p) { return live.filter(s => s.playing && s.volume > 0 && (!p || s.clip.path === p)); },
    plays(p) { return live.filter(s => !p || s.clip.path === p).length; },
  };
}

const results = [];
function test(engine, name, run) {
  try { run(); results.push({ engine, name, passed: true }); }
  catch (e) { results.push({ engine, name, passed: false, error: e.message }); }
}
for (const engine of ['2.4', '3.x']) {
  const fresh = s => load(engine, s);
  test(engine, 'zero then ON restores last nonzero independently', () => {
    const h = fresh(); const a = h.manager; a.setMusicLevel(4); a.setMusicLevel(0); a.setMusic(true);
    assert.strictEqual(h.level('music'), 4); assert.strictEqual(h.level('sfx'), 10);
    a.setSFXLevel(6); a.setSFXLevel(0); a.setSFX(true); assert.strictEqual(h.level('sfx'), 6); assert(h.on('sfx'));
  });
  test(engine, 'OFF effective zero and positive absolute grid level opens selected level', () => {
    const h = fresh(); const a = h.manager; a.setMusicLevel(7); a.setMusic(false);
    assert.strictEqual(h.level('music'), 0); assert.strictEqual(h.on('music'), false);
    a.setMusicLevel(3); assert(h.on('music')); assert.strictEqual(h.level('music'), 3);
    a.setSFX(false); assert.strictEqual(h.level('sfx'), 0); a.setSFXLevel(2); assert(h.on('sfx')); assert.strictEqual(h.level('sfx'), 2);
  });
  test(engine, 'OFF minus stays zero plus starts at one and boundaries clamp', () => {
    const h = fresh(); const a = h.manager;
    for (const kind of ['Music', 'SFX']) { a['set' + kind + 'Level'](8); a['set' + kind](false);
      a['decrease' + kind + 'Level'](); assert.strictEqual(h.level(kind === 'Music' ? 'music' : 'sfx'), 0);
      a['increase' + kind + 'Level'](); assert.strictEqual(h.level(kind === 'Music' ? 'music' : 'sfx'), 1);
      for (let i=0;i<15;i++) a['increase' + kind + 'Level'](); assert.strictEqual(h.level(kind === 'Music' ? 'music' : 'sfx'), 10);
      for (let i=0;i<15;i++) a['decrease' + kind + 'Level'](); assert.strictEqual(h.level(kind === 'Music' ? 'music' : 'sfx'), 0);
      a['set' + kind](true); assert.strictEqual(h.level(kind === 'Music' ? 'music' : 'sfx'), 1);
    }
  });
  test(engine, 'saved OFF/zero reload preserves memory and original mute choice', () => {
    const h=fresh(); h.manager.setMusicLevel(4); h.manager.setSFXLevel(7); h.manager.setMusic(false); h.manager.setSFXLevel(0);
    const next=fresh(JSON.parse(h.storage.raw)); assert.strictEqual(next.level('music'),0); assert.strictEqual(next.level('sfx'),0);
    next.manager.setMusic(true); next.manager.setSFX(true); assert.strictEqual(next.level('music'),4); assert.strictEqual(next.level('sfx'),7);
    const legacy=fresh({musicOn:false,sfxOn:false,musicLevel:3,sfxLevel:6}); assert.strictEqual(legacy.level('music'),0);
    legacy.manager.setMusic(true); legacy.manager.setSFX(true); assert.strictEqual(legacy.level('music'),3); assert.strictEqual(legacy.level('sfx'),6);
  });
  test(engine, 'zero without history restores unchanged default ten', () => {
    const h=fresh({musicOn:true,sfxOn:true,musicLevel:0,sfxLevel:0}); assert.strictEqual(h.on('music'),false);
    h.manager.setMusic(true); h.manager.setSFX(true); assert.strictEqual(h.level('music'),10); assert.strictEqual(h.level('sfx'),10);
  });
  test(engine, 'pending BGM callback after OFF cannot start', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.manager.setMusic(false); h.resolve('menu'); h.fades(); assert.strictEqual(h.plays(),0);
  });
  test(engine, 'same id OFF then ON cannot resurrect old BGM request', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.manager.setMusic(false); h.manager.setMusic(true);
    h.resolve('menu'); assert.strictEqual(h.plays(),0); h.resolve('menu'); h.fades(); assert.strictEqual(h.sounding('menu').length,1);
  });
  test(engine, 'new BGM invalidates prior loading request', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.manager.playBGM('bgm_game'); h.resolve('menu'); assert.strictEqual(h.plays(),0);
    h.resolve('game'); h.fades(); assert.strictEqual(h.sounding('game').length,1);
  });
  test(engine, 'active BGM and fade immediately silent at OFF/zero', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.resolve('menu'); h.fades(); assert.strictEqual(h.sounding().length,1);
    h.manager.setMusic(false); assert.strictEqual(h.sounding().length,0); h.fades(); assert.strictEqual(h.sounding().length,0);
    h.manager.setMusic(true); h.fades(); assert.strictEqual(h.sounding().length,1); h.manager.setMusicLevel(0); assert.strictEqual(h.sounding().length,0);
  });
  test(engine, 'pending SFX callback after OFF or pause cannot start', () => {
    for (const action of ['off','pause']) { const h=fresh(); h.manager.playSFX('sfx_ui_click');
      if(action==='off') h.manager.setSFX(false); else {h.manager.pause('ad');h.manager.resume('ad');}
      h.resolve('click'); assert.strictEqual(h.plays(),0); }
  });
  test(engine, 'active SFX immediately silent and cannot revive after ON', () => {
    const h=fresh(); h.manager.playSFX('sfx_ui_click'); h.resolve('click'); assert.strictEqual(h.sounding('click').length,1);
    h.manager.setSFX(false); assert.strictEqual(h.sounding('click').length,0); h.manager.setSFX(true); assert.strictEqual(h.sounding('click').length,0);
  });
  test(engine, 'active SFX volume follows current positive level', () => {
    const h=fresh(); h.manager.playSFX('sfx_ui_click'); h.resolve('click'); h.manager.setSFXLevel(5);
    assert.strictEqual(h.sounding('click')[0].volume,0.4);
  });
  test(engine, 'music and SFX buses remain independent including jingle', () => {
    const h=fresh(); h.manager.playSFX('sfx_ui_click'); h.resolve('click'); h.manager.playJingle('jingle_win'); h.resolve('win');
    h.manager.setSFX(false); assert.strictEqual(h.sounding('click').length,0); assert.strictEqual(h.sounding('win').length,1);
    h.manager.setMusic(false); assert.strictEqual(h.sounding('win').length,0);
  });
  test(engine, 'pending jingle callback after mute cannot start', () => {
    const h=fresh(); h.manager.playJingle('jingle_win'); h.manager.setMusic(false); h.resolve('win'); assert.strictEqual(h.plays(),0);
  });
  test(engine, 'old jingle timer cannot stop newly chosen BGM', () => {
    const h=fresh(); h.manager.playJingle('jingle_win'); h.resolve('win'); h.manager.playBGM('bgm_game'); h.resolve('game'); h.fades();
    h.once(); h.fades(); assert.strictEqual(h.sounding('game').length,1);
  });
  test(engine, 'ad and background need both resume reasons; mute never auto-enables', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.resolve('menu'); h.fades(); h.manager.pause('ad'); h.manager.pause('hide');
    h.manager.resume('hide'); h.fades(); assert.strictEqual(h.sounding().length,0);
    h.manager.setMusic(false); h.manager.resume('ad'); h.fades(); assert.strictEqual(h.sounding().length,0); assert.strictEqual(h.on('music'),false);
  });
  test(engine, 'pending callback invalidated by pause and allowed resume is fresh', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.manager.pause('ad'); h.manager.pause('hide'); h.manager.resume('hide');
    h.resolve('menu'); assert.strictEqual(h.plays(),0); h.manager.resume('ad'); h.fades(); assert.strictEqual(h.sounding().length,1);
  });
  test(engine, 'resume while new clip pending never plays previous clip', () => {
    const h=fresh(); h.manager.playBGM('bgm_menu'); h.resolve('menu'); h.fades(); h.manager.pause('ad'); h.manager.playBGM('bgm_game');
    h.manager.resume('ad'); assert.strictEqual(h.sounding('menu').length,0); h.resolve('game'); h.fades(); assert.strictEqual(h.sounding('game').length,1);
  });
  test(engine, 'SFX concurrency rechecked at async completion and cleanup cannot undercount', () => {
    const h=fresh(); for(let i=0;i<8;i++) { h.manager.lastPlayTime && h.manager.lastPlayTime.clear(); if(h.manager._lastPlay) h.manager._lastPlay={}; h.manager.playSFX('sfx_ui_click'); }
    while(h.pending.length) h.resolve('click'); assert.strictEqual(h.sounding('click').length,6);
    h.manager.setSFX(false); h.manager.setSFX(true); h.manager.playSFX('sfx_coin'); h.resolve('coin'); assert.strictEqual(h.sounding('coin').length,1);
    h.finish('coin'); h.once(); assert.strictEqual(h.manager._activeSfx === undefined ? h.manager.activeSfx : h.manager._activeSfx,0);
  });
  test(engine, 'load and persistence failures keep state coherent and retry usable', () => {
    const h=fresh(); h.storage.fail=true; h.manager.setMusicLevel(4); h.manager.setMusic(false); assert.strictEqual(h.level('music'),0);
    assert(h.warnings.length); h.storage.fail=false; h.manager.setMusic(true); assert.strictEqual(JSON.parse(h.storage.raw).musicLevel,4);
    while(h.pending.length) h.resolve('menu',true); assert.strictEqual(h.plays(),0); h.manager.playBGM('bgm_menu'); h.resolve('menu'); h.fades(); assert.strictEqual(h.sounding().length,1);
  });
  test(engine, 'first gesture never unlocks muted pending audio', () => {
    const h=load(engine,undefined,true); h.manager.playBGM('bgm_menu'); h.manager.setMusic(false); h.manager.unlock();
    assert.strictEqual(h.pending.length,0); assert.strictEqual(h.plays(),0);
  });
  test(engine, 'destroy invalidates callbacks and stops only managed sources', () => {
    const h=fresh(); h.manager.playSFX('sfx_ui_click'); h.manager.playBGM('bgm_menu'); h.manager.onDestroy();
    h.resolve('click'); h.resolve('menu'); assert.strictEqual(h.plays(),0);
  });
  test(engine, 'scheduled coin action cannot replay after mute toggle or ad resume', () => {
    for(const action of ['mute','pause']) { const h=fresh(); h.manager.playCoins(3);
      if(action==='mute') {h.manager.setSFX(false);h.manager.setSFX(true);} else {h.manager.pause('ad');h.manager.resume('ad');}
      h.once(); assert.strictEqual(h.pending.length,0); assert.strictEqual(h.plays(),0); }
  });
  test(engine, 'enabling music while paused remembers intended loop but starts only after resume', () => {
    const h=fresh({musicOn:false,musicLevel:7}); h.manager.pause('ad'); h.manager.setMusic(true);
    assert.strictEqual(h.pending.length,0); h.manager.resume('ad'); h.resolve('menu'); h.fades(); assert.strictEqual(h.sounding('menu').length,1);
  });
  test(engine, 'stopping locked BGM clears pending first gesture intent', () => {
    const h=load(engine,undefined,true); h.manager.playBGM('bgm_menu'); h.manager.stopBGM(); h.manager.unlock();
    assert.strictEqual(h.pending.length,0); assert.strictEqual(h.plays(),0);
  });
  if(engine==='3.x') test(engine, 'cleanup timer cannot truncate playing managed source; natural end cleans only matching source', () => {
    const h=fresh(); h.manager.playSFX('sfx_ui_click');h.resolve('click');h.manager.playSFX('sfx_coin');h.resolve('coin');
    h.once();assert.strictEqual(h.sounding().length,2);h.finish('click');assert.strictEqual(h.sounding('coin').length,1);
    assert.strictEqual(h.manager.activeSfx,1);h.finish('coin');assert.strictEqual(h.manager.activeSfx,0);
  });
  test(engine, 'save failure is observable and explicit retry preserves current independent settings', () => {
    const h=fresh();h.storage.fail=true;h.manager.setSFXLevel(3);
    assert.strictEqual(engine==='2.4'?h.manager.isSettingsSaved():h.manager.settingsSaved,false);
    assert.strictEqual(h.manager.retrySaveSettings(),false);h.storage.fail=false;assert.strictEqual(h.manager.retrySaveSettings(),true);
    assert.strictEqual(engine==='2.4'?h.manager.isSettingsSaved():h.manager.settingsSaved,true);
    assert.strictEqual(JSON.parse(h.storage.raw).sfxLevel,3);assert.strictEqual(JSON.parse(h.storage.raw).musicLevel,10);
  });
  test(engine, 'volume edit during BGM transition does not strand previous clip', () => {
    const h=fresh();h.manager.playBGM('bgm_menu');h.resolve('menu');h.fades();h.manager.playBGM('bgm_game');h.manager.setMusicLevel(4);
    h.fades();h.resolve('game');h.fades();assert.strictEqual(h.sounding('menu').length,0);assert.strictEqual(h.sounding('game').length,1);
  });
  test(engine, 'positive music volume edit preserves current jingle completion behavior', () => {
    const h=fresh();h.manager.playBGM('bgm_menu');h.resolve('menu');h.fades();h.manager.playJingle('jingle_win');h.resolve('win');
    h.manager.setMusicLevel(4);h.once();h.fades();assert.strictEqual(h.sounding('menu').length,0);
  });
}
const report = { root, typescript: ts && ts.version, tests: results.length, passed: results.filter(r=>r.passed).length,
  failed: results.filter(r=>!r.passed).length, results, scope: 'Real production template modules under controlled Cocos API/resource/storage boundaries; no real PCM, renderer, browser or game.' };
const out = option('--out'); if(out) fs.writeFileSync(out, JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2)); process.exitCode = report.failed ? 1 : 0;
