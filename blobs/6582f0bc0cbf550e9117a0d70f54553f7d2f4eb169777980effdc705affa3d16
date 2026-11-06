"""Read-only merge of an unchanged passed art baseline and approved local UI evidence.

This is not a new full ART-06 verdict. Unknown projects keep the normal receipt gate.
The explicit manifest pins the prior source, exact changed source files, user approval,
current Native, registered UI executions (including a bad control), and current values.
"""
import hashlib
import json
from pathlib import Path

MANIFEST = Path('docs/art/approved-local-ui-scope.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checked(ref):
    p = Path(ref['path']).resolve()
    if not p.is_file() or sha(p) != ref['sha256']:
        raise ValueError('approved UI evidence missing or changed: ' + str(p))
    return p


def assets(root):
    root = Path(root).resolve()
    result = {}
    for p in sorted((root/'assets').rglob('*')):
        if p.is_file():
            if not p.resolve().is_relative_to(root/'assets'):
                raise ValueError('source asset symlink outside project')
            result[p.relative_to(root).as_posix()] = sha(p)
    return result


def validate(project, receipt, manifest=None):
    """Return scoped provenance or raise; never writes a receipt or changes a verdict."""
    import art_receipt as A
    import audit_value_presentation as V
    import audit_ui_contract as U
    import project_qa

    project = Path(project).resolve()
    location = Path(manifest).resolve() if manifest else project/MANIFEST
    doc = read(location)
    if doc.get('schema') != 'approved_local_ui_scope.v1' or doc.get('project') != str(project):
        raise ValueError('approved local UI scope project/schema mismatch')
    approval = doc.get('approval', {})
    if approval.get('decided_by') != 'user' or not approval.get('date') or len(approval.get('quote', '').strip()) < 8:
        raise ValueError('explicit dated user approval required')
    if approval['quote'] not in checked(approval['record']).read_text(encoding='utf-8'):
        raise ValueError('approved quote absent from pinned decision')
    baseline = read(checked(doc['baseline_receipt']))
    if baseline != receipt or baseline.get('status') != 'pass' or baseline.get('passed') is not True:
        raise ValueError('unchanged actual passed baseline receipt required')
    report = read(checked({'path':baseline['art_check']['report'], 'sha256':baseline['art_check']['report_sha256']}))
    if report.get('passed') is not True or report.get('failed') != 0:
        raise ValueError('baseline full art report did not pass')
    if baseline.get('images') != A.image_fingerprints(project) or baseline.get('display') != A.display_fingerprints(project):
        raise ValueError('approved merge cannot cover changed images or serialized display')
    old = Path(doc['baseline_source']).resolve()
    if old == project or not (old/'assets').is_dir():
        raise ValueError('distinct actual baseline source required')
    prior = baseline.get('value_presentation', {})
    if prior.get('passed') is not True or prior.get('mode') != 'runtime' or V.source_fingerprint(old) != prior.get('source_sha256'):
        raise ValueError('baseline source does not match accepted value evidence')
    before, after = assets(old), assets(project)
    actual = {p:{'before':before.get(p), 'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)}
    declared = doc.get('changed_sources')
    if not actual or not isinstance(declared, dict) or actual != declared:
        raise ValueError('source changes differ from approved exact scope')
    if any(not p.startswith('assets/') or Path(p).suffix.lower() not in {'.ts','.js','.meta'} for p in actual):
        raise ValueError('local script merge cannot authorize artwork/font/serialized changes')
    if V.source_fingerprint(project) != doc.get('source_sha256'):
        raise ValueError('current value source fingerprint changed')
    native = Path(doc['native']).resolve()
    if not native.is_relative_to(project) or U.tree_digest(native) != doc.get('native_tree_sha256'):
        raise ValueError('current Native changed')
    sizes, calibrated, expected_captures = set(), False, {}
    ui = doc.get('ui_reports', [])
    if len(ui) < 2:
        raise ValueError('two mobile UI executions required')
    for ref in ui:
        result = read(checked(ref))
        if result.get('schema') != 'ui_contract_check.v1' or result.get('native_tree_sha256') != doc['native_tree_sha256']:
            raise ValueError('local UI report belongs to another Native')
        policy = project_qa.lookup(project, 'ui_runners', result['registered_runner'])
        for p, digest in {policy['path']:policy['sha256'], **policy['dependencies'], policy['contract']:policy['contract_sha256']}.items():
            checked({'path':p, 'sha256':digest})
        if result.get('contract_sha256') != policy['contract_sha256'] or result.get('runner_sha256') != policy['sha256']:
            raise ValueError('UI report differs from reviewed collector/contract')
        contract = read(policy['contract'])
        finals = [r for r in result['executions'] if r.get('variant') == 'final']
        if len(finals) != 1 or finals[0].get('passed') is not True or finals[0].get('errors') != []:
            raise ValueError('actual final UI execution failed')
        for run in result['executions']:
            raw = read(checked({'path':run['runtime_path'], 'sha256':run['runtime_sha256']}))
            if raw.get('execution', {}).get('runner') != {'path':policy['path'],'sha256':policy['sha256']}:
                raise ValueError('actual UI runner identity changed')
            errors = U.validate(raw, contract, doc['native_tree_sha256'], run['variant'], project)
            if run['variant'] == 'final':
                if errors:
                    raise ValueError('actual final UI evidence no longer validates')
                vp = raw['execution']['viewport']; sizes.add((vp['width'], vp['height']))
                for state in raw['execution']['states']:
                    shot = checked(state['screenshot'])
                    dump_path = shot.parent/('ui-dump-'+state['id']+'.json')
                    expected_captures[str(dump_path.resolve())] = state['screenshot']
            else:
                required = contract.get('calibration', {}).get(run['variant'], [])
                if not required or not U.detected_expected(errors, required):
                    raise ValueError('bad UI calibration no longer detects its defect')
        if result.get('mode') == 'calibration':
            if result.get('calibration_passed') is not True or len(result['executions']) < 2:
                raise ValueError('UI bad control missing')
            calibrated = True
    if len(sizes) < 2 or any(w<=0 or h<=w for w,h in sizes) or not calibrated:
        raise ValueError('both portrait sizes and a calibrated bad control required')
    refs = doc.get('current_value_captures', [])
    if len(refs) < 2:
        raise ValueError('current homepage value captures required')
    if {str(Path(r['path']).resolve()) for r in refs} != set(expected_captures) or len(refs) != len(expected_captures):
        raise ValueError('values must use the exact current registered UI same-capture dumps')
    folders = set()
    for ref in refs:
        p = checked(ref); dump = read(p); shot = checked(ref['screenshot'])
        if ref['screenshot'] != expected_captures[str(p)]:
            raise ValueError('value screenshot differs from actual current UI execution')
        actual_shot = Path(dump.get('screenshot', '')); actual_shot = actual_shot if actual_shot.is_absolute() else p.parent/actual_shot
        if dump.get('tool') != 'ui_dump' or dump.get('errors') or dump.get('truncated') or actual_shot.resolve() != shot:
            raise ValueError('current value capture/screenshot mismatch')
        if not p.is_relative_to(project) or not shot.is_relative_to(project):
            raise ValueError('current values outside project')
        folders.add(p.parent)
    value = read(checked(doc['value_report']))
    current = V.audit(project, sorted(folders))
    keys = ('tool','schema','revision','mode','passed','source_sha256','pages','findings')
    if any(value.get(k) != current.get(k) for k in keys) or value.get('passed') is not True or value.get('mode') != 'runtime':
        raise ValueError('current runtime value audit failed or changed')
    return {'state':'approved_local_ui_scope','manifest':str(location),'manifest_sha256':sha(location),
            'baseline_art_report':baseline['art_check']['report'], 'native_tree_sha256':doc['native_tree_sha256'],
            'changed_sources':sorted(actual), 'ui_viewports':sorted(sizes), 'value_pages':value['pages'],
            'boundary':'Previously passed unchanged artwork plus user-approved affected UI and current runtime values; not a new full ART-06 verdict.'}
