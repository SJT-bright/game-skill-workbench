#!/usr/bin/env python3
"""Source-stage TikTok package size estimate (v7.5, Germ2048 item 3). Read-only, static.

Estimates, before any build, what a Cocos Creator 2.4 / 3.x project will put into the TikTok upload package:
  - total bytes that reach the TikTok build: every non-.meta file under assets/ plus build-templates/bytedance/
    (build-templates/wechatgame open-data domains, web-mobile templates, docs, audio_work ... never reach it);
  - main-package bytes: everything outside asset bundles whose ByteDance compression type is "subpackage", plus a
    fixed engine/adapter allowance;
  - each image's pixel size against its largest display size in a prefab/scene; > 3x is listed with a suggested
    size (2.75x the display size, the iPhone Pro Max factor Germ2048 v3 used).
Verdict: estimated total > 30,000,000 bytes, or estimated main > 4,000,000 bytes while assets/resources is not a
ByteDance subpackage -> "needs_fix" (exit 1). Otherwise exit 0. The estimate is not the real package: the final
gate is still the native ZIP check (verify_native_zip.py / build_checked_zip.py).

  python3 audit_package_estimate.py --project <cocos project> [--out report.json]
"""
import argparse
import json
import math
import re
from pathlib import Path
import struct
import sys

from audit_image_clarity import content_size, node_scale

TOTAL_LIMIT = 30_000_000
MAIN_LIMIT = 4_000_000
ENGINE_ALLOWANCE = {'2': 1_500_000, '3': 2_600_000}   # engine + adapter + boot files; Germ2048 v3 2.4.15 build: 1.36 MB
# Scenes/prefabs/animations are re-serialized into packed import JSON (Germ2048 v3: 777 KB source -> 74 KB built).
SERIALIZED_FACTOR = 0.15
SERIALIZED = ('.fire', '.scene', '.prefab', '.anim')
RATIO_LIMIT = 3.0
SUGGEST_FACTOR = 2.75
SKIP = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles'}
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')


def image_size(path):
    """(width, height) from the file header, or None. PNG / JPEG / WebP, no Pillow needed."""
    try:
        with open(path, 'rb') as f:
            head = f.read(64)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                return struct.unpack('>II', head[16:24])
            if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
                kind = head[12:16]
                if kind == b'VP8 ':
                    w, h = struct.unpack('<HH', head[26:30]); return w & 0x3fff, h & 0x3fff
                if kind == b'VP8L':
                    b = head[21:25]; return 1 + (((b[1] & 0x3f) << 8) | b[0]), 1 + (((b[3] & 0xf) << 10) | (b[2] << 2) | ((b[1] & 0xc0) >> 6))
                if kind == b'VP8X':
                    return 1 + int.from_bytes(head[24:27], 'little'), 1 + int.from_bytes(head[27:30], 'little')
                return None
            if head[:2] == b'\xff\xd8':
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xff:
                        return None
                    if marker[1] in (0xd8, 0x01) or 0xd0 <= marker[1] <= 0xd7:
                        continue
                    length = struct.unpack('>H', f.read(2))[0]
                    if marker[1] in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                        h, w = struct.unpack('>xHH', f.read(5)); return w, h
                    f.seek(length - 2, 1)
    except (OSError, struct.error):
        return None
    return None


def files(root):
    for p in sorted(root.rglob('*')):
        if p.is_file() and not SKIP & {x.lower() for x in p.relative_to(root).parts} and p.name != '.DS_Store':
            yield p


def bundles(project):
    """folder path (relative to assets/) -> ByteDance compression type, for every Asset Bundle folder."""
    out = {}
    assets = project / 'assets'
    for meta in assets.rglob('*.meta'):
        folder = meta.with_suffix('')
        if not folder.is_dir():
            continue
        try:
            m = json.loads(meta.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        if isinstance(m, dict) and m.get('isBundle'):
            ctype = m.get('compressionType') or {}
            out[folder.relative_to(assets).as_posix()] = ctype.get('bytedance') if isinstance(ctype, dict) else None
    if (assets / 'resources').is_dir() and 'resources' not in out:
        out['resources'] = None   # built-in bundle: always built whole, even when its .meta lacks isBundle
    return out


UUID_REF = re.compile(r'"__uuid__"\s*:\s*"([0-9a-fA-F-]{20,}[^"]*)"')


def referenced_uuids(project):
    """Every asset uuid named by a scene, prefab, animation, material or other serialized asset under assets/."""
    refs = set()
    for p in files(project / 'assets'):
        if p.suffix in ('.fire', '.scene', '.prefab', '.anim', '.mtl', '.json', '.pmtl', '.effect', '.labelatlas', '.plist'):
            try:
                refs.update(m.split('@')[0] for m in UUID_REF.findall(p.read_text(encoding='utf-8', errors='ignore')))
            except OSError:
                pass
    return refs


def asset_uuids(path):
    """The asset's own uuid and its sub-asset (sprite frame) uuids, from its .meta file."""
    try:
        m = json.loads(Path(str(path) + '.meta').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return set()
    if not isinstance(m, dict):
        return set()
    out = {m.get('uuid')}
    for s in (m.get('subMetas') or {}).values():
        if isinstance(s, dict):
            out.add(s.get('uuid'))
            for t in (s.get('subMetas') or {}).values():
                if isinstance(t, dict):
                    out.add(t.get('uuid'))
    return {u for u in out if u}


def engine_major(project):
    try:
        v = str(json.loads((project / 'project.json').read_text(encoding='utf-8-sig')).get('version') or '')
    except (OSError, ValueError):
        v = ''
    if not v and (project / 'package.json').is_file():
        try:
            v = str((json.loads((project / 'package.json').read_text(encoding='utf-8-sig')).get('creator') or {}).get('version') or '')
        except (OSError, ValueError):
            v = ''
    return v, ('3' if v.startswith('3') else '2')


def display_sizes(project):
    """sprite-frame uuid -> largest (width, height) it is shown at in any scene/prefab (simple sprites only)."""
    best = {}
    for f in sorted((project / 'assets').rglob('*')):
        if f.suffix not in ('.fire', '.scene', '.prefab') or not f.is_file():
            continue
        try:
            objs = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(objs, list):
            continue
        cache = {}
        for o in objs:
            if not isinstance(o, dict) or o.get('__type__') != 'cc.Sprite' or o.get('_type') in (1, 2):
                continue
            uuid = (o.get('_spriteFrame') or {}).get('__uuid__')
            node = (o.get('node') or {}).get('__id__')
            if not uuid or not isinstance(node, int) or not 0 <= node < len(objs):
                continue
            try:
                w, h = content_size(objs, node)
                sx, sy = node_scale(objs, node, cache)
            except (TypeError, KeyError, IndexError, AttributeError):
                continue
            dw, dh = abs(w * sx), abs(h * sy)
            if dw <= 0 or dh <= 0:
                continue
            old = best.get(uuid)
            if not old or dw * dh > old[0] * old[1]:
                best[uuid] = (dw, dh, f.relative_to(project).as_posix())
    return best


def audit(project):
    project = Path(project).resolve()
    assets = project / 'assets'
    if not assets.is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    version, major = engine_major(project)
    bset = bundles(project)
    sub = sorted(k for k, v in bset.items() if v == 'subpackage')
    in_bundle = lambda rel: any(rel == b or rel.startswith(b + '/') for b in bset)
    referenced = referenced_uuids(project)
    total = main = unused = 0
    by_top = {}
    for p in files(assets):
        if p.suffix == '.meta':
            continue
        rel = p.relative_to(assets).as_posix()
        size = p.stat().st_size
        if p.suffix in SERIALIZED:
            size = int(size * SERIALIZED_FACTOR)
        # Outside bundles Cocos builds only what a scene/prefab/other asset references (scenes and scripts always).
        if not in_bundle(rel) and p.suffix not in ('.fire', '.scene', '.ts', '.js') and not asset_uuids(p) & referenced:
            unused += size
            continue
        total += size
        if not any(rel == s or rel.startswith(s + '/') for s in sub):
            main += size
        top = rel.split('/')[0]
        by_top[top] = by_top.get(top, 0) + size
    templates = project / 'build-templates' / 'bytedance'
    template_bytes = sum(p.stat().st_size for p in files(templates)) if templates.is_dir() else 0
    allowance = ENGINE_ALLOWANCE[major]
    est_total = total + template_bytes + allowance
    est_main = main + template_bytes + allowance
    # images: pixel size vs largest display size
    shown = display_sizes(project)
    big = []
    for meta in files(assets):
        if not meta.name.lower().endswith(tuple(s + '.meta' for s in IMAGE_SUFFIXES)):
            continue
        image = meta.with_suffix('')
        dims = image_size(image) if image.is_file() else None
        if not dims:
            continue
        try:
            m = json.loads(meta.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        uses = [shown[s['uuid']] for s in (m.get('subMetas') or {}).values() if isinstance(s, dict) and s.get('uuid') in shown]
        if not uses:
            continue
        frames = [s for s in (m.get('subMetas') or {}).values() if isinstance(s, dict)]
        if len(frames) > 1:
            continue   # atlas / multi-frame sheet: one frame's display size says nothing about the sheet
        dw, dh, where = max(uses, key=lambda u: u[0] * u[1])
        ratio = max(dims[0] / dw, dims[1] / dh)
        if ratio > RATIO_LIMIT:
            scale = min(1.0, SUGGEST_FACTOR * max(dw / dims[0], dh / dims[1]))
            big.append({'image': image.relative_to(project).as_posix(), 'bytes': image.stat().st_size, 'pixels': list(dims),
                        'display': [round(dw), round(dh)], 'shown_in': where, 'ratio': round(ratio, 2),
                        'suggested': [max(1, math.ceil(dims[0] * scale)), max(1, math.ceil(dims[1] * scale))]})
    big.sort(key=lambda x: -x['bytes'])
    resources_sub = bset.get('resources') == 'subpackage'
    problems = []
    if est_total > TOTAL_LIMIT:
        problems.append('estimated total %d bytes > %d (TikTok upload limit)' % (est_total, TOTAL_LIMIT))
    if est_main > MAIN_LIMIT and not resources_sub:
        problems.append('estimated main package %d bytes > %d and assets/resources is not a ByteDance subpackage' % (est_main, MAIN_LIMIT))
    warnings = []
    if est_main > MAIN_LIMIT and resources_sub:
        warnings.append('estimated main package %d bytes > %d even with resources as a subpackage: move more into bundles' % (est_main, MAIN_LIMIT))
    return {'tool': 'audit_package_estimate', 'schema': 1, 'project': str(project), 'engine': version,
            'passed': not problems, 'status': 'pass' if not problems else 'needs_fix', 'problems': problems, 'warnings': warnings,
            'estimate': {'total_bytes': est_total, 'main_bytes': est_main, 'asset_bytes': total, 'main_asset_bytes': main,
                         'unreferenced_outside_bundles_bytes': unused,
                         'bytedance_template_bytes': template_bytes, 'engine_allowance_bytes': allowance,
                         'total_limit': TOTAL_LIMIT, 'main_limit': MAIN_LIMIT},
            'bundles': bset, 'resources_is_bytedance_subpackage': resources_sub, 'by_top_folder': by_top,
            'oversized_images': big, 'oversized_image_bytes': sum(x['bytes'] for x in big),
            'boundary': 'static estimate from source files; the native ZIP check is the real size gate'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        r = audit(a.project)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False)); return 2
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: r[k] for k in ('status', 'problems', 'warnings', 'estimate', 'resources_is_bytedance_subpackage',
                                        'oversized_image_bytes')} | {'oversized_images': r['oversized_images'][:8]}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
