#!/usr/bin/env python3
"""Review English trial and Native images before the formal trial. Delivery only verifies the record.

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
API for the package entries (board localize):  check(files, record_path) -> {"passed": bool, "problems": [...], ...}
  files: a dict {name: bytes}, an iterable of (name, bytes) pairs, or an iterable of file paths.
CLI:  python3 audit_image_review_record.py --zip <upload.zip> --record <image-review.json> [--out report.json]
      python3 audit_image_review_record.py write --directory <Web> --directory <prepared Native>
                                         --out docs/english/image-review.json [--ocr auto]
                                         [--verdict <sha256>=yes|no ... --by "<who>"]
      Both modes also accept a ZIP as input, or one or more --directory arguments.
P16 (2026-11-04): the record is written ONLY by `write` (OCR of every image and slice in the package, sealed with
generated_by.entries_sha256); a hand-filled or hand-edited record is refused.
Exit 0 pass, 1 refused, 2 bad input.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import sys
import zipfile

IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp')
import spine_atlas_binding as spine

ATLAS_SUFFIXES = ('.plist', '.atlas', '.fnt', 'tex.json')


def _atlas_input(name):
    return name.lower().endswith(ATLAS_SUFFIXES)


def _review_input(name):
    return (name.lower().endswith(IMAGE_SUFFIXES) or _atlas_input(name)
            or spine.CONFIG.fullmatch(name) or spine.IMPORT.fullmatch(name))


def directory_items(directories):
    """Read actual export bytes. Give each root its own namespace so atlas sidecars keep their neighbours."""
    directories = [Path(directory).resolve() for directory in directories]
    for i, root in enumerate(directories, 1):
        if not root.is_dir():
            raise ValueError('image review input is not a directory: %s' % root)
        for path in sorted(root.rglob('*')):
            rel = path.relative_to(root).as_posix()
            name = 'export-%d/%s' % (i, rel) if len(directories) > 1 else rel
            if not _review_input(name):
                continue
            if path.is_symlink():
                raise ValueError('symbolic link in image review input: %s' % path)
            if path.is_file():
                yield name, path.read_bytes()


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



def _descriptor_text(data):
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return data.decode(encoding)


def _atlas_context(names, descriptors, chinese, inputs):
    """Bind each texture to the exact descriptors and page names that determine its slices."""
    contexts, expected_slices, spine_pages = {}, {}, {}
    try:
        configs = spine.bundle_configs(inputs)
        missing = sorted(set(spine.missing_runtime_atlases(inputs, configs)))
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        raise ValueError('could not read runtime Spine inventory: %s' % error) from error
    if missing:
        raise ValueError('missing runtime Spine atlas: ' + ', '.join(missing))
    if chinese is None:
        if any(name.lower().endswith('.atlas') for name in descriptors):
            raise ValueError('Spine atlas verification requires the English audit module')
        return contexts, expected_slices, spine_pages
    for name, data in descriptors.items():
        regions, bindings = [], {}
        low = name.lower()
        try:
            if low.endswith('.atlas'):
                pages, regions = chinese.parse_spine_atlas(_descriptor_text(data))
                page_names = [page['file'] for page in pages]
                if not page_names or not regions or len(set(page_names)) != len(page_names):
                    raise ValueError('missing or repeated Spine pages, or no slices')
                if spine.COMPILED.fullmatch(name):
                    bindings = spine.resolve(inputs, name, page_names, configs)
            elif low.endswith('.plist'):
                parsed = chinese.parse_plist_atlas(data)
                if parsed is None:
                    continue
                pages, regions = parsed
            elif low.endswith('.fnt'):
                pages, _ = chinese.parse_bmfont(_descriptor_text(data))
            else:
                parsed = chinese.parse_dragonbones_tex(json.loads(_descriptor_text(data)))
                if parsed is None:
                    continue
                pages, regions = parsed
        except (ValueError, TypeError, KeyError, AttributeError, SyntaxError, IndexError) as error:
            if low.endswith('tex.json') and b'SubTexture' not in data:
                continue
            raise ValueError('atlas descriptor %s could not be read: %s' % (name, error)) from error
        descriptor = hashlib.sha256(data).hexdigest()
        parent = posixpath.dirname(name)
        count = {}
        for region in regions:
            file = region.get('page')
            count[file] = count.get(file, 0) + 1
        for page in pages:
            file = page.get('file')
            candidates = []
            if file:
                candidates.extend((posixpath.normpath(posixpath.join(parent, file)),
                                   posixpath.join(parent, posixpath.basename(file))))
            if not file or not PurePosixPath(file).suffix:
                candidates.extend(str(PurePosixPath(name).with_suffix(ext)) for ext in IMAGE_SUFFIXES)
            binding = bindings.get(file)
            image = (binding['texture'] if binding else
                     next((candidate for candidate in candidates if candidate in names), None))
            if low.endswith('.atlas'):
                if image not in names or not count.get(file):
                    raise ValueError('Spine atlas %s has no reviewable texture or slices for page %s' % (name, file))
                spine_pages.setdefault('assets/' + name, {})[file] = 'assets/' + image
            if image is not None:
                identity = descriptor + ':' + (file or '')
                if binding:
                    identity += ':' + binding['texture_uuid']
                    if binding['image_uuid'] != binding['texture_uuid']:
                        identity += ':' + binding['image_uuid']
                contexts.setdefault(names[image], set()).add(identity)
                expected_slices[image] = expected_slices.get(image, 0) + count.get(file, 0)
    return {digest: sorted(values) for digest, values in contexts.items()}, expected_slices, spine_pages


def _review_files(files):
    inputs, names, descriptors = {}, {}, {}
    for name, data in _items(files):
        if not _review_input(name):
            continue
        if callable(getattr(data, 'read', None)):
            data = data.read()
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix() != name or name in inputs:
            raise ValueError('noncanonical or repeated image review input: ' + name)
        inputs[name] = data
        if name.lower().endswith(IMAGE_SUFFIXES):
            names[name] = hashlib.sha256(data).hexdigest()
        elif _atlas_input(name):
            descriptors[name] = data
    return inputs, names, descriptors


def _record_entries(record):
    if not isinstance(record, dict) or record.get('schema') != 'image_review.v1':
        return None
    entries, gen = record.get('images'), record.get('generated_by')
    if (isinstance(entries, list) and isinstance(gen, dict) and gen.get('tool') == WRITER
            and gen.get('entries_sha256') == entries_seal(entries)):
        return entries
    return None


def _entries_by_sha(entries):
    out = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get('sha256'), str):
            out.setdefault(entry['sha256'].lower(), entry)
    return out


def _review_rules(chinese):
    if chinese is None:
        return None
    paths = [Path(__file__), Path(__file__).with_name('audit_new_english_images.py'), Path(chinese.__file__), Path(spine.__file__)]
    return entries_seal([hashlib.sha256(path.read_bytes()).hexdigest() for path in paths])


def _read_record(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(files, ocr='auto', verdicts=None, by=None, previous=None):
    """Build the record from the exports or ZIP (P16, 2026-11-04: image-review.json is written only by this script).

    Every distinct package image and every slice/frame inside it is read by the local recognizer (via
    audit_new_english_images.scan_chinese -> chinese_audit). chinese = yes if the picture or any of its slices has Chinese;
    no if the picture and all slices were read clean. Anything the recognizer could not settle (or every image, on a
    computer with no recognizer) stays "pending" until a person gives a verdict: verdicts {sha256: 'yes'|'no'} with by=<who>.
    An existing clean entry is reused when the image bytes, slice descriptors and review tools are unchanged.
    """
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import audit_new_english_images as ani
    verdicts = {k.lower(): v for k, v in (verdicts or {}).items()}
    chinese = ani._chinese_audit()
    rules = _review_rules(chinese)
    previous_entries = _record_entries(previous)
    old = {}
    if previous_entries is not None and rules is not None:
        gen = previous['generated_by']
        if gen.get('rules_sha256') == rules and gen.get('ocr') == ocr:
            old = _entries_by_sha(previous_entries)
    inputs, names, descriptors = _review_files(files)
    contexts, expected_slices, spine_pages = _atlas_context(names, descriptors, chinese, inputs)
    by_sha = {}
    for name, digest in names.items():
        by_sha.setdefault(digest, []).append(name)
    unknown_verdicts = set(verdicts) - set(by_sha)
    if unknown_verdicts:
        raise ValueError('manual verdict SHA is not an actual input image: ' + ', '.join(sorted(unknown_verdicts)))
    reused = {}
    for digest, paths in by_sha.items():
        entry = old.get(digest, {})
        if (digest not in verdicts and entry.get('status') == 'done' and entry.get('chinese') == 'no'
                and entry.get('slices_reviewed') is True and str(entry.get('reviewer') or '').strip()
                and entry.get('atlas_context') == contexts.get(digest, [])):
            reused[digest] = dict(entry, file=paths[0])
    scan = {'status': 'reused'}
    if len(reused) < len(by_sha):
        with tempfile.TemporaryDirectory(prefix='image-review-') as scratch:
            root = Path(scratch) / 'assets'
            root.mkdir()
            changed = {name: inputs[name] for name, digest in names.items() if digest not in reused}
            changed.update(descriptors)
            for name, data in changed.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            scan = ani.scan_chinese(Path(scratch), ocr, spine_pages=spine_pages)
    per_file = {}
    slice_findings = {}
    for item, verdict, text, reasons in scan.get('items') or []:
        f = item.get('file')
        if f and not item.get('error'):
            per_file.setdefault(f, []).append((item['kind'], verdict, text))
        if f and item['kind'] == 'slice' and verdict != 'clean':
            slice_findings.setdefault(f, []).append({
                'atlas': item['atlas_file'].removeprefix('assets/'), 'slice': item['slice'],
                'region': item['region'], 'verdict': verdict, 'text': text, 'reasons': reasons,
            })
    entries = []
    for digest, paths in sorted(by_sha.items(), key=lambda kv: kv[1][0]):
        name = paths[0]
        if digest in reused:
            entries.append(reused[digest])
            continue
        uses = [per_file.get('assets/' + path, []) for path in paths]
        has_all_slices = all(sum(row[0] == 'slice' for row in use) >= expected_slices.get(path, 0)
                             for path, use in zip(paths, uses))
        got = [entry for use in uses for entry in use]
        slices = [g for g in got if g[0] == 'slice']
        verdicts_here = {g[1] for g in got}
        e = {'sha256': digest, 'file': name, 'atlas': bool(slices), 'slices': len(slices),
             'atlas_context': contexts.get(digest, []),
             'recognizer': (scan.get('recognizer') or {}).get('name')}
        findings = [finding for path in paths for finding in slice_findings.get('assets/' + path, ())]
        if findings:
            e['slice_finding_count'] = len(findings)
            e['slice_findings'] = findings[:20]
        if got and 'chinese' in verdicts_here:
            e.update(status='done', chinese='yes', reviewer=WRITER, slices_reviewed=True)
        elif all(uses) and has_all_slices and verdicts_here == {'clean'}:
            e.update(status='done', chinese='no', reviewer=WRITER, slices_reviewed=True)
        else:
            e.update(status='pending', chinese='unknown', slices_reviewed=False,
                     why=scan.get('note') or 'recognizer could not settle this picture or one of its slices')
        v = verdicts.get(digest)
        if v in ('yes', 'no'):
            if not has_all_slices:
                raise ValueError('manual verdict cannot replace missing atlas slices: ' + name)
            if not str(by or '').strip():
                raise ValueError('--verdict needs --by <who looked>')
            e['recognizer_verdict'] = {'status': e['status'], 'chinese': e.get('chinese'), 'text': [g[2] for g in got]}
            e.update(status='done', chinese=v, reviewer=str(by), slices_reviewed=True, verdict_source='person')
        entries.append(e)
    if len(reused) == len(by_sha) and entries == previous_entries:
        return previous
    return {'schema': 'image_review.v1', 'generated_by': {'tool': WRITER, 'scan': scan.get('status'), 'ocr': ocr,
                                                          'rules_sha256': rules, 'reused': len(reused),
                                                          'entries_sha256': entries_seal(entries)}, 'images': entries}


def check(files, record_path):
    inputs, names, descriptors = _review_files(files)
    images = {}
    for name, digest in names.items():
        images.setdefault(digest, name)
    plists = {name.lower()[:-len('.plist')] for name in descriptors if name.lower().endswith('.plist')}
    report = {'tool': 'audit_image_review_record', 'schema': 1, 'record': str(record_path), 'distinct_images': len(images),
              'problems': [], 'passed': False}
    try:
        record = _read_record(record_path)
        if not isinstance(record, dict) or not isinstance(record.get('images'), list):
            raise ValueError('no "images" list')
    except (OSError, ValueError) as exc:
        report['problems'].append('image review record missing or unreadable (%s): return to pre-trial review of every distinct image in the Web and Native '
                                  'exports and write docs/english/image-review.json' % exc)
        return report
    entries = _record_entries(record)
    if entries is None:
        report['problems'].append('image-review.json was not written by %s (or was edited by hand afterwards): a hand-filled '
                                  'record does not count (P16, 2026-11-04). Run: python3 audit_image_review_record.py write '
                                  '--directory <Web> --directory <prepared Native> --out docs/english/image-review.json' % WRITER)
        return report
    try:
        import audit_new_english_images as ani
        contexts, _, _ = _atlas_context(names, descriptors, ani._chinese_audit(), inputs)
    except ValueError as error:
        report['problems'].append(str(error))
        return report
    atlas_digests = {digest for name, digest in names.items() if name.lower().rsplit('.', 1)[0] in plists}
    by_sha = _entries_by_sha(entries)
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
        current = contexts.get(digest, [])
        recorded = e.get('atlas_context')
        if current and (not isinstance(recorded, list) or any(value not in recorded for value in current)):
            report['problems'].append('%s: atlas descriptor or page changed; review the current slices before trial' % name)
        if (e.get('atlas') or current or digest in atlas_digests) and e.get('slices_reviewed') is not True:
            report['problems'].append('%s: atlas must be reviewed slice by slice ("slices_reviewed": true)' % name)
    report['passed'] = not report['problems']
    return report


def input_args(parser):
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--zip', type=Path, help='existing package ZIP')
    inputs.add_argument('--directory', type=Path, action='append', help='export root, repeat for Web and prepared Native')


def input_items(args):
    if args.zip:
        with zipfile.ZipFile(args.zip) as archive:
            for name in archive.namelist():
                if _review_input(name):
                    yield name, archive.read(name)
    else:
        yield from directory_items(args.directory)


def main_write(argv):
    ap = argparse.ArgumentParser(prog='audit_image_review_record.py write', description=write.__doc__)
    input_args(ap)
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
        previous = _read_record(a.out)
    except (OSError, ValueError):
        previous = None
    try:
        doc = write(input_items(a), a.ocr, verdicts, a.by, previous)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'written': False, 'error': str(exc)})); return 2
    if doc is not previous:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    reused = len(doc['images']) if doc is previous else doc['generated_by']['reused']
    pending = [e['file'] for e in doc['images'] if e['status'] != 'done']
    still = [e['file'] for e in doc['images'] if e.get('chinese') == 'yes']
    print(json.dumps({'written': str(a.out), 'images': len(doc['images']), 'reused': reused, 'pending': pending[:20], 'chinese_still_in_package': still[:20]},
                     ensure_ascii=False))
    return 0 if not pending and not still else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['write']:
        return main_write(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    input_args(ap)
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    try:
        r = check(input_items(a), a.record)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)})); return 2
    if a.zip:
        r['zip'] = str(a.zip)
    else:
        r['directories'] = [str(path.resolve()) for path in a.directory]
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': r['passed'], 'distinct_images': r['distinct_images'], 'problems': r['problems'][:10]}, ensure_ascii=False))
    return 0 if r['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
