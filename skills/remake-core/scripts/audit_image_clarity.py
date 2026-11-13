#!/usr/bin/env python3
"""Read-only static image resolution measurements for Cocos scenes/prefabs.

Default: ordinary/background 1.0x source/render reference, advisory only; actual visible clarity is the standard. Explicit
strict preset uses ordinary 2.0x/background 1.5x, blocking. Project JSON and CLI can
adjust thresholds/severity; see --clarity-* help. Ratios do not replace actual
visual review or missing glyph, crop, distortion, contrast and text-size checks.
Sliced/tiled and code-assigned sprites require independent runtime/screenshot review.
Exit 0: no blocking resolution findings; 1: blocking findings; 2: invalid input/not_run.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from clarity_policy import add_arguments, from_args, measure

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts'))
from check_guard import engine_of, zero_items  # P20 shared guard

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}


def walk(project, suffixes):
    root = project / 'assets'
    for p in sorted(root.rglob('*')):
        if p.suffix in suffixes and p.is_file() and not SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}:
            yield p


def frame_sizes(project, files=None):
    """sprite-frame uuid -> (name, raw width, raw height). files (a dict, optional): also gets uuid -> the picture's
    project-relative path (art_check checks an exempt original against its bytes, 美工skill 2026-11-05)."""
    frames = {}
    for meta in walk(project, {'.meta'}):
        if not meta.name.lower().endswith(('.png.meta', '.jpg.meta', '.jpeg.meta', '.webp.meta')):
            continue
        try:
            m = json.loads(meta.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        name = meta.name[:-5]
        for key, sub in (m.get('subMetas') or {}).items():
            if not isinstance(sub, dict):
                continue
            data = sub.get('userData') if isinstance(sub.get('userData'), dict) else sub   # 3.x keeps sizes in userData
            w, h = data.get('rawWidth') or data.get('width'), data.get('rawHeight') or data.get('height')
            if sub.get('uuid') and w and h:
                frames[sub['uuid']] = (name + ('' if key in ('f9941', name.rsplit('.', 1)[0]) else ':' + key), w, h)
                if isinstance(files, dict):
                    files[sub['uuid']] = (meta.parent / name).relative_to(project).as_posix()
    return frames


def node_scale(objs, idx, cache):
    if idx in cache:
        return cache[idx]
    node = objs[idx] if 0 <= idx < len(objs) else {}
    sx = sy = 1.0
    trs = node.get('_trs')
    if isinstance(trs, dict) and isinstance(trs.get('array'), list) and len(trs['array']) >= 9:
        sx, sy = trs['array'][7], trs['array'][8]                    # 2.4
    elif isinstance(node.get('_lscale'), dict):
        sx, sy = node['_lscale'].get('x', 1), node['_lscale'].get('y', 1)   # 3.x
    else:
        sx = node.get('_scaleX', node.get('_scale', {}).get('x', 1) if isinstance(node.get('_scale'), dict) else 1)
        sy = node.get('_scaleY', node.get('_scale', {}).get('y', 1) if isinstance(node.get('_scale'), dict) else 1)
    cache[idx] = (abs(sx or 0), abs(sy or 0))                       # placeholder against cycles
    parent = node.get('_parent')
    if isinstance(parent, dict) and isinstance(parent.get('__id__'), int):
        px, py = node_scale(objs, parent['__id__'], cache)
        cache[idx] = (abs(sx) * px, abs(sy) * py)
    return cache[idx]


def content_size(objs, node_idx):
    node = objs[node_idx]
    size = node.get('_contentSize')
    if isinstance(size, dict):
        return size.get('width', 0), size.get('height', 0)
    for comp in node.get('_components', []):                       # 3.x: size lives on cc.UITransform
        c = objs[comp['__id__']] if isinstance(comp, dict) and isinstance(comp.get('__id__'), int) else {}
        if c.get('__type__') == 'cc.UITransform' and isinstance(c.get('_contentSize'), dict):
            return c['_contentSize'].get('width', 0), c['_contentSize'].get('height', 0)
    return 0, 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--min-display', type=float, default=24, help='ignore sprites smaller than this on screen (design px)')
    ap.add_argument('--out', type=Path)
    add_arguments(ap)
    a = ap.parse_args()
    try:
        policy = from_args(a)
    except ValueError as exc:
        ap.error(str(exc))
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'status': 'error', 'error': f'no assets folder in {a.project}'}))
        return 2
    if a.out and a.out.exists():
        print(json.dumps({'status': 'error', 'error': f'output exists: {a.out}'}))
        return 2
    files = {}
    frames = frame_sizes(a.project, files)
    findings, items, checked, seen = [], [], 0, set()
    for f in walk(a.project, {'.fire', '.scene', '.prefab'}):
        try:
            objs = json.loads(f.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        if not isinstance(objs, list):
            continue
        cache = {}
        for o in objs:
            if not isinstance(o, dict) or o.get('__type__') != 'cc.Sprite':
                continue
            if o.get('_type') in (1, 2):                                   # SLICED / TILED
                continue
            uuid = (o.get('_spriteFrame') or {}).get('__uuid__')
            node_ref = (o.get('node') or {}).get('__id__')
            if not uuid or uuid not in frames or not isinstance(node_ref, int):
                continue
            w, h = content_size(objs, node_ref)
            sx, sy = node_scale(objs, node_ref, cache)
            dw, dh = w * sx, h * sy
            if max(dw, dh) < a.min_display:
                continue
            name, rw, rh = frames[uuid]
            node_name = objs[node_ref].get('_name', '')
            background = bool(re.search(r'(?:^|[/_. -])(?:bg|background|backdrop)(?:[0-9]|[/_. -]|$)', node_name + ' ' + name, re.I))
            metric = measure([rw, rh], [dw, dh], policy, background=background)
            checked += 1
            key = (f.relative_to(a.project).as_posix(), node_name, name)
            if key in seen:
                continue
            seen.add(key)
            both_upscaled = max(metric['axis_source_render_ratios']) < 1.0
            item = {'file': key[0], 'node': node_name, 'image': name,
                    **metric, 'display': [round(dw, 3), round(dh, 3)],
                    'ratio': round(max(dw / rw, dh / rh), 6),
                    'ratio_definition': 'legacy ratio = render/source; source_render_ratio is source/render',
                    'render_units': 'scene node units multiplied by ancestor scale; not phone CSS pixels',
                    'level': 'upscaled' if both_upscaled else 'below_threshold',
                    **({'image_path': files[uuid]} if uuid in files else {})}
            items.append(item)
            if metric['below_threshold']:
                findings.append(item)
    findings.sort(key=lambda x: x['source_render_ratio'])
    upscaled = sum(1 for x in findings if x['level'] == 'upscaled')
    blocked = sum(1 for x in findings if x['blocking'])
    below_2x = sum(1 for x in items if x['source_render_ratio'] < 2 and x['level'] != 'upscaled')
    report = {'tool': 'audit_image_clarity', 'checked': checked, 'upscaled': upscaled,
              'below_2x': below_2x, 'below_threshold': len(findings), 'blocking_count': blocked,
              'advisory_count': sum(x['severity'] == 'advisory' for x in findings),
              'findings': findings, 'items': items, 'clarity_policy': policy,
              'note': 'Resolution measurements only; no automatic regeneration. Static scene/prefab sprites only; sliced/tiled skipped; code-assigned sprites need runtime measurements and actual visual review.'}
    # P20 (问题普查 T20): 0 sprites checked (for example a Cocos 3.x project, whose sprite frames this static reader
    # does not resolve) used to print exit 0 like a pass. It is "not_run" now, with the engine, exit 2.
    report['engine'] = engine_of(a.project)
    report['passed'] = not blocked
    report['status'] = 'fail' if blocked else ('advisory' if findings else 'pass')
    zero_items(report, what='场景和预制体里没有能对上图片尺寸的 Sprite（Cocos %s）' % (report['engine']['version'] or report['engine']['major']),
               need='运行时 dump 的 low_res 检查（art_check 已做）', engine=report['engine'])
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    # R4I1 (Round4 #4): the printed report starts with the engine and the number of items actually checked
    print(json.dumps({'engine': report['engine'], 'checked': checked, 'upscaled': upscaled, 'below_2x': below_2x, 'below_threshold': len(findings), 'blocking_count': blocked, 'clarity_policy': policy,
                      'worst': findings[:8], 'status': report.get('status', 'checked'),
                      **({'reason': report['reason']} if report.get('status') == 'not_run' else {})}, ensure_ascii=False))
    if report.get('status') == 'not_run':
        return 2
    return 1 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
