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
  var fake = missionSDK(), states = [];
  var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'he', login: false}); store.load();
  var c = new Entries.Controller({store: store, native: opts.native !== undefined ? opts.native : true,
    missions: new Mission({getSDK: function () { return fake.sdk; }, now: function () { return 0; }, autoPoll: false, timeoutMs: 10000}),
    render: function (s) { states.push(s); }});
  return {c: c, store: store, fake: fake, states: states, state: function () { return states[states.length - 1]; }};
}

(async function () {
  var keepB = config.normalLevelCoins;
  config.normalLevelCoins = 12;
  try {
    await test('studio_without_sdk_keeps_both_entries_silent', function () {
      var t = setup({native: false});
      assert.strictEqual(t.c.press('shortcut'), 'unsupported');
      assert.strictEqual(t.c.press('profile'), 'unsupported');
      assert(t.states.every(function (state) { return state.message === ''; }));
      assert.strictEqual(t.fake.calls.length, 0, 'no fake success, no SDK call');
      assert.strictEqual(t.state().shortcut.title, 'Add to Home');
      assert.strictEqual(t.state().profile.title, 'Profile Revisit', 'entries are not hidden');
    });
    await test('icon_failure_shows_text_fallback', function () {
      var t = setup();
      assert.strictEqual(t.state().shortcut.text, '');
      t.c.iconFailed('shortcut');
      assert.strictEqual(t.state().shortcut.text, 'Add to Home', '11.17.15: title only, no reward words');
      assert.strictEqual(t.state().profile.text, '', 'only the failed entry');
    });
    await test('reward_is_platformconfig_growth_reward', async function () {
      var t = setup();
      assert.strictEqual(t.state().shortcut.rewardText, '+60', '5B with B = 12');
      assert.strictEqual(t.state().shortcut.reward, '', '11.17.15: no reward words drawn on the entry');
      t.c.press('shortcut');
      t.fake.last('addShortcut').opts.success({}); await flush();
      t.c.onShow({scene: 'desktop_shortcut'}); await flush();                                       // back from the new icon
      t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(t.store.get().coins, 60);
      assert.strictEqual(t.state().shortcut.claimed, true);
      assert.strictEqual(t.state().shortcut.reward, '', '11.17.15: claimed state is the game badge, no Collected text');
    });
    // 简化.11.3 (Saul 2026-11-02): until 简化.11.2 the first tap only asked for the reward and a second tap was
    // needed to navigate; on the phone (77~86, Mosslight v20) the entries looked dead.
    await test('both_home_entries_dispatch_before_rendering_and_show_no_hint', async function () {
      var methods = {shortcut: 'addShortcut', profile: 'startEntranceMission'};
      for (var kind of Object.keys(methods)) {
        var t = setup(), method = methods[kind];
        var renderCount = t.states.length;
        var original = t.fake.sdk[method], atDispatch = null;
        t.fake.sdk[method] = function (opts) {
          atDispatch = t.states.length;
          original(opts);
        };
        assert.strictEqual(t.c.press(kind), 'start');
        assert.strictEqual(atDispatch, renderCount, 'the SDK is called before a view renders');
        assert.deepStrictEqual(t.fake.calls.map(function (call) { return call.method; }), [method]);
        assert.strictEqual(t.c.flow.view().open, false, 'no in-game panel');
        t.fake.last(method).opts.success({});
        await flush();
        assert(t.states.every(function (state) { return state.message === ''; }), 'no transient or success guidance');
        assert.strictEqual(t.store.get().coins, 0, 'navigation success never pays');
      }
    });
    await test('repeated_taps_send_one_request_and_pay_once', async function () {
      var t = setup();
      assert.strictEqual(t.c.press('profile'), 'start');
      assert.strictEqual(t.c.press('profile'), 'busy');
      assert.strictEqual(t.c.press('profile'), 'busy');
      assert.strictEqual(t.fake.count('startEntranceMission'), 1, 'one jump for three taps');
      t.fake.last('startEntranceMission').opts.success({}); await flush();
      t.c.onShow({scene: 'center'}); await flush();
      t.fake.last('getEntranceMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(t.store.get().coins, 60);
      t.c.onShow({scene: 'center'}); await flush();
      assert.strictEqual(t.store.get().coins, 60, 'paid once');
      assert.strictEqual(t.fake.count('getEntranceMissionReward'), 1, 'no query once collected');
    });
    await test('collected_entry_still_opens_tiktok_and_pays_nothing', async function () {
      var t = setup();
      t.c.press('shortcut');
      t.fake.last('addShortcut').opts.success({}); await flush();
      t.c.onShow({scene: 'desktop_shortcut'}); await flush();
      t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: true}); await flush();
      assert.strictEqual(t.c.press('shortcut'), 'start');
      assert.strictEqual(t.fake.count('addShortcut'), 2, 'the entry keeps working');
      t.fake.last('addShortcut').opts.success({}); await flush();
      t.c.onShow({scene: 'desktop_shortcut'}); await flush();
      assert.strictEqual(t.store.get().coins, 60, 'no second reward');
    });
    await test('not_eligible_after_return_then_tap_goes_again', async function () {
      var t = setup();
      t.c.press('shortcut');
      t.fake.last('addShortcut').opts.success({}); await flush();
      t.c.onShow({scene: 'desktop_shortcut'}); await flush();
      t.fake.last('getShortcutMissionReward').opts.success({canReceiveReward: false}); await flush();
      assert.strictEqual(t.store.get().coins, 0);
      assert.strictEqual(t.fake.count('addShortcut'), 1, 'the check after returning does not jump by itself');
      assert.strictEqual(t.c.press('shortcut'), 'start');
      assert.strictEqual(t.fake.count('addShortcut'), 2, 'one more tap goes again');
    });
    await test('navigation_failure_is_silent_retryable_and_keeps_diagnostics', async function () {
      var t = setup();
      t.c.press('profile');
      t.fake.last('startEntranceMission').opts.fail({errMsg: 'startEntranceMission:fail not support', errCode: 10002}); await flush();
      assert.strictEqual(t.c.flow.phase, 'idle', 'a failed jump frees the entry');
      assert(t.states.every(function (state) { return state.message === ''; }));
      assert.strictEqual(t.store.get().coins, 0, 'a failed jump pays nothing');
      assert.strictEqual(t.c.press('profile'), 'start', 'the next tap tries again');
      assert.strictEqual(t.fake.count('startEntranceMission'), 2);
      var seen = null;
      var m = new Mission({getSDK: function () { return {startEntranceMission: function (o) { o.fail({errMsg: 'x:fail not support', errCode: 10002}); }}; }, autoPoll: false});
      seen = await m.navigate('profile');
      assert.strictEqual(seen.errorCode, 10002);
      assert.strictEqual(seen.errMsg, 'x:fail not support');
      assert.strictEqual(seen.api, 'startEntranceMission');
      assert.strictEqual(seen.message, '');
    });
    await test('canIUse_undefined_or_missing_still_calls_the_platform', async function () {
      var Missions = require(path.join(base, 'TikTokMissionService.js'));
      var calls = [];
      var undef = {canIUse: function () { return undefined; }, startEntranceMission: function () { calls.push('undef'); }};
      var none = {addShortcut: function () { calls.push('none'); }};
      var no = {canIUse: function () { return false; }, addShortcut: function () { calls.push('false'); }};
      var throws = {canIUse: function () { throw new Error('x'); }, addShortcut: function () { calls.push('throws'); }};
      var r1 = new Missions({getSDK: function () { return undef; }, autoPoll: false}).navigate('profile');
      var r2 = new Missions({getSDK: function () { return none; }, autoPoll: false}).navigate('shortcut');
      var r3 = await new Missions({getSDK: function () { return no; }, autoPoll: false}).navigate('shortcut');
      var r4 = await new Missions({getSDK: function () { return throws; }, autoPoll: false}).navigate('shortcut');
      assert.deepStrictEqual(calls, ['undef', 'none'], 'only an explicit false or a throwing canIUse stops the call');
      assert.strictEqual(r3.status, 'unsupported');
      assert.strictEqual(r4.status, 'unsupported');
      void r1; void r2;
    });
    await test('default_lookup_takes_tt_when_canIUse_answers_undefined', function () {
      var Missions = require(path.join(base, 'TikTokMissionService.js'));
      var calls = [];
      global.TTMinis = {game: {canIUse: function () { return false; }, addShortcut: function () { calls.push('TTMinis'); }}};
      global.tt = {canIUse: function () { return undefined; }, addShortcut: function () { calls.push('tt'); }};
      try {
        new Missions({autoPoll: false}).navigate('shortcut');
      } finally { delete global.TTMinis; delete global.tt; }
      assert.deepStrictEqual(calls, ['tt'], 'TTMinis.game said false, tt (undefined) is used');
    });
    await test('returning_cancels_a_pending_jump_answer', async function () {
      var t = setup();
      t.c.press('shortcut');
      var jump = t.fake.last('addShortcut');
      t.c.onShow({scene: 'desktop_shortcut'}); await flush();                                       // back before the jump answered
      jump.opts.success({}); await flush();                              // late answer of the old jump
      assert.strictEqual(t.fake.count('getShortcutMissionReward'), 1, 'one check after returning');
      assert.strictEqual(t.state().message, '', 'the late jump answer does not reopen guidance');
    });
    await test('platform_answers_are_logged_in_the_engine', async function () {
      var lines = [], keep = console.info;
      global.cc = {sys: {}};
      global.tt = {canIUse: function (m) { return m === 'getShortcutMissionReward' ? false : undefined; }, addShortcut: function () {}};
      console.info = function (s) { lines.push(String(s)); };
      try {
        var t = setup();
        t.c.press('shortcut');
        t.fake.last('addShortcut').opts.fail({errMsg: 'addShortcut:fail cancel', errCode: 21500}); await flush();
      } finally { console.info = keep; delete global.cc; delete global.tt; }
      var text = lines.join('\n');
      assert(/\[TikTokKit\] runtime tt \{addShortcut=undefined, getShortcutMissionReward\(missing\)=false/.test(text), text);
      assert(/shortcut navigate -> error \(addShortcut\) errorCode 21500 errMsg addShortcut:fail cancel/.test(text), text);
      assert(/shortcut navigate \.\.\./.test(text), text);
    });
    await test('unset_B_pays_nothing', async function () {
      config.normalLevelCoins = 0;
      try {
        var t = setup();
        assert.strictEqual(t.state().shortcut.reward, '');
        t.c.press('shortcut');
        t.fake.last('addShortcut').opts.success({}); await flush();
        t.c.onShow({scene: 'desktop_shortcut'}); await flush();
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
        var comp = new Comp(); comp.node = {activeInHierarchy: true}; comp.scheduleOnce = function () {};
        comp.shortcutNode = new Node('a'); comp.profileNode = new Node('b');
        comp.shortcutNode.comps.Button = new Button();
        var store = new SaveStore({coins: 0}, {storage: memoryStorage(), key: 'cc', login: false}); store.load();
        var toasts = [];
        var ctrl = comp.init(store, {native: false, ui: {toast: function (message) { toasts.push(message); }}});
        assert(comp.shortcutNode.active && comp.profileNode.active, 'both entries shown');
        var label = comp.shortcutNode.getChildByName('HomeEntryText').getComponent(Label);
        assert.strictEqual(label.string, 'Add to Home', 'no sprite -> title only (11.17.15: no reward words)');
        assert.strictEqual(typeof comp.profileNode.handlers.touchend, 'function');
        comp.shortcutNode.handlers.touchend();
        comp.profileNode.handlers.touchend();
        assert.strictEqual(ctrl.flow.native, false);
        assert.deepStrictEqual(toasts, []);
        assert.strictEqual(store.get().coins, 0);
        comp.onDestroy();
      } finally { delete global.cc; }
    });
  } finally { config.normalLevelCoins = keepB; }

  var failed = results.filter(function (r) { return r.status !== 'passed'; });
  console.log(JSON.stringify({suite: 'home-entries', passed: results.length - failed.length, failed: failed.length, results: results}, null, 2));
  if (failed.length) process.exitCode = 1;
  setTimeout(function () { process.exit(process.exitCode || 0); }, 10);
})();
