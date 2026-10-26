#!/usr/bin/env python3
"""Static image-clarity check: compare each Sprite's display size with its source image size.

Read-only. Works on Cocos 2.4 and 3.x projects (scenes .fire/.scene and .prefab).
For every Sprite with a sprite frame it computes
    ratio = display size / source size   (display = node content size x parent scales)
  upscaled  - enlarged on both axes (shown larger than the image itself; blurry, must fix)
  below 2x  - worst axis ratio > 0.5, i.e. source under the 2x rule (should fix); bars or lines
              stretched on one axis land here instead of "upscaled"
Sliced (nine-slice) and tiled sprites are skipped (stretching is intended), as are
sprites set only from code (they are not in scene files) - check those on screenshots.

Usage:
  python audit_image_clarity.py --project GAME_PROJECT [--min-display 24] [--out result.json]
Exit codes: 0 no upscaled images, 1 upscaled images found, 2 bad input.
Images "below 2x" are reported for fixing but do not change the exit code.
"""
import argparse
import json
from pathlib import Path

SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}


def walk(project, suffixes):
    root = project / 'assets'
    for p in sorted(root.rglob('*')):
        if p.suffix in suffixes and p.is_file() and not SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}:
            yield p


def frame_sizes(project):
    """sprite-frame uuid -> (name, raw width, raw height)"""
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
    a = ap.parse_args()
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'status': 'error', 'error': f'no assets folder in {a.project}'}))
        return 2
    if a.out and a.out.exists():
        print(json.dumps({'status': 'error', 'error': f'output exists: {a.out}'}))
        return 2
    frames = frame_sizes(a.project)
    findings, checked, seen = [], 0, set()
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
            ratio = max(dw / rw, dh / rh)          # worst axis: used for the 2x rule
            both = min(dw / rw, dh / rh)           # both axes enlarged = really upscaled (bars stretched one way are not)
            checked += 1
            if ratio <= 0.5:
                continue
            node_name = objs[node_ref].get('_name', '')
            key = (f.relative_to(a.project).as_posix(), node_name, name)
            if key in seen:
                continue
            seen.add(key)
            findings.append({'file': key[0], 'node': node_name, 'image': name,
                             'source': [rw, rh], 'display': [round(dw), round(dh)], 'ratio': round(ratio, 2),
                             'level': 'upscaled' if both > 1.0 else 'below_2x'})
    findings.sort(key=lambda x: -x['ratio'])
    upscaled = sum(1 for x in findings if x['level'] == 'upscaled')
    report = {'tool': 'audit_image_clarity', 'checked': checked, 'upscaled': upscaled,
              'below_2x': len(findings) - upscaled, 'findings': findings,
              'note': 'Static scene/prefab sprites only; sliced/tiled skipped; code-assigned sprites need screenshot review.'}
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checked': checked, 'upscaled': upscaled, 'below_2x': len(findings) - upscaled,
                      'worst': findings[:8]}, ensure_ascii=False))
    return 1 if upscaled else 0


if __name__ == '__main__':
    raise SystemExit(main())
