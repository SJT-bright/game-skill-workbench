'use strict';
// node tests/game-ui-frame-release.test.js   (GameUIKit 1.1.7, 生成时预防 R4R4, 问题普查 补读 P3/P6 第 8 组补充)
// 火箭三消: "先打开设置/音量，之后复活变空壳". The original settings panel put a close picture of its own prefab into
// GameUIKit.config().closeFrame; closing settings released the prefab with its pictures, and the next popup (revive)
// built its Close from the destroyed frame - Cocos 2.4 throws there and the popup stops half built.
// (A path the code allows, from the AI's source reading; not reproduced on a phone.)
// The stand-in engine here throws like the engine when a Sprite gets a released frame. A released frame: cc.isValid
// false and no texture. Cases:
//  1. config().closeFrame swapped by a page and released -> the next popup still has a Close, with the start-up picture;
//  2. no other picture -> the kit draws its own X (Close still there, nothing released handed to a Sprite);
//  3. config() / setup() hold the picture with addRef() and give the replaced one back with decRef(false);
//  4. released panel / toast / digit pictures do not stop a popup, a toast or a number.
// GAMEUI_KINDS=24 or 3x picks one engine (default both); GAMEUI_KIT_FILE / GAMEUI_KIT_3X_FILE run the cases on
// another copy (the 1.1.6 kit must fail).
var assert = require('assert');
var S = require('./engine-stub-ui');

var KINDS = (process.env.GAMEUI_KINDS || '24,3x').split(',');
var cases = [];
function test(name, fn) { cases.push({name: name, fn: fn}); }

// A loaded picture of a prefab: counts refs, release() destroys it as the asset manager does.
function asset(env, kind, w, h, name) {
  var f = env.frame(w, h, name);
  var tex = new env.cc.Texture2D(w, h);
  if (kind === '24') { f._texture = tex; f.getTexture = function () { return f._texture; }; } else f.texture = tex;
  f.refs = 0; f.decRefArgs = [];
  f.addRef = function () { f.refs++; return f; };
  f.decRef = function (auto) { f.refs--; f.decRefArgs.push(auto); return f; };
  f.release = function () { f._valid = false; tex._valid = false; if (kind === '24') f._texture = null; else f.texture = null; };
  return f;
}
// Like the engine: a Sprite given a released frame throws (2.4: spriteFrame.textureLoaded() on a null texture).
function strictSprites(env) {
  Object.defineProperty(env.cc.Sprite.prototype, 'spriteFrame', {configurable: true,
    get: function () { return this._sf || null; },
    set: function (v) {
      if (v && !env.cc.isValid(v)) throw new Error("Cannot read properties of null (reading 'loaded')");
      this._sf = v;
    }});
}
function find(n, name) {
  if (!n) return null;
  if (n.name === name) return n;
  for (var i = 0; i < n.children.length; i++) { var r = find(n.children[i], name); if (r) return r; }
  return null;
}
function spritesOk(env, n) {
  var bad = [];
  (function walk(x) {
    var s = x.getComponent(env.cc.Sprite);
    if (s && s.spriteFrame && !env.cc.isValid(s.spriteFrame)) bad.push(x.name);
    x.children.forEach(walk);
  })(n);
  return bad;
}

test('1 settings swapped config().closeFrame and was released: revive still gets a Close with the start-up picture', function (env, kind) {
  var boot = asset(env, kind, 64, 64, 'ui_close');
  env.Kit.setup({closeFrame: boot});
  var own = asset(env, kind, 60, 60, 'settings_close');           // 火箭三消 设置面板 OnOpen()
  env.Kit.config().closeFrame = own;
  var settings = env.Kit.popup(env.canvas, {name: 'Settings', panelFrame: env.frame(560, 700)});
  env.flush(); settings.close(); env.flush();
  own.release();                                                   // prefab released with its pictures
  var revive;
  assert.doesNotThrow(function () { revive = env.Kit.popup(env.canvas, {name: 'Revive', panelFrame: env.frame(560, 700)}); },
    'popup() threw on the released close picture (revive half built)');
  env.flush();
  var close = find(revive.root, 'Close');
  assert.ok(close, 'revive has no Close');
  var icon = find(close, 'Icon');
  assert.ok(icon, 'Close has no Icon');
  var s = icon.getComponent(env.cc.Sprite);
  assert.ok(s && s.spriteFrame === boot, 'Close does not use the start-up close picture');
  assert.deepStrictEqual(spritesOk(env, revive.root), []);
  assert.ok(env.cc.warnings.some(function (m) { return /released/.test(m); }), 'no warning logged');
  assert.strictEqual(typeof env.Kit.frameIssues, 'function');
  assert.strictEqual(env.Kit.frameIssues().length, 1, 'logged once');
  // the dead frame is not handed to the next popup either
  var next = env.Kit.popup(env.canvas, {name: 'Result', panelFrame: env.frame(560, 700)});
  assert.ok(find(next.root, 'Close'));
  assert.strictEqual(env.Kit.frameIssues().length, 1, 'the released frame was checked again for the next popup');
});

test('2 only a released picture is left: the kit draws its own X, the Close still works', function (env, kind) {
  var own = asset(env, kind, 60, 60, 'settings_close');
  env.Kit.config().closeFrame = own;
  own.release();
  var p;
  assert.doesNotThrow(function () { p = env.Kit.popup(env.canvas, {name: 'Revive', panelFrame: env.frame(560, 700)}); }, 'popup() threw');
  env.flush();
  var close = find(p.root, 'Close');
  assert.ok(close, 'no Close (popup cannot be closed)');
  assert.ok(close.width >= 104 && close.height >= 104, 'Close hit area under 104');
  assert.ok(find(close, 'Plate') && find(close, 'Bar0') && find(close, 'Bar1'), 'no drawn X');
  assert.deepStrictEqual(spritesOk(env, p.root), []);
  close.emit('touch-end', {}); env.flush();
  assert.strictEqual(p.root.active, false, 'tapping the drawn X did not close the popup');
  // closeFrame: false still means no close button
  var q = env.Kit.popup(env.canvas, {name: 'NoClose', closeFrame: false});
  assert.strictEqual(find(q.root, 'Close'), null);
});

test('3 config() and setup() hold the picture (addRef) and give the replaced one back (decRef(false))', function (env, kind) {
  var a = asset(env, kind, 64, 64, 'a'), b = asset(env, kind, 64, 64, 'b'), c = asset(env, kind, 64, 64, 'c');
  env.Kit.setup({closeFrame: a});
  assert.ok(a.refs >= 1, 'setup() did not addRef the close picture');
  var aRefs = a.refs;
  env.Kit.config().closeFrame = b;
  assert.strictEqual(b.refs, 1, 'config().closeFrame = b did not addRef b');
  assert.strictEqual(a.refs, aRefs - 1, 'the replaced picture was not given back');
  env.Kit.config({closeFrame: c});
  assert.strictEqual(b.refs, 0);
  assert.deepStrictEqual(b.decRefArgs, [false], 'decRef must not auto-release (decRef(false))');
  assert.strictEqual(c.refs, 1);
  var t = asset(env, kind, 200, 60, 'toast');
  env.Kit.setup({toastFrame: t});
  assert.strictEqual(t.refs, 1, 'toastFrame not held');
  var g = asset(env, kind, 20, 30, 'g0');
  env.Kit.setup({digitFrames: {light: {'0': g}}});
  assert.strictEqual(g.refs, 1, 'digitFrames not held');
  env.Kit.setup({digitFrames: null});
  assert.strictEqual(g.refs, 0);
  // engines without refs: plain frames work as before
  env.Kit.setup({closeFrame: env.frame(64, 64)});
});

test('4 released panel / toast / digit pictures: popup, toast and number are still built', function (env, kind) {
  var panel = asset(env, kind, 560, 700, 'panel'), toast = asset(env, kind, 200, 60, 'toast'), g = asset(env, kind, 20, 30, 'g1');
  env.Kit.setup({closeFrame: asset(env, kind, 64, 64, 'x'), toastFrame: toast, digitFrames: {light: {'1': g, '2': env.frame(20, 30)}}});
  panel.release(); toast.release(); g.release();
  var p;
  assert.doesNotThrow(function () { p = env.Kit.popup(env.canvas, {name: 'Shop', panelFrame: panel, width: 560, height: 700}); }, 'popup() threw on a released panel');
  env.flush();
  assert.ok(find(p.root, 'Close'), 'no Close');
  assert.doesNotThrow(function () { env.Kit.toast('Saved'); }, 'toast threw on a released background');
  assert.strictEqual(env.Kit.toastText(), 'Saved');
  assert.doesNotThrow(function () { env.Kit.digits(env.canvas, {value: 12}); }, 'digits threw on a released glyph');
});

var failed = 0;
KINDS.forEach(function (kind) {
  cases.forEach(function (c) {
    var env = S.loadKit(kind); env.Kit._reset(); env.cc.warnings.length = 0; strictSprites(env);
    try { c.fn(env, kind); console.log('PASS [' + kind + '] ' + c.name); }
    catch (e) { failed++; console.log('FAIL [' + kind + '] ' + c.name + ': ' + (e && e.message)); }
  });
});
console.log(failed ? '\n' + failed + ' failed' : '\nall ' + cases.length * KINDS.length + ' passed (GameUIKit 1.1.7 released pictures, 24 + 3x, Node stand-in; 待真机复测)');
process.exitCode = failed ? 1 : 0;
