'use strict';
// node tests/game-ui-pages.test.js   (生成时预防 A2 批: GameUIKit 1.1.0 page templates + valueLabel, Cocos 2.4 and 3.x)
// UI.pausePage / UI.revivePage / UI.resultPage (fixed slots, RunSession pause by reason, SaveStore.grant when present,
// RewardedService / runAd) and UI.valueLabel (P06 point 2). Each case also runs a "hand-written the old way" copy taken
// from the census (问题普查 20261104) and asserts that the old way shows the bug. Every case runs on both engines
// (GAMEUI_KINDS=24 or 3x picks one; GAMEUI_KIT_FILE / GAMEUI_KIT_3X_FILE run the cases on another copy of the kit).
var assert = require('assert');
var S = require('./engine-stub-ui');
var RunSession = require('../parts/RunSession.js');

var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var KIND = KINDS[0];
function fresh() { var env = S.loadKit(KIND); env.Kit._reset(); return env; }
function node(env, name, w, h, x, y, parent) {
  var n = new env.cc.Node(name); (parent || env.canvas).addChild(n);
  n.setContentSize(w, h); n.setPosition(x || 0, y || 0); return n;
}
function session(env) { return RunSession.create(env.cc, {autoHide: false, sceneBound: false}); }
function tap(env, page, slot) { env.clock.advance(600); return env.tapNode(page.button(slot).node); }
function after(env) { env.clock.advance(200); env.flush(); }
// RewardedService stand-in: request() stays pending until the test answers it
function fakeAds() {
  var a = {calls: [], answer: null};
  a.request = function (req) {
    a.calls.push(req);
    return new Promise(function (resolve) { a.answer = function (r) { a.answer = null; resolve(r); }; });
  };
  return a;
}
var WATCHED = {status: 'completed', rewarded: true, message: 'Reward ready.'};
var CLOSED = {status: 'cancelled', rewarded: false, message: 'Video closed. No reward was claimed.'};
// the kit runs in its own vm context: compare its arrays / objects by value
function eq(a, b) { assert.strictEqual(JSON.stringify(a), JSON.stringify(b)); }
function settle() { return new Promise(function (r) { setImmediate(r); }); }
function boxOf(s) { return {x: s.x, y: s.y, w: s.width, h: s.height}; }
function meet(a, b) { return Math.abs(a.x - b.x) * 2 < a.w + b.w && Math.abs(a.y - b.y) * 2 < a.h + b.h; }

test('1 pause by reason: Resume after another popup closed leaves the game running (shared paused boolean freezes it)', function () {
  var env = fresh(), s = session(env), resumed = 0;
  s.newRun(function () { return {score: 0}; });
  var intro = s.pause('intro');                                 // level-start popup still open
  var page = env.Kit.pausePage(env.canvas, {session: s, initRun: function () { return {score: 0}; },
    onResume: function () { resumed++; }, onHome: function () {}});
  env.flush();
  assert.deepStrictEqual(s.reasons().sort(), ['intro', 'popup']);
  intro();                                                      // the intro popup closes underneath
  tap(env, page, 'resume'); after(env);
  assert.strictEqual(resumed, 1);
  assert.strictEqual(s.isPaused(), false, 'running after Resume');
  assert.ok(page.root.active === false, 'pause page inactive after the fade');
  page.close();                                                 // a second close gives nothing back twice
  assert.strictEqual(s.isPaused(), false);
  var home = 0, b = node(env, 'Board', 300, 120, 0, -500);
  env.Kit.button(b, function () { home++; });
  env.clock.advance(600); env.tapAt(0, -500);
  assert.strictEqual(home, 1, 'the page underneath takes taps again');
  // old way (甜点消消乐 R39-R47 / 密室消除): one boolean, the pause popup saves and restores it
  var game = {paused: false}, was;
  game.paused = true;                                           // intro popup
  was = game.paused; game.paused = true;                        // pause popup opens
  game.paused = false;                                          // intro closes
  game.paused = was;                                            // Resume restores the saved value
  assert.strictEqual(game.paused, true, 'OLD WAY BUG: Resume put back a stale paused=true, the board is frozen');
});

test('2 Restart rebuilds the whole run and drops old timers (割草 Retry reset only the score)', function () {
  var env = fresh(), s = session(env), ticks = 0, restarted = null;
  function init() { return {score: 0, revives: 1, combo: 0}; }
  s.newRun(init);
  s.every(1000, function () { ticks++; });
  s.state.score = 50; s.state.revives = 0; s.state.combo = 7;
  var page = env.Kit.pausePage(env.canvas, {session: s, initRun: init, onRestart: function (st) { restarted = st; }, onHome: function () {}});
  env.flush();
  tap(env, page, 'restart'); after(env);
  assert.deepStrictEqual(s.state, {score: 0, revives: 1, combo: 0}, 'every per-run field is fresh');
  assert.strictEqual(restarted, s.state);
  assert.strictEqual(s.isPaused(), false);
  s.tick(0.1); for (var i = 0; i < 30; i++) s.tick(0.1);
  assert.strictEqual(ticks, 0, 'the old run\'s timer is gone');
  assert.throws(function () {
    env.Kit.pausePage(env.canvas, {session: s, onRestart: function () {}, onHome: function () {}});
  }, /initRun/, 'a pause page with a session but no initRun is refused when it is built');
  // old way (割草 v011): RETRY handler resets the fields the author remembered
  var g = {score: 50, revives: 0, combo: 7, timer: setInterval(function () {}, 1000)};
  (function retry() { g.score = 0; })();
  clearInterval(g.timer);
  assert.ok(g.revives === 0 && g.combo === 7, 'OLD WAY BUG: Retry kept revives 0 and combo 7 from the last run');
});

test('3 fixed slots: a new button only goes into an empty slot (a guessed position sits on Next)', function () {
  var env = fresh();
  var page = env.Kit.resultPage(env.canvas, {amount: 20, ads: fakeAds(), onReward: function () {}, onNext: function () {}, onHome: function () {}});
  env.flush();
  assert.throws(function () { page.addButton('next', {text: 'SHOP'}, function () {}); }, /slot "next" is taken/);
  assert.throws(function () { page.addButton('shop', {text: 'SHOP'}, function () {}); }, /no slot "shop"/);
  var h = page.addButton('extra', {text: 'SKINS'}, function () {});
  assert.ok(h && h.node, 'the empty slot takes it');
  assert.throws(function () { page.addButton('extra', {text: 'MORE'}, function () {}); }, /taken/);
  var names = env.Kit.pageSlots('result');
  for (var i = 0; i < names.length; i++) for (var j = i + 1; j < names.length; j++) {
    assert.ok(!meet(boxOf(page.slot(names[i])), boxOf(page.slot(names[j]))), names[i] + ' / ' + names[j] + ' overlap');
  }
  assert.ok(page.slot('claim').y < page.slot('double').y && page.slot('claim').x === page.slot('double').x, 'CLAIM right under x2');
  assert.throws(function () { page.addButton('extra', {ad: true}, function () {}); }, /taken|one ad button/);
  var rv = env.Kit.revivePage(env.canvas, {ads: fakeAds(), onRevive: function () {}, onGiveUp: function () {}});
  assert.throws(function () { rv.addButton('extra', {ad: true, text: 'x2'}, function () {}); }, /one ad button per page/);
  // old way (大西瓜 result): the AI put the added Claim at a guessed y between the buttons
  var guess = {x: 0, y: Math.round(-0.25 * 900), w: 380, h: 110};
  assert.ok(meet(guess, boxOf(page.slot('next'))), 'OLD WAY BUG: the guessed Claim covers Next');
});

test('4 revive: one ad per tap, reward only when watched, pause("ad") given back, NO THANKS is free', async function () {
  var env = fresh(), s = session(env), ads = fakeAds(), revived = 0, gaveUp = 0;
  s.newRun(function () { return {}; });
  var page = env.Kit.revivePage(env.canvas, {session: s, ads: ads, placementKey: 'revive',
    onRevive: function () { revived++; }, onGiveUp: function () { gaveUp++; }});
  env.flush();
  tap(env, page, 'watchAd'); env.clock.advance(100); env.tapNode(page.button('watchAd').node);
  tap(env, page, 'watchAd');
  assert.strictEqual(ads.calls.length, 1, 'one request while the ad runs');
  assert.strictEqual(ads.calls[0].placementKey, 'revive');
  assert.deepStrictEqual(s.reasons().sort(), ['ad', 'popup']);
  tap(env, page, 'noThanks');
  assert.strictEqual(gaveUp, 0, 'NO THANKS waits for the ad');
  ads.answer(CLOSED); await settle();
  assert.strictEqual(revived, 0, 'closed early: no revive');
  assert.ok(page.isOpen(), 'page stays for another try');
  assert.strictEqual(env.Kit.toastText(), CLOSED.message);
  assert.deepStrictEqual(s.reasons(), ['popup'], 'ad pause given back');
  tap(env, page, 'watchAd');
  ads.answer(WATCHED); await settle(); after(env);
  assert.strictEqual(revived, 1);
  assert.strictEqual(s.isPaused(), false, 'running after the revive');
  assert.ok(page.root.active === false);
  page.open(); env.flush();
  tap(env, page, 'watchAd');
  page.close();                                                 // page closed while the ad plays
  ads.answer(WATCHED); await settle();
  assert.strictEqual(revived, 1, 'a late result after the page closed pays nothing');
  assert.strictEqual(s.isPaused(), false, 'and holds no pause');
  page.open(); env.flush(); tap(env, page, 'noThanks'); after(env);
  assert.strictEqual(gaveUp, 1);
  assert.throws(function () { env.Kit.revivePage(env.canvas, {onRevive: function () {}, onGiveUp: function () {}}); }, /RewardedService/);
  // old way: revive on any ad close (rewarded never read)
  var oldRevived = 0, ads2 = fakeAds();
  ads2.request({placementKey: 'revive'}).then(function () { oldRevived++; });
  ads2.answer(CLOSED); await settle();
  assert.strictEqual(oldRevived, 1, 'OLD WAY BUG: a video closed after 2 s still revives');
});

test('5 result x2: grant when the save has it, else update; a failed save stays on the page; never pays twice', async function () {
  var env = fresh(), s = session(env), ads = fakeAds(), grants = [], next = 0, claimed = [];
  s.newRun(function () { return {}; });
  var store = {grant: function (d, done) { grants.push(d); done(); return {ok: true}; }, update: function () { throw new Error('update used'); }};
  var page = env.Kit.resultPage(env.canvas, {session: s, store: store, amount: 30, ads: ads, placementKey: 'result_x2',
    onClaimed: function (i) { claimed.push(i); }, onNext: function () { next++; }, onHome: function () {}});
  env.flush();
  assert.strictEqual(page.grantMode, 'grant');
  tap(env, page, 'double'); ads.answer(WATCHED); await settle();
  assert.strictEqual(JSON.stringify(grants), JSON.stringify([{id: 'run:1:result', add: {coins: 60}}]));
  tap(env, page, 'claim'); tap(env, page, 'next'); after(env);
  assert.strictEqual(grants.length, 1, 'x2 then CLAIM / NEXT pays once');
  assert.strictEqual(next, 1);
  assert.deepStrictEqual(claimed.map(function (c) { return [c.amount, c.doubled]; }), [[60, true]]);
  // a save with only update (SaveStore before I1)
  var env2 = fresh(), save = {coins: 5}, fail = true, home = 0;
  var store2 = {update: function (m) { if (fail) return {ok: false, error: 'write_failed'}; var d = {coins: save.coins}; m(d); save = d; return {ok: true}; }};
  var p2 = env2.Kit.resultPage(env2.canvas, {store: store2, amount: 10, double: false, onNext: function () {}, onHome: function () { home++; }});
  env2.flush();
  assert.strictEqual(p2.grantMode, 'update');
  assert.strictEqual(p2.button('double'), null, 'double:false leaves the x2 slot empty');
  tap(env2, p2, 'home');
  assert.strictEqual(home, 0, 'save failed: stays on the page');
  assert.ok(p2.isOpen());
  assert.strictEqual(env2.Kit.toastText(), 'Could not save. Please try again.');
  fail = false;
  tap(env2, p2, 'home'); after(env2);
  assert.strictEqual(home, 1);
  assert.strictEqual(save.coins, 15, 'HOME paid the free amount first');
  assert.throws(function () { env2.Kit.resultPage(env2.canvas, {amount: 1, double: false, onNext: function () {}, onHome: function () {}}); }, /store/);
  // old way (水杯传奇 v20 result): coins in memory first, the write fails, the page leaves anyway
  var mem = {coins: 5}, left = false;
  (function claimOld() { mem.coins += 10; var r = {ok: false}; void r; left = true; })();
  assert.ok(mem.coins === 15 && left, 'OLD WAY BUG: the screen shows 15 coins and leaves, the save still has 5');
});

test('6 valueLabel: "100%" stays on one line (a box made for "50%" with wrapping takes two lines)', function () {
  var env = fresh();
  var n = node(env, 'MusicPct', 0, 0, 200, 300);
  var v = env.Kit.valueLabel(n, {longest: '100%', value: '50%', fontSize: 30});
  v.set('100%');
  var lay = S.labelLayout(v.label, n);
  assert.strictEqual(lay.lines, 1, 'one line');
  assert.ok(lay.fits, 'fits its box');
  assert.strictEqual(lay.fontSize, 30, 'no shrink needed: the box was made for the longest value');
  assert.strictEqual(v.label.enableWrapText, false);
  assert.strictEqual(v.label.overflow, env.cc.Label.Overflow.SHRINK);
  var m = node(env, 'Coins', 0, 0, 0, 0);
  var c = env.Kit.valueLabel(m, {longest: '999999', maxWidth: 80, value: 0, fontSize: 30});
  c.set('999999');
  var l2 = S.labelLayout(c.label, m);
  assert.ok(l2.lines === 1 && l2.fits && l2.fontSize < 30, 'narrow space: shrinks on one line');
  var pre = node(env, 'PrefabLabel', 40, 30); var pl = pre.addComponent(env.cc.Label); pl.fontSize = 24; pl.string = '0';
  var p = env.Kit.valueLabel(pre, {longest: '00:00:00'});
  assert.strictEqual(p.label, pl, 'uses the Label already on the node');
  assert.throws(function () { env.Kit.valueLabel(node(env, 'X', 10, 10), {}); }, /longest/);
  // old way (设置页 MUSIC 100%): sized to the current "50%", RESIZE_HEIGHT, wrapping on
  var o = node(env, 'HandPct', 0, 0); var ol = o.addComponent(env.cc.Label); ol.fontSize = 30;
  ol.overflow = env.cc.Label.Overflow.NONE; ol.string = '50%'; S.labelLayout(ol, o);
  ol.overflow = env.cc.Label.Overflow.RESIZE_HEIGHT; ol.string = '100%';
  assert.strictEqual(S.labelLayout(ol, o).lines, 2, 'OLD WAY BUG: "100%" wraps to two lines');
});

test('7 onPageOpen: one record per popup() / open() and per page opening (L2 page registry hook)', function () {
  var env = fresh(), log = [];
  env.Kit.setup({onPageOpen: function (i) { log.push(i); }});
  var p = env.Kit.popup(env.canvas, {name: 'Shop', panelFrame: env.frame(500, 600), closeFrame: env.frame(64, 64), keep: true});
  env.flush(); p.close(); env.flush(); p.open();
  var page = env.Kit.pausePage(env.canvas, {session: session(env), initRun: function () { return {}; }, closeFrame: env.frame(64, 64), onHome: function () {}});
  env.flush(); page.close(); env.flush(); page.open();
  var rv = env.Kit.revivePage(env.canvas, {ads: fakeAds(), placementKey: 'revive', onRevive: function () {}, onGiveUp: function () {}});
  void rv;
  assert.deepStrictEqual(log.map(function (i) { return [i.kind, i.page || i.name, i.opening]; }),
    [['popup', 'Shop', 1], ['popup', 'Shop', 2], ['page', 'pause', 1], ['page', 'pause', 2], ['page', 'revive', 1]]);
  eq(log[2].buttons, ['resume', 'restart', 'home']);
  eq(log[2].slots, ['resume', 'restart', 'home', 'extra']);
  assert.strictEqual(log[2].close, 'Close');
  eq(log[4].ads, [{slot: 'watchAd', placementKey: 'revive'}]);
  env.Kit.setup({onPageOpen: null});
});

test('8 sounds through AudioService (setup({audio})), a set sfx wins; X of the pause page resumes (never a silent close)', function () {
  var env = fresh(), played = [], s = session(env), resumed = 0;
  env.Kit.setup({audio: {playSfx: function (id) { played.push(id); }}});
  s.newRun(function () { return {}; });
  var page = env.Kit.pausePage(env.canvas, {session: s, initRun: function () { return {}; }, closeFrame: env.frame(64, 64),
    onResume: function () { resumed++; }, onHome: function () {}});
  env.flush();
  env.clock.advance(600); env.tapNode(page.popup.closeNode); after(env);
  assert.strictEqual(resumed, 1, 'X = Resume');
  assert.strictEqual(s.isPaused(), false);
  assert.ok(played.indexOf('ui_popup_open') >= 0 && played.indexOf('ui_popup_close') >= 0, played.join(','));
  var mine = [];
  env.Kit.setup({sfx: function (id) { mine.push(id); }});
  page.open(); env.flush(); tap(env, page, 'resume');
  assert.ok(mine.indexOf('ui_button_tap') >= 0, 'sfx set: it plays');
  env.Kit.setup({sfx: null, audio: null});
  // old way (甜点消消乐 pause X): the X only hid the popup and kept the game paused
  var g = {paused: true}, hidden = false;
  (function onX() { hidden = true; })();
  assert.ok(hidden && g.paused, 'OLD WAY BUG: popup gone, game still paused');
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
  console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit pages + valueLabel, ' + KINDS.join(' + ') + ', Node stand-in; 待真机复测)');
  if (failed) process.exitCode = 1;
})();
