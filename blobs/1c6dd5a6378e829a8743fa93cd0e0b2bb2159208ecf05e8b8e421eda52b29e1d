'use strict';
// node tests/home-entries-notice-settle.test.js   (生成时预防 R4Q6, 问题普查 补查3 第 6 组; Node only, < 1 s)
// HomeGrowthEntries:
//  - one notice: "Available in TikTok" / "Opening..." go through the GameUIKit toast when the game has it, else a
//    messageLabel that hides itself after NOTICE_MS; a second notice replaces the first, leaving the home clears it
//    (火箭三消: the text had no backing, stayed on the next page, two stacked; 奔跑吧巨人: notices stacked);
//  - entries are placed only after the home settled (>= 3 frames, the same layout signature on two frames in a row),
//    tested with two frames of different fake boxes (奔跑吧巨人: placed from boxes taken mid-layout);
//  - obstacles only inside the home panel (searchRoot): a settings popup button under the Canvas does not move them.
// HOME_ENTRIES=<old HomeGrowthEntries.js> runs the same cases on another copy (the 11.16 part must fail).
var assert = require('assert'), path = require('path');
var HGE = require(process.env.HOME_ENTRIES || path.join(__dirname, '..', 'assets', 'tiktok-platform', 'HomeGrowthEntries.js'));
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

// ---- tiny Cocos 2.4 stand-in: translation only, anchor 0.5
function Btn() {}
var cc = {Button: Btn, v2: function (x, y) { return {x: x, y: y}; }};
function world(n) { var p = n.parent ? world(n.parent) : {x: 0, y: 0}; return {x: p.x + n.position.x, y: p.y + n.position.y}; }
function node(name, parent, x, y, w, h, isButton) {
  var n = {name: name, position: {x: x, y: y}, w: w, h: h, children: [], parent: parent || null, active: true, btn: !!isButton};
  n.getComponent = function (C) { return C === Btn && n.btn ? {} : null; };
  n.getBoundingBoxToWorld = function () { var c = world(n); return {x: c.x - n.w / 2, y: c.y - n.h / 2, width: n.w, height: n.h}; };
  n.convertToNodeSpaceAR = function (v) { var c = world(n); return {x: v.x - c.x, y: v.y - c.y}; };
  n.convertToWorldSpaceAR = function (v) { var c = world(n); return {x: v.x + c.x, y: v.y + c.y}; };
  n.setPosition = function (v) { n.position = {x: v.x, y: v.y}; };
  if (parent) parent.children.push(n);
  return n;
}
function home() {
  var canvas = node('Canvas', null, 0, 0, 720, 1280);
  var panel = node('homePanel', canvas, 0, 0, 720, 1280);
  var start = node('btnStart', panel, 0, -200, 360, 140, true);
  var row = node('BottomRow', panel, 0, -520, 600, 120);
  var a = node('AddToHome', row, -150, 0, 200, 80), b = node('ProfileRevisit', row, 150, 0, 200, 80);
  // the settings popup is kept (inactive look but active node) under the Canvas, its button lies over the entries
  var settings = node('SettingsPopup', canvas, 0, 0, 720, 1280);
  var close = node('btnSettingClose', settings, -150, -520, 220, 100, true);
  return {canvas: canvas, panel: panel, start: start, entries: [a, b], settings: settings, close: close};
}

test('notice_goes_through_gameuikit_toast_single_and_cleared_when_home_left', function () {
  assert.strictEqual(typeof HGE.makeNotice, 'function', 'HomeGrowthEntries has no single notice (makeNotice)');
  var shown = [], cleared = 0, text = '';
  var ui = {toast: function (t) { shown.push(t); text = t; }, toastText: function () { return text; },
    clearToast: function () { cleared++; text = ''; return true; }};
  var n = HGE.makeNotice({ui: ui, platform: function () { return true; }});
  assert.strictEqual(n.show('Available in TikTok'), 'GameUIKit', 'the kit toast is not used first');
  n.show('Opening...');
  assert.deepStrictEqual(shown, ['Available in TikTok', 'Opening...']);
  assert.strictEqual(n.text(), 'Opening...');
  n.clear();
  assert.strictEqual(cleared, 1); assert.strictEqual(n.text(), '');
  // another part's toast is not cleared by the home
  n.show('Opening...'); ui.toast('Reward claimed'); n.clear();
  assert.strictEqual(cleared, 1, 'the home cleared a toast it did not show');
});

test('notice_without_gameuikit_hides_label_after_time_one_at_a_time', function () {
  assert.strictEqual(typeof HGE.makeNotice, 'function', 'HomeGrowthEntries has no single notice (makeNotice)');
  var timers = [], label = {text: '', active: false};
  var n = HGE.makeNotice({platform: function () { return false; },
    label: {set: function (t) { label.text = t; label.active = true; }, hide: function () { label.active = false; }},
    later: function (ms, fn) { var t = {ms: ms, live: true}; t.fn = function () { t.live = false; fn(); }; timers.push(t); return function () { t.live = false; }; }});
  assert.strictEqual(n.show('Available in TikTok'), 'label');
  assert.ok(label.active && timers[0].ms === HGE.NOTICE_MS && HGE.NOTICE_MS > 0 && HGE.NOTICE_MS <= 3000);
  n.show('Available in TikTok');
  assert.strictEqual(timers.filter(function (t) { return t.live; }).length, 1, 'two notice timers live (stacked notices)');
  timers[1].fn();
  assert.strictEqual(label.active, false, 'the label stays on screen after its time');
  n.show('Opening...'); n.clear();
  assert.strictEqual(label.active, false, 'the label stays after leaving the home');
  assert.strictEqual(timers.filter(function (t) { return t.live; }).length, 0);
});

test('placement_waits_three_frames_and_two_equal_signatures', function () {
  assert.strictEqual(typeof HGE.settleGate, 'function', 'HomeGrowthEntries places on the first frame (no settleGate)');
  function run(sigs) {
    var i = 0, placedAt = 0;
    var g = HGE.settleGate({signature: function () { return sigs[Math.min(i - 1, sigs.length - 1)]; },
      place: function () { placedAt = i; return {ok: true}; }});
    for (i = 1; i <= 20 && !g.done; i++) g.tick();
    return placedAt;
  }
  assert.strictEqual(run(['A', 'A', 'A']), 3, 'placed before frame 3');
  assert.strictEqual(run(['A', 'B', 'B']), 3);
  assert.strictEqual(run(['A', 'B', 'C', 'C']), 4, 'placed while the boxes still moved');
  // two frames of real (fake) boxes: the start button slides in, then stops
  var h = home();
  var spec = {root: h.canvas, searchRoot: h.panel, entries: h.entries};
  var s1 = HGE.layoutSignature(cc, spec);
  h.start.position.y = -520;                          // frame 2: the Widget / tween moved it over the row
  var s2 = HGE.layoutSignature(cc, spec);
  assert.notStrictEqual(s1, s2, 'a moved button does not change the signature');
  assert.strictEqual(HGE.layoutSignature(cc, spec), s2);
});

test('obstacles_only_inside_home_panel', function () {
  var h = home();
  var r = HGE.placeEntries(cc, {root: h.canvas, searchRoot: h.panel, entries: h.entries, screen: {w: 720, h: 1280}});
  assert.ok(r.ok && r.kept === true, 'entries moved because of a settings popup button: ' + JSON.stringify(r.buttons && r.buttons.map(function (b) { return b.name; })));
  assert.ok(!r.buttons.some(function (b) { return b.name === 'btnSettingClose'; }));
  var whole = HGE.placeEntries(cc, {root: h.canvas, entries: home().entries, screen: {w: 720, h: 1280}});
  assert.ok(whole.ok, 'fixture: without searchRoot the whole Canvas still works');
});

var failed = results.filter(function (r) { return r.status !== 'passed'; });
console.log(JSON.stringify({suite: 'home-entries-notice-settle', passed: results.length - failed.length, failed: failed.length,
  results: results}, null, 2));
process.exitCode = failed.length ? 1 : 0;
