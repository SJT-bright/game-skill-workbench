#!/usr/bin/env python3
"""Trim a generated transparent picture to its VISIBLE pixels, then keep a 2 px safe margin (R4O2, 补查2 第 7 组).

Image models leave near-invisible specks (alpha 1-7) in the "empty" part of a transparent PNG. A plain
alpha.getbbox() counts them, so the crop keeps wide transparent margins and the button or word looks too small and
off-centre once the node is sized to the picture (合成进化恐龙 NO THANKS / CLAIM, 2026-11-05). Use this instead of
hand-written crops:

    python3 trim_visible.py in.png --out out.png            writes out.png and out.png.trim.json
    from trim_visible import visible_box, trim               (compose_fixed_button.py uses it)

The box is computed on alpha >= 8 (VISIBLE_ALPHA), then grown by 2 px (SAFE_MARGIN) and clamped to the picture, so
soft anti-aliased edges survive. The pixels are not changed, only cropped. A picture with no visible pixel is refused.
"""
import argparse
import hashlib
import json
from pathlib import Path

if __name__ == '__main__':
    import importlib.util as _ilu
    _cg = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts' / 'check_guard.py'
    if _cg.is_file():
        _spec = _ilu.spec_from_file_location('check_guard', _cg)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.need_modules('PIL')
from PIL import Image

VISIBLE_ALPHA = 8
SAFE_MARGIN = 2


def visible_box(image, threshold=VISIBLE_ALPHA, margin=SAFE_MARGIN):
    """(left, top, right, bottom) of the pixels with alpha >= threshold, grown by margin and clamped; None if none."""
    alpha = image.convert('RGBA').getchannel('A')
    box = alpha.point(lambda a: 255 if a >= threshold else 0).getbbox()
    if box is None:
        return None
    x1, y1, x2, y2 = box
    return (max(0, x1 - margin), max(0, y1 - margin), min(image.width, x2 + margin), min(image.height, y2 + margin))


def trim(image, threshold=VISIBLE_ALPHA, margin=SAFE_MARGIN):
    image = image.convert('RGBA')
    box = visible_box(image, threshold, margin)
    if box is None:
        raise ValueError('no visible pixel (alpha >= %d)' % threshold)
    return image.crop(box), box


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('image', type=Path)
    ap.add_argument('--out', type=Path, required=True, help='new PNG, never the input')
    ap.add_argument('--threshold', type=int, default=VISIBLE_ALPHA)
    ap.add_argument('--margin', type=int, default=SAFE_MARGIN)
    ap.add_argument('--word', action='store_true',
                    help='a generated word picture: remove its glow first (clean_glow.py, R4R3); exit 1 + prompt if it cannot')
    a = ap.parse_args(argv)
    if a.out.suffix.lower() != '.png' or a.out.resolve() == a.image.resolve():
        ap.error('--out must be a separate .png')
    glow = None
    try:
        data = a.image.read_bytes()
        with Image.open(a.image) as im:
            src = im.convert('RGBA')
            size = im.size
        if a.word:
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).resolve().parent))
            from clean_glow import clean
            verdict, cleaned, info = clean(src, a.image)
            glow = {'verdict': verdict, 'glow_px': info.get('glow_px', 0)}
            if verdict == 'regenerate':
                print(json.dumps({'tool': 'trim_visible', 'source': str(a.image), 'glow': info}, ensure_ascii=False))
                ap.exit(1, 'REGENERATE %s: %s\n  prompt: %s\n' % (a.image, info['why'], info['prompt']))
            if cleaned is not None:
                src = cleaned          # the input file stays as it was: it is the backup
        out, box = trim(src, a.threshold, a.margin)
    except (OSError, ValueError) as exc:
        ap.exit(2, 'trim refused: %s\n' % exc)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out)
    receipt = {'tool': 'trim_visible', 'source': str(a.image), 'source_sha256': hashlib.sha256(data).hexdigest(),
               'source_size': list(size), 'threshold': a.threshold, 'margin': a.margin, 'crop_box': list(box),
               'size': list(out.size), 'out_sha256': hashlib.sha256(a.out.read_bytes()).hexdigest()}
    if glow is not None:
        receipt['glow'] = glow
    Path(str(a.out) + '.trim.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
