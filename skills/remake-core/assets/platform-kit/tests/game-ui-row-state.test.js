'use strict';
// node tests/game-ui-row-state.test.js   (GameUIKit 1.1.6, 生成时预防 R4Q6, 问题普查 补查3 第 6 / 7 / 8 组)
// 1. a toast is cleared when the next page opens (火箭三消: "Available in TikTok" stayed on the next page);
// 2. UI.iconValue: the icon keeps its own box and the number is centred right of it (方块收割者: check-in 200 read
//    as 00 under the icon, HUD coins ran into LEVEL);
// 3. popup / page templates refresh from the save on EVERY opening (奔跑吧巨人: a cached page kept old coins);
// 4. UI.newButton / UI.button({active}) set the first active state when the node is made (奔跑吧巨人: the pause key
//    showed on the first frame).
// Each case also shows the old way. GAMEUI_KINDS=24 or 3x picks one engine (default both); GAMEUI_KIT_FILE /
// GAMEUI_KIT_3X_FILE run the cases on another copy (the 1.1.5 kit must fail).
var assert = require('assert');
var S = require('./engine-stub-ui');

var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
function overlap(a, b) { return Math.abs(a.x - b.x) * 2 < a.width + b.width && Math.abs(a.y - b.y) * 2 < a.height + b.height; }

test('1 a toast is gone once the next page opens; the old kit keeps it on screen', function (env) {
  env.Kit.toast('Available in TikTok');
  assert.strictEqual(env.Kit.toastText(), 'Available in TikTok');
  env.Kit.popup(env.canvas, {name: 'Shop'});
  assert.strictEqual(env.Kit.toastText(), '', 'the toast of the home is still shown on the Shop page');
  assert.strictEqual(typeof env.Kit.clearToast, 'function', 'no UI.clearToast for pages the game switches itself');
  env.Kit.toast('Saved', {keepOnPage: true});
  env.Kit.popup(env.canvas, {name: 'Next'});
  assert.strictEqual(env.Kit.toastText(), 'Saved', 'keepOnPage toast survives a page opening');
  assert.strictEqual(env.Kit.clearToast(), true);
  assert.strictEqual(env.Kit.toastText(), '');
});

test('2 UI.iconValue: icon box and number box never overlap, "200" fits; old hand-made cell overlaps', function (env) {
  assert.strictEqual(typeof env.Kit.iconValue, 'function', 'GameUIKit has no UI.iconValue (icon + number row)');
  // old way (方块收割者 签到格): icon and Label both centred in the 120 x 40 cell
  var cell = new env.cc.Node('OldCell'); env.canvas.addChild(cell);
  var ic = new env.cc.Node('Icon'); cell.addChild(ic); ic.width = 40; ic.height = 40;
  var tx = new env.cc.Node('Num'); cell.addChild(tx); tx.width = 60; tx.height = 40;
  assert.ok(overlap(env.worldBox(ic), env.worldBox(tx)), 'fixture: the old cell must overlap');
  var row = env.Kit.iconValue(env.canvas, {w: 120, h: 40, iconW: 40, value: 200, digits: false, fontSize: 24});
  var ib = env.worldBox(row.icon), nb = env.worldBox(row.number.node);
  assert.ok(!overlap(ib, nb), 'icon ' + JSON.stringify(ib) + ' and number ' + JSON.stringify(nb) + ' overlap');
  assert.ok(nb.x - nb.width / 2 >= ib.x + ib.width / 2 - 0.01, 'number box starts left of the icon edge');
  var lay = S.labelLayout(row.number.label, row.number.node);
  assert.ok(lay.fits, '"200" does not fit its box');
  row.set(999999);
  assert.ok(S.labelLayout(row.number.label, row.number.node).fits, 'a long amount runs out of the row instead of shrinking');
  assert.throws(function () { env.Kit.iconValue(env.canvas, {w: 40, h: 40}); }, /no room/);
});

test('3 a keep:true popup and the page templates refresh from the save on every opening', function (env) {
  var data = {coins: 10}, shown = [];
  var store = {get: function () { return data; }};
  var p = env.Kit.popup(env.canvas, {name: 'Cached', keep: true, store: store, refresh: function (d) { shown.push(d.coins); }});
  assert.deepStrictEqual(shown, [10], 'refresh did not run on the first opening');
  p.close(); env.flush();
  data = {coins: 55};
  p.open();
  assert.deepStrictEqual(shown, [10, 55], 'the reopened page still shows the coins of its first opening');
  var seen = [];
  var page = env.Kit.pausePage(env.canvas, {onRestart: function () {}, onHome: function () {}, store: store,
    refresh: function (d, pg) { seen.push(d.coins + ':' + (pg && pg.kind)); }});
  page.close(); env.flush();
  data = {coins: 70};
  page.open();
  assert.deepStrictEqual(seen, ['55:pause', '70:pause']);
});

test('4 UI.newButton({active: false}) is hidden from the first frame; newButton without active throws', function (env) {
  assert.strictEqual(typeof env.Kit.newButton, 'function', 'GameUIKit has no UI.newButton');
  var b = env.Kit.newButton(env.canvas, function () {}, {name: 'Pause', w: 96, h: 96, active: false});
  assert.strictEqual(b.node.active, false, 'pause key is active on the first frame');
  assert.throws(function () { env.Kit.newButton(env.canvas, function () {}, {name: 'X', w: 96, h: 96}); }, /opts\.active/);
  var n = new env.cc.Node('Continue'); env.canvas.addChild(n); n.width = 200; n.height = 80;
  env.Kit.button(n, function () {}, {active: false});
  assert.strictEqual(n.active, false, 'UI.button({active: false}) left the node active');
});

var failed = 0;
KINDS.forEach(function (kind) {
  cases.forEach(function (c) {
    var env = S.loadKit(kind); env.Kit._reset();
    try { c.fn(env); console.log('PASS [' + kind + '] ' + c.name); }
    catch (e) { failed++; console.log('FAIL [' + kind + '] ' + c.name + ': ' + (e && e.message)); }
  });
});
console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit 1.1.6 row / toast / refresh / active, 24 + 3x, Node stand-in; 待真机复测)');
process.exitCode = failed ? 1 : 0;
