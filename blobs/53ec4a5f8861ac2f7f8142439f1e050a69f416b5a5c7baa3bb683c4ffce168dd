#!/usr/bin/env python3
"""Read-only shared STORAGE-01 proof gate for every writer and final delivery.

This never starts the runner/browser. The runtime auditor approves once; all
consumers recheck exact tool, dependencies, report and final Native identity.
"""
from pathlib import Path
from check_known_issues import auto_reports, load, sha, tree_sha, snapshot


def audit_final_storage(native, project, startup_contract=None, *, review=None):
    native = Path(native).resolve()
    if project is None:
        raise ValueError('storage.native.contract: actual source project required')
    project = Path(project).resolve()
    path = Path(review or startup_contract or '').resolve()
    if not path.is_file():
        raise ValueError('storage.native.contract: review or startup contract required')
    doc = load(path)
    if not isinstance(doc, dict) or not isinstance(doc.get('binding'), dict):
        raise ValueError('storage.native.contract: current binding required')
    binding = doc['binding']
    # The envelope can retain an original binding. Each actual report must either
    # match exact current bytes or carry a verified immutable dependency scope.
    current_binding = dict(binding, native_tree_sha256=tree_sha(native), source_sha256=snapshot(project)[2])
    if review:
        checks = doc.get('checks', {})
        row = checks.get('STORAGE-01', {}) if isinstance(checks, dict) else {}
    else:
        ref = doc.get('native_storage_report')
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            raise ValueError('storage.native.contract: startup contract needs native_storage_report path and SHA-256')
        row = {'auto_reports': [ref]}
    refs = row.get('auto_reports', []) if isinstance(row, dict) else []
    # The report must name this very directory, not another same-byte archive.
    matched = []
    for ref in refs if isinstance(refs, list) else []:
        try:
            report_path = Path(ref['path'])
            if not report_path.is_absolute(): report_path = path.parent / report_path
            report = load(report_path)
            if (isinstance(report, dict) and sha(report_path.read_bytes()) == ref.get('sha256') and
                    report.get('tool') == 'audit_native_storage_contract'):
                matched.append(ref)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    from storage_scoped_reuse import validate_report
    errors = []
    accepted = []
    for ref in matched:
        report_path = Path(ref['path'])
        if not report_path.is_absolute(): report_path = path.parent / report_path
        report = load(report_path)
        if binding not in (report.get('binding'), current_binding):
            errors.append('binding stale: envelope does not match the original or actual current artifacts')
            continue
        result = validate_report(report, native, current_binding, project=project)
        if not result:
            accepted.append(ref)
        else:
            errors.extend(result)
    if not accepted:
        raise ValueError('storage.native.contract: ' + '; '.join(errors or ['missing current native_storage_report / STORAGE-01 approval']))
    return {'id': 'storage.native.contract', 'action': 'rejudged',
            'reason': 'read-only approval receipt and final source/Native identity verification',
            'evidence': [str(path)] + [str(ref['path']) for ref in accepted],
            'current_binding': current_binding, 'original_binding': binding,
            'game_executed': False}
