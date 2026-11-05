'use strict';
// build-templates/bytedance/touch-coordinates.js, part 2 (v7.9 手机问题源头约束): a finger that is down when TikTok
// takes the game away never gets touchend; on cc.game EVENT_HIDE / EVENT_SHOW the touches the Cocos 2.4 input
// manager still holds get a TOUCH_CANCEL and its touch state is cleared. Against a fake Cocos 2.4 input manager with
// the fields the real one has (_touchesIntegerDict, _touches, _indexBitsUsed, handleTouchesCancel, eventManager
// _clearCurTouch). Node only; the real-engine proof is the runtime suite resume_play finger_held in the TikTok host
// (割草 v015 refused with the old file, passes with this one; 测试记录 of the patch). Does NOT prove a real phone.
// Usage: node tests/touch-lifecycle-24.test.js         -> cases, then the negative controls (each mutant MUST fail)
//        TOUCH24=/path/file.js node tests/touch-lifecycle-24.test.js   -> cases only, on that file
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var KIT_FILE = path.join(__dirname, '..', 'build-templates', 'bytedance', 'touch-coordinates.js');
var target = process.env.TOUCH24 || KIT_FILE;
var results = [];

function fresh() { delete require.cache[require.resolve(target)]; return require(target); }
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
// A Cocos 2.4 stand-in: the input manager keeps touches by identifier until touchend / touchcancel.
function fakeCocos(opts) {
  opts = opts || {};
  var handlers = {};
  var cancelled = [], cleared = {n: 0};
  var manager = {
    _touchesIntegerDict: {}, _touches: [], _indexBitsUsed: 0, _touchesCache: {}, _touchCount: 0,
    getTouchesByEvent: function (event) { return event.changedTouches; },
    handleTouchesBegin: function (touches) {
      touches.forEach(function (t) {
        var id = t.identifier;
        if (manager._touchesIntegerDict[id] !== undefined) return;       // same id still held: the tap is dropped
        var index = manager._touches.length;
        manager._touches[index] = {_point: {x: t.clientX, y: t.clientY}, _prevPoint: {x: 0, y: 0}, getID: function () { return id; }};
        manager._touchesIntegerDict[id] = index;
        manager._indexBitsUsed |= (1 << index);
      });
    },
    handleTouchesCancel: function (touches) { cancelled.push(touches.map(function (t) { return t.getID(); })); }
  };
  var game = opts.noGameEvents ? {} : {
    EVENT_HIDE: 'game_on_hide', EVENT_SHOW: 'game_on_show',
    on: function (type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
    emit: function (type) { (handlers[type] || []).slice().forEach(function (fn) { fn(); }); }
  };
  var cc = {internal: {inputManager: manager, eventManager: {_clearCurTouch: function () { cleared.n++; }}}, game: game};
  return {cc: cc, manager: manager, cancelled: cancelled, cleared: cleared, handlers: handlers};
}
function down(f, id, x, y) { f.manager.handleTouchesBegin(f.manager.getTouchesByEvent({changedTouches: [{identifier: id, screenX: x, screenY: y}]})); }

test('held_touch_cancelled_and_cleared_on_hide', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc);
  down(f, 0, 195, 422);
  assert.deepStrictEqual(Object.keys(f.manager._touchesIntegerDict), ['0']);
  f.cc.game.emit('game_on_hide');
  assert.deepStrictEqual(f.cancelled, [[0]], 'the held touch got TOUCH_CANCEL');
  assert.deepStrictEqual(f.manager._touchesIntegerDict, {}, 'touch state cleared');
  assert.strictEqual(f.manager._indexBitsUsed, 0);
  assert.strictEqual(f.cleared.n, 1, 'eventManager current touch cleared');
});
test('same_identifier_after_returning_starts_a_new_touch', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc);
  down(f, 0, 100, 100);
  f.cc.game.emit('game_on_hide'); f.cc.game.emit('game_on_show');
  var before = f.manager._touches.length;
  down(f, 0, 120, 140);
  assert.strictEqual(f.manager._touches.length, before + 1, 'the first tap after returning is not dropped');
});
test('show_also_clears', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc);
  down(f, 3, 10, 10);
  f.cc.game.emit('game_on_show');
  assert.deepStrictEqual(f.cancelled, [[3]]);
  assert.deepStrictEqual(f.manager._touchesIntegerDict, {});
});
test('nothing_held_nothing_cancelled', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc);
  f.cc.game.emit('game_on_hide');
  assert.deepStrictEqual(f.cancelled, []);
});
test('install_twice_registers_once', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc); m.install(f.cc);
  assert.strictEqual(f.handlers.game_on_hide.length, 1);
  assert.strictEqual(f.handlers.game_on_show.length, 1);
});
test('screen_coordinates_still_converted', function () {
  var f = fakeCocos(), m = fresh();
  m.install(f.cc);
  var out = f.manager.getTouchesByEvent({changedTouches: [{identifier: 0, screenX: 120, screenY: 300}], touches: []});
  assert.strictEqual(out[0].clientX, 120); assert.strictEqual(out[0].clientY, 300);
});
test('no_game_events_still_converts', function () {
  var f = fakeCocos({noGameEvents: true}), m = fresh();
  m.install(f.cc);
  var out = f.manager.getTouchesByEvent({changedTouches: [{identifier: 1, screenX: 5, screenY: 6}]});
  assert.strictEqual(out[0].clientX, 5);
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
var report = {suite: 'touch-lifecycle-24', file: target, passed: results.length - failed.length, failed: failed.length, results: results};
if (!process.env.TOUCH24) {
  var src = fs.readFileSync(KIT_FILE, 'utf8');
  var variants = [
    {name: 'no_hide_show_hooks', before: 'game.on(game.EVENT_HIDE,cancelStale);game.on(game.EVENT_SHOW,cancelStale);', after: ''},
    {name: 'only_hide_hook', before: 'game.on(game.EVENT_SHOW,cancelStale);', after: ''},
    {name: 'state_not_cleared', before: 'manager._touchesIntegerDict={};', after: ''},
    {name: 'no_touch_cancel', before: 'manager.handleTouchesCancel(held);', after: 'void 0;'},
    {name: 'current_touch_kept', before: 'events._clearCurTouch();', after: 'void 0;'},
    {name: 'hooks_outside_the_install_guard', before: ' manager.__starPopTouchCoordinates=true;\n', after: ''}
  ];
  report.negative_controls = variants.map(function (v) {
    var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'touch24-neg-'));
    var file = path.join(dir, 'touch-coordinates.js'), applied = src.indexOf(v.before) >= 0;
    fs.writeFileSync(file, applied ? src.replace(v.before, v.after) : src);
    var r = child.spawnSync(process.execPath, [__filename], {encoding: 'utf8', timeout: 20000, env: Object.assign({}, process.env, {TOUCH24: file})});
    fs.rmSync(dir, {recursive: true, force: true});
    var caught = [];
    try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
    return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
  });
  report.negative_missed = report.negative_controls.filter(function (n) { return !n.test_failed_as_expected; }).map(function (n) { return n.name; });
}
console.log(JSON.stringify(report, null, 2));
if (failed.length || (report.negative_missed && report.negative_missed.length)) process.exitCode = 1;
