/* 生成时预防 P13 ④ preview-touch-bridge (serve_preview.py injects it into the fixed-phone game page only; never
 * shipped, never written into the export). On a desktop the mouse is the finger: a mouse press / drag / release on
 * the game canvas becomes touchstart / touchmove / touchend (touchcancel when the window loses focus), so a game that
 * only listens to touches can be dragged in the preview (BrothersRush 2026-10-22: 「这个我鼠标划不动啊，没反应」).
 * Fields are the ones the platform kit touch parts read (touch24 / tiktok-touch-3x: identifier, clientX/clientY,
 * screenX/screenY; TouchOwner reads the engine's getID / getLocation built from them). screenX/screenY equal the
 * game-page coordinates like on TikTok, not desktop monitor coordinates. The converted mouse event is stopped, so the
 * engine does not get the same press twice. Presses on non-canvas elements (ad simulator panel, vConsole) are left as
 * mouse clicks. Real touch input (Chrome device mode, a touch screen) is untouched. */
(function (w) {
  'use strict';
  var d = w.document;
  if (!d || w.__previewTouchBridge) return;
  // Engines enable touch input only when the page says it supports touches (cc.sys.capabilities.touches,
  // 3.x INPUT_TOUCH): declare it like a phone does.
  try { if (!('ontouchstart' in d.documentElement)) d.documentElement.ontouchstart = null; } catch (e) {}
  try { if (!('ontouchstart' in w)) w.ontouchstart = null; } catch (e) {}
  var nextId = 1, active = null;

  function point(a, e) {
    var target = a.target;
    var x = e.clientX, y = e.clientY;
    a.x = x; a.y = y;
    var init = {identifier: a.id, target: target, clientX: x, clientY: y, screenX: x, screenY: y,
      pageX: x + (w.pageXOffset || 0), pageY: y + (w.pageYOffset || 0), radiusX: 1, radiusY: 1, rotationAngle: 0,
      force: 1};
    try { if (typeof w.Touch === 'function') return new w.Touch(init); } catch (err) {}
    return init;
  }

  function fire(type, target, touch, stillDown) {
    var touches = stillDown ? [touch] : [];
    var event;
    try {
      if (typeof w.TouchEvent === 'function' && typeof w.Touch === 'function' && touch instanceof w.Touch) {
        event = new w.TouchEvent(type, {bubbles: true, cancelable: true, composed: true, touches: touches,
          targetTouches: touches, changedTouches: [touch]});
      }
    } catch (err) { event = null; }
    if (!event) {
      event = d.createEvent('Event');
      event.initEvent(type, true, true);
      Object.defineProperty(event, 'touches', {value: touches});
      Object.defineProperty(event, 'targetTouches', {value: touches});
      Object.defineProperty(event, 'changedTouches', {value: [touch]});
    }
    Object.defineProperty(event, '__previewTouchBridge', {value: true});
    target.dispatchEvent(event);
  }

  function isCanvas(t) { return !!t && String(t.tagName || t.nodeName || '').toUpperCase() === 'CANVAS'; }

  function swallow(e) { e.stopImmediatePropagation(); if (e.cancelable) e.preventDefault(); }

  w.addEventListener('mousedown', function (e) {
    if (e.button !== 0 || !isCanvas(e.target)) return;
    swallow(e);
    if (active) fire('touchcancel', active.target, point(active, e), false);
    active = {id: nextId++, target: e.target};
    fire('touchstart', active.target, point(active, e), true);
  }, true);
  w.addEventListener('mousemove', function (e) {
    if (!active) return;
    swallow(e);
    fire('touchmove', active.target, point(active, e), true);
  }, true);
  w.addEventListener('mouseup', function (e) {
    if (!active || e.button !== 0) return;
    swallow(e);
    var a = active;
    fire('touchend', a.target, point(a, e), false);
    active = null;
  }, true);
  w.addEventListener('blur', function () {
    if (!active) return;
    var a = active;
    active = null;
    fire('touchcancel', a.target, point(a, {clientX: a.x || 0, clientY: a.y || 0}), false);
  });
  w.__previewTouchBridge = {version: 1};
})(window);
