#!/usr/bin/env python3
"""Final-package checks; shared production verifier, no gameplay CI."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

SHARED = Path(__file__).resolve().parents[3] / 'remake-core' / 'scripts'
sys.path.insert(0, str(SHARED))
import verify_native_zip as verifier
from audit_packed_assets import audit as packed_assets


def native_files(root):
    files = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink in Native: ' + str(path))
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        why = verifier.forbidden(name)
        if why == 'Finder/Windows junk file':
            continue
        if why:
            raise ValueError(name + ': ' + why)
        files[name] = path.read_bytes()
    return files


def write_archive(path, files):
    from upload_size_gate import enforce_files
    enforce_files(files)
    from audit_no_ad_simulator import enforce_files as enforce_no_simulator
    enforce_no_simulator(files)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)


def check(archive, app_id=None, tree=None):
    verified_files = {}
    result = verifier.verify(archive, expected_app_id=app_id, _verified_files=verified_files)
    if tree is not None:
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in native_files(Path(tree)).items()}
        if expected != result['file_sha256']:
            raise ValueError('final ZIP differs from actual Native input paths/bytes')
        result['expected_tree_exact'] = True
    with tempfile.TemporaryDirectory(prefix='TikTok package extract ') as folder:
        # Paths and CRC were validated above; stage those exact bytes, not a second ZIP read.
        for name, data in verified_files.items():
            target = Path(folder) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        assets = packed_assets(folder)
        if not assets['passed']:
            raise ValueError('packed resource check: ' + '; '.join(assets['errors']))
        result['packed_resource_check'] = assets
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != result['sha256']:
        raise ValueError('ZIP changed during package checks')
    # Encoding and decoding are distinct capabilities. Never silently treat
    # a successful static archive check as WebP runtime coverage.
    webp = sorted(name for name in result['file_sha256'] if name.lower().endswith('.webp'))
    result['runtime_requirements'] = []
    if webp:
        result['runtime_requirements'].append({
            'id': 'webp_decode_capability', 'status': 'requires_runtime_evidence',
            'resource_count': len(webp), 'resources': webp,
            'reference': 'cocos-game-check/package-check/references/webp-decode-capability.md',
            'cases': ['png_only_encoder_working_decoder_old_failure',
                      'png_only_encoder_working_decoder_fixed_success',
                      'normal_encoder_control', 'decoder_error_not_enabled',
                      'decoder_timeout_not_enabled', 'zero_dimensions_not_enabled',
                      'duplicate_terminal_once'],
            'boundary': 'Static detection only. Use actual final Native engine/adapter; do not force webp=true or count Canvas encoding as decoding.'})
    result['runtime_execution'] = 'not_executed_by_static_package_checker'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--expected-app-id')
    parser.add_argument('--expected-tree', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        if args.report and args.report.exists():
            raise ValueError('refuse to overwrite report')
        if args.input.is_dir():
            with tempfile.TemporaryDirectory(prefix='TikTok Native preflight ') as temp:
                zipped = Path(temp) / 'candidate.zip'
                write_archive(zipped, native_files(args.input))
                result = check(zipped, args.expected_app_id, args.input)
                result['input'] = str(args.input.resolve())
                result.pop('archive', None)
        else:
            result = check(args.input, args.expected_app_id, args.expected_tree)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('file_sha256', 'packed_resource_check')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(json.dumps({'status':'refuse', 'error':str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
