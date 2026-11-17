'use strict';
// Targeted policy tests use the same platform-kit Node runtime; no real network or player save writes.
var assert = require('assert');
var fs = require('fs'), path = require('path'), vm = require('vm');
var Policy = require('../assets/tiktok-platform/AdDisplayPolicy');
var results = [];
var reported = false;
process.once('beforeExit', function () { if (!reported) { console.error('ad-display-policy suite incomplete: pending asynchronous case'); process.exitCode = 1; } });
function config(overrides) {
  var c = {gameId: 'policy-test', appId: 'test-app', adDisplay: {enabled: true, channel: 'production',
    remoteUrl: 'https://config.example.test/game.json', refreshAfterMs: 60000, requestTimeoutMs: 1500}};
  Object.keys(overrides || {}).forEach(function (key) { c.adDisplay[key] = overrides[key]; });
  return c;
}
function storage() {
  var s = {data: {'player-save': '{"coins":19,"claimed":true}'}, writes: [], failWrite: false, silentWrite: false,
    getItem: function (key) { return Object.prototype.hasOwnProperty.call(s.data, key) ? s.data[key] : null; },
    setItem: function (key, text) { if (s.failWrite) throw new Error('disk full'); s.writes.push(key); if (!s.silentWrite) s.data[key] = text; }};
  return s;
}
async function withGlobals(changes, fn) {
  var saved = {};
  Object.keys(changes).forEach(function (key) {
    saved[key] = Object.getOwnPropertyDescriptor(global, key);
    Object.defineProperty(global, key, changes[key]);
  });
  try { await fn(); }
  finally {
    Object.keys(changes).forEach(function (key) {
      if (saved[key]) Object.defineProperty(global, key, saved[key]); else delete global[key];
    });
  }
}
function globalValue(value) { return {configurable: true, writable: true, value: value}; }
function throwingGetter() { return {configurable: true, get: function () { throw new Error('storage access denied'); }}; }
function payload(revision, enabled) {
  return {schemaVersion: 1, gameId: 'policy-test', appId: 'test-app', channel: 'production', revision: revision, ads: {enabled: enabled}};
}
function world(c, s) {
  var w = {time: 0, requests: [], timers: [], aborted: 0, store: s || storage()};
  w.options = {storage: w.store, bindLifecycle: false, now: function () { return w.time; },
    request: function (o) { w.requests.push(o); return {abort: function () { w.aborted++; o.fail(); }}; },
    setTimeout: function (fn, ms) { var t = {fn: fn, ms: ms, active: true}; w.timers.push(t); return t; },
    clearTimeout: function (t) { t.active = false; }};
  w.p = Policy.create(c || config(), w.options);
  w.next = function () { w.time += 60000; return w.p.refresh(); };
  w.respond = function (value, status) { w.requests[w.requests.length - 1].success({statusCode: status === undefined ? 200 : status, data: value}); };
  return w;
}
function adSDK() {
  var w = {creates: 0, shows: 0, ads: []};
  w.sdk = {canIUse: function () { return true; }, createRewardedVideoAd: function () {
    w.creates++;
    var ad = {close: null, savedClose: null, error: null,
      onClose: function (fn) { ad.close = ad.savedClose = fn; }, onError: function (fn) { ad.error = fn; },
      offClose: function (fn) { if (ad.close === fn) ad.close = null; },
      offError: function (fn) { if (ad.error === fn) ad.error = null; },
      show: function () { w.shows++; return Promise.resolve(); }};
    w.ads.push(ad); return ad;
  }};
  return w;
}
async function flush() { for (var i = 0; i < 6; i++) await Promise.resolve(); }
async function accept(w, revision, enabled) { var done = w.next(); w.respond(payload(revision, enabled)); await done; }
async function test(name, fn) {
  try { await fn(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e.stack || e)}); }
}
(async function () {
  await test('missing_optional_block_and_missing_remote_default_ON_without_network', async function () {
    var w = world({gameId: 'legacy-game', appId: 'test-app'});
    assert.strictEqual(w.p.isEnabled(), true); await w.p.refresh();
    assert.strictEqual(w.requests.length, 0); assert.strictEqual(w.timers.length, 0); assert.strictEqual(w.store.writes.length, 0);
  });
  await test('local_OFF_is_effective_without_remote_and_cannot_be_overridden_by_remote_ON', async function () {
    var w = world(config({enabled: false})); assert.strictEqual(w.p.isEnabled(), false);
    await accept(w, 1, true); assert.strictEqual(w.p.isEnabled(), false);
    var local = world(config({enabled: false, remoteUrl: ''})); await local.p.refresh();
    assert.strictEqual(local.p.isEnabled(), false); assert.strictEqual(local.requests.length, 0);
  });
  await test('remote_OFF_then_newer_ON_restore_same_policy', async function () {
    var w = world(), calls = 0;
    w.p.subscribe(function () { calls++; });
    await accept(w, 2, false); assert.strictEqual(w.p.isEnabled(), false);
    assert.strictEqual(w.p.state().revision, 2);
    await accept(w, 3, true); assert.strictEqual(w.p.isEnabled(), true); assert.strictEqual(calls, 2);
  });
  await test('synchronous_cache_initialization_preserves_OFF_and_full_revision_before_first_read', async function () {
    var w = world(); await accept(w, 12, false);
    var cached = JSON.parse(w.store.data[w.p.cacheKey]);
    assert.strictEqual(cached.revision, 12); assert.strictEqual(cached.gameId, 'policy-test');
    assert.strictEqual(cached.channel, 'production'); assert.strictEqual(cached.ads.enabled, false);
    var restart = world(config(), w.store);
    assert.strictEqual(restart.p.isEnabled(), false); assert.strictEqual(restart.p.state().revision, 12);
    assert.strictEqual(restart.requests.length, 0);
    await accept(restart, 11, true); assert.strictEqual(restart.p.isEnabled(), false);
  });
  await test('Cocos3_without_global_cc_persists_and_restores_OFF_using_window_localStorage', async function () {
    var store = storage();
    await withGlobals({cc: globalValue(undefined), window: globalValue({localStorage: store}), localStorage: globalValue(null)}, async function () {
      var w = world(); delete w.options.storage;
      w.p = Policy.create(config(), w.options);
      await accept(w, 4, false);
      assert.strictEqual(w.p.state().cacheWriteFailed, false);
      var restarted = Policy.create(config(), {bindLifecycle: false});
      assert.strictEqual(restarted.isEnabled(), false); assert.strictEqual(restarted.state().revision, 4);
      assert.strictEqual(store.data['player-save'], '{"coins":19,"claimed":true}');
    });
  });
  await test('storage_getter_failures_fall_through_to_root_storage_or_safe_default', async function () {
    var store = storage(), denied = {};
    Object.defineProperty(denied, 'localStorage', throwingGetter());
    await withGlobals({cc: throwingGetter(), window: globalValue(denied), localStorage: globalValue(store)}, async function () {
      var w = world(); delete w.options.storage; w.p = Policy.create(config(), w.options);
      await accept(w, 5, false); assert.strictEqual(w.p.state().cacheWriteFailed, false);
      var restarted = Policy.create(config(), {bindLifecycle: false});
      assert.strictEqual(restarted.isEnabled(), false); assert.strictEqual(restarted.state().revision, 5);
    });
    await withGlobals({cc: throwingGetter(), window: globalValue(denied), localStorage: throwingGetter()}, async function () {
      var p = Policy.create(config({remoteUrl: ''}), {bindLifecycle: false});
      assert.strictEqual(p.isEnabled(), true); await p.refresh(); assert.strictEqual(p.isEnabled(), true);
    });
  });
  await test('network_failure_or_expired_refresh_does_not_reenable_cached_OFF', async function () {
    var w = world(); await accept(w, 2, false);
    var done = w.next(); w.requests[1].fail({errMsg: 'offline'}); await done;
    assert.strictEqual(w.p.isEnabled(), false); assert.strictEqual(w.p.state().revision, 2);
    var count = w.requests.length; w.time += 59999; await w.p.refresh(); assert.strictEqual(w.requests.length, count);
    w.time += 1; done = w.p.refresh(); assert.strictEqual(w.requests.length, count + 1); w.requests[count].fail(); await done;
    assert.strictEqual(w.p.isEnabled(), false);
  });
  await test('invalid_boolean_revision_identity_channel_schema_and_http_do_not_replace_accepted_OFF', async function () {
    var values = [payload(3, 'false'), payload(3, 0), payload(-1, true), payload(1.2, true), payload(Infinity, true),
      payload(9007199254740992, true), payload('3', true), {}, null, [], '{bad json'];
    var v = payload(3, true); delete v.ads.enabled; values.push(v);
    v = payload(3, true); v.gameId = 'another-game'; values.push(v);
    v = payload(3, true); v.appId = 'another-app'; values.push(v);
    v = payload(3, true); v.channel = 'test'; values.push(v);
    v = payload(3, true); v.schemaVersion = 2; values.push(v);
    var w = world(); await accept(w, 2, false);
    for (var i = 0; i < values.length; i++) {
      var done = w.next(); w.respond(values[i]); await done;
      assert.strictEqual(w.p.isEnabled(), false, 'bad payload index ' + i); assert.strictEqual(w.p.state().revision, 2);
    }
    done = w.next(); w.respond(payload(3, true), 500); await done;
    assert.strictEqual(w.p.isEnabled(), false); assert.strictEqual(w.p.state().revision, 2);
  });
  await test('old_revision_and_same_revision_conflict_are_rejected_and_same_record_is_quiet', async function () {
    var w = world(), notices = 0; w.p.subscribe(function () { notices++; });
    await accept(w, 10, false); var writes = w.store.writes.length;
    await accept(w, 9, true); await accept(w, 10, true); await accept(w, 10, false);
    assert.strictEqual(w.p.isEnabled(), false); assert.strictEqual(w.p.state().revision, 10);
    assert.strictEqual(w.store.writes.length, writes); assert.strictEqual(notices, 1);
    await accept(w, 11, true); assert.strictEqual(w.p.isEnabled(), true); assert.strictEqual(notices, 2);
  });
  await test('inflight_refresh_is_shared_and_failed_attempts_are_throttled', async function () {
    var w = world(), a = w.p.refresh(), b = w.p.refresh();
    assert.strictEqual(a, b); assert.strictEqual(w.requests.length, 1); w.requests[0].fail(); await a;
    await w.p.refresh(); assert.strictEqual(w.requests.length, 1);
    w.time = 60000; var c = w.p.refresh(); assert.strictEqual(w.requests.length, 2); w.requests[1].fail(); await c;
  });
  await test('timeout_releases_only_its_refresh_and_late_response_never_overwrites_newer_state', async function () {
    var w = world(), first = w.p.refresh(), old = w.requests[0];
    assert.strictEqual(old.timeout, 1500);
    assert.strictEqual(w.timers[0].ms, 1500); w.timers[0].fn(); await first;
    assert.strictEqual(w.p.state().lastOutcome, 'timeout'); assert.strictEqual(w.aborted, 1);
    w.time = 60000; var second = w.p.refresh();
    old.success({statusCode: 200, data: payload(100, true)});
    assert.strictEqual(w.p.refresh(), second); w.respond(payload(2, false)); await second;
    old.success({statusCode: 200, data: payload(101, true)});
    assert.strictEqual(w.p.isEnabled(), false); assert.strictEqual(w.p.state().revision, 2);
  });
  await test('exceptional_subscriber_is_isolated_and_unsubscribe_is_idempotent', async function () {
    var w = world(), notices = 0;
    w.p.subscribe(function () { throw new Error('destroyed page'); });
    var off = w.p.subscribe(function (state) { notices++; state.enabled = true; });
    await accept(w, 1, false); assert.strictEqual(notices, 1); assert.strictEqual(w.p.isEnabled(), false);
    off(); off(); await accept(w, 2, true); assert.strictEqual(notices, 1); assert.strictEqual(w.p.isEnabled(), true);
  });
  await test('cache_write_throw_or_silent_failure_preserves_current_memory_and_reports_limit', async function () {
    for (var i = 0; i < 2; i++) {
      var w = world(); w.store[i ? 'silentWrite' : 'failWrite'] = true;
      await accept(w, 3, false); assert.strictEqual(w.p.isEnabled(), false); assert.strictEqual(w.p.state().cacheWriteFailed, true);
      var restarted = world(config(), w.store); assert.strictEqual(restarted.p.isEnabled(), true);
    }
  });
  await test('bad_cache_is_ignored_and_not_written_into_player_save', async function () {
    var w = world(), key = w.p.cacheKey; w.store.data[key] = '{broken';
    var restarted = world(config(), w.store); assert.strictEqual(restarted.p.isEnabled(), true);
    assert.strictEqual(restarted.p.state().lastOutcome, 'invalid_cache');
    await accept(restarted, 1, false);
    assert.strictEqual(w.store.data['player-save'], '{"coins":19,"claimed":true}');
    assert.deepStrictEqual(w.store.writes, [key]);
  });
  await test('cache_keys_and_payload_checks_isolate_game_app_channel_and_source', async function () {
    var first = world(); await accept(first, 2, false);
    var variants = [];
    var c = config(); c.gameId = 'another-game'; variants.push(c);
    c = config(); c.appId = 'another-app'; variants.push(c);
    variants.push(config({channel: 'staging'})); variants.push(config({remoteUrl: 'https://config.example.test/other.json'}));
    for (var i = 0; i < variants.length; i++) {
      var other = world(variants[i], first.store); assert.notStrictEqual(other.p.cacheKey, first.p.cacheKey);
      first.store.data[other.p.cacheKey] = first.store.data[first.p.cacheKey];
      var mismatched = world(variants[i], first.store); assert.strictEqual(mismatched.p.isEnabled(), true);
    }
    assert.strictEqual(first.p.isEnabled(), false);
  });
  await test('get_publishes_one_initialized_instance_without_request_and_rejects_overwrite', async function () {
    var root = {}, w = world(), opts = Object.assign({}, w.options, {root: root});
    var first = Policy.get(config(), opts), second = Policy.get(config(), opts);
    assert.strictEqual(first, second); assert.strictEqual(Policy.current(root), first);
    assert.strictEqual(root[Policy.ROOT_KEY].instance, first); assert.strictEqual(w.requests.length, 0);
    var different = config(); different.gameId = 'different';
    assert.throws(function () { Policy.get(different, opts); }, /identity_conflict/);
    assert.throws(function () { Policy.get(config({enabled: false}), opts); }, /config_conflict/);
    assert.strictEqual(Policy.current(root), first);
    var incompatible = {}; incompatible[Policy.ROOT_KEY] = {version: 2, instance: first, identity: first.identity};
    assert.strictEqual(Policy.current(incompatible), null);
    assert.throws(function () { Policy.get(config(), Object.assign({}, opts, {root: incompatible})); }, /identity_conflict/);
  });
  await test('foreground_listener_is_bound_once_even_when_entries_are_hidden', async function () {
    var root = {}, listeners = [], w = world(), sdk = {onShow: function (fn) { listeners.push(fn); }};
    var opts = Object.assign({}, w.options, {root: root, bindLifecycle: true, getSDK: function () { return sdk; }});
    var p = Policy.get(config(), opts); Policy.get(config(), opts);
    assert.strictEqual(listeners.length, 1); assert.strictEqual(w.requests.length, 0);
    listeners[0](); w.respond(payload(1, false)); await p.refresh(); assert.strictEqual(p.isEnabled(), false);
    w.time = 60000; listeners[0](); w.respond(payload(2, true)); await p.refresh(); assert.strictEqual(p.isEnabled(), true);
    assert.strictEqual(listeners.length, 1);
  });
  await test('SDK_receiver_and_sync_success_and_Promise_transport_are_supported', async function () {
    var sdk = {request: function (o) { assert.strictEqual(this, sdk); o.success({statusCode: 200, data: JSON.stringify(payload(1, false))}); return {}; }};
    var p = Policy.create(config(), {storage: storage(), bindLifecycle: false, getSDK: function () { return sdk; }});
    await p.refresh(); assert.strictEqual(p.isEnabled(), false);
    p = Policy.create(config(), {storage: storage(), bindLifecycle: false, request: function () { return Promise.resolve({statusCode: 200, data: payload(2, false)}); }});
    await p.refresh(); assert.strictEqual(p.isEnabled(), false);
  });
  await test('request_throw_and_missing_transport_leave_default_ON_and_release_refresh', async function () {
    var w = world(); w.options.request = function () { throw new Error('adapter failed'); };
    var p = Policy.create(config(), w.options); await p.refresh(); assert.strictEqual(p.isEnabled(), true);
    assert.strictEqual(p.state().lastOutcome, 'network_error'); assert.strictEqual(w.timers[0].active, false);
    p = Policy.create(config(), {bindLifecycle: false, storage: null, getSDK: function () { return null; }});
    await p.refresh(); assert.strictEqual(p.isEnabled(), true); assert.strictEqual(p.state().lastOutcome, 'request_unavailable');
  });
  await test('clock_rollback_recovers_throttle_without_revision_rollback', async function () {
    var w = world(); await accept(w, 2, false);
    w.time = -100; var done = w.p.refresh(); assert.strictEqual(w.requests.length, 2);
    w.respond(payload(1, true)); await done; assert.strictEqual(w.p.isEnabled(), false);
    await w.p.refresh(); assert.strictEqual(w.requests.length, 2);
  });
  await test('invalid_local_configuration_fails_explicitly_instead_of_silent_ON', async function () {
    assert.throws(function () { Policy.create(config({enabled: 'false'})); }, /invalid_enabled/);
    assert.throws(function () { Policy.create(config({remoteUrl: 'http://config.example.test/a'})); }, /requires_https/);
    assert.throws(function () { Policy.create(config({remoteUrl: 1})); }, /invalid_remote_url/);
    assert.throws(function () { Policy.create(config({channel: ''})); }, /invalid_identity/);
    var c = config(); c.gameId = 'change-me'; assert.throws(function () { Policy.create(c); }, /unconfigured_identity/);
  });
  await test('real_service_policy_and_SaveStore_close_restore_preserve_wallet_and_grant_deduplication', async function () {
    var RewardedService = require('../assets/tiktok-platform/RewardedService');
    var SaveStore = require('../assets/tiktok-platform/SaveStore');
    var w = world(), native = adSDK(), store = new SaveStore({coins: 19}, {storage: w.store, key: 'integration:save', login: false, schema: false});
    assert.strictEqual(store.load().ok, true);
    assert.strictEqual(store.grant({id: 'preexisting-grant', add: {coins: 1}}).ok, true);
    var service = new RewardedService({adDisplayPolicy: w.p, getSDK: function () { return native.sdk; }, now: function () { return w.time; }, autoPoll: false});
    try {
      assert.strictEqual(w.requests.length, 1, 'service initializes one background refresh');
      w.respond(payload(1, true)); await w.p.refresh();
      var deliveries = 0;
      function request(id) {
        return service.request({placementKey: 'double_coins', ownerId: 'result'}).then(function (r) {
          if (r.rewarded) { deliveries++; assert.strictEqual(store.grant({id: id, add: {coins: 10}}).ok, true); }
          return r;
        });
      }
      var on = request('ad:one'); await flush();
      native.ads[0].savedClose({isEnded: true}); native.ads[0].savedClose({isEnded: true});
      assert.strictEqual((await on).status, 'completed'); assert.strictEqual(deliveries, 1); assert.strictEqual(store.get().coins, 30);
      var beforeWallet = w.store.getItem(store.key), beforeWrites = w.store.writes.length;
      await accept(w, 2, false);
      assert.strictEqual(w.store.getItem(store.key), beforeWallet);
      assert.deepStrictEqual(w.store.writes.slice(beforeWrites), [w.p.cacheKey]);
      var beforeCalls = [native.creates, native.shows], off = await request('ad:blocked');
      assert.strictEqual(off.status, 'disabled'); assert.strictEqual(off.rewarded, false);
      assert.deepStrictEqual([native.creates, native.shows], beforeCalls);
      assert.strictEqual(w.store.getItem(store.key), beforeWallet); assert.strictEqual(deliveries, 1);
      await accept(w, 3, true);
      assert.strictEqual(w.store.getItem(store.key), beforeWallet);
      var restored = request('ad:two'); await flush(); native.ads[1].savedClose({isEnded: true});
      assert.strictEqual((await restored).status, 'completed'); assert.strictEqual(deliveries, 2); assert.strictEqual(store.get().coins, 40);
      var afterWallet = w.store.getItem(store.key), writes = w.store.writes.length;
      assert.strictEqual(store.grant({id: 'ad:one', add: {coins: 10}}).already, true);
      assert.strictEqual(store.grant({id: 'preexisting-grant', add: {coins: 1}}).already, true);
      assert.strictEqual(w.store.writes.length, writes); assert.strictEqual(w.store.getItem(store.key), afterWallet);
      assert.strictEqual(service.pending, null); assert.strictEqual(service.isNativeBusy(), false);
      var reload = new SaveStore({coins: 0}, {storage: w.store, key: store.key, login: false, schema: false});
      assert.strictEqual(reload.load().ok, true); assert.strictEqual(reload.get().coins, 40);
      assert.strictEqual(reload.grant({id: 'ad:two', add: {coins: 10}}).already, true);
    } finally { service.dispose(); }
  });
  await test('real_service_cold_start_cached_OFF_blocks_first_request_before_network_returns', async function () {
    var RewardedService = require('../assets/tiktok-platform/RewardedService');
    var SaveStore = require('../assets/tiktok-platform/SaveStore');
    var old = world(), store = new SaveStore({coins: 25}, {storage: old.store, key: 'cold:save', login: false, schema: false});
    store.load(); assert.strictEqual(store.grant({id: 'earned-before-restart', add: {coins: 7}}).ok, true);
    await accept(old, 2, false);
    var wallet = old.store.getItem(store.key), restarted = world(config(), old.store), native = adSDK();
    assert.strictEqual(restarted.p.isEnabled(), false); assert.strictEqual(restarted.requests.length, 0);
    var service = new RewardedService({adDisplayPolicy: restarted.p, getSDK: function () { return native.sdk; }, autoPoll: false});
    try {
      assert.strictEqual(restarted.requests.length, 1, 'refresh pending, cache already initialized');
      var first = await service.request({placementKey: 'double_coins', ownerId: 'result'});
      assert.strictEqual(first.status, 'disabled'); assert.strictEqual(first.rewarded, false);
      assert.deepStrictEqual([native.creates, native.shows], [0, 0]);
      assert.strictEqual(old.store.getItem(store.key), wallet);
      var reloaded = new SaveStore({coins: 0}, {storage: old.store, key: store.key, login: false, schema: false});
      assert.strictEqual(reloaded.load().ok, true); assert.strictEqual(reloaded.get().coins, 32);
      assert.strictEqual(reloaded.grant({id: 'earned-before-restart', add: {coins: 7}}).already, true);
      restarted.respond(payload(3, true)); await restarted.p.refresh();
      var next = service.request({placementKey: 'double_coins', ownerId: 'result'}); await flush();
      native.ads[0].savedClose({isEnded: true}); assert.strictEqual((await next).rewarded, true);
      assert.deepStrictEqual([native.creates, native.shows], [1, 1]);
      assert.strictEqual(old.store.getItem(store.key), wallet, 'ad service and policy never grant into the save by themselves');
    } finally { service.dispose(); }
  });
  await test('real_remote_OFF_after_show_preserves_completion_and_SaveStore_grants_once', async function () {
    var RewardedService = require('../assets/tiktok-platform/RewardedService');
    var SaveStore = require('../assets/tiktok-platform/SaveStore');
    var w = world(), native = adSDK(), store = new SaveStore({coins: 10}, {storage: w.store, key: 'playing:save', login: false, schema: false});
    store.load();
    var service = new RewardedService({adDisplayPolicy: w.p, getSDK: function () { return native.sdk; }, autoPoll: false});
    try {
      var grants = 0;
      var done = service.request({placementKey: 'double_coins', ownerId: 'result'}).then(function (r) {
        if (r.rewarded) { grants++; return store.grant({id: 'ad:already-showing', add: {coins: 5}}); }
        throw new Error('existing show must retain its legal completed result');
      });
      assert.deepStrictEqual([native.creates, native.shows], [1, 1]);
      w.respond(payload(1, false)); await w.p.refresh();
      assert.strictEqual(service.isEnabled(), false);
      native.ads[0].savedClose({isEnded: true}); native.ads[0].savedClose({isEnded: true});
      assert.strictEqual((await done).ok, true); assert.strictEqual(grants, 1); assert.strictEqual(store.get().coins, 15);
      assert.strictEqual(store.grant({id: 'ad:already-showing', add: {coins: 5}}).already, true);
      var blocked = await service.request({placementKey: 'double_coins', ownerId: 'result'});
      assert.strictEqual(blocked.status, 'disabled'); assert.deepStrictEqual([native.creates, native.shows], [1, 1]);
    } finally { service.dispose(); }
  });
  await test('default_tt_and_TTMinis_hosts_refresh_when_canIUse_is_undefined_for_general_APIs', async function () {
    for (var i = 0; i < 2; i++) {
      var native = adSDK(), requests = [], listeners = [], timers = [], support = true, store = storage();
      native.sdk.canIUse = function (method) { return method === 'createRewardedVideoAd' ? support : undefined; };
      native.sdk.request = function (options) { assert.strictEqual(this, native.sdk); requests.push(options); return {abort: function () {}}; };
      native.sdk.onShow = function (fn) { listeners.push(fn); };
      native.sdk.offShow = function (fn) { var at = listeners.indexOf(fn); if (at >= 0) listeners.splice(at, 1); };
      var sandbox = {console: console, cc: {sys: {localStorage: store}}, __time: 0,
        setTimeout: function (fn, ms) { var t = {fn: fn, ms: ms, active: true}; timers.push(t); return t; },
        clearTimeout: function (timer) { timer.active = false; }, clearInterval: function () {}};
      if (i) sandbox.TTMinis = {game: native.sdk}; else sandbox.tt = native.sdk;
      var context = vm.createContext(sandbox), cache = {}, base = path.resolve(__dirname, '../assets/tiktok-platform');
      vm.runInContext('Date.now = function () { return __time; };', context);
      function load(file) {
        file = path.resolve(file); if (!/\.js$/.test(file)) file += '.js';
        if (cache[file]) return cache[file].exports;
        var module = {exports: {}}; cache[file] = module;
        var factory = vm.runInContext('(function(require,module,exports){\n' + fs.readFileSync(file, 'utf8') + '\n})', context, {filename: file});
        factory(function (name) { assert.strictEqual(name.charAt(0), '.'); return load(path.resolve(path.dirname(file), name)); }, module, module.exports);
        return module.exports;
      }
      var isolatedConfig = load(path.join(base, 'PlatformConfig'));
      isolatedConfig.gameId = 'policy-test'; isolatedConfig.appId = 'test-app'; isolatedConfig.adDisplay = config().adDisplay;
      var Service = load(path.join(base, 'RewardedService')), service = new Service({autoPoll: false});
      try {
        assert.strictEqual(service.policyError, null);
        assert.strictEqual(requests.length, 1, 'general request API exists even though canIUse(request) is undefined');
        assert.strictEqual(listeners.length, 1, 'policy foreground listener binds without a canIUse(onShow) gate');
        assert.strictEqual(native.sdk.canIUse('request'), undefined);
        var original = service.request({placementKey: 'double_coins', ownerId: 'result'}); await flush();
        native.ads[0].savedClose({isEnded: true}); assert.strictEqual((await original).status, 'completed');
        requests[0].success({statusCode: 200, data: payload(1, false)}); await service.refreshPolicy();
        assert.strictEqual(service.isEnabled(), false);
        var blocked = await service.request({placementKey: 'double_coins', ownerId: 'result'});
        assert.strictEqual(blocked.status, 'disabled'); assert.strictEqual(blocked.rewarded, false);
        assert.deepStrictEqual([native.creates, native.shows], [1, 1]);
        sandbox.__time = 60000; listeners[0]();
        assert.strictEqual(requests.length, 2, 'default foreground route refreshes an OFF policy');
        requests[1].success({statusCode: 200, data: payload(2, true)}); await service.refreshPolicy();
        assert.strictEqual(service.isEnabled(), true);
        support = false;
        assert.strictEqual((await service.request({placementKey: 'double_coins'})).status, 'unsupported');
        support = undefined;
        assert.strictEqual((await service.request({placementKey: 'double_coins'})).status, 'unsupported');
        assert.deepStrictEqual([native.creates, native.shows], [1, 1], 'original strict advertisement capability check remains intact');
        assert.strictEqual(listeners.length, 1); assert.strictEqual(timers.filter(function (t) { return t.active; }).length, 0);
      } finally { service.dispose(); }
    }
  });
  var failed = results.filter(function (r) { return r.status === 'failed'; });
  reported = true;
  console.log(JSON.stringify({suite: 'ad-display-policy', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
})();
