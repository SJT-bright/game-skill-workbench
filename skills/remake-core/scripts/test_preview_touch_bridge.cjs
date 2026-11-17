#!/usr/bin/env node
'use strict';
/*
 * Behavior regressions for the HTTP-only preview mouse -> touch bridge.
 * Uses Node's actual EventTarget/Event dispatch and brand validation. A minimal
 * Touch/TouchEvent fixture supplies the DOM fields absent from Node; it never
 * substitutes dispatchEvent. A window mouse event gets a canvas target, modeling
 * its capture-phase route. Browser layout/bubbling and isTrusted are outside this
 * unit harness; the real browser DOM -> SDK -> engine -> reward calibration is
 * separate. No production bridge source is changed, parsed or asserted as text.
 *
 * Install: remake-core/scripts/test_preview_touch_bridge.cjs and
 *          remake-core/scripts/fixtures/preview-touch-bridge-v1.js
 * Run: node test_preview_touch_bridge.cjs [--bridge ../assets/preview-touch-bridge.js]
 *      [--old-bridge fixtures/preview-touch-bridge-v1.js] [--report results.json]
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const RealEvent = globalThis.Event;
const RealEventTarget = globalThis.EventTarget;
const realDispatch = RealEventTarget.prototype.dispatchEvent;
const realAdd = RealEventTarget.prototype.addEventListener;
const argv = process.argv.slice(2);
function option(key, fallback) {
  const at = argv.indexOf(key);
  if (at < 0) return fallback;
  if (!argv[at + 1] || argv[at + 1].startsWith('--')) throw new Error('Missing value for '+key);
  return argv[at + 1];
}
const currentFile = path.resolve(option('--bridge', path.join(__dirname, '../assets/preview-touch-bridge.js')));
const oldFile = path.resolve(option('--old-bridge', path.join(__dirname, 'fixtures/preview-touch-bridge-v1.js')));
const reportFile = option('--report', null);
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const current = fs.readFileSync(currentFile, 'utf8');
const old = fs.readFileSync(oldFile, 'utf8');
const rows = [];

function realm(options = {}) {
  const errors = [], records = [], sdk = [], downstream = [], stats = {
    nativeCreateEvent: 0, nativeTouch: 0, nativeTouchEvent: 0,
    fakeCreateEvent: 0, fakeTouch: 0, fakeTouchEvent: 0, targetDispatchStub: 0,
  };
  // Each realm owns its prototype so replacement cannot contaminate another test
  // or Node's actual EventTarget implementation.
  class DomTarget extends RealEventTarget {}
  Object.defineProperty(DomTarget.prototype, 'dispatchEvent', {
    value: realDispatch, configurable: true, writable: true,
  });
  class WindowTarget extends DomTarget {
    addEventListener(type, callback, settings) {
      // Browsers report an exception from a DOM listener and continue. Keep that
      // observation synchronous instead of Node's next-tick uncaught exception.
      realAdd.call(this, type, event => {
        try { callback.call(this, event); }
        catch (error) { errors.push({ name: error.name, code: error.code || null, message: String(error.message) }); }
      }, settings);
    }
  }
  const w = new WindowTarget();
  class Touch {
    constructor(init) {
      stats.nativeTouch++;
      if (options.touchThrows) throw new TypeError('Touch construction unavailable');
      for (const [key, value] of Object.entries(init)) {
        Object.defineProperty(this, key, { value, enumerable: true });
      }
    }
  }
  class TouchEvent extends RealEvent {
    constructor(type, init) {
      stats.nativeTouchEvent++;
      if (options.touchEventThrows) throw new TypeError('TouchEvent construction unavailable');
      super(type, init);
      for (const key of ['touches', 'targetTouches', 'changedTouches']) {
        Object.defineProperty(this, key, { value: init[key], enumerable: true });
      }
    }
  }
  const doc = {
    documentElement: {},
    createEvent(kind) {
      assert.equal(this, doc, 'the original Document receiver must be retained');
      assert.equal(kind, 'Event');
      stats.nativeCreateEvent++;
      return new RealEvent('uninitialized');
    },
  };
  Object.assign(w, {
    document: options.noDocument ? undefined : doc,
    EventTarget: DomTarget, Event: RealEvent,
    Touch: options.noTouch ? undefined : Touch,
    TouchEvent: options.noTouchEvent ? undefined : TouchEvent,
    pageXOffset: 11, pageYOffset: 17,
  });
  const targets = new Map();
  function target(name, tag = 'CANVAS') {
    const node = new DomTarget();
    Object.assign(node, { name, tagName: tag, nodeName: tag });
    targets.set(name, node);
    for (const type of ['touchstart', 'touchmove', 'touchend', 'touchcancel']) {
      realAdd.call(node, type, event => {
        const item = {
          on: name, type: event.type, isRealEvent: event instanceof RealEvent,
          bridged: event.__previewTouchBridge === true,
          bubbles: event.bubbles, cancelable: event.cancelable,
          touches: event.touches.length, targetTouches: event.targetTouches.length,
          changed: event.changedTouches.length,
          points: [...event.changedTouches].map(t => ({
            id: t.identifier, target: t.target.name, nativeTouch: t instanceof Touch,
            clientX: t.clientX, clientY: t.clientY, screenX: t.screenX, screenY: t.screenY,
            pageX: t.pageX, pageY: t.pageY, force: t.force,
          })),
        };
        records.push(item);
        // A distinct SDK observer consumes actual dispatched fields.
        sdk.push({ on: name, type: event.type, points: item.points.map(t => [t.id, t.screenX, t.screenY]) });
      });
    }
    return node;
  }
  const canvas = target('canvas');
  const otherCanvas = target('otherCanvas');
  const overlay = target('overlay', 'BUTTON');
  const context = vm.createContext({ window: w });
  function install(source = current, filename = currentFile) {
    return vm.runInContext(source, context, { filename, timeout: 1000 });
  }
  function mouse(type, node = canvas, x = 42, y = 73, button = 0) {
    const event = new RealEvent(type, { bubbles: true, cancelable: true });
    // Native DOM capture reports the leaf canvas as target, while the listener
    // executes on window. Node has no DOM tree, so provide only that leaf route.
    Object.defineProperties(event, {
      target: { value: node }, clientX: { value: x }, clientY: { value: y }, button: { value: button },
    });
    const dispatchReturned = realDispatch.call(w, event);
    return { event, dispatchReturned };
  }
  function click(node = canvas, x = 42, y = 73, button = 0) {
    return [mouse('mousedown', node, x, y, button), mouse('mouseup', node, x, y, button)];
  }
  function listenDownstream() {
    for (const type of ['mousedown','mousemove','mouseup']) {
      realAdd.call(w, type, event => downstream.push({ type, target: event.target.name, button: event.button }));
    }
  }
  function replaceAdapter({ dispatch = false, constructors = false, createEvent = false, eventTarget = false } = {}) {
    if (dispatch) for (const node of [canvas, otherCanvas]) {
      node.dispatchEvent = function () { stats.targetDispatchStub++; };
    }
    if (constructors) {
      w.Touch = function FakeTouch(init) { stats.fakeTouch++; Object.assign(this, init); };
      w.TouchEvent = function FakeTouchEvent(type, init) { stats.fakeTouchEvent++; return { type, ...init }; };
    }
    if (createEvent) doc.createEvent = function () {
      stats.fakeCreateEvent++;
      return { initEvent(type) { this.type = type; } };
    };
    if (eventTarget) w.EventTarget = { prototype: { dispatchEvent() { throw new Error('adapter global dispatch must not be consulted'); } } };
  }
  function blur() { return realDispatch.call(w, new RealEvent('blur')); }
  function noErrors() { assert.deepEqual(errors, []); }
  return { w, doc, canvas, otherCanvas, overlay, records, sdk, downstream, stats, errors,
    Touch, TouchEvent, install, mouse, click, listenDownstream, replaceAdapter, blur, noErrors };
}
function types(h, on = 'canvas') { return h.records.filter(x => x.on === on).map(x => x.type); }
function points(h, on = 'canvas') { return h.records.filter(x => x.on === on).map(x => x.points[0]); }
function touchPair(h) {
  assert.deepEqual(types(h), ['touchstart', 'touchend']);
  assert.deepEqual(h.records.map(x => x.touches), [1,0]);
  assert.deepEqual(h.records.map(x => x.targetTouches), [1,0]);
  assert(h.records.every(x => x.isRealEvent && x.bridged && x.bubbles && x.cancelable && x.changed === 1));
  assert.deepEqual(h.sdk.map(x => x.type), ['touchstart', 'touchend']);
  h.noErrors();
}
function test(id, fn, kind = 'current') {
  const start = process.hrtime.bigint();
  try {
    const observations = fn() || {};
    rows.push({ id, kind, passed: true, milliseconds: Number(process.hrtime.bigint()-start)/1e6, observations });
    process.stdout.write('PASS '+id+'\n');
  } catch (error) {
    rows.push({ id, kind, passed: false, error: error.stack || String(error) });
    process.stdout.write('FAIL '+id+'\n'+(error.stack || error)+'\n');
  }
}

test('native_event_brand_calibration', () => {
  const t = new RealEventTarget(); let called = 0;
  realAdd.call(t, 'calibration', () => called++);
  assert.equal(realDispatch.call(t, new RealEvent('calibration')), true);
  assert.equal(called, 1);
  assert.throws(() => realDispatch.call(t, { type: 'calibration' }), TypeError);
  return { real_event_delivered: called, plain_object_rejected: true };
});

test('ordinary_web_two_clicks_fields_and_single_delivery', () => {
  const h=realm(); h.install(); h.listenDownstream();
  const first=h.click(h.canvas,42,73), second=h.click(h.canvas,80,90);
  assert.deepEqual(types(h), ['touchstart','touchend','touchstart','touchend']);
  assert.deepEqual(points(h).map(x=>x.id), [1,1,2,2]);
  for (const p of points(h)) {
    assert.equal(p.target,'canvas'); assert.equal(p.nativeTouch,true);
    assert.equal(p.screenX,p.clientX); assert.equal(p.screenY,p.clientY);
    assert.equal(p.pageX,p.clientX+11); assert.equal(p.pageY,p.clientY+17); assert.equal(p.force,1);
  }
  assert.deepEqual(h.downstream,[]); assert([...first,...second].every(x=>x.event.defaultPrevented&&!x.dispatchReturned));
  assert.equal(h.sdk.length,4); h.noErrors();
  assert('ontouchstart' in h.w && 'ontouchstart' in h.doc.documentElement);
  return { events: types(h), finger_ids: points(h).map(x=>x.id), sdk_events: h.sdk.length };
});

test('adapter_canvas_dispatch_override_is_bypassed', () => {
  const h=realm(); h.install(); h.replaceAdapter({dispatch:true}); h.click(); touchPair(h);
  assert.equal(h.stats.targetDispatchStub,0);
  return { events: types(h), overwritten_dispatch_calls: h.stats.targetDispatchStub };
});

test('adapter_touch_constructor_replacement_keeps_original_touch_objects', () => {
  const h=realm(); h.install(); h.replaceAdapter({constructors:true}); h.click(); touchPair(h);
  assert(points(h).every(x=>x.nativeTouch)); assert.equal(h.stats.fakeTouch,0); assert.equal(h.stats.fakeTouchEvent,0);
  return { native_touch_instances: points(h).length, fake_constructor_calls: 0 };
});

test('adapter_all_replacements_preserve_one_dom_and_sdk_event', () => {
  const h=realm(); h.install(); h.replaceAdapter({dispatch:true,constructors:true,createEvent:true,eventTarget:true}); h.click(); touchPair(h);
  for (const key of ['targetDispatchStub','fakeTouch','fakeTouchEvent','fakeCreateEvent']) assert.equal(h.stats[key],0);
  return { dom_events: h.records.length, sdk_events: h.sdk.length, errors: h.errors };
});

test('fallback_without_touch_constructors_uses_real_dom_events', () => {
  const h=realm({noTouch:true,noTouchEvent:true}); h.install(); h.click(); touchPair(h);
  assert.equal(h.stats.nativeCreateEvent,2); assert(points(h).every(x=>!x.nativeTouch));
  return { fallback_events: h.stats.nativeCreateEvent, real_event_brands: h.records.map(x=>x.isRealEvent) };
});

test('fallback_retains_original_document_create_event_after_adapter_replacement', () => {
  const h=realm({noTouch:true,noTouchEvent:true}); h.install(); h.replaceAdapter({createEvent:true}); h.click(); touchPair(h);
  assert.equal(h.stats.nativeCreateEvent,2); assert.equal(h.stats.fakeCreateEvent,0);
  return { original_create_event_calls: 2, replacement_create_event_calls: 0 };
});

test('throwing_touch_constructor_uses_valid_event_fallback', () => {
  const h=realm({touchThrows:true}); h.install(); h.click(); touchPair(h); assert.equal(h.stats.nativeCreateEvent,2);
});

test('throwing_touch_event_constructor_uses_valid_event_fallback', () => {
  const h=realm({touchEventThrows:true}); h.install(); h.click(); touchPair(h); assert.equal(h.stats.nativeCreateEvent,2);
});

test('non_canvas_and_right_button_events_are_not_intercepted', () => {
  const h=realm(); h.install(); h.listenDownstream();
  const events=[...h.click(h.overlay,5,6),...h.click(h.canvas,7,8,2)];
  assert.equal(h.records.length,0); assert.equal(h.downstream.length,4);
  assert(events.every(x=>!x.event.defaultPrevented&&x.dispatchReturned)); h.noErrors();
  return { ordinary_mouse_events: h.downstream, synthetic_events: 0 };
});

test('inactive_mouse_move_and_mouse_up_are_left_alone', () => {
  const h=realm(); h.install(); h.listenDownstream();
  const a=h.mouse('mousemove'),b=h.mouse('mouseup');
  assert.equal(h.records.length,0); assert.equal(h.downstream.length,2);
  assert(!a.event.defaultPrevented&&!b.event.defaultPrevented);h.noErrors();
});

test('drag_outside_canvas_keeps_one_finger_and_original_target', () => {
  const h=realm(); h.install(); h.listenDownstream();
  h.mouse('mousedown',h.canvas,10,20); h.mouse('mousemove',h.overlay,30,40);
  h.mouse('mousemove',h.overlay,200,210); h.mouse('mouseup',h.overlay,220,230);
  const after=h.mouse('mousemove',h.overlay,250,260);
  assert.deepEqual(types(h),['touchstart','touchmove','touchmove','touchend']);
  assert.deepEqual(points(h).map(x=>[x.clientX,x.clientY]),[[10,20],[30,40],[200,210],[220,230]]);
  assert(points(h).every(x=>x.id===1&&x.target==='canvas')); assert.deepEqual(types(h,'overlay'),[]);
  assert.deepEqual(h.records.map(x=>x.touches),[1,1,1,0]); assert(!after.event.defaultPrevented);h.noErrors();
  return { events: types(h), targets: points(h).map(x=>x.target) };
});

test('blur_cancels_at_last_drag_point_and_does_not_emit_a_second_terminal', () => {
  const h=realm(); h.install(); h.mouse('mousedown',h.canvas,1,2);h.mouse('mousemove',h.overlay,78,99);h.blur();
  const up=h.mouse('mouseup',h.canvas,88,100);h.blur();
  assert.deepEqual(types(h),['touchstart','touchmove','touchcancel']);
  assert.deepEqual([points(h).at(-1).clientX,points(h).at(-1).clientY],[78,99]);
  assert.equal(h.records.at(-1).touches,0);assert(!up.event.defaultPrevented);h.noErrors();
});

test('new_press_cancels_old_finger_and_allocates_a_fresh_identifier', () => {
  const h=realm(); h.install();h.mouse('mousedown',h.canvas,1,2);h.mouse('mousedown',h.otherCanvas,3,4);h.mouse('mouseup',h.otherCanvas,3,4);
  assert.deepEqual(types(h),['touchstart','touchcancel']); assert.deepEqual(points(h).map(x=>x.id),[1,1]);
  assert.deepEqual(types(h,'otherCanvas'),['touchstart','touchend']); assert.deepEqual(points(h,'otherCanvas').map(x=>x.id),[2,2]);h.noErrors();
});

test('right_mouse_up_does_not_end_an_active_left_drag', () => {
  const h=realm();h.install();h.mouse('mousedown',h.canvas,1,2);const right=h.mouse('mouseup',h.canvas,3,4,2);
  assert.deepEqual(types(h),['touchstart']); assert(!right.event.defaultPrevented);
  h.mouse('mouseup',h.canvas,5,6,0);touchPair(h);
});

test('real_touch_is_not_rewritten_or_suppressed', () => {
  const h=realm();h.install();const t=new h.Touch({identifier:8,target:h.canvas,clientX:7,clientY:9,screenX:7,screenY:9});
  const e=new h.TouchEvent('touchend',{bubbles:true,cancelable:true,touches:[],targetTouches:[],changedTouches:[t]});
  assert.equal(realDispatch.call(h.canvas,e),true);
  assert.equal(h.records.length,1);assert.equal(h.records[0].bridged,false);assert.equal(h.records[0].points[0].id,8);h.noErrors();
});

test('duplicate_install_returns_before_reading_replaced_dom_apis', () => {
  const h=realm();h.install();h.doc.createEvent=null;
  Object.defineProperty(h.w,'EventTarget',{get(){throw new Error('duplicate install must not capture again');},configurable:true});
  h.install();h.click();touchPair(h);
  return { pair_events: h.records.length, duplicate_handlers: false };
});

test('missing_document_returns_without_installing_or_intercepting', () => {
  const h=realm({noDocument:true});h.install();h.listenDownstream();const result=h.click();
  assert.equal(h.w.__previewTouchBridge,undefined);assert.equal(h.records.length,0);assert.equal(h.downstream.length,2);
  assert(result.every(x=>!x.event.defaultPrevented));h.noErrors();
});

test('preserved_old_bridge_ordinary_web_is_a_valid_normal_control', () => {
  const h=realm();h.install(old,oldFile);h.click();touchPair(h);
  return { events: types(h), sdk_events: h.sdk.length };
},'preserved_original_control');

test('preserved_old_bridge_reproduces_overridden_dispatch_loss', () => {
  const h=realm();h.install(old,oldFile);h.replaceAdapter({dispatch:true});const result=h.click();
  assert.equal(h.records.length,0);assert.equal(h.sdk.length,0);assert.equal(h.stats.targetDispatchStub,2);
  assert(result.every(x=>x.event.defaultPrevented));h.noErrors();
  return { swallowed_mouse_events: 2, stub_calls: 2, dom_events: 0, sdk_events: 0 };
},'preserved_original_negative');

test('preserved_old_bridge_reproduces_fake_touch_event_brand_failure', () => {
  const h=realm();h.install(old,oldFile);h.replaceAdapter({constructors:true});h.click();
  assert.equal(h.records.length,0);assert.equal(h.errors.length,2);
  assert(h.errors.every(e=>e.name==='TypeError'&&/Event/.test(e.message)));
  assert.equal(h.stats.fakeTouchEvent,2);
  return { rejected_events: h.errors, dom_events: 0 };
},'preserved_original_negative');

test('preserved_old_bridge_reproduces_replaced_create_event_fallback_failure', () => {
  const h=realm({noTouch:true,noTouchEvent:true});h.install(old,oldFile);h.replaceAdapter({createEvent:true});h.click();
  assert.equal(h.records.length,0);assert.equal(h.errors.length,2);assert.equal(h.stats.fakeCreateEvent,2);
  assert(h.errors.every(e=>e.name==='TypeError'&&/Event/.test(e.message)));
  return { rejected_events: h.errors, fake_document_calls: h.stats.fakeCreateEvent };
},'preserved_original_negative');

const report={
  tool:'test_preview_touch_bridge',schema:'preview_touch_bridge.behavior.v1',
  runtime:process.version,
  current:{path:currentFile,sha256:sha(current)},preserved_original:{path:oldFile,sha256:sha(old)},
  passed:rows.every(x=>x.passed),test_count:rows.length,
  current_behavior_cases:rows.filter(x=>x.kind==='current').length,
  original_normal_controls:rows.filter(x=>x.kind==='preserved_original_control').length,
  original_negative_controls:rows.filter(x=>x.kind==='preserved_original_negative').length,
  rows,
  boundary:'Actual Node EventTarget/Event brand and dispatch behavior with minimal Touch and capture-route fixtures. It is not a browser layout, real-touch-trust, engine or device pass; retain the separate real browser calibration.',
};
if(reportFile)fs.writeFileSync(path.resolve(reportFile),JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify({passed:report.passed,test_count:report.test_count,current_behavior_cases:report.current_behavior_cases,original_normal_controls:report.original_normal_controls,original_negative_controls:report.original_negative_controls})+'\n');
process.exitCode=report.passed?0:1;
