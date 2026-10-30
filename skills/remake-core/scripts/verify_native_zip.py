#!/usr/bin/env python3
"""Local TikTok Native ZIP structure/bytes check, not platform or device acceptance.

User 2026-10-23 (SquareRush UPLOADFIX): every package is the one uploadable TikTok form, and the TikTok size limits are
built in (not optional): uncompressed main package <= 4,000,000 bytes, total <= 30,000,000 bytes, each independent
subpackage <= 4,000,000 bytes; normal subpackages count only toward the total. --max-*-bytes can only make a limit
stricter. Also refused: an outer folder, a Web build (index.html), Finder/Windows junk, a ZIP inside the ZIP, source-project
files (.ts, .meta, library/, temp/ ...), non-ASCII paths and the test-only level jump marker.

v7.5 (D7 items 1/14): the result carries entry = official | unofficial (官方入口 / 非官方入口). Only a ZIP with a
matching <zip>.receipt.json written by make_tiktok_zip.py or build_checked_zip.py is official; this read-only check
never writes a receipt, so "verify + ordinary zip" stays unofficial and prepare_delivery.py refuses it.

v7.7 (design D77 1.6): receipt schema 2 carries `finalize`, the writer's tiktok_finalize native record in short
(kit version, policy and why, each step's state and changed files, the Chinese parts table, the source record's
digest). A receipt without it, with a refused or --policy (test-only) finalize, or whose finalized files differ from
the ZIP is not official, so a ZIP that never went through finalize cannot be delivered.

v7.7.4 (总表 B17): run as a command, an unofficial ZIP is refused (status unofficial_not_deliverable, exit 3), so
"verify + ordinary zip" can no longer look like a pass (DriftRacer v2 shipped an outdated ad service that way).
--structure-only keeps the read-only structure answer for diagnosis. Writers and checks that import verify() are
unchanged."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

QA_MARKER = b'__QA_LEVEL_JUMP__'  # test-only level jump; must never ship
TIKTOK_MAIN, TIKTOK_TOTAL, TIKTOK_INDEPENDENT = 4_000_000, 30_000_000, 4_000_000
LIMITS_SOURCE = ('TikTok Minis overview 2026-10-05 (non-Unity): total 30MB, main 4MB, each independent subpackage 4MB, '
                 'normal subpackages count toward the total only; enforced in bytes as 30,000,000 / 4,000,000')
JUNK_NAMES = {'.ds_store', 'thumbs.db', 'desktop.ini', '.gitkeep', '.git', '.svn'}
ARCHIVES = ('.zip', '.7z', '.rar', '.tar', '.gz', '.tgz', '.apk', '.ipa')
SOURCE_SUFFIXES = ('.ts', '.meta', '.scene', '.prefab', '.fire', '.psd', '.blend')
SOURCE_DIRS = {'library', 'temp', 'local', 'profiles', 'node_modules', '.creator', 'extensions', 'packages', 'settings', 'build'}
SOURCE_FILES = {'tsconfig.json', 'creator.d.ts', 'package-lock.json', 'cocos.config.json', 'project.json'}
FIX_SIZE = ('move assets/resources (and other big bundles) into a Cocos mini-game NORMAL subpackage (subpackages/<name>, '
            'declared in game.json "subpackages") and load it at startup with visible progress and Retry; the main package '
            'keeps only the engine, entry and first-screen files')


def forbidden(name):
    """Why this entry may not be in the TikTok upload package, or None."""
    parts = name.rstrip('/').split('/')
    base = parts[-1].casefold()
    if '__MACOSX' in parts or base in JUNK_NAMES or base.startswith('._'):
        return 'Finder/Windows junk file'
    if base.endswith(ARCHIVES):
        return 'an archive inside the upload ZIP (zip-in-zip): upload the Native files themselves'
    if base.endswith(SOURCE_SUFFIXES):
        return 'a source-project file (.ts/.meta/scene/prefab/source art): the upload package is the built Native output only'
    if parts[0].casefold() in SOURCE_DIRS or base in SOURCE_FILES:
        return 'a source-project folder/file (library, temp, settings, build ...): zip the Native build output, not the project'
    if len(parts) == 1 and base in ('index.html', 'index.htm'):
        return 'index.html at the root: this is a Web build (web-mobile), not the TikTok Native mini-game build'
    if any(ord(ch) > 126 or ord(ch) < 32 for ch in name):
        return 'a non-ASCII path (rename it with ASCII letters, digits, _ - .)'
    return None


RECEIPT_TOOLS = ('make_tiktok_zip', 'build_checked_zip')
RECEIPT_SUFFIX = '.receipt.json'
ENTRY_LABEL = {'official': '官方入口', 'unofficial': '非官方入口'}
# v7.7.4 (总表 B17): the standalone verify_native_zip / upload_preflight refusal for an unofficial ZIP.
UNOFFICIAL_REFUSAL = ('not deliverable: unofficial entry (非官方入口) - %s. Only a ZIP written by build_checked_zip.py '
                      'or make_tiktok_zip.py (with <zip>.receipt.json beside it) may be uploaded or delivered; '
                      'add --structure-only for a read-only structure check')


def receipt_path(archive):
    """<Game>.zip -> <Game>.zip.receipt.json next to it (written only by the two official writers)."""
    return Path(str(Path(archive)) + RECEIPT_SUFFIX)


def tree_digest(file_sha256):
    """One digest for a {path: sha256} map (the Native tree that went into the ZIP)."""
    h = hashlib.sha256()
    for name in sorted(file_sha256):
        h.update(name.encode('utf-8') + b'\0' + file_sha256[name].encode('ascii') + b'\n')
    return h.hexdigest()


RECEIPT_SCHEMA = 2


def finalize_summary(record):
    """Short form of a tiktok_finalize.finalize_native record for receipts and reports (no file bytes)."""
    if not isinstance(record, dict):
        return None
    decision = record.get('decision') or {}
    steps = []
    for step in record.get('steps') or []:
        steps.append({'step': step.get('step'), 'state': step.get('state'),
                      'changed': [{'file': c.get('file'), 'after_sha256': c.get('after_sha256'), 'what': c.get('what')}
                                  for c in step.get('changed') or []],
                      'blocks': [b.get('id') for b in step.get('blocks') or []],
                      'warnings': [w.get('id') for w in step.get('warnings') or []]})
    return {'kind': record.get('kind'), 'kit_version': record.get('kit_version'), 'policy': record.get('policy'),
            'policy_reason': decision.get('reason'), 'legacy_match': [m.get('folder') for m in
                                                                      decision.get('legacy_match') or []],
            'policy_override': bool(record.get('policy_override')), 'board': record.get('board'),
            'engine': record.get('engine'), 'blocks': [b.get('id') for b in record.get('blocks') or []],
            'warnings': ['%s: %s' % (w.get('id'), w.get('message')) for w in record.get('warnings') or []],
            'files_after': dict(record.get('files_after') or {}), 'table': record.get('table') or [],
            'steps': steps, 'source_record': record.get('source_record')}


def finalize_problem(summary, file_sha256):
    """Why a receipt's finalize summary does not prove THIS package went through finalize, or None."""
    if not isinstance(summary, dict) or summary.get('kind') != 'finalize-native':
        return 'writer receipt has no finalize record (written before v7.7 or by hand): rewrite the ZIP with the v7.7 writer'
    if summary.get('blocks'):
        return 'writer receipt records a refused finalize: %s' % ', '.join(map(str, summary['blocks'][:3]))
    if summary.get('policy_override'):
        return 'writer receipt records finalize with --policy (tests and calibration only)'
    if summary.get('policy') not in ('new', 'legacy'):
        return 'writer receipt finalize record has no policy'
    for rel, digest in sorted((summary.get('files_after') or {}).items()):
        if digest is None and rel in file_sha256:
            return 'finalize moved %s away but it is in the ZIP' % rel
        if digest is not None and file_sha256.get(rel) != digest:
            return 'finalize wrote %s but the ZIP holds other bytes' % rel
    return None


def make_receipt(tool, zip_path, zip_sha256, file_sha256, gate_result, board, extra=None, finalize=None):
    """finalize: the writer's finalize_native record (or its finalize_summary); required since v7.7."""
    if tool not in RECEIPT_TOOLS:
        raise ValueError('receipt tool must be one of the official writers')
    import datetime
    if isinstance(finalize, dict) and 'decision' in finalize:      # a full record, not yet summarised
        finalize = finalize_summary(finalize)
    receipt = {'schema': RECEIPT_SCHEMA, 'tool': tool, 'zip': Path(zip_path).name, 'zip_sha256': zip_sha256,
               'zip_bytes': Path(zip_path).stat().st_size, 'native_tree_sha256': tree_digest(file_sha256),
               'files': len(file_sha256), 'board': board,
               'gate_result': {'passed': not gate_result.get('blocks'), 'blocks': gate_result.get('blocks', []),
                               'warnings': [w.get('id') for w in gate_result.get('warnings', [])],
                               'gates': gate_result.get('gates', []), 'missing': gate_result.get('missing', []),
                               'policy': gate_result.get('policy'), 'policy_reason': gate_result.get('policy_reason')},
               'finalize': finalize,
               'created': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'boundary': 'Written by the official writer after every package gate passed; local structure only, '
                           'not platform or device acceptance.'}
    if extra:
        receipt.update(extra)
    return receipt


def receipt_status(archive, zip_sha256, file_sha256):
    """'official' only when <zip>.receipt.json was written by an official writer for exactly these bytes."""
    path = receipt_path(archive)
    out = {'entry': 'unofficial', 'entry_label': ENTRY_LABEL['unofficial'], 'receipt': str(path)}
    if not path.is_file() or path.is_symlink():
        out['entry_reason'] = ('no writer receipt %s: this ZIP was not written by make_tiktok_zip.py / build_checked_zip.py '
                               '(hand-zipped or renamed)' % path.name)
        return out
    try:
        receipt = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        out['entry_reason'] = 'writer receipt unreadable: %s' % error
        return out
    if not isinstance(receipt, dict) or receipt.get('tool') not in RECEIPT_TOOLS:
        out['entry_reason'] = 'writer receipt is not from an official writer'
    elif receipt.get('zip_sha256') != zip_sha256:
        out['entry_reason'] = 'writer receipt is for other ZIP bytes (zip_sha256 differs): the ZIP was changed or re-zipped'
    elif receipt.get('native_tree_sha256') != tree_digest(file_sha256):
        out['entry_reason'] = 'writer receipt is for another Native tree (native_tree_sha256 differs)'
    elif not isinstance(receipt.get('gate_result'), dict) or receipt['gate_result'].get('passed') is not True \
            or receipt['gate_result'].get('blocks'):
        out['entry_reason'] = 'writer receipt does not record a passed package gate'
    elif finalize_problem(receipt.get('finalize'), file_sha256):
        out['entry_reason'] = finalize_problem(receipt.get('finalize'), file_sha256)
    else:
        out.update(entry='official', entry_label=ENTRY_LABEL['official'], entry_reason='matching receipt from ' + receipt['tool'],
                   receipt_tool=receipt['tool'], receipt_board=receipt.get('board'),
                   receipt_policy=receipt['finalize'].get('policy'), receipt_kit_version=receipt['finalize'].get('kit_version'))
    return out


def safe_name(name):
    if not name or name.startswith('/') or '\\' in name or re.match(r'^[A-Za-z]:', name):
        raise ValueError('Unsafe archive path: ' + name)
    raw_parts = name.rstrip('/').split('/')
    if any(p in ('', '.', '..') for p in raw_parts):
        raise ValueError('Unsafe archive path: ' + name)
    return PurePosixPath(name)


def stricter(value, limit):
    return limit if value is None else min(value, limit)


def verify(archive, expected_app_id=None, expected_tree=None, max_main=None, max_total=None, max_independent=None, tiktok=True, *, _verified_files=None):
    """tiktok=True (default): the built-in TikTok limits and forbidden entries apply; explicit limits can only be lower."""
    if _verified_files is not None and (type(_verified_files) is not dict or _verified_files):
        raise ValueError('verified payload output must be an empty dict')
    archive_before = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    contents = {}
    if tiktok:
        max_main, max_total = stricter(max_main, TIKTOK_MAIN), stricter(max_total, TIKTOK_TOTAL)
        max_independent = stricter(max_independent, TIKTOK_INDEPENDENT)
    hashes, sizes, seen = {}, {}, set()
    with zipfile.ZipFile(archive) as z:
        names = [i.filename for i in z.infolist()]
        if tiktok and not any(n == 'game.json' for n in names):
            tops = {n.split('/', 1)[0] for n in names if n.strip('/')}
            if len(tops) == 1 and any(n.split('/', 1)[-1] == 'game.json' for n in names if '/' in n):
                raise ValueError('Outer folder "%s/" around the Native files: zip the CONTENTS of the Native build folder so '
                                 'game.js, game.json and project.config.json are at the ZIP root' % tops.pop())
            if any(n.rsplit('/', 1)[-1].casefold() == 'index.html' for n in names):
                raise ValueError('This is a Web build (index.html, no game.json): build the TikTok Native mini-game in Cocos; '
                                 'never rename a Web ZIP as the upload package')
        for info in z.infolist():
            safe_name(info.filename)
            why = forbidden(info.filename) if tiktok else None
            if why:
                raise ValueError('Not allowed in the TikTok upload package: %s - %s' % (info.filename, why))
            canonical = info.filename.rstrip('/').casefold()
            if canonical in seen:
                raise ValueError('Duplicate or case-colliding archive path: ' + info.filename)
            seen.add(canonical)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Symlink entry is not allowed: ' + info.filename)
            if info.flag_bits & 1:
                raise ValueError('Encrypted entry is not a normal upload file: ' + info.filename)
            if info.is_dir():
                continue
            sizes[info.filename] = info.file_size
        file_paths = {name.casefold() for name in sizes}
        for name in sizes:
            for parent in PurePosixPath(name).parents:
                if parent.as_posix().casefold() in file_paths:
                    raise ValueError('File/directory collision: ' + name)
        for name in ('game.js', 'game.json', 'project.config.json'):
            if not sizes.get(name):
                raise ValueError('Missing or empty root file: ' + name + '; select the Native upload ZIP, without an outer delivery folder')
        total = sum(sizes.values())
        if max_total is not None and total > max_total:
            raise ValueError('Uncompressed total package %d bytes exceeds the limit %d bytes' % (total, max_total))
        contents['game.json'] = z.read('game.json')
        contents['project.config.json'] = z.read('project.config.json')
        game = json.loads(contents['game.json'])
        project = json.loads(contents['project.config.json'])
        if not isinstance(game, dict) or not isinstance(project, dict):
            raise ValueError('Root configurations must be JSON objects')
        app_id = project.get('appid')
        if not isinstance(app_id, str):
            raise ValueError('project.config.json appid must be a string')
        if expected_app_id is not None and app_id != expected_app_id:
            raise ValueError('Root App ID does not match the requested target')
        subpackages = game.get('subpackages', [])
        if not isinstance(subpackages, list):
            raise ValueError('game.json subpackages must be an array')
        roots, independent, normal, warnings = [], {}, {}, []
        for sub in subpackages:
            if not isinstance(sub, dict) or not isinstance(sub.get('root'), str):
                raise ValueError('Each subpackage needs a relative root')
            root = safe_name(sub['root']).as_posix().rstrip('/') + '/'
            if not any(n.startswith(root) for n in sizes):
                raise ValueError('Declared subpackage has no files: ' + root)
            roots.append(root)
            bytes_ = sum(size for name, size in sizes.items() if name.startswith(root))
            (independent if sub.get('independent') is True else normal)[root] = bytes_
            if root + 'game.js' not in sizes:
                warnings.append('subpackage %s has no game.js entry: check it matches what the Cocos loader expects' % root)
        for root, bytes_ in independent.items():
            if max_independent is not None and bytes_ > max_independent:
                raise ValueError('Independent subpackage %s is %d bytes, over the limit %d bytes: make it a normal subpackage or '
                                 'split it' % (root, bytes_, max_independent))
        main_files = {name: size for name, size in sizes.items() if not any(name.startswith(root) for root in roots)}
        main = sum(main_files.values())
        if max_main is not None and main > max_main:
            big = sorted(main_files.items(), key=lambda kv: -kv[1])[:5]
            raise ValueError('Uncompressed main package %d bytes exceeds the limit %d bytes (biggest: %s): %s'
                             % (main, max_main, ', '.join('%s %d' % kv for kv in big), FIX_SIZE))
        for name in sorted(sizes):
            if name not in contents:
                contents[name] = z.read(name)  # reading verifies CRC exactly once
            data = contents[name]
            from audit_no_ad_simulator import check_entry
            check_entry(name, data)
            if QA_MARKER in data:
                raise ValueError('Test-only level jump (' + QA_MARKER.decode() + ') is still in the upload package: ' + name)
            hashes[name] = hashlib.sha256(data).hexdigest()
        from audit_upload_startup import audit_files
        startup = audit_files(contents)
        if not startup['passed']:
            raise ValueError('Startup dependency check failed: ' + '; '.join(startup['errors']))
    if expected_tree is not None:
        tree = Path(expected_tree)
        if not tree.is_dir():
            raise ValueError('Expected tree is not a directory')
        actual = {}
        for f in tree.rglob('*'):
            if f.is_symlink():
                raise ValueError('Expected tree contains a symlink')
            if f.is_file():
                actual[f.relative_to(tree).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
        if actual != hashes:
            raise ValueError('ZIP and expected tree differ in paths or file bytes')
    archive_after = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    if archive_before != archive_after:
        raise ValueError('ZIP changed during verification')
    if _verified_files is not None:
        _verified_files.update(contents)
    entry = receipt_status(archive, archive_after, hashes)
    return {
        'archive': str(Path(archive).resolve()),
        'sha256': archive_after,
        'archive_bytes': Path(archive).stat().st_size,
        'files': len(hashes), 'uncompressed_total_bytes': total,
        'main_bytes': main, 'subpackage_roots': roots, 'appId': app_id,
        'crc_and_safe_paths': True, 'root_entries': True, 'no_test_level_jump': True,
        'no_local_ad_simulator': True,
        'expected_tree_exact': expected_tree is not None,
        'status': 'local_structure_checks_passed', 'file_sha256': hashes,
        'limits': {'total': max_total, 'main': max_main, 'independent_subpackage': max_independent,
                   'source': LIMITS_SOURCE if tiktok else 'supplied by the caller'},
        'independent_subpackages': independent, 'normal_subpackages': normal, 'warnings': warnings,
        'tiktok_upload_form': bool(tiktok),
        'startup_dependency_check': startup,
        'not_verified': ['Client Key/ad ownership or enablement', 'SDK behavior', 'DevTool', 'real phone/IAA', 'platform upload/release'],
        **entry,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('--expected-app-id')
    p.add_argument('--expected-tree', type=Path)
    p.add_argument('--max-main-bytes', type=int)
    p.add_argument('--max-total-bytes', type=int)
    p.add_argument('--max-independent-bytes', type=int, help='only stricter than the built-in TikTok limits')
    p.add_argument('--report', type=Path, help='New report file; existing reports are preserved')
    p.add_argument('--structure-only', action='store_true',
                   help='read-only structure diagnosis: do not refuse a ZIP without a matching writer receipt')
    args = p.parse_args()
    refused = None
    try:
        if args.report and args.report.exists():
            raise ValueError('Report already exists; choose a new path')
        for value in (args.max_main_bytes, args.max_total_bytes, args.max_independent_bytes):
            if value is not None and value <= 0:
                raise ValueError('Package limits must be positive')
        result = verify(args.archive, args.expected_app_id, args.expected_tree, args.max_main_bytes, args.max_total_bytes,
                        args.max_independent_bytes)
        if result['entry'] != 'official' and not args.structure_only:
            refused = UNOFFICIAL_REFUSAL % result['entry_reason']
            result.update(status='unofficial_not_deliverable', refused=refused)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in result.items() if k != 'file_sha256'}, ensure_ascii=False, indent=2))
        print('entry: %s (%s) - %s' % (result['entry'], result['entry_label'], result['entry_reason']))
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print('Native ZIP check failed: ' + str(error), file=sys.stderr)
        return 2
    if refused:
        print('REFUSED: ' + refused, file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main())
