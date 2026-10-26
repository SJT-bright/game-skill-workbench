#!/usr/bin/env python3
"""Find dynamic visual glitches in a gameplay recording: black/white flashes, one-frame pops and flicker.

Static screenshots cannot see these. Record the flow (chrome_touch.py --record, a screen recording of the
phone simulation, or a phone screen recording) and run this on the video. Read-only.

Detects (times in seconds):
  flash_dark / flash_light  screen suddenly turns (mostly) black/white and comes back      -> blocking
  one_frame_glitch          1-2 frames differ strongly from both neighbours (blank frame,
                            UI popping in/out, texture missing for a moment); >= 3 screen
                            regions or the whole screen                                   -> blocking
  one_frame_glitch_small    same in 1-2 small regions (could be a particle)               -> review
  long_black                mostly black for longer than --max-black seconds mid-recording  -> blocking
  flicker                   a screen region switches colour back and forth fast (>= --flicker-hz) -> blocking
  flicker_slow              same at 3 Hz..--flicker-hz (may be an intended blink)         -> review
  fade_dark                 gradual fade to black (normal scene transition)                -> info
For every blocking/review event it saves before/during/after PNGs, so a reviewer only looks at those.

Usage:
  python audit_frame_glitches.py VIDEO_OR_FRAME_FOLDER [--fps 25] [--out-dir evidence/] [--binding review.json]
      [--report result.json] [--max-black 1.5] [--flicker-hz 6] [--ignore-start 1.0] [--delete-frames]
Never queue it (user 2026-10-23: nothing waits for an occupied resource). --delete-frames removes the frame folder after the
evidence PNGs are saved (they are all a reviewer needs).
Video input needs ffmpeg (the audio module installs it). A frame folder (png/jpg in time order) needs Pillow.
Exit codes: 0 no blocking events, 1 blocking events found, 2 bad input or missing tool.
"""
import argparse
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

W, H = 72, 128               # analysis size (aspect is ignored on purpose; only changes matter)
GX, GY = 6, 8                # flicker grid
DARK, LIGHT = 40, 225        # gray levels counted as black / white


def load_video(path, fps):
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg not found (run game-audio-library/scripts/setup.py once, or install ffmpeg)')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'fps={fps},scale={W}:{H}',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg could not read the video: ' + r.stderr.decode(errors='replace')[-300:])
    size = W * H * 3
    return [r.stdout[i:i + size] for i in range(0, len(r.stdout) - size + 1, size)]


def load_folder(path, fps):
    """Frames in time order. Names like 00012_0000200ms.jpg (chrome_touch.py --record) give real times."""
    import re
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError('Pillow is needed for a frame folder: pip install pillow')
    files = sorted(p for p in path.iterdir() if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'))
    frames, times = [], []
    for i, f in enumerate(files):
        with Image.open(f) as im:
            frames.append(im.convert('RGB').resize((W, H)).tobytes())
        m = re.search(r'_(\d+)ms', f.name)
        times.append(int(m.group(1)) / 1000 if m else i / fps)
    return frames, files, times


def stats(frame):
    """frame: RGB bytes. Returns gray mean, dark share, light share, per-cell mean colours."""
    gray = [(frame[i] * 299 + frame[i + 1] * 587 + frame[i + 2] * 114) // 1000 for i in range(0, len(frame), 3)]
    n = len(gray)
    mean = sum(gray) / n
    dark = sum(1 for v in gray if v < DARK) / n
    light = sum(1 for v in gray if v > LIGHT) / n
    cells = []
    cw, ch = W // GX, H // GY
    for gy in range(GY):
        for gx in range(GX):
            r = g = b = 0
            for y in range(gy * ch, (gy + 1) * ch):
                row = (y * W + gx * cw) * 3
                seg = frame[row:row + cw * 3]
                r += sum(seg[0::3]); g += sum(seg[1::3]); b += sum(seg[2::3])
            k = cw * ch
            cells.append((r / k, g / k, b / k))
    return mean, dark, light, cells, gray


def cdist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def diff(a, b):
    """mean gray difference of two frames (gray lists)"""
    return sum(abs(x - y) for x, y in zip(a[::2], b[::2])) / len(a[::2])


def analyse(frames, times, max_black, flicker_hz, ignore_start):
    st = [stats(f) for f in frames]
    frames = [s[4] for s in st]            # gray versions for whole-frame differences
    n = len(frames)
    end_time = times[-1] + (times[-1] - times[-2] if n > 1 else 0)
    T = lambda i: times[i] if i < n else end_time          # noqa: E731
    d = [0.0] + [diff(frames[i - 1], frames[i]) for i in range(1, n)]
    events = []
    start = next((i for i in range(n) if times[i] >= ignore_start), n)

    # flashes, fades and long black: runs of mostly-dark (or mostly-light) frames
    for kind, idx in (('dark', 1), ('light', 2)):
        i = start
        while i < n:
            if st[i][idx] < 0.6:
                i += 1
                continue
            j = i
            while j + 1 < n and st[j + 1][idx] >= 0.6:
                j += 1
            before = i - 1
            duration = T(j + 1) - T(i)
            ends = j + 1 < n
            if before < start:          # starts dark: loading/splash, judged by long_black only
                if kind == 'dark' and duration > max_black and ends:
                    events.append({'type': 'long_black', 'level': 'blocking', 'start': T(i), 'end': T(j + 1)})
                i = j + 1
                continue
            drop = st[before][0] - st[i][0] if kind == 'dark' else st[i][0] - st[before][0]
            ramp, k = 0, before     # frames already moving the same way before the run = deliberate fade
            while k > max(start, before - 12) and (st[k - 1][0] - st[k][0] if kind == 'dark' else st[k][0] - st[k - 1][0]) > 3:
                ramp += 1
                k -= 1
            if kind == 'dark' and duration > max_black and ends:
                events.append({'type': 'long_black', 'level': 'blocking', 'start': T(i), 'end': T(j + 1)})
            elif ramp >= 2 and drop < 60:
                if kind == 'dark':
                    events.append({'type': 'fade_dark', 'level': 'info', 'start': T(i), 'end': T(j + 1)})
            elif ends and drop >= 35:
                events.append({'type': 'flash_' + kind, 'level': 'blocking', 'start': T(i), 'end': T(j + 1),
                               'jump': round(drop, 1)})
            i = j + 1

    # one/two-frame pops: frame(s) unlike both neighbours while the neighbours match each other
    flagged = set()
    for e in events:
        flagged.update(i for i in range(n) if e['start'] - 0.05 <= times[i] <= e['end'] + 0.05)
    POP = 40
    for i in range(max(1, start), n - 1):
        if i in flagged:
            continue
        for width in (1, 2):
            if i + width >= n:
                continue
            a, b, first, last = st[i - 1][3], st[i + width][3], st[i][3], st[i + width - 1][3]
            cells = [c for c in range(GX * GY)
                     if cdist(a[c], first[c]) > POP and cdist(last[c], b[c]) > POP and cdist(a[c], b[c]) < 10]
            whole = d[i] > 22 and diff(frames[i + width - 1], frames[i + width]) > 22 and diff(frames[i - 1], frames[i + width]) < 6
            if cells or whole:
                big = whole or len(cells) >= 3
                events.append({'type': 'one_frame_glitch' if big else 'one_frame_glitch_small',
                               'level': 'blocking' if big else 'review', 'start': T(i), 'end': T(i + width),
                               'frames': width, 'regions': [{'col': c % GX, 'row': c // GX} for c in cells][:12],
                               'grid': [GX, GY]})
                flagged.update(range(i, i + width + 1))
                break

    # flicker: a grid cell switching up/down repeatedly within one second
    for c in range(GX * GY):
        series = [s[3][c] for s in st]
        alternations, last = [], 0
        for i in range(max(1, start), n):
            if i in flagged:
                continue
            prev, cur = series[i - 1], series[i]
            ch = max(range(3), key=lambda k: abs(cur[k] - prev[k]))
            delta = cur[ch] - prev[ch]
            sgn = 1 if delta > 30 else -1 if delta < -30 else 0
            if sgn and last and sgn != last:
                alternations.append(i)
            if sgn:
                last = sgn
        i = 0
        while i < len(alternations):
            j = i
            while j + 1 < len(alternations) and times[alternations[j + 1]] - times[alternations[i]] < 1.0:
                j += 1
            count = j - i + 1
            if count >= 3:
                level = 'blocking' if count >= flicker_hz else 'review'
                events.append({'type': 'flicker' if level == 'blocking' else 'flicker_slow', 'level': level,
                               'start': T(alternations[i]), 'end': T(alternations[j]),
                               'region': {'col': c % GX, 'row': c // GX, 'of': [GX, GY]},
                               'switches_per_second': count})
                i = j + 1
            else:
                i += 1
    # merge flicker events of neighbouring cells at the same time
    merged, seen = [], []
    for e in sorted(events, key=lambda e: (e['type'], e['start'])):
        if e['type'].startswith('flicker'):
            dup = next((m for m in seen if m['type'] == e['type'] and abs(m['start'] - e['start']) < 0.6), None)
            if dup:
                if 'region' in dup:
                    dup['regions'] = [dup.pop('region')]
                dup['regions'].append(e['region'])
                dup['end'] = max(dup['end'], e['end'])
                continue
            seen.append(e)
        merged.append(e)
    for e in merged:
        e['start'], e['end'] = round(e['start'], 3), round(e['end'], 3)
    return sorted(merged, key=lambda e: e['start']), n


def save_evidence(src, is_video, files, times, events, fps, out_dir, n):
    out_dir.mkdir(parents=True, exist_ok=True)
    for k, e in enumerate([e for e in events if e['level'] != 'info'][:20]):
        shots = {'before': max(e['start'] - 0.1, 0), 'during': e['start'] + 0.004, 'after': e['end'] + 0.1}
        e['evidence'] = []
        for label, t in shots.items():
            dst = out_dir / f'{k:02d}-{e["type"]}-{label}-{t:.2f}s.png'
            if is_video:
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(src), '-frames:v', '1', str(dst)])
            else:
                idx = min(range(n), key=lambda i: abs(times[i] - t))
                shutil.copy2(files[idx], dst.with_suffix(files[idx].suffix))
                dst = dst.with_suffix(files[idx].suffix)
            if dst.exists():
                e['evidence'].append(str(dst))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', type=Path, help='video file (webm/mp4/mov) or folder of frames')
    ap.add_argument('--fps', type=float, default=25)
    ap.add_argument('--max-black', type=float, default=1.5, help='longest acceptable black screen mid-recording (s)')
    ap.add_argument('--flicker-hz', type=int, default=6, help='alternations per second treated as a flicker bug')
    ap.add_argument('--ignore-start', type=float, default=1.0, help='skip the first seconds (page/engine start)')
    ap.add_argument('--out-dir', type=Path, help='where to save evidence PNGs (default: <report folder>/glitch-frames)')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--delete-frames', action='store_true',
                    help='after saving evidence PNGs, delete the recorded frame folder to free disk (folder input only)')
    ap.add_argument('--report', type=Path)
    a = ap.parse_args()
    try:
        if a.report and a.report.exists():
            raise RuntimeError(f'report exists: {a.report}')
        if a.source.is_dir():
            frames, files, times = load_folder(a.source, a.fps)
            is_video = False
        elif a.source.is_file():
            frames, files, is_video = load_video(a.source, a.fps), [], True
            times = [i / a.fps for i in range(len(frames))]
        else:
            raise RuntimeError(f'not found: {a.source}')
        if len(frames) < 3:
            raise RuntimeError('recording too short (need at least 3 frames)')
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise RuntimeError(f'no binding object in {a.binding}')
    except (RuntimeError, OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False))
        return 2
    events, n = analyse(frames, times, a.max_black, a.flicker_hz, a.ignore_start)
    out_dir = a.out_dir or ((a.report.parent if a.report else Path('.')) / 'glitch-frames')
    save_evidence(a.source, is_video, files, times, events, a.fps, out_dir, n)
    blocking = [e for e in events if e['level'] == 'blocking']
    report = {'tool': 'audit_frame_glitches', 'source': str(a.source), 'seconds': round(times[-1], 2),
              'checked': n, 'failed': len(blocking), 'passed': not blocking,
              'checks': [{'passed': False, **e} for e in blocking], 'review': [e for e in events if e['level'] == 'review'],
              'info': [e for e in events if e['level'] == 'info'],
              'note': 'Look at the evidence PNGs of each event. Intended effects (a planned blink) can be noted in the report; real glitches must be fixed and re-recorded.'}
    if binding is not None:
        report['binding'] = binding
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if a.delete_frames and not is_video and a.source.is_dir() and not out_dir.resolve().is_relative_to(a.source.resolve()):
        shutil.rmtree(a.source, ignore_errors=True)
        report['frames_deleted'] = True
    print(json.dumps({'seconds': report['seconds'], 'blocking': len(blocking), 'review': len(report['review']),
                      'transitions': len(report['info']),
                      'events': [{k: e[k] for k in ('type', 'start', 'end') if k in e} for e in blocking + report['review']][:10]},
                     ensure_ascii=False))
    return 1 if blocking else 0


if __name__ == '__main__':
    sys.exit(main())
