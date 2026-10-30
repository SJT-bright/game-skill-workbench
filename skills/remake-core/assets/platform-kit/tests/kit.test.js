'use strict';
// Kit tests for SaveStore + MissionFlow + PlatformConfig (Node SDK substitutes; no engine, no device).
// Scenarios come from the skill's recorded failures (tiktok-home-growth.md, Run Home energy save bug).
var assert = require('assert');
var path = require('path');
var base = process.env.KIT_DIR || path.join(__dirname, '..', 'assets', 'tiktok-platform');
var config = require(path.join(base, 'PlatformConfig.js'));
var SaveStore = require(path.join(base, 'SaveStore.js'));
var MissionFlow = require(path.join(base, 'MissionFlow.js'));
var Mission = require(path.join(base, 'TikTokMissionService.js'));

var results = [];
function flush() { return new Promise(function (r) { setTimeout(r, 0); }); }
async function test(name, run) {
  try { await run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

function memoryStorage() {
  var map = {}, s = {
    failWrite: false, transform: null, writes: 0,
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null; },
    setItem: function (k, v) {
      if (s.failWrite) throw new Error('quota');
      s.writes++;
      map[k] = s.transform ? s.transform(String(v)) : String(v);
    },
    raw: map
  };
  return s;
}

// Mission SDK substitute: every call is held until the test settles it.
function missionSDK() {
  var calls = [], supported = {addShortcut: true, getShortcutMissionReward: true, startEntranceMission: true, getEntranceMissionReward: true};
  var sdk = {canIUse: function (m) { return supported[m] === true; }};
  Object.keys(supported).forEach(function (m) {
    sdk[m] = function (opts) { var c = {method: m, opts: opts}; calls.push(c); return undefined; };
  });
  return {sdk: sdk, calls: calls, supported: supported,
    last: function (m) { for (var i = calls.length - 1; i >= 0; i--) if (calls[i].method === m) return calls[i]; return null; }};
}

function setup(options) {
  options = options || {};
  var time = 0, storage = options.storage || memoryStorage(), fake = missionSDK();
  var missions = new Mission({getSDK: function () { return fake.sdk; }, now: function () { return time; }, autoPoll: false, timeoutMs: 10000});
  var store = new SaveStore({coins: 0}, {storage: storage, key: 'test:save'});
  store.load();
  var views = [];
  var flow = new MissionFlow({
    store: store, missions: missions, native: options.native !== undefined ? options.native : true,
    reward: function (kind, draft) { draft.coins += 25; },
    rewardText: {shortcut: '+25 Coins', profile: '+25 Coins'},
    render: function (v) { views.push(v); }
  });
  return {flow: flow, store: store, storage: storage, fake: fake, views: views, missions: missions,
    advance: function (ms) { time += ms; missions.tick(); }, view: function () { return views[views.length - 1]; }};
}

(async function () {
  // ---------- PlatformConfig ----------
  await test('config_three_placements_and_namespaced_save_key', function () {
    assert.strictEqual(config.rewardedPlacements.length, 3);
    Object.keys(config.placementMap).forEach(function (k) { assert(config.getAdUnitId(k).indexOf('ad') === 0, k); });
    assert.strictEqual(config.getAdUnitId('not_listed'), '');
    assert(config.saveKey().indexOf(config.gameId + ':') === 0);
  });
  await test('config_growth_reward_is_5B_and_refuses_unset_B', function () {
    var keep = config.normalLevelCoins;
    try {
      assert.strictEqual(config.GROWTH_REWARD_B, 5);
      config.normalLevelCoins = 0;
      assert.throws(function () { config.growthReward(); }, /normalLevelCoins/);
      config.normalLevelCoins = 2.5;
      assert.throws(function () { config.growthReward(); }, /normalLevelCoins/);
      config.normalLevelCoins = 12;
      assert.strictEqual(config.growthReward(), 60);
      // a forgotten B pays nothing and keeps the entry unclaimed (SaveStore refuses the throwing mutator)
      config.normalLevelCoins = 0;
      var s = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'g'});
      s.load();
      var r = s.update(function (d) { d.platformClaims.shortcut = true; d.coins += config.growthReward(); });
      assert.strictEqual(r.ok, false);
      assert.strictEqual(s.data.coins, 0);
      assert.strictEqual(s.isClaimed('shortcut'), false);
    } finally { config.normalLevelCoins = keep; }
  });

  // ---------- SaveStore ----------
  await test('save_new_has_defaults_and_platform_claims', function () {
    var s = new SaveStore({coins: 5}, {storage: memoryStorage(), key: 'k'});
    var r = s.load();
    assert(r.ok); assert.strictEqual(r.status, 'new');
    assert.deepStrictEqual(r.data.platformClaims, {shortcut: false, profile: false});
    assert.strictEqual(r.data.coins, 5);
  });
  await test('save_update_persists_exact_string_and_reloads', function () {
    var st = memoryStorage(), s = new SaveStore({coins: 0}, {storage: st, key: 'k'});
    s.load();
    var r = s.update(function (d) { d.coins = 40; });
    assert(r.ok);
    var again = new SaveStore({coins: 0}, {storage: st, key: 'k'}); again.load();
    assert.strictEqual(again.get().coins, 40);
    assert.strictEqual(typeof st.raw.k, 'string');
  });
  await test('save_write_failure_reports_error_and_keeps_memory', function () {
    var st = memoryStorage(), s = new SaveStore({coins: 10}, {storage: st, key: 'k'});
    s.load(); st.failWrite = true;
    var r = s.update(function (d) { d.coins = 999; });
    assert(!r.ok); assert.strictEqual(r.error, 'write_failed');
    assert.strictEqual(s.get().coins, 10);
  });
  await test('save_readback_mismatch_rejected_memory_kept_previous_restored', function () {
    var st = memoryStorage(), s = new SaveStore({coins: 1}, {storage: st, key: 'k'});
    s.load(); s.update(function (d) { d.coins = 2; });
    var before = st.raw.k;
    st.transform = function (v) { return v.replace('"coins":3', '"coins":0'); };
    var r = s.update(function (d) { d.coins = 3; });
    assert(!r.ok); assert.strictEqual(r.error, 'readback_mismatch');
    assert.strictEqual(s.get().coins, 2);
    st.transform = null;
    assert.strictEqual(st.raw.k.indexOf('"coins":0') >= 0 ? 'bad' : 'ok', 'ok');
    assert(before.indexOf('"coins":2') >= 0);
  });
  await test('save_corrupt_is_backed_up_and_one_time_rewards_not_repaid', function () {
    var st = memoryStorage(); st.raw.k = '{not json';
    var s = new SaveStore({coins: 0}, {storage: st, key: 'k'});
    var r = s.load();
    assert.strictEqual(r.status, 'recovered');
    assert.strictEqual(st.raw['k:corrupt-backup'], '{not json');
    assert(s.isClaimed('shortcut') && s.isClaimed('profile'));
  });
  await test('save_cancelled_mutator_does_not_write', function () {
    var st = memoryStorage(), s = new SaveStore({}, {storage: st, key: 'k'});
    s.load(); var w = st.writes;
    var r = s.update(function () { return false; });
    assert(!r.ok); assert.strictEqual(r.error, 'cancelled'); assert.strictEqual(st.writes, w);
  });
  await test('save_object_returned_by_storage_is_accepted', function () {
    var st = memoryStorage(); st.getItem = function () { return {gold: 7, coins: 3}; };
    var s = new SaveStore({coins: 0}, {storage: st, key: 'k'});
    var r = s.load();
    assert(r.ok); assert.strictEqual(s.get().coins, 3); assert.strictEqual(s.get().gold, 7);
  });
  // MergeShot2048 v81-v85 on a real iPhone (D6 items 4 + 9): TikTok storage read back true/false/undefined or threw.
  [['true', true], ['false', false], ['undefined', undefined], ['throws', 'THROW']].forEach(function (c) {
    test('save_read_' + c[0] + '_for_missing_key_is_no_save_and_defaults_written', function () {
      var st = memoryStorage(), get = st.getItem;
      st.getItem = function (k) { if (k === 'k' && !Object.prototype.hasOwnProperty.call(st.raw, k)) { if (c[1] === 'THROW') throw new Error('read'); return c[1]; } return get(k); };
      var s = new SaveStore({coins: 5}, {storage: st, key: 'k', storageKeys: function () { return Object.keys(st.raw); }, login: false});
      var r = s.load();
      assert(r.ok, 'a missing key is not an error'); assert.strictEqual(r.status, 'new');
      assert.strictEqual(s.get().coins, 5);
      assert.strictEqual(typeof st.raw.k, 'string', 'defaults written once as text');
      assert.strictEqual(st.raw['k:corrupt-backup'], undefined, 'nothing to back up');
      var again = new SaveStore({coins: 0}, {storage: st, key: 'k', storageKeys: function () { return Object.keys(st.raw); }, login: false});
      assert.strictEqual(again.load().status, 'loaded', 'next start reads the written save');
      assert.strictEqual(again.get().coins, 5);
    });
  });
  await test('save_read_true_for_existing_key_is_recovered_once_not_every_read', function () {
    var st = memoryStorage(); st.raw.k = 'x';
    var get = st.getItem, broken = true;
    st.getItem = function (k) { return k === 'k' && broken ? true : get(k); };
    var s = new SaveStore({coins: 0}, {storage: st, key: 'k', storageKeys: function () { return Object.keys(st.raw); }, login: false});
    var r = s.load();
    assert.strictEqual(r.status, 'recovered'); assert(s.isClaimed('shortcut'), 'one-time rewards not paid twice');
    assert.strictEqual(st.raw['k:corrupt-backup'], 'true');
    broken = false;
    var again = new SaveStore({coins: 0}, {storage: st, key: 'k', storageKeys: function () { return Object.keys(st.raw); }, login: false});
    assert.strictEqual(again.load().status, 'loaded', 'defaults were written once; no repeated failure');
  });
  await test('save_numbers_are_written_as_text', function () {
    var st = memoryStorage(), s = new SaveStore({level: 1, gems: 0}, {storage: st, key: 'k', login: false});
    s.load(); s.update(function (d) { d.level = 2; d.gems = 16; });
    assert.strictEqual(typeof st.raw.k, 'string');
    var again = new SaveStore({level: 1, gems: 0}, {storage: st, key: 'k', login: false}); again.load();
    assert.strictEqual(again.get().level, 2); assert.strictEqual(again.get().gems, 16);
  });
  // Mabel's Meadow r8 (D4 problem 6): one fire-and-forget login after the save loads.
  await test('login_sent_once_after_load_and_never_awaited', async function () {
    var calls = [];
    globalThis.tt = {login: function (o) { calls.push(o); return new Promise(function () {}); }};
    SaveStore._resetLoginForTests && SaveStore._resetLoginForTests();
    try {
      var a = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'a'});
      var r = a.load();
      assert(r.ok, 'load returns at once, before any login answer');
      assert.strictEqual(calls.length, 0, 'login is deferred, not inside load');
      await flush();
      assert.strictEqual(calls.length, 1, 'login sent after the save loaded');
      var b = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'b'}); b.load(); a.load(); await flush();
      assert.strictEqual(calls.length, 1, 'only one login per game process');
      assert(a.update(function (d) { d.coins = 3; }).ok, 'save keeps working while login never answers');
    } finally { delete globalThis.tt; }
  });
  await test('login_failure_throw_or_missing_api_changes_nothing', async function () {
    var variants = [
      function () { return {login: function (o) { o.fail({errMsg: 'login:fail'}); }}; },
      function () { return {login: function () { throw new Error('boom'); }}; },
      function () { return {login: function () { return Promise.reject(new Error('no')); }}; },
      function () { return {}; }
    ];
    for (var i = 0; i < variants.length; i++) {
      globalThis.tt = variants[i]();
      SaveStore._resetLoginForTests && SaveStore._resetLoginForTests();
      try {
        var s = new SaveStore({coins: 1}, {storage: memoryStorage(), key: 'k'});
        var r = s.load(); await flush(); await flush();
        assert(r.ok, 'variant ' + i); assert.strictEqual(s.get().coins, 1);
        assert(s.update(function (d) { d.coins = 2; }).ok, 'variant ' + i + ' save still works');
      } finally { delete globalThis.tt; }
    }
  });

  // ---------- MissionFlow ----------
  await test('flow_normal_claim_once_in_one_write', async function () {
    var t = setup();
    t.flow.open('shortcut');
    assert(t.fake.last('getShortcutMissionReward'), 'opening rechecks eligibility');
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: false}); await flush();
    assert.strictEqual(t.view().phase, 'idle'); assert(/Open this game/.test(t.view().message));
    t.flow.start(); t.fake.last('addShortcut').opts.success({}); await flush();
    assert.strictEqual(t.view().message, MissionFlow.TEXT.navigated);
    t.flow.onShow();
    var w = t.storage.writes;
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.storage.writes, w + 1, 'claim + coins in exactly one write');
    assert.strictEqual(t.store.get().coins, 25);
    assert(t.store.isClaimed('shortcut'));
    assert.strictEqual(t.view().phase, 'done'); assert(/\+25 Coins/.test(t.view().message));
    var again = new SaveStore({coins: 0}, {storage: t.storage, key: 'test:save'}); again.load();
    assert.strictEqual(again.get().coins, 25); assert(again.isClaimed('shortcut'));
  });
  await test('flow_leave_during_query_A_new_query_B_and_late_A_ignored', async function () {
    var t = setup();
    t.flow.open('profile');
    var A = t.fake.last('getEntranceMissionReward');
    t.flow.onShow();
    var B = t.fake.last('getEntranceMissionReward');
    assert(A !== B, 'coming back must send a NEW query');
    A.opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.store.get().coins, 0, 'late A must not pay');
    B.opts.success({canReceiveReward: false}); await flush();
    assert.strictEqual(t.view().phase, 'idle'); assert(t.view().message.length > 0);
    assert.strictEqual(t.store.get().coins, 0);
  });
  await test('flow_taps_during_one_check_are_merged', async function () {
    var t = setup();
    t.flow.open('shortcut');
    t.flow.check(); t.flow.check(); t.flow.check();
    var n = t.fake.calls.filter(function (c) { return c.method === 'getShortcutMissionReward'; }).length;
    assert.strictEqual(n, 1);
  });
  await test('flow_every_non_success_result_is_visible', async function () {
    var cases = [
      ['fail', function (c) { c.opts.fail({errorCode: 1}); }],
      ['ineligible', function (c) { c.opts.success({canReceiveReward: false}); }],
      ['complete_only', function (c, t) { c.opts.complete(); t.advance(150); }],
      ['timeout', function (c, t) { t.advance(10001); }]
    ];
    for (var i = 0; i < cases.length; i++) {
      var t = setup();
      t.flow.open('shortcut');
      cases[i][1](t.fake.last('getShortcutMissionReward'), t); await flush();
      assert.strictEqual(t.view().phase, 'idle', cases[i][0]);
      assert(t.view().message && t.view().message !== MissionFlow.TEXT.checking, cases[i][0] + ' shows a message');
      assert.strictEqual(t.store.get().coins, 0, cases[i][0]);
      assert(t.view().canCheck, cases[i][0] + ' can retry');
    }
  });
  await test('flow_unsupported_client_shows_message', async function () {
    var t = setup();
    t.fake.supported.getShortcutMissionReward = false;
    t.flow.open('shortcut'); await flush();
    assert.strictEqual(t.view().phase, 'idle'); assert(/supported TikTok/.test(t.view().message));
  });
  await test('flow_navigation_answer_never_overwrites_newer_check', async function () {
    var t = setup();
    t.flow.open('shortcut');
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: false}); await flush();
    t.flow.start(); var nav = t.fake.last('addShortcut');
    t.flow.onShow();
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.view().phase, 'done');
    nav.opts.success({}); await flush();
    assert.strictEqual(t.view().phase, 'done'); assert(/Reward received/.test(t.view().message));
  });
  await test('flow_save_failure_pays_nothing_then_retry_pays_once', async function () {
    var t = setup();
    t.flow.open('shortcut'); t.storage.failWrite = true;
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.view().message, MissionFlow.TEXT.saveFailed);
    assert(!t.store.isClaimed('shortcut')); assert.strictEqual(t.store.get().coins, 0);
    t.storage.failWrite = false;
    t.flow.check(); t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.store.get().coins, 25);
    t.flow.check(); await flush();
    assert.strictEqual(t.store.get().coins, 25, 'never twice');
    assert.strictEqual(t.view().message, MissionFlow.TEXT.claimed);
  });
  await test('flow_close_then_late_result_changes_nothing', async function () {
    var t = setup();
    t.flow.open('profile'); var q = t.fake.last('getEntranceMissionReward');
    t.flow.close(); var n = t.views.length;
    q.opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.views.length, n); assert.strictEqual(t.store.get().coins, 0);
    assert.strictEqual(t.view().open, false);
  });
  await test('flow_reopen_after_close_is_not_blocked', async function () {
    var t = setup();
    t.flow.open('profile'); t.flow.close(); t.flow.open('profile');
    var n = t.fake.calls.filter(function (c) { return c.method === 'getEntranceMissionReward'; }).length;
    assert.strictEqual(n, 2, 'old lock released, new query sent');
  });
  await test('flow_browser_preview_no_auto_check_and_no_reward', async function () {
    var t = setup({native: false});
    t.fake.supported.getShortcutMissionReward = false; t.fake.supported.addShortcut = false;
    t.flow.open('shortcut');
    assert.strictEqual(t.fake.calls.length, 0);
    assert.strictEqual(t.view().message, MissionFlow.TEXT.preview);
    t.flow.start(); await flush();
    assert.strictEqual(t.view().message, MissionFlow.TEXT.preview);
    assert.strictEqual(t.store.get().coins, 0);
  });
  await test('flow_check_ends_without_tick_using_default_timer', async function () {
    // No missions passed: MissionFlow builds its own service from the global TTMinis.game, like in a game.
    var fake = missionSDK();
    globalThis.TTMinis = {game: fake.sdk};
    try {
      var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'k'}); store.load();
      var last = null;
      var flow = new MissionFlow({store: store, missionTimeoutMs: 60, reward: function () {}, render: function (v) { last = v; }});
      flow.open('shortcut');
      assert.strictEqual(fake.calls.length, 1, 'real global SDK was used');
      await new Promise(function (r) { setTimeout(r, 300); });
      assert.strictEqual(last.phase, 'idle'); assert(/too long/.test(last.message));
      flow.dispose();
    } finally { delete globalThis.TTMinis; }
  });
  await test('flow_tt_only_runtime_is_native_not_local_preview', async function () {
    // Mabel's Meadow r7/r8 (D4 1.3): the runtime exposes only tt. MissionFlow must find the SDK in the
    // same order as TikTokMissionService (TTMinis.game, tt, wx) and never show the LOCAL PREVIEW text.
    var fake = missionSDK();
    delete globalThis.TTMinis; globalThis.tt = fake.sdk;
    try {
      var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'k'}); store.load();
      var last = null;
      var flow = new MissionFlow({store: store, missionTimeoutMs: 60, reward: function () {}, render: function (v) { last = v; }});
      flow.open('profile');
      assert.strictEqual(last.native, true, 'tt-only runtime is native');
      assert.notStrictEqual(last.message, MissionFlow.TEXT.preview);
      assert.strictEqual(fake.calls.length, 1, 'opening checks the reward through tt');
      flow.dispose();
    } finally { delete globalThis.tt; }
  });
  await test('flow_no_sdk_at_all_is_local_preview', async function () {
    delete globalThis.TTMinis; delete globalThis.tt; delete globalThis.wx;
    var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'k'}); store.load();
    var last = null;
    var flow = new MissionFlow({store: store, missionTimeoutMs: 60, reward: function () {}, render: function (v) { last = v; }});
    flow.open('shortcut');
    assert.strictEqual(last.native, false);
    assert.strictEqual(last.message, MissionFlow.TEXT.preview);
    flow.dispose();
  });
  await test('flow_two_entries_paid_separately_once_each', async function () {
    var t = setup();
    t.flow.open('shortcut'); t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    t.flow.open('profile'); t.fake.last('getEntranceMissionReward').opts.success({canReceiveReward: true}); await flush();
    t.flow.open('shortcut'); await flush();
    assert.strictEqual(t.store.get().coins, 50);
    assert.strictEqual(t.view().message, MissionFlow.TEXT.claimed);
  });

  // ---------- v7.7: SaveStore + parts/storage-guard.js on the same storage ----------
  await test('savestore_with_storage_guard_behaves_the_same', function () {
    var install = require(process.env.STORAGE_GUARD || path.join(__dirname, '..', 'parts', 'storage-guard.js'));
    var key = 'demo:7683427172773644296:save:v1';
    // TikTok-like storage: unwritten key reads false; 'poison' keys read back true.
    function tiktokStorage(poison) {
      var map = {}, st = {
        getItem: function (k) { if (!(k in map)) return false; return poison[k] ? true : map[k]; },
        setItem: function (k, v) { map[k] = v; }, raw: map
      };
      return st;
    }
    function run(guarded, prefill, poison) {
      var st = tiktokStorage(poison || {});
      Object.keys(prefill || {}).forEach(function (k) { st.raw[k] = prefill[k]; });
      if (guarded) install({sys: {localStorage: st}}, {getStorageInfoSync: function () { return {keys: Object.keys(st.raw)}; }});
      var keys = function () { return Object.keys(st.raw); };
      var s = new SaveStore({coins: 0}, {storage: st, key: key, storageKeys: keys, login: false});
      var r = s.load();
      var u = s.update(function (d) { d.coins += 7; });
      var again = new SaveStore({coins: 0}, {storage: st, key: key, storageKeys: keys, login: false}).load();
      return {status: r.status, ok: r.ok, claimed: s.isClaimed('shortcut'), update: u.ok, coins: s.get().coins,
        again: again.status, backup: (key + ':corrupt-backup') in st.raw, guardLevel: guarded ? (st.setItem('level', 3), st.raw.level) : 3};
    }
    var cases = [
      ['new_player', null, null],
      ['existing_save', (function () { var o = {}; o[key] = JSON.stringify({coins: 4, platformClaims: {shortcut: false, profile: true}, meta: {}}); return o; })(), null],
      ['existing_key_reads_true', (function () { var o = {}; o[key] = '{"coins":9}'; return o; })(), (function () { var o = {}; o[key] = true; return o; })()]
    ];
    cases.forEach(function (c) {
      var plain = run(false, c[1], c[2]), withGuard = run(true, c[1], c[2]);
      assert.strictEqual(withGuard.guardLevel, '3', c[0] + ': guard is really installed (number written as text)');
      delete plain.guardLevel; delete withGuard.guardLevel;
      assert.deepStrictEqual(withGuard, plain, c[0]);
    });
    assert.strictEqual(run(true, cases[2][1], cases[2][2]).status, 'recovered');
  });

  await test('flow_without_reward_pays_platformconfig_growth_reward', async function () {
    var keep = config.normalLevelCoins;
    try {
      config.normalLevelCoins = 12;
      var fake = missionSDK(), time = 0, views = [];
      var missions = new Mission({getSDK: function () { return fake.sdk; }, now: function () { return time; }, autoPoll: false, timeoutMs: 10000});
      var store = new SaveStore({coins: 3}, {storage: memoryStorage(), key: 'gr', login: false}); store.load();
      var flow = new MissionFlow({store: store, missions: missions, native: true, render: function (v) { views.push(v); }});
      flow.open('shortcut'); fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(store.get().coins, 63, '3 + 5B (B = 12)');
      assert.strictEqual(views[views.length - 1].message, MissionFlow.TEXT.granted + '+60 Coins');
      config.normalLevelCoins = 0;
      var store2 = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'gr2', login: false}); store2.load();
      var fake2 = missionSDK();
      var flow2 = new MissionFlow({store: store2, native: true, render: function () {},
        missions: new Mission({getSDK: function () { return fake2.sdk; }, now: function () { return 0; }, autoPoll: false, timeoutMs: 10000})});
      flow2.open('profile'); fake2.last('getEntranceMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(store2.get().coins, 0, 'unset B pays nothing');
      assert.strictEqual(store2.isClaimed('profile'), false, 'and can be retried');
    } finally { config.normalLevelCoins = keep; }
  });

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'tiktok-platform-kit', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
