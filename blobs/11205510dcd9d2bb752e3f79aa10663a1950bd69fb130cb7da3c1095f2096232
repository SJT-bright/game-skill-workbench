'use strict';
// node tests/run-session.test.js  -- parts/RunSession.js (生成时预防 P11 + P18 move): pause counted per reason, EVENT_HIDE
// held until EVENT_SHOW, newRun rebuilds the whole per-run state, guarded callbacks and timers of an old run are dropped,
// a scene launch / dispose clears timers, movement per second is the same at 60 Hz and 120 Hz, 2.4 and 3.x.
// Negative controls (the shapes the 问题普查 found, written the old way) must FAIL the same checks:
//   甜点消消乐 / 密室消除: one `paused` boolean shared by popup and ad
//   割草 / Pinecone: run data in loose fields, retry resets only some of them
//   大西瓜之见缝插针: old level's collision callback sets IsHit on the new level; setInterval opened per scene entry
//   per-frame movement: node.x += 5 every frame (割草、这也太牛了 60/120 Hz)
var assert = require('assert');
var path = require('path');
// RUN_SESSION_FILE: run the same checks on a broken copy (mutation check in the patch's test record)
var FILE = process.env.RUN_SESSION_FILE || path.join(__dirname, '..', 'parts', 'RunSession.js');
delete require.cache[require.resolve(FILE)];
var RunSession = require(FILE);

function emitter() {
  var h = {};
  return {
    on: function (e, f) { (h[e] = h[e] || []).push(f); },
    off: function (e, f) { h[e] = (h[e] || []).filter(function (g) { return g !== f; }); },
    emit: function (e) { (h[e] || []).slice().forEach(function (f) { f(); }); },
    count: function (e) { return (h[e] || []).length; }
  };
}
function fakeCc24() {
  var game = emitter(), director = emitter();
  game.EVENT_HIDE = 'game_on_hide'; game.EVENT_SHOW = 'game_on_show';
  return { game: game, director: director, Director: { EVENT_BEFORE_SCENE_LAUNCH: 'director_before_scene_launch' },
    isValid: function (n) { return !!n && n.isValid !== false; } };
}
function fakeCc3() {
  var game = emitter(), director = emitter();
  return { game: game, director: director, UITransform: function () {},
    Game: { EVENT_HIDE: 'game_on_hide', EVENT_SHOW: 'game_on_show' },
    Director: { EVENT_BEFORE_SCENE_LAUNCH: 'director_before_scene_launch' },
    isValid: function (n) { return !!n && n.isValid !== false; } };
}
var quiet = { warn: function () {} };
function mk(cc, o) { var x = Object.assign({}, quiet, o || {}); return RunSession.create(cc, x); }

// ---- shared scenarios: each takes an "api" {pause(r), resume(r), isPaused(), hide(), show()} ----
function popupThenAd(api) { api.pause('popup'); api.pause('ad'); api.resume('ad'); return api.isPaused(); }
function hideThenClosePopup(api) { api.hide(); api.resume('popup'); return api.isPaused(); }

function sessionApi(cc) {
  var s = mk(cc);
  return { s: s, pause: s.pause, resume: s.resume, isPaused: s.isPaused,
    hide: function () { cc.game.emit('game_on_hide'); }, show: function () { cc.game.emit('game_on_show'); } };
}
// 甜点消消乐 shape: a single boolean, every pause/resume writes it
function booleanApi() {
  var paused = false;
  return { pause: function () { paused = true; }, resume: function () { paused = false; }, isPaused: function () { return paused; },
    hide: function () { paused = true; }, show: function () { paused = false; } };
}
var results = [];
function check(name, fn) { fn(); results.push(name); }

// 1. pause counted per reason
check('pause by reason', function () {
  var a = sessionApi(fakeCc24());
  assert.strictEqual(popupThenAd(a), true, "pause('popup'), pause('ad'), resume('ad') -> still paused");
  assert.deepStrictEqual(a.s.reasons(), ['popup']);
  assert.strictEqual(a.s.tick(1 / 60), 0, 'tick returns 0 while paused');
  a.resume('popup');
  assert.strictEqual(a.isPaused(), false);
  assert.ok(Math.abs(a.s.tick(1 / 60) - 1 / 60) < 1e-12, 'tick returns dt when running');
  // nested popups: two holds, one release -> still paused; release() is idempotent; unknown reason ignored
  var r1 = a.s.pause('popup'); a.s.pause('popup');
  r1(); r1();
  assert.strictEqual(a.isPaused(), true, 'second popup still open');
  a.resume('nothing'); a.resume('popup'); a.resume('popup');
  assert.strictEqual(a.isPaused(), false);
  assert.deepStrictEqual(a.s.reasons(), []);
  // negative control
  assert.strictEqual(popupThenAd(booleanApi()), false, 'negative control: one boolean resumes while the popup is open');
});

// 2. EVENT_HIDE holds until EVENT_SHOW, whatever else is released
check('hide/show', function () {
  var cc = fakeCc24(), a = sessionApi(cc);
  a.pause('popup');
  assert.strictEqual(hideThenClosePopup(a), true, "EVENT_HIDE then resume('popup') -> still paused");
  cc.game.emit('game_on_hide');                             // a second hide does not stack
  cc.game.emit('game_on_show');
  assert.strictEqual(a.isPaused(), false, 'EVENT_SHOW releases hide');
  a.pause('popup'); a.s.resumeAll();
  assert.strictEqual(a.isPaused(), false, 'resumeAll');
  cc.game.emit('game_on_hide'); a.s.resumeAll();
  assert.strictEqual(a.isPaused(), true, 'resumeAll keeps hide');
  cc.game.emit('game_on_show');
  var b = booleanApi(); b.pause('popup');
  assert.strictEqual(hideThenClosePopup(b), false, 'negative control: boolean resumes in the background');
  // autoHide:false listens to nothing
  var cc2 = fakeCc24(); mk(cc2, { autoHide: false });
  assert.strictEqual(cc2.game.count('game_on_hide'), 0);
});

// 3. newRun rebuilds the whole state (割草 score, Pinecone revives)
check('newRun resets', function () {
  var s = mk(fakeCc24());
  function init() { return { score: 0, revives: 1, hit: false }; }
  var first = s.newRun(init);
  s.state.score = 120; s.state.revives = 0; s.state.hit = true;
  var second = s.newRun(init);
  assert.notStrictEqual(first, second, 'a new object');
  assert.deepStrictEqual(s.state, { score: 0, revives: 1, hit: false }, 'retry starts from the initial values');
  assert.strictEqual(s.run, 2);
  var third = s.newRun(function (st) { st.score = 0; });     // init may fill the given object
  assert.deepStrictEqual(third, { run: 3, score: 0 });
  // negative control: loose fields, retry resets the score only (Pinecone forgot revives; 割草 shared the score)
  var game = { score: 0, revives: 1, retry: function () { this.score = 0; } };
  game.score = 120; game.revives = 0; game.retry();
  assert.notDeepStrictEqual({ score: game.score, revives: game.revives }, { score: 0, revives: 1 },
    'negative control: the old shape keeps revives at 0 after retry');
});

// 4. guarded callbacks of an old run are dropped (大西瓜 IsHit), once() runs one time, a destroyed owner drops them
check('guard / once / owner', function () {
  var cc = fakeCc24(), s = mk(cc);
  s.newRun(function () { return { hit: false }; });
  var oldHit = s.guard(function () { s.state.hit = true; return 'ran'; });
  s.newRun(function () { return { hit: false }; });
  assert.strictEqual(oldHit(), undefined, 'old collision callback does nothing');
  assert.strictEqual(s.state.hit, false, 'new level not marked as hit');
  var nowHit = s.guard(function () { s.state.hit = true; return 'ran'; });
  assert.strictEqual(nowHit(), 'ran');
  var n = 0, grant = s.once(function () { n += 1; });
  grant(); grant();
  assert.strictEqual(n, 1, 'once');
  var owner = { isValid: true }, s2 = mk(cc, { owner: owner }), touched = 0;
  var load = s2.guard(function () { touched += 1; });
  owner.isValid = false;
  load();
  assert.strictEqual(touched, 0, 'texture callback after the owner was destroyed does nothing');
  assert.throws(function () { s.guard(undefined); }, /not a function/, 'guard(undefined) throws at wiring time');
  // negative control: a plain callback still runs on the new level
  var IsHit = false, plain = function () { IsHit = true; };
  IsHit = false;  // "new level"
  plain();
  assert.strictEqual(IsHit, true, 'negative control: plain callback marks the new level');
});

// 5. timers: die with newRun / dispose / scene launch; do not run while paused; at most once per frame
check('timers', function () {
  var cc = fakeCc24(), s = mk(cc), ticks = 0;
  s.newRun();
  s.every(1000, function () { ticks += 1; });
  for (var i = 0; i < 60; i++) s.tick(1 / 60);
  assert.strictEqual(ticks, 1, 'fired after 1 s');
  var release = s.pause('popup');
  for (i = 0; i < 120; i++) s.tick(1 / 60);
  assert.strictEqual(ticks, 1, 'no ticks while paused');
  release();
  for (i = 0; i < 60; i++) s.tick(1 / 60);
  assert.strictEqual(ticks, 2);
  s.newRun();
  for (i = 0; i < 180; i++) s.tick(1 / 60);
  assert.strictEqual(ticks, 2, 'old run timer dropped by newRun');
  var once = 0; s.after(500, function () { once += 1; });
  s.tick(5);                                                 // one long frame: clamped to maxDt 0.1 s
  assert.strictEqual(once, 0, 'a 5 s hitch only advances 0.1 s');
  for (i = 0; i < 30; i++) s.tick(1 / 60);
  assert.strictEqual(once, 1);
  var h = s.every(100, function () { once += 100; }); h.cancel();
  for (i = 0; i < 30; i++) s.tick(1 / 60);
  assert.strictEqual(once, 1, 'cancel');
  // a timer that starts a new run stops the old run's other timers in the same frame
  var later = 0;
  s.after(10, function () { s.newRun(); });
  s.after(10, function () { later += 1; });
  s.tick(1 / 60);
  assert.strictEqual(later, 0, 'newRun from a timer drops the rest of the old run');
  // scene launch: 3 entries of the scene = 1 live timer, the old scenes' timers are gone (大西瓜 setInterval)
  var live = 0;
  function enterSceneWithSession() {
    cc.director.emit('director_before_scene_launch');
    var sc = mk(cc); sc.newRun(); sc.every(500, function () { live += 1; }); return sc;
  }
  var last;
  for (i = 0; i < 3; i++) last = enterSceneWithSession();
  live = 0;
  // every scene's session is ticked by its own (possibly still running) update; only the newest is alive
  for (i = 0; i < 30; i++) last.tick(1 / 60);
  assert.strictEqual(live, 1, 'one timer per scene');
  assert.strictEqual(cc.director.count('director_before_scene_launch'), 1, 'disposed sessions stop listening');
  last.dispose();
  for (i = 0; i < 60; i++) last.tick(1 / 60);
  assert.strictEqual(live, 1, 'dispose stops timers');
  assert.strictEqual(cc.game.count('game_on_hide'), 0, 'every session of the old scenes (and s) was disposed by the launches');
  assert.strictEqual(s.tick(1 / 60), 0, 's was disposed by the first scene launch');
  // negative control: setInterval per scene entry, never cleared
  var intervals = [];
  var fakeSetInterval = function (fn) { intervals.push(fn); };
  for (i = 0; i < 3; i++) fakeSetInterval(function () {});
  assert.notStrictEqual(intervals.length, 1, 'negative control: setInterval per entry leaves 3 timers');
  assert.throws(function () { s.every(0, function () {}); }, /interval/);
});

// 6. ad-boost runAd hooks: reason 'ad', paired
check('adHooks', function () {
  var s = mk(fakeCc24()), hooks = s.adHooks();
  s.pause('revive');
  hooks.pauseGame({ placementKey: 'revive' });
  hooks.resumeGame({ rewarded: true });
  assert.deepStrictEqual(s.reasons(), ['revive'], 'ad end does not resume the revive popup');
  hooks.resumeGame({});                                      // an extra resume does nothing
  s.resume('revive');
  assert.strictEqual(s.isPaused(), false);
});

// 7. move per second: same distance at 60 Hz and 120 Hz; 2.4 and 3.x node shapes
check('move', function () {
  function runFor(hz, cc, node, perFrameOldWay) {
    var s = mk(cc); s.newRun();
    for (var i = 0; i < hz * 2; i++) {
      var d = s.tick(1 / hz);
      if (perFrameOldWay) node.x += 5; else s.move(node, 300, -60, d);
    }
    return node;
  }
  var a = runFor(60, fakeCc24(), { x: 0, y: 0 }), b = runFor(120, fakeCc24(), { x: 0, y: 0 });
  assert.ok(Math.abs(a.x - 600) < 1e-6 && Math.abs(b.x - 600) < 1e-6, '2 s at 300/s = 600 at both rates');
  assert.ok(Math.abs(a.y + 120) < 1e-6 && Math.abs(b.y + 120) < 1e-6);
  function node3() { var p = { x: 0, y: 0, z: 7 }; return { position: p, setPosition: function (x, y, z) { p.x = x; p.y = y; p.z = z; } }; }
  var c = runFor(120, fakeCc3(), node3());
  assert.ok(Math.abs(c.position.x - 600) < 1e-6 && c.position.z === 7, '3.x setPosition keeps z');
  var paused = mk(fakeCc24()), n = { x: 0, y: 0 }; paused.pause('popup');
  paused.move(n, 300, 0, paused.tick(1 / 60));
  assert.strictEqual(n.x, 0, 'no movement while paused');
  assert.strictEqual(RunSession.step(10, 90, 0.5), 55);
  var o60 = runFor(60, fakeCc24(), { x: 0, y: 0 }, true), o120 = runFor(120, fakeCc24(), { x: 0, y: 0 }, true);
  assert.ok(Math.abs(o120.x - o60.x) / o60.x > 0.5, 'negative control: += 5 per frame goes twice as far at 120 Hz');
});

// 8. 3.x events (cc.Game.EVENT_HIDE), onPause/onResume edges
check('3.x and edges', function () {
  var cc = fakeCc3(), edges = [];
  var s = mk(cc, { onPause: function (r) { edges.push('pause:' + r.join(',')); }, onResume: function () { edges.push('resume'); } });
  cc.game.emit('game_on_hide');
  s.pause('ad');
  cc.game.emit('game_on_show');
  s.resume('ad');
  assert.deepStrictEqual(edges, ['pause:hide', 'resume'], 'only the edges are reported');
  s.dispose();
  assert.strictEqual(cc.game.count('game_on_hide'), 0, 'dispose stops listening');
  assert.strictEqual(s.newRun(), null);
  assert.strictEqual(s.tick(1 / 60), 0);
});

// 9. the module carries no game names and no engine timers
var code = require('fs').readFileSync(FILE, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
['setInterval', 'setTimeout', 'schedule(', 'IsHit', 'globalData'].forEach(function (n) { assert.ok(code.indexOf(n) < 0, n); });
results.push('no engine timers in the part');

console.log('run-session: ' + results.length + ' groups passed (' + results.join('; ') + ')');
