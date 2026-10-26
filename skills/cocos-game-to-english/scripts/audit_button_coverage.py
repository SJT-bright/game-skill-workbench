#!/usr/bin/env python3
"""Every button tapped once on the simulated iPhone, and every tap visibly did something (INPUT-05, both boards;
user 2026-10-22: "点击各个按钮都没有问题，这些按钮都点哪些要写清楚").

The button list is not typed by hand: it is read from the chrome_touch dump_ui files of the running game (every
interactable button on every dumped page and popup, only the ones on top of an open popup's mask). The taps come
from the same chrome_touch runs (report.json steps): each tap is matched to the button under the finger in the
latest dump before it, at the position where the render camera really DRAWS the button (dump "screen" rect, i.e.
where the player sees it; user 2026-10-22: a camera offset once made buttons look fine but not react), and counts as
"reacted" when a screenshot after the tap (until the next tap) differs from
the one before it (> 0.3% of the pixels), so take a dump_ui or snapshot after each tap (wait ~600 ms for animations).

Required: dumps with purpose home, result_win, result_fail, settings, settings_sound and one gameplay dump
(plus checkin / league when the game has them, see docs/features.json and docs/league/decision.json).
Camera check per dump: the Canvas drawn off-centre (> 2% of the screen) or a button drawn > 2% away from where the
layout puts it (several cameras / viewport offset) is reported as camera_offset: tap tests then show which buttons fail.
Buttons that cannot work in a browser go into docs/test/button-skip.json with a reason:
  [{"screen": "home_iphone15", "path": "Canvas/BtnRevisit", "reason": "opens the TikTok profile; checked as an explanation popup"}]

Usage:
  python audit_button_coverage.py --project <game> [--runs <folder> ...] [--binding review.json] --out report.json [--md button-list.md]
Writes the button list (page, button, text, tapped, reacted) as Markdown for the test report.
Exit codes: 0 every button tapped and reacted, 1 missing, 2 bad input.
"""
import argparse
import json
from pathlib import Path
import re

REACT = 0.003
REQUIRED = ('home', 'result_win', 'result_fail', 'settings', 'settings_sound')


def area(r):
    return max(0.0, r[2]) * max(0.0, r[3])


def under(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def text(n):
    for k in ('label', 'richtext', 'image_text'):
        s = str((n.get('comps', {}).get(k) or {}).get('string', '')).strip()
        if s:
            return s
    return ''


def buttons_of(dump):
    nodes = [n for n in dump.get('nodes', []) if n.get('opacity', 1) > 0.05 and area(n['rect']) > 0]
    masks = [n for n in nodes if n['comps'].get('block_input') and area(n['rect']) >= 0.8]
    top_mask = max((m.get('order', 0) for m in masks), default=-1)
    out = []
    for n in nodes:
        b = n['comps'].get('button')
        if not b or not b.get('interactable', True) or b.get('enabled') is False:
            continue
        if n.get('order', 0) < top_mask:          # under an open popup's mask: not reachable now
            continue
        label = next((text(m) for m in nodes if under(m['path'], n['path']) and text(m)), '') or \
            str((n['comps'].get('sprite') or {}).get('frame', '')) or n['name']
        out.append({'path': n['path'], 'name': n['name'], 'label': label[:40], 'rect': n.get('screen') or n['rect'],
                    'layout_rect': n['rect'], 'drawn': bool(n.get('screen')), 'order': n.get('order', 0)})
    return out


def camera_problems(dump):
    """Where the camera draws things vs where the layout puts them (both normalised to the game canvas)."""
    out = []
    nodes = [n for n in dump.get('nodes', []) if n.get('screen')]
    canvas = next((n for n in sorted(dump.get('nodes', []), key=lambda n: n.get('depth', 0))
                   if n.get('screen') and all(abs(a - b) < 0.02 for a, b in zip(n['rect'], (0, 0, 1, 1)))), None)
    if not nodes or not canvas:
        return out
    cs = canvas['screen']
    cx, cy = cs[0] + cs[2] / 2, cs[1] + cs[3] / 2
    if abs(cx - 0.5) > 0.02 or abs(cy - 0.5) > 0.02:
        out.append('camera_offset: %s is drawn %.0f%% right / %.0f%% down of the centre (render camera or viewport offset): what the '
                   'player sees is not where the game expects it' % (dump.get('screen'), (cx - 0.5) * 100, (cy - 0.5) * 100))
    for n in dump.get('nodes', []):
        if not n['comps'].get('button') or not n.get('screen'):
            continue
        r, sc = n['rect'], n['screen']
        ex = cs[0] + (r[0] + r[2] / 2) * cs[2]
        ey = cs[1] + (r[1] + r[3] / 2) * cs[3]
        if abs(sc[0] + sc[2] / 2 - ex) > 0.02 or abs(sc[1] + sc[3] / 2 - ey) > 0.02:
            out.append('camera_offset: %s %s is drawn %.0f%%/%.0f%% away from its layout position (another camera or viewport)'
                       % (dump.get('screen'), n['path'], (sc[0] + sc[2] / 2 - ex) * 100, (sc[1] + sc[3] / 2 - ey) * 100))
    return out


def shot_diff(a, b, image_module):
    if not a or not b or not a.is_file() or not b.is_file():
        return None
    with image_module.open(a) as ia, image_module.open(b) as ib:
        ia = ia.convert('RGB').resize((90, 195))
        ib = ib.convert('RGB').resize((90, 195))
        pa, pb = ia.load(), ib.load()
        changed = sum(1 for y in range(195) for x in range(90) if sum(abs(u - v) for u, v in zip(pa[x, y], pb[x, y])) > 30)
    return changed / (90 * 195)


def step_files(run, i):
    return sorted(run.glob('%03d-*' % i))


def read_runs(folders):
    runs = []
    for folder in folders:
        for rep in sorted(Path(folder).rglob('report.json')):
            try:
                data = json.loads(rep.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get('steps'), list):
                runs.append((rep.parent, data))
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--runs', type=Path, nargs='*', help='chrome_touch output folders (default <project>/docs/test)')
    ap.add_argument('--skip', type=Path, help='default <project>/docs/test/button-skip.json')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--md', type=Path)
    a = ap.parse_args()
    try:
        from PIL import Image
    except ImportError:
        ap.error('Pillow is needed to compare screenshots: pip install pillow')
    proj = a.project.resolve()
    runs = read_runs(a.runs or [proj / 'docs' / 'test'])
    skip_file = a.skip or proj / 'docs' / 'test' / 'button-skip.json'
    skips, problems = {}, []
    if skip_file.is_file():
        try:
            for s in json.loads(skip_file.read_text(encoding='utf-8')):
                if len(str(s.get('reason', '')).strip()) < 8:
                    problems.append('button-skip.json: %s %s needs a real reason' % (s.get('screen'), s.get('path')))
                else:
                    skips[(s.get('screen'), s.get('path'))] = s['reason']
        except (OSError, ValueError, AttributeError) as exc:
            problems.append('button-skip.json unreadable: %s' % exc)
    inventory, purposes, kinds, devices = {}, set(), set(), set()
    for run, data in runs:
        devices.add(str(data.get('device') or 'custom'))
        last_dump = None
        steps = data['steps']
        tap_steps = [i for i, s in enumerate(steps) if isinstance(s.get('action'), dict) and s['action'].get('type') == 'tap']
        for i, step in enumerate(steps):
            action = step.get('action') if isinstance(step.get('action'), dict) else {}
            if action.get('type') == 'dump_ui':
                f = run / ('%03d-ui-dump-%s.json' % (i, action.get('screen')))
                try:
                    last_dump = json.loads(f.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    problems.append('%s: dump of step %d missing' % (run.name, i)); last_dump = None; continue
                purposes.add(last_dump.get('purpose', 'other')); kinds.add(last_dump.get('kind'))
                for c in camera_problems(last_dump):
                    if c not in problems:
                        problems.append(c)
                for b in buttons_of(last_dump):
                    key = (last_dump.get('screen'), b['path'])
                    entry = inventory.setdefault(key, dict(b, screen=last_dump.get('screen'), purpose=last_dump.get('purpose', 'other'),
                                                           taps=0, reacted=0))
                    entry['rect'] = b['rect']
            elif action.get('type') == 'tap' and last_dump and 'x' in action:
                cx, cy, cw, ch = last_dump.get('canvas_css') or [0, 0, 1, 1]
                nx, ny = (action['x'] - cx) / cw, (action['y'] - cy) / ch
                hit = [b for b in buttons_of(last_dump) if b['rect'][0] <= nx <= b['rect'][0] + b['rect'][2]
                       and b['rect'][1] <= ny <= b['rect'][1] + b['rect'][3]]
                if not hit:
                    continue
                b = max(hit, key=lambda b: b['order'])
                entry = inventory.setdefault((last_dump.get('screen'), b['path']), dict(b, screen=last_dump.get('screen'),
                                             purpose=last_dump.get('purpose', 'other'), taps=0, reacted=0))
                entry['taps'] += 1
                before = next((f for f in step_files(run, i - 1) if f.suffix == '.png'), None)
                nxt = next((t for t in tap_steps if t > i), len(steps))
                diffs = [shot_diff(before, f, Image) for j in range(i, nxt) for f in step_files(run, j) if f.suffix == '.png']
                if any(d is not None and d > REACT for d in diffs):
                    entry['reacted'] += 1
    need = list(REQUIRED)
    for path, key, name in (('docs/features.json', 'daily_checkin', 'checkin'), ('docs/league/decision.json', 'decision', 'league')):
        try:
            v = json.loads((proj / path).read_text(encoding='utf-8-sig')).get(key)
            if v is True or v in ('add', 'keep_original'):
                need.append(name)
        except (OSError, ValueError, AttributeError):
            pass
    from audit_level_plan import plan_mode
    if plan_mode(proj) == 'levels' and __import__('maintenance_scope').required_map(proj) and 'map' not in need:
        need.append('map')
    missing_pages = [p for p in need if p not in purposes] + ([] if 'gameplay' in kinds else ['gameplay'])
    if not runs:
        problems.append('no chrome_touch runs found: run the phone simulation with dump_ui on every page and tap every button')
    if missing_pages:
        problems.append('pages never dumped in the tap runs: ' + ', '.join(missing_pages))
    rows, untapped, silent = [], [], []
    for key, e in sorted(inventory.items(), key=lambda kv: (str(kv[0][0]), kv[1]['order'])):
        skipped = skips.get(key)
        state = 'skipped' if skipped else ('ok' if e['reacted'] else ('no_reaction' if e['taps'] else 'not_tapped'))
        rows.append({'screen': key[0], 'purpose': e['purpose'], 'path': key[1], 'label': e['label'], 'taps': e['taps'],
                     'reacted': e['reacted'], 'state': state, 'skip_reason': skipped or ''})
        if state == 'not_tapped':
            untapped.append('%s %s "%s"' % (key[0], key[1], e['label']))
        elif state == 'no_reaction':
            silent.append('%s %s "%s"' % (key[0], key[1], e['label']))
    if untapped:
        problems.append('%d buttons never tapped: %s' % (len(untapped), '; '.join(untapped[:8])))
    if silent:
        problems.append('%d buttons tapped but nothing changed on screen (点了没反应): %s' % (len(silent), '; '.join(silent[:8])))
    report = {'tool': 'audit_button_coverage', 'schema': 1, 'devices': sorted(devices), 'buttons': len(rows),
              'tapped_ok': sum(r['state'] == 'ok' for r in rows), 'skipped': sum(r['state'] == 'skipped' for r in rows),
              'checked': len(rows), 'failed': len(problems), 'passed': not problems and bool(rows),
              'status': 'pass' if not problems and rows else 'fail', 'problems': problems, 'rows': rows,
              'boundary': 'Taps on a simulated iPhone in Chromium (Ego Lite or Chrome); a visible screen change is the reaction. '
                          'Whether the reaction is the RIGHT one is checked by the flow tests (AD/CLAIM/FLOW items).'}
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if a.md:
        state_zh = {'ok': '点过，有反应', 'no_reaction': '**点了没反应**', 'not_tapped': '**没点过**', 'skipped': '跳过'}
        md = ['# 按钮清单（从运行中的游戏读出，模拟 %s）' % '、'.join(sorted(devices)), '',
              '共 %d 个按钮：%d 个点过且有反应，%d 个跳过。' % (len(rows), report['tapped_ok'], report['skipped']), '',
              '| 页面 | 按钮 | 文字/图 | 点了几次 | 结果 |', '| --- | --- | --- | --- | --- |']
        md += ['| %s | %s | %s | %d | %s%s |' % (r['screen'], r['path'].split('/')[-1], r['label'].replace('|', '/'), r['taps'],
                                               state_zh[r['state']], ('：' + r['skip_reason']) if r['skip_reason'] else '') for r in rows]
        if problems:
            md += ['', '## 需处理', ''] + ['- ' + p for p in problems]
        a.md.parent.mkdir(parents=True, exist_ok=True)
        a.md.write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'buttons': len(rows), 'tapped_ok': report['tapped_ok'], 'failed': len(problems),
                      'problems': [p[:200] for p in problems][:6], 'report': str(a.out)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
