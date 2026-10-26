#!/usr/bin/env python3
"""Pack many test screenshots (or a game's image assets) into a few numbered overview sheets (contact sheets).

Why: looking at screenshots one by one is the most expensive part of testing. The test
executor (any agent) runs the touch tests and builds these sheets; GPT then looks at a
few sheets at once and only opens the originals of suspicious numbers.

  python make_contact_sheet.py SHOTS_DIR_OR_FILES... --out SHEETS_DIR
      [--cols 4] [--per-sheet 8] [--cell 300] [--binding review.json]

Writes SHEETS_DIR/sheet_01.jpg, sheet_02.jpg ... and SHEETS_DIR/contact-sheets.json
(every number -> original file path and SHA-256). Each thumbnail is labelled "#NN name".
--binding copies the "binding" of the known-issue review so check_known_issues.py can
accept the sheets as current-build input for the GPT visual verdict.
Exit codes: 0 written, 2 bad input or SHEETS_DIR not empty, 3 Pillow missing.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

EXTS = {'.png', '.jpg', '.jpeg', '.webp'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(inputs):
    files = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            files += sorted(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in EXTS)
        elif p.is_file() and p.suffix.lower() in EXTS:
            files.append(p)
        else:
            raise ValueError('not an image or folder: ' + str(p))
    seen, out = set(), []
    for f in files:
        key = f.resolve()
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:          # Pillow < 10.1
        return ImageFont.load_default()


def build(files, out, cols, per_sheet, cell, binding):
    from PIL import Image, ImageDraw
    rows = math.ceil(per_sheet / cols)
    label_h, pad = 26, 8
    images = []
    for f in files:
        with Image.open(f) as im:
            images.append((f, im.size))
    # One cell height for all sheets: the tallest aspect ratio decides (phones are portrait).
    ratio = max(h / w for _, (w, h) in images)
    thumb_h = int(cell * min(ratio, 2.4))
    cw, ch = cell + pad * 2, thumb_h + label_h + pad * 2
    fnt = font(16)
    sheets = []
    for s in range(0, len(files), per_sheet):
        chunk = files[s:s + per_sheet]
        n_rows = math.ceil(len(chunk) / cols)
        sheet = Image.new('RGB', (cw * min(cols, len(chunk)), ch * n_rows), (235, 235, 235))
        draw = ImageDraw.Draw(sheet)
        items = []
        for i, f in enumerate(chunk):
            n = s + i + 1
            x0, y0 = (i % cols) * cw, (i // cols) * ch
            with Image.open(f) as im:
                w, h = im.size
                if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                    # Transparent UI art: put it on a grey checkerboard so both dark and light text stay
                    # visible (a plain convert('RGB') turns transparent areas black and hides dark letters).
                    rgba = im.convert('RGBA')
                    board = Image.new('RGBA', rgba.size, (200, 200, 200, 255))
                    sq = ImageDraw.Draw(board)
                    step = max(8, min(rgba.size) // 12)
                    for yy in range(0, rgba.size[1], step):
                        for xx in range(0, rgba.size[0], step):
                            if (xx // step + yy // step) % 2:
                                sq.rectangle([xx, yy, xx + step - 1, yy + step - 1], fill=(150, 150, 150, 255))
                    im = Image.alpha_composite(board, rgba).convert('RGB')
                else:
                    im = im.convert('RGB')
                scale = min(cell / w, thumb_h / h)
                t = im.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            sheet.paste(t, (x0 + pad + (cell - t.width) // 2, y0 + pad))
            draw.rectangle([x0 + pad - 1, y0 + pad - 1, x0 + pad + cell, y0 + pad + thumb_h], outline=(150, 150, 150))
            label = '#%02d %s' % (n, f.stem)
            draw.text((x0 + pad, y0 + pad + thumb_h + 4), label[:34], fill=(0, 0, 0), font=fnt)
            items.append({'n': n, 'label': f.stem, 'source': str(f.resolve()), 'sha256': sha(f), 'size': [w, h]})
        name = 'sheet_%02d.jpg' % (len(sheets) + 1)
        sheet.save(out / name, quality=88)
        sheets.append({'file': name, 'sha256': sha(out / name), 'items': items})
    manifest = {'tool': 'make_contact_sheet', 'total': len(files), 'sheets': sheets,
                'how_to_review': 'Look at each sheet; for any doubtful number open the original "source" file.'}
    if binding is not None:
        manifest['binding'] = binding
    (out / 'contact-sheets.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--per-sheet', type=int, default=8)
    ap.add_argument('--cell', type=int, default=300, help='thumbnail width in pixels')
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied')
    a = ap.parse_args()
    try:
        import PIL  # noqa: F401
    except ImportError:
        print(json.dumps({'status': 'error', 'error': 'Pillow missing: pip install pillow'}), file=sys.stderr)
        return 3
    try:
        if a.cols < 1 or a.per_sheet < 1 or a.cell < 60:
            raise ValueError('cols/per-sheet must be >= 1 and cell >= 60')
        files = collect(a.inputs)
        if not files:
            raise ValueError('no screenshots found')
        if a.out.exists() and any(a.out.iterdir()):
            raise ValueError('output folder is not empty: ' + str(a.out))
        binding = None
        if a.binding:
            binding = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
            if not isinstance(binding, dict):
                raise ValueError('no binding object in ' + str(a.binding))
        a.out.mkdir(parents=True, exist_ok=True)
        m = build(files, a.out, a.cols, a.per_sheet, a.cell, binding)
    except (ValueError, OSError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({'status': 'written', 'screenshots': m['total'], 'sheets': [s['file'] for s in m['sheets']],
                      'manifest': str((a.out / 'contact-sheets.json').resolve())}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
