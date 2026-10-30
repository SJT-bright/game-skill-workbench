"""Verify the existing official-loading presentation exception, never a game pass.

Names, purpose flags and a pass stamp do not select the exception. A frame must
bind current renderer/asset bytes, an exact runtime dump and its paired screenshot.
The original resource, timing, Retry and real-input gates remain independent.
"""
import hashlib
import json
import math
import re
from pathlib import Path

CATALOG = Path(__file__).with_name('official_loading_assets.json')
MANIFEST = 'docs/art/official-loading.json'
STANDARD = re.compile(r'(?:Loading(?: (?:engine|resources|assets|scene|game))?[.\u2026]*|Please wait[.\u2026]*|Retry|Retrying[.\u2026]*|Tap to retry|Unable to load[.\u2026]*|Loading failed[.\u2026]*|Connection (?:failed|lost)[.\u2026]*|(?:100|[0-9]{1,2})(?:\.[0-9]+)?%)', re.I)
PRIMITIVES = {'white', 'white-sprite', 'default_sprite', 'default_sprite_splash'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(project, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('use a project-relative evidence/asset path')
    path = (project / relative).resolve()
    path.relative_to(project.resolve())
    return path


def dumps_in(folders):
    for folder in folders:
        for path in sorted(Path(folder).rglob('*ui-dump*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                data['_file'] = str(path.resolve())
                yield data


def screenshot(d):
    f = Path(d['_file'])
    return f.parent / (d.get('screenshot') or f.name.replace('-ui-dump-', '-ui-').rsplit('.', 1)[0] + '.png')


def on_blend(pixel, a, b):
    # Raster antialiasing stays on the line between actual fill and backing.
    vector = [y-x for x,y in zip(a,b)]
    length = sum(v*v for v in vector)
    alpha = max(0, min(1, sum((p-x)*v for p,x,v in zip(pixel,a,vector))/length)) if length else 0
    return max(abs(p-(x+alpha*v)) for p,x,v in zip(pixel,a,vector)) <= 6


def audit(d, project, image_module, binding=None, manifest=None):
    """None = ordinary page; otherwise problems/stats, including invalid claims."""
    project = Path(project).resolve() if project is not None else None
    claim = d.get('purpose') in {'loading', 'loading_retry'} or d.get('official_loading') is not None
    if project is None or (manifest is None and not (project / MANIFEST).is_file()):
        return (['official_loading: missing project presentation evidence'], {}) if claim else None
    try:
        manifest = manifest if manifest is not None else json.loads((project / MANIFEST).read_text(encoding='utf-8'))
        rows = [r for r in manifest['frames'] if inside(project, r['dump']) == Path(d['_file']).resolve()]
        if not rows:
            return (['official_loading: frame not in presentation evidence'], {}) if claim else None
        if len(rows) != 1:
            raise ValueError('exactly one entry per dump required')
        row = rows[0]
        if manifest.get('schema') != 1 or d.get('producer') not in {'chrome_touch.dump_ui', 'ego_page.dump_ui'} or d.get('tool') != 'ui_dump' or d.get('error') or d.get('errors') or d.get('truncated'):
            raise ValueError('complete successful runtime dump required')
        if d.get('kind') != 'page' or d.get('purpose', 'other') not in {'other', 'loading', 'loading_retry'}:
            raise ValueError('ordinary home/gameplay/popup cannot be reclassified as a full loading page')
        if row.get('phase') not in {'cold_start', 'engine_resources', 'scene_switch', 'retry'}:
            raise ValueError('developer-controlled full loading/retry phase required')
        if binding is not None and manifest.get('binding') != binding:
            raise ValueError('stale/missing current build binding')
        sources = manifest['source_files']
        if not isinstance(sources, dict) or not any(Path(n).suffix in {'.js', '.ts', '.cjs', '.html', '.scene', '.prefab'} for n in sources):
            raise ValueError('current loading renderer source binding required')
        for relative, digest in sources.items():
            if sha(inside(project, relative)) != digest:
                raise ValueError('changed/missing loading source: ' + relative)
        dump_path = inside(project, row['dump'])
        shot = screenshot(d).resolve()
        if sha(dump_path) != row.get('dump_sha256') or shot != inside(project, row['screenshot']) or sha(shot) != row.get('screenshot_sha256'):
            raise ValueError('changed/mismatched dump or same-frame screenshot')
        actual = json.loads(dump_path.read_text(encoding='utf-8'))
        if {k:v for k,v in d.items() if k != '_file'} != actual:
            raise ValueError('in-memory dump differs from hashed original capture')
        vp = d.get('viewport', {})
        if row.get('screen') != d.get('screen') or row.get('viewport') != [vp.get('width'), vp.get('height')]:
            raise ValueError('exact screen and viewport required')
        screens = json.loads((project / 'docs/art/screens.json').read_text(encoding='utf-8'))
        matches = [s for s in screens['screens'] if s.get('id') == d.get('screen')]
        if len(matches) != 1 or matches[0].get('purpose') in {'home', 'gameplay', 'shop', 'map', 'result_win', 'result_fail'}:
            raise ValueError('loading state must retain its exact runtime screen identity')
        asset = inside(project, row['logo_asset'])
        if sources.get(row['logo_asset']) != sha(asset):
            raise ValueError('logo must be bound with renderer sources')
        catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
        known = [r for r in catalog['assets'] if r['sha256'] == sha(asset) and row.get('creator_version') in r['creator_versions']]
        if len(known) != 1 or (d.get('engine') and d['engine'] != row['creator_version']):
            raise ValueError('logo bytes must match a reviewed original official Creator asset/version')
        if image_module is None:
            raise ValueError('Pillow and actual screenshot required')
        im = image_module.open(shot).convert('RGB')
        original = image_module.open(asset).convert('RGBA')
        if list(original.size) != known[0]['size'] or original.getbbox() is None:
            raise ValueError('invalid original official logo')
        canvas = d.get('canvas_css')
        dpr = (d.get('page') or {}).get('dpr', 1)
        if not isinstance(canvas, list) or len(canvas) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in canvas) or min(canvas[2:]) <= 0:
            raise ValueError('actual canvas CSS box required')
        if type(dpr) not in (int, float) or not math.isfinite(dpr) or dpr <= 0 or im.size != (round(vp['width'] * dpr), round(vp['height'] * dpr)):
            raise ValueError('screenshot does not match actual viewport/DPR')
        cx, cy, cw, ch = [v * dpr for v in canvas]
        if cx < 0 or cy < 0 or cx + cw > im.width + 1 or cy + ch > im.height + 1:
            raise ValueError('canvas is outside screenshot')
        active = []
        for original_node in d.get('nodes', []):
            if original_node.get('opacity', 1) <= 0.05:
                continue
            n = original_node
            # Loading-only capture metadata must not add ordinary HUD components
            # to other layout/coverage consumers. Normalize only within this audit.
            if isinstance(n.get('loading_progress'), dict):
                n = dict(n, comps=dict(n.get('comps', {}), progress=n['loading_progress']))
            active.append(n)
        logos = [n for n in active if n.get('path') == row['logo_node']]
        if len(logos) != 1 or 'sprite' not in logos[0].get('comps', {}):
            raise ValueError('one actual rendered official logo node required')
        logo = logos[0]
        fs = logo['comps']['sprite'].get('frame_size')
        bbox = original.getbbox()
        if fs == [bbox[2] - bbox[0], bbox[3] - bbox[1]]:
            original = original.crop(bbox)
        elif fs != list(original.size):
            raise ValueError('logo frame must preserve original image/alpha-body bounds')
        masks = []
        surfaces = []
        background = im.getpixel((round(cx), round(cy)))
        has_wait = False
        has_failure_text = False
        logo_box = None
        text_boxes = []
        retry = [n for n in active if 'button' in n.get('comps', {})]
        for n in active:
            comps = n.get('comps') or {}
            r = n.get('screen') or n.get('rect')
            if not isinstance(r, list) or len(r) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in r) or min(r[2:]) <= 0:
                raise ValueError('actual visible node rectangle required')
            if r[0] + r[2] <= 0 or r[1] + r[3] <= 0 or r[0] >= 1 or r[1] >= 1:
                continue
            if min(r[:2]) < -0.001 or r[0] + r[2] > 1.001 or r[1] + r[3] > 1.001:
                raise ValueError('loading element clipped outside canvas')
            rect = [round(cx + r[0] * cw), round(cy + r[1] * ch), round(cx + (r[0] + r[2]) * cw), round(cy + (r[1] + r[3]) * ch)]
            label = comps.get('label') or comps.get('richtext') or comps.get('image_text')
            text = str((label or {}).get('string', '')).strip()
            if text:
                text_boxes.append((rect, text))
                if not STANDARD.fullmatch(text):
                    raise ValueError('game/story/nonstandard content on loading page: ' + text[:50])
                is_wait = bool(re.fullmatch(r'(?:Loading(?! failed).*|Please wait.*|Retrying.*|[0-9.]+%)', text, re.I))
                has_wait = has_wait or is_wait
                has_failure_text = has_failure_text or not is_wait
                if text.endswith('%') and not 0 <= float(text[:-1]) <= 100:
                    raise ValueError('invalid displayed loading percentage')
            if 'button' in comps:
                text_boxes.append((rect, 'Retry button'))
                below = [str(((m.get('comps') or {}).get('label') or {}).get('string', '')).strip() for m in active if m.get('path', '').startswith(n['path'] + '/')]
                if text.casefold() not in {'retry', 'tap to retry'} and not any(t.casefold() in {'retry', 'tap to retry'} for t in below):
                    raise ValueError('only the standard Retry action belongs to this loading surface')
                if not comps['button'].get('interactable', True) or comps['button'].get('enabled') is False:
                    raise ValueError('Retry is not operable')
            if 'progress' in comps:
                progress = comps['progress'].get('value')
                if type(progress) not in (int, float) or not math.isfinite(progress) or not 0 <= progress <= 1:
                    raise ValueError('invalid actual loading progress')
                has_wait = True
            if n is logo:
                logo_box = rect
            elif 'sprite' in comps:
                sprite = comps['sprite']
                if sprite.get('frame', '').lower() not in PRIMITIVES:
                    raise ValueError('extra nonofficial picture on loading page: ' + n['path'])
            if n is not logo and ('graphics' in comps or 'sprite' in comps):
                color = (comps.get('graphics') or {}).get('fillColor') or (comps.get('sprite') or {}).get('color')
                # Only the background must be neutral. Official progress fills may
                # use their standard blue; they are not game-themed pictures.
                if r[2] * r[3] >= 0.85:
                    if not color or max(color[:3]) - min(color[:3]) > 18:
                        raise ValueError('neutral loading background required')
                    continue
                parent_progress = any('progress' in m.get('comps', {}) and n['path'].startswith(m['path'] + '/') for m in active)
                parent_retry = any(n['path'] == m['path'] or n['path'].startswith(m['path'] + '/') for m in retry)
                if r[3] > 0.15 or r[2] > 0.9:
                    raise ValueError('loading control is not a bounded standard bar/Retry')
                if not ('progress' in comps or parent_progress or parent_retry):
                    raise ValueError('nonstandard loading decoration/graphic')
            if text and (r[3] > 0.10 or r[2] > 1):
                raise ValueError('loading text must not mask a full-page picture')
            if comps:
                if set(comps) - {'sprite', 'graphics', 'label', 'richtext', 'image_text', 'button', 'progress', 'block_input'}:
                    raise ValueError('unsupported visible loading component')
                if n is logo or text or 'graphics' in comps or 'sprite' in comps:
                    masks.append(rect)
                    if n is not logo:
                        surfaces.append((rect, n))
        if row['phase'] == 'retry' and len(retry) != 1:
            raise ValueError('failed frame requires exactly one visible, operable Retry')
        if row['phase'] != 'retry' and (retry or has_failure_text or not has_wait):
            raise ValueError('normal loading frame requires a standard wait/progress, not a failure state')
        if logo_box is not None:
            # Marlows r4 (user 2026-10-28): the enlarged logo's visible body covered "Unable to load. Please retry.".
            # Compare the logo's opaque pixels, scaled into its rendered box, with every text and the Retry button.
            ox0, oy0, ox1, oy1 = original.getbbox()
            width, height = logo_box[2] - logo_box[0], logo_box[3] - logo_box[1]
            body = [logo_box[0] + width * ox0 / original.width, logo_box[1] + height * oy0 / original.height,
                    logo_box[0] + width * ox1 / original.width, logo_box[1] + height * oy1 / original.height]
            for box, label_text in text_boxes:
                if min(body[2], box[2]) - max(body[0], box[0]) > 1 and min(body[3], box[3]) - max(body[1], box[1]) > 1:
                    raise ValueError('official logo overlaps loading text or Retry: ' + label_text[:40])
        for box, node in surfaces:
            comps = node.get('comps', {})
            label = comps.get('label') or comps.get('richtext') or comps.get('image_text')
            sample = list(im.crop(box).getdata())
            ancestors = [n for n in active if node['path'] == n['path'] or node['path'].startswith(n['path'] + '/')]
            backings = [((n.get('comps', {}).get('graphics') or {}).get('fillColor') or (n.get('comps', {}).get('sprite') or {}).get('color')) for n in ancestors]
            backings = [v[:3] for v in backings if isinstance(v,list) and len(v)>=3]
            backing = backings[-1] if backings else background
            if label:
                foreground = label.get('color')
                if not isinstance(foreground,list) or len(foreground)!=3:
                    raise ValueError('actual standard text colour required for pixel binding')
                if any(not on_blend(pixel,backing,foreground) for pixel in sample):
                    raise ValueError('non-text/game pixels hidden inside standard loading text')
                if not any(max(abs(p-c) for p,c in zip(pixel,backing))>6 for pixel in sample) or not any(max(abs(p-c) for p,c in zip(pixel,foreground))>6 for pixel in sample):
                    raise ValueError('loading text is absent or replaced by a solid block')
            else:
                family = [n for n in active if node['path'] == n['path'] or n['path'].startswith(node['path'] + '/')]
                colors = [background,(255,255,255),(0,0,0)]
                for item in family:
                    c = item.get('comps', {})
                    value = (c.get('graphics') or {}).get('fillColor') or (c.get('sprite') or {}).get('color') or (c.get('label') or {}).get('color')
                    if isinstance(value,list) and len(value)>=3:
                        colors.append(value[:3])
                if any(not any(on_blend(pixel,a,b) for a in colors for b in colors) for pixel in sample):
                    raise ValueError('nonstandard/game image hidden inside loading control')
        if logo_box is None:
            raise ValueError('official logo is outside the actual canvas')
        width, height = logo_box[2] - logo_box[0], logo_box[3] - logo_box[1]
        if min(width, height) <= 0:
            raise ValueError('logo has no visible pixels')
        stretch = (width / height) / (original.width / original.height)
        if max(stretch, 1 / stretch) > 1.10:
            raise ValueError('official logo is stretched (original 10% geometry limit)')
        # Source identity alone is insufficient: compare its real rendered pixels too.
        bg = im.getpixel((round(cx), round(cy)))
        crop = im.crop(logo_box)
        errors = []
        resampling = getattr(image_module, 'Resampling', image_module)
        for method in (resampling.BILINEAR, resampling.BICUBIC, resampling.LANCZOS):
            resized = original.resize((width, height), method)
            expected = image_module.new('RGBA', (width, height), (*bg, 255))
            expected.alpha_composite(resized)
            delta = [max(abs(a-b) for a,b in zip(p,q)) for p,q in zip(crop.getdata(), expected.convert('RGB').getdata())]
            errors.append((sum(delta) / len(delta), sum(v > 32 for v in delta) / len(delta)))
        if not any(avg <= 6 and bad <= 0.02 for avg, bad in errors):
            raise ValueError('screenshot does not show the unmodified original official logo')
        # Neutral background must not hide omitted title/character/scenery pixels.
        pixels = im.load()
        for y in range(round(cy), round(cy + ch)):
            for x in range(round(cx), round(cx + cw)):
                if any(a-1 <= x < c+1 and b-1 <= y < e+1 for a,b,c,e in masks):
                    continue
                value = pixels[x, y]
                if max(value) - min(value) > 18 or max(abs(v-b) for v,b in zip(value,bg)) > 6:
                    raise ValueError('unaccounted content or non-neutral backdrop in actual loading frame')
        return [], {'official_loading': True, 'phase': row['phase'], 'logo_sha256': sha(asset), 'presentation_only': True}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        return ['official_loading: ' + str(exc)], {'official_loading': False}


def main():
    """Bind already captured evidence; never manufacture a visual/runtime pass."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--dump', required=True, type=Path, action='append')
    parser.add_argument('--logo-node', required=True)
    parser.add_argument('--logo-asset', required=True)
    parser.add_argument('--creator-version', required=True)
    parser.add_argument('--phase', required=True, choices=['cold_start', 'engine_resources', 'scene_switch', 'retry'])
    parser.add_argument('--source-file', required=True, action='append')
    parser.add_argument('--binding', type=Path)
    parser.add_argument('--new-capture-set', action='store_true', help='archive old manifest and bind newly captured current-source frames')
    args = parser.parse_args()
    project = args.project.resolve()
    target = project / MANIFEST
    before = target.read_bytes() if target.exists() else None
    try:
        from PIL import Image
        previous = json.loads(before) if before else None
        data = json.loads(before) if before and not args.new_capture_set else {'schema': 1, 'source_files': {}, 'frames': []}
        binding = json.loads(args.binding.read_text())['binding'] if args.binding else None
        if binding is not None:
            data['binding'] = binding
        # A new source revision invalidates every old frame that it would relabel.
        sources = {n: sha(inside(project, n)) for n in [*args.source_file, args.logo_asset]}
        if data.get('source_files') and data['source_files'] != sources:
            raise ValueError('loading sources changed; capture a fresh frames with --new-capture-set; do not relabel old frames')
        if previous and previous.get('frames') and previous.get('binding') != data.get('binding') and not args.new_capture_set:
            raise ValueError('build binding changed; capture fresh frames with --new-capture-set')
        old_capture_hashes = {r.get('dump_sha256') for r in (previous or {}).get('frames', [])} if args.new_capture_set else set()
        data['source_files'] = sources
        checks = []
        for path in args.dump:
            path = (path if path.is_absolute() else project / path).resolve()
            d = json.loads(path.read_text())
            d['_file'] = str(path)
            if sha(path) in old_capture_hashes:
                raise ValueError('old runtime capture cannot be relabelled as a fresh capture set; recapture with the real producer')
            shot = screenshot(d).resolve()
            viewport = d.get('viewport', {})
            relative = path.relative_to(project).as_posix()
            row = {'dump': relative, 'dump_sha256': sha(path), 'screenshot': shot.relative_to(project).as_posix(),
                   'screenshot_sha256': sha(shot), 'screen': d.get('screen'),
                   'viewport': [viewport.get('width'), viewport.get('height')], 'phase': args.phase,
                   'logo_node': args.logo_node, 'logo_asset': args.logo_asset, 'creator_version': args.creator_version}
            data['frames'] = [r for r in data['frames'] if r['dump'] != relative] + [row]
            checks.append(d)
        for d in checks:
            problems, _ = audit(d, project, Image, binding, data)
            if problems:
                raise ValueError('; '.join(problems))
        if (target.read_bytes() if target.exists() else None) != before:
            raise ValueError('evidence manifest changed concurrently')
        target.parent.mkdir(parents=True, exist_ok=True)
        if before is not None and args.new_capture_set:
            archive = target.with_name('official-loading-' + hashlib.sha256(before).hexdigest()[:16] + '.json')
            if not archive.exists():
                with archive.open('xb') as saved:
                    saved.write(before)
        temporary = target.with_suffix('.json.tmp')
        with temporary.open('x', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
        print(json.dumps({'recorded': len(checks), 'path': str(target), 'scope': 'presentation evidence only; run art and original functional gates'}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(json.dumps({'error': str(exc), 'recorded': 0}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
