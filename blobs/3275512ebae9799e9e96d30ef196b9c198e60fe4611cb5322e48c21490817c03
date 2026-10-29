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
  await test('flow_two_entries_paid_separately_once_each', async function () {
    var t = setup();
    t.flow.open('shortcut'); t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
    t.flow.open('profile'); t.fake.last('getEntranceMissionReward').opts.success({canReceiveReward: true}); await flush();
    t.flow.open('shortcut'); await flush();
    assert.strictEqual(t.store.get().coins, 50);
    assert.strictEqual(t.view().message, MissionFlow.TEXT.claimed);
  });

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'tiktok-platform-kit', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
