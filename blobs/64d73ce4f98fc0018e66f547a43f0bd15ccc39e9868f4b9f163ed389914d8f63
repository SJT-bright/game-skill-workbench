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
      python3 audit_image_review_record.py write --zip <upload.zip> --out docs/english/image-review.json [--ocr auto]
                                         [--verdict <sha256>=yes|no ... --by "<who>"]
P16 (2026-11-04): the record is written ONLY by `write` (OCR of every image and slice in the package, sealed with
generated_by.entries_sha256); a hand-filled or hand-edited record is refused.
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


WRITER = 'audit_image_review_record.py write'


def entries_seal(entries):
    """SHA-256 over the entries exactly as the writer made them. A hand edit (P16, 2026-11-04) no longer matches."""
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def write(files, ocr='auto', verdicts=None, by=None):
    """Build the record from the package itself (P16, 2026-11-04: image-review.json is written only by this script).

    Every distinct package image and every slice/frame inside it is read by the local recognizer (via
    audit_new_english_images.scan_chinese -> chinese_audit). chinese = yes if the picture or any of its slices has Chinese;
    no if the picture and all slices were read clean. Anything the recognizer could not settle (or every image, on a
    computer with no recognizer) stays "pending" until a person gives a verdict: verdicts {sha256: 'yes'|'no'} with by=<who>.
    """
    import tempfile
    import shutil
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import audit_new_english_images as ani
    verdicts = {k.lower(): v for k, v in (verdicts or {}).items()}
    tmp = Path(tempfile.mkdtemp(prefix='image-review-'))
    try:
        by_sha, root = {}, tmp / 'assets'
        for name, data in _items(files):
            if callable(getattr(data, 'read', None)):
                data = data.read()
            if name.lower().endswith(IMAGE_SUFFIXES + ('.plist', '.atlas', '.json', '.fnt')):
                target = root / name.lstrip('/').replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                if name.lower().endswith(IMAGE_SUFFIXES):
                    by_sha.setdefault(hashlib.sha256(data).hexdigest(), name)
        root.mkdir(exist_ok=True)
        scan = ani.scan_chinese(tmp, ocr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    per_file = {}
    for item, verdict, text, _ in scan.get('items') or []:
        f = item.get('file')
        if f:
            per_file.setdefault('assets/' + f if not f.startswith('assets/') else f, []).append((item['kind'], verdict, text))
    entries = []
    for digest, name in sorted(by_sha.items(), key=lambda kv: kv[1]):
        got = per_file.get('assets/' + name.lstrip('/')) or []
        slices = [g for g in got if g[0] == 'slice']
        verdicts_here = {g[1] for g in got}
        e = {'sha256': digest, 'file': name, 'atlas': bool(slices), 'slices': len(slices),
             'recognizer': (scan.get('recognizer') or {}).get('name')}
        if got and 'chinese' in verdicts_here:
            e.update(status='done', chinese='yes', reviewer=WRITER, slices_reviewed=True)
        elif got and verdicts_here == {'clean'}:
            e.update(status='done', chinese='no', reviewer=WRITER, slices_reviewed=True)
        else:
            e.update(status='pending', chinese='unknown', slices_reviewed=False,
                     why=scan.get('note') or 'recognizer could not settle this picture or one of its slices')
        v = verdicts.get(digest)
        if v in ('yes', 'no') and e['status'] == 'pending':
            if not str(by or '').strip():
                raise ValueError('--verdict needs --by <who looked>')
            e.update(status='done', chinese=v, reviewer=str(by), slices_reviewed=True, verdict_source='person')
        entries.append(e)
    return {'schema': 'image_review.v1', 'generated_by': {'tool': WRITER, 'scan': scan.get('status'),
                                                          'entries_sha256': entries_seal(entries)}, 'images': entries}


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
    gen = record.get('generated_by') if isinstance(record.get('generated_by'), dict) else {}
    if gen.get('tool') != WRITER or gen.get('entries_sha256') != entries_seal(entries):
        report['problems'].append('image-review.json was not written by %s (or was edited by hand afterwards): a hand-filled '
                                  'record does not count (P16, 2026-11-04). Run: python3 audit_image_review_record.py write '
                                  '--zip <upload.zip> --out docs/english/image-review.json' % WRITER)
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


def main_write(argv):
    ap = argparse.ArgumentParser(prog='audit_image_review_record.py write', description=write.__doc__)
    ap.add_argument('--zip', type=Path, required=True, help='upload package ZIP')
    ap.add_argument('--out', type=Path, required=True, help='docs/english/image-review.json')
    ap.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'windows', 'none', 'fake'])
    ap.add_argument('--verdict', action='append', default=[], metavar='SHA256=yes|no',
                    help='a person\'s verdict for a picture the recognizer left pending (needs --by)')
    ap.add_argument('--by', help='who looked at the pictures given in --verdict')
    a = ap.parse_args(argv)
    verdicts = {}
    for v in a.verdict:
        sha, _, val = v.partition('=')
        if val not in ('yes', 'no'):
            ap.error('--verdict must be SHA256=yes or SHA256=no: %r' % v)
        verdicts[sha.strip()] = val
    try:
        with zipfile.ZipFile(a.zip) as zf:
            doc = write(((n, zf.read(n)) for n in zf.namelist() if not n.endswith('/')), a.ocr, verdicts, a.by)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'written': False, 'error': str(exc)})); return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pending = [e['file'] for e in doc['images'] if e['status'] != 'done']
    still = [e['file'] for e in doc['images'] if e.get('chinese') == 'yes']
    print(json.dumps({'written': str(a.out), 'images': len(doc['images']), 'pending': pending[:20], 'chinese_still_in_package': still[:20]},
                     ensure_ascii=False))
    return 0 if not pending and not still else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['write']:
        return main_write(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path, required=True, help='upload package ZIP')
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
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
