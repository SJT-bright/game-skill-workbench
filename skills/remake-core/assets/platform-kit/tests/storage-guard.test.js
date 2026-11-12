'use strict';
// parts/storage-guard.js against a fake TikTok storage that behaves like the phones in the game reports:
// unwritten keys read back as false / '' / undefined, raw numbers read back as true.
// Node only; it does NOT prove a real phone (待真机复测).
var assert = require('assert'), path = require('path');
var guardPath = process.env.STORAGE_GUARD || path.join(__dirname, '..', 'parts', 'storage-guard.js');
var install = require(guardPath);
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

// absent: what an unwritten key reads back as. numberAs: what a raw number reads back as.
function fakeRuntime(opts) {
  opts = opts || {};
  var data = {}, writes = [];
  var storage = {
    getItem: function (k) {
      if (opts.throwListed && k in data) throw new Error('getStorageSync fail existing');
      if (opts.throwAbsent && !(k in data)) throw new Error('getStorageSync fail');
      if (!(k in data)) return opts.absent;
      var v = data[k];
      if (typeof v === 'number' && 'numberAs' in opts) return opts.numberAs;
      if (typeof v === 'boolean' && 'boolAs' in opts) return opts.boolAs;
      return v;
    },
    setItem: function (k, v) { writes.push({k: k, v: v}); data[k] = v; },
    removeItem: function (k) { delete data[k]; }
  };
  var api = opts.noKeys ? {} : {getStorageInfoSync: function () { return {keys: Object.keys(data)}; }};
  var cc = {sys: {localStorage: storage}};
  var saved = {TTMinis: global.TTMinis, tt: global.tt, localStorage: global.localStorage};
  delete global.TTMinis; delete global.tt; delete global.localStorage;
  var r = install(cc, api);
  return {cc: cc, storage: storage, data: data, writes: writes, installed: r, restore: function () {
    ['TTMinis', 'tt', 'localStorage'].forEach(function (k) { if (saved[k] === undefined) delete global[k]; else global[k] = saved[k]; });
  }};
}

[false, '', undefined, null].forEach(function (absent) {
  test('unwritten_key_reading_' + JSON.stringify(absent === undefined ? 'undefined' : absent) + '_is_null', function () {
    var s = fakeRuntime({absent: absent});
    assert.strictEqual(s.cc.sys.localStorage.getItem('level'), null, 'new player');
    s.restore();
  });
});
// 2026-11-12: reading saved data never stops the game. Before this, a new player on a phone without a key list
// (or any player with a listed Boolean) made every read throw and the game could not start.
[false, '', undefined, null].forEach(function (absent) {
  test('unwritten_key_without_key_list_reading_' + JSON.stringify(absent === undefined ? 'undefined' : absent) + '_is_null_and_writable', function () {
    var s = fakeRuntime({absent: absent, noKeys: true});
    assert.strictEqual(s.cc.sys.localStorage.getItem('level'), null, 'a new player starts');
    s.cc.sys.localStorage.setItem('level', 0);
    assert.deepStrictEqual(s.data, {level: '0'});
    assert.strictEqual(s.cc.sys.localStorage.getItem('level'), '0');
    s.restore();
  });
});
test('read_that_throws_for_unlisted_key_is_null', function () {
  var s = fakeRuntime({throwAbsent: true});
  assert.strictEqual(s.cc.sys.localStorage.getItem('coins'), null);
  s.restore();
});
test('existing_read_error_reads_as_no_value_and_does_not_block', function(){
  var s=fakeRuntime({throwListed:true});s.data.wallet=45;
  assert.strictEqual(s.storage.getItem('wallet'), null, 'the read does not throw');
  assert.strictEqual(s.data.wallet,45, 'a read changes nothing');
  assert.strictEqual(s.writes.length,0);
  s.storage.setItem('wallet',3);
  assert.strictEqual(s.data.wallet,'3', 'the game can save again');s.restore();
});
test('numbers_and_booleans_are_written_as_text', function () {
  var s = fakeRuntime({numberAs: true, boolAs: true});
  var ls = s.cc.sys.localStorage;
  ls.setItem('level', 3); ls.setItem('sound', false); ls.setItem('zero', 0);
  assert.deepStrictEqual(s.writes.map(function (w) { return [w.k, w.v]; }), [['level', '3'], ['sound', 'false'], ['zero', '0']]);
  assert.strictEqual(ls.getItem('level'), '3', 'number read back as text, not true');
  assert.strictEqual(Number(ls.getItem('zero')), 0);
  assert.strictEqual(ls.getItem('sound'), 'false');
  s.restore();
});
test('object_write_is_json_text', function () {
  var s = fakeRuntime({});
  s.cc.sys.localStorage.setItem('save', {coins: 5});
  assert.strictEqual(s.writes[0].v, '{"coins":5}');
  s.restore();
});
test('raw_number_read_back_as_boolean_is_no_value_until_typed_recovery', function () {
  var s = fakeRuntime({numberAs: true});
  s.data.level = 7;                         // written by an old build without the guard
  assert.strictEqual(s.cc.sys.localStorage.getItem('level'), null, 'not true, not "true", and no throw');
  assert.strictEqual(s.data.level, 7, 'reading does not touch the old value');
  assert.strictEqual(s.writes.length,0);
  s.cc.sys.localStorage.setItem('level', 2);
  assert.strictEqual(s.data.level, '2');
  s.restore();
});
test('game_scripts_reach_the_helper_through_a_global', function () {
  var s = fakeRuntime({});
  assert.strictEqual(typeof globalThis.TikTokStorageGuard, 'function');
  assert.strictEqual(typeof globalThis.TikTokStorageGuard.recoverTyped, 'function');
  assert.strictEqual(typeof globalThis.TikTokStorageGuard.recoverNumeric, 'function');
  s.restore();
});
test('listed_boolean_switch_reads_as_no_value_and_is_logged', function () {
  var s = fakeRuntime({});
  s.data.IS_GAME_MUSIC = false; s.data.TUTORIAL_DONE = true;   // an older build stored real Booleans
  var lines = [], warn = console.warn; console.warn = function (x) { lines.push(String(x)); };
  try {
    assert.strictEqual(s.cc.sys.localStorage.getItem('IS_GAME_MUSIC'), null);
    assert.strictEqual(s.cc.sys.localStorage.getItem('TUTORIAL_DONE'), null);
    assert.strictEqual(s.cc.sys.localStorage.getItem('IS_GAME_MUSIC'), null, 'second read, still no throw');
  } finally { console.warn = warn; }
  assert.deepStrictEqual(lines, ['[TikTokKit] storage IS_GAME_MUSIC: boolean_read false, read as no value',
                                 '[TikTokKit] storage TUTORIAL_DONE: boolean_read true, read as no value'], 'one line per key');
  assert.strictEqual(s.data.IS_GAME_MUSIC, false);
  s.restore();
});
test('console_line_only_for_shapes_that_point_at_the_platform', function () {
  var lines = [], warn = console.warn; console.warn = function (x) { lines.push(String(x)); };
  try {
    var quiet = fakeRuntime({absent: null, noKeys: true});            // never written, no key list: the usual null
    assert.strictEqual(quiet.cc.sys.localStorage.getItem('level'), null);
    quiet.restore();
    var undef = fakeRuntime({absent: undefined, noKeys: true});
    assert.strictEqual(undef.cc.sys.localStorage.getItem('level'), null);
    undef.restore();
    assert.deepStrictEqual(lines, [], 'no line for a plain missing key');
    var odd = fakeRuntime({absent: false, noKeys: true});             // a missing key read as false: worth a line
    assert.strictEqual(odd.cc.sys.localStorage.getItem('level'), null);
    odd.restore();
    var listed = fakeRuntime({});                                     // the platform lists the key but hands back nothing
    listed.data.coins = undefined;
    assert.strictEqual(listed.cc.sys.localStorage.getItem('coins'), null);
    listed.restore();
  } finally { console.warn = warn; }
  assert.deepStrictEqual(lines, ['[TikTokKit] storage level: boolean_read false, read as no value',
                                 '[TikTokKit] storage coins: empty_read, read as no value']);
});
test('reading_never_throws_for_any_value_shape', function () {
  [{}, {noKeys: true}].forEach(function (keys) {
    [true, false, '', undefined, null, NaN, 0, 1, 45, 'x', {a: 1}].forEach(function (stored) {
      var s = fakeRuntime(Object.assign({absent: false}, keys));
      s.data.k = stored;
      assert.doesNotThrow(function () { s.cc.sys.localStorage.getItem('k'); s.cc.sys.localStorage.getItem('missing'); },
        'stored ' + String(stored) + (keys.noKeys ? ', no key list' : ''));
      assert.doesNotThrow(function () { s.cc.sys.localStorage.setItem('k', 5); });
      s.restore();
    });
  });
  var t = fakeRuntime({throwListed: true, throwAbsent: true, noKeys: true});
  t.data.k = 1;
  assert.strictEqual(t.cc.sys.localStorage.getItem('k'), null);
  assert.strictEqual(t.cc.sys.localStorage.getItem('missing'), null);
  t.restore();
});
test('listed_empty_string_stays_empty_string', function () {
  var s = fakeRuntime({absent: ''});
  s.cc.sys.localStorage.setItem('name', '');
  assert.strictEqual(s.cc.sys.localStorage.getItem('name'), '');
  assert.strictEqual(s.cc.sys.localStorage.getItem('other'), null);
  s.restore();
});
test('object_read_is_handed_back_unchanged', function () {
  var s = fakeRuntime({});
  var obj = {coins: 9};
  s.data.save = obj;                        // the platform hands back an object
  assert.strictEqual(s.cc.sys.localStorage.getItem('save'), obj);
  s.restore();
});
test('raw_number_read_becomes_text', function () {
  var s = fakeRuntime({});
  s.data.n = 12;
  assert.strictEqual(s.cc.sys.localStorage.getItem('n'), '12');
  s.restore();
});
test('string_values_pass_through', function () {
  var s = fakeRuntime({absent: false});
  s.cc.sys.localStorage.setItem('k', '{"a":1}');
  assert.strictEqual(s.cc.sys.localStorage.getItem('k'), '{"a":1}');
  s.restore();
});
test('savestore_key_is_read_raw', function () {
  var s = fakeRuntime({numberAs: true, absent: false});
  s.data['demo:768:save:v1'] = 5;            // listed, unreadable: SaveStore must still see true and recover
  assert.strictEqual(s.cc.sys.localStorage.getItem('demo:768:save:v1'), true);
  assert.strictEqual(s.cc.sys.localStorage.getItem('demo:768:save:v1:corrupt-backup'), false, 'raw absent value');
  assert.strictEqual(s.cc.sys.localStorage.getItem('demo:768:save:v1x'), null, 'only the exact SaveStore pattern');
  s.restore();
});
test('install_twice_is_one_layer', function () {
  var s = fakeRuntime({absent: false});
  var first = s.cc.sys.localStorage.getItem;
  assert.strictEqual(s.installed, true);
  assert.strictEqual(install(s.cc, {}), false, 'second install does nothing');
  assert.strictEqual(s.cc.sys.localStorage.getItem, first);
  s.restore();
});
test('no_storage_does_not_throw', function () {
  assert.strictEqual(install({sys: {}}, {}), false);
  assert.strictEqual(install(undefined, undefined), false);
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
console.log(JSON.stringify({suite: 'storage-guard', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
if (failed.length) process.exitCode = 1;
