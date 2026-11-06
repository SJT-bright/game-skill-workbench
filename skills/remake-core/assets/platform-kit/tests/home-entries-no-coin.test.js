'use strict';
// R4O3 (补查2 第 5 组, SLS07; Saul 2026-11-04 ECON-SHORTCUT / ECON-REVISIT): HomeGrowthEntries in a game WITHOUT
// coins (PlatformConfig.normalLevelCoins 0). Before R4O3 the entries always called growthReward(), which throws
// while B is 0: every visit ended in "Could not save your reward" and a no-coin replacement (+3 energy) could not
// be given. Run on the old file: HOME_ENTRIES=<old HomeGrowthEntries.js> node tests/home-entries-no-coin.test.js
// (must fail). Node only; it does NOT prove a real phone (待真机复测).
var assert = require('assert'), path = require('path'), fs = require('fs'), vm = require('vm');
var base = process.env.KIT_DIR || path.join(__dirname, '..', 'assets', 'tiktok-platform');
var entriesPath = process.env.HOME_ENTRIES || path.join(base, 'HomeGrowthEntries.js');
var config = require(path.join(base, 'PlatformConfig.js'));
var SaveStore = require(path.join(base, 'SaveStore.js'));
var Mission = require(path.join(base, 'TikTokMissionService.js'));
function loadEntries() {
  var src = fs.readFileSync(entriesPath, 'utf8'), mod = {exports: {}};
  var req = function (p) { return require(path.join(base, p.replace(/^\.\//, '') + '.js')); };
  vm.runInThisContext('(function (module, exports, require) {' + src + '\n})')(mod, mod.exports, req);
  return mod.exports;
}
var Entries = loadEntries();
var results = [];
function flush() { return new Promise(function (r) { setTimeout(r, 0); }); }
async function test(name, run) {
  try { await run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}
function memoryStorage() {
  var map = {};
  return {getItem: function (k) { return k in map ? map[k] : null; }, setItem: function (k, v) { map[k] = String(v); }};
}
function missionSDK() {
  var calls = [], sdk = {canIUse: function () { return true; }};
  ['addShortcut', 'getShortcutMissionReward', 'startEntranceMission', 'getEntranceMissionReward'].forEach(function (m) {
    sdk[m] = function (opts) { calls.push({method: m, opts: opts}); };
  });
  return {sdk: sdk, last: function (m) { for (var i = calls.length - 1; i >= 0; i--) if (calls[i].method === m) return calls[i]; return null; }};
}
// SLS07-like save: no coins, an energy counter (the game's own field).
function setup(extra) {
  var fake = missionSDK(), states = [];
  var store = new SaveStore({energy: 5}, {storage: memoryStorage(), key: 'nc', login: false}); store.load();
  var opts = {store: store, native: true,
    missions: new Mission({getSDK: function () { return fake.sdk; }, now: function () { return 0; }, autoPoll: false, timeoutMs: 10000}),
    toast: function () {}, render: function (s) { states.push(s); }};
  Object.keys(extra || {}).forEach(function (k) { opts[k] = extra[k]; });
  var c = new Entries.Controller(opts);
  return {c: c, store: store, fake: fake, state: function () { return states[states.length - 1]; }};
}
async function visit(t, kind) {
  var nav = kind === 'shortcut' ? 'addShortcut' : 'startEntranceMission';
  var query = kind === 'shortcut' ? 'getShortcutMissionReward' : 'getEntranceMissionReward';
  t.c.press(kind);
  t.fake.last(nav).opts.success({}); await flush();
  t.c.onShow(); await flush();
  t.fake.last(query).opts.success({canReceiveReward: true}); await flush();
}
var energy = function (kind, draft) { draft.energy = (Number(draft.energy) || 0) + 3; };

(async function () {
  var keepB = config.normalLevelCoins;
  config.normalLevelCoins = 0;
  try {
    await test('no_coin_game_reward_option_pays_energy_once_each', async function () {
      var t = setup({reward: energy, rewardText: '+3 Energy'});
      assert.strictEqual(t.state().shortcut.reward, '+3 Energy', 'entry shows the replacement, not an empty label');
      await visit(t, 'shortcut');
      assert.strictEqual(t.store.get().energy, 8, 'add-to-home pays +3 energy (ECON-SHORTCUT no_coin_with_energy)');
      assert.strictEqual(t.store.isClaimed('shortcut'), true);
      assert(!/Could not save/.test(t.state().message), 'no save error: ' + t.state().message);
      await visit(t, 'profile');
      assert.strictEqual(t.store.get().energy, 11, 'revisit pays +3 energy (ECON-REVISIT)');
      t.c.onShow(); await flush();
      assert.strictEqual(t.store.get().energy, 11, 'paid once');
      assert.strictEqual(t.c.rewardSource, 'game');
    });
    await test('reward_text_per_entry_and_cocos_init_forwarding', async function () {
      var t = setup({reward: energy, rewardText: {shortcut: '+3 Energy', profile: '+3 Energy!'}});
      assert.strictEqual(t.state().profile.reward, '+3 Energy!');
      assert.strictEqual(t.state().rewardSource, 'game');
      var src = fs.readFileSync(entriesPath, 'utf8');
      assert(/reward:\s*options\.reward/.test(src), 'the Cocos component init(store, {reward}) passes the option on');
    });
    await test('neither_coins_nor_reward_pays_nothing_without_save_error_and_records_why', async function () {
      var t = setup();
      assert.strictEqual(t.state().shortcut.reward, '');
      await visit(t, 'shortcut');
      assert.strictEqual(t.store.get().energy, 5, 'nothing paid');
      assert.strictEqual(t.store.isClaimed('shortcut'), false, 'claim not spent: a later build with a reward still pays');
      assert(!/Could not save/.test(t.state().message), 'old code showed a save error: ' + t.state().message);
      assert.strictEqual(t.c.rewardSource, 'none');
      assert(/normalLevelCoins is 0/.test(t.c.rewardIssue || ''), 'controller.rewardIssue says why: ' + t.c.rewardIssue);
      assert.strictEqual(t.state().rewardIssue, t.c.rewardIssue);
    });
    await test('game_with_coins_still_pays_5B_and_ignores_reward_option', async function () {
      config.normalLevelCoins = 12;
      try {
        var t = setup({reward: energy, rewardText: '+3 Energy'});
        await visit(t, 'shortcut');
        assert.strictEqual(t.store.get().coins, 60, '5B with B = 12');
        assert.strictEqual(t.store.get().energy, 5, 'replacement not used when there are coins');
        assert.strictEqual(t.c.rewardSource, 'coins');
      } finally { config.normalLevelCoins = 0; }
    });
    await test('bad_reward_option_is_refused', function () {
      assert.throws(function () { setup({reward: 3}); }, /reward must be function/);
    });
  } finally { config.normalLevelCoins = keepB; }

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'home-entries-no-coin', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
