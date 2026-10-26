#!/usr/bin/env python3
"""Isolated contract adversaries. No real AI app, GUI, game or dispatch is exercised."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    tool = Path(__file__).with_name('check_dispatch_contract.py')
    spec = importlib.util.spec_from_file_location('dispatch_contract', tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    now = datetime.now(timezone.utc)
    checks = []
    with tempfile.TemporaryDirectory(prefix='dispatch-contract-adversaries-') as temporary:
        root = Path(temporary)
        project = root / 'project with spaces'
        evidence, source = project / 'evidence', project / 'src'
        evidence.mkdir(parents=True)
        source.mkdir()
        app_path = root / 'fixture.app'
        app_path.mkdir()
        manifest, design = project / 'input.json', project / 'main-design.md'
        manifest.write_text('{"fixture": true}')
        design.write_text('Main fixture design: UI only. Existing core and assertions are read only.')
        ref = lambda p: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        task = {'run_id': 'fixture-run', 'task_id': 'UI-1', 'task_type': 'B03', 'role': 'ui',
                'decision_owner': 'main', 'acceptance_owner': 'main',
                'critical_logic': False, 'subdelegate': False, 'change_tests': False,
                'steps': ['Bind the supplied fixture sprite to the specified UI node.'],
                'expected_outputs': ['Only src/ui.py changes; raw result is preserved.'],
                'project_root': str(project), 'write_paths': [str(source / 'ui.py')],
                'input_ref': ref(manifest), 'spec_ref': ref(design), 'resource_locks': []}
        app = {'id': 'qoder_cn', 'app_path': str(app_path), 'bundle_id': 'fixture.qoder',
               'conversation': 'ui-conversation', 'roles': ['ui'], 'roles_approved': True,
               'capabilities': ['files', 'edit', 'terminal'],
               'ui_readable': True, 'project_verified': True, 'tools_verified': True,
               'model_verified': True, 'quota_ok': True, 'capacity_group': 'qoder',
               'configured_limit': 3, 'global_occupied': 0,
               'observed_at': now.isoformat(), 'observation_ref': 'synthetic-fixture-only'}
        ledger = {'activation': {'run_id': 'fixture-run', 'mode': 'desktop_multi', 'user_confirmed': True, 'authorization_ref': 'synthetic-human-selection'}, 'allowed_roots': [str(project)], 'protected_paths': [str(source / 'core.py')],
                  'evidence_roots': [str(evidence)], 'tasks': [], 'apps': [app]}

        def case(name, expected, change=None, base_task=None, base_ledger=None):
            t, l = deepcopy(base_task or task), deepcopy(base_ledger or ledger)
            if change:
                change(t, l)
            result = module.inspect(t, l, now=now)
            passed = result['status'] == expected
            checks.append({'name': name, 'passed': passed, 'expected': expected,
                           'actual': result['status'], 'eligible_apps': result['eligible_apps']})
            if not passed:
                checks[-1]['result'] = result

        case('bounded-UI-with-pinned-spec-and-isolated-path', 'ready')
        case('missing-current-human-selection', 'activation_required', lambda t,l:l.pop('activation'))
        case('unconfirmed-mode-cannot-dispatch', 'activation_required', lambda t,l:l['activation'].update(user_confirmed=False))
        case('old-empty-run-cannot-dispatch', 'activation_required', lambda t,l:l['activation'].update(run_id=''))
        case('missing-human-evidence', 'activation_required', lambda t,l:l['activation'].update(authorization_ref=''))
        case('single-agent-selection-no-app-dispatch', 'single_agent', lambda t,l:l['activation'].update(mode='single'))
        case('unknown-mode-requires-selection', 'activation_required', lambda t,l:l['activation'].update(mode='auto'))
        case('different-run-cannot-reuse-old-selection', 'activation_required', lambda t,l:t.update(run_id='next-run'))
        case('missing-task-run-cannot-reuse-selection', 'activation_required', lambda t,l:t.pop('run_id'))

        for i in range(1, 9):
            case(f'C{i:02}-retained-by-main', 'main_only', lambda t, l, i=i: t.update(task_type=f'C{i:02}'))
        mutations = [
            ('critical-behavior-cannot-be-relabelled-B', 'main_only', lambda t, l: t.update(critical_logic=True)),
            ('missing-approved-spec', 'needs_main_decision', lambda t, l: t.pop('spec_ref')),
            ('changed-input', 'needs_main_decision', lambda t, l: t['input_ref'].update(sha256='0' * 64)),
            ('changed-main-spec', 'needs_main_decision', lambda t, l: t['spec_ref'].update(sha256='0' * 64)),
            ('vague-task-without-steps', 'needs_main_decision', lambda t, l: t.update(steps=[])),
            ('main-only-acceptance-right', 'needs_main_decision', lambda t, l: t.update(acceptance_owner='worker')),
            ('no-worker-subdelegation', 'needs_main_decision', lambda t, l: t.update(subdelegate=True)),
            ('no-incidental-test-edit', 'needs_main_decision', lambda t, l: t.update(change_tests=True)),
            ('numeric-flag-is-not-explicit-bool', 'needs_main_decision', lambda t, l: t.update(change_tests=0)),
            ('mixed-UI-critical-file-protected', 'needs_main_decision', lambda t, l: t.update(write_paths=[str(source / 'core.py')])),
            ('worker-cannot-rewrite-main-spec', 'needs_main_decision', lambda t, l: t.update(write_paths=[str(design)])),
            ('whole-project-write-rejected', 'needs_main_decision', lambda t, l: t.update(write_paths=[str(project)])),
            ('outside-workspace-write-rejected', 'needs_main_decision', lambda t, l: t.update(write_paths=[str(root / 'other-project.py')])),
            ('unknown-global-occupancy-not-zero', 'channel_unavailable', lambda t, l: l['apps'][0].update(global_occupied=None)),
            ('full-shared-Qoder-capacity', 'channel_unavailable', lambda t, l: l['apps'][0].update(global_occupied=3)),
            ('cannot-expand-user-limit', 'channel_unavailable', lambda t, l: l['apps'][0].update(configured_limit=9)),
            ('Qoder-CN-cannot-create-extra-pool', 'channel_unavailable', lambda t, l: l['apps'][0].update(capacity_group='qoder_cn')),
            ('non-listed-app-cannot-borrow-Grok-capacity', 'channel_unavailable', lambda t, l: l['apps'][0].update(id='outside_app', capacity_group='grok', configured_limit=6)),
            ('AStudio-cannot-borrow-Grok-capacity', 'channel_unavailable', lambda t, l: l['apps'][0].update(id='astudio', capacity_group='grok', configured_limit=6)),
            ('stale-UI-observation', 'channel_unavailable', lambda t, l: l['apps'][0].update(observed_at=(now - timedelta(hours=1)).isoformat())),
            ('invalid-observation-fails-closed', 'channel_unavailable', lambda t, l: l['apps'][0].update(observed_at=None)),
            ('installed-app-without-current-tools', 'channel_unavailable', lambda t, l: l['apps'][0].update(tools_verified=False)),
            ('unknown-model-not-ready', 'channel_unavailable', lambda t, l: l['apps'][0].update(model_verified=False)),
            ('Grok-cannot-receive-UI-code-in-seven-app-workflow', 'channel_unavailable', lambda t, l: l['apps'][0].update(id='grok', capacity_group='grok', configured_limit=5)),
            ('stopping-writer-still-owns-file', 'needs_main_decision', lambda t, l: l['tasks'].append({'task_id': 'old', 'state': 'stopping', 'write_paths': t['write_paths']})),
            ('recorded-busy-tasks-cannot-be-hidden', 'channel_unavailable', lambda t, l: l['tasks'].append({'task_id': 'other', 'app': 'qoder_cn', 'conversation': 'other-conv', 'state': 'running', 'write_paths': []})),
        ]
        for row in mutations:
            case(*row)
        qa_task = deepcopy(task)
        qa_task.update(task_id='QA-1', task_type='B05', role='qa', write_paths=[str(evidence / 'qa')],
                       independent_of=['producer'], resource_locks=['browser:fixture-space'])
        qa_ledger = deepcopy(ledger)
        qa_ledger['tasks'] = [{'task_id': 'producer', 'app': 'qoder_cn', 'conversation': 'producer-conv',
                               'state': 'accepted', 'write_paths': []}]
        qa_ledger['apps'][0].update(id='workbuddy_ai', capacity_group='workbuddy_ai',
                                     conversation='independent-qa', roles=['qa'],
                                     capabilities=['files', 'browser', 'trusted_touch'])
        case('independent-GUI-with-real-tool-declarations', 'ready', base_task=qa_task, base_ledger=qa_ledger)
        case('QA-cannot-write-product', 'needs_main_decision', lambda t, l: t.update(write_paths=[str(source / 'ui.py')]), qa_task, qa_ledger)
        case('QA-cannot-use-producer-conversation', 'channel_unavailable', lambda t, l: (l['tasks'][0].update(app='workbuddy_ai'), l['apps'][0].update(conversation='producer-conv')), qa_task, qa_ledger)
        case('equal-conversation-ID-in-different-app-is-distinct', 'ready', lambda t, l: l['apps'][0].update(conversation='producer-conv'), qa_task, qa_ledger)
        case('GUI-needs-trusted-touch-tool', 'channel_unavailable', lambda t, l: l['apps'][0].update(capabilities=['files', 'browser']), qa_task, qa_ledger)
        case('browser-space-is-exclusive', 'needs_main_decision', lambda t, l: l['tasks'].append({'task_id': 'browser-owner', 'state': 'uncertain', 'resource_locks': t['resource_locks']}), qa_task, qa_ledger)
        case('review-producer-must-be-known', 'needs_main_decision', lambda t, l: t.update(independent_of=['missing']), qa_task, qa_ledger)
        case('AStudio-can-fill-approved-role', 'ready', lambda t, l: l['apps'][0].update(id='astudio', capacity_group='astudio', configured_limit=1))
        literal_task = deepcopy(task)
        literal_task.update(task_id='OCR-1', task_type='clear_text_ocr', role='literal',
                            write_paths=[str(evidence / 'ocr')])
        literal_ledger = deepcopy(ledger)
        literal_ledger['apps'][0].update(id='grok', capacity_group='grok', roles=['literal'],
                                         configured_limit=5, capabilities=['files', 'vision'])
        case('Grok-clear-print-OCR-only', 'ready', base_task=literal_task, base_ledger=literal_ledger)
        writer_task, writer_ledger = deepcopy(task), deepcopy(ledger)
        writer_task.update(task_id='ZIP-WRITER', task_type='A17', role='package_writer',
                           write_paths=[str(evidence / 'package-output')])
        writer_ledger['apps'][0].update(id='opencode', capacity_group='opencode',
                                         configured_limit=1, roles=['package_writer'])
        case('frozen-package-writer-can-produce-own-output', 'ready', base_task=writer_task, base_ledger=writer_ledger)
        case('package-writer-needs-frozen-main-spec', 'needs_main_decision', lambda t, l: t.pop('spec_ref'), writer_task, writer_ledger)
        verifier_task, verifier_ledger = deepcopy(writer_task), deepcopy(writer_ledger)
        verifier_task.update(task_id='ZIP-VERIFY', role='package', independent_of=['ZIP-WRITER'],
                             write_paths=[str(evidence / 'package-readback')])
        verifier_ledger['tasks'] = [{'task_id': 'ZIP-WRITER', 'app': 'opencode', 'conversation': 'writer-conv', 'state': 'accepted'}]
        verifier_ledger['apps'][0].update(id='grok', capacity_group='grok', configured_limit=5,
                                           roles=['package'], conversation='independent-package')
        case('independent-package-readback-has-separate-conversation', 'ready', base_task=verifier_task, base_ledger=verifier_ledger)
        case('writer-cannot-verify-same-conversation', 'channel_unavailable', lambda t, l: (l['tasks'][0].update(app='grok'), l['apps'][0].update(conversation='writer-conv')), verifier_task, verifier_ledger)
        capture_task = deepcopy(task)
        capture_task.update(task_id='CAPTURE', task_type='A13', role='build', capture_mode='offline_assets',
                            write_paths=[str(evidence / 'capture')])
        capture_ledger = deepcopy(ledger)
        capture_ledger['apps'][0].update(id='qoder', roles=['build'])
        case('offline-contact-sheet-needs-no-browser', 'ready', base_task=capture_task, base_ledger=capture_ledger)
        case('runtime-capture-needs-browser-lock', 'needs_main_decision', lambda t, l: t.update(capture_mode='runtime_gui'), capture_task, capture_ledger)
        case('runtime-capture-needs-browser-tool', 'channel_unavailable', lambda t, l: t.update(capture_mode='runtime_gui', resource_locks=['browser:fixture']), capture_task, capture_ledger)
        case('capture-mode-cannot-be-omitted', 'needs_main_decision', lambda t, l: t.pop('capture_mode'), capture_task, capture_ledger)
        case('preview-server-needs-service-lock', 'needs_main_decision', lambda t, l: t.update(task_type='A12'), capture_task, capture_ledger)
        case('unrelated-lock-does-not-authorize-Creator', 'needs_main_decision', lambda t, l: t.update(task_type='A09', resource_locks=['browser:fixture']), capture_task, capture_ledger)
        for candidate, role, kind in [('workbuddy', 'intake', 'A01'), ('astudio', 'resources', 'B01'),
                                      ('qoder_cn', 'ui', 'B03'), ('qoder', 'patch', 'B04'),
                                      ('opencode', 'build', 'A10')]:
            t, l = deepcopy(task), deepcopy(ledger)
            t.update(task_type=kind, role=role)
            group = 'qoder' if candidate in {'qoder', 'qoder_cn'} else candidate
            l['apps'][0].update(id=candidate, roles=[role], capacity_group=group,
                                  configured_limit=module.USER_LIMITS[group])
            case('seven-pool-role-' + candidate, 'ready', base_task=t, base_ledger=l)
        for candidate in ['outside_alpha', 'outside_beta', 'outside_gamma']:
            case('non-listed-app-rejected-' + candidate, 'channel_unavailable',
                 lambda t, l, candidate=candidate: l['apps'][0].update(
                     id=candidate, capacity_group=candidate, configured_limit=1))
        cli_fixture = root / 'fixture-grok-executable'
        cli_fixture.write_text('Synthetic path; never executed.')
        cli_ledger = deepcopy(verifier_ledger)
        cli_ledger['apps'][0].update(transport='grok_cli', cli_ready=True,
                                     ui_readable=False, app_path=str(cli_fixture))
        case('Grok-CLI-package-does-not-require-desktop', 'ready', base_task=verifier_task, base_ledger=cli_ledger)
        case('Grok-CLI-requires-verified-availability', 'channel_unavailable',
             lambda t, l: l['apps'][0].update(cli_ready=False), verifier_task, cli_ledger)
        case('desktop-app-cannot-borrow-Grok-CLI-transport', 'channel_unavailable',
             lambda t, l: l['apps'][0].update(id='opencode', capacity_group='opencode', configured_limit=1),
             verifier_task, cli_ledger)
        task_file, ledger_file, output = root / 'task.json', root / 'ledger.json', root / 'cli.json'
        for label, kind, expected_code, expected_status in [('CLI-positive', 'B03', 0, 'ready'),
                                                          ('CLI-main-only', 'C06', 2, 'main_only')]:
            current = deepcopy(task)
            current['task_type'] = kind
            task_file.write_text(json.dumps(current))
            ledger_file.write_text(json.dumps(ledger))
            run = subprocess.run([sys.executable, str(tool), '--task', str(task_file),
                                  '--ledger', str(ledger_file), '--report', str(output)], capture_output=True, text=True)
            data = json.loads(output.read_text())
            checks.append({'name': label, 'passed': run.returncode == expected_code and data['status'] == expected_status,
                           'exit_code': run.returncode, 'actual': data['status']})
    result = {'status': 'pass' if all(c['passed'] for c in checks) else 'fail',
              'checks': len(checks), 'failed': sum(not c['passed'] for c in checks),
              'tool_sha256': hashlib.sha256(tool.read_bytes()).hexdigest(),
              'boundary': 'Synthetic contract fixtures and actual checker CLI only; no app dispatch or game acceptance.',
              'results': checks}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'failed', 'boundary')}, ensure_ascii=False))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
