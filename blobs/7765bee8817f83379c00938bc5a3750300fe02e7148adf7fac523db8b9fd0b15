#!/usr/bin/env python3
"""Before/after image comparison for tiktok_finalize (v7.7 design 3.6, Q3: banded images one by one).

    python3 finalize_images_compare.py --project <Cocos project> [--native <build>] \
        [--shots-before <dir> --shots-after <dir>] [--out <dir>]

For every image under <project>/assets it pairs
  BEFORE = the original kept by images.py in <project>/.tiktok-kit/originals/ (else the project file itself)
  AFTER  = what the player gets: the build file of the same uuid when --native is given; otherwise the project
           file run through the same pngquant arguments png.py uses (unless image-overrides says quantize=false)
and writes to <project>/.tiktok-kit/image-compare/ (or --out):
  pairs/<n>.png          before | after side by side (scaled for viewing)
  pages/<name>.png       page screenshots side by side, when --shots-before/--shots-after hold files of the
                         same name (home.png, level1.png, shop.png from the runtime tools before and after)
  index.html             everything, images with a banding risk first
  report.json            per image: sizes, format, PSNR, smooth-area share, flattened share, verdict
  suggested-overrides.json  {"images": {...}} entries for the images marked "check", ready to copy into
                         <project>/.tiktok-kit/image-overrides.json after the art check agrees

Banding heuristic (PIL only): pixels whose original has a gentle gradient (edge strength 1-8) form the smooth
area; banding shows as those pixels becoming flat (edge 0) after quantisation. smooth share >= 15 % and flattened
share >= 50 % -> "check". It only ranks images for a human look; it does not decide anything by itself.
Read-only for the project except the output folder.
"""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from tiktok_finalize_steps import png as pngstep  # noqa: E402

IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', '.tiktok-kit'}
SMOOTH_MIN, FLAT_MIN = 0.15, 0.50
VIEW_H = 320


def _img():
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    return Image, ImageChops, ImageFilter, ImageStat


def project_images(project):
    root = project / 'assets'
    out = []
    for p in sorted(root.rglob('*')) if root.is_dir() else []:
        if p.is_file() and p.suffix.lower() in IMAGE_EXT and \
                not SKIP_DIRS & {x.lower() for x in p.relative_to(project).parts}:
            out.append(p)
    return out


def original_of(project, current):
    """Backup written by images.py for this image (same stem, any image extension), else None."""
    rel = current.relative_to(project)
    base = project / '.tiktok-kit' / 'originals' / rel.parent
    for ext in IMAGE_EXT:
        cand = base / (rel.stem + ext)
        if cand.is_file():
            return cand
    return None


def uuid_of(path):
    try:
        return json.loads(path.with_name(path.name + '.meta').read_text(encoding='utf-8')).get('uuid')
    except (OSError, ValueError, AttributeError):
        return None


def build_index(native):
    out = {}
    for p in sorted(native.rglob('*')) if native else []:
        if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            m = pngstep.UUID_IN_NAME.search(p.name)
            if m:
                out.setdefault(m.group(1), p)
    return out


def no_quantize_keys(project):
    try:
        data = json.loads((project / '.tiktok-kit' / 'image-overrides.json').read_text(encoding='utf-8'))
        images = data.get('images') or {}
    except (OSError, ValueError, AttributeError):
        return set()
    return {k.rsplit('.', 1)[0] for k, v in images.items() if isinstance(v, dict) and v.get('quantize') is False}


def _flat_rgb(im):
    Image = _img()[0]
    im = im.convert('RGBA')
    bg = Image.new('RGBA', im.size, (128, 128, 128, 255))
    return Image.alpha_composite(bg, im).convert('RGB'), im.getchannel('A')


def _count(mask):
    return mask.convert('L').histogram()[255]


def metrics(before, after):
    Image, ImageChops, ImageFilter, ImageStat = _img()
    if before.size != after.size:
        before = before.convert('RGBA').resize(after.size, Image.LANCZOS)
    b_rgb, b_alpha = _flat_rgb(before)
    a_rgb, _ = _flat_rgb(after)
    rms = ImageStat.Stat(ImageChops.difference(b_rgb, a_rgb)).rms
    rms = math.sqrt(sum(x * x for x in rms) / len(rms))
    psnr = 99.0 if rms == 0 else round(20 * math.log10(255.0 / rms), 2)
    visible = b_alpha.point(lambda v: 255 if v > 0 else 0).convert('1')
    b_edges = b_rgb.convert('L').filter(ImageFilter.FIND_EDGES)
    a_edges = a_rgb.convert('L').filter(ImageFilter.FIND_EDGES)
    smooth = ImageChops.logical_and(b_edges.point(lambda v: 255 if 1 <= v <= 8 else 0).convert('1'), visible)
    flat = ImageChops.logical_and(a_edges.point(lambda v: 255 if v == 0 else 0).convert('1'), smooth)
    n_vis, n_smooth, n_flat = max(1, _count(visible)), _count(smooth), _count(flat)
    smooth_share = round(n_smooth / n_vis, 4)
    flat_share = round(n_flat / n_smooth, 4) if n_smooth else 0.0
    verdict = 'check' if smooth_share >= SMOOTH_MIN and flat_share >= FLAT_MIN else 'ok'
    return {'psnr_db': psnr, 'smooth_share': smooth_share, 'flattened_share': flat_share, 'verdict': verdict}


def side_by_side(before, after, dest, label=None):
    Image = _img()[0]
    pair = []
    for im in (before, after):
        im = im.convert('RGBA')
        scale = min(1.0, VIEW_H / max(1, im.size[1]))
        size = (max(1, round(im.size[0] * scale)), max(1, round(im.size[1] * scale)))
        pair.append(im.resize(size, Image.LANCZOS) if scale < 1 else im)
    w = pair[0].size[0] + pair[1].size[0] + 12
    h = max(pair[0].size[1], pair[1].size[1])
    sheet = Image.new('RGBA', (w, h), (40, 40, 40, 255))
    sheet.alpha_composite(pair[0], (0, 0))
    sheet.alpha_composite(pair[1], (pair[0].size[0] + 12, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, 'PNG')


def after_image(cur, rel, native_index, exe, no_q):
    """-> (PIL image, source note) of what ends up in the package."""
    Image = _img()[0]
    import io
    uuid = uuid_of(cur)
    if native_index:
        hit = native_index.get(uuid)
        if hit is None:
            return None, 'not found in build by uuid (auto atlas or unused)'
        im = Image.open(hit)
        im.load()
        return im, 'build ' + hit.name
    data = cur.read_bytes()
    if cur.suffix.lower() == '.png' and rel.rsplit('.', 1)[0] not in no_q:
        data = pngstep.run_pngquant(exe, data)
        note = 'project file + pngquant ' + ' '.join(pngstep.ARGS)
    else:
        note = 'project file (not quantised)'
    im = Image.open(io.BytesIO(data))
    im.load()
    return im, note


def compare(project, native=None, shots_before=None, shots_after=None, out=None):
    Image = _img()[0]
    project = Path(project)
    out = Path(out) if out else project / '.tiktok-kit' / 'image-compare'
    (out / 'pairs').mkdir(parents=True, exist_ok=True)
    exe = pngstep.pngquant_path()
    if not native and not exe:
        raise SystemExit('pngquant not found: cannot show the compressed result')
    native_index = build_index(Path(native)) if native else None
    no_q = no_quantize_keys(project)
    rows = []
    for n, cur in enumerate(project_images(project)):
        rel = cur.relative_to(project).as_posix()
        orig = original_of(project, cur) or cur
        row = {'image': rel, 'before': orig.relative_to(project).as_posix()}
        try:
            b = Image.open(orig)
            b.load()
            a, note = after_image(cur, rel, native_index, exe, no_q)
        except Exception as exc:                      # report, never stop the whole comparison
            row.update(verdict='error', note=str(exc)[:200])
            rows.append(row)
            continue
        row['after'] = note
        if a is None:
            row.update(verdict='n/a')
            rows.append(row)
            continue
        row.update(before_size=list(b.size), after_size=list(a.size), before_format=b.format, after_format=a.format)
        row.update(metrics(b, a))
        pair = out / 'pairs' / ('%04d_%s.png' % (n, re.sub(r'[^\w.-]+', '_', cur.stem)[:60]))
        side_by_side(b, a, pair)
        row['pair'] = pair.relative_to(out).as_posix()
        rows.append(row)
    pages = []
    if shots_before and shots_after:
        for b in sorted(Path(shots_before).glob('*.png')):
            a = Path(shots_after) / b.name
            if a.is_file():
                dest = out / 'pages' / b.name
                side_by_side(Image.open(b), Image.open(a), dest)
                pages.append(dest.relative_to(out).as_posix())
    rank = {'check': 0, 'error': 1, 'ok': 2, 'n/a': 3}
    rows.sort(key=lambda r: (rank.get(r.get('verdict'), 9), r.get('psnr_db', 99), r['image']))
    flagged = [r for r in rows if r.get('verdict') == 'check']
    suggest = {'images': {r['image']: {'quantize': False, 'note': 'banding risk: smooth %.0f%%, flattened %.0f%%'
                                       % (100 * r['smooth_share'], 100 * r['flattened_share'])} for r in flagged}}
    report = {'project': str(project), 'native': str(native) if native else None, 'images': len(rows),
              'check': len(flagged), 'pages': pages, 'rows': rows,
              'rule': 'check when smooth_share >= %.2f and flattened_share >= %.2f' % (SMOOTH_MIN, FLAT_MIN)}
    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'suggested-overrides.json').write_text(json.dumps(suggest, indent=1, ensure_ascii=False) + '\n',
                                                  encoding='utf-8')
    write_html(out, report)
    return report


def write_html(out, report):
    e = html.escape
    parts = ['<!doctype html><meta charset="utf-8"><title>image compare</title>',
             '<style>body{font:14px sans-serif;background:#222;color:#ddd}img{max-width:100%}'
             '.check{color:#ffb000}.row{margin:16px 0}</style>',
             '<h1>finalize 图片前后对比（左：原图，右：进包的图）</h1>',
             '<p>%d 张图，%d 张疑似色带（标 check，排在最前）。有色带的图把 suggested-overrides.json 里对应条目抄进 '
             '.tiktok-kit/image-overrides.json。</p>' % (report['images'], report['check'])]
    for page in report['pages']:
        parts.append('<div class="row"><h3>%s</h3><img src="%s"></div>' % (e(page), e(page)))
    for r in report['rows']:
        cls = 'check' if r.get('verdict') == 'check' else ''
        info = 'PSNR %s dB, smooth %s, flattened %s' % (r.get('psnr_db'), r.get('smooth_share'),
                                                        r.get('flattened_share'))
        parts.append('<div class="row"><div class="%s"><b>%s</b> [%s] %s<br>%s</div>%s</div>' % (
            cls, e(r['image']), e(str(r.get('verdict'))), e(info), e(str(r.get('after') or r.get('note') or '')),
            '<img src="%s">' % e(r['pair']) if r.get('pair') else ''))
    (out / 'index.html').write_text('\n'.join(parts) + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', required=True)
    ap.add_argument('--native')
    ap.add_argument('--shots-before')
    ap.add_argument('--shots-after')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    rep = compare(a.project, a.native, a.shots_before, a.shots_after, a.out)
    out = Path(a.out) if a.out else Path(a.project) / '.tiktok-kit' / 'image-compare'
    print('images %d, check %d, pages %d -> %s' % (rep['images'], rep['check'], len(rep['pages']), out / 'index.html'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
