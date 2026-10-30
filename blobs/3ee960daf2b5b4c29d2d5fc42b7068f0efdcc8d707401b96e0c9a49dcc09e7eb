#!/usr/bin/env python3
"""English image review record (v7.5, MusicSlice item 7). Read-only.

MusicSlice v29b shipped HomeSprites.png with "已拥有" drawn on the skin-shop button: the English rules said "look at every
image" but nothing at packaging time checked that anyone had. So every English upload package needs a record with one
entry per DISTINCT image (by SHA-256) in the package:

  docs/english/image-review.json
  {"schema": "image_review.v1",
   "images": [{"sha256": "...", "file": "assets/Texture/首页/HomeSprites.png", "reviewer": "main agent",
               "status": "done", "chinese": "no" | "yes", "replaced_with": "<new sha256 or file>",
               "atlas": true, "slices_reviewed": true}]}

Refused when: the record is missing or unreadable; an image in the package has no entry; an entry is pending / has no
reviewer / says neither yes nor no; an entry says "chinese": "yes" and that same SHA is still in the package (it was not
replaced); an atlas (entry "atlas": true, or a .plist next to it) was not reviewed slice by slice.
grok-image-review may transcribe the text on an image; the verdict in the record is the main agent's.

API for the package entries (board localize):  check(files, record_path) -> {"passed": bool, "problems": [...], ...}
  files: a dict {name: bytes}, an iterable of (name, bytes) pairs, or an iterable of file paths.
CLI:  python3 audit_image_review_record.py --zip <upload.zip> --record <image-review.json> [--out report.json]
Exit 0 pass, 1 refused, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')


def _items(files):
    if isinstance(files, dict):
        files = files.items()
    for item in files:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            yield str(item[0]), item[1]
        else:
            p = Path(item)
            yield str(p), p.read_bytes()


def check(files, record_path):
    names, images, plists = {}, {}, set()
    for name, data in _items(files):
        low = name.lower()
        if low.endswith('.plist'):
            plists.add(low[:-len('.plist')])
        if not low.endswith(IMAGE_SUFFIXES):
            continue
        if callable(getattr(data, 'read', None)):
            data = data.read()
        digest = hashlib.sha256(data).hexdigest()
        images.setdefault(digest, name)
        names[name] = digest
    report = {'tool': 'audit_image_review_record', 'schema': 1, 'record': str(record_path), 'distinct_images': len(images),
              'problems': [], 'passed': False}
    try:
        record = json.loads(Path(record_path).read_text(encoding='utf-8-sig'))
        entries = record.get('images') if isinstance(record, dict) else None
        if not isinstance(entries, list):
            raise ValueError('no "images" list')
    except (OSError, ValueError) as exc:
        report['problems'].append('image review record missing or unreadable (%s): review every distinct image in the upload '
                                  'package and write docs/english/image-review.json' % exc)
        return report
    by_sha = {}
    for e in entries:
        if isinstance(e, dict) and isinstance(e.get('sha256'), str):
            by_sha.setdefault(e['sha256'].lower(), e)
    for digest, name in sorted(images.items(), key=lambda kv: kv[1]):
        e = by_sha.get(digest)
        if e is None:
            report['problems'].append('%s (sha256 %s): not in the image review record' % (name, digest[:12]))
            continue
        if str(e.get('status', '')).lower() != 'done' or not str(e.get('reviewer') or '').strip():
            report['problems'].append('%s: review is %s%s' % (name, e.get('status') or 'missing a status',
                                                              '' if str(e.get('reviewer') or '').strip() else ', no reviewer'))
        chinese = str(e.get('chinese', '')).lower()
        if chinese not in ('yes', 'no'):
            report['problems'].append('%s: record must say chinese yes or no' % name)
        elif chinese == 'yes':
            report['problems'].append('%s (sha256 %s): recorded as having Chinese but the same image is still in the package '
                                      '(redraw it in English, then record the new image)' % (name, digest[:12]))
        stem = name.lower().rsplit('.', 1)[0]
        if (e.get('atlas') or stem in plists) and e.get('slices_reviewed') is not True:
            report['problems'].append('%s: atlas must be reviewed slice by slice ("slices_reviewed": true)' % name)
    report['passed'] = not report['problems']
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path, required=True, help='upload package ZIP')
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    try:
        with zipfile.ZipFile(a.zip) as zf:
            r = check(((n, zf.read(n)) for n in zf.namelist() if not n.endswith('/')), a.record)
    except (OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)})); return 2
    r['zip'] = str(a.zip)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': r['passed'], 'distinct_images': r['distinct_images'], 'problems': r['problems'][:10]}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
