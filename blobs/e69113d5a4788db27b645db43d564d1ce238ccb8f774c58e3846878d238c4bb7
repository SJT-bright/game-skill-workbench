#!/usr/bin/env python3
"""Verify the exact stable upload ZIP linked in the final response; never upload it."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from check_package import check, native_files
from audit_final_package_startup import audit_final_startup
import package_obligations


def prepare(archive, native, app_id, record, project=None, startup_contract=None, loading_recovery_runtime=None, resource_manifest=None):
    archive, native, record = (Path(p).resolve() for p in (archive, native, record))
    temporary = Path(tempfile.gettempdir()).resolve()
    if archive.is_relative_to(temporary) or any(x.casefold() in ('temp', 'rwtemp') for x in archive.parts):
        raise ValueError('delivery ZIP must be in a stable directory, not a temporary attachment path')
    if not archive.is_file() or archive.suffix.lower() != '.zip':
        raise ValueError('delivery ZIP is missing or not a ZIP file')
    if record == archive or record.is_relative_to(native):
        raise ValueError('delivery record must be outside Native and distinct from ZIP')
    if record.exists() or record.is_symlink():
        raise ValueError('delivery record already exists; choose a new record path')
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    result = check(archive, app_id, native)
    files = native_files(native)
    obligations = package_obligations.verify(files, native, project, resource_manifest)
    startup_runtime = audit_final_startup(native, project, startup_contract, loading_recovery_runtime, replay=False)
    after = hashlib.sha256(archive.read_bytes()).hexdigest()
    if before != after or result['sha256'] != after:
        raise ValueError('delivery ZIP changed while checking; retry against the final file')
    current_native = {name: hashlib.sha256(data).hexdigest()
                      for name, data in native_files(native).items()}
    if current_native != result['file_sha256']:
        raise ValueError('Native changed during delivery verification; no delivery record written')
    receipt = {'status': 'delivery_file_verified', 'archive': str(archive),
               'sha256': after, 'bytes': archive.stat().st_size,
               'native': str(native), 'app_id': app_id, 'expected_tree_exact': True,
               'markdown_link': '[' + archive.name + '](<' + str(archive) + '>)',
               'runtime_execution': result['runtime_execution'],
               'final_startup_runtime': startup_runtime,
               'package_obligations': obligations,
               'boundary': 'Local file/link identity only; include markdown_link in the actual reply. No upload performed.'}
    record.parent.mkdir(parents=True, exist_ok=True)
    with package_obligations.publication_guard(files, native, project, resource_manifest, obligations):
        with record.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--expected-app-id', required=True)
    parser.add_argument('--record', required=True, type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--startup-contract', type=Path)
    parser.add_argument('--loading-recovery-runtime', type=Path)
    parser.add_argument('--resource-manifest', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.zip, args.native, args.expected_app_id, args.record, args.project, args.startup_contract, args.loading_recovery_runtime, args.resource_manifest), ensure_ascii=False))
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
