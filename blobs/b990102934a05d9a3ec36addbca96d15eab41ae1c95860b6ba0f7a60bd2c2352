#!/usr/bin/env python3
"""Verify the exact stable upload ZIP linked in the final response; never upload it.

v7.5 (D7 items 1, 14, 15): refuses a ZIP without a matching <zip>.receipt.json from make_tiktok_zip.py /
build_checked_zip.py (hand-zipped "verify + ordinary zip" packages are 非官方入口), and with --logic-report refuses
when the delivered source differs from the real project or its existing per-case logic records are no longer valid.
Legacy reports without a ledger retain the exact aggregate source-hash check; no delivery check registers observations.

v7.7: the writer receipt must carry a passed finalize record (verify_native_zip receipt schema 2), so a ZIP that never
went through tiktok_finalize is unofficial and refused. The delivery record repeats the finalize policy and the
Chinese parts table for the reply, plus the line KIT_PARTS_PHONE_RETEST (DECISIONS.md, risk R9)."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from check_package import check, native_files
from audit_final_package_startup import audit_final_startup, StartupRefused
import package_obligations
from verify_delivery_preview import verify_preview
from delivery_continuation import failure, repair_context
from audit_upload_startup import audit_invocation

# Parent decision 2026-10-29 (DECISIONS.md, design risk R9): until the first v7.7 NEW game passes a phone scan, every
# delivery reply says this line. Remove this constant (and its use below) after the first v7.7 game passes a phone
# scan with the standard parts installed.
KIT_PARTS_PHONE_RETEST = '标准件待真机复测'


def writer_board(archive, app_id, project=None, *, files=None):
    """Retain the board of the byte-verified official writer, never a CLI waiver."""
    from verify_native_zip import verify
    verified = verify(archive, expected_app_id=app_id)
    if verified.get('entry') != 'official':
        raise ValueError('delivery requires a byte-matching official writer receipt')
    if files is not None and verified['file_sha256'] != {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}:
        raise ValueError('final ZIP differs from actual Native input paths/bytes')
    receipt = json.loads(Path(verified['receipt']).read_text(encoding='utf-8'))
    board = receipt.get('board')
    if board not in ('localize', 'remake'):
        return None  # Old / unknown receipts keep the strict unknown-board rules.
    if receipt.get('finalize', {}).get('board') != board:
        raise ValueError('writer board differs from its finalize record')
    if project is not None:
        declared = Path(project) / 'docs' / 'board.txt'
        if declared.is_file() and declared.read_text(encoding='utf-8').strip() != board:
            raise ValueError('writer board differs from the project board')
    return board


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


def logic_source_binding(logic_report, source, project=None):
    """Verify delivered source identity and existing observations without running gameplay."""
    from logic_regressions import current_report, source_digest
    report_path, source = Path(logic_report).resolve(), Path(source).resolve()
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not isinstance(report, dict):
        raise ValueError('logic_check report must be an object')
    checked, delivered = report.get('current_source_sha256'), source_sha256(source)
    recorded_project = report.get('project_root')
    root = Path(project).resolve() if project is not None else (source if source.is_dir() else None)
    if root is None and isinstance(recorded_project, str) and Path(recorded_project).is_absolute():
        root = Path(recorded_project).resolve()
    if root is not None:
        if not (root / 'assets').is_dir() or source_digest(root) != delivered:
            raise ValueError('delivered source differs from the current project source; verify the actual delivery source before reusing logic evidence')
    modern = 'project_root' in report or any(isinstance(row, dict) and 'incremental' in row
                                            for field in ('regressions', 'flows')
                                            for row in (report.get(field) if isinstance(report.get(field), list) else []))
    ledger = root / 'docs/checks/incremental/ledger.sqlite3' if root is not None else None
    if modern or (ledger is not None and ledger.is_file()):
        if root is None or not current_report(report, root):
            raise ValueError('logic_check existing per-case records cannot be reused for the current project; '
                             'locate the affected evidence or missing binding; delivery does not register records or rerun gameplay')
        validation = 'existing_case_records'
    else:
        # Old reports had only an aggregate source identity. Preserve that exact
        # compatibility boundary; a mismatched hash must never become a new pass.
        if not checked or checked != delivered:
            raise ValueError('logic_check report current_source_sha256 %s differs from the delivered source %s (%s): '
                             'verify the delivery source and original evidence binding' % (checked, delivered, source))
        validation = 'legacy_exact_source'
    return {'report': str(report_path), 'source': str(source), 'project': str(root) if root is not None else None,
            'current_source_sha256': delivered, 'report_source_sha256': checked,
            'validation': validation, 'browser_executed': False}


def regression_checks(result):
    """Expose per-case execution where recorded; older receipts keep their proven granularity."""
    reuse = result.get('regression_reuse') or {}
    rows = []
    for group, key in (('ads', 'rewarded_ad_regression'), ('runtime', 'runtime_regression')):
        summary = result.get(key) or {}
        if not summary:
            continue
        source = summary.get('reused_from') or result.get('receipt')
        def add(check_id, detail=None, evidence=None):
            detail = detail or {}
            reused = reuse.get('reused') or detail.get('reused') or summary.get('reused_from')
            action = ('not_applicable' if summary.get('status') == 'not_applicable' else
                      'reused' if reused else 'rerun')
            reason = (summary.get('reason') if action == 'not_applicable' else
                      '当前 ZIP 与已验证 writer 记录一致' if reuse.get('reused') else
                      '输入未变，沿用逐项账本' if reused else
                      reuse.get('why') or '本次回归执行通过')
            rows.append({'id': check_id, 'action': action, 'reason': reason,
                         'evidence': evidence or ([source] if source else []),
                         **{k: detail[k] for k in ('key', 'source_key', 'original_at', 'seconds') if k in detail}})
        if summary.get('status') == 'not_applicable':
            add(group)
        elif group == 'ads':
            for case in summary.get('cases') or []:
                name = case if isinstance(case, str) else case.get('case')
                if name:
                    cid = 'ads.' + name
                    add(cid, (summary.get('incremental') or {}).get(cid), summary.get('raw_files'))
        else:
            for suite in summary.get('suites') or []:
                for cid, detail in (suite.get('incremental') or {}).items():
                    add(cid, detail, suite.get('raw_files'))
                if suite.get('suite') and not suite.get('incremental'):
                    add('runtime.' + suite['suite'], {'reused': bool(suite.get('reused_from'))}, suite.get('raw_files'))
        if not any(row['id'] == group or row['id'].startswith(group + '.') for row in rows):
            add(group)
    return rows


@audit_invocation()
def prepare(archive, native, app_id, record, project=None, startup_contract=None, loading_recovery_runtime=None, resource_manifest=None, ad_regression=None, logic_report=None, source=None, preview_url=None, platform_feedback=None):
    checks, state = [], {}
    try:
        return _prepare(archive, native, app_id, record, project, startup_contract, loading_recovery_runtime,
                        resource_manifest, ad_regression, logic_report, source, preview_url, platform_feedback, checks, state)
    except (ValueError, OSError, RuntimeError) as error:
        if 'record' in state:
            path = Path(str(state['record']) + '.blocked.json')
            blocked = {'status': 'delivery_blocked', 'delivery_ready': False, 'archive': state['archive'], 'sha256': state.get('sha256'),
                       **repair_context('delivery'),
                       'checks': checks + [{'id': error.check_id if isinstance(error, StartupRefused) else state['stage'],
                                            'action': 'blocked',
                                            'reason': str(error), 'evidence': state.get('evidence', [])}]}
            try:
                with path.open('x', encoding='utf-8') as stream:
                    json.dump(blocked, stream, ensure_ascii=False, indent=2)
                    stream.write('\n')
            except OSError:
                pass  # Keep the original refusal if the failure record cannot be written.
        raise


def _prepare(archive, native, app_id, record, project, startup_contract, loading_recovery_runtime,
             resource_manifest, ad_regression, logic_report, source, preview_url, platform_feedback, checks, state):
    archive, native, record = (Path(p).resolve() for p in (archive, native, record))
    temporary = Path(tempfile.gettempdir()).resolve()
    if archive.is_relative_to(temporary) or any(x.casefold() in ('temp', 'rwtemp') for x in archive.parts):
        raise ValueError('delivery ZIP must be in a stable directory, not a temporary attachment path')
    if not archive.is_file() or archive.suffix.lower() != '.zip':
        raise ValueError('delivery ZIP is missing or not a ZIP file')
    if record == archive or record.is_relative_to(native):
        raise ValueError('delivery record must be outside Native and distinct from ZIP')
    blocked_record = Path(str(record) + '.blocked.json')
    if record.exists() or record.is_symlink() or blocked_record.exists() or blocked_record.is_symlink():
        raise ValueError('delivery record already exists; choose a new record path')
    # Every delivery (even identical bytes / renamed or imported ZIPs) gets a fresh,
    # independent size receipt BEFORE startup/gameplay checks can fail or reuse CI.
    from upload_size_gate import inspect_final_zip
    size_record = Path(str(record) + '.size.json')
    if size_record.exists() or size_record.is_symlink():
        raise ValueError('size receipt already exists; choose a fresh delivery record path')
    size_check = inspect_final_zip(archive, 'tiktok', platform_feedback)
    size_record.parent.mkdir(parents=True, exist_ok=True)
    with size_record.open('x', encoding='utf-8') as stream:
        json.dump(size_check, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    state.update(record=record, archive=str(archive), sha256=size_check['sha256'],
                 stage=('package.size_crc' if not size_check.get('size_passed') else
                        'package.writer_receipt' if size_check.get('writer_receipt', {}).get('entry') == 'unofficial' else 'package.tiktok_cli'),
                 evidence=[str(size_record)])
    if size_check.get('size_passed') or size_check['passed']:
        checks.append({'id': 'package.size_crc', 'action': 'rerun', 'reason': '逐次核对最终 ZIP 体积、分包和 CRC',
                       'evidence': [str(size_record)], 'run_id': size_check['run_id']})
    if not size_check['passed']:
        phase = ('writer receipt' if size_check.get('writer_receipt', {}).get('entry') == 'unofficial' else
                 'TikTok CLI' if size_check.get('size_passed') else 'size')
        raise ValueError(f'fresh delivery {phase} check failed: ' + '; '.join(size_check['errors']))
    checks.append({'id': 'package.tiktok_cli', 'action': 'rerun', 'reason': '本次对最终 ZIP 执行官方 check/build',
                   'evidence': [str(size_record)], 'run_id': size_check['run_id']})
    # 简化.11.6 (Saul 2026-11-04, 91 SLS11): a delivered source never carries .git / .svn / .idea or credential files
    hygiene = None
    if source is not None:
        state.update(stage='source.hygiene', evidence=[str(source)])
        from source_hygiene import audit as audit_source_hygiene
        hygiene = audit_source_hygiene(source)
        if not hygiene['passed']:
            raise ValueError('delivered source is not clean (source_hygiene.py): ' + '; '.join(hygiene['problems'][:8]) +
                             ' - make the source ZIP with remake-core/scripts/make_source_zip.py; no delivery record written')
        checks.append({'id': 'source.hygiene', 'action': 'rerun', 'reason': '核查本次交付源码', 'evidence': [str(source)]})
    state.update(stage='package.identity', evidence=[str(size_record)])
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    if before != size_check['sha256']:
        raise ValueError('ZIP changed after the fresh size check; retry with a new delivery record')
    # Delivery can verify existing writer evidence only. Read it before even asking for the startup ledger;
    # missing, changed or incomplete evidence never launches a browser from this command.
    files = native_files(native)
    board = writer_board(archive, app_id, project, files=files)
    state.update(stage='package.obligations', evidence=[str(resource_manifest)] if resource_manifest else [])
    obligations = package_obligations.verify(files, native, project, resource_manifest)
    checks.append({'id': 'package.obligations', 'action': 'rejudged', 'reason': '核对最终资源和已知问题证据', 'evidence': state['evidence']})
    state.update(stage='package.regressions', evidence=[str(archive) + '.receipt.json'])
    result = check(archive, app_id, native, ad_regression, board=board, reuse_writer_regressions=True, project=project)
    checks.extend(regression_checks(result))
    state.update(stage='storage.native.contract', evidence=[str(startup_contract)] if startup_contract else [])
    from audit_final_storage import audit_final_storage
    checks.append(audit_final_storage(native, project, startup_contract))
    state.update(stage='startup.native.current_evidence', evidence=[str(p) for p in (startup_contract, loading_recovery_runtime) if p])
    startup_runtime = audit_final_startup(native, project, startup_contract, loading_recovery_runtime, reuse_only=True)
    checks.extend(startup_runtime.get('checks') or [])
    if native_files(native) != files:
        raise ValueError('Native changed during startup verification; no delivery record written')
    state.update(stage='package.identity', evidence=[str(size_record), str(result.get('receipt') or archive)])
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
    checks.append({'id': 'package.identity', 'action': 'rejudged', 'reason': 'ZIP、Native 树和正式 writer 记录一致',
                   'evidence': state['evidence']})
    logic = None
    if logic_report is not None:
        state.update(stage='source.logic', evidence=[str(logic_report)])
        if source is None:
            raise ValueError('--logic-report needs --source (the delivered source folder or ZIP)')
        logic = logic_source_binding(logic_report, source, project)
        checks.append({'id': 'source.logic', 'action': 'rejudged', 'reason': '核对已有逐项玩法证据和本次源码身份',
                       'evidence': [str(logic_report)]})
    receipt = {'status': 'delivery_file_verified', 'delivery_ready': False, 'archive': str(archive),
               'sha256': after, 'bytes': archive.stat().st_size,
               'native': str(native), 'app_id': app_id, 'expected_tree_exact': True,
               'markdown_link': '[' + archive.name + '](<' + str(archive) + '>)',
               'runtime_execution': result['runtime_execution'],
               'regression_reuse': result.get('regression_reuse'),
               'regression_scope': result.get('regression_scope'),
               'fresh_size_check': {'report': str(size_record), 'run_id': size_check['run_id'],
                                    'sha256': size_check['sha256'], 'main_bytes': size_check['main_bytes'],
                                    'total_bytes': size_check['total_bytes'], 'reused': False},
               'tiktok_cli': {'version': size_check['tiktok_cli']['version'], 'report': str(size_record), 'passed': True},
               'final_startup_runtime': startup_runtime,
               'package_obligations': obligations,
               'source_hygiene': ({'source': hygiene['source'], 'passed': True} if hygiene else None),
               'entry': result['entry'], 'receipt': result.get('receipt'),
               'receipt_artifacts': [
                   {'kind': 'writer_receipt', 'path': str(result.get('receipt')),
                    'markdown_link': '[' + Path(result['receipt']).name + '](<' + str(result['receipt']) + '>)'},
                   {'kind': 'delivery_record', 'path': str(record),
                    'markdown_link': '[' + record.name + '](<' + str(record) + '>)'}],
               'team_handoff': {'next': 'game_handoff.py export with this record and the actual source ZIP',
                                'evidence_exported': False, 'receiver_current_approval': False},
               'finalize': writer_finalize(result.get('receipt')),
               'kit_parts_status': KIT_PARTS_PHONE_RETEST,
               'reply_lines': [KIT_PARTS_PHONE_RETEST],
               'logic_source_binding': logic,
               'check_schema': 'delivery-checks.v1', 'checks': checks,
               'boundary': 'Local file/link identity only; include markdown_link, reply_lines and the finalize '
                           'table_markdown and preview.markdown_link in the actual reply. No upload performed.'}
    state.update(stage='preview.same_build', evidence=[str(startup_contract)] if startup_contract else [])
    contract_bytes = Path(startup_contract).read_bytes() if startup_contract else b''
    if not preview_url:
        raise ValueError('缺同版试玩链接：只有 ZIP，交付未完成。')
    if hashlib.sha256(contract_bytes).hexdigest() != startup_runtime.get('startup_contract_sha256'):
        raise ValueError('同版启动合同缺失或在校验后变化，无法核对试玩版本。')
    # A scoped witness keeps the original contract/observation immutable while
    # binding the exact current Web served to the user.
    web_sha = (startup_runtime.get('current_binding') or json.loads(contract_bytes)['binding'])['web_tree_sha256']
    record.parent.mkdir(parents=True, exist_ok=True)
    with package_obligations.publication_guard(files, native, project, resource_manifest, obligations):
        receipt['preview'] = verify_preview(preview_url, web_sha)
        checks.append({'id': 'preview.same_build', 'action': 'rerun', 'reason': '实际访问试玩并核对本版 Web 快照',
                       'evidence': [preview_url, str(startup_contract)], 'web_tree_sha256': web_sha})
        state.update(stage='delivery.publication', evidence=[str(size_record)])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != after:
            raise ValueError('ZIP changed while checking the preview; no delivery record written')
        receipt['delivery_ready'] = True
        with record.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    # Learning reads already existing project evidence after publication. It
    # neither mutates the signed record/ZIP nor participates in delivery gates.
    try:
        from production_hooks import collect_after_delivery
        collect_after_delivery(project, record_paths=[record, startup_contract, resource_manifest,
                               ad_regression, logic_report], final_zip_sha256=after)
    except Exception:
        pass  # Even an unavailable hook cannot invalidate a verified delivery.
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
    parser.add_argument('--logic-report', type=Path, help='logic_check.py report; reuse existing per-case project records only after --source identity matches the current project')
    parser.add_argument('--source', type=Path, help='delivered source project folder or source ZIP: checked by source_hygiene.py (no .git/.svn/.idea, no credential files); also needed with --logic-report')
    parser.add_argument('--preview-url', help='live matching phone preview URL; required for delivery')
    parser.add_argument('--platform-feedback', type=Path, help='project-local record of a known platform rejection')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.zip, args.native, args.expected_app_id, args.record, args.project, args.startup_contract, args.loading_recovery_runtime, args.resource_manifest, args.ad_regression, args.logic_report, args.source, args.preview_url, args.platform_feedback), ensure_ascii=False))
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps(failure(error, stage='delivery'), ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
