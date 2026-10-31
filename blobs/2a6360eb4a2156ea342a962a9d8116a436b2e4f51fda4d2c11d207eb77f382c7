#!/usr/bin/env python3
"""Grey-box reference for image generation (总表 H12, 企鹅雪道美术 v2: the base game's atlas was sent as the reference
and the new art copied its style, highlights and outlines). Send THIS picture to the image model, never the base art.

The output is drawn on a new canvas from shapes only: every piece of the base picture becomes a flat grey block with
a number, nothing of its colours, shading, outline or texture is copied. A legend JSON lists what each number is, so
the prompt can say "#3 is the start button, 220x90".

    python3 make_greybox_reference.py --image <atlas or sprite.png> --out ref.png     pieces = transparent islands
    python3 make_greybox_reference.py --folder <dir of sprites> --out ref.png        one block per file, in a grid
    python3 make_greybox_reference.py --dump <ui-dump.json> --out ref.png            one block per visible node
                                                                                      (chrome_touch dump_ui)
Options: --boxes (rectangles instead of silhouettes), --min-area N (ignore specks, default 64 px), --scale S.
An opaque picture (a screenshot) has no islands to find: use --dump of the same page instead (the tool refuses).
Writes <out> and <out>.json ({source, sha256, mode, items: [{n, name, box: [x, y, w, h]}]}). Needs Pillow only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - reported, not raised
    Image = None

TONES = ((176, 176, 176), (140, 140, 140), (204, 204, 204))   # three flat greys so neighbours stay apart
BACK = (244, 244, 244)
INK = (32, 32, 32)
EXT = ('.png', '.webp', '.jpg', '.jpeg')


def font(size):
    try:
        return ImageFont.load_default(size=max(10, int(size)))
    except TypeError:                                   # Pillow < 10.1
        return ImageFont.load_default()


def islands(img, min_area=64, step=None):
    """Connected opaque areas of an RGBA picture -> [(x, y, w, h, mask cells)] on a coarse grid (fast, no numpy)."""
    w, h = img.size
    step = step or max(1, int(max(w, h) / 512))
    alpha = img.getchannel('A').resize((max(1, w // step), max(1, h // step)), Image.NEAREST)
    gw, gh = alpha.size
    px = alpha.load()
    seen = bytearray(gw * gh)
    out = []
    for y0 in range(gh):
        for x0 in range(gw):
            i = y0 * gw + x0
            if seen[i] or px[x0, y0] < 24:
                continue
            stack, cells = [(x0, y0)], []
            seen[i] = 1
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < gw and 0 <= ny < gh and not seen[ny * gw + nx] and px[nx, ny] >= 24:
                        seen[ny * gw + nx] = 1
                        stack.append((nx, ny))
            if len(cells) * step * step < min_area:
                continue
            xs, ys = [c[0] for c in cells], [c[1] for c in cells]
            out.append((min(xs) * step, min(ys) * step, (max(xs) - min(xs) + 1) * step, (max(ys) - min(ys) + 1) * step,
                        cells, (step, 0, 0)))
    out.sort(key=lambda r: (r[1] // 64, r[0]))
    return out


def opaque(img):
    a = img.getchannel('A')
    lo, _hi = a.getextrema()
    return lo >= 250


def draw_items(size, items, boxes=False):
    """items: [(n, name, (x, y, w, h), cells or None, step)] -> new picture (shapes + numbers only)."""
    canvas = Image.new('RGB', size, BACK)
    d = ImageDraw.Draw(canvas)
    for n, _name, (x, y, w, h), cells, step in items:
        tone = TONES[n % len(TONES)]
        if cells and not boxes:
            for cx, cy in cells:                         # grid cells, offset to the item's own corner
                d.rectangle([step[1] + cx * step[0], step[2] + cy * step[0],
                             step[1] + cx * step[0] + step[0] - 1, step[2] + cy * step[0] + step[0] - 1], fill=tone)
        else:
            d.rectangle([x, y, x + w - 1, y + h - 1], fill=tone)
        d.rectangle([x, y, x + w - 1, y + h - 1], outline=INK, width=1)
        f = font(min(48, max(10, min(w, h) * 0.4)))
        label = str(n)
        tb = d.textbbox((0, 0), label, font=f)
        d.text((x + (w - (tb[2] - tb[0])) / 2, y + (h - (tb[3] - tb[1])) / 2 - tb[1]), label, fill=INK, font=f)
    return canvas


def from_image(path, min_area, boxes):
    img = Image.open(path).convert('RGBA')
    if opaque(img):
        raise ValueError('%s is opaque (a screenshot or a background): it has no pieces to find. Use --dump with a '
                         'chrome_touch dump_ui of the same page, or cut the pieces out first.' % path)
    found = islands(img, min_area)
    items = [(i + 1, '%s#%d' % (Path(path).name, i + 1), r[:4], r[4], r[5]) for i, r in enumerate(found)]
    return img.size, items


def from_folder(folder, min_area, boxes, gap=24):
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in EXT and p.is_file())
    if not files:
        raise ValueError('no pictures in %s' % folder)
    sizes = []
    for p in files:
        with Image.open(p) as im:
            sizes.append(im.size)
    cols = max(1, int(len(files) ** 0.5 + 0.999))
    cell_w = max(s[0] for s in sizes) + gap
    cell_h = max(s[1] for s in sizes) + gap
    items = []
    for i, (p, (w, h)) in enumerate(zip(files, sizes)):
        x, y = (i % cols) * cell_w + gap // 2, (i // cols) * cell_h + gap // 2
        cells, step = None, (1, x, y)
        if not boxes:
            img = Image.open(p).convert('RGBA')
            if not opaque(img):
                s = max(1, int(max(w, h) / 128))
                a = img.getchannel('A').resize((max(1, w // s), max(1, h // s)), Image.NEAREST)
                ap = a.load()
                cells = [(cx, cy) for cy in range(a.size[1]) for cx in range(a.size[0]) if ap[cx, cy] >= 24]
                step = (s, x, y)
        items.append((i + 1, p.name, (x, y, w, h), cells, step))
    rows = (len(files) + cols - 1) // cols
    return (cols * cell_w, rows * cell_h), items


def from_dump(path, scale):
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    canvas = d.get('canvas_css') or [0, 0, 390, 844]
    W, H = int(canvas[2] * scale), int(canvas[3] * scale)
    items, n = [], 0
    for node in d.get('nodes', []):
        comps = node.get('comps') or {}
        if node.get('opacity', 1) < 0.05 or not node.get('rect') or not (set(comps) & {'sprite', 'button', 'label'}):
            continue
        rx, ry, rw, rh = node['rect']
        box = (int(rx * W), int(ry * H), max(2, int(rw * W)), max(2, int(rh * H)))
        if box[2] * box[3] >= 0.9 * W * H:                 # full-screen background: leave the page white
            continue
        n += 1
        kind = 'button' if 'button' in comps else 'label' if 'label' in comps else 'sprite'
        items.append((n, '%s (%s)' % (node.get('path', ''), kind), box, None, (1, 0, 0)))
    return (W, H), items


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--image', type=Path)
    src.add_argument('--folder', type=Path)
    src.add_argument('--dump', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--boxes', action='store_true', help='rectangles instead of silhouettes')
    ap.add_argument('--min-area', type=int, default=64)
    ap.add_argument('--scale', type=float, default=2.0, help='--dump only: output pixels per CSS pixel')
    a = ap.parse_args(argv)
    if Image is None:
        print('Pillow is missing: run with a Python that has it (e.g. /usr/bin/python3 on macOS)', file=sys.stderr)
        return 2
    try:
        if a.image:
            size, items = from_image(a.image, a.min_area, a.boxes)
            source = a.image
        elif a.folder:
            size, items = from_folder(a.folder, a.min_area, a.boxes)
            source = a.folder
        else:
            size, items = from_dump(a.dump, a.scale)
            source = a.dump
    except (OSError, ValueError) as error:
        print('greybox: %s' % error, file=sys.stderr)
        return 2
    if not items:
        print('greybox: nothing found in %s' % source, file=sys.stderr)
        return 2
    picture = draw_items(size, items, a.boxes)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    picture.save(a.out)
    digest = hashlib.sha256(Path(source).read_bytes()).hexdigest() if Path(source).is_file() else None
    legend = {'tool': 'make_greybox_reference', 'source': str(source), 'source_sha256': digest,
              'mode': 'image' if a.image else 'folder' if a.folder else 'dump', 'size': list(size),
              'note': 'Only this grey-box picture goes to the image model, never the base art (总表 H12).',
              'items': [{'n': n, 'name': name, 'box': list(box)} for n, name, box, _c, _s in items]}
    Path(str(a.out) + '.json').write_text(json.dumps(legend, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(a.out), 'items': len(items), 'legend': str(a.out) + '.json'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
