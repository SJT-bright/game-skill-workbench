'use strict';
// build-templates/bytedance-mini-game/tiktok-touch-3x.js (Cocos 3.x touch coordinates, kit 2.0) against a fake
// TikTok SDK whose touch points carry only identifier/screenX/screenY/force, like the real one.
// Node only; it does NOT prove a real phone (待真机复测). The real-package proof is the Marlows R4 probe run
// recorded in briefs/out/W-A2/RESULT.md (probe_cocos3_touch_coordinates.cjs).
// Usage: node tests/touch-3x.test.js            -> cases, then the negative controls (each mutant MUST fail)
//        TOUCH3X=/path/file.js node tests/touch-3x.test.js   -> cases only, on that file
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var KIT_FILE = path.join(__dirname, '..', 'build-templates', 'bytedance-mini-game', 'tiktok-touch-3x.js');
var target = process.env.TOUCH3X || KIT_FILE;
var PHASES = ['Start', 'Move', 'End', 'Cancel'];
var results = [];

function fresh() {
  delete require.cache[require.resolve(target)];
  return require(target);
}
function clearGlobals() { delete globalThis.tt; delete globalThis.TTMinis; }
function test(name, run) {
  clearGlobals();
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
  clearGlobals();
}
// A TikTok SDK stand-in: onTouchX/offTouchX keep listener lists; fire() calls them like the platform does.
function fakeSdk(opts) {
  opts = opts || {};
  var sdk = {listeners: {}, onCalls: 0};
  PHASES.forEach(function (p) {
    sdk.listeners[p] = [];
    sdk['onTouch' + p] = function (fn) { sdk.onCalls++; sdk.listeners[p].push(fn); };
    if (!opts.noOff) sdk['offTouch' + p] = function (fn) {
      var i = sdk.listeners[p].indexOf(fn); if (i >= 0) sdk.listeners[p].splice(i, 1);
    };
  });
  sdk.fire = function (phase, point) {
    var event = {touches: phase === 'End' || phase === 'Cancel' ? [] : [point], changedTouches: [point], timeStamp: 7};
    sdk.listeners[phase].slice().forEach(function (fn) { fn.call(sdk, event); });
  };
  return sdk;
}
function screenPoint(x, y) { return {identifier: 3, screenX: x, screenY: y, force: 1}; }
function record(sdk, phase) {
  var got = [];
  sdk['onTouch' + phase](function (e) { got.push(e); });
  return got;
}

test('screen_only_point_reaches_listener_with_client_coordinates', function () {
  var sdk = fakeSdk(), m = fresh();
  assert.strictEqual(m.install(sdk), 1);
  var got = record(sdk, 'Start');
  sdk.fire('Start', screenPoint(195, 422));
  assert.strictEqual(got.length, 1);
  var t = got[0].changedTouches[0];
  assert.strictEqual(t.clientX, 195); assert.strictEqual(t.clientY, 422);
  assert.strictEqual(t.identifier, 3); assert.strictEqual(t.force, 1);
  assert.strictEqual(got[0].touches[0].clientX, 195, 'touches[] converted too');
  assert.strictEqual(got[0].timeStamp, 7, 'other event fields kept');
});
test('all_four_phases_converted', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  PHASES.forEach(function (p) {
    var got = record(sdk, p);
    sdk.fire(p, screenPoint(20, 800));
    assert.strictEqual(got.length, 1, p);
    assert.strictEqual(got[0].changedTouches[0].clientX, 20, p + ' x');
    assert.strictEqual(got[0].changedTouches[0].clientY, 800, p + ' y');
  });
});
test('zero_coordinates_stay_zero_not_dropped', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var got = record(sdk, 'Start');
  sdk.fire('Start', screenPoint(0, 0));
  assert.strictEqual(got[0].changedTouches[0].clientX, 0); assert.strictEqual(got[0].changedTouches[0].clientY, 0);
});
test('client_coordinates_left_unchanged', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var got = record(sdk, 'Start'), p = {identifier: 0, clientX: 20, clientY: 30, screenX: 99, screenY: 99, force: 1};
  sdk.fire('Start', p);
  assert.strictEqual(got[0].changedTouches[0], p, 'a point that already has clientX/clientY is passed through');
});
test('prototype_getter_touch_keeps_identifier', function () {
  // a platform touch object whose fields are prototype getters: Object.assign copies none of them
  function Touch(id, x, y) { this._v = {identifier: id, screenX: x, screenY: y}; }
  ['identifier', 'screenX', 'screenY'].forEach(function (k) {
    Object.defineProperty(Touch.prototype, k, {get: function () { return this._v[k]; }});
  });
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var got = record(sdk, 'Start');
  sdk.fire('Start', new Touch(5, 11, 12));
  var t = got[0].changedTouches[0];
  assert.strictEqual(t.identifier, 5); assert.strictEqual(t.clientX, 11); assert.strictEqual(t.clientY, 12);
});
test('install_twice_wraps_once', function () {
  var sdk = fakeSdk(), m = fresh();
  assert.strictEqual(m.install(sdk), 1);
  var first = sdk.onTouchStart;
  assert.strictEqual(m.install(sdk), 0, 'second install changes nothing');
  assert.strictEqual(sdk.onTouchStart, first, 'onTouchStart not wrapped again');
  var m2 = fresh();               // a second copy of the module (e.g. loaded twice) must not add a layer either
  assert.strictEqual(m2.install(sdk), 0);
  assert.strictEqual(sdk.onTouchStart, first);
});
test('one_listener_registered_once_even_if_added_twice', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var calls = 0, fn = function () { calls++; };
  sdk.onTouchStart(fn); sdk.onTouchStart(fn);
  assert.strictEqual(sdk.listeners.Start[0], sdk.listeners.Start[1], 'same wrapper reused for the same listener');
  sdk.offTouchStart(fn);
  assert.strictEqual(sdk.listeners.Start.length, 1);
});
test('off_removes_the_wrapped_listener', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var calls = 0, fn = function () { calls++; };
  sdk.onTouchEnd(fn);
  sdk.offTouchEnd(fn);
  sdk.fire('End', screenPoint(1, 2));
  assert.strictEqual(calls, 0);
  assert.strictEqual(sdk.listeners.End.length, 0);
});
test('only_ttminis_game_present', function () {
  var game = fakeSdk(), m = fresh();
  globalThis.TTMinis = {game: game};
  assert.strictEqual(m.install(globalThis.TTMinis && TTMinis.game || globalThis.tt), 1);
  var got = record(game, 'Move');
  game.fire('Move', screenPoint(40, 50));
  assert.strictEqual(got[0].changedTouches[0].clientX, 40);
});
test('only_tt_present_and_wiring_line_argument_is_undefined_safe', function () {
  var sdk = fakeSdk(), m = fresh();
  globalThis.tt = sdk;
  assert.strictEqual(m.install(globalThis.TTMinis && TTMinis.game || globalThis.tt), 1);
  assert.strictEqual(m.install(undefined), 0);
  var got = record(sdk, 'Start');
  sdk.fire('Start', screenPoint(7, 8));
  assert.strictEqual(got[0].changedTouches[0].clientY, 8);
});
test('ttminis_game_passed_tt_also_wrapped', function () {
  // the 3.x engine clones `tt`; when TTMinis.game and tt are different objects both must be wrapped
  var game = fakeSdk(), raw = fakeSdk(), m = fresh();
  globalThis.TTMinis = {game: game}; globalThis.tt = raw;
  assert.strictEqual(m.install(TTMinis.game), 2);
  var got = record(raw, 'Start');
  raw.fire('Start', screenPoint(9, 10));
  assert.strictEqual(got[0].changedTouches[0].clientX, 9);
  assert.strictEqual(m.install(TTMinis.game), 0, 'idempotent for both');
});
test('engine_clone_after_install_gets_wrapped_functions', function () {
  // Cocos 3.x minigame: for (key in tt) copy[key] = tt[key]; then copy.onTouchStart(callback)
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  var copy = {};
  for (var k in sdk) copy[k] = sdk[k];
  assert.strictEqual(Object.prototype.hasOwnProperty.call(copy, '__tiktokKitTouch3x'), false, 'marker not enumerable');
  var got = [];
  copy.onTouchStart(function (e) { got.push(e); });
  sdk.fire('Start', screenPoint(30, 31));
  assert.strictEqual(got[0].changedTouches[0].clientX, 30);
});
test('no_sdk_and_partial_sdk_do_not_throw', function () {
  var m = fresh();
  assert.strictEqual(m.install(undefined), 0);
  assert.strictEqual(m.install(null), 0);
  assert.strictEqual(m.install({}), 0, 'object without onTouch* is not counted');
  var sdk = fakeSdk({noOff: true});
  assert.strictEqual(m.install(sdk), 1, 'SDK without offTouch* still wrapped');
  var got = record(sdk, 'Start');
  sdk.fire('Start', screenPoint(2, 3));
  assert.strictEqual(got[0].changedTouches[0].clientX, 2);
});
test('non_function_listener_passed_through', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk);
  sdk.onTouchStart(null);
  assert.strictEqual(sdk.listeners.Start[0], null);
});
test('version_and_marker_comment', function () {
  var m = fresh(), text = fs.readFileSync(target, 'utf8');
  assert.strictEqual(m.version, '2.0');
  assert.ok(text.indexOf('// tiktok-kit:touch3x:2.0') >= 0, 'file carries its kit marker');
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
var report = {suite: 'touch-3x', file: target, passed: results.length - failed.length, failed: failed.length, results: results};

// Negative controls: break one rule in a temporary copy; the cases above MUST fail on it.
if (!process.env.TOUCH3X) {
  var src = fs.readFileSync(KIT_FILE, 'utf8');
  var variants = [
    {name: 'screen_coordinates_not_copied', before: 'finite(value.screenX) ? value.screenX : ', after: ''},
    {name: 'identifier_not_copied', before: 'copy.identifier = value.identifier;', after: ''},
    {name: 'wraps_twice', before: 'if (api[MARK]) return false;', after: ''},
    {name: 'tt_not_wrapped_when_ttminis_given', before: "try { if (typeof tt !== 'undefined') list.push(tt); } catch (e) {}\n  try { if (g.tt) list.push(g.tt); } catch (e) {}", after: ''},
    {name: 'off_not_mapped', before: 'listeners.get(listener) || listener', after: 'listener'},
    {name: 'new_wrapper_per_registration', before: 'var w = listeners.get(listener);', after: 'var w = null;'},
    {name: 'only_start_phase', before: "var PHASES = ['Start', 'Move', 'End', 'Cancel'];", after: "var PHASES = ['Start'];"},
    {name: 'marker_enumerable', before: 'enumerable: false', after: 'enumerable: true'}
  ];
  report.negative_controls = variants.map(function (v) {
    var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'touch3x-neg-'));
    var file = path.join(dir, 'tiktok-touch-3x.js'), applied = src.indexOf(v.before) >= 0;
    fs.writeFileSync(file, applied ? src.replace(v.before, v.after) : src);
    var r = child.spawnSync(process.execPath, [__filename], {encoding: 'utf8', timeout: 20000,
      env: Object.assign({}, process.env, {TOUCH3X: file})});
    fs.rmSync(dir, {recursive: true, force: true});
    var caught = [];
    try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
    return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
  });
  report.negative_missed = report.negative_controls.filter(function (n) { return !n.test_failed_as_expected; }).map(function (n) { return n.name; });
}
console.log(JSON.stringify(report, null, 2));
if (failed.length || (report.negative_missed && report.negative_missed.length)) process.exitCode = 1;
