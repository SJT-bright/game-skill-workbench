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
test('unwritten_key_without_key_list_is_null', function () {
  var s = fakeRuntime({absent: false, noKeys: true});
  assert.strictEqual(s.cc.sys.localStorage.getItem('level'), null);
  assert.strictEqual(s.cc.sys.localStorage.getItem('x'), null);
  s.restore();
});
test('read_that_throws_for_unlisted_key_is_null', function () {
  var s = fakeRuntime({throwAbsent: true});
  assert.strictEqual(s.cc.sys.localStorage.getItem('coins'), null);
  s.restore();
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
test('raw_number_written_before_the_guard_reads_true_then_null', function () {
  var s = fakeRuntime({numberAs: true});
  s.data.level = 7;                         // written by an old build without the guard
  assert.strictEqual(s.cc.sys.localStorage.getItem('level'), null, 'listed key, unreadable value -> default once');
  s.restore();
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
