// frame_rate pieces (v7.8, 总表 P16 第 3 步): the page-side display clock and sampler, and the pure comparison.
// No browser here: suites/frame_rate.mjs injects RAF_JS before the page loads and runs SAMPLER_JS; the Node test
// (test_frame_rate_gate.py) runs compare() on recorded runs.
//
// Display clock: the page's requestAnimationFrame is replaced, before any page script runs, by a timer that fires at
// exactly `hz` per second (a real 120 Hz Mac and a 60 Hz phone, on the same machine). Cocos 2.4 takes
// window.requestAnimationFrame when the game starts (cc.game._setAnimFrame), so its main loop, cc.director's dt and the
// 2.4 physics step follow this clock. window.__fr counts the ticks.
export const RAF_JS = (hz) => `(function(){var iv=1000/${+hz},q=[],id=0,next=0;
window.__fr={hz:${+hz},ticks:0};
function tick(){var now=performance.now(),cbs=q;q=[];window.__fr.ticks++;
for(var i=0;i<cbs.length;i++){try{cbs[i][1](now)}catch(e){(function(x){setTimeout(function(){throw x})})(e)}}
next+=iv;var d=next-performance.now();if(d<-iv){next=performance.now()+iv;d=iv}setTimeout(tick,Math.max(0,d))}
window.requestAnimationFrame=function(cb){q.push([++id,cb]);return id};
window.cancelAnimationFrame=function(k){q=q.filter(function(x){return x[0]!==k})};
window.webkitRequestAnimationFrame=window.requestAnimationFrame;window.webkitCancelAnimationFrame=window.cancelAnimationFrame;
next=performance.now()+iv;setTimeout(tick,iv)})();`;

// Runs once in the page at t0: the operation (drive_js), timed steps (steps[].at_s, real time), and a 10 ms real-time
// sampler of the tracked node's world position. Read window.__fps after run_s.
export const SAMPLER_JS = `(function(cfg){
var W=window.__fps={t0:performance.now(),s:[],err:null,done:false,
  f0:(window.cc&&cc.director&&cc.director.getTotalFrames)?cc.director.getTotalFrames():null,k0:window.__fr?window.__fr.ticks:null};
var track=new Function(cfg.track);
function pos(){var r=track();if(!r)return null;
  if(typeof r.x==='number'&&typeof r.y==='number'&&!r.getComponent&&!r.convertToWorldSpaceAR)return [r.x,r.y,+r.z||0];
  var n=r.node||r,w;
  if(n.is3DNode&&n.getWorldPosition){w=n.getWorldPosition(cc.v3());return [w.x,w.y,w.z]}
  if(n.convertToWorldSpaceAR){w=n.convertToWorldSpaceAR(cc.v2(0,0));return [w.x,w.y,+w.z||0]}
  if(n.worldPosition){w=n.worldPosition;return [w.x,w.y,w.z]}
  return null}
function sample(){try{var p=pos();W.s.push([Math.round((performance.now()-W.t0)*10)/10].concat(p||[null,null,null]))}
  catch(e){if(!W.err)W.err='track threw: '+String(e&&e.message||e).slice(0,200)}}
try{W.drive=(new Function(cfg.drive_js))();if(W.drive&&typeof W.drive==='object'&&!Array.isArray(W.drive))W.drive=JSON.parse(JSON.stringify(W.drive))}
catch(e){W.err='drive_js threw: '+String(e&&e.message||e).slice(0,200)}
(cfg.steps||[]).forEach(function(s){setTimeout(function(){try{(new Function(s.js))()}catch(e){if(!W.err)W.err='step at '+s.at_s+' s threw: '+String(e&&e.message||e).slice(0,200)}},s.at_s*1000)});
sample();W.iv=setInterval(sample,10);
setTimeout(function(){clearInterval(W.iv);sample();W.done=true;W.t1=performance.now()-W.t0;
  W.f1=(window.cc&&cc.director&&cc.director.getTotalFrames)?cc.director.getTotalFrames():null;W.k1=window.__fr?window.__fr.ticks:null},cfg.run_s*1000);
return true})`;

export const TOLERANCE = 0.05;      // P16: position differs by more than 5 % at the same real time -> not passed
export const CHECK_FROM_S = 1.0;    // checkpoints start 1 s after the motion starts (one frame of start jitter is < 2 %)
export const CHECK_EVERY_S = 0.25;
export const MOVE_EPS = 2;          // world units: the motion "starts" at the first sample this far from the start point

function at(samples, t) {
  // linear interpolation of [t, x, y, z] rows (t ascending; rows with null positions are skipped)
  let prev = null;
  for (const row of samples) {
    if (row[1] == null) continue;
    if (row[0] >= t) {
      if (!prev || row[0] === t) return row.slice(1);
      const k = (t - prev[0]) / (row[0] - prev[0]);
      return [1, 2, 3].map((i) => prev[i] + (row[i] - prev[i]) * k);
    }
    prev = row;
  }
  return null;
}
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], (a[2] || 0) - (b[2] || 0));

// Where the tracked node starts moving: {t, origin} (origin = first sampled position; t in ms after t0), or null.
export function motionStart(samples, align = 'move') {
  const rows = (samples || []).filter((r) => r[1] != null);
  if (!rows.length) return null;
  const origin = rows[0].slice(1);
  if (align === 'drive') return { t: 0, origin };
  const moved = rows.find((r) => dist(r.slice(1), origin) >= MOVE_EPS);
  return moved ? { t: moved[0], origin } : null;
}

// Pure verdict over two runs {hz, samples, ticks, seconds, frames}. -> {passed, code, worst, checkpoints, ...}
// code: 'same_motion' (passed or not), 'no_motion' (the tracked node never moved min_move: adapter or start wrong).
export function compare(slow, fast, opt = {}) {
  const runS = +opt.run_s || 5, minMove = +opt.min_move || 20, align = opt.align || 'move';
  const s0 = motionStart(slow.samples, align), f0 = motionStart(fast.samples, align);
  const out = { tolerance: TOLERANCE, align, min_move: minMove, start_ms: { [slow.hz]: s0 && s0.t, [fast.hz]: f0 && f0.t },
                checkpoints: [], worst: null, passed: false, code: 'same_motion' };
  if (!s0 || !f0) { out.code = 'no_motion'; out.why = 'the tracked node did not move in the ' + (!s0 ? slow.hz : fast.hz) + ' Hz run'; return out; }
  const end = runS * 1000 - Math.max(s0.t, f0.t);
  for (let t = CHECK_FROM_S * 1000; t <= end + 1e-6; t += CHECK_EVERY_S * 1000) {
    const a = at(slow.samples, s0.t + t), b = at(fast.samples, f0.t + t);
    if (!a || !b) continue;
    const da = [a[0] - s0.origin[0], a[1] - s0.origin[1], a[2] - s0.origin[2]];
    const db = [b[0] - f0.origin[0], b[1] - f0.origin[1], b[2] - f0.origin[2]];
    const scale = Math.max(Math.hypot(...da), Math.hypot(...db));
    if (scale < minMove) continue;
    const row = { t_s: Math.round(t) / 1000, [slow.hz]: da.map((v) => Math.round(v * 10) / 10), [fast.hz]: db.map((v) => Math.round(v * 10) / 10),
                  rel: Math.round(dist(da, db) / scale * 10000) / 10000 };
    out.checkpoints.push(row);
    if (!out.worst || row.rel > out.worst.rel) out.worst = row;
  }
  if (out.checkpoints.length < 2) { out.code = 'no_motion'; out.why = 'fewer than 2 checkpoints with a move of ' + minMove + ' world units or more'; return out; }
  out.passed = out.worst.rel <= TOLERANCE;
  return out;
}

// Did the run really follow its display clock? invalid: ticks/s off by more than 8 % (the run proves nothing, re-run);
// warnings: engine frames/s off by more than 15 % (a game with frameRate 30, or skipped frames; the comparison still
// decides, it is only reported).
export function clockCheck(run) {
  const secs = run.seconds || 0;
  if (!secs) return { invalid: ['no run time recorded'], warnings: [] };
  const tick = run.ticks / secs, frames = run.frames == null ? null : run.frames / secs;
  const invalid = [], warnings = [];
  if (!(Math.abs(tick - run.hz) <= run.hz * 0.08)) invalid.push(run.hz + ' Hz run: the display clock ran at ' + tick.toFixed(1) + ' Hz (machine too busy or the tab throttled; re-run with the Ego window visible)');
  if (frames != null && !(Math.abs(frames - run.hz) <= run.hz * 0.15)) warnings.push(run.hz + ' Hz run: the engine drew ' + frames.toFixed(1) + ' frames/s (its main loop does not follow requestAnimationFrame one to one: frameRate 30, or skipped frames)');
  return { invalid, warnings };
}
