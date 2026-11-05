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
  {"images": {sha: name}} / [sha, ...], or (v7.8) the original recorded by `art_records.py base`
  (docs/art/base-assets.json); display: optional {name or sha: (width, height)}.
CLI:  python3 audit_new_english_images.py --zip <upload.zip> --pre-english <list.json> [--out report.json]
      python3 audit_new_english_images.py --make-list <Chinese original project dir> --out <list.json> [--ocr auto|none]
      P16 (2026-11-04): --make-list also cuts every atlas slice / animation frame, reads each with the local OCR and
      writes art-replace-round1.json next to --out: "replace" = pictures/slices with Chinese (first art round), "manual_review"
      = unreadable or no recognizer (no recognizer: everything is listed, nothing is called clean).
Exit 0 pass, 1 refused, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
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
        if isinstance(doc, dict) and doc.get('kind') == 'base-assets':
            # v7.8: the original recorded by art_records.py base (docs/art/base-assets.json, {path: sha})
            return {str(s).lower() for key in ('images', 'embedded') for s in (doc.get(key) or {}).values()}
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


def _chinese_audit():
    """cocos-game-to-english/scripts/chinese_audit.py (English pack). None when this remake-core has no English skill next to it."""
    d = Path(__file__).resolve().parent.parent.parent / 'cocos-game-to-english' / 'scripts'
    if not (d / 'chinese_audit.py').is_file():
        return None
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    import chinese_audit
    return chinese_audit


def _row(item, ocr_text=None, reasons=None):
    r = {k: item.get(k) for k in ('kind', 'file', 'slice', 'atlas_file', 'atlas_format', 'pixels_sha256', 'file_sha256', 'size')
         if item.get(k) is not None}
    if ocr_text is not None:
        r['ocr_text'] = ocr_text[:20]
    if reasons:
        r['reasons'] = reasons
    return r


def scan_chinese(project, ocr='auto'):
    """P16 (生成时预防, 2026-11-04): at the START of English work, cut every atlas slice and animation frame (Cocos .plist,
    Spine/libGDX .atlas, DragonBones *_tex.json, BMFont pages, via chinese_audit.current_state) and read each whole
    picture and slice with the local recognizer (Vision on macOS, Windows.Media.Ocr via ocr_windows.ps1, tesseract).
    Pictures/slices with Chinese go straight onto the first-round art replacement list; ones the recognizer could not
    settle go to manual_review. No recognizer (or no Pillow, or no English skill next to remake-core): nothing is
    called clean, every picture and slice goes to manual_review, and the reason is written down."""
    C = _chinese_audit()
    base = {'schema': 'art_replace_round1.v1', 'tool': 'audit_new_english_images --make-list', 'replace': [],
            'manual_review': [], 'clean': 0, 'pictures': 0, 'slices': 0}
    if C is None:
        return dict(base, status='unavailable', recognizer=None,
                    note='chinese_audit.py not found next to remake-core: open every picture and atlas slice yourself')
    try:
        rec, notes = C.pick_recognizer(ocr)
        use = not isinstance(rec, C.NoRecognizer)
        tasks, tmp = {}, tempfile.mkdtemp(prefix='english-make-list-')

        def on_pixels(item, img):
            if not use:
                return
            both = item.get('rotate', 0) in (90, 270)
            key = C.receipt_key(item['pixels_sha256'], both, rec.name, rec.version)
            item['ocr_key'] = key
            if key in tasks:
                return
            prep, info = C.prepare_ocr_input(img, both)
            p = Path(tmp) / (key + '.png')
            prep.save(str(p), format='PNG')
            tasks[key] = {'key': key, 'path': str(p), 'pixels_sha256': item['pixels_sha256'], 'size': list(img.size),
                          'both': both, 'prepared': info}
        try:
            state = C.current_state(project, None, None, on_pixels)
            results = rec.run(list(tasks.values())) if tasks else {}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:  # no Pillow, unreadable project ...: fall back to "look at everything"
        return dict(base, status='unavailable', recognizer=None, note='scan could not run (%s): open every picture and '
                    'atlas slice yourself' % exc)
    out = dict(base, status='ok' if use else 'no_recognizer',
               recognizer={'name': rec.name, 'version': rec.version, 'note': rec.note, 'notes': notes})
    if not use:
        out['note'] = rec.note or 'no recognizer that reads Chinese: every picture and slice is listed for manual review'
    out['items'] = []   # (item, verdict 'chinese' | 'clean' | 'manual', ocr text, reasons); dropped before writing
    for item in state['items']:
        k = item['kind']
        if k not in ('image', 'slice', 'atlas_error'):
            continue
        if k == 'atlas_error' or item.get('error'):
            out['items'].append((item, 'manual', None, [item.get('error') or 'unreadable']))
            continue
        out['pictures' if k == 'image' else 'slices'] += 1
        if not use:
            out['items'].append((item, 'manual', None, ['not read by a recognizer']))
            continue
        r = results.get(item.get('ocr_key')) or {'ok': False, 'error': 'recognizer returned nothing', 'items': []}
        receipt = {'status': 'ok' if r.get('ok') else 'failed', 'error': r.get('error'), 'results': r.get('items') or []}
        st, reasons, hits = C.classify(receipt)
        text = [x.get('text') for x in receipt['results']]
        out['items'].append((item, 'chinese' if hits else 'manual' if st == 'needs_review' else 'clean', text, reasons))
    for item, verdict, text, reasons in out['items']:
        if verdict == 'chinese':
            out['replace'].append(_row(item, text, reasons))
        elif verdict == 'manual':
            out['manual_review'].append(_row(item, text, reasons))
        else:
            out['clean'] += 1
    return out


def make_list(project, ocr='auto', scan=True):
    out = {}
    for p in sorted(Path(project).rglob('*')):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not {'library', 'temp', 'build'} & set(p.parts):
            out[hashlib.sha256(p.read_bytes()).hexdigest()] = p.relative_to(project).as_posix()
    doc = {'source': str(Path(project).resolve()), 'images': out}
    if scan:
        scan = scan_chinese(project, ocr)
        scan.pop('items', None)
        doc['chinese_scan'] = scan
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--zip', type=Path)
    ap.add_argument('--pre-english', type=Path)
    ap.add_argument('--make-list', type=Path, help='Chinese original project: write its image SHA list to --out')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'windows', 'none', 'fake'],
                    help='--make-list: recognizer for the Chinese scan of every picture and atlas slice (default auto)')
    ap.add_argument('--replace-out', type=Path, help='--make-list: first-round art replacement list '
                    '(default: art-replace-round1.json next to --out)')
    a = ap.parse_args(argv)
    try:
        if a.make_list:
            if not a.out:
                ap.error('--make-list needs --out')
            doc = make_list(a.make_list, a.ocr)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            scan = doc['chinese_scan']
            rp = a.replace_out or a.out.parent / 'art-replace-round1.json'
            rp.write_text(json.dumps(scan, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(json.dumps({'images': len(doc['images']), 'scan': scan['status'], 'replace': len(scan['replace']),
                              'manual_review': len(scan['manual_review']), 'replace_list': str(rp)}, ensure_ascii=False))
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
