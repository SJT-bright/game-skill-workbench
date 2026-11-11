'use strict';
// Test helper for test_p21b_p13_preview.py (no real browser): a tiny DOM with capture / bubble phases, a canvas and
// a non-canvas overlay. argv[2]: path of preview-touch-bridge.js, or "none" (the 11.12 phone page: no bridge).
// Drags the mouse on the canvas, clicks the overlay, prints JSON of what the game's listeners received.
const fs = require('fs');
const path = require('path');
class N {
  constructor(tag, parent) { this.tagName = tag; this.parentNode = parent || null; this.l = {}; }
  addEventListener(type, fn, capture) { (this.l[type] = this.l[type] || []).push({fn, capture: !!(capture && (capture === true || capture.capture))}); }
  dispatchEvent(ev) {
    const chain = []; for (let n = this; n; n = n.parentNode) chain.push(n);
    ev.target = this; ev._stop = false;
    ev.stopImmediatePropagation = () => { ev._stop = true; };
    ev.stopPropagation = () => { ev._stop = true; };
    ev.preventDefault = () => { ev.defaultPrevented = true; };
    const call = (n, capture) => { for (const x of (n.l[ev.type] || []).slice()) { if (ev._stop) return; if (x.capture === capture || n === this) x.fn.call(n, ev); } };
    for (let i = chain.length - 1; i > 0 && !ev._stop; i--) call(chain[i], true);
    if (!ev._stop) call(this, null);
    for (let i = 1; i < chain.length && !ev._stop && ev.bubbles; i++) call(chain[i], false);
    return !ev.defaultPrevented;
  }
}
const win = new N('#window', null);
const doc = new N('#document', win);
doc.documentElement = new N('HTML', doc);
const body = new N('BODY', doc.documentElement);
const canvas = new N('CANVAS', body);
const overlay = new N('DIV', body);
doc.createEvent = () => ({initEvent(type, bubbles, cancelable) { this.type = type; this.bubbles = bubbles; this.cancelable = cancelable; }});
// This synthetic DOM exposes the EventTarget constructor whose prototype implements its capture/bubble dispatch.
win.EventTarget = N;
win.document = doc; win.pageXOffset = 0; win.pageYOffset = 0;
const got = [];
['touchstart', 'touchmove', 'touchend', 'touchcancel', 'mousedown', 'mousemove', 'mouseup'].forEach((t) => {
  canvas.addEventListener(t, (e) => {
    const c = e.changedTouches && e.changedTouches[0];
    got.push(c ? {on: 'canvas', type: t, identifier: c.identifier, clientX: c.clientX, clientY: c.clientY, screenX: c.screenX,
      screenY: c.screenY, touches: e.touches.length, raw: c} : {on: 'canvas', type: t});
  });
  overlay.addEventListener(t, (e) => got.push({on: 'overlay', type: t}));
});
if (!process.argv[2] || process.argv[2] === '--help' || process.argv[2] === '-h') {  // R4I1: usage, never a crash
  console.log('usage: node preview_touch_fakedom.cjs <path of preview-touch-bridge.js | none>  (test helper of test_p21b_p13_preview.py)');
  process.exit(process.argv[2] ? 0 : 2);
}
const bridge = process.argv[2];
if (bridge !== 'none') new Function('window', fs.readFileSync(bridge, 'utf8'))(win);
const mouse = (target, type, x, y) => target.dispatchEvent({type, bubbles: true, cancelable: true, button: 0, clientX: x, clientY: y,
  screenX: x + 1000, screenY: y + 600});
mouse(canvas, 'mousedown', 100, 200); mouse(canvas, 'mousemove', 150, 200); mouse(canvas, 'mousemove', 200, 210); mouse(canvas, 'mouseup', 200, 210);
mouse(canvas, 'mousedown', 50, 60); mouse(canvas, 'mouseup', 50, 60);
mouse(overlay, 'mousedown', 10, 10); mouse(overlay, 'mouseup', 10, 10);
// the platform kit touch parts must read the converted touches unchanged
const kit = path.join(__dirname, '..', 'assets', 'platform-kit', 'build-templates');
const touch3x = require(path.join(kit, 'bytedance-mini-game', 'tiktok-touch-3x.js'));
const kitRead = got.filter((g) => g.raw).map((g) => { const p = touch3x.normalizePoint(g.raw); return [p.identifier, p.clientX, p.clientY]; });
got.forEach((g) => { delete g.raw; });
console.log(JSON.stringify({touchCapable: 'ontouchstart' in doc.documentElement, events: got, kitRead}));
