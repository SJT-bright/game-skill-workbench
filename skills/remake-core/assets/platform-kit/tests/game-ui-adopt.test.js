'use strict';
// node tests/game-ui-adopt.test.js   (生成时预防 A3 批: GameUIKit 1.1.1 adoptPopup, Cocos 2.4 and 3.x)
// AdBoostKit and GameUIKit kept separate popup stacks: an AdBoostKit popup over a GameUIKit result page (or the other
// way round) showed two dim layers, and the lower X stayed visible but could not be tapped. 1.1.1:
//   var release = UI.adoptPopup({isOpen: fn, setCovered: fn(covered)})
// puts the other kit's popup into the same stack; only the top layer is dimmed. The AdBoostKit popup here is a
// stand-in with only isOpen / setCovered (its owner hides / shows its own mask and X on setCovered). Without
// adoptPopup (GameUIKit 1.1.0, AdBoostKit as it is now) every case fails with "2 dim layers": that is the old bug.
// GAMEUI_KINDS=24 or 3x picks one engine; GAMEUI_KIT_FILE / GAMEUI_KIT_3X_FILE run the cases on another copy.
var assert = require('assert');
var S = require('./engine-stub-ui');

var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var KIND = KINDS[0];
function fresh() { var env = S.loadKit(KIND); env.Kit._reset(); return env; }
function after(env) { env.clock.advance(200); env.flush(); }

// AdBoostKit popup stand-in: open until closed; covered = its own mask and X hidden by its owner
function adPopup() {
  var f = {open: true, covered: false, calls: []};
  f.isOpen = function () { return f.open; };
  f.setCovered = function (c) { f.calls.push(c); f.covered = c; };
  return f;
}
// what AdBoostKit.popup does: join the GameUIKit stack when the kit offers adoptPopup (1.1.0 does not: nothing joins)
function join(env, f) {
  if (typeof env.Kit.adoptPopup !== 'function') return function () { return false; };
  return env.Kit.adoptPopup({isOpen: f.isOpen, setCovered: f.setCovered});
}
function active(n) { return !!n && n.active !== false; }
// dim layers on screen: GameUIKit masks still active + AdBoostKit popups open and not covered
function layers(pages, ads) {
  var n = 0;
  pages.forEach(function (p) { if (p.isOpen() && active(p.mask)) n++; });
  ads.forEach(function (f) { if (f.open && !f.covered) n++; });
  return n;
}
function resultPage(env) {
  var page = env.Kit.resultPage(env.canvas, {amount: 20, double: false, onReward: function () {}, onNext: function () {}, onHome: function () {}});
  env.flush();
  return page.popup;
}
function popupWithX(env) {
  var p = env.Kit.popup(env.canvas, {closeFrame: env.frame(64, 64)});
  env.flush();
  return p;
}

test('1 AdBoostKit popup over a GameUIKit result page: one dim layer; closing it brings the page mask back', function () {
  var env = fresh(), res = resultPage(env), ad = adPopup();
  assert.strictEqual(layers([res], []), 1);
  var release = join(env, ad);
  assert.strictEqual(layers([res], [ad]), 1, layers([res], [ad]) + ' dim layers (old: the result mask stays under the ad popup)');
  assert.strictEqual(active(res.mask), false, 'result page mask hidden while covered');
  assert.strictEqual(ad.covered, false, 'the top (ad) popup keeps its mask and X');
  ad.open = false; assert.strictEqual(release(), true);
  assert.strictEqual(active(res.mask), true, 'result page mask back after the ad popup closed');
  assert.strictEqual(layers([res], [ad]), 1);
});

test('2 GameUIKit popup over an AdBoostKit popup: the ad popup is covered (mask and X hidden), uncovered after', function () {
  var env = fresh(), ad = adPopup(), release = join(env, ad);
  var p = popupWithX(env);
  assert.strictEqual(layers([p], [ad]), 1, layers([p], [ad]) + ' dim layers (old: the ad popup keeps its mask under the GameUIKit popup)');
  assert.strictEqual(ad.covered, true, 'setCovered(true): the ad popup hides its own mask and X');
  assert.ok(active(p.mask) && active(p.closeNode), 'the top popup shows its mask and X');
  p.close(); after(env);
  assert.strictEqual(ad.covered, false, 'setCovered(false) once the GameUIKit popup closed');
  assert.strictEqual(JSON.stringify(ad.calls), '[true,false]', 'told only when the state changes: ' + JSON.stringify(ad.calls));
  ad.open = false; release();
});

test('3 three layers (result page, ad popup, GameUIKit popup with X): only the top one dims and shows its X', function () {
  var env = fresh(), res = resultPage(env), ad = adPopup(), release = join(env, ad), top = popupWithX(env);
  assert.strictEqual(layers([res, top], [ad]), 1, layers([res, top], [ad]) + ' dim layers');
  assert.ok(ad.covered && !active(res.mask) && active(top.closeNode));
  top.close(); after(env);
  assert.ok(!ad.covered && !active(res.mask), 'ad popup is the top again');
  ad.open = false; release();
  assert.ok(active(res.mask), 'result page is the top again');
  assert.strictEqual(layers([res, top], [ad]), 1);
});

test('4 release(): twice is harmless; releasing while covered uncovers once (keep:true popup reopens with its X)', function () {
  var env = fresh(), ad = adPopup(), release = join(env, ad), p = popupWithX(env);
  assert.strictEqual(ad.covered, true, 'covered by the GameUIKit popup (old: never told)');
  assert.strictEqual(release(), true);
  assert.strictEqual(release(), false, 'second release does nothing');
  assert.strictEqual(JSON.stringify(ad.calls), '[true,false]', JSON.stringify(ad.calls));
  assert.strictEqual(env.Kit.openPopups().length, 1, 'only the GameUIKit popup is left');
  p.close(); after(env);
  assert.strictEqual(JSON.stringify(ad.calls), '[true,false]', 'a released popup is never told again');
});

test('5 isOpen() turned false without release(): the next restack drops it and the page underneath gets its mask back', function () {
  var env = fresh(), res = resultPage(env), ad = adPopup();
  join(env, ad);
  assert.strictEqual(active(res.mask), false, 'covered by the ad popup (old: never covered: 2 dim layers)');
  ad.open = false;                                   // AdBoostKit forgot release()
  assert.strictEqual(env.Kit.openPopups().length, 1, 'dropped at restack');
  assert.strictEqual(active(res.mask), true, 'result page mask back');
  var ad2 = adPopup(), r2 = join(env, ad2), p = popupWithX(env);
  assert.strictEqual(ad2.covered, true);
  ad2.open = false; p.close(); after(env);           // dropped while covered: one setCovered(false)
  assert.strictEqual(JSON.stringify(ad2.calls), '[true,false]', JSON.stringify(ad2.calls));
  assert.strictEqual(r2(), true); assert.strictEqual(r2(), false);
});

test('6 adopting the same popup again replaces it (a reopen); a wrong spec throws at build time', function () {
  var env = fresh();
  assert.strictEqual(typeof env.Kit.adoptPopup, 'function', 'GameUIKit has no adoptPopup (1.1.0): AdBoostKit popups cannot join the stack');
  var res = resultPage(env), ad = adPopup(), r1 = join(env, ad), r2 = join(env, ad);
  assert.strictEqual(env.Kit.openPopups().length, 2, 'result page + one entry for the ad popup');
  assert.strictEqual(ad.covered, false);
  assert.strictEqual(r1(), false, 'the replaced entry is already released');
  ad.open = false; assert.strictEqual(r2(), true);
  assert.ok(active(res.mask));
  assert.throws(function () { env.Kit.adoptPopup({isOpen: function () { return true; }}); }, /needs \{isOpen/);
  assert.throws(function () { env.Kit.adoptPopup(); }, /needs \{isOpen/);
  env.Kit.setup({stackPopups: false});
  var r3 = env.Kit.adoptPopup({isOpen: ad.isOpen, setCovered: ad.setCovered});
  assert.strictEqual(r3(), false, 'stackPopups:false: nothing joins, release is a no-op');
  env.Kit.setup({stackPopups: true});
});

(async function main() {
  var failed = 0;
  for (var k = 0; k < KINDS.length; k++) {
    KIND = KINDS[k];
    for (var i = 0; i < cases.length; i++) {
      var c = cases[i];
      try { await c.fn(); console.log('PASS [' + KIND + '] ' + c.name); } catch (e) { failed++; console.log('FAIL [' + KIND + '] ' + c.name + '\n     ' + (e && e.message)); }
    }
  }
  console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit adoptPopup, ' + KINDS.join(' + ') + ', Node stand-in; 待真机复测)');
  if (failed) process.exitCode = 1;
})();
