'use strict';
// node tests/game-ui-text-guide.test.js   (生成时预防 R4N4, 问题普查 补查2 第 3 / 9 / 10 组 + 第 5 节)
// GameUIKit 1.1.4 UI.text (box, overflow and wrap before the font and the text), page templates forwarding titleSize,
// UI.guide (tutorial hand placed from the target's world position after every layout), and RunSession 1.2 track()
// (newRun stops only the registered tween targets). Every case also runs the old way taken from the census and shows
// the bug. GAMEUI_KINDS=24 or 3x picks one engine (default both); GAMEUI_KIT_FILE / GAMEUI_KIT_3X_FILE / RUN_SESSION_FILE
// run the same cases on another copy (the pre-R4N4 part must fail).
var assert = require('assert');
var path = require('path');
var S = require('./engine-stub-ui');

var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }

// Records, in order, every setter the code calls on a new Label and the node's width at the moment of each call.
function recordLabels(env) {
  var log = [];
  var orig = env.cc.Node.prototype.addComponent;
  env.cc.Node.prototype.addComponent = function (C) {
    var c = orig.call(this, C);
    if (C !== env.cc.Label) return c;
    var node = this;
    ['string', 'overflow', 'enableWrapText', 'fontSize', 'lineHeight', 'font'].forEach(function (k) {
      var v = c[k];
      Object.defineProperty(c, k, {get: function () { return v; },
        set: function (x) { v = x; log.push({key: k, width: node.width, value: x}); }, configurable: true});
    });
    return c;
  };
  return log;
}
function firstIndex(log, key) { for (var i = 0; i < log.length; i++) if (log[i].key === key) return i; return -1; }
// the order the kit promises: overflow and wrap set, and the node already its box width, before the first text
function setBeforeText(log, w) {
  var s = firstIndex(log, 'string'), o = firstIndex(log, 'overflow'), wr = firstIndex(log, 'enableWrapText'), f = firstIndex(log, 'fontSize');
  return s >= 0 && o >= 0 && o < s && wr >= 0 && wr < s && f >= 0 && f < s && log[s].width === w;
}
var RULES = 'Tap two matching tiles to clear them. Clear the whole board before the timer runs out to win the level.';

// SLS35 settings / shop body text, the old way: Label made, text and font first, CLAMP and wrap afterwards
function oldBodyText(env, parent) {
  var n = new env.cc.Node('Rules'); parent.addChild(n);
  var l = n.addComponent(env.cc.Label);
  l.string = RULES;
  l.fontSize = 28;
  l._forceUpdateRenderData();               // the engine lays the label out on the next frame (here: now)
  l.overflow = env.cc.Label.Overflow.CLAMP;
  l.enableWrapText = true;
  return {node: n, label: l};
}

test('UI.text sets box, overflow and wrap before the font and the text; the node keeps its width', function (env) {
  var log = recordLabels(env);
  var t = env.Kit.text(env.canvas, {w: 480, h: 220, text: RULES, overflow: 'clamp', fontSize: 28});
  assert.ok(setBeforeText(log, 480), 'setter order: ' + log.map(function (x) { return x.key + '@' + x.width; }).join(', '));
  t.label._forceUpdateRenderData();
  assert.strictEqual(t.node.width, 480, 'UI.text node width after layout');
  assert.strictEqual(t.label.overflow, env.cc.Label.Overflow.CLAMP);
  assert.strictEqual(t.label.enableWrapText, true);
  t.set('Short.');
  t.label._forceUpdateRenderData();
  assert.strictEqual(t.node.width, 480, 'set() keeps the box');
  // the old way: text first under NONE, the node is sized to the text (about 1.5 screens)
  var log2 = recordLabels(env);
  var old = oldBodyText(env, env.canvas);
  assert.ok(!setBeforeText(log2, 480), 'old way must show text-before-overflow');
  assert.ok(old.node.width > 720, 'old way node width ' + old.node.width + ' (> one screen of 720)');
});

test('UI.text refuses NONE and a missing box; resize keeps the width and grows the height', function (env) {
  assert.throws(function () { env.Kit.text(env.canvas, {w: 300, h: 80, overflow: 'none', text: 'x'}); }, /overflow must be/);
  assert.throws(function () { env.Kit.text(env.canvas, {h: 80, text: 'x'}); }, /opts\.w/);
  assert.throws(function () { env.Kit.text(env.canvas, {w: 300, text: 'x'}); }, /opts\.h/);
  var t = env.Kit.text(env.canvas, {w: 300, text: RULES, overflow: 'resize', fontSize: 20, align: 'left'});
  t.label._forceUpdateRenderData();
  assert.strictEqual(t.node.width, 300);
  assert.ok(t.node.height > 25, 'RESIZE_HEIGHT grew the height: ' + t.node.height);
  assert.strictEqual(t.label.horizontalAlign, env.cc.Label.HorizontalAlign.LEFT);
  assert.strictEqual(S.renderCount(t.node), 1, 'one render component');
});

test('page templates forward titleSize to the title picture (合成进化恐龙)', function (env) {
  var page = env.Kit.pausePage(env.canvas, {titleFrame: env.frame(400, 100), titleSize: {width: 200, height: 50},
    onRestart: function () {}, onHome: function () {}, buttons: {}});
  var title = S.find(page.panel, 'Title');
  assert.ok(title, 'title node');
  assert.strictEqual(title.width, 200, 'title width from titleSize');
  assert.strictEqual(title.height, 50, 'title height from titleSize');
  var p2 = env.Kit.popup(env.canvas, {titleFrame: env.frame(400, 100), titleSize: [300, 0]});
  var t2 = S.find(p2.panel, 'Title');
  assert.strictEqual(t2.width, 300);
  assert.strictEqual(t2.height, 75, 'one side given: the other follows the picture ratio');
});

// 火箭三消 tutorial, the old way: the element is moved to an overlay once, at the world position of that moment
function oldGuide(env, target) {
  var overlay = new env.cc.Node('TutorialOverlay'); env.canvas.addChild(overlay);
  overlay.setContentSize(720, 1280);
  var w = env.worldBox(target);
  var c = env.canvas, cw = env.worldBox(c);
  var hand = new env.cc.Node('Hand'); overlay.addChild(hand);
  hand.setContentSize(target.width, target.height);
  hand.setPosition(w.x - cw.x, w.y - cw.y);
  return hand;
}

test('UI.guide follows its target after the Widget moves the page; the target keeps its parent (火箭三消 93.75)', function (env) {
  var board = new env.cc.Node('Board'); env.canvas.addChild(board); board.setContentSize(600, 600); board.setPosition(0, 200);
  var cell = new env.cc.Node('Cell'); board.addChild(cell); cell.setContentSize(100, 100); cell.setPosition(50, 0);
  var g = env.Kit.guide(cell, {frame: env.frame(80, 80)});
  var hand = oldGuide(env, cell);
  env.draw();
  var a = env.worldBox(g.node), b = env.worldBox(cell);
  assert.ok(Math.abs(a.x - b.x) < 0.01 && Math.abs(a.y - b.y) < 0.01, 'guide on the target at start');
  // the Widget aligns the page for a taller phone (the board moves up 93.75 design units), then the frame is drawn
  board.setPosition(0, 293.75);
  env.draw();
  a = env.worldBox(g.node); b = env.worldBox(cell);
  assert.ok(Math.abs(a.x - b.x) < 0.01 && Math.abs(a.y - b.y) < 0.01, 'guide follows: ' + JSON.stringify([a, b]));
  assert.strictEqual(cell.parent, board, 'target was not moved to another parent');
  var h = env.worldBox(hand);
  assert.ok(Math.abs(h.y - b.y - (-93.75)) < 0.01, 'old way stays 93.75 off: ' + (h.y - b.y));
  // scaled parent
  board.setScale(0.5); env.draw();
  a = env.worldBox(g.node); b = env.worldBox(cell);
  assert.ok(Math.abs(a.x - b.x) < 0.01 && Math.abs(a.y - b.y) < 0.01, 'guide follows a scaled board');
  // close stops following and removes the guide; a destroyed target closes it
  assert.strictEqual(g.close(), true);
  assert.strictEqual(g.isOpen(), false);
  var g2 = env.Kit.guide(cell, {});
  cell.destroy(); env.draw();
  assert.strictEqual(g2.isOpen(), false, 'guide closed itself with its target');
  assert.throws(function () { env.Kit.guide(null, {}); }, /no valid target/);
});

// ---- RunSession 1.2 (engine-neutral: one run per file)
function loadRunSession() {
  var file = process.env.RUN_SESSION_FILE ? path.resolve(process.env.RUN_SESSION_FILE) : path.join(__dirname, '..', 'parts', 'RunSession.js');
  delete require.cache[require.resolve(file)];
  return require(file);
}
function fakeCc() {
  var tweens = [];
  var cc = {isValid: function (n) { return !!n && n.isValid !== false; },
    Tween: {stopAll: function () { tweens.forEach(function (t) { t.stopped = true; }); },
      stopAllByTarget: function (target) { tweens.forEach(function (t) { if (t.target === target) t.stopped = true; }); }}};
  cc.tween = function (target) { var t = {target: target, stopped: false}; tweens.push(t); return t; };
  return cc;
}
function runSessionCase() {
  var RS = loadRunSession();
  var cc = fakeCc();
  var boardNode = {name: 'Board', stopAllActions: function () { boardNode.actionsStopped = true; }};
  var popupNode = {name: 'ResultPopup'};
  var s = RS.create(cc, {autoHide: false, sceneBound: false});
  assert.strictEqual(typeof s.track, 'function', 'session.track (RunSession 1.2)');
  s.track(boardNode);
  var boardTween = cc.tween(boardNode), popupTween = cc.tween(popupNode);
  s.newRun(function () { return {score: 0}; });
  assert.strictEqual(boardTween.stopped, true, 'the run\'s tween stopped on newRun');
  assert.strictEqual(boardNode.actionsStopped, true, 'the run node\'s actions stopped');
  assert.strictEqual(popupTween.stopped, false, 'the popup closing tween keeps running');
  s.untrack(boardNode);
  var t2 = cc.tween(boardNode); s.stopTracked();
  assert.strictEqual(t2.stopped, false, 'untracked node not stopped');
  // the old way (SLS35 Retry / Home): the global stop also kills the popup's closing tween
  var cc2 = fakeCc(), pt = cc2.tween(popupNode);
  cc2.Tween.stopAll();
  assert.strictEqual(pt.stopped, true, 'old way kills the popup tween');
}

var failed = 0;
KINDS.forEach(function (kind) {
  cases.forEach(function (c) {
    var env = S.loadKit(kind); env.Kit._reset();
    try { c.fn(env); console.log('ok   [' + kind + '] ' + c.name); }
    catch (e) { failed++; console.log('FAIL [' + kind + '] ' + c.name + '\n     ' + (e && e.message)); }
  });
});
try { runSessionCase(); console.log('ok   RunSession.track: newRun stops only the registered targets (SLS35 Tween.stopAll)'); }
catch (e) { failed++; console.log('FAIL RunSession.track\n     ' + (e && e.message)); }
console.log(failed ? '\n' + failed + ' failed' : '\nall passed');
if (failed) process.exitCode = 1;
