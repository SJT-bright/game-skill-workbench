'use strict';
// assets/tiktok-platform/HomeGrowthEntries.js (controller + the Cocos 2.4 component on a fake cc).
// Node only; it does NOT prove a real phone (待真机复测).
var assert = require('assert'), path = require('path'), fs = require('fs'), vm = require('vm');
var base = process.env.KIT_DIR || path.join(__dirname, '..', 'assets', 'tiktok-platform');
var entriesPath = process.env.HOME_ENTRIES || path.join(base, 'HomeGrowthEntries.js');
var config = require(path.join(base, 'PlatformConfig.js'));
var SaveStore = require(path.join(base, 'SaveStore.js'));
var Mission = require(path.join(base, 'TikTokMissionService.js'));
var MissionFlow = require(path.join(base, 'MissionFlow.js'));
// Load the file under test with its siblings from base (so a mutated copy still finds them).
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
  return {sdk: sdk, calls: calls, count: function (m) { return calls.filter(function (c) { return c.method === m; }).length; },
    last: function (m) { for (var i = calls.length - 1; i >= 0; i--) if (calls[i].method === m) return calls[i]; return null; }};
}
function setup(opts) {
  opts = opts || {};
  var fake = missionSDK(), toasts = [], states = [];
  var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'he', login: false}); store.load();
  var c = new Entries.Controller({store: store, native: opts.native !== undefined ? opts.native : true,
    missions: new Mission({getSDK: function () { return fake.sdk; }, now: function () { return 0; }, autoPoll: false, timeoutMs: 10000}),
    toast: function (t) { toasts.push(t); }, render: function (s) { states.push(s); }});
  return {c: c, store: store, fake: fake, toasts: toasts, state: function () { return states[states.length - 1]; }};
}

(async function () {
  var keepB = config.normalLevelCoins;
  config.normalLevelCoins = 12;
  try {
    await test('unsupported_runtime_shows_available_in_tiktok_and_keeps_entries', function () {
      var t = setup({native: false});
      assert.strictEqual(t.c.press('shortcut'), 'unsupported');
      assert.strictEqual(t.c.press('profile'), 'unsupported');
      assert.deepStrictEqual(t.toasts, ['Available in TikTok', 'Available in TikTok']);
      assert.strictEqual(t.fake.calls.length, 0, 'no fake success, no SDK call');
      assert.strictEqual(t.state().shortcut.title, 'Add to Home');
      assert.strictEqual(t.state().profile.title, 'Profile Revisit', 'entries are not hidden');
    });
    await test('icon_failure_shows_text_fallback', function () {
      var t = setup();
      assert.strictEqual(t.state().shortcut.text, '');
      t.c.iconFailed('shortcut');
      assert.strictEqual(t.state().shortcut.text, 'Add to Home\n+60');
      assert.strictEqual(t.state().profile.text, '', 'only the failed entry');
    });
    await test('reward_is_platformconfig_growth_reward', async function () {
      var t = setup();
      assert.strictEqual(t.state().shortcut.reward, '+60', '5B with B = 12');
      t.c.press('shortcut');
      t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(t.store.get().coins, 60);
      assert.strictEqual(t.state().shortcut.reward, 'Collected');
    });
    await test('repeated_taps_send_one_request_and_pay_once', async function () {
      var t = setup();
      assert.strictEqual(t.c.press('profile'), 'opened');
      assert.strictEqual(t.c.press('profile'), 'busy');
      assert.strictEqual(t.c.press('profile'), 'busy');
      assert.strictEqual(t.fake.count('getEntranceMissionReward'), 1, 'one query for three taps');
      t.fake.last('getEntranceMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(t.c.press('profile'), 'claimed');
      t.c.onShow(); await flush();
      assert.strictEqual(t.store.get().coins, 60, 'paid once');
      assert.strictEqual(t.fake.count('getEntranceMissionReward'), 1);
    });
    await test('not_eligible_then_second_tap_goes_to_tiktok', async function () {
      var t = setup();
      t.c.press('shortcut');
      t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: false}); await flush();
      assert.strictEqual(t.c.press('shortcut'), 'start');
      assert.strictEqual(t.fake.count('addShortcut'), 1);
      assert.strictEqual(t.store.get().coins, 0);
    });
    await test('unset_B_pays_nothing', async function () {
      config.normalLevelCoins = 0;
      try {
        var t = setup();
        assert.strictEqual(t.state().shortcut.reward, '');
        t.c.press('shortcut');
        t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
        assert.strictEqual(t.store.get().coins, 0);
        assert.strictEqual(t.store.isClaimed('shortcut'), false);
      } finally { config.normalLevelCoins = 12; }
    });
    await test('cocos_component_wires_both_nodes_and_falls_back_to_text', function () {
      function Node(name) { this.name = name; this.children = []; this.handlers = {}; this.active = false; this.comps = {}; this.width = 160; this.height = 80; }
      Node.prototype.on = function (ev, fn, target) { this.handlers[ev] = fn.bind(target); };
      Node.prototype.off = function (ev) { delete this.handlers[ev]; };
      Node.prototype.getComponent = function (k) { return this.comps[k.name || k] || null; };
      Node.prototype.addComponent = function (k) { var c = new k(); c.node = this; this.comps[k.name] = c; return c; };
      Node.prototype.getChildByName = function (n) { return this.children.filter(function (c) { return c.name === n; })[0] || null; };
      Node.prototype.setContentSize = function () {};
      Object.defineProperty(Node.prototype, 'parent', {set: function (p) { p.children.push(this); }});
      function Label() { this.string = ''; } function Sprite() {} function Button() { this.interactable = true; }
      var fakeCC = {Node: Node, Label: Label, Sprite: Sprite, Button: Button, Component: function () {},
        Color: {WHITE: {}}, game: {EVENT_SHOW: 'show', on: function () {}, off: function () {}}, error: function () {}};
      Label.HorizontalAlign = {CENTER: 1}; Label.Overflow = {SHRINK: 2}; Node.EventType = {TOUCH_END: 'touchend'};
      fakeCC.Class = function (def) { function C() {} Object.keys(def).forEach(function (k) { if (k !== 'properties' && k !== 'statics' && k !== 'extends') C.prototype[k] = def[k]; }); C.statics = def.statics; return C; };
      global.cc = fakeCC;
      try {
        var Comp = loadEntries();
        var comp = new Comp(); comp.scheduleOnce = function () {};
        comp.shortcutNode = new Node('a'); comp.profileNode = new Node('b');
        comp.shortcutNode.comps.Button = new Button();
        var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'cc', login: false}); store.load();
        var ctrl = comp.init(store, {native: false});
        assert(comp.shortcutNode.active && comp.profileNode.active, 'both entries shown');
        var label = comp.shortcutNode.getChildByName('HomeEntryText').getComponent(Label);
        assert.strictEqual(label.string, 'Add to Home\n+60', 'no sprite -> text fallback');
        assert.strictEqual(typeof comp.profileNode.handlers.touchend, 'function');
        comp.profileNode.handlers.touchend();
        assert.strictEqual(ctrl.flow.native, false);
        comp.onDestroy();
      } finally { delete global.cc; }
    });
  } finally { config.normalLevelCoins = keepB; }

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'home-entries', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
