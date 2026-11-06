#!/usr/bin/env python3
"""Find and remove the soft coloured glow image models put around generated WORD pictures (R4R3, 补读第 11 组).

The prompt said "no glow" and the model still drew a blue-purple halo outside the outline (弹球传奇 FREE GEMS / OK,
2026-11-05; 2 of 8 word jobs). A prompt cannot stop it, so every generated word picture goes through this right
after it is received, before it is trimmed, recorded or bound:

    python3 clean_glow.py txt_free_gems.png [more.png ...]        fixes in place (default)
    python3 clean_glow.py --check <png ...>                       read only (calibration)
    python3 trim_visible.py txt_ok.png --out ok.png --word        the same clean, then the trim (one step)

How it decides (alpha only, no numpy):
  * solid  = alpha >= 230 (letters and their drawn outline); the 2 px around it is the anti-aliased edge, kept;
  * glow   = pixels farther out than that edge with alpha 26..229 (10 %..90 %) that are coloured or light
             (max-min channel >= 32, or brightest channel >= 200). Dark grey soft pixels are a shadow, never glow;
  * a picture "has glow" when the glow pixels are at least 40 and at least half the outline length, AND they sit
    on all four sides of the letters (the thinnest side, per unit of side length, >= 40 % of the thickest). A drop shadow is on one or two
    sides only, so a designed shadow (any colour) is reported as "shadow" and left alone.
What it does (Saul 11-05: 发现问题直接处理): every coloured or light pixel outside the 2 px edge with alpha < 230 is
made transparent (the solid letters, outline and dark shadow pixels are untouched), then the picture is checked again.
  * cleaned     -> the original goes to _glow_backup/ next to it, the clean picture replaces it, a line is added to
                   glow_clean.json (sha before/after, counts, backup path). Exit 0.
  * regenerate  -> the glow could not be removed (it carries more than 35 % of the picture's alpha, or it is still
                   there after the clean). Nothing is changed; a ready prompt is printed and recorded (same size, same
                   words, no glow). Exit 1. Regenerate with that prompt and run this again; do not bind the old one.
Exit 2: the input is not a readable picture.
"""
import argparse
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

if __name__ == '__main__':
    import importlib.util as _ilu
    _cg = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts' / 'check_guard.py'
    if _cg.is_file():
        _spec = _ilu.spec_from_file_location('check_guard', _cg)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.need_modules('PIL')
from PIL import Image, ImageChops, ImageFilter

SOLID = 230          # alpha >= this is a drawn letter or outline
EDGE = 2             # anti-aliased edge kept around the solid part
SOFT_MIN = 26        # 10 % alpha: fainter pixels alone never make a glow verdict
CHROMA = 32          # max-min channel: "coloured"
LIGHT = 200          # brightest channel: a light / white glow
MIN_PIXELS = 40
MIN_PER_OUTLINE = 0.5
MIN_SIDE_SHARE = 0.4
MAX_MASS_SHARE = 0.35


def _mask(channel, lo, hi=255):
    return channel.point(lambda v: 255 if lo <= v <= hi else 0)


def _count(mask):
    return mask.histogram()[255]


def _grow(mask, n):
    return mask.filter(ImageFilter.MaxFilter(2 * n + 1)) if n > 0 else mask


def _masks(im):
    r, g, b, a = im.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    colour = ImageChops.lighter(_mask(ImageChops.subtract(mx, mn), CHROMA), _mask(mx, LIGHT))
    solid = _mask(a, SOLID)
    outside = ImageChops.invert(_grow(solid, EDGE))
    soft = _mask(a, SOFT_MIN, SOLID - 1)
    glow = ImageChops.multiply(ImageChops.multiply(soft, outside), colour)
    removable = ImageChops.multiply(ImageChops.multiply(_mask(a, 1, SOLID - 1), outside), colour)
    return a, solid, glow, removable


def measure(im):
    """Numbers and a verdict ('clean' / 'glow' / 'shadow') for one RGBA picture."""
    im = im.convert('RGBA')
    a, solid, glow, removable = _masks(im)
    box = solid.getbbox()
    if box is None:
        return {'verdict': 'clean', 'glow_px': 0, 'note': 'no solid pixel'}
    outline = _count(_grow(solid, 1)) - _count(solid)
    px = _count(glow)
    x1, y1, x2, y2 = box
    w, h = im.size
    sides = {'top': _count(glow.crop((0, 0, w, y1))), 'bottom': _count(glow.crop((0, y2, w, h))),
             'left': _count(glow.crop((0, 0, x1, h))), 'right': _count(glow.crop((x2, 0, w, h)))}
    # per unit of side length: a word is wide, so top/bottom strips are longer than left/right ones
    dens = {k: v / float(max(1, (x2 - x1) if k in ('top', 'bottom') else (y2 - y1))) for k, v in sides.items()}
    big = max(dens.values())
    share = (min(dens.values()) / big) if big else 0.0
    mass = sum(i * n for i, n in enumerate(a.histogram()))
    rm_alpha = ImageChops.multiply(a, removable)
    rm_mass = sum(i * n for i, n in enumerate(rm_alpha.histogram()))
    info = {'glow_px': px, 'outline_px': outline, 'per_outline': round(px / float(max(1, outline)), 3),
            'sides': sides, 'side_share': round(share, 3), 'removable_px': _count(removable),
            'removable_alpha_share': round(rm_mass / float(max(1, mass)), 4)}
    soft_enough = px >= MIN_PIXELS and px >= MIN_PER_OUTLINE * outline
    info['verdict'] = ('glow' if share >= MIN_SIDE_SHARE else 'shadow') if soft_enough else 'clean'
    return info


def remove_glow(im):
    """Return a copy with every coloured / light soft pixel outside the 2 px edge made transparent."""
    im = im.convert('RGBA')
    a, _solid, _glow, removable = _masks(im)
    out = im.copy()
    out.putalpha(ImageChops.multiply(a, ImageChops.invert(removable)))
    return out


def words_from(path, word=None):
    if word:
        return word
    stem = re.sub(r'^(txt|word|title|lbl|btn)_', '', Path(path).stem, flags=re.I)
    return re.sub(r'[_\-]+', ' ', stem).strip().upper()


def regenerate_prompt(path, size, word=None):
    return ('Regenerate %s at exactly %dx%d px: the same words "%s", same font, colours and outline as before, on a '
            'fully transparent background. Hard clean edge right outside the outline: no glow, no outer glow, no '
            'soft halo, no bloom, no light rays, no coloured haze around the letters.'
            % (Path(path).name, size[0], size[1], words_from(path, word)))


def clean(im, path='word.png', word=None):
    """(verdict, picture_or_None, info). verdict: clean / shadow / cleaned / regenerate."""
    im = im.convert('RGBA')
    info = measure(im)
    if info['verdict'] != 'glow':
        return info['verdict'], None, info
    if info['removable_alpha_share'] > MAX_MASS_SHARE:
        info['why'] = 'the glow carries %.0f%% of the picture alpha' % (100 * info['removable_alpha_share'])
        info['prompt'] = regenerate_prompt(path, im.size, word)
        return 'regenerate', None, info
    out = remove_glow(im)
    after = measure(out)
    info['after'] = after
    if after['verdict'] == 'glow':
        info['why'] = 'glow still found after the clean'
        info['prompt'] = regenerate_prompt(path, im.size, word)
        return 'regenerate', None, info
    return 'cleaned', out, info


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('images', nargs='+', type=Path)
    ap.add_argument('--check', action='store_true', help='read only: report, change nothing')
    ap.add_argument('--word', help='the words on the picture (for the regenerate prompt); default from the file name')
    ap.add_argument('--record', type=Path, help='record file (default: glow_clean.json next to the first picture)')
    ap.add_argument('--backup-dir', type=Path, help='default: _glow_backup/ next to each picture')
    a = ap.parse_args(argv)
    rows, worst = [], 0
    for path in a.images:
        try:
            with Image.open(path) as src:
                im = src.convert('RGBA')
        except OSError as exc:
            print(json.dumps({'file': str(path), 'verdict': 'unreadable', 'error': str(exc)}, ensure_ascii=False))
            worst = 2
            continue
        verdict, out, info = clean(im, path, a.word)
        row = {'file': str(path), 'verdict': verdict, 'size': list(im.size), 'sha256_before': _sha(path)}
        row.update(info)
        row['measured'] = row.pop('verdict')
        row['verdict'] = verdict
        if verdict == 'cleaned' and not a.check:
            bdir = a.backup_dir or path.parent / '_glow_backup'
            bdir.mkdir(parents=True, exist_ok=True)
            backup = bdir / path.name
            if backup.exists():
                backup = bdir / ('%s.%d%s' % (path.stem, int(time.time()), path.suffix))
            shutil.copy2(path, backup)
            out.save(path, format='PNG')
            row.update({'backup': str(backup), 'sha256_after': _sha(path), 'replaced': True})
        elif verdict == 'cleaned':
            row['verdict'] = 'glow'      # --check: would be cleaned
        if row['verdict'] == 'regenerate' or (a.check and row['verdict'] == 'glow'):
            worst = max(worst, 1)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    if rows and not a.check:
        rec = a.record or a.images[0].parent / 'glow_clean.json'
        old = []
        if rec.is_file():
            try:
                old = json.loads(rec.read_text(encoding='utf-8')).get('entries', [])
            except (ValueError, AttributeError):
                old = []
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        for row in rows:
            row['at'] = stamp
        rec.write_text(json.dumps({'tool': 'clean_glow', 'entries': old + rows}, ensure_ascii=False, indent=1) + '\n',
                       encoding='utf-8')
    for row in rows:
        if row['verdict'] == 'regenerate':
            print('REGENERATE %s: %s\n  prompt: %s' % (row['file'], row['why'], row['prompt']))
    return worst


if __name__ == '__main__':
    raise SystemExit(main())
