// In-page frame watcher of the popin suite (v7.8, 总表 P2 补), Cocos 2.4. Its own module so test_popin_gate.py can run
// it in Node on a fake engine. Use: page.evaluate(WATCH_JS + '(' + JSON.stringify(opts) + ')'), opts {player, ignore,
// ignore_groups}; results in window.__popin {V, ev, counts, frames, watched, covered, hitches, phase}.
// Keep this text free of backquotes and dollar-brace (pasted into a template string).
export const WATCH_JS = `(function (P) {
  var cc = window.cc;
  var PL = String(P.player || ''), IG = P.ignore ? new RegExp(P.ignore) : null, GR = P.ignore_groups || [];
  var plTail = '/' + PL.replace(/^[*][/]/, ''), plName = PL.split('/').pop();
  function pathOf(n) { var p = []; while (n && n.parent) { p.unshift(n.name); n = n.parent; } return p.join('/'); }
  function isPlayer(n) { return !!plName && n.name === plName && ('/' + pathOf(n)).slice(-plTail.length) === plTail; }
  var vr = cc.visibleRect, vs = cc.view.getVisibleSize(), vo = cc.view.getVisibleOrigin();
  var CAM = !!(cc.Camera && cc.Camera.findCamera);
  var V = CAM ? { l: 0, r: vr.width, b: 0, t: vr.height } : { l: vo.x, r: vo.x + vs.width, b: vo.y, t: vo.y + vs.height };
  function box(n) {
    var r = n.getBoundingBoxToWorld(), cam = CAM ? cc.Camera.findCamera(n) : null;
    if (!cam) return { l: r.x, r: r.x + r.width, b: r.y, t: r.y + r.height };
    var a = cam.getWorldToScreenPoint(cc.v2(r.x, r.y)), c = cam.getWorldToScreenPoint(cc.v2(r.x + r.width, r.y + r.height));
    return { l: Math.min(a.x, c.x), r: Math.max(a.x, c.x), b: Math.min(a.y, c.y), t: Math.max(a.y, c.y) };
  }
  function alpha(n) { var a = 1; for (var x = n; x; x = x.parent) { if (x.opacity === 0 || x.scaleX === 0 || x.scaleY === 0) return 0; a *= (x.opacity == null ? 255 : x.opacity) / 255; } return a; }
  function draws(n) {
    var hit = false;
    var own = function (x) { var rc = cc.RenderComponent && x.getComponent(cc.RenderComponent); if (!rc || !rc.enabled) return false; if (rc instanceof cc.Sprite) return !!rc.spriteFrame; if (rc instanceof cc.Label) return !!rc.string; return true; };
    if (own(n)) return true;
    n.walk(function (x) { if (!hit && x !== n && x.activeInHierarchy && own(x)) hit = true; });
    return hit;
  }
  function inV(b) { return !!b && b.r > V.l + 1 && b.l < V.r - 1 && b.t > V.b + 1 && b.b < V.t - 1; }
  var W = window.__popin = { V: V, camera: CAM, ev: [], counts: {}, frames: 0, watched: 0, phase: 'flight', covered: 0, t0: performance.now(), hitches: 0 };
  var prev = new Map(), last = performance.now();
  function push(e) { var k = e.phase + ':' + e.kind; W.counts[k] = (W.counts[k] || 0) + 1; if (W.ev.length < 300) W.ev.push(e); }
  W.fn = function () {
    var now = performance.now(), dt = now - last; last = now; W.frames++;
    if (dt > 50) W.hitches++;
    var thr = 40 * Math.max(1, dt / 16.7), all = [], cur = new Map(), playerRoot = null;
    var walk = function (n) { all.push(n); if (!playerRoot && isPlayer(n)) playerRoot = n; n.children.forEach(walk); };
    walk(cc.director.getScene());
    var idx = new Map(); all.forEach(function (n, i) { idx.set(n, i); });
    var under = function (n, p) { for (; n; n = n.parent) if (n === p) return true; return false; };
    var coverIdx;   // lazily: drawing index of the first full-screen opaque cover (-1 = none)
    var covered = function (n) {
      if (coverIdx === undefined) {
        coverIdx = -1;
        for (var i = all.length - 1; i >= 0; i--) {
          var x = all[i]; if (!x.activeInHierarchy) continue;
          var s = x.getComponent(cc.Sprite) || (cc.Graphics && x.getComponent(cc.Graphics)); if (!s || !s.enabled || (s instanceof cc.Sprite && !s.spriteFrame)) continue;
          if (alpha(x) < 0.98) continue;
          var b = box(x); if (b.l <= V.l + 1 && b.r >= V.r - 1 && b.b <= V.b + 1 && b.t >= V.t - 1) { coverIdx = i; break; }
        }
      }
      return coverIdx >= 0 && coverIdx > idx.get(n);
    };
    all.forEach(function (n) {
      if (playerRoot && under(n, playerRoot)) return;
      if (!(n.getComponent(cc.PhysicsCollider) || n.getComponent(cc.Collider))) return;
      if (GR.indexOf(n.group) >= 0 || (IG && IG.test(pathOf(n)))) return;
      if (!draws(n)) return;
      var a = n.activeInHierarchy ? alpha(n) : 0, b = a > 0 ? box(n) : null;
      cur.set(n, { a: a, b: b });
      var o = prev.get(n) || { a: 0, b: null };
      if (W.frames <= 2) return;   // the first frames only build the baseline
      var wasIn = o.a >= 0.25 && inV(o.b), isIn = a >= 0.25 && inV(b);
      var e = null;
      if (o.a < 0.05 && isIn) e = { kind: 'appeared_on_screen', at: [Math.round(b.l), Math.round(b.r), Math.round(b.b)] };
      else if (wasIn && a < 0.05) e = { kind: 'vanished_on_screen', at: [Math.round(o.b.l), Math.round(o.b.r), Math.round(o.b.b)] };
      else if (o.b && b && Math.max(o.a, a) >= 0.25 && (wasIn || isIn)) {
        var dx = b.l - o.b.l, dy = b.b - o.b.b;
        if (Math.abs(dx) > thr || Math.abs(dy) > thr) e = { kind: 'jumped_on_screen', from: [Math.round(o.b.l), Math.round(o.b.b)], to: [Math.round(b.l), Math.round(b.b)], visibleBefore: wasIn, visibleAfter: isIn };
      }
      if (e) {
        if (covered(n)) { W.covered++; return; }
        e.node = n.name; e.path = pathOf(n); e.f = W.frames; e.phase = W.phase; e.dt = Math.round(dt); push(e);
      }
    });
    prev.forEach(function (o, n) {   // destroyed or removed from the scene while on screen
      if (cur.has(n) || W.frames <= 2) return;
      if (n.isValid && n.parent && playerRoot && under(n, playerRoot)) return;
      if (o.a >= 0.25 && inV(o.b)) push({ kind: 'vanished_on_screen', node: n.name, f: W.frames, phase: W.phase, removed: true, at: [Math.round(o.b.l), Math.round(o.b.r), Math.round(o.b.b)] });
    });
    W.watched = Math.max(W.watched, cur.size);
    prev = cur;
  };
  cc.director.on(cc.Director.EVENT_AFTER_DRAW, W.fn);
  var found = false; cc.director.getScene().walk(function (n) { if (!found && isPlayer(n)) found = true; });
  return { V: V, camera: CAM, player: found };
})`;
