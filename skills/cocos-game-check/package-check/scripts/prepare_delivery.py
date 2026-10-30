#!/usr/bin/env python3
"""Verify the exact stable upload ZIP linked in the final response; never upload it.

v7.5 (D7 items 1, 14, 15): refuses a ZIP without a matching <zip>.receipt.json from make_tiktok_zip.py /
build_checked_zip.py (hand-zipped "verify + ordinary zip" packages are 非官方入口), and with --logic-report refuses
when the logic_check report's current_source_sha256 differs from the delivered source (--source folder or ZIP).

v7.7: the writer receipt must carry a passed finalize record (verify_native_zip receipt schema 2), so a ZIP that never
went through tiktok_finalize is unofficial and refused. The delivery record repeats the finalize policy and the
Chinese parts table for the reply, plus the line KIT_PARTS_PHONE_RETEST (DECISIONS.md, risk R9)."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from check_package import check, native_files
from audit_final_package_startup import audit_final_startup
import package_obligations

# Parent decision 2026-10-29 (DECISIONS.md, design risk R9): until the first v7.7 NEW game passes a phone scan, every
# delivery reply says this line. Remove this constant (and its use below) after the first v7.7 game passes a phone
# scan with the standard parts installed.
KIT_PARTS_PHONE_RETEST = '标准件待真机复测'


def writer_finalize(receipt_file):
    """policy and parts table from the writer receipt (official entries always carry it since v7.7)."""
    try:
        data = json.loads(Path(receipt_file).read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError):
        return None
    fin = data.get('finalize') if isinstance(data, dict) else None
    if not isinstance(fin, dict):
        return None
    rows = fin.get('table') or []
    table = '\n'.join(['| 标准件 | 结果 | 改动文件 | 警告 |', '|---|---|---|---|'] +
                      ['| %s | %s | %s | %s |' % (r.get('step'), r.get('result'), r.get('changed'), r.get('warnings'))
                       for r in rows])
    return {'policy': fin.get('policy'), 'policy_reason': fin.get('policy_reason'),
            'kit_version': fin.get('kit_version'), 'table': rows, 'table_markdown': table,
            'warnings': fin.get('warnings') or []}


def source_sha256(source):
    """logic_regressions.source_digest for a project folder, or the same digest over a source ZIP (the folder
    holding assets/ inside it)."""
    import zipfile
    from pathlib import PurePosixPath
    from logic_regressions import source_digest
    source = Path(source)
    if source.is_dir():
        return source_digest(source)
    skip = {'node_modules', 'library', 'temp', 'build', '.git'}
    with zipfile.ZipFile(source) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        bases = set()
        for n in names:
            parts = PurePosixPath(n).parts
            if 'assets' in parts[:-1]:
                i = parts.index('assets')
                if not skip & set(parts[:i]) and '__MACOSX' not in parts[:i]:
                    bases.add('/'.join(parts[:i]))
        if not bases:
            raise ValueError('source ZIP has no assets/ folder')
        base = sorted(bases, key=lambda b: (b.count('/') if b else -1, b))[0]
        prefix = base + '/' if base else ''
        rows = []
        for n in names:
            if not n.startswith(prefix + 'assets/'):
                continue
            rel = PurePosixPath(n[len(prefix):])
            if rel.suffix not in {'.js', '.ts', '.json'} or skip & set(rel.parts):
                continue
            rows.append((rel.parts, rel.as_posix(), n))
        digest = hashlib.sha256()
        for _, rel, n in sorted(rows):
            digest.update(rel.encode('utf-8') + b'\0' + hashlib.sha256(z.read(n)).digest())
    return digest.hexdigest()


def prepare(archive, native, app_id, record, project=None, startup_contract=None, loading_recovery_runtime=None, resource_manifest=None, ad_regression=None, logic_report=None, source=None):
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
    result = check(archive, app_id, native, ad_regression)
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
    if result.get('entry') != 'official':
        raise ValueError('unofficial entry (非官方入口): ' + str(result.get('entry_reason')) +
                         ' - write the ZIP with build_checked_zip.py or make_tiktok_zip.py; no delivery record written')
    logic = None
    if logic_report is not None:
        if source is None:
            raise ValueError('--logic-report needs --source (the delivered source folder or ZIP)')
        import json as _json
        logic = _json.loads(Path(logic_report).read_text(encoding='utf-8'))
        checked = logic.get('current_source_sha256') if isinstance(logic, dict) else None
        delivered = source_sha256(source)
        if not checked or checked != delivered:
            raise ValueError('logic_check report current_source_sha256 %s differs from the delivered source %s (%s): '
                             'rerun logic_check on the source you deliver' % (checked, delivered, source))
        logic = {'report': str(Path(logic_report).resolve()), 'source': str(Path(source).resolve()),
                 'current_source_sha256': delivered}
    receipt = {'status': 'delivery_file_verified', 'archive': str(archive),
               'sha256': after, 'bytes': archive.stat().st_size,
               'native': str(native), 'app_id': app_id, 'expected_tree_exact': True,
               'markdown_link': '[' + archive.name + '](<' + str(archive) + '>)',
               'runtime_execution': result['runtime_execution'],
               'final_startup_runtime': startup_runtime,
               'package_obligations': obligations,
               'entry': result['entry'], 'receipt': result.get('receipt'),
               'finalize': writer_finalize(result.get('receipt')),
               'kit_parts_status': KIT_PARTS_PHONE_RETEST,
               'reply_lines': [KIT_PARTS_PHONE_RETEST],
               'logic_source_binding': logic,
               'boundary': 'Local file/link identity only; include markdown_link, reply_lines and the finalize '
                           'table_markdown in the actual reply. No upload performed.'}
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
    parser.add_argument('--ad-regression', type=Path, help='adapter JSON for the rewarded-ad and runtime regressions (default $TIKTOK_AD_REGRESSION_ADAPTER); every package with game.js is refused without it')
    parser.add_argument('--logic-report', type=Path, help='logic_check.py report; its current_source_sha256 must equal the delivered --source')
    parser.add_argument('--source', type=Path, help='delivered source project folder or source ZIP (with --logic-report)')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.zip, args.native, args.expected_app_id, args.record, args.project, args.startup_contract, args.loading_recovery_runtime, args.resource_manifest, args.ad_regression, args.logic_report, args.source), ensure_ascii=False))
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
