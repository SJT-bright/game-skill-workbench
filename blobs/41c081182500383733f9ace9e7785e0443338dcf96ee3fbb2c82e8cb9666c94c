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
    assert.strictEqual(t.view().phase, 'idle'); assert.strictEqual(t.view().message, MissionFlow.TEXT.notReady);
    t.flow.start(); t.fake.last('addShortcut').opts.success({}); await flush();
    assert.strictEqual(t.view().message, MissionFlow.TEXT.navigated);
    t.flow.onShow({scene: 'desktop_shortcut'});
    var w = t.storage.writes;
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.storage.writes, w + 1, 'claim + coins in exactly one write');
    assert.strictEqual(t.store.get().coins, 25);
    assert(t.store.isClaimed('shortcut'));
    assert.strictEqual(t.view().phase, 'done'); assert.strictEqual(t.view().message, '', 'automatic award stays quiet');
    var again = new SaveStore({coins: 0}, {storage: t.storage, key: 'test:save'}); again.load();
    assert.strictEqual(again.get().coins, 25); assert(again.isClaimed('shortcut'));
  });
  await test('flow_leave_during_query_A_new_query_B_and_late_A_ignored', async function () {
    var t = setup();
    t.flow.open('profile');
    var A = t.fake.last('getEntranceMissionReward');
    t.flow.onShow({scene: 'center'});
    var B = t.fake.last('getEntranceMissionReward');
    assert(A !== B, 'coming back must send a NEW query');
    A.opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.store.get().coins, 0, 'late A must not pay');
    B.opts.success({canReceiveReward: false}); await flush();
    assert.strictEqual(t.view().phase, 'idle'); assert.strictEqual(t.view().message, '');
    assert.strictEqual(t.store.get().coins, 0);
  });
  await test('flow_taps_during_one_check_are_merged', async function () {
    var t = setup();
    t.flow.open('shortcut');
    t.flow.check(); t.flow.check(); t.flow.check();
    var n = t.fake.calls.filter(function (c) { return c.method === 'getShortcutMissionReward'; }).length;
    assert.strictEqual(n, 1);
  });
  await test('flow_second_sidebar_entry_replaces_pending_qualification', async function () {
    var t = setup();
    t.flow.onShow({scene: 'center'});
    var first = t.fake.last('getEntranceMissionReward');
    t.flow.onShow({scene: 'center'});
    var latest = t.fake.last('getEntranceMissionReward');
    assert.notStrictEqual(latest, first, 'each real entry uses its own qualification');
    first.opts.success({canReceiveReward: true});
    latest.opts.success({canReceiveReward: false});
    await flush();
    assert.strictEqual(t.store.get().coins, 0);
    assert.strictEqual(t.store.isClaimed('profile'), false);
  });
  await test('flow_ordinary_return_does_not_query_last_selected_task', async function () {
    var t = setup();
    t.flow.open('profile', {navigate: true});
    t.fake.last('startEntranceMission').opts.success({}); await flush();
    t.flow.onShow({scene: 'search'}); await flush();
    assert.strictEqual(t.fake.last('getEntranceMissionReward'), null);
    assert.strictEqual(t.store.get().coins, 0);
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
    t.flow.onShow({scene: 'desktop_shortcut'});
    t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    assert.strictEqual(t.view().phase, 'done');
    nav.opts.success({}); await flush();
    assert.strictEqual(t.view().phase, 'done'); assert.strictEqual(t.view().message, '');
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
  await test('flow_runtime_without_canIUse_is_native_and_still_calls', async function () {
    // 简化.11.3: a runtime with the mission methods but no canIUse (or canIUse answering undefined) is TikTok.
    var fake = missionSDK();
    delete fake.sdk.canIUse;
    delete globalThis.TTMinis; globalThis.tt = fake.sdk;
    try {
      var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'k'}); store.load();
      var last = null;
      var flow = new MissionFlow({store: store, missionTimeoutMs: 60, reward: function () {}, render: function (v) { last = v; }});
      flow.open('profile', {navigate: true});
      assert.strictEqual(last.native, true, 'no canIUse is still native');
      assert.strictEqual(fake.calls.filter(function (c) { return c.method === 'startEntranceMission'; }).length, 1, 'the tap goes to TikTok');
      flow.dispose();
      fake.sdk.canIUse = function () { return undefined; };
      flow = new MissionFlow({store: store, missionTimeoutMs: 60, reward: function () {}, render: function (v) { last = v; }});
      flow.open('shortcut', {navigate: true});
      assert.strictEqual(fake.calls.filter(function (c) { return c.method === 'addShortcut'; }).length, 1, 'canIUse answering undefined does not block');
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

  // ---------- 简化.11.13 P10: SaveStore.grant / SaveStore.best ----------
  // Each check takes a way of paying a reward (or of keeping a best score) and returns what went wrong.
  // The kit's grant/best must pass every check; the old writings from the 2026-11-04 census must be caught.
  function rewardEnv(coins, storage) {
    var st = storage || memoryStorage();
    var store = new SaveStore({coins: coins || 0}, {storage: st, key: 'p10', login: false}); store.load();
    return {storage: st, store: store, game: {coins: store.get().coins}, ui: [], defaults: {coins: coins || 0}};
  }
  function reload(env) { var s = new SaveStore(env.defaults || {coins: 0}, {storage: env.storage, key: 'p10', login: false}); s.load(); return s.get(); }
  var claimWays = {
    kit_grant: function (env, id, amount) {
      return env.store.grant({id: id, add: {coins: amount}}, function (r) { env.game.coins = r.data.coins; env.ui.push('coins:' + r.data.coins, 'leave'); });
    },
    // 方块冲冲 (02:163, 10-21): inventory changed in memory first, then saved; a failed save could not be retried.
    old_blockdash_memory_first: function (env, id, amount) {
      env.game.coins += amount; env.ui.push('coins:' + env.game.coins);
      return env.store.update(function (d) { d.coins = env.game.coins; });
    },
    // 水杯传奇 HappyCup (03:398, 10-23): saved the base coins, then left the win page whatever the save answered.
    old_happycup_leave_anyway: function (env, id, amount) {
      var r = env.store.update(function (d) { d.coins += amount; });
      env.game.coins = env.store.get().coins; env.ui.push('coins:' + env.game.coins, 'leave');
      return r;
    }
  };
  function claimWriteFails(way) {
    var env = rewardEnv(10), bad = [];
    env.storage.failWrite = true;
    var r = way(env, 'win:3', 40);
    if (r && r.ok) bad.push('reported ok');
    if (env.store.get().coins !== 10) bad.push('saved coins changed');
    if (env.game.coins !== 10) bad.push('wallet in memory changed to ' + env.game.coins);
    if (env.ui.length) bad.push('UI ran: ' + env.ui.join(','));
    env.storage.failWrite = false;
    if (reload(env).coins !== 10) bad.push('storage changed');
    return bad;
  }
  function claimReadbackFails(way) {
    var env = rewardEnv(10), bad = [];
    way(env, 'win:1', 50);
    var committed = env.store.get().coins, ui = env.ui.length;
    env.storage.transform = function (v) { return v.replace('"coins":90', '"coins":0'); };
    var r = way(env, 'win:2', 30);
    env.storage.transform = null;
    if (committed !== 60) bad.push('first reward not committed: ' + committed);
    if (r && r.ok) bad.push('reported ok');
    if (env.store.get().coins !== committed) bad.push('saved coins became ' + env.store.get().coins);
    if (reload(env).coins !== committed) bad.push('storage lost the committed ' + committed + ': ' + reload(env).coins);
    if (env.game.coins !== committed) bad.push('wallet in memory became ' + env.game.coins);
    if (env.ui.length !== ui) bad.push('UI ran after the failed read-back');
    return bad;
  }
  function claimTwice(way) {
    var env = rewardEnv(0), bad = [];
    way(env, 'run:7:x2', 20); way(env, 'run:7:x2', 20);
    if (env.store.get().coins !== 20) bad.push('paid ' + env.store.get().coins + ' for one claim id');
    if (reload(env).coins !== 20) bad.push('storage has ' + reload(env).coins);
    if (env.game.coins !== 20) bad.push('wallet shows ' + env.game.coins);
    return bad;
  }
  function bestEnv(prefill) {
    var st = memoryStorage();
    if (prefill !== undefined) st.raw.p10 = JSON.stringify({coins: 0, bestScore: prefill, platformClaims: {shortcut: false, profile: false}, meta: {}});
    var store = new SaveStore({coins: 0}, {storage: st, key: 'p10', login: false}); store.load();
    return {storage: st, store: store, ui: []};
  }
  var bestWays = {
    kit_best: function (env, score) { var r = env.store.best('bestScore', score); env.ui.push('best:' + r.best); return r; },
    // 旋律动物园 MelodyZoo (学习卡 87): MAX_SCORE was read but never put on bestScoreLabel, so the compare starts at the
    // scene's "0" and every score above 0 overwrites the saved best.
    old_melodyzoo_label_zero: function (env, score) {
      var saved = env.store.get().bestScore, label = 0; void saved;
      if (score > label) env.store.update(function (d) { d.bestScore = score; });
    },
    // 海洋逃脱 OceanEscape (学习卡 91, game_over() 373-385): compares only when a record exists; with none it writes 0.
    old_oceanescape_first_skipped: function (env, score) {
      var rec = env.store.get().bestScore;
      if (rec !== undefined && rec !== null) { if (score > rec) env.store.update(function (d) { d.bestScore = score; }); }
      else env.store.update(function (d) { d.bestScore = 0; });
    }
  };
  function bestFirstRun(way) {
    var env = bestEnv(), bad = [];
    way(env, 300);
    if (env.store.get().bestScore !== 300) bad.push('first score saved as ' + env.store.get().bestScore);
    return bad;
  }
  function bestLowerKept(way) {
    var env = bestEnv(500), bad = [];
    way(env, 120);
    if (env.store.get().bestScore !== 500) bad.push('lower score overwrote the best: ' + env.store.get().bestScore);
    way(env, 800);
    if (env.store.get().bestScore !== 800) bad.push('higher score not saved: ' + env.store.get().bestScore);
    return bad;
  }

  await test('grant_write_failure_changes_neither_wallet_nor_ui', function () {
    assert.deepStrictEqual(claimWriteFails(claimWays.kit_grant), []);
    var env = rewardEnv(10); env.storage.failWrite = true;
    var r = env.store.grant({id: 'win:3', add: {coins: 40}}, function () { throw new Error('onDone must not run'); });
    assert.strictEqual(r.ok, false); assert.strictEqual(r.error, 'write_failed');
    env.storage.failWrite = false;
    assert(env.store.grant({id: 'win:3', add: {coins: 40}}).ok, 'the same reward can be retried after a failed save');
    assert.strictEqual(env.store.get().coins, 50);
  });
  await test('grant_readback_failure_keeps_committed_value', function () {
    assert.deepStrictEqual(claimReadbackFails(claimWays.kit_grant), []);
  });
  await test('grant_same_id_twice_pays_once', function () {
    assert.deepStrictEqual(claimTwice(claimWays.kit_grant), []);
    var env = rewardEnv(0), calls = 0;
    env.store.grant({id: 'level:4:first', add: {coins: 5}}, function () { calls++; });
    var again = env.store.grant({id: 'level:4:first', add: {coins: 5}}, function () { calls++; });
    assert.strictEqual(again.ok, true); assert.strictEqual(again.already, true); assert.strictEqual(calls, 1);
    var s2 = new SaveStore({coins: 0}, {storage: env.storage, key: 'p10', login: false}); s2.load();
    assert.strictEqual(s2.grant({id: 'level:4:first', add: {coins: 5}}).already, true, 'claim mark survives a restart');
  });
  await test('grant_coins_and_extra_change_in_one_write_and_spending_checked', function () {
    var env = rewardEnv(30), w = env.storage.writes;
    var r = env.store.grant({id: 'buy:skin_cat', add: {coins: -20}, apply: function (d) { d.skins = ['cat']; }});
    assert(r.ok); assert.strictEqual(env.storage.writes, w + 1, 'coins + owned skin + claim mark in one write');
    assert.deepStrictEqual(reload(env).skins, ['cat']); assert.strictEqual(reload(env).coins, 10);
    assert.strictEqual(env.store.grant({add: {coins: -11}}).error, 'not_enough');
    assert.strictEqual(env.store.grant({add: {cions: 5}}).error, 'unknown_key', 'a typo in the wallet key is refused');
    assert.strictEqual(env.store.grant({add: {coins: 'x'}}).error, 'invalid_amount');
    assert.strictEqual(env.store.get().coins, 10);
  });
  await test('grant_and_best_accept_old_numeric_text_like_storage_guard', function () {
    var st = memoryStorage();
    st.raw.p10 = JSON.stringify({coins: '120', bestScore: '500', lives: true, platformClaims: {shortcut: false, profile: false}, meta: {}});
    var s = new SaveStore({coins: 0, lives: 3}, {storage: st, key: 'p10', login: false}); s.load();
    assert(s.grant({add: {coins: 5, lives: 1}}).ok);
    assert.strictEqual(s.get().coins, 125); assert.strictEqual(s.get().lives, 4, 'unreadable true counts as the default 3');
    var b = s.best('bestScore', 120);
    assert.strictEqual(b.ok, true); assert.strictEqual(b.best, 500); assert.strictEqual(b.isNew, false);
  });
  await test('grant_run_ids_keep_only_last_50', function () {
    var env = rewardEnv(0);
    env.store.grant({id: 'level:1:first', add: {coins: 1}});
    for (var i = 0; i < 60; i++) env.store.grant({id: 'run:' + i + ':x2', add: {coins: 1}});
    var g = env.store.get().meta.grants;
    assert.strictEqual(Object.keys(g).filter(function (k) { return k.indexOf('run:') === 0; }).length, 50);
    assert(g['level:1:first'], 'one-time ids are never dropped');
    assert(!g['run:0:x2'] && g['run:59:x2']);
  });
  await test('best_first_write_and_lower_never_overwrites', function () {
    assert.deepStrictEqual(bestFirstRun(bestWays.kit_best), []);
    assert.deepStrictEqual(bestLowerKept(bestWays.kit_best), []);
    var env = bestEnv(500), w = env.storage.writes;
    var r = env.store.best('bestScore', 500);
    assert.strictEqual(r.isNew, false); assert.strictEqual(env.storage.writes, w, 'equal score writes nothing');
    env.storage.failWrite = true;
    r = env.store.best('bestScore', 900);
    assert.strictEqual(r.ok, false); assert.strictEqual(r.best, 500); assert.strictEqual(env.store.get().bestScore, 500);
    assert.strictEqual(env.store.best('bestScore', NaN).error, 'invalid_value');
  });
  await test('p10_old_census_writings_are_caught', function () {
    var caught = {
      old_blockdash_memory_first: [claimWriteFails, claimReadbackFails, claimTwice],
      old_happycup_leave_anyway: [claimWriteFails, claimTwice],
      old_melodyzoo_label_zero: [bestLowerKept],
      old_oceanescape_first_skipped: [bestFirstRun]
    };
    Object.keys(caught).forEach(function (name) {
      var way = claimWays[name] || bestWays[name];
      caught[name].forEach(function (check) {
        var found = check(way);
        if (process.env.P10_SHOW) console.error(name + ' / ' + check.name + ': ' + JSON.stringify(found));
        assert(found.length > 0, name + ' must be caught by ' + check.name);
      });
    });
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

  // R4E (问题普查补查 第四节 2, 蛋壳特工队 T07:save_value_unvalidated): a save holding 999999 for level / map / VIP / skin.
  var R4E_SCHEMA = {schema: 1, tables: {maps: [1, 2, 3], skins: ['cat', 'dog'], heroes: ['h1', 'h2']},
    keys: {level: {type: 'int', min: 1, max: 60, 'default': 1}, mapId: {type: 'id', 'table': 'maps', 'default': 1},
      vip: {type: 'int', min: 0, max: 3, 'default': 0}, skin: {type: 'id', 'table': 'skins', 'default': 'cat'},
      heroLevel: {type: 'map', keyTable: 'heroes', of: {type: 'int', min: 1, max: 30}, 'default': {h1: 1}},
      coins: {type: 'int', min: 0, 'default': 0}}};
  function r4eStore(schema, logs) {
    var st = memoryStorage();
    st.setItem('egg', JSON.stringify({level: 999999, mapId: 999999, vip: 999999, skin: 999999, coins: 77,
      heroLevel: {h1: 999999, h2: 4, ghost: 1}, platformClaims: {shortcut: false, profile: false}, meta: {}}));
    var o = {storage: st, key: 'egg', login: false, log: function (l) { logs.push(l); }};
    if (schema !== undefined) o.schema = schema;
    return {store: new SaveStore({level: 1, mapId: 1, vip: 0, skin: 'cat', coins: 0, heroLevel: {h1: 1}}, o), storage: st};
  }

  await test('schema_out_of_range_values_fall_back_to_defaults_and_log', async function () {
    var logs = [], w = r4eStore(R4E_SCHEMA, logs), writes = w.storage.writes, r = w.store.load(), d = w.store.get();
    assert.strictEqual(r.ok, true); assert.strictEqual(r.status, 'loaded');
    assert.deepStrictEqual([d.level, d.mapId, d.vip, d.skin, d.coins], [1, 1, 0, 'cat', 77]);
    assert.deepStrictEqual(d.heroLevel, {h1: 1, h2: 4}, 'known hero back to its default, unknown hero dropped');
    assert.strictEqual(r.repaired.length, 5);
    assert.strictEqual(logs.length, 5);
    assert.ok(logs.every(function (l) { return l.indexOf('[SaveStore] schema: ') === 0; }), logs.join('\n'));
    assert.strictEqual(w.storage.writes, writes, 'the read-time check writes nothing');
    assert.strictEqual(w.store.update(function (x) { x.coins += 1; }).ok, true);
    assert.strictEqual(JSON.parse(w.storage.raw.egg).level, 1, 'the next save stores the repaired value');
  });

  await test('schema_absent_or_false_keeps_old_behaviour', async function () {
    [undefined, false].forEach(function (schema) {
      var logs = [], w = r4eStore(schema, logs), r = w.store.load();
      assert.strictEqual(w.store.get().level, 999999, 'without a schema the value is handed back as before');
      assert.strictEqual(r.repaired, undefined); assert.strictEqual(logs.length, 0);
    });
    global.TikTokSaveSchema = R4E_SCHEMA;
    try {
      var logs = [], w = r4eStore(undefined, logs); w.store.load();
      assert.strictEqual(w.store.get().level, 1, 'the generated SaveSchema.js global is used when no option is given');
      var logs2 = [], w2 = r4eStore(false, logs2); w2.store.load();
      assert.strictEqual(w2.store.get().level, 999999, 'schema: false turns it off');
    } finally { delete global.TikTokSaveSchema; }
  });

  // R4J1 (广告skill ad-boost v1.2.17): a year of daily claim ids must not pile up in meta.grants, and pruning must
  // never let a claim that can still be made again pay twice. Ids are the ones the ad-boost modules build.
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function ymd(t) { var d = new Date(t); return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()); }
  var J1_DAYS = 90;   // a quarter keeps the test at about a second; the old kit kept 1620 ids by then (6570, 225 KB a year)
  function yearOfDailyClaims(options) {
    var DAY = 86400000, start = Date.UTC(2026, 10, 5, 12), clock = {t: start};
    var o = {storage: memoryStorage(), key: 'j1', login: false, now: function () { return clock.t; }};
    Object.keys(options || {}).forEach(function (k) { o[k] = options[k]; });
    var s = new SaveStore({coins: 0}, o); s.load();
    var once = ['level:1:first', 'gift:chest:L6', 'gift:home:0', 'checkin:20397'];
    once.forEach(function (id) { s.grant({id: id, add: {coins: 1}}); });
    for (var day = 0; day < J1_DAYS; day++) {
      clock.t = start + day * DAY;
      var today = ymd(clock.t), i;
      for (i = 0; i < 5; i++) s.grant({id: 'online-ladder:' + today + ':' + i, add: {coins: 1}});
      for (i = 0; i < 4; i++) s.grant({id: 'timer-chest:tchest:' + (day * 4 + i) + ':' + (clock.t + i * 60000), add: {coins: 1}});
      for (i = 0; i < 3; i++) s.grant({id: 'coin-ad:' + today + ':r' + i, add: {coins: 1}});
      for (i = 0; i < 6; i++) s.grant({id: 'gift:home:' + (clock.t + i * 1800000), add: {coins: 1}});
    }
    return {store: s, clock: clock, once: once, ymd: ymd, DAY: DAY};
  }
  await test('grant_daily_ids_with_their_day_are_pruned_after_7_days', function () {
    var y = yearOfDailyClaims(), g = y.store.get().meta.grants, n = Object.keys(g).length;
    var bytes = JSON.stringify(g).length;
    assert(n <= 4 + 9 * 18, '90 days of daily claims keep about 8 days of ids, got ' + n);
    assert(bytes < 12000, 'meta.grants stays small, got ' + bytes + ' bytes');
    y.once.forEach(function (id) { assert(g[id], id + ' (no day in it) is kept for good'); });
    assert.strictEqual(y.store.get().coins, 4 + J1_DAYS * 18, 'every claim paid exactly once');
  });
  await test('grant_wheel_daily_ids_are_pruned_offline_and_shopfree_kept_r4n6', function () {   // R4N6 (广告skill)
    var DAY = 86400000, start = Date.UTC(2026, 10, 5, 12), clock = {t: start};
    var s = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'n6', login: false, now: function () { return clock.t; }});
    s.load();
    var keep = ['offline:claim:' + ymd(start), 'shopfree:' + ymd(start) + ':1', 'checkin:20397'];
    keep.forEach(function (id) { s.grant({id: id, add: {coins: 1}}); });
    for (var day = 0; day < 30; day++) {
      clock.t = start + day * DAY;
      for (var i = 0; i < 3; i++) s.grant({id: 'wheel:' + ymd(clock.t) + ':' + i, add: {coins: 1}});
    }
    var g = s.get().meta.grants, wheel = Object.keys(g).filter(function (id) { return id.indexOf('wheel:') === 0; });
    assert(wheel.length <= 3 * 8, '30 days of wheel spins keep about 8 days of ids, got ' + wheel.length);
    keep.forEach(function (id) { assert(g[id], id + ' is not a pruned prefix and stays'); });
    assert.strictEqual(s.grant({id: 'wheel:' + ymd(clock.t) + ':0', add: {coins: 1}}).already, true, 'today\'s spin is still once only');
  });
  await test('grant_pruning_keeps_claims_that_can_still_come_again', function () {
    var y = yearOfDailyClaims(), s = y.store, coins = s.get().coins, today = y.ymd(y.clock.t);
    var threeDaysAgo = y.ymd(y.clock.t - 3 * y.DAY);
    ['online-ladder:' + today + ':0', 'coin-ad:' + threeDaysAgo + ':r2', 'gift:home:' + y.clock.t, 'level:1:first', 'gift:chest:L6']
      .forEach(function (id) {
        var r = s.grant({id: id, add: {coins: 100}});
        assert.strictEqual(r.already, true, id + ' must still be a repeat');
      });
    assert.strictEqual(s.get().coins, coins, 'nothing paid twice');
    var off = yearOfDailyClaims({grantDayPrefixes: []});
    assert(Object.keys(off.store.get().meta.grants).length > J1_DAYS * 18, 'grantDayPrefixes: [] keeps every id (old behaviour)');
  });
  // schema 2 (make_save_schema.py "nullable" / type object / "in_defaults": false), the shapes ad-boost could not express
  var J1_SCHEMA = {schema: 2, tables: {}, keys: {
    'checkin.state': {type: 'object', nullable: true, in_defaults: false},
    'checkin.state.claimed': {type: 'int', min: 0, max: 6, in_defaults: false},
    'checkin.state.last_day': {type: 'int', nullable: true, in_defaults: false},
    'energy.value': {type: 'int', min: 0, max: 60, in_defaults: false},
    'adboostTimerChest.round': {type: 'object', nullable: true, in_defaults: false},
    'wheel.pending': {type: 'int', min: 0, nullable: true, 'default': null}}};
  await test('schema2_null_kept_object_checked_out_of_defaults_key_removed_when_bad', function () {
    var st = memoryStorage(), logs = [];
    st.setItem('j1s', JSON.stringify({checkin: {state: {v: 1, claimed: 99, last_day: null, created: 5}}, energy: {value: 'lots', anchorAt: 3},
      adboostTimerChest: {day: '2026-11-05', round: null}, wheel: {pending: null}, platformClaims: {shortcut: false, profile: false}, meta: {}}));
    var s = new SaveStore({wheel: {pending: null}}, {storage: st, key: 'j1s', login: false, schema: J1_SCHEMA, log: function (l) { logs.push(l); }});
    var r = s.load(), d = s.get();
    assert.strictEqual(d.checkin.state.last_day, null, 'null last_day is a valid value (before: removed, CheckinFlow then repaired it as claimed today)');
    assert.strictEqual(d.adboostTimerChest.round, null);
    assert.strictEqual(d.wheel.pending, null);
    assert.ok(!('claimed' in d.checkin.state), 'bad claimed with no default is removed, CheckinFlow rebuilds it');
    assert.ok(!('value' in d.energy), 'bad energy.value removed, Energy.normalize fills it');
    assert.strictEqual(d.energy.anchorAt, 3);
    assert.strictEqual(r.repaired.length, 2, logs.join('\n'));
    st.setItem('j1s', JSON.stringify({checkin: {state: 'x'}, adboostTimerChest: {round: 7}, platformClaims: {shortcut: false, profile: false}, meta: {}}));
    var s2 = new SaveStore({}, {storage: st, key: 'j1s', login: false, schema: J1_SCHEMA, log: function () {}}); s2.load();
    assert.ok(!('state' in s2.get().checkin) && !('round' in s2.get().adboostTimerChest), 'a non-object state / round is removed');
    assert.strictEqual(SaveStore.SUPPORTED_SCHEMA, 2);
  });

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'tiktok-platform-kit', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
