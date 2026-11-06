'use strict';
// node tests/game-ui-kit.test.js   (生成时预防 P05: parts/GameUIKit.js, Cocos 2.4, and parts-3x/GameUIKit.ts, Cocos 3.x)
// A2 批: every case runs on both engines (GAMEUI_KINDS=24 or 3x picks one); the hand-written copies are the same.
// Each case runs the kit AND a "hand-written the old way" copy taken from the census (问题普查 20261104): the kit must
// pass, the hand-written copy must show the bug. Taps go through env.tapAt (topmost active touch node, like 2.4).
var assert = require('assert');
var S = require('./engine-stub-ui');

var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }
var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var KIND = KINDS[0];
function fresh() { var env = S.loadKit(KIND); env.Kit._reset(); return env; }
function node(env, name, w, h, x, y, parent) {
  var n = new env.cc.Node(name); (parent || env.canvas).addChild(n);
  n.setContentSize(w, h); n.setPosition(x || 0, y || 0); return n;
}
function homeButton(env) {
  var calls = {n: 0};
  var n = node(env, 'Home', 240, 100, 0, -300);
  env.Kit.button(n, function () { calls.n++; }, {name: 'Home'});
  return {node: n, calls: calls};
}
function popup(env, o) {
  o = o || {};
  var p = env.Kit.popup(env.canvas, {panelFrame: env.frame(560, 700), closeFrame: env.frame(o.close || 64, o.close || 64), keep: o.keep});
  env.flush();
  return p;
}

// ---- hand-written copies (the old way)
// 花园守卫者 / 星星点点消: popup with its own mask; closing only fades it out (node stays active)
function handPopup(env, blockInput) {
  var root = node(env, 'HandPopup', 720, 1280);
  root.zIndex = 30000;
  var mask = node(env, 'Mask', 720, 1280, 0, 0, root);
  mask.addComponent(env.cc.Sprite);                         // a dim picture
  if (blockInput) mask.addComponent(env.cc.BlockInputEvents);
  return {root: root, mask: mask,
    close: function () { env.cc.tween(root).to(0.16, {opacity: 0}).start(); },       // fade only
    rebuild: function () { root.destroy(); return handPopup(env, blockInput); }};
}
// 割草 revive: handler bound by name, the method does not exist; Cocos 2.4 EventHandler skips it silently
function bindByName(n, comp, name) {
  n.on('touch-end', function () { var f = comp[name]; if (typeof f === 'function') f.call(comp); });
}
// cc.Button as the engine runs it: clickEvents on touch-end, SCALE transition while pressed
function engineButton(env, n, events, scale) {
  var b = n.addComponent(env.cc.Button);
  b.clickEvents = events; b.transition = scale ? env.cc.Button.Transition.SCALE : env.cc.Button.Transition.COLOR;
  n.on('touch-start', function () { if (b.transition === env.cc.Button.Transition.SCALE) n.scale = 0.9; });
  n.on('touch-end', function () { (b.clickEvents || []).forEach(function (e) { e(); }); n.scale = 1; });
  return b;
}
// engine: a Sprite whose sizeMode is not CUSTOM resizes its node to every new frame (animation)
function playFrame(env, n, frame) {
  var s = n.getComponent(env.cc.Sprite); s.spriteFrame = frame;
  if (s.sizeMode !== env.cc.Sprite.SizeMode.CUSTOM) n.setContentSize(frame.getOriginalSize());
}

test('1 popup open: a tap on the page underneath is swallowed (hand mask without BlockInputEvents lets it through)', function () {
  var env = fresh(), home = homeButton(env);
  var p = popup(env);
  assert.ok(env.tapAt(0, -300) === p.mask, 'the mask takes the tap');
  assert.strictEqual(home.calls.n, 0);
  var env2 = fresh(), home2 = homeButton(env2);
  handPopup(env2, false);
  env2.tapAt(0, -300);
  assert.strictEqual(home2.calls.n, 1, 'OLD WAY BUG: hand mask without BlockInputEvents passes the tap to Home');
});

test('2 close(): after the 160 ms fade the popup is inactive and the page works (hand fade-out keeps blocking)', function () {
  [false, true].forEach(function (keep) {
    var env = fresh(), home = homeButton(env);
    var p = popup(env, {keep: keep});
    p.close();
    env.clock.advance(160); env.flush();
    assert.ok(!env.cc.isValid(p.root) || p.root.active === false, 'popup root inactive (keep ' + keep + ')');
    env.clock.advance(600);
    env.tapAt(0, -300);
    assert.strictEqual(home.calls.n, 1, 'Home works after close (keep ' + keep + ')');
  });
  var env2 = fresh(), home2 = homeButton(env2);
  var h = handPopup(env2, true);
  h.close(); env2.flush();
  assert.strictEqual(h.root.opacity, 0, 'hand popup is invisible');
  env2.tapAt(0, -300);
  assert.strictEqual(home2.calls.n, 0, 'OLD WAY BUG: the invisible hand popup still swallows the tap');
});

test('3 two taps within 100 ms call the handler once (plain node.on calls it twice)', function () {
  var env = fresh(), home = homeButton(env);
  env.tapAt(0, -300); env.clock.advance(100); env.tapAt(0, -300);
  assert.strictEqual(home.calls.n, 1);
  env.clock.advance(500); env.tapAt(0, -300);
  assert.strictEqual(home.calls.n, 2, 'a tap after 500 ms works again');
  var n = 0, b = node(env, 'HandClaim', 200, 90, 0, 300);
  b.on('touch-end', function () { n++; });
  env.tapAt(0, 300); env.clock.advance(100); env.tapAt(0, 300);
  assert.strictEqual(n, 2, 'OLD WAY BUG: hand button pays twice');
});

test('4 a missing handler throws when the page is built (bind-by-name stays silent and does nothing)', function () {
  var env = fresh();
  var comp = {onReviveAd: function () {}};
  var n = node(env, 'Revive', 300, 110);
  assert.throws(function () { env.Kit.button(n, comp.onRevive, {name: 'Revive'}); }, /handler of "Revive" is undefined/);
  assert.throws(function () { env.Kit.button(n, 'onRevive'); }, /is string/);
  assert.throws(function () { env.Kit.wrapExisting(n, undefined); }, /wrapExisting/);
  var ran = 0, m = node(env, 'HandRevive', 300, 110, 0, 200);
  comp.onReviveAd = function () { ran++; };
  assert.doesNotThrow(function () { bindByName(m, comp, 'onRevive'); }, 'old way: no error when binding');
  env.tapAt(0, 200);
  assert.strictEqual(ran, 0, 'OLD WAY BUG: tap does nothing and nobody is told');
});

test('5 keep:true reopens the same nodes (hand rebuild creates and destroys a whole page each time)', function () {
  var env = fresh();
  var p = popup(env, {keep: true});
  p.close(); env.flush();
  var created = env.stats.created, destroyed = env.stats.destroyed;
  for (var i = 0; i < 3; i++) { assert.strictEqual(p.open(), true); env.flush(); p.close(); env.flush(); }
  assert.strictEqual(env.stats.created, created, 'no node created on reopen');
  assert.strictEqual(env.stats.destroyed, destroyed, 'no node destroyed on close');
  var env2 = fresh(), h = handPopup(env2, true), c0 = env2.stats.created;
  for (var j = 0; j < 3; j++) h = h.rebuild();
  assert.ok(env2.stats.created > c0, 'OLD WAY BUG: rebuild makes new nodes every time (flash frame)');
});

test('6 close X hit area >= 104 x 104 from a 32 px picture (hand 32 x 32 X misses a finger 40 px off)', function () {
  var env = fresh();
  var p = popup(env, {close: 32});
  assert.ok(p.closeNode.width >= 104 && p.closeNode.height >= 104, 'close hit area ' + p.closeNode.width);
  var b = env.worldBox(p.closeNode);
  assert.strictEqual(env.tapAt(b.x - 40, b.y - 40), p.closeNode, 'a tap 40 px off the X centre still closes');
  var x = node(env, 'X', 32, 32, 200, 500);
  env.Kit.button(x, function () {}, {close: true});
  assert.ok(x.width >= 104 && x.height >= 104, 'UI.button close:true widens a 32 px X');
  var env2 = fresh(), hx = node(env2, 'HandX', 32, 32, 200, 500), hit = 0;
  hx.on('touch-end', function () { hit++; });
  env2.tapAt(240, 540);
  assert.strictEqual(hit, 0, 'OLD WAY BUG: a 32 px X misses a finger 40 px off');
});

test('7 press keeps the hit area: no press scale, animation frames do not resize the button', function () {
  var env = fresh(), n = node(env, 'Play', 300, 120, 0, 0), calls = 0;
  n.addComponent(env.cc.Sprite).sizeMode = env.cc.Sprite.SizeMode.TRIMMED;
  env.Kit.button(n, function () { calls++; });
  var before = env.worldBox(n);
  n.emit('touch-start');
  assert.ok(env.hitNode(145, 0) === n, 'edge of the button still hit while pressed');
  env.tapAt(0, 0);
  assert.strictEqual(n.scale, 1, 'no scale on press');
  playFrame(env, n, env.frame(420, 260));                 // glow frame of the idle animation
  assert.deepStrictEqual(env.worldBox(n), before, 'hit area unchanged by the animation frame');
  assert.strictEqual(calls, 1);
  var env2 = fresh(), m = node(env2, 'HandPlay', 300, 120, 0, 0);
  m.addComponent(env2.cc.Sprite).sizeMode = env2.cc.Sprite.SizeMode.TRIMMED;
  engineButton(env2, m, [function () {}], true);
  m.emit('touch-start');
  assert.strictEqual(env2.hitNode(145, 0), null, 'OLD WAY BUG: SCALE transition shrinks the button under the finger');
  playFrame(env2, m, env2.frame(420, 260));
  assert.notDeepStrictEqual(env2.worldBox(m), {x: 0, y: 0, width: 300, height: 120}, 'OLD WAY BUG: animation frame resizes the hit area');
});

test('8 popup.guard drops a late callback after close and after reopen (a plain callback writes into the closed page)', function () {
  var env = fresh();
  var p = popup(env, {keep: true}), ran = [];
  var late = p.guard(function () { ran.push('first'); });
  p.close(); env.flush();
  late();
  assert.deepStrictEqual(ran, [], 'dropped after close');
  p.open(); env.flush();
  late();
  assert.deepStrictEqual(ran, [], 'still dropped after reopen (belongs to the earlier opening)');
  p.guard(function () { ran.push('second'); })();
  assert.deepStrictEqual(ran, ['second'], 'a callback of the current opening runs');
  var env2 = fresh(), h = handPopup(env2, true), wrote = 0;
  var plain = function () { wrote++; };
  h.close(); env2.flush(); plain();
  assert.strictEqual(wrote, 1, 'OLD WAY BUG: the late callback still runs on the closed popup');
});

test('9 a disabled button explains itself (hand interactable=false does nothing)', function () {
  var env = fresh(), n = node(env, 'Claim', 260, 100, 0, 100), calls = 0, told = 0;
  var b = env.Kit.button(n, function () { calls++; }, {disabledText: 'Come back tomorrow', onDisabledTap: function () { told++; }});
  b.setEnabled(false);
  env.tapAt(0, 100);
  assert.strictEqual(calls, 0);
  assert.strictEqual(told, 1);
  assert.strictEqual(env.Kit.toastText(), 'Come back tomorrow');
  b.setEnabled(true); env.clock.advance(600); env.tapAt(0, 100);
  assert.strictEqual(calls, 1);
});

test('10 wrapExisting: an original cc.Button runs once, SCALE becomes COLOR (adding node.on beside it pays twice)', function () {
  var env = fresh(), n = node(env, 'OrigShop', 220, 90, 0, -100), old = 0, now = 0;
  n.addComponent(env.cc.Sprite).spriteFrame = env.frame(260, 110);
  var btn = engineButton(env, n, [function () { old++; }], true);
  var h = env.Kit.wrapExisting(n, function () { now++; });
  env.tapAt(0, -100);
  assert.strictEqual(now, 1); assert.strictEqual(old, 0, 'old click events are off');
  assert.strictEqual(h.oldClickEvents.length, 1, 'kept for the record');
  assert.strictEqual(btn.transition, env.cc.Button.Transition.COLOR);
  assert.deepStrictEqual([n.width, n.height], [220, 90], 'keep the laid-out size; frame pixels are not screen units');
  var env2 = fresh(), m = node(env2, 'HandShop', 220, 90, 0, -100), paid = 0;
  engineButton(env2, m, [function () { paid++; }], true);
  m.on('touch-end', function () { paid++; });
  env2.tapAt(0, -100);
  assert.strictEqual(paid, 2, 'OLD WAY BUG: original click event plus the new listener');
});

// 1.1.8: real BallMaster R14 FREE GEMS was 136x122 in its prefab, 1136x1149 in its PNG.
// These cases must fail against 1.1.7: wrapExisting used max(node size, frame pixels).
test('wrap size: Ball FREE GEMS high-resolution frame keeps the 136x122 slot and does not steal adjacent taps', function () {
  var env = fresh(), n = node(env, 'FreeDiamondBtn', 136, 122), taps = 0;
  n.addComponent(env.cc.Sprite).spriteFrame = env.frame(1136, 1149);
  env.Kit.wrapExisting(n, function () { taps++; });
  assert.deepStrictEqual([n.width, n.height], [136, 122]);
  assert.strictEqual(env.tapAt(150, 0), null, 'outside the slot must not hit FREE GEMS');
  env.tapAt(0, 0); assert.strictEqual(taps, 1);
  assert.strictEqual(n.getComponent(env.cc.Sprite).sizeMode, env.cc.Sprite.SizeMode.CUSTOM);
});
test('wrap size: explicit dimensions and a single explicit axis keep precedence', function () {
  var env = fresh(), n = node(env, 'Explicit', 136, 122);
  n.addComponent(env.cc.Sprite).spriteFrame = env.frame(1136, 1149);
  env.Kit.wrapExisting(n, function () {}, {width: 200, height: 80});
  assert.deepStrictEqual([n.width, n.height], [200, 80]);
  var m = node(env, 'PartialExplicit', 136, 122);
  m.addComponent(env.cc.Sprite).spriteFrame = env.frame(1136, 1149);
  env.Kit.wrapExisting(m, function () {}, {width: 160});
  assert.deepStrictEqual([m.width, m.height], [160, 122]);
});
test('wrap size: a zero-size host uses child display size including nested scales, not texture pixels', function () {
  var env = fresh(), n = node(env, 'ZeroHost', 0, 0), group = node(env, 'ArtGroup', 0, 0, 0, 0, n);
  group.setScale(0.5);
  var art = node(env, 'Art', 200, 72, 0, 0, group); art.setScale(0.5);
  art.addComponent(env.cc.Sprite).spriteFrame = env.frame(800, 288);
  env.Kit.wrapExisting(n, function () {}, {art: art});
  assert.deepStrictEqual([n.width, n.height], [50, 18]);
  assert.deepStrictEqual([art.width, art.height, art.scale, group.scale], [200, 72, 0.5, 0.5]);
});
test('wrap size: button() shares the child-display fallback with wrapExisting()', function () {
  var env = fresh(), n = node(env, 'ZeroHost', 0, 0), art = node(env, 'Art', 200, 72, 0, 0, n);
  art.setScale(0.5); art.addComponent(env.cc.Sprite).spriteFrame = env.frame(800, 288);
  env.Kit.button(n, function () {}, {art: art});
  assert.deepStrictEqual([n.width, n.height], [100, 36]);
});
test('wrap size: missing axes fall back independently without overwriting a valid node axis', function () {
  var env = fresh(), n = node(env, 'PartialHost', 136, 0), art = node(env, 'Art', 200, 72, 0, 0, n);
  art.setScale(0.5); art.addComponent(env.cc.Sprite).spriteFrame = env.frame(800, 288);
  env.Kit.wrapExisting(n, function () {}, {art: art});
  assert.deepStrictEqual([n.width, n.height], [136, 36]);
});
test('wrap size: frame metadata is a last resort for zero dimensions, including child scale', function () {
  var env = fresh(), n = node(env, 'ZeroFrameHost', 0, 0);
  n.addComponent(env.cc.Sprite).spriteFrame = env.frame(170, 172);
  env.Kit.wrapExisting(n, function () {});
  assert.deepStrictEqual([n.width, n.height], [170, 172]);
  var m = node(env, 'ZeroChildHost', 0, 0), art = node(env, 'Art', 0, 0, 0, 0, m);
  art.setScale(0.25); art.addComponent(env.cc.Sprite).spriteFrame = env.frame(800, 288);
  env.Kit.wrapExisting(m, function () {}, {art: art});
  assert.deepStrictEqual([m.width, m.height], [200, 72]);
});
test('wrap size: close minimum remains 104 while an independent 78x78 child X stays 78x78', function () {
  var env = fresh(), n = node(env, 'CloseHit', 78, 78), art = node(env, 'CloseArt', 78, 78, 0, 0, n), taps = 0;
  art.addComponent(env.cc.Sprite).spriteFrame = env.frame(170, 172);
  var h = env.Kit.wrapExisting(n, function () { taps++; }, {close: true, art: art});
  assert.deepStrictEqual([n.width, n.height], [104, 104]);
  assert.deepStrictEqual([art.width, art.height], [78, 78]);
  h.setEnabled(false); env.tapAt(0, 0); assert.strictEqual(taps, 0);
  h.setEnabled(true); env.clock.advance(600); env.tapAt(0, 0); assert.strictEqual(taps, 1);
});

// R4H 批 (Round4 #20, 问题普查 checker_gap 31/84, check_inputs_missing 19/20): pages.json seen_at_runtime was typed in by
// hand because no popup() / open() called PageRegistry.record. Three pages opened through the kit -> ui_dump "pages" ->
// page_registry.py merge-dumps -> all three seen_at_runtime. A hand-made popup records nothing (old way).
function mergeDumps(pagesList, ids) {
  var fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
  var dir = fs.mkdtempSync(path.join(os.tmpdir(), 'r4h-pages-'));
  fs.mkdirSync(path.join(dir, 'docs', 'logic'), {recursive: true});
  fs.mkdirSync(path.join(dir, 'docs', 'test'), {recursive: true});
  fs.writeFileSync(path.join(dir, 'docs', 'logic', 'pages.json'), JSON.stringify({schema: 'pages.v1', game: 'fixture',
    pages: ids.map(function (id) { return {id: id, name: id, kind: id === 'pause' ? 'page' : 'popup', node: 'Canvas/' + id}; })}));
  fs.writeFileSync(path.join(dir, 'docs', 'test', 'iphone14-ui-dump-1.json'), JSON.stringify({pages: pagesList}));
  var py = path.join(__dirname, '..', '..', '..', 'scripts', 'page_registry.py');
  var r = cp.spawnSync(process.env.PYTHON || 'python3', ['-B', py, 'merge-dumps', '--project', dir, '--dumps', path.join(dir, 'docs', 'test')], {encoding: 'utf8'});
  var doc = JSON.parse(fs.readFileSync(path.join(dir, 'docs', 'logic', 'pages.json'), 'utf8'));
  fs.rmSync(dir, {recursive: true, force: true});
  return {report: r.stdout, seen: doc.pages.filter(function (p) { return p.seen_at_runtime === true; }).map(function (p) { return p.id; })};
}
test('11 popup() / open() / page templates record into PageRegistry: 3 pages opened -> 3 seen_at_runtime (hand popup: none)', function () {
  var env = fresh();
  var quiet = fresh();                                   // release build (no CC_DEBUG, no __QA_PAGES): nothing recorded
  popup(quiet);
  assert.strictEqual(quiet.global.__pageRegistry, undefined, 'release build must not record');
  env.Kit.setup({pageRegistry: true});
  var shop = env.Kit.popup(env.canvas, {pageId: 'shop', name: 'Shop', panelFrame: env.frame(500, 600), closeFrame: env.frame(64, 64), keep: true});
  env.flush(); shop.close(); env.flush(); shop.open(); env.flush();
  env.Kit.popup(env.canvas, {pageId: 'settings', name: 'Settings', panelFrame: env.frame(500, 600), closeFrame: env.frame(64, 64)});
  env.flush();
  var pause = env.Kit.pausePage(env.canvas, {closeFrame: env.frame(64, 64), onRestart: function () {}, onHome: function () {}});
  env.flush(); void pause;
  var list = JSON.parse(JSON.stringify(env.global.__pageRegistry.list()));   // out of the vm realm
  assert.deepStrictEqual(list.map(function (r) { return [r.id, r.opened]; }), [['shop', 2], ['settings', 1], ['pause', 1]]);
  assert.ok(/Close$/.test(list[0].close) && list[0].node, 'record has the node path and the real close path: ' + JSON.stringify(list[0]));
  assert.deepStrictEqual(list[2].buttons, ['resume', 'restart', 'home']);
  var m = mergeDumps(list, ['shop', 'settings', 'pause']);
  assert.deepStrictEqual(m.seen, ['shop', 'settings', 'pause'], m.report);
  env.Kit.setup({pageRegistry: 'auto'});
  // old way: the same three pages built by hand (or by a kit without the hook) never reach the registry
  var env2 = fresh(); env2.global.__QA_PAGES = true;
  handPopup(env2, true); handPopup(env2, true); handPopup(env2, true);
  var none = env2.global.__pageRegistry ? env2.global.__pageRegistry.list() : [];
  assert.deepStrictEqual(mergeDumps(none, ['shop', 'settings', 'pause']).seen, [], 'OLD WAY BUG: hand popups leave seen_at_runtime to be typed in');
});
// R4J2 (lead decision 11-05): AdBoostKit builds its own popups, so they never passed popup() / open() and never reached
// the registry. UI.recordPage is the public name of the same record (Kit._pageHook stays): an ad-boost board popup is
// recorded with its id, the onPageOpen hook fires, and merge-dumps only warns for an unlisted "ad-boost:" id.
test('12 UI.recordPage: an AdBoostKit popup is recorded like popup(); unlisted ad-boost: ids only warn in merge-dumps', function () {
  var env = fresh(), opened = [];
  assert.strictEqual(typeof env.Kit.recordPage, 'function', 'OLD WAY BUG: no public UI.recordPage, AdBoostKit popups go unrecorded');
  env.Kit.setup({pageRegistry: true, onPageOpen: function (i) { opened.push(i.id); }});
  var wheel = node(env, 'AdBoostWheel', 600, 700), close = node(env, 'Close', 104, 104, 250, 300, wheel);
  env.Kit.recordPage({id: 'ad-boost:wheel', name: 'Wheel', kind: 'popup', ads: ['wheel_spin']}, wheel, close);
  env.Kit.recordPage(null, wheel);                                         // a broken call never throws
  var list = JSON.parse(JSON.stringify(env.global.__pageRegistry.list()));
  assert.deepStrictEqual(list.map(function (r) { return [r.id, r.opened]; }), [['ad-boost:wheel', 1]]);
  assert.ok(/AdBoostWheel\/Close$/.test(list[0].close), 'real close path: ' + JSON.stringify(list[0]));
  assert.deepStrictEqual(list[0].ad, ['wheel_spin']);
  assert.deepStrictEqual(opened.slice(0, 1), ['ad-boost:wheel']);
  var m = mergeDumps(list.concat([{id: 'shop'}]), ['shop']);
  var rep = JSON.parse(m.report);
  assert.strictEqual(rep.status, 'passed', m.report);
  assert.ok(rep.warnings && /record_ad_entries\.py/.test(rep.warnings[0]), m.report);
  env.Kit.setup({pageRegistry: 'auto', onPageOpen: null});
});

var failed = 0;
KINDS.forEach(function (k) {
  KIND = k;
  cases.forEach(function (c) {
    try { c.fn(); console.log('PASS [' + k + '] ' + c.name); } catch (e) { failed++; console.log('FAIL [' + k + '] ' + c.name + '\n     ' + (e && e.message)); }
  });
});
console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit ' + KINDS.join(' + ') + ', Node stand-in; 待真机复测)');
if (failed) process.exitCode = 1;
