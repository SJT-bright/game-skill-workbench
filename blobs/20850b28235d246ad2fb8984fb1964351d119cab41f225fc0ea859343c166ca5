'use strict';
// tools/home_free_slot.js (生成时预防 P06 3): a home with 6 original buttons; the two platform entries go where no
// button is, never on one. Includes the old way (a guessed bottom-row position) failing on the same fixture.
// Node only, a fraction of a second.
var assert = require('assert'), path = require('path'), fs = require('fs'), os = require('os');
var child = require('child_process');
var TOOL = process.env.HOME_FREE_SLOT || path.join(__dirname, '..', 'tools', 'home_free_slot.js');
var S = require(TOOL);
var results = [];
function test(name, run) {
  try { run(); results.push({name: name, status: 'passed'}); }
  catch (e) { results.push({name: name, status: 'failed', error: String(e && e.message || e)}); }
}

var SCREEN = {w: 720, h: 1280}, ENTRY = {w: 140, h: 140};
// 720x1280 design, centre origin, y up: the kind of home the 11-04 survey found entries piled on.
var HOME = [
  {name: 'btnStart', x: 0, y: -330, w: 360, h: 140},
  {name: 'btnSetting', x: -290, y: 520, w: 100, h: 100},
  {name: 'btnShop', x: -260, y: -560, w: 150, h: 130},
  {name: 'btnSkin', x: 260, y: -560, w: 150, h: 130},
  {name: 'btnSign', x: -290, y: 160, w: 110, h: 110},
  {name: 'btnGift', x: 290, y: 160, w: 110, h: 110}
];

function inside(s) {
  return s.x - s.w / 2 >= -SCREEN.w / 2 && s.x + s.w / 2 <= SCREEN.w / 2 &&
    s.y - s.h / 2 >= -SCREEN.h / 2 && s.y + s.h / 2 <= SCREEN.h / 2 - SCREEN.h * S.DEFAULTS.topReserve;
}

test('six_button_home_two_free_slots_touch_no_button', function () {
  var r = S.findFreeSlots({screen: SCREEN, buttons: HOME, entry: ENTRY});
  assert.ok(r.ok, r.error);
  assert.strictEqual(r.slots.length, 2);
  r.slots.forEach(function (s) {
    HOME.forEach(function (b) { assert.ok(!S.intersects(s, b), 'slot ' + JSON.stringify(s) + ' hits ' + b.name); });
    // and keeps the gap: grown by 16 on each side it still touches nothing
    HOME.forEach(function (b) {
      assert.ok(!S.intersects({x: s.x, y: s.y, w: s.w + 2 * 16, h: s.h + 2 * 16}, b), 'slot within the gap of ' + b.name);
    });
    assert.ok(inside(s), 'slot off the screen or in the capsule band: ' + JSON.stringify(s));
  });
  assert.ok(!S.intersects(r.slots[0], r.slots[1]), 'the two entries overlap each other');
});

test('old_way_guessed_bottom_row_hits_an_original_button', function () {
  // what an AI wrote without measuring: the bottom row at +-260, -560 (rule U3 for remakes) -- right on Shop / Skin
  var guessed = [{x: -260, y: -560, w: 140, h: 140}, {x: 260, y: -560, w: 140, h: 140}];
  var hit = guessed.some(function (s) { return HOME.some(function (b) { return S.intersects(s, b); }); });
  assert.ok(hit, 'fixture must make the guessed position fail');
});

test('no_room_is_an_error_not_a_guess', function () {
  var wall = [];
  for (var y = -560; y <= 560; y += 160) for (var x = -280; x <= 280; x += 140) wall.push({name: 'b' + x + '_' + y, x: x, y: y, w: 130, h: 150});
  var r = S.findFreeSlots({screen: SCREEN, buttons: wall, entry: ENTRY});
  assert.strictEqual(r.ok, false);
  assert.ok(/no free place/.test(r.error) && /do not guess/.test(r.error), r.error);
  assert.ok(!r.slots);
});

test('one_slot_each_when_no_row_holds_both', function () {
  // a narrow free column on each side only: the pair cannot share a row, each still lands clear
  var r = S.findFreeSlots({screen: {w: 600, h: 1280}, entry: {w: 120, h: 120},
    buttons: [{name: 'mid', x: 0, y: 0, w: 120, h: 1280}, {name: 'leftLow', x: -200, y: -320, w: 200, h: 640},
      {name: 'rightHigh', x: 200, y: 320, w: 200, h: 640}]});
  assert.ok(r.ok, r.error);
  assert.ok(!S.intersects(r.slots[0], r.slots[1]));
});

test('safe_area_is_respected', function () {
  var safe = {x0: -300, y0: -500, x1: 300, y1: 400};
  var r = S.findFreeSlots({screen: SCREEN, buttons: HOME, entry: ENTRY, safe: safe});
  assert.ok(r.ok, r.error);
  r.slots.forEach(function (s) {
    assert.ok(s.x - s.w / 2 >= safe.x0 && s.x + s.w / 2 <= safe.x1 && s.y - s.h / 2 >= safe.y0 && s.y + s.h / 2 <= safe.y1,
      'outside the safe area: ' + JSON.stringify(s));
    HOME.forEach(function (b) { assert.ok(!S.intersects(s, b), b.name); });
  });
  assert.strictEqual(S.findFreeSlots({screen: SCREEN, buttons: HOME, entry: ENTRY, safe: {x0: 0, y0: 0, x1: 0, y1: 0}}).ok, false);
});

test('bad_input_is_refused', function () {
  assert.strictEqual(S.findFreeSlots({screen: SCREEN, buttons: HOME}).ok, false);
  assert.strictEqual(S.findFreeSlots({screen: SCREEN, entry: ENTRY, buttons: [{name: 'x', x: 0}]}).ok, false);
});

test('reads_buttons_from_a_24_and_a_3x_prefab', function () {
  var p24 = [
    {__type__: 'cc.Prefab', data: {__id__: 1}},
    {__type__: 'cc.Node', _name: 'Home', _parent: null, _components: [], _contentSize: {width: 720, height: 1280},
      _trs: {array: [360, 640, 0, 0, 0, 0, 1, 1, 1, 1]}},
    {__type__: 'cc.Node', _name: 'bottom', _parent: {__id__: 1}, _components: [], _contentSize: {width: 0, height: 0},
      _trs: {array: [0, -500, 0, 0, 0, 0, 1, 2, 2, 1]}},
    {__type__: 'cc.Node', _name: 'btnShop', _parent: {__id__: 2}, _components: [{__id__: 4}],
      _contentSize: {width: 50, height: 40}, _anchorPoint: {x: 0, y: 0}, _trs: {array: [10, 5, 0, 0, 0, 0, 1, 1, 1, 1]}},
    {__type__: 'cc.Button', node: {__id__: 3}}
  ];
  var b = S.boxesFromPrefab(p24);
  assert.strictEqual(b.length, 1);
  assert.deepStrictEqual([b[0].x, b[0].y, b[0].w, b[0].h], [70, -450, 100, 80]);   // 10*2 + 50, -500 + 5*2 + 40
  var p3 = [
    {__type__: 'cc.Prefab', data: {__id__: 1}},
    {__type__: 'cc.Node', _name: 'Home', _parent: null, _components: [], _lpos: {x: 0, y: 0}},
    {__type__: 'cc.Node', _name: 'logo', _parent: {__id__: 1}, _components: [{__id__: 3}], _lpos: {x: 0, y: 300}},
    {__type__: 'cc.UITransform', node: {__id__: 2}, _contentSize: {width: 400, height: 200}, _anchorPoint: {x: 0.5, y: 0.5}}
  ];
  assert.strictEqual(S.boxesFromPrefab(p3).length, 0, 'no cc.Button: not a button');
  var o = S.boxesFromPrefab(p3, ['logo']);
  assert.deepStrictEqual([o[0].x, o[0].y, o[0].w, o[0].h], [0, 300, 400, 200]);
});

test('reads_buttons_from_a_ui_dump', function () {
  var d = {nodes: [{name: 'btnStart', opacity: 1, comps: {button: {}}, rect: [0.25, 0.75, 0.5, 0.1]},
    {name: 'bg', opacity: 1, comps: {sprite: {}}, rect: [0, 0, 1, 1]}]};
  var b = S.boxesFromDump(d, SCREEN);
  assert.strictEqual(b.length, 1);
  assert.deepStrictEqual([b[0].x, Math.round(b[0].y), b[0].w, b[0].h], [0, -384, 360, 128]);
});

test('cli_exit_codes', function () {
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freeslot-'));
  try {
    var f = path.join(dir, 'home.json');
    fs.writeFileSync(f, JSON.stringify({nodes: HOME.map(function (b) {
      return {name: b.name, opacity: 1, comps: {button: {}}, rect: [(b.x - b.w / 2) / 720 + 0.5, 0.5 - (b.y + b.h / 2) / 1280, b.w / 720, b.h / 1280]};
    })}));
    var ok = child.spawnSync(process.execPath, [TOOL, '--dump', f, '--screen', '720x1280', '--entry', '140x140'], {encoding: 'utf8'});
    assert.strictEqual(ok.status, 0, ok.stdout + ok.stderr);
    var out = JSON.parse(ok.stdout);
    out.slots.forEach(function (s) { HOME.forEach(function (b) { assert.ok(!S.intersects(s, b)); }); });
    var full = child.spawnSync(process.execPath, [TOOL, '--dump', f, '--screen', '720x1280', '--entry', '700x700'], {encoding: 'utf8'});
    assert.strictEqual(full.status, 1, full.stdout);
    var bad = child.spawnSync(process.execPath, [TOOL, '--screen', '720x1280'], {encoding: 'utf8'});
    assert.strictEqual(bad.status, 2);
  } finally { fs.rmSync(dir, {recursive: true, force: true}); }
});

var failed = results.filter(function (r) { return r.status !== 'passed'; }).length;
console.log(JSON.stringify({suite: 'home-free-slot', passed: results.length - failed, failed: failed, results: results}, null, 2));
if (failed) process.exitCode = 1;
