"""Build one fixed-caption button from reviewed artwork and integer pixel constraints."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image


def positive(value, field):
    if type(value) is not int or value <= 0:
        raise ValueError(f'{field} must be a positive integer')
    return value


def load_art(root, record):
    data = (root / record['file']).read_bytes()
    if hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError(f"art changed: {record['file']}")
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'PNG':
            raise ValueError('expected PNG artwork')
        return image.convert('RGBA')


def foreground(root, record):
    image = load_art(root, record)
    alpha = image.getchannel('A')
    if alpha.getextrema()[0] == 255 or alpha.getbbox() is None:
        raise ValueError('foreground requires visible ink and a transparent background')
    return image.crop(alpha.getbbox())


def width_at(image, height):
    return max(1, round(image.width * height / image.height))


def compose(spec, root):
    word = spec['word']
    if not isinstance(spec['caption'], str) or not spec['caption'].strip() or spec['caption'] != word['approved_text']:
        raise ValueError('caption differs from the reviewed word artwork')
    base = load_art(root, spec['base'])
    label = foreground(root, word)
    left, top, right, bottom = spec['safe_box']
    if any(type(n) is not int for n in (left, top, right, bottom)) or not (
            0 <= left < right <= base.width and 0 <= top < bottom <= base.height):
        raise ValueError('safe_box must be inside the base')
    safe_w, safe_h = right-left, bottom-top
    gap = 0
    icon_w = 0
    icon = None
    if 'icon' in spec:
        icon = foreground(root, spec['icon'])
        icon_h = positive(spec['icon']['height'], 'icon.height')
        icon_w = width_at(icon, icon_h)
        gap = positive(spec['gap'], 'gap')
        if icon_h > min(safe_h, icon.height) or icon_w > safe_w:
            raise ValueError('icon cannot fit at its specified size')
    minimum = positive(word['min_height'], 'word.min_height')
    maximum = positive(word['max_height'], 'word.max_height')
    for height in range(min(maximum, safe_h, label.height), minimum-1, -1):
        width = width_at(label, height)
        if icon_w + gap + width <= safe_w:
            break
    else:
        raise ValueError('no readable layout fits the safe box; enlarge or redesign the button')
    x = left + (safe_w - icon_w - gap - width)//2
    boxes = {}
    def place(name, image, x, w, h):
        y = top + (safe_h-h)//2
        base.alpha_composite(image.resize((w,h), Image.Resampling.LANCZOS), (x,y))
        boxes[name] = [x,y,x+w,y+h]
    if icon is not None:
        place('icon', icon, x, icon_w, icon_h)
    place('word', label, x+icon_w+gap, width, height)
    return base, boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    output = args.output.resolve()
    inputs = [args.spec, *(args.spec.parent / spec[key]['file'] for key in ('base','word','icon') if key in spec)]
    if output.suffix.lower() != '.png' or output in [p.resolve() for p in inputs]:
        parser.error('output must be a separate PNG')
    image, boxes = compose(spec, args.spec.parent)
    with NamedTemporaryFile(dir=output.parent, delete=False) as temp:
        path = Path(temp.name)
    try:
        image.save(path, format='PNG')
        os.replace(path, output)
    finally:
        path.unlink(missing_ok=True)
    print(json.dumps(dict(caption=spec['caption'], size=image.size, boxes=boxes)))


if __name__ == '__main__':
    main()
