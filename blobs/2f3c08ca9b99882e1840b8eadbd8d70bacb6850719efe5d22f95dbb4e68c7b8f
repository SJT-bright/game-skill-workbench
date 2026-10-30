#!/usr/bin/env python3
"""Size limits for images made during English localisation (v7.5, MusicSlice item 6). Read-only.

MusicSlice v29b replaced its result/settings art with English images of 1.5-2.2 MB each (result-btn-retry.png 1983x793,
shown about 390 wide: 5x), so about 25 MB had to download before the home page. Only NEW images are judged: an image
whose SHA-256 is in the pre-English list (the Chinese original's images) is the game's own art and is never refused, so
completed games are not affected.

  new image > 800,000 bytes                            -> refused
  new image wider or taller than 2.5x its display size -> refused (display size from the prefab/scene, when known)
Export new English images at 2x display size, then compress (the 2x rule of audit_image_clarity.py).

API:  check(images, pre_english, display=None) -> {"passed": bool, "problems": [...], "new_images": [...]}
  images: {name: bytes} or iterable of (name, bytes); pre_english: iterable of SHA-256 strings, or a JSON file
  {"images": {sha: name}} / [sha, ...]; display: optional {name or sha: (width, height)}.
CLI:  python3 audit_new_english_images.py --zip <upload.zip> --pre-english <list.json> [--out report.json]
      python3 audit_new_english_images.py --make-list <Chinese original project dir> --out <list.json>
Exit 0 pass, 1 refused, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')
MAX_BYTES = 800_000
MAX_RATIO = 2.5


def pixels(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        if data[12:16] == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if data[12:16] == b'VP8L':
            b = data[21:25]
            return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        if data[12:16] == b'VP8 ':
            return struct.unpack('<H', data[26:28])[0] & 0x3FFF, struct.unpack('<H', data[28:30])[0] & 0x3FFF
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, length = data[i + 1], struct.unpack('>H', data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return w, h
            i += 2 + length
    return None


def load_pre(pre_english):
    if isinstance(pre_english, (str, Path)):
        doc = json.loads(Path(pre_english).read_text(encoding='utf-8-sig'))
        pre_english = doc.get('images', doc) if isinstance(doc, dict) else doc
    return {str(s).lower() for s in pre_english}


def check(images, pre_english, display=None):
    pre = load_pre(pre_english)
    display = display or {}
    items = images.items() if isinstance(images, dict) else images
    seen, new, problems = set(), [], []
    for name, data in items:
        if not str(name).lower().endswith(IMAGE_SUFFIXES):
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest in pre or digest in seen:
            continue
        seen.add(digest)
        dims = pixels(data)
        row = {'image': name, 'sha256': digest, 'bytes': len(data), 'pixels': list(dims) if dims else None}
        shown = display.get(name) or display.get(digest)
        if len(data) > MAX_BYTES:
            problems.append('%s: new English image is %d bytes (> %d): export at 2x display size and compress' % (name, len(data), MAX_BYTES))
        if dims and shown and shown[0] and shown[1]:
            ratio = max(dims[0] / shown[0], dims[1] / shown[1])
            row.update(display=list(shown), ratio=round(ratio, 2))
            if ratio > MAX_RATIO:
                problems.append('%s: %dx%d is %.1fx its display size %dx%d (> %.1fx): export at 2x display size'
                                % (name, dims[0], dims[1], ratio, shown[0], shown[1], MAX_RATIO))
        new.append(row)
    return {'tool': 'audit_new_english_images', 'schema': 1, 'pre_english_images': len(pre), 'new_images': new,
            'problems': problems, 'passed': not problems}


def make_list(project):
    out = {}
    for p in sorted(Path(project).rglob('*')):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not {'library', 'temp', 'build'} & set(p.parts):
            out[hashlib.sha256(p.read_bytes()).hexdigest()] = p.relative_to(project).as_posix()
    return {'source': str(Path(project).resolve()), 'images': out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path)
    ap.add_argument('--pre-english', type=Path)
    ap.add_argument('--make-list', type=Path, help='Chinese original project: write its image SHA list to --out')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        if a.make_list:
            if not a.out:
                ap.error('--make-list needs --out')
            a.out.write_text(json.dumps(make_list(a.make_list), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            return 0
        if not (a.zip and a.pre_english):
            ap.error('--zip and --pre-english are required')
        with zipfile.ZipFile(a.zip) as zf:
            r = check(((n, zf.read(n)) for n in zf.namelist() if n.lower().endswith(IMAGE_SUFFIXES)), a.pre_english)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)})); return 2
    if a.out:
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': r['passed'], 'new_images': len(r['new_images']), 'problems': r['problems'][:10]}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
