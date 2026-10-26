#!/usr/bin/env python3
"""Inventory a starter ZIP or single file without extracting or executing it.

Exit 0: structural inventory and dependency presence completed.
Exit 2: unsafe/corrupt/oversized input or incomplete dependency.
Neither result proves semantic completeness, gameplay, buildability, or acceptance.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import sys
import unicodedata
import zipfile


TEXT_SUFFIXES = {'.md', '.txt', '.tsv', '.csv', '.json', '.yaml', '.yml',
                 '.ts', '.js', '.html', '.css', '.xml'}
REQUIRED_BASE = (
    'SKILL.md', 'references/cocos-runtime.md', 'references/process-gates.md',
    'references/english-ui-rebuild.md', 'references/artwork-and-feedback.md',
    'references/common-game-components.md', 'references/full-visual-review.md',
    'references/first-level-onboarding.md',
    'references/rewarded-revive-and-help-layout.md',
    'references/local-agent-dispatch.md', 'references/prepackage-mobile-review.md',
    'references/mobile-input-gates.md', 'references/tiktok-native-iaa.md',
    'references/local-review-and-test-ids.md', 'references/ad-configuration-reuse.md',
    'references/tiktok-home-growth.md', 'references/known-issue-checklist.md',
    'references/delivery-and-handoff.md', 'assets/known-issues.json',
    'scripts/audit_project.py', 'scripts/audit_english_coverage.py',
    'scripts/audit_mobile_input.py', 'scripts/audit_platform_markers.py',
    'scripts/check_known_issues.py', 'scripts/verify_native_zip.py', 'scripts/make_tiktok_zip.py',
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def dependency_inventory(base):
    missing = [name for name in REQUIRED_BASE if not (base / name).is_file()]
    files = {}
    if base.is_dir():
        for path in sorted(base.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.name != '.DS_Store':
                files[path.relative_to(base).as_posix()] = sha256_file(path)
    revision = None
    catalog = base / 'assets/known-issues.json'
    if catalog.is_file():
        try:
            data = json.loads(catalog.read_text(encoding='utf-8'))
            revision = data.get('revision') if isinstance(data, dict) else None
        except (ValueError, UnicodeError):
            missing.append('assets/known-issues.json: unreadable JSON')
    return {'path': str(base), 'missing': missing, 'files_sha256': files,
            'catalog_revision': revision,
            'status': 'present_pending_read' if not missing else 'incomplete'}


def member_path_errors(name):
    errors = []
    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if not name or '\x00' in name or posix.is_absolute() or windows.is_absolute() or windows.drive:
        errors.append('absolute_or_invalid_path')
    if '\\' in name:
        errors.append('backslash_path')
    if any(part in {'.', '..', ''} for part in name.rstrip('/').split('/')):
        errors.append('noncanonical_or_parent_path')
    return errors


def describe_bytes(name, data):
    result = {'name': name, 'bytes': len(data),
              'sha256': hashlib.sha256(data).hexdigest(),
              'suffix': PurePosixPath(name).suffix.lower()}
    if result['suffix'] not in TEXT_SUFFIXES:
        result['kind'] = 'binary_pending_specialized_read'
        return result
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        result.update(kind='text_pending_encoding_resolution', encoding=None)
        return result
    result.update(kind='text', encoding='utf-8-sig', lines=len(text.splitlines()))
    if result['suffix'] in {'.tsv', '.csv'}:
        delimiter = '\t' if result['suffix'] == '.tsv' else ','
        try:
            rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True))
            header = rows[0] if rows else []
            malformed = [i for i, row in enumerate(rows[1:], 2) if len(row) != len(header)]
            result['table'] = {
                'columns': header, 'data_rows': max(0, len(rows) - 1),
                'duplicate_headers': sorted({h for h in header if header.count(h) > 1}),
                'nonmatching_record_numbers': malformed,
                'scope': 'structure_only_no_rule_or_solvability_validation',
            }
        except csv.Error as exc:
            result['table'] = {'parse_error': str(exc)}
    if PurePosixPath(name).name in {'project.json', 'package.json'}:
        try:
            project = json.loads(text)
            if isinstance(project, dict):
                result['cocos_manifest_candidate'] = (
                    'creator' in project or 'cocos' in str(project.get('engine', '')).lower())
        except ValueError:
            result['json_parse_error'] = True
    return result


def inspect_input(path, max_member, max_total):
    result = {'path': str(path), 'bytes': path.stat().st_size,
              'sha256': sha256_file(path), 'members': [], 'errors': []}
    if path.suffix.lower() != '.zip':
        result['format'] = 'single_file'
        if path.stat().st_size > max_member:
            result['errors'].append('single_file_exceeds_read_budget')
        else:
            result['members'].append(describe_bytes(path.name, path.read_bytes()))
        return result
    result['format'] = 'zip'
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            result['declared_expanded_bytes'] = sum(info.file_size for info in infos)
            result['archive_entries'] = len(infos)
            if result['declared_expanded_bytes'] > max_total:
                result['errors'].append('archive_exceeds_total_read_budget')
                return result
            seen = set()
            # A ZIP may contain both the file "assets" and "assets/scene.txt".
            # Check all members first so detection is independent of entry order.
            file_keys = {
                unicodedata.normalize('NFC', info.filename.rstrip('/')).casefold()
                for info in infos if not info.is_dir()
            }
            for info in infos:
                key = unicodedata.normalize('NFC', info.filename.rstrip('/')).casefold()
                errors = member_path_errors(info.filename)
                if key in seen:
                    errors.append('duplicate_or_normalized_path_collision')
                parts = key.split('/')
                if any('/'.join(parts[:i]) in file_keys for i in range(1, len(parts))):
                    errors.append('file_ancestor_path_conflict')
                seen.add(key)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    errors.append('symlink_member')
                if info.flag_bits & 1:
                    errors.append('encrypted_member')
                if info.file_size > max_member:
                    errors.append('member_exceeds_read_budget')
                if errors:
                    result['errors'].append({'name': info.filename, 'errors': errors})
                    continue
                if info.is_dir():
                    continue
                try:
                    # Reading every complete member verifies its ZIP CRC; no extraction.
                    data = archive.read(info)
                    item = describe_bytes(info.filename, data)
                    item['zip_crc_verified'] = True
                    result['members'].append(item)
                except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
                    result['errors'].append({'name': info.filename, 'read_error': str(exc)})
    except (OSError, zipfile.BadZipFile) as exc:
        result['errors'].append({'archive_error': str(exc)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; never overwritten')
    parser.add_argument('--base-skill', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'cocos-game-to-english')
    parser.add_argument('--max-member-mb', type=int, default=64, help='Read budget, not a platform limit')
    parser.add_argument('--max-total-mb', type=int, default=512, help='Read budget, not a platform limit')
    args = parser.parse_args()
    if args.max_member_mb < 1 or args.max_total_mb < 1:
        parser.error('read budgets must be positive')
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        parser.error('input must be an existing file')
    if output.exists() or not output.parent.is_dir():
        parser.error('output must be new and its parent must exist')
    report = {
        'schema': 'cocos-game-from-starter.inventory.v1',
        'scope': 'inventory_only_no_execution_extraction_or_semantic_acceptance',
        'input': inspect_input(source, args.max_member_mb * 1024**2, args.max_total_mb * 1024**2),
        'dependency': dependency_inventory(args.base_skill.expanduser().resolve()),
    }
    blocked = bool(report['input']['errors'] or report['dependency']['missing'])
    report['status'] = 'blocked' if blocked else 'inventory_complete_pending_semantic_review'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'report': str(output),
                      'members_read': len(report['input']['members']),
                      'errors': len(report['input']['errors']),
                      'missing_dependency_files': len(report['dependency']['missing'])}, ensure_ascii=False))
    return 2 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())
