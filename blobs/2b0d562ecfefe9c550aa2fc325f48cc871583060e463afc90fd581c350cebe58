"""Check local player-chain observations and executable assertions, never real IAA."""
from pathlib import Path
import package_issue_gate as issues

REQUIRED_CASES = {'completed','cancelled','failed','unsupported','timeout_retry',
                  'duplicate','write_retry','reopen','consumer','capability_compatibility'}


def verify(project, native_hash, report_ref):
    import audit_ad_storage_contract as storage
    path = storage._ref(project, report_ref, 'local ad retest')
    report = storage._object(path, 'local ad retest')
    if report.get('schema') != 'native_ad_local_retest.v1' or report.get('native_tree_sha256') != native_hash:
        raise ValueError('local ad retest schema or Native identity mismatch')
    cases = report.get('cases')
    if not isinstance(cases, dict) or not REQUIRED_CASES.issubset(cases):
        raise ValueError('local ad retest lacks required player-chain cases')
    checked = {}

    def assertions(rows):
        if not isinstance(rows, list) or not rows:
            raise ValueError('local ad retest requires nonempty business assertions')
        for row in rows:
            if (not isinstance(row, dict) or row.get('op') not in ('eq','ne','gt','ge','lt','le')
                    or 'value' not in row or not isinstance(row.get('path'), list) or not row['path']
                    or any(type(k) not in (str, int) for k in row['path'])):
                raise ValueError('invalid local ad business assertion')

    def read_raw(ref, expected):
        raw = storage._object(storage._ref(project, ref, 'local ad raw'), 'local ad raw')
        if raw.get('native_tree_sha256') != expected or raw.get('input_transport') not in ('playwright_cdp_touch', 'ego_page_cdp_touch'):
            raise ValueError('local ad raw Native/input identity mismatch')
        storage._ref(project, raw.get('runner'), 'local ad runner')
        deps = raw.get('harness_dependencies')
        if not isinstance(deps, list) or not deps:
            raise ValueError('local ad raw harness dependencies missing')
        for dep in deps:
            storage._ref(project, dep, 'local ad harness')
        if raw.get('schema') == 'native_storage_shape_case.v2':
            if raw.get('errors') != [] or raw.get('observed', {}).get('trusted_touch_count', 0) < 2:
                raise ValueError('local ad raw has harness errors or no trusted input')
        elif raw.get('schema') == 'player_ad_flow.v1':
            records = raw.get('records')
            if not isinstance(records, list) or not records:
                raise ValueError('local ad flow has no records')
            for record in records:
                state = record.get('state', {})
                if not isinstance(state.get('errors'), list) or any(e.startswith(('UNCAUGHT','UNHANDLED','HOST_UNCAUGHT')) for e in state['errors']):
                    raise ValueError('local ad flow has harness errors')
            if not any(e.get('kind') == 'sdk_touch' and e.get('isTrusted') is True for e in records[-1]['state'].get('events', [])):
                raise ValueError('local ad flow has no trusted input')
        else:
            raise ValueError('unsupported local ad raw schema')
        return raw

    for name, case in cases.items():
        if not isinstance(case, dict):
            raise ValueError('invalid local ad case')
        assertions(case.get('assertions'))
        raw = read_raw(case.get('raw'), native_hash)
        if issues.assertions_pass(raw, case['assertions']) is not True:
            raise ValueError('local ad postconditions failed: '+name)
        checked[name] = case
    controls = report.get('controls')
    if not isinstance(controls, list) or not controls:
        raise ValueError('local ad retest needs reproduced historical/controlled failures')
    for control in controls:
        if not isinstance(control, dict) or control.get('case') not in cases:
            raise ValueError('local ad control must reference a current case')
        root = control.get('native_root')
        if not isinstance(root, str) or not Path(root).is_dir():
            raise ValueError('local ad control Native missing')
        old_hash = storage.tree_sha(root)
        if old_hash == native_hash:
            raise ValueError('local ad negative must use a distinct defect Native')
        negative = read_raw(control.get('raw'), old_hash)
        if issues.assertions_pass(negative, cases[control['case']]['assertions']) is not False:
            raise ValueError('local ad negative did not reproduce business failure')
    return {'passed': True, 'report': report_ref, 'cases': checked, 'controls': controls,
            'coverage': 'local_player_ad_chain', 'physical_iaa_claimed': False}
