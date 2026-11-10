// 11.17.16 (Saul 2026-11-09): "the log says home, the screen still shows loading" is a startup failure, whatever the
// cause. SLS36 v61: the engine reached the lobby and kept drawing, but on the phone the loading picture never left the
// screen (the engine drew to a canvas that was not on screen). Every check that read engine state passed.
//
// The startup suites keep the last screenshot taken while the engine has no scene yet (the loading picture) and
// compare it with the screen 1.5 s after the home page is reported. Almost no change = the player still sees the
// loading picture. Two screenshots per case, no recording. Node only (zlib), no extra package.
import zlib from 'node:zlib';
import fs from 'node:fs';
import path from 'node:path';

export const STEP = 4;             // sample every 4th pixel in both directions
export const PIXEL_DELTA = 24;     // a sampled pixel counts as changed when one channel moved more than this
export const MIN_CHANGED = 0.02;   // less than 2 % of sampled pixels changed = the screen did not leave loading

// 8-bit RGB / RGBA, non-interlaced PNG (what Chromium screenshots are). -> {w, h, ch, data} or null.
export function decodePng(buf) {
  if (!buf || buf.length < 33 || buf.readUInt32BE(0) !== 0x89504e47) return null;
  let off = 8, w = 0, h = 0, depth = 0, type = 0, interlace = 0;
  const idat = [];
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32BE(off), kind = buf.toString('latin1', off + 4, off + 8), body = buf.subarray(off + 8, off + 8 + len);
    if (kind === 'IHDR') { w = body.readUInt32BE(0); h = body.readUInt32BE(4); depth = body[8]; type = body[9]; interlace = body[12]; }
    else if (kind === 'IDAT') idat.push(body);
    else if (kind === 'IEND') break;
    off += 12 + len;
  }
  const ch = type === 6 ? 4 : type === 2 ? 3 : 0;
  if (!w || !h || depth !== 8 || !ch || interlace) return null;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = w * ch, data = Buffer.alloc(stride * h);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = y * (stride + 1) + 1, dst = y * stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= ch ? data[dst + x - ch] : 0, b = y ? data[dst - stride + x] : 0, c = x >= ch && y ? data[dst - stride + x - ch] : 0;
      let v = raw[src + x];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      data[dst + x] = v & 255;
    }
  }
  return { w, h, ch, data };
}

// Share of sampled pixels that changed between two screenshots of the same size (null when not comparable).
export function changedShare(before, after) {
  const a = decodePng(before), b = decodePng(after);
  if (!a || !b || a.w !== b.w || a.h !== b.h) return null;
  let seen = 0, moved = 0;
  for (let y = 0; y < a.h; y += STEP) {
    for (let x = 0; x < a.w; x += STEP) {
      const i = (y * a.w + x) * a.ch, j = (y * b.w + x) * b.ch;
      seen++;
      if (Math.abs(a.data[i] - b.data[j]) > PIXEL_DELTA || Math.abs(a.data[i + 1] - b.data[j + 1]) > PIXEL_DELTA ||
          Math.abs(a.data[i + 2] - b.data[j + 2]) > PIXEL_DELTA) moved++;
    }
  }
  return seen ? moved / seen : null;
}

// No "one colour = skip" rule: SLS36's own loading picture is 97 % one colour (a small logo and bar), and a home that
// differs from it by under 2 % looks the same to the player. Calibrated on SLS36 v61/v62 Ego screenshots: loading ->
// home 99.1 % changed, v61 stuck 0.1 %, home -> after PLAY 98.7 %.

export const MARGIN_MS = 2000;      // the loading frame is taken at least this long before the home page was reported
export const RECHECK_MS = 3000;    // an unchanged screen is looked at once more after this long (slow home intro)

// One per case: watch.loading(page) on every poll while the home page is not reported, then watch.judge(...)
// 1.5 s after it is. The loading frame is the newest one taken >= MARGIN_MS before the home was reported (a home
// that is already visible a poll before the adapter says so is never used). Many Cocos games draw their loading
// screen inside a scene, so "engine has no scene yet" is not a usable signal.
// The Ego page writes screenshots to a file (page.screenshot({path}), as every suite does); read the bytes back.
async function grab(page, file) {
  try { await page.screenshot({ path: file }); return fs.readFileSync(file); } catch (_) { return null; }
}

export function watch(dir, id) {
  let shots = [], homeAt = null;
  const tmp = path.join(dir || '.', `screen-${id}-poll.png`);
  return {
    async loading(page) {
      const buf = await grab(page, tmp);
      if (buf) shots.push({ t: Date.now(), buf });
      const keep = Date.now() - MARGIN_MS - 6000;
      while (shots.length > 2 && shots[1].t < keep) shots.shift();
    },
    home() { if (homeAt === null) homeAt = Date.now(); },
    // -> {problem: string|null, share, recheck, note, files}
    async judge(page) {
      const at = homeAt === null ? Date.now() : homeAt;
      const base = shots.filter(s => s.t <= at - MARGIN_MS).pop();
      try { fs.unlinkSync(tmp); } catch (_) {}
      if (!base) return { problem: null, share: null, note: 'home came within ' + MARGIN_MS / 1000 + ' s: no loading frame to compare (fast start)' };
      const homeShot = await grab(page, tmp);
      if (!homeShot) return { problem: null, share: null, note: 'no home screenshot' };
      const files = {};
      const save = (k, v) => { try { files[k] = path.join(dir, `screen-${id}-${k}.png`); fs.writeFileSync(files[k], v); } catch (_) {} };
      save('loading', base.buf); save('home', homeShot);
      let share = changedShare(base.buf, homeShot), recheck = null;
      if (share === null) return { problem: null, share, note: 'screenshots not comparable', files };
      if (share < MIN_CHANGED) {                    // a slow home intro gets one more look
        await new Promise(r => setTimeout(r, RECHECK_MS));
        const later = await grab(page, tmp);
        if (later) { save('home-later', later); recheck = changedShare(base.buf, later); }
      }
      try { fs.unlinkSync(tmp); } catch (_) {}
      const still = share < MIN_CHANGED && (recheck === null || recheck < MIN_CHANGED);
      const problem = still
        ? `the engine reports the home page but the screen still shows the loading picture (${(share * 100).toFixed(1)}%` +
          (recheck === null ? '' : `, ${(recheck * 100).toFixed(1)}% after ${RECHECK_MS / 1000} s more`) +
          ` of the screen changed, need >= ${MIN_CHANGED * 100}%): the player is stuck on loading although the log says home. ` +
          `Look for a loading layer and the engine drawing to different canvases / SDK objects (SLS36 v61)`
        : null;
      return { problem, share, recheck, files, loadingAgeMs: at - base.t };
    }
  };
}
