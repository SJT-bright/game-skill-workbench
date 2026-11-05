#!/usr/bin/env node
'use strict';
// Free slots for the two platform entries on a home screen (生成时预防 P06 3, Saul 2026-11-04: avoid at generation
// time, do not find it in the check). English games keep every original home button where it is and add
// "Add to Home" + "Profile Revisit" only in empty space (tiktok-fixed-adaptation item 9). Until now the AI guessed
// the coordinates and the entries landed on other buttons (element_overlap: 61 games in the 11-04 survey).
// This finds two places that touch no existing button (each box grown by the gap), stay inside the screen minus the
// top capsule band, and do not touch each other. No room -> an error, never a guessed position.
//
// Coordinates: design units, origin at the screen centre, y up (Cocos node space under a centred Canvas).
//   const S = require('./home_free_slot');
//   S.findFreeSlots({screen: {w: 720, h: 1280}, buttons: [{name, x, y, w, h}], entry: {w: 140, h: 140}})
//   optional safe: {x0, y0, x1, y1} -- the safe area in the same coordinates (default: the screen minus topReserve)
//     -> {ok: true, slots: [{x, y, w, h}, {x, y, w, h}]}   or   {ok: false, error: '...'}
// CLI (prints JSON, exit 0 found / 1 no room / 2 bad input):
//   node home_free_slot.js --prefab assets/Home.prefab --screen 720x1280 --entry 140x140
//   node home_free_slot.js --dump docs/.../003-ui-dump-home.json --screen 720x1280 --entry 140x140
// Options: --safe x0,y0,x1,y1 (safe area, same coordinates), --gap 16 (space kept around every button), --top-reserve 0.12 (share of the screen height kept for the
// TikTok capsule and status bar), --obstacle name1,name2 (non-button nodes to keep clear: logo, title, banner).
// Node only; nothing here runs in the game. Pure functions, no dependencies.

var DEFAULTS = {gap: 16, topReserve: 0.12, step: 4};

function box(b) { return {x0: b.x - b.w / 2, y0: b.y - b.h / 2, x1: b.x + b.w / 2, y1: b.y + b.h / 2}; }
function grow(b, g) { return {x0: b.x0 - g, y0: b.y0 - g, x1: b.x1 + g, y1: b.y1 + g}; }
function hits(a, b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }

// Every place where one entry fits, row by row from the bottom up (the bottom row first, then upwards).
function freeRows(screen, obstacles, entry, o) {
  var hw = entry.w / 2, hh = entry.h / 2, rows = [];
  var safe = o.safe || {x0: -screen.w / 2, y0: -screen.h / 2, x1: screen.w / 2, y1: screen.h / 2 - screen.h * o.topReserve};
  var left = safe.x0 + o.gap + hw, right = safe.x1 - o.gap - hw;
  var bottom = safe.y0 + o.gap + hh, top = safe.y1 - hh;
  for (var y = bottom; y <= top; y += o.step) {
    var xs = [];
    for (var x = left; x <= right; x += o.step) {
      var b = {x0: x - hw, y0: y - hh, x1: x + hw, y1: y + hh};
      if (!obstacles.some(function (ob) { return hits(b, ob); })) xs.push(x);
    }
    if (xs.length) rows.push({y: y, xs: xs});
  }
  return rows;
}

// Both entries in one row when possible: the pair whose middle is nearest the screen centre, then the closest pair.
function pairInRow(row, entry, gap) {
  var best = null, xs = row.xs, need = entry.w + gap;
  for (var i = 0; i < xs.length; i++) {
    for (var j = xs.length - 1; j > i; j--) {
      var d = xs[j] - xs[i];
      if (d < need) break;
      var off = Math.abs(xs[i] + xs[j]), score = off * 4 + (d - need);
      if (!best || score < best.score) best = {score: score, a: xs[i], b: xs[j]};
    }
  }
  return best;
}

function findFreeSlots(spec) {
  spec = spec || {};
  var screen = spec.screen, entry = spec.entry, count = spec.count || 2;
  if (!screen || !(screen.w > 0) || !(screen.h > 0)) return {ok: false, error: 'screen {w, h} is required'};
  if (!entry || !(entry.w > 0) || !(entry.h > 0)) return {ok: false, error: 'entry {w, h} is required'};
  var o = {gap: spec.gap === undefined ? DEFAULTS.gap : spec.gap,
    topReserve: spec.topReserve === undefined ? DEFAULTS.topReserve : spec.topReserve, step: spec.step || DEFAULTS.step,
    safe: spec.safe || null};
  if (o.safe && !(o.safe.x1 > o.safe.x0 && o.safe.y1 > o.safe.y0)) return {ok: false, error: 'safe {x0, y0, x1, y1} is empty'};
  var buttons = (spec.buttons || []).concat(spec.obstacles || []);
  var bad = buttons.filter(function (b) { return ![b.x, b.y, b.w, b.h].every(isFinite); });
  if (bad.length) return {ok: false, error: 'button without x, y, w, h: ' + bad.map(function (b) { return b.name; }).join(', ')};
  var obstacles = buttons.map(function (b) { return grow(box(b), o.gap); });
  var rows = freeRows(screen, obstacles, entry, o);
  var slots = [];
  for (var r = 0; r < rows.length && count === 2; r++) {
    var p = pairInRow(rows[r], entry, o.gap);
    if (p) { slots = [{x: p.a, y: rows[r].y}, {x: p.b, y: rows[r].y}]; break; }
  }
  if (!slots.length) {
    // no row holds both: place them one by one, lowest first, each keeping clear of the ones already placed
    for (var k = 0; k < count; k++) {
      var extra = obstacles.concat(slots.map(function (s) { return grow(box({x: s.x, y: s.y, w: entry.w, h: entry.h}), o.gap); }));
      var free = freeRows(screen, extra, entry, o);
      if (!free.length) {
        return {ok: false, error: 'no free place for ' + count + ' entries of ' + entry.w + 'x' + entry.h + ' on a ' +
          screen.w + 'x' + screen.h + ' home with ' + buttons.length + ' buttons/obstacles (gap ' + o.gap +
          '): make the entries smaller, or ask before moving an original button -- do not guess a position',
          placed: slots.length};
      }
      var row = free[0], best = row.xs.reduce(function (m, x) { return Math.abs(x) < Math.abs(m) ? x : m; }, row.xs[0]);
      slots.push({x: best, y: row.y});
    }
  }
  return {ok: true, coords: 'design units, origin at the screen centre, y up', gap: o.gap,
    slots: slots.map(function (s) { return {x: s.x, y: s.y, w: entry.w, h: entry.h}; })};
}

// ------------------------------------------------------------------------------------------- reading a home screen

function components(objs, node) {
  return (node._components || []).map(function (c) { return objs[c.__id__]; }).filter(Boolean);
}
function nodeSize(objs, node) {
  var t = components(objs, node).filter(function (c) { return c.__type__ === 'cc.UITransform'; })[0];
  var s = (t && t._contentSize) || node._contentSize || {width: 0, height: 0};
  var a = (t && t._anchorPoint) || node._anchorPoint || {x: 0.5, y: 0.5};
  return {w: s.width || 0, h: s.height || 0, ax: a.x === undefined ? 0.5 : a.x, ay: a.y === undefined ? 0.5 : a.y};
}
function local(node) {
  if (node._trs && node._trs.array) {
    var t = node._trs.array;
    return {x: t[0], y: t[1], sx: t[7] === undefined ? 1 : t[7], sy: t[8] === undefined ? 1 : t[8]};
  }
  var p = node._lpos || node._position || {}, s = node._lscale || node._scale || {};
  return {x: p.x || 0, y: p.y || 0, sx: s.x === undefined ? 1 : s.x, sy: s.y === undefined ? 1 : s.y};
}

// Buttons (nodes with cc.Button) and named obstacles of a 2.4 / 3.x prefab or scene, as centre boxes in the space
// of the prefab root (= screen centre for a full-screen home). Rotation is ignored; cc.Widget is not run, so a
// home laid out by Widgets at runtime should be read from a ui_dump instead (--dump).
function boxesFromPrefab(objs, obstacleNames) {
  var names = obstacleNames || [], out = [];
  var parentOf = function (n) { return n._parent ? objs[n._parent.__id__] : null; };
  objs.forEach(function (n) {
    if (!n || n.__type__ !== 'cc.Node') return;
    var isButton = components(objs, n).some(function (c) { return c.__type__ === 'cc.Button'; });
    if (!isButton && names.indexOf(n._name) < 0) return;
    if (n._active === false) return;
    var chain = [], cur = n;
    while (cur && cur.__type__ === 'cc.Node') { chain.unshift(cur); cur = parentOf(cur); }
    var x = 0, y = 0, sx = 1, sy = 1;
    chain.forEach(function (c, i) {
      var l = local(c);
      if (i === 0) return;                    // the prefab root sits at the screen centre
      x += l.x * sx; y += l.y * sy; sx *= l.sx; sy *= l.sy;
    });
    var s = nodeSize(objs, n), w = s.w * Math.abs(sx), h = s.h * Math.abs(sy);
    out.push({name: n._name, x: x + (0.5 - s.ax) * w, y: y + (0.5 - s.ay) * h, w: w, h: h, button: isButton});
  });
  return out;
}

// Buttons of a ui_dump.js page (screen rects as fractions, top-left origin) converted to design units.
function boxesFromDump(dump, screen, obstacleNames) {
  var names = obstacleNames || [];
  return (dump.nodes || []).filter(function (n) {
    var c = n.comps || {};
    return (c.button || names.indexOf(n.name) >= 0) && (n.opacity === undefined || n.opacity >= 0.05) && (n.screen || n.rect);
  }).map(function (n) {
    var r = n.screen || n.rect;
    var w = r[2] * screen.w, h = r[3] * screen.h;
    return {name: n.name, x: (r[0] + r[2] / 2 - 0.5) * screen.w, y: (0.5 - r[1] - r[3] / 2) * screen.h, w: w, h: h,
      button: !!(n.comps || {}).button};
  });
}

function parseSize(v) {
  var m = /^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$/.exec(String(v || ''));
  return m ? {w: +m[1], h: +m[2]} : null;
}

function main(argv) {
  var fs = require('fs'), a = {};
  for (var i = 0; i < argv.length; i++) if (argv[i].indexOf('--') === 0) a[argv[i].slice(2)] = argv[i + 1];
  var screen = parseSize(a.screen), entry = parseSize(a.entry);
  var obstacles = a.obstacle ? String(a.obstacle).split(',') : [];
  if (!screen || !entry || !(a.prefab || a.dump)) {
    console.log(JSON.stringify({ok: false, error: 'usage: --prefab FILE | --dump FILE, --screen WxH, --entry WxH'}));
    return 2;
  }
  var buttons;
  try {
    var data = JSON.parse(fs.readFileSync(a.prefab || a.dump, 'utf8'));
    buttons = a.prefab ? boxesFromPrefab(data, obstacles) : boxesFromDump(data, screen, obstacles);
  } catch (e) {
    console.log(JSON.stringify({ok: false, error: 'cannot read ' + (a.prefab || a.dump) + ': ' + e.message}));
    return 2;
  }
  var safe = a.safe ? String(a.safe).split(',').map(Number) : null;
  var r = findFreeSlots({screen: screen, entry: entry, buttons: buttons,
    safe: safe && safe.length === 4 ? {x0: safe[0], y0: safe[1], x1: safe[2], y1: safe[3]} : undefined,
    gap: a.gap === undefined ? undefined : +a.gap, topReserve: a['top-reserve'] === undefined ? undefined : +a['top-reserve']});
  r.buttons = buttons;
  console.log(JSON.stringify(r, null, 2));
  return r.ok ? 0 : 1;
}

module.exports = {findFreeSlots: findFreeSlots, boxesFromPrefab: boxesFromPrefab, boxesFromDump: boxesFromDump,
  intersects: function (a, b) { return hits(box(a), box(b)); }, DEFAULTS: DEFAULTS};
if (require.main === module) process.exitCode = main(process.argv.slice(2));
