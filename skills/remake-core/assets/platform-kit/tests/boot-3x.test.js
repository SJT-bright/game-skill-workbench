'use strict';
// parts-3x/boot-guard-3x.js (Cocos 3.x startup guard) against a fake 3.x engine and a fake TikTok runtime, on a
// virtual clock (no real waiting: the whole file runs in about a second).
// The fake engine starts like cc.game.init + run in 3.x: loadBundle('main') -> loadBundle('resources') ->
// director.loadScene('Home'); a step that reports an error rejects init (frozen loading screen). Its downloader
// keeps handlers in _downloaders and register(), and a failed scene stays in assetManager._files like 2.4/3.x.
// The old-way fixture is the hand-written 3.x wait found in TrashPanda / 恢复线场 / 美女快跑 (问题普查 2026-11-04,
// startup_false_timeout): one fixed 15 s wall-clock deadline. It MUST misjudge the slow-but-moving and the
// background cases; the kit guard must not.
// It does NOT prove a real phone or a real 3.x engine (待真机复测; 3.7.1 / 3.8.8 host runs not done yet).
// Usage: node tests/boot-3x.test.js               -> cases, then negative controls (each mutant MUST fail)
//        BOOT3X=/path/file.js node tests/boot-3x.test.js   -> cases only, on that file
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var KIT_FILE = path.join(__dirname, '..', 'parts-3x', 'boot-guard-3x.js');
var target = process.env.BOOT3X || KIT_FILE;
var results = [];
function fresh() { delete require.cache[require.resolve(target)]; return require(target); }
function test(name, run) {
  var err = console.error; console.error = function () {};
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
  finally { console.error = err; }
}

// ---- virtual clock ----
function Clock() { this.t = 0; this.q = []; this.seq = 0; this.frameMs = 16; }
Clock.prototype.now = function () { return this.t; };
Clock.prototype.setTimeout = function (f, ms) { var id = ++this.seq; this.q.push({id: id, at: this.t + (ms || 0), f: f}); return id; };
Clock.prototype.clearTimeout = function (id) { this.q = this.q.filter(function (x) { return x.id !== id; }); };
Clock.prototype.setInterval = function (f, ms) { var id = ++this.seq; this.q.push({id: id, at: this.t + ms, f: f, every: ms}); return id; };
Clock.prototype.clearInterval = Clock.prototype.clearTimeout;
Clock.prototype.raf = function (f) { return this.setTimeout(f, this.frameMs); };
Clock.prototype.advance = function (ms) {
  var end = this.t + ms;
  for (;;) {
    var next = null;
    this.q.forEach(function (x) { if (x.at <= end && (!next || x.at < next.at || (x.at === next.at && x.id < next.id))) next = x; });
    if (!next) break;
    this.t = next.at;
    if (next.every) next.at += next.every; else this.q.splice(this.q.indexOf(next), 1);
    next.f();
  }
  this.t = end;
};
function bind(clock) {
  var c = {};
  ['now', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'raf'].forEach(function (k) { c[k] = clock[k].bind(clock); });
  return c;
}

// ---- fake TikTok runtime ----
function fakeSdk() {
  var sdk = {modal: [], loading: [], hide: 0, toast: 0, handlers: {}};
  sdk.showModal = function (o) { sdk.modal.push(o); };
  sdk.showLoading = function (o) { sdk.loading.push(o.title); };
  sdk.hideLoading = function () { sdk.hide++; };
  sdk.showToast = function () { sdk.toast++; };
  sdk.onHide = function (f) { sdk.handlers.hide = f; };
  sdk.onShow = function (f) { sdk.handlers.show = f; };
  sdk.tapRetry = function () { var m = sdk.modal[sdk.modal.length - 1]; m.success({confirm: true}); };
  return sdk;
}
function fakeCache() {
  var map = {};
  return {map: map, has: function (k) { return k in map; }, add: function (k, v) { map[k] = v; return v; },
    remove: function (k) { var v = map[k]; delete map[k]; return v; }};
}

// ---- fake 3.x engine ----
// sc.file(call, clock): answers one raw file request (call.url, call.n = how many times this url was asked, call.done)
function makeEngine(clock, sc) {
  sc = sc || {};
  var calls = [], engine = {frozen: false, launched: [], sceneCb: 0};
  function count(url) { return calls.filter(function (x) { return x.url === url; }).length; }
  function rawFile(kind) {
    return function (url, options, done) {
      var c = {kind: kind, url: url, done: done, n: count(url) + 1, at: clock.t};
      calls.push(c);
      if (engine.hangFirst === url && c.n === 1) return;
      (sc.file || function (x) { clock.setTimeout(function () { x.done(null, {url: x.url}); }, 100); })(c, clock);
    };
  }
  var downloader = {_downloaders: {'.json': rawFile('json'), '.png': rawFile('png'), bundle: rawFile('bundle')}, maxRetryCount: 3,
    register: function (ext, fn) { this._downloaders[ext] = fn; }};
  engine.rawHandlers = Object.assign({}, downloader._downloaders);
  function ext(u) { return /\.bundle$/.test(u) ? 'bundle' : u.slice(u.lastIndexOf('.')); }
  function loadFiles(list, done) {
    var i = 0;
    (function next(err) {
      if (err) { done(err); return; }
      if (i >= list.length) { done(null); return; }
      var u = list[i++];
      downloader._downloaders[ext(u)](u, {}, function (e) { next(e || null); });
    })();
  }
  var files = fakeCache();
  var am = {downloader: downloader, parser: {register: function () {}}, _files: files, _parsed: fakeCache(),
    bundles: {find: function (fn) { var b = {getSceneInfo: function (n) { return n === 'Home' ? {uuid: 'home'} : null; }}; return fn(b) ? b : null; }},
    loadBundle: function (name, options, cb) {
      if (typeof options === 'function') cb = options;
      var bundleFiles = (sc.bundleFiles || {})[name] || [name + '/config.json'];
      engine.bundleCalls = (engine.bundleCalls || 0) + 1;
      if (sc.lateError && engine.bundleCalls === 1) clock.setTimeout(function () { cb(new Error('late answer of the first request')); }, sc.lateError);
      loadFiles(['remote/' + name + '/index.bundle'].concat(bundleFiles), function (e) {
        cb(e, e ? null : {name: name});
        if (sc.doubleCallback) cb(e, e ? null : {name: name});  // an engine path that answers twice
      });
    }};
  var director = {_loadingScene: '', loadScene: function (name, onLaunched) {
    var self = this;
    if (self._loadingScene || name !== 'Home') return false;
    var id = 'home@import';
    self._loadingScene = name;
    if (files.has(id)) {  // deserialized in place last time: a second deserialize fails at once
      clock.setTimeout(function () { self._loadingScene = ''; onLaunched && onLaunched(new Error('Can not deserialize the same JSON data again')); }, 0);
      return true;
    }
    files.add(id, {deserialized: true});
    loadFiles(sc.sceneFiles || ['scene/home.json', 'scene/bg.png'], function (err) {
      self._loadingScene = '';
      if (err) { onLaunched && onLaunched(err); return; }  // entry kept on a dependency error, like the engine
      files.remove(id);
      clock.setTimeout(function () { engine.launched.push(name); engine.sceneCb++; onLaunched && onLaunched(null, {name: name}); }, 16);
    });
    return true;
  }};
  engine.cc = {assetManager: am, director: director};
  engine.calls = calls;
  engine.boot = function (onHome) {
    am.loadBundle('main', function (e) {
      if (e) { engine.frozen = true; return; }
      am.loadBundle('resources', function (e2) {
        if (e2) { engine.frozen = true; return; }
        var ok = director.loadScene('Home', function (e3) { if (e3) { engine.frozen = true; return; } if (onHome) onHome(); });
        if (ok === false) engine.frozen = true;
      });
    });
  };
  return engine;
}

// Old way: the hand-written 3.x startup wait (TrashPanda / 恢复线场 / 美女快跑 before their fix).
function oldFixedDeadlineBoot(engine, sdk, clock) {
  var state = {home: false, failedAt: null};
  clock.setTimeout(function () {  // one total deadline, wall clock (background counted, progress ignored)
    if (!state.home) { state.failedAt = clock.t; sdk.showModal({title: 'Load failed', success: function () {}}); }
  }, 15000);
  engine.boot(function () { state.home = true; });
  return state;
}

function start(sc, opts) {
  opts = opts || {};
  var clock = new Clock(), sdk = fakeSdk(), engine = makeEngine(clock, sc);
  var guard = opts.noGuard ? null : fresh().install(engine.cc, sdk, {clock: bind(clock), root: {}, homeScene: opts.homeScene});
  var run = {clock: clock, sdk: sdk, engine: engine, guard: guard, homeAt: null};
  if (opts.old) run.old = oldFixedDeadlineBoot(engine, sdk, clock);
  else engine.boot(function () { run.homeAt = clock.t; });
  return run;
}
// slow but moving: 12 resource files, one every 1.5 s (about 18 s in all)
var SLOW = {bundleFiles: {resources: Array.apply(null, Array(12)).map(function (_, i) { return 'res/' + i + '.png'; })},
  file: function (c, clock) { clock.setTimeout(function () { c.done(null, {}); }, /^res\//.test(c.url) ? 1500 : 100); }};

test('old_fixed_15s_deadline_misjudges_slow_download', function () {
  var r = start(SLOW, {old: true, noGuard: true});
  r.clock.advance(40000);
  assert.strictEqual(r.old.failedAt, 15000, 'fixture: Retry at 15 s while files still arrive');
  assert.strictEqual(r.old.home, true, 'and the home page came up behind the dialog');
});
test('slow_but_moving_download_no_false_retry', function () {
  var r = start(SLOW);
  r.clock.advance(40000);
  assert.strictEqual(r.sdk.modal.length, 0, 'no Retry');
  assert.ok(r.homeAt > 15000 && r.homeAt < 25000, 'home at ' + r.homeAt);
  assert.strictEqual(r.guard.status().started, true);
  assert.ok(r.sdk.hide >= 1, 'loading hidden');
  var pcts = r.sdk.loading.map(function (t) { return parseInt(t.replace(/\D+/g, ''), 10); });
  assert.ok(pcts.length >= 5 && pcts[pcts.length - 1] > pcts[0], 'Loading N% moves: ' + pcts.join(','));
});
// background: resources files only answer once the app is back in front (hidden 2 s .. 42 s)
var BG = {file: function (c, clock) {
  var due = c.url === 'resources/config.json' ? 43000 : clock.t + 100;
  clock.setTimeout(function () { c.done(null, {}); }, Math.max(100, due - clock.t));
}};
function hideBetween(r, a, b) {
  r.clock.setTimeout(function () { r.sdk.handlers.hide && r.sdk.handlers.hide(); if (r.old) r.hidden = true; }, a);
  r.clock.setTimeout(function () { r.sdk.handlers.show && r.sdk.handlers.show(); }, b);
}
test('old_deadline_counts_background_time', function () {
  var r = start(BG, {old: true, noGuard: true});
  r.clock.advance(60000);
  assert.strictEqual(r.old.failedAt, 15000, 'fixture: failed while the app was in the background');
});
test('background_time_not_counted', function () {
  var r = start(BG);
  hideBetween(r, 2000, 42000);
  r.clock.advance(60000);
  assert.strictEqual(r.sdk.modal.length, 0, 'no Retry: ' + JSON.stringify(r.guard.status()));
  var asked = r.engine.calls.filter(function (c) { return c.url === 'resources/config.json'; }).length;
  assert.strictEqual(asked, 1, 'not re-requested while hidden');
  assert.ok(r.homeAt !== null, 'home came up');
});
// a bundle request that never answers the first time; asked again it answers
var BUNDLE_HANG = {file: function (c, clock) {
  if (c.url === 'remote/resources/index.bundle' && c.n === 1) return;
  clock.setTimeout(function () { c.done(null, {}); }, 100);
}};
test('no_guard_hanging_bundle_is_frozen_forever', function () {
  var r = start(BUNDLE_HANG, {noGuard: true});
  r.clock.advance(120000);
  assert.strictEqual(r.homeAt, null); assert.strictEqual(r.sdk.modal.length, 0, 'fixture: no Retry ever');
});
test('hanging_bundle_retry_within_10s_and_one_retry_enters', function () {
  var r = start(BUNDLE_HANG);
  r.clock.advance(10500);
  assert.strictEqual(r.sdk.modal.length, 1, 'Retry visible by 10.5 s: ' + JSON.stringify(r.guard.status()));
  assert.strictEqual(r.homeAt, null);
  assert.strictEqual(r.engine.frozen, false, 'engine never saw the failure');
  r.sdk.tapRetry();
  r.clock.advance(5000);
  assert.ok(r.homeAt !== null, 'one Retry enters');
  assert.strictEqual(r.sdk.modal.length, 1);
});
// one image never answers the first time; the 10 s re-request answers
var FILE_HANG = {file: function (c, clock) {
  if (c.url === 'scene/bg.png' && c.n === 1) return;
  clock.setTimeout(function () { c.done(null, {}); }, 100);
}};
test('stuck_file_re_requested_at_10s_without_retry_dialog', function () {
  var r = start(FILE_HANG);
  r.clock.advance(15000);
  var asks = r.engine.calls.filter(function (c) { return c.url === 'scene/bg.png'; });
  assert.strictEqual(asks.length, 2, 'asked again');
  assert.ok(asks[1].at - asks[0].at >= 9900 && asks[1].at - asks[0].at <= 10200, 'after 10 s: ' + (asks[1].at - asks[0].at));
  assert.strictEqual(r.sdk.modal.length, 0, 'no Retry dialog while the file is inside its 30 s budget');
  assert.ok(r.homeAt !== null);
});
test('long_frames_count_at_most_1s_each', function () {
  var r = start(FILE_HANG);
  r.clock.advance(300);
  r.clock.frameMs = 5000;  // the JS thread freezes 5 s per frame
  r.clock.advance(25000);
  var asks = r.engine.calls.filter(function (c) { return c.url === 'scene/bg.png'; }).length;
  assert.strictEqual(asks, 1, 'five 5 s frames are 5 s, not 25 s');
});
// a file that never answers at all until Retry
var DEAD = {file: function (c, clock) {
  if (c.url === 'scene/bg.png' && c.n <= 2) return;
  clock.setTimeout(function () { c.done(null, {}); }, 100);
}};
test('dead_file_fails_at_30s_then_retry_enters', function () {
  var r = start(DEAD);
  r.clock.advance(29000);
  assert.strictEqual(r.sdk.modal.length, 0, 'not before 30 s');
  r.clock.advance(2000);
  assert.strictEqual(r.sdk.modal.length, 1, 'Retry at 30 s: ' + JSON.stringify(r.guard.status()));
  assert.strictEqual(r.engine.frozen, false);
  r.sdk.tapRetry();
  r.clock.advance(3000);
  assert.ok(r.homeAt !== null, 'one Retry enters');
  assert.strictEqual(r.engine.sceneCb, 1);
});
// the scene image errors twice (scene request fails after deserialize), then works
var SCENE_FAIL = {file: function (c, clock) {
  clock.setTimeout(function () { if (c.url === 'scene/bg.png' && c.n <= 2) c.done(new Error('image error')); else c.done(null, {}); }, 100);
}};
test('failed_scene_first_retry_works', function () {
  var r = start(SCENE_FAIL);
  r.clock.advance(3000);
  assert.strictEqual(r.sdk.modal.length, 1);
  assert.strictEqual(r.engine.frozen, false, 'engine not told');
  r.sdk.tapRetry();
  r.clock.advance(3000);
  assert.ok(r.homeAt !== null, 'first Retry enters (failed scene dropped from the file cache)');
  assert.strictEqual(r.sdk.modal.length, 1);
});
// first bundle request errors, the second works; the engine also answers twice
var FAIL_THEN_OK = {doubleCallback: true, file: function (c, clock) {
  clock.setTimeout(function () { if (c.url === 'main/config.json' && c.n <= 2) c.done(new Error('net')); else c.done(null, {}); }, 100);
}};
test('first_fails_second_ok_old_answers_dropped', function () {
  var r = start(FAIL_THEN_OK);
  r.clock.advance(2000);
  assert.strictEqual(r.sdk.modal.length, 1, 'one Retry, not one per duplicate answer');
  r.sdk.tapRetry();
  r.clock.advance(3000);
  assert.ok(r.homeAt !== null, 'enters');
  assert.strictEqual(r.engine.frozen, false);
  assert.strictEqual(r.sdk.modal.length, 1, 'late duplicate answers of the old request are dropped');
  assert.strictEqual(r.guard.status().retries, 1);
});
// the first 'main' request errors at once and its engine path answers AGAIN 2.5 s later (after Retry);
// the Retry request is slow (3 s). The late answer of the old request must not show a second Retry.
var LATE = {lateError: 2500, file: function (c, clock) {
  var bad = c.url === 'main/config.json' && c.n <= 2;
  clock.setTimeout(function () { c.done(bad ? new Error('net') : null, {}); }, c.url === 'main/config.json' && c.n > 2 ? 3000 : 100);
}};
test('late_answer_of_old_request_dropped_after_retry', function () {
  var r = start(LATE);
  r.clock.advance(1000);
  assert.strictEqual(r.sdk.modal.length, 1);
  r.sdk.tapRetry();
  r.clock.advance(8000);
  assert.strictEqual(r.sdk.modal.length, 1, 'old request answered late: dropped, no second Retry');
  assert.ok(r.homeAt !== null, 'the Retry request enters');
  assert.strictEqual(r.engine.frozen, false);
});
test('started_only_when_home_scene_launched', function () {
  var r = start({file: function (c, clock) { clock.setTimeout(function () { c.done(null, {}); }, 1000); }});
  r.clock.advance(4500);
  assert.strictEqual(r.guard.status().started, false, 'bundles done, scene still loading');
  assert.strictEqual(r.sdk.hide, 0, 'loading still shown');
  r.clock.advance(5000);
  assert.strictEqual(r.guard.status().started, true);
  assert.ok(r.sdk.hide >= 1);
  var before = r.sdk.modal.length;
  r.clock.advance(60000);
  assert.strictEqual(r.sdk.modal.length, before, 'no Retry after start');
});
// R4Q5 (补查3 第 5 组 奔跑吧巨人): stats off when the home scene is up, whatever a save turned on during loading.
test('stats_off_at_home_even_after_save_switch_turned_them_on', function () {
  var r = start({file: function (c, clock) { clock.setTimeout(function () { c.done(null, {}); }, 100); }});
  var shown = [], hidden = 0;
  r.engine.cc.setDisplayStats = function (on) { shown.push(on); };
  r.engine.cc.profiler = {hideStats: function () { hidden++; }, showStats: function () {}};
  r.engine.cc.setDisplayStats(true);            // the game read debug=true from an old save while loading
  r.clock.advance(5000);
  assert.strictEqual(r.guard.status().started, true);
  assert.ok(hidden >= 2, 'profiler.hideStats at home and one tick later');
  assert.strictEqual(shown[shown.length - 1], false, 'stats end up off');
});
test('stats_api_missing_does_not_break_start', function () {
  var r = start({file: function (c, clock) { clock.setTimeout(function () { c.done(null, {}); }, 100); }});
  r.engine.cc.profiler = {hideStats: function () { throw new Error('no profiler'); }};
  r.clock.advance(5000);
  assert.strictEqual(r.guard.status().started, true);
  assert.strictEqual(r.engine.frozen, false);
});
test('install_twice_one_guard_and_version_marker', function () {
  var clock = new Clock(), sdk = fakeSdk(), engine = makeEngine(clock, {}), m = fresh();
  var a = m.install(engine.cc, sdk, {clock: bind(clock), root: {}});
  var b = m.install(engine.cc, sdk, {clock: bind(clock), root: {}});
  assert.strictEqual(a, b);
  assert.strictEqual(m.version, '1.0');
  assert.ok(fs.readFileSync(target, 'utf8').indexOf('// tiktok-kit:boot3x:1.0') >= 0);
  assert.strictEqual(m.install(null, sdk, {root: {}}), null, 'nothing to hook: no throw');
});

function finish() {
  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  var report = {suite: 'boot-3x', file: target, passed: results.length - failed.length, failed: failed.length, results: results};
  if (!process.env.BOOT3X) {
    var src = fs.readFileSync(KIT_FILE, 'utf8');
    var variants = [
      {name: 'background_counted', before: 'if (!S.hidden) waited +=', after: 'waited +='},
      {name: 'no_frame_cap', before: 'waited += Math.min(T.cap, Math.max(0, now - last));', after: 'waited += Math.max(0, now - last);'},
      {name: 'no_parallel_re_request', before: 'if (policy.parallelAfter && attempts === 1 && waited >= policy.parallelAfter) again();', after: ''},
      {name: 'watchdog_ignores_file_budget', before: '&& !S.guardsWaiting && S.ops.length', after: '&& S.ops.length'},
      {name: 'bundle_waits_30s', before: 'giveUp: T.bundleGiveUp', after: 'giveUp: T.giveUp'},
      {name: 'error_passed_to_engine', before: 'op.failed = true; fail(op.name, error); return;', after: 'finishOp(op, error, value); fail(op.name, error); return;'},
      {name: 'old_answers_not_dropped', before: 'if (op.done || token !== op.token) return;', after: 'if (op.done) return;'},
      {name: 'retry_does_not_reissue', before: 'S.ops.slice().forEach(function (op) { if (!op.done) issue(op); });', after: ''},
      {name: 'failed_scene_not_released', before: "if (S.failedScene === sceneName) { S.failedScene = ''; releaseFailedScene(sceneName); }", after: ''},
      {name: 'file_guard_not_reapplied_after_engine_adapter', before: "    installFileGuard();\n    var op = {", after: "    var op = {"},
      {name: 'stats_not_turned_off', before: '    hideStats();\n    clock.setTimeout(hideStats, 0);', after: ''},
      {name: 'started_before_home_scene', before: "step('bundle ' + name, function (settle) {", after: "launched(); step('bundle ' + name, function (settle) {"}
    ];
    report.negative_controls = variants.map(function (v) {
      var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'boot3x-neg-'));
      var file = path.join(dir, 'boot-guard-3x.js'), applied = src.indexOf(v.before) >= 0;
      fs.writeFileSync(file, applied ? src.replace(v.before, v.after) : src);
      var r = child.spawnSync(process.execPath, [__filename], {encoding: 'utf8', timeout: 60000,
        env: Object.assign({}, process.env, {BOOT3X: file})});
      fs.rmSync(dir, {recursive: true, force: true});
      var caught = [];
      try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
      return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
    });
    report.negative_missed = report.negative_controls.filter(function (n) { return !n.test_failed_as_expected; }).map(function (n) { return n.name; });
  }
  console.log(JSON.stringify(report, null, 2));
  if (failed.length || (report.negative_missed && report.negative_missed.length)) process.exitCode = 1;
}

// game.js path: install(null, ...) before System.warmup hooks the first System.import('cc').
(function systemImportCase() {
  var clock = new Clock(), sdk = fakeSdk(), engine = makeEngine(clock, {}), m = fresh(), seen = [];
  var System = {import: function (id) { seen.push(id); return Promise.resolve(id === 'cc' ? engine.cc : {}); }};
  var pending = m.install(null, sdk, {System: System, clock: bind(clock), root: {}});
  System.import('./application.js')
    .then(function () { return System.import('cc'); })
    .then(function (cc) {
      // application.init(cc) and cc.game.init run here, after the guard is in
      test('game_js_hook_installs_on_system_import_cc', function () {
        assert.strictEqual(pending.pending, false);
        assert.ok(cc.assetManager.__tiktokKitBoot3x, 'guard installed before the engine starts');
        assert.ok(cc.assetManager.downloader.__kitLoadGuard, 'file guard installed');
        // game.js then runs require('./engine-adapter'), which registers the mini-game handlers again
        var d = cc.assetManager.downloader, raw = engine.rawHandlers;
        Object.keys(raw).forEach(function (ext) { d.register(ext, raw[ext]); });
        assert.ok(!d._downloaders['.png'].__kitBounded, 'fixture: adapter replaced the guarded handler');
        engine.hangFirst = 'scene/bg.png';  // the first image request never answers
        var home = null;
        engine.boot(function () { home = clock.t; });
        clock.advance(12000);
        assert.ok(d._downloaders['.png'].__kitBounded, 'guard re-applied before the first startup step');
        assert.ok(home !== null, 'stuck image re-requested at 10 s and the home scene came up');
        assert.strictEqual(sdk.modal.length, 0);
        assert.deepStrictEqual(seen, ['./application.js', 'cc']);
      });
      finish();
    }, function (e) { test('game_js_hook_installs_on_system_import_cc', function () { throw e; }); finish(); });
})();
