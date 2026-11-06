'use strict';
// node tests/game-ui-ad-feedback.test.js   (GameUIKit 1.1.5, Cocos 2.4 and 3.x; 广告skill 11-05 建议)
// Page templates (revive, result x2) with runAd: AdBoostKit shows its own "no reward" reason, so the page stays quiet,
// unless the result says AdBoostKit did not show one (feedbackShown === false, AdBoostKit 1.3.3). Then the page shows
// exactly one toast. A runAd without the field keeps the old behaviour (no page toast), toast:false keeps the page quiet,
// and the RewardedService path (no runAd) is unchanged. The old kit (1.1.4) shows nothing at all in the
// feedbackShown === false case: the player gets no word that the video did not pay.
// GAMEUI_KINDS=24 or 3x picks one engine; GAMEUI_KIT_FILE / GAMEUI_KIT_3X_FILE run the cases on another copy of the kit.
var assert = require('assert');
var S = require('./engine-stub-ui');
var RunSession = require('../parts/RunSession.js');

var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var KIND = KINDS[0];
function fresh() { var env = S.loadKit(KIND); env.Kit._reset(); return env; }
function session(env) { return RunSession.create(env.cc, {autoHide: false, sceneBound: false}); }
function tap(env, page, slot) { env.clock.advance(600); return env.tapNode(page.button(slot).node); }
function settle() { return new Promise(function (r) { setImmediate(r); }); }
var CLOSED = {status: 'cancelled', rewarded: false, message: 'Video closed. No reward was claimed.'};
function closedWith(extra) { var r = {}, k; for (k in CLOSED) r[k] = CLOSED[k]; for (k in extra) r[k] = extra[k]; return r; }
// count the page's own toasts (Kit.toast is called through the Kit object)
function countToasts(env) {
  var c = {n: 0, texts: []}, orig = env.Kit.toast;
  env.Kit.toast = function (text) { c.n++; c.texts.push(text); return orig.apply(this, arguments); };
  return c;
}
// runAd stand-in for AdBoostKit.runAd: answers at once with the given result
function runAdAnswering(result, calls) {
  return function (ads, req, done) { calls.push(req.placementKey); done(result); };
}
function revive(env, opts) {
  var s = session(env);
  s.newRun(function () { return {}; });
  var o = {session: s, ads: {}, placementKey: 'revive', onRevive: function () {}, onGiveUp: function () {}};
  for (var k in opts) o[k] = opts[k];
  var page = env.Kit.revivePage(env.canvas, o);
  env.flush();
  return page;
}

test('1 runAd says it showed nothing (feedbackShown false): the revive page shows one toast', async function () {
  var env = fresh(), calls = [], t = countToasts(env);
  var page = revive(env, {runAd: runAdAnswering(closedWith({feedbackShown: false}), calls)});
  tap(env, page, 'watchAd'); await settle();
  assert.deepStrictEqual(calls, ['revive'], 'one ad request');
  assert.strictEqual(t.n, 1, 'exactly one toast (the old kit shows none)');
  assert.strictEqual(env.Kit.toastText(), CLOSED.message);
  assert.ok(page.isOpen(), 'page stays for another try');
});

test('2 runAd already showed its reason (feedbackShown true): the page stays quiet (no second toast)', async function () {
  var env = fresh(), calls = [], t = countToasts(env);
  var page = revive(env, {runAd: runAdAnswering(closedWith({feedbackShown: true}), calls)});
  tap(env, page, 'watchAd'); await settle();
  assert.strictEqual(t.n, 0, 'no page toast on top of the AdBoostKit one');
});

test('3 an older runAd without the field: same as before (no page toast)', async function () {
  var env = fresh(), calls = [], t = countToasts(env);
  var page = revive(env, {runAd: runAdAnswering(closedWith({}), calls)});
  tap(env, page, 'watchAd'); await settle();
  assert.strictEqual(t.n, 0);
});

test('4 toast:false keeps the page quiet even when runAd showed nothing', async function () {
  var env = fresh(), calls = [], t = countToasts(env);
  var page = revive(env, {toast: false, runAd: runAdAnswering(closedWith({feedbackShown: false}), calls)});
  tap(env, page, 'watchAd'); await settle();
  assert.strictEqual(t.n, 0);
});

test('5 RewardedService path (no runAd) unchanged: one toast with the result message', async function () {
  var env = fresh(), t = countToasts(env), answer = null;
  var ads = {request: function () { return new Promise(function (r) { answer = r; }); }};
  var page = revive(env, {ads: ads});
  tap(env, page, 'watchAd'); answer(CLOSED); await settle();
  assert.strictEqual(t.n, 1);
  assert.strictEqual(env.Kit.toastText(), CLOSED.message);
});

test('6 result page x2 with runAd that showed nothing: one toast, nothing paid', async function () {
  var env = fresh(), s = session(env), calls = [], t = countToasts(env), grants = [];
  s.newRun(function () { return {}; });
  var store = {grant: function (d, done) { grants.push(d); done(); return {ok: true}; }};
  var page = env.Kit.resultPage(env.canvas, {session: s, store: store, amount: 30, ads: {}, placementKey: 'result_x2',
    runAd: runAdAnswering(closedWith({feedbackShown: false}), calls), onNext: function () {}, onHome: function () {}});
  env.flush();
  tap(env, page, 'double'); await settle();
  assert.deepStrictEqual(calls, ['result_x2']);
  assert.strictEqual(grants.length, 0, 'not watched: nothing paid');
  assert.strictEqual(t.n, 1);
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
  console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit page ad feedback, ' + KINDS.join(' + ') + ', Node stand-in; 待真机复测)');
  if (failed) process.exitCode = 1;
})();
