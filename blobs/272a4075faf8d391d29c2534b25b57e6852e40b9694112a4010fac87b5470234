'use strict';
// parts/host-shim.js (TikTok host API safe defaults, 2.4 and 3.x) against fake TikTok SDKs with fields removed.
// Old-way fixtures are the host checks found in real games (问题普查 2026-11-04, sub host_api_mismatch):
// 躲雨小鸭 v16 adapter (SDKVersion[0] + "isSubContext = getOpenDataContext === undefined"), 射击高手2048 v83
// (SDKVersion[0] of '10.x'). They MUST break without the shim and work with it.
// Node only; it does NOT prove a real phone (待真机复测).
// Usage: node tests/host-shim.test.js              -> cases, then the negative controls (each mutant MUST fail)
//        HOSTSHIM=/path/file.js node tests/host-shim.test.js   -> cases only, on that file
var assert = require('assert'), fs = require('fs'), os = require('os'), path = require('path'), child = require('child_process');
var KIT_FILE = path.join(__dirname, '..', 'parts', 'host-shim.js');
var target = process.env.HOSTSHIM || KIT_FILE;
var results = [];

function fresh() { delete require.cache[require.resolve(target)]; return require(target); }
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
// A TikTok SDK stand-in. opts.drop: names to leave out; opts.sdkVersion: value (undefined = field missing).
function fakeSdk(opts) {
  opts = opts || {};
  var drop = opts.drop || [];
  var sdk = {
    getSystemInfoSync: function () {
      if (opts.infoThrows) throw new Error('getSystemInfoSync:fail');
      var info = {screenWidth: 390, screenHeight: 844, windowWidth: 390, windowHeight: 844, pixelRatio: 3, platform: 'ios'};
      if (opts.sdkVersion !== undefined) info.SDKVersion = opts.sdkVersion;
      return info;
    },
    canIUse: function (name) { return name === 'createRewardedVideoAd'; },
    getOpenDataContext: function () { return {postMessage: function () {}, real: true}; },
    createRewardedVideoAd: function () { return {}; },
    loadSubpackage: function () {}
  };
  drop.forEach(function (k) { delete sdk[k]; });
  return sdk;
}
var fakeRoot = {innerWidth: 360, innerHeight: 780, devicePixelRatio: 2, screen: {width: 360, height: 780}};

// ---- old-way fixtures, copied in shape from the games ----
// 躲雨小鸭 v16 old adapter (RainyDuck platform layer): reads the version digit and guesses the domain.
function rainyDuckOldDetect(api) {
  var info = api.getSystemInfoSync();
  var major = info.SDKVersion[0];                       // throws when SDKVersion is missing
  var isSubContext = api.getOpenDataContext === undefined;  // TikTok main package without it -> "sub-context"
  return {major: major, isSubContext: isSubContext, oldDouyinBranch: major < 2};
}
// 射击高手2048 v83: first character of SDKVersion as the major version.
function mergeShotOldMajor(api) { return Number(api.getSystemInfoSync().SDKVersion[0]); }
// Cocos 2.4 / 3.x mini-game adapter line, as shipped: decides the domain once, when the adapter loads.
function cocosAdapterInit(root, api) { var ga = root.__globalAdapter = {}; for (var k in api) ga[k] = api[k]; ga.isSubContext = ga.getOpenDataContext === undefined; return ga; }

test('old_rainyduck_check_breaks_without_shim', function () {
  var sdk = fakeSdk({drop: ['getOpenDataContext']}); // SDKVersion missing too
  assert.throws(function () { rainyDuckOldDetect(sdk); }, TypeError, 'fixture must reproduce the crash');
  var sdk2 = fakeSdk({drop: ['getOpenDataContext'], sdkVersion: '0.9.1'});
  assert.strictEqual(rainyDuckOldDetect(sdk2).isSubContext, true, 'fixture must reproduce the wrong domain');
});
test('rainyduck_check_works_with_shim', function () {
  var sdk = fakeSdk({drop: ['getOpenDataContext']}), m = fresh();
  var r = m.install(sdk, {root: fakeRoot, alsoGlobals: false});
  assert.strictEqual(r.targets, 1);
  var got = rainyDuckOldDetect(sdk);
  assert.strictEqual(got.isSubContext, false, 'main domain');
  assert.strictEqual(got.major, '0');
  assert.strictEqual(sdk.getOpenDataContext().canvas, null, 'stub is harmless');
  assert.doesNotThrow(function () { sdk.getOpenDataContext().postMessage({a: 1}); });
});
test('sdkversion_missing_gets_0_0_0_and_parse_helpers', function () {
  var sdk = fakeSdk(), m = fresh();
  m.install(sdk, {root: fakeRoot, alsoGlobals: false});
  assert.strictEqual(sdk.getSystemInfoSync().SDKVersion, '0.0.0');
  assert.deepStrictEqual(m.sdkVersion(sdk), [0, 0, 0]);
  assert.deepStrictEqual(m.parseVersion('10.2.1'), [10, 2, 1], 'ten is ten (射击高手2048 read 1)');
  assert.deepStrictEqual(m.parseVersion(undefined), [0, 0, 0]);
  assert.deepStrictEqual(m.parseVersion('x.7'), [0, 7, 0]);
  var tenSdk = fakeSdk({sdkVersion: '10.2.1'});
  assert.strictEqual(mergeShotOldMajor(tenSdk), 1, 'fixture reproduces the misread');
  m.install(tenSdk, {root: fakeRoot, alsoGlobals: false});
  assert.deepStrictEqual(m.sdkVersion(tenSdk), [10, 2, 1]);
});
test('getsysteminfosync_throw_returns_screen_defaults', function () {
  var sdk = fakeSdk({infoThrows: true}), m = fresh();
  assert.throws(function () { sdk.getSystemInfoSync(); });
  var err = console.error; console.error = function () {};
  try {
    m.install(sdk, {root: fakeRoot, alsoGlobals: false});
    var info = sdk.getSystemInfoSync();
    assert.strictEqual(info.windowWidth, 360); assert.strictEqual(info.windowHeight, 780);
    assert.strictEqual(info.SDKVersion, '0.0.0');
  } finally { console.error = err; }
});
test('missing_getsysteminfosync_and_canIUse_filled', function () {
  var sdk = fakeSdk({drop: ['getSystemInfoSync', 'canIUse']}), m = fresh();
  m.install(sdk, {root: fakeRoot, alsoGlobals: false});
  assert.strictEqual(sdk.getSystemInfoSync().screenWidth, 360);
  assert.strictEqual(sdk.canIUse('createRewardedVideoAd'), true, 'real API present -> true');
  assert.strictEqual(sdk.canIUse('addShortcut'), false, 'absent -> false');
  assert.strictEqual(sdk.canIUse('getSystemInfoSync.return.safeArea'), false, 'dotted -> false');
});
test('existing_apis_not_replaced', function () {
  var sdk = fakeSdk({sdkVersion: '3.4.0'}), m = fresh();
  var odc = sdk.getOpenDataContext, can = sdk.canIUse, before = sdk.getSystemInfoSync();
  m.install(sdk, {root: fakeRoot, alsoGlobals: false});
  assert.strictEqual(sdk.getOpenDataContext, odc, 'getOpenDataContext kept');
  assert.strictEqual(sdk.canIUse, can, 'canIUse kept');
  assert.strictEqual(sdk.canIUse('addShortcut'), false, 'its own answers kept');
  assert.deepStrictEqual(sdk.getSystemInfoSync(), before, 'normal result unchanged');
  assert.strictEqual(sdk.getOpenDataContext().real, true);
});
test('adapter_already_ran_domain_fixed_up', function () {
  var root = {innerWidth: 360, innerHeight: 780}, sdk = fakeSdk({drop: ['getOpenDataContext'], sdkVersion: '1.0.0'}), m = fresh();
  var ga = cocosAdapterInit(root, sdk);
  assert.strictEqual(ga.isSubContext, true, 'fixture: adapter guessed sub-context');
  m.install(sdk, {root: root, alsoGlobals: false});
  assert.strictEqual(ga.isSubContext, false, 'set back to main domain');
  var root2 = {}, sdk2 = fakeSdk({drop: ['getOpenDataContext']});
  fresh().install(sdk2, {root: root2, alsoGlobals: false});
  assert.strictEqual(cocosAdapterInit(root2, sdk2).isSubContext, false, 'shim first -> adapter sees main domain');
});
test('ttminis_and_tt_both_shimmed_once', function () {
  var root = {TTMinis: {game: fakeSdk({drop: ['getOpenDataContext']})}, tt: fakeSdk({drop: ['canIUse']})}, m = fresh();
  var r = m.install(root.TTMinis.game, {root: root});
  assert.strictEqual(r.targets, 2);
  assert.strictEqual(typeof root.TTMinis.game.getOpenDataContext, 'function');
  assert.strictEqual(typeof root.tt.canIUse, 'function');
  var wrapped = root.tt.getSystemInfoSync;
  var r2 = m.install(root.tt, {root: root});
  assert.strictEqual(r2.targets, 0, 'second install does nothing');
  assert.strictEqual(root.tt.getSystemInfoSync, wrapped, 'not wrapped twice');
});
test('no_sdk_and_frozen_sdk_do_not_throw', function () {
  var m = fresh();
  assert.strictEqual(m.install(null, {root: {}}).targets, 0);
  var frozen = Object.freeze(fakeSdk({drop: ['getOpenDataContext']}));
  var r;
  assert.doesNotThrow(function () { r = m.install(frozen, {root: {}, alsoGlobals: false}); });
  assert.ok(r.skipped.indexOf('getOpenDataContext') >= 0, 'reported as skipped');
});
test('version_and_marker_comment', function () {
  var m = fresh(), text = fs.readFileSync(target, 'utf8');
  assert.strictEqual(m.version, '1.0');
  assert.ok(text.indexOf('// tiktok-kit:hostshim:1.0') >= 0, 'file carries its kit marker');
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
var report = {suite: 'host-shim', file: target, passed: results.length - failed.length, failed: failed.length, results: results};

// Negative controls: break one rule in a temporary copy; the cases above MUST fail on it.
if (!process.env.HOSTSHIM) {
  var src = fs.readFileSync(KIT_FILE, 'utf8');
  var variants = [
    {name: 'no_open_data_context_stub', before: "var filledOdc = setIfMissing(api, 'getOpenDataContext',", after: "var filledOdc = false && setIfMissing(api, 'getOpenDataContext',"},
    {name: 'no_sdkversion_default', before: "info.SDKVersion = info.SDKVersion == null || info.SDKVersion === '' ? '0.0.0' : String(info.SDKVersion);", after: ''},
    {name: 'throw_not_caught', before: 'try { info = original.apply(this, arguments); }', after: 'info = original.apply(this, arguments); try {}'},
    {name: 'overwrites_existing', before: 'if (api[name] !== undefined && api[name] !== null) return false;', after: ''},
    {name: 'version_first_char', before: "String(value).split('.').slice(0, 3)", after: "String(value).charAt(0).split('.')"},
    {name: 'canIUse_always_true', before: "if (typeof name !== 'string' || !name || name.indexOf('.') >= 0) return false;", after: 'return true;'},
    {name: 'wraps_twice', before: 'if (api[MARK]) return false;', after: ''},
    {name: 'no_adapter_fixup', before: 'ga.isSubContext = false;', after: ''}
  ];
  report.negative_controls = variants.map(function (v) {
    var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hostshim-neg-'));
    var file = path.join(dir, 'host-shim.js'), applied = src.indexOf(v.before) >= 0;
    fs.writeFileSync(file, applied ? src.replace(v.before, v.after) : src);
    var r = child.spawnSync(process.execPath, [__filename], {encoding: 'utf8', timeout: 20000,
      env: Object.assign({}, process.env, {HOSTSHIM: file})});
    fs.rmSync(dir, {recursive: true, force: true});
    var caught = [];
    try { caught = JSON.parse(r.stdout).results.filter(function (x) { return x.status !== 'passed'; }).map(function (x) { return x.name; }); } catch (_) {}
    return {name: v.name, mutation_applied: applied, test_failed_as_expected: applied && r.status !== 0, caught_by: caught};
  });
  report.negative_missed = report.negative_controls.filter(function (n) { return !n.test_failed_as_expected; }).map(function (n) { return n.name; });
}
console.log(JSON.stringify(report, null, 2));
if (failed.length || (report.negative_missed && report.negative_missed.length)) process.exitCode = 1;
