"""Extract one named frame from a transparent sheet using verified separator bands.

Row/column are 1-based. A grid is a search hint, never a cutting rectangle.
A failing or ambiguous separator produces no cut. Output is a lossless master.
"""
import argparse
import hashlib
import io
import itertools
import json
from pathlib import Path
from PIL import Image

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def seam(projection, index, count):
    length = len(projection)
    if index in (0, count):
        return 0 if index == 0 else length
    pitch = length / count
    centre = index * pitch
    candidates = []
    for occupied, group in itertools.groupby(range(length), projection.__getitem__):
        if occupied:
            continue
        coords = list(group)
        lo, hi = coords[0], coords[-1] + 1
        mid = (lo + hi) // 2
        if hi - lo >= 4 and abs(mid - centre) <= pitch * 0.32:
            candidates.append(mid)
    if len(candidates) != 1:
        raise ValueError(f'boundary {index}/{count}: {len(candidates)} plausible clear bands; supply a separated sheet or individual source')
    return candidates[0]

def extract(sheet, rows, cols, row, col):
    if not (1 <= row <= rows and 1 <= col <= cols):
        raise ValueError('row or column outside grid')
    im = sheet.convert('RGBA')
    mask = im.getchannel('A').point(lambda a: 255 if a > 8 else 0)
    if not mask.getbbox() or mask.getextrema()[0] != 0:
        raise ValueError('expected transparent sheet')
    yp = mask.getprojection()[1]
    top, bottom = (seam(yp, i, rows) for i in (row-1, row))
    xp = mask.crop((0, top, im.width, bottom)).getprojection()[0]
    left, right = (seam(xp, i, cols) for i in (col-1, col))
    cell = (left, top, right, bottom)
    box = mask.crop(cell).getbbox()
    if box is None:
        raise ValueError('empty frame')
    x1,y1,x2,y2 = box
    if min(x1,y1,right-left-x2,bottom-top-y2) < 2:
        raise ValueError('subject touches boundary; missing pixels cannot be inferred')
    bounds = (left+x1-2, top+y1-2, left+x2+2, top+y2+2)
    return im.crop(bounds), cell, bounds

def fixed_frame(image, owner, rect):
    """Compare the declared consumer rectangle to the cell found from transparent seams."""
    left, top, right, bottom = rect
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError('fixed rectangle exceeds sheet or has no area')
    mask = image.getchannel('A').point(lambda a: 255 if a > 8 else 0)
    overlap = (max(left, owner[0]), max(top, owner[1]),
               min(right, owner[2]), min(bottom, owner[3]))
    def count(box):
        return mask.crop(box).histogram()[255]
    shared = count(overlap) if overlap[0] < overlap[2] and overlap[1] < overlap[3] else 0
    missing = count(owner) - shared
    foreign = count(rect) - shared
    if missing or foreign:
        raise ValueError(f'fixed rectangle loses {missing} subject pixels and includes {foreign} foreign pixels')
    return image.crop(rect)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sheet',type=Path)
    parser.add_argument('--grid',type=int,nargs=2,required=True,metavar=('ROWS','COLS'))
    parser.add_argument('--cell',type=int,nargs=2,required=True,metavar=('ROW','COL'))
    parser.add_argument('--out',type=Path,required=True,help='new PNG master, never the original')
    parser.add_argument('--fixed-rect', type=int, nargs=4, metavar=('L','T','R','B'),
                        help='use an unrotated integer source rectangle mandated by the importer')
    parser.add_argument('--source-sha256', help='expected hash of the visually approved source sheet')
    args=parser.parse_args()
    receipt=args.out.with_suffix('.crop.json')
    if args.out.exists() or receipt.exists() or args.out.suffix.lower()!='.png':
        parser.error('supply a new .png path with no previous receipt')
    try:
        data = args.sheet.read_bytes()
        sheet_hash = hashlib.sha256(data).hexdigest()
        if args.source_sha256 and args.source_sha256.lower() != sheet_hash:
            raise ValueError('source differs from approved sheet')
        with Image.open(io.BytesIO(data)) as im:
            rgba = im.convert('RGBA')
            master,cell,bounds=extract(rgba,*args.grid,*args.cell)
            if args.fixed_rect:
                bounds = tuple(args.fixed_rect)
                master = fixed_frame(rgba, cell, bounds)
    except (OSError, ValueError) as exc:
        parser.exit(2,f'crop refused: {exc}\n')
    master.save(args.out)
    receipt.write_text(json.dumps(dict(sheet_sha256=sheet_hash,mode=("fixed_rect" if args.fixed_rect else "tight_master"),grid=args.grid,cell=args.cell,cell_rect=cell,crop_rect=bounds,master_sha256=digest(args.out)),indent=2))
if __name__=='__main__':main()
