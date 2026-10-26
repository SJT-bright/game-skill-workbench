#!/usr/bin/env python3
"""Test checklist rejection/acceptance using isolated synthetic artifacts, never a game pass."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import subprocess
import sys
import check_known_issues as gate
import logic_regressions as logic_reg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    from unittest.mock import patch
    import audit_startup_contract
    results = [{'name':'production startup contract refuses a source-only stamped pass',
                'passed':bool(audit_startup_contract.validate_runtime_report({'passed':True},{}))}]
    # Explicit unit boundary: this matrix has no real Cocos/browser renderer.
    renderer_boundary=patch.object(audit_startup_contract,'validate_runtime_report',
        side_effect=lambda report,binding: [] if report.get('policy_version')==2 and report.get('runtime_required') is True and report.get('binding')==binding else ['synthetic runtime boundary metadata invalid'])
    renderer_boundary.start()
    import atexit
    atexit.register(renderer_boundary.stop)
    with tempfile.TemporaryDirectory(prefix='known-issue-gate-selftest-') as temp:
        root = Path(temp)
        project, native, web = [root / name for name in ('Source', 'Native', 'Web')]
        for directory in (project / 'assets', native, web):
            directory.mkdir(parents=True)
        (project / 'assets/fixture.js').write_text('// Synthetic gate test; no game or SDK\n')
        (native / 'game.js').write_text('// Synthetic Native\n')
        (web / 'index.html').write_text('<p>Synthetic, not UI evidence</p>')
        # User 2026-10-24: the final audit reads the design decisions from the project records (docs/ is not part of the
        # source binding), because MOD-01 / RANK-01 / FEAT-00 / LEVEL-01 are design-stage rows now.
        def records(league='none', skin_bonus=True, daily_checkin=True, skins=True, mode='levels'):
            for rel, data in (('docs/league/decision.json', {'schema': 'league_decision.v1', 'decision': league}),
                              ('docs/features.json', {'schema': 'optional_features.v1', 'skin_bonus': skin_bonus,
                                                      'daily_checkin': daily_checkin}),
                              ('docs/modules.json', {'schema': 'game_modules.v1', 'asked': 'synthetic',
                                                     'skins': {'user_choice': skins}}),
                              ('docs/levels/level_plan.json', {'schema': 'level_plan.v1', 'mode': mode, 'why': 'synthetic'})):
                (project / rel).parent.mkdir(parents=True, exist_ok=True)
                (project / rel).write_text(json.dumps(data))
        records()
        inventory = root / 'inventory.json'
        entries = [{'id': 'video', 'policy': 'repeatable', 'trigger': 'rewarded_video', 'persistence': 'durable',
                    'reach_steps': 'Synthetic only', 'binding': 'Synthetic video binding', 'api': 'createRewardedVideoAd'},
                   {'id': 'mission', 'policy': 'navigation_reward', 'trigger': 'platform_mission', 'persistence': 'durable',
                    'reach_steps': 'Synthetic only', 'binding': 'Synthetic mission binding', 'api': 'getShortcutMissionReward'},
                   {'id': 'daily', 'policy': 'daily', 'trigger': 'direct', 'persistence': 'session',
                    'reach_steps': 'Synthetic only', 'binding': 'Synthetic daily binding'}]
        inventory.write_text(json.dumps(entries))
        a = SimpleNamespace(project=project, native=native, web=web, build_tag='synthetic-selftest',
                            inventory=inventory, review=root / 'review.json', markdown=root / 'review.md', stage='pre_scan')
        gate.init(a)
        baseline = gate.load(a.review)
        initial = gate.audit(a)
        results.append({'name': 'new checklist stays pending', 'passed': initial['status'] == 'blocked'})
        binding = baseline['binding']
        artifact = root / 'synthetic-observation.txt'
        artifact.write_text('Synthetic schema fixture. No actual GUI, phone or IAA observation.')
        ref = {'path': str(artifact), 'sha256': gate.sha(artifact.read_bytes()), 'role': 'current_artifact', 'binding': binding}
        def row(name='state'):
            return {'status': 'pass', 'layer': 'source', 'observed': 'Synthetic schema fixture only ' + name, 'evidence': [deepcopy(ref)]}
        baseline['inventory_complete'] = True
        baseline['inventory_evidence'] = [deepcopy(ref)]
        catalog = gate.load(gate.CATALOG)
        for item in catalog['items']:
            baseline['checks'][item['id']] = row(item['id'])
            if item.get('requires_gui'):
                baseline['checks'][item['id']].update(layer='gui_touch')
            if item.get('required_observations'):
                baseline['checks'][item['id']].update(observations={k: 'Synthetic ' + item['id'] + ' ' + k for k in item['required_observations']})
        auto_files = {}
        for tool in sorted({x for item in catalog['items'] for x in item.get('auto_check', [])}):
            report = root / (tool + '-report.json')
            extra = ({'reward_apis': ['createRewardedVideoAd', 'getShortcutMissionReward']} if tool == 'audit_async_contracts' else
                     {'decision': 'none'} if tool == 'audit_league' else
                     {'decision': {'skin_bonus': True, 'daily_checkin': True}} if tool == 'audit_optional_features' else
                     {'mode': 'levels'} if tool == 'audit_level_plan' else
                     {'stage': 'runtime'} if tool in {'audit_page_readiness', 'audit_loading_recovery'} else {})
            if tool == 'audit_native_storage_contract':
                from audit_native_storage_contract import CASES, digest
                runner = root / 'synthetic-storage-runner.py'
                runner.write_text('import argparse,hashlib,json\n'
                    'p=argparse.ArgumentParser();p.add_argument("--bundle");p.add_argument("--adapter");a=p.parse_args()\n'
                    'h=lambda q:hashlib.sha256(open(q,"rb").read()).hexdigest()\n'
                    'cases={k:"pass" for k in ' + repr(CASES) + '} if "Native" in a.bundle else {"missing_empty_string":"fail"}\n'
                    'print(json.dumps({"runner_sha256":h(__file__),"bundle_sha256":h(a.bundle),"adapter_sha256":h(a.adapter),"cases":cases}))\n')
                negative = root / 'negative-storage.js'; negative.write_text('// known bad synthetic control')
                def execution(bundle, label):
                    raw = root / (label + '-storage.json')
                    run = subprocess.run([sys.executable, str(runner), '--bundle', str(bundle), '--adapter', str(bundle)], capture_output=True, text=True, check=True)
                    raw.write_text(run.stdout)
                    return {'bundle': str(bundle), 'bundle_sha256': digest(bundle), 'adapter': str(bundle),
                            'adapter_sha256': digest(bundle), 'raw_report': str(raw), 'raw_sha256': digest(raw)}
                trace = {'schema': 'native_storage_trace.v1', 'binding': binding,
                         'execution': {'runner': str(runner), 'runner_sha256': digest(runner),
                                       'command': [sys.executable, str(runner), '--bundle', '{bundle}', '--adapter', '{adapter}']},
                         'current': execution(native / 'game.js', 'current'), 'negative_control': execution(negative, 'negative')}
                trace_file = root / 'synthetic-storage-trace.json'; trace_file.write_text(json.dumps(trace))
                extra = {'policy_version': 1, 'required_cases': list(CASES), 'trace': str(trace_file),
                         'trace_sha256': digest(trace_file), 'native': str(native)}
            if tool == 'test_writer_refusal':
                extra = {'checks': [{'id': cid, 'passed': True} for cid in
                                   ('missing_review', 'failed_check', 'stale_binding', 'missing_storage', 'normal')]}
            if tool == 'logic_check':
                digest = logic_reg.source_digest(project)
                extra = {'mode': 'build', 'regression_version': 1, 'regression_problems': 0,
                         'current_source_sha256': digest, 'regression_binding': {'source_sha256': digest},
                         'regressions': [{'id': spec[0], 'status': 'n/a',
                                          'note': 'Synthetic gate fixture only; no actual game tested'} for spec in logic_reg.CASES]}
            if tool == 'audit_startup_contract':
                extra={'policy_version':2,'runtime_required':True,'unit_boundary':'Renderer runtime is separately calibrated; this fixture only exercises catalog orchestration.'}
            if tool == 'logic_check':
                from test_button_state_check import save_fixture_report
                button_dir=root
                button_ref=save_fixture_report(button_dir)
                spec=next(spec for spec in logic_reg.CASES if spec[0]=='R06')
                extra['regressions'][5]={'id':'R06','status':'pass','layer':spec[3][0],
                    'observations':{k:'Synthetic orchestration observation: '+k for k in spec[4]},
                    'evidence':[{'path':str(artifact),'sha256':gate.sha(artifact.read_bytes())}],
                    'button_check_root':str(root),
                    'button_check':{'path':str((button_dir/button_ref['path']).resolve()),'sha256':button_ref['sha256']}}
            if tool == 'audit_loading_recovery':
                from audit_loading_recovery import SCENARIOS, POLICY_VERSION
                from test_loading_recovery_gate import RecoveryGateTests
                fixture = RecoveryGateTests()
                fixture.setUp()
                runtime_data = deepcopy(fixture.data)
                runtime_data['binding'] = binding
                runtime_data['raw_evidence'] = [{'path': artifact.name, 'sha256': gate.sha(artifact.read_bytes())}]
                fixture.doCleanups()
                runtime_path = root / 'synthetic-loading-runtime.json'
                runtime_path.write_text(json.dumps(runtime_data))
                extra.update(checked=len(SCENARIOS), policy_version=POLICY_VERSION, runtime_file=str(runtime_path), runtime_sha256=gate.sha(runtime_path.read_bytes()))
            if tool == 'audit_startup_loading':
                from test_startup_raw_gate import fixture as startup_fixture
                extra = startup_fixture(root / 'synthetic-startup', binding)
            report.write_text(json.dumps({'tool': tool, 'checked': 3, 'failed': 0, 'passed': True,
                                          'checks': [], 'binding': binding, **extra}))
            auto_files[tool] = report
        def auto_ref(tool):
            return {'path': str(auto_files[tool]), 'sha256': gate.sha(auto_files[tool].read_bytes())}
        for item in catalog['items']:
            if item.get('auto_check'):
                baseline['checks'][item['id']]['auto_reports'] = [auto_ref(x) for x in item['auto_check']]
            if item.get('reviewer'):
                baseline['checks'][item['id']]['reviewer'] = item['reviewer']
        for entry in baseline['reward_entries']:
            for state in catalog['reward_states']:
                entry['states'][state] = row()
                post = {'reward_applied_once': True, 'model_updated': True,
                        'presentation': ('next_eligible' if entry['policy'] == 'repeatable' else
                                         'retained_navigation' if entry['policy'] == 'navigation_reward' else 'disabled_claimed'),
                        'interactable': False, 'claimed_text_visible': True,
                        'navigation_available': True, 'claim_state_visible': True,
                        'reward_delta_zero': True, 'can_retry_or_exit': True,
                        'no_extra_reward_or_request': True, 'no_automatic_replay': True,
                        'terminal_failure_retry_available': True, 'unconfirmed_session_not_reopened': True,
                        'same_transaction_retried': True, 'no_additional_ad_request': True,
                        'commit_readback_ambiguity_checked': True, 'no_premature_success_ui': True,
                        'recovery_scope': 'process_only', 'actual_effect_verified': True,
                        'correct_target': True, 'quantity_and_effect_consistent': True,
                        'reward_identity_verified': True, 'current_reward_display_consistent': True,
                        'success_feedback_consistent': True, 'model_and_presentation_consistent': True,
                        'ownership_and_usage_distinguished': True, 'related_views_consistent': True,
                        'proof_target_preserved': True, 'checking_state_visible': True, 'bounded_wait': True,
                        'stale_request_invalidated': True, 'new_check_started': True, 'late_result_ignored': True,
                        'visible_result_feedback': True, 'failure_feedback_visible': True,
                        'sdk_and_timer_held_recovers': True, 'retry_after_recovery_works': True,
                        'each_channel_settles_once': True, 'non_eligible_results_no_reward': True,
                        'every_result_visible_end_state': True, 'test_double_supports_each_channel': True,
                        'channels_tested': ['callback', 'promise', 'both', 'void_or_incomplete', 'reject_or_throw', 'event']}
                entry['states'][state]['postconditions'] = post
        # Calibration (Monkey Dash 2026-10-21): the same check must have failed on a known-bad version.
        cal_tool = root / 'return-contract-check.py'
        cal_tool.write_text('# synthetic return-contract check\n')
        cal_raw = root / 'cal-raw.json'
        cal_raw.write_text(json.dumps({'passed': True, 'failed': 0, 'checks': [{'id': 'promise-only', 'passed': True}], 'binding': binding}))
        cal_current = root / 'cal-current.json'
        cal_current.write_text(json.dumps({'schema': 'known_issue_current_result.v1', 'binding': binding, 'status': 'pass', 'failed': 0,
            'execution': {'command': [sys.executable, str(cal_tool)], 'exit_code': 0,
                          'tool': {'path': str(cal_tool), 'sha256': gate.sha(cal_tool.read_bytes())},
                          'raw_report': {'path': str(cal_raw), 'sha256': gate.sha(cal_raw.read_bytes())}}}))
        cal_negative = root / 'cal-negative.json'
        def negative_doc(**change):
            doc = {'schema': 'known_issue_negative_control.v1', 'mutant': 'removed the Promise then handler', 'status': 'fail',
                   'failed': 8, 'tool': {'path': str(cal_tool), 'sha256': gate.sha(cal_tool.read_bytes())}}
            doc.update(change)
            return doc
        cal_negative.write_text(json.dumps(negative_doc()))
        def cal_refs(neg=cal_negative):
            return [{'path': str(cal_current), 'sha256': gate.sha(cal_current.read_bytes()), 'role': 'current_result'},
                    {'path': str(neg), 'sha256': gate.sha(neg.read_bytes()), 'role': 'negative_control'}]
        for item in catalog['items']:
            if item.get('requires_negative_control'):
                baseline['checks'][item['id']]['evidence'] = [deepcopy(ref)] + cal_refs()
        # GPT verdict on this build's contact sheets (any agent runs the tests; GPT judges the screens).
        import make_contact_sheet as cs
        from PIL import Image
        shots = root / 'shots'; shots.mkdir()
        for i, colour in enumerate([(170, 215, 250), (255, 240, 200)]):
            Image.new('RGB', (75, 162), colour).save(shots / ('page%d.png' % i))
        sheets = root / 'sheets'; sheets.mkdir()
        cs.build(cs.collect([shots]), sheets, 4, 8, 120, binding)
        manifest = sheets / 'contact-sheets.json'
        baseline['visual_verdict'] = {'reviewer': 'gpt', 'images_reviewed': 2, 'verdict': 'pass', 'open_issues': [],
                                      'observed': 'Synthetic sheets only: two plain pages, nothing judged.',
                                      'contact_sheets': {'path': str(manifest), 'sha256': gate.sha(manifest.read_bytes())}}
        def probe(name, change, expected='blocked'):
            current = deepcopy(baseline)
            change(current)
            a.review.write_text(json.dumps(current))
            result = gate.audit(a)
            results.append({'name': name, 'passed': result['status'] == expected,
                            'expected': expected, 'actual': result['status'], 'errors': result['errors']})
        def probe_records(name, change, expected='blocked', **rec):
            records(**rec)
            try:
                probe(name, change, expected)
            finally:
                records()
        probe('complete synthetic schema accepted (not a game pass)', lambda d: None, 'passed')
        # User 2026-10-24: design and art rows are checked at their own stage (design_check.py / art_check.py).
        gated = [x['id'] for x in catalog['items'] if x.get('gate') in ('design', 'art')]
        results.append({'name': 'design/art rows are the expected earlier-stage checks',
                        'passed': sorted(gated) == sorted(['MOD-01', 'ECON-01', 'LEVEL-01', 'FEAT-00', 'RANK-01', 'ART-01', 'ART-02',
                                                           'ART-03', 'ART-04', 'ART-05', 'ART-06', 'PAGE-01', 'UI-02', 'UI-03', 'UI-05'])})
        probe('final review without any design/art row accepted', lambda d: [d['checks'].pop(cid) for cid in gated], 'passed')
        def stale_gated_rows(d):
            d['checks']['ART-01'].update(layer='source'); d['checks']['ART-01'].pop('observations')
            d['checks']['UI-03'].update(status='not_applicable', reason='left over')
            d['checks']['MOD-01'].update(auto_reports=[])
            d['checks']['ART-06'].update(status='pending')
        probe('left-over design/art rows are ignored by the final audit', stale_gated_rows, 'passed')
        results.append({'name': 'final audit reports the earlier-stage checks',
                        'passed': set(gate.audit(SimpleNamespace(**{**vars(a), 'review': a.review})).get('earlier_stage_checks', {})) == {'design', 'art'}})
        logic_path = auto_files['logic_check']
        logic_good = logic_path.read_text()
        for missing in ('regression_version', 'regressions'):
            old = json.loads(logic_good)
            old.pop(missing)
            logic_path.write_text(json.dumps(old))
            probe('LOGIC-01 rejects missing ' + missing, lambda d: d['checks']['LOGIC-01'].update(
                auto_reports=[auto_ref('logic_check')]))
        logic_path.write_text(logic_good)
        probe('missing catalog item', lambda d: d['checks'].pop('AD-03'))
        probe('stale catalog digest', lambda d: d.update(catalog_sha256='0' * 64))
        for field in ('source_sha256', 'native_tree_sha256', 'web_tree_sha256'):
            probe('stale ' + field, lambda d, field=field: d['binding'].update({field: '0' * 64}))
        probe('remove actual inventory entry', lambda d: d['reward_entries'].pop())
        probe('alter durable reward to skip saving', lambda d: d['reward_entries'][0].update(persistence='session'))
        for cid in ('AD-03', 'STATE-02'):
            probe('declared mechanism cannot waive ' + cid, lambda d, cid=cid: d['checks'][cid].update(status='not_applicable', reason='Synthetic waiver'))
        probe('daily reward cannot waive period checks', lambda d: d['checks']['STATE-03'].update(
            status='not_applicable', reason='Synthetic contradictory waiver'))
        probe('historical evidence cannot waive current check', lambda d: d['checks']['STATE-05'].update(
            status='not_applicable', reason='No synthetic setting', evidence=[{**ref, 'role': 'historical_reference'}]))
        for cid in ('UI-01', 'UI-06', 'LOAD-02'):
            probe(cid + ' source alone cannot prove GUI', lambda d, cid=cid: d['checks'][cid].update(layer='source'))
            probe(cid + ' missing observations', lambda d, cid=cid: d['checks'][cid].pop('observations'))
        states = lambda d: d['reward_entries'][0]['states']
        probe('durable save retry cannot be waived', lambda d: states(d)['save_failure_retry'].update(status='not_applicable', reason='Synthetic skip'))
        probe('write committed/readback failure not checked', lambda d: states(d)['save_failure_retry']['postconditions'].pop('commit_readback_ambiguity_checked'))
        probe('save retry replays ad', lambda d: states(d)['save_failure_retry']['postconditions'].update(no_additional_ad_request=False))
        probe('memory receipt not declared durable', lambda d: states(d)['save_failure_retry']['postconditions'].update(recovery_scope='always_recovers'))
        probe('terminal error only exits but cannot retry', lambda d: states(d)['error']['postconditions'].pop('terminal_failure_retry_available'))
        probe('timeout can overlap old session', lambda d: states(d)['timeout']['postconditions'].update(unconfirmed_session_not_reopened=False))
        probe('reward balance without usable effect', lambda d: states(d)['apply_or_consume']['postconditions'].update(actual_effect_verified=False))
        # A correct balance cannot conceal a conflicting UI, cached use state, or receipt target.
        for state, fields in {
            'completed': ('reward_identity_verified', 'current_reward_display_consistent',
                          'success_feedback_consistent'),
            'reopen': ('model_and_presentation_consistent',),
            'reload': ('model_and_presentation_consistent',),
            'save_failure_retry': ('proof_target_preserved',),
            'apply_or_consume': ('ownership_and_usage_distinguished', 'related_views_consistent'),
        }.items():
            for field in fields:
                probe(state + ' missing ' + field,
                      lambda d, state=state, field=field: states(d)[state]['postconditions'].pop(field))
                probe(state + ' inconsistent ' + field,
                      lambda d, state=state, field=field: states(d)[state]['postconditions'].update({field: False}))
        probe('same observed text copied into two checks', lambda d: d['checks']['LOAD-02'].update(
            observed=d['checks']['FLOW-01']['observed']))
        probe('LOAD-03 observation fields repeat one summary', lambda d: d['checks']['LOAD-03'].update(
            observations={k: 'Played normally, revive worked' for k in d['checks']['LOAD-03']['observations']}))
        probe('VIS-01 without frame analysis report', lambda d: d['checks']['VIS-01'].update(auto_reports=[]))
        probe('AUDIO-02 cannot be waived', lambda d: d['checks']['AUDIO-02'].update(status='not_applicable', reason='Synthetic skip'))
        def bad_auto(d, change):
            tool = 'audit_frame_glitches'
            bad = root / ('bad-' + str(len(results)) + '.json')
            data = {'tool': tool, 'checked': 3, 'failed': 0, 'passed': True, 'checks': [], 'binding': binding}
            change(data)
            bad.write_text(json.dumps(data))
            d['checks']['VIS-01']['auto_reports'] = [{'path': str(bad), 'sha256': gate.sha(bad.read_bytes())}]
        probe('failed screenshot measurement blocks', lambda d: bad_auto(d, lambda x: x.update(failed=1, passed=False)))
        probe('measurement of another build blocks', lambda d: bad_auto(d, lambda x: x.update(binding={**binding, 'build_tag': 'old'})))
        probe('measurement with zero screenshots blocks', lambda d: bad_auto(d, lambda x: x.update(checked=0)))
        probe('report from a different tool blocks', lambda d: bad_auto(d, lambda x: x.update(tool='audit_audio_sources')))
        probe('edited report blocks', lambda d: d['checks']['VIS-01'].update(
            auto_reports=[{**auto_ref('audit_frame_glitches'), 'sha256': '0' * 64}]))
        vv = lambda d: d['visual_verdict']
        probe('visual checks need a GPT verdict', lambda d: d.pop('visual_verdict'))
        probe('test executor cannot sign the screen verdict', lambda d: vv(d).update(reviewer='executor-agent'))
        probe('screen verdict still pending', lambda d: vv(d).update(verdict='pending'))
        probe('open screen issues block', lambda d: vv(d).update(open_issues=['#07 coins overlap']))
        probe('verdict must cover every screenshot', lambda d: vv(d).update(images_reviewed=1))
        probe('verdict needs its own observation', lambda d: vv(d).update(observed='ok'))
        probe('edited sheet manifest blocks', lambda d: vv(d)['contact_sheets'].update(sha256='0' * 64))
        def old_sheets(d):
            other = root / 'sheets-old'; other.mkdir(exist_ok=True)
            for f in other.iterdir():
                f.unlink()
            cs.build(cs.collect([shots]), other, 4, 8, 120, {**binding, 'build_tag': 'old'})
            m = other / 'contact-sheets.json'
            vv(d)['contact_sheets'] = {'path': str(m), 'sha256': gate.sha(m.read_bytes())}
        probe('sheets of another build block', old_sheets)
        mission = lambda d: d['reward_entries'][1]['states']
        probe('declared platform task cannot waive GROW-01', lambda d: d['checks']['GROW-01'].update(
            status='not_applicable', reason='Synthetic skip'))
        probe('platform task cannot skip leave-and-return', lambda d: mission(d)['leave_and_return'].update(
            status='not_applicable', reason='Synthetic skip'))
        probe('return must start a new check', lambda d: mission(d)['leave_and_return']['postconditions'].update(new_check_started=False))
        probe('late old result must be ignored', lambda d: mission(d)['leave_and_return']['postconditions'].pop('late_result_ignored'))
        probe('silent failure looks like a dead button', lambda d: mission(d)['error']['postconditions'].update(failure_feedback_visible=False))
        probe('silent timeout on a video entry', lambda d: states(d)['timeout']['postconditions'].pop('failure_feedback_visible'))
        probe('waiting without a visible checking state', lambda d: mission(d)['pending']['postconditions'].update(checking_state_visible=False))
        probe('GROW-01 needs its GUI observations', lambda d: d['checks']['GROW-01']['observations'].pop('query_pending_then_leave_and_return'))
        probe('navigation can leave claim page', lambda d: d['reward_entries'][1]['states']['completed']['postconditions'].update(
            presentation='navigated', claim_page_left=True), 'passed')
        probe('navigation cannot claim leaving without readback', lambda d: d['reward_entries'][1]['states']['completed']['postconditions'].update(
            presentation='navigated', claim_page_left=False))

        # Two boards (references/two-boards.md): localize = Chinese source to English, remake = starter pack.
        remake_only = [x['id'] for x in catalog['items'] if not gate.applies(x, 'localize')]
        results.append({'name': 'remake-only items are the three new-art rules plus the league test (Q style, generated backgrounds, '
                                'new sound files, Weekly League in the game)',
                        'passed': sorted(remake_only) == ['ART-02', 'ART-03', 'AUDIO-02', 'RANK-02']})
        def localize(d):
            d['board'] = 'localize'
            for cid in remake_only:
                d['checks'].pop(cid)
        probe('localize review without new-game art/sound/economy rows accepted', localize, 'passed')
        # User 2026-10-21: 英化 art round 2 "按重塑画风重做" brings back the Q-style and background checks.
        def localize_remake_style(d):
            localize(d); d['art_style'] = 'remake'
        probe('localize in remake art style without ART-02/ART-03 rows accepted (art stage)', localize_remake_style, 'passed')
        def localize_remake_style_full(d):
            keep = {k: deepcopy(d['checks'][k]) for k in ('ART-02', 'ART-03')}
            localize(d); d['art_style'] = 'remake'; d['checks'].update(keep)
        probe('localize in remake art style with ART-02/ART-03 rows accepted', localize_remake_style_full, 'passed')
        probe('unknown art style rejected', lambda d: d.update(art_style='fancy'))
        probe('localize may still carry a remake-only row', lambda d: (localize(d), d['checks'].update(
            {'ART-02': {'status': 'not_applicable', 'reason': 'Localize keeps the original art'}})), 'passed')
        probe('localize review without the design-stage ECON-01 row accepted', lambda d: (localize(d), d['checks'].pop('ECON-01')), 'passed')
        probe('localize cannot mark the skin trial/map flow not applicable', lambda d: (localize(d), d['checks']['ECON-02'].update(
            status='not_applicable', reason='original game had no skins', evidence=[deepcopy(ref)])))
        probe('localize cannot skip the sound settings', lambda d: (localize(d), d['checks'].pop('AUDIO-01')))
        probe('localize cannot waive no-ad-skip', lambda d: (localize(d), d['checks']['NOSKIP-01'].update(
            status='not_applicable', reason='Synthetic skip')))
        probe('localize cannot drop the Chinese coverage check', lambda d: (localize(d), d['checks'].pop('UI-01')))
        probe('localize still needs the GPT screen verdict', lambda d: (localize(d), d.pop('visual_verdict')))
        probe('remake review cannot drop AUDIO-02', lambda d: d['checks'].pop('AUDIO-02'))
        probe('unknown board rejected', lambda d: (localize(d), d.update(board='english')))
        a.board = 'remake'
        probe('review made for localize cannot be checked as remake', localize)
        a.board = None
        loc = SimpleNamespace(**{**vars(a), 'review': root / 'loc' / 'review.json', 'markdown': root / 'loc' / 'review.md',
                                 'board': 'localize'})
        made = gate.init(loc)
        loc_review = gate.load(loc.review)
        results.append({'name': 'init --board localize records the board and leaves out remake-only rows',
                        'passed': made['board'] == 'localize' and loc_review['board'] == 'localize'
                                  and not set(remake_only) & set(loc_review['checks'])
                                  and 'ECON-02' in loc_review['checks'] and 'AUDIO-01' in loc_review['checks']
                                  and not set(gated) & set(loc_review['checks'])
                                  and '（英化）' in loc.markdown.read_text() and '前面阶段已查' in loc.markdown.read_text()})

        # Monkey Dash 2026-10-21: return channels, held timers, calibration, discovery, writer refusal.
        probe('mission without Promise channel tested', lambda d: d['reward_entries'][1]['states']['return_contracts']['postconditions'].update(
            channels_tested=['callback', 'both', 'void_or_incomplete', 'reject_or_throw']))
        probe('test double that only answers through success', lambda d: states(d)['return_contracts']['postconditions'].update(
            test_double_supports_each_channel=False))
        probe('return_contracts cannot be waived for a mission', lambda d: mission(d)['return_contracts'].update(
            status='not_applicable', reason='Synthetic skip'))
        probe('timeout code without held-timer recovery', lambda d: mission(d)['pending']['postconditions'].update(
            sdk_and_timer_held_recovers=False))
        probe('video wait without retry after recovery', lambda d: states(d)['pending']['postconditions'].pop('retry_after_recovery_works'))
        for cid in ('ASYNC-01', 'GROW-01'):
            probe(cid + ' without a known-bad run', lambda d, cid=cid: d['checks'][cid].update(evidence=[deepcopy(ref)] + cal_refs()[:1]))
        def other_tool_negative(d):
            other = root / 'other-check.py'; other.write_text('# a different check\n')
            neg = root / 'neg-other.json'
            neg.write_text(json.dumps(negative_doc(tool={'path': str(other), 'sha256': gate.sha(other.read_bytes())})))
            d['checks']['ASYNC-01']['evidence'] = [deepcopy(ref)] + cal_refs(neg)
        probe('known-bad run of a different check does not calibrate', other_tool_negative)
        def passing_negative(d):
            neg = root / 'neg-pass.json'; neg.write_text(json.dumps(negative_doc(status='pass', failed=0)))
            d['checks']['ASYNC-01']['evidence'] = [deepcopy(ref)] + cal_refs(neg)
        probe('a known-bad run that passed proves nothing', passing_negative)
        probe('ASYNC-01 missing the held-timer observation', lambda d: d['checks']['ASYNC-01']['observations'].pop('sdk_and_timer_held_recovery'))
        probe('ASYNC-01 cannot be waived', lambda d: d['checks']['ASYNC-01'].update(status='not_applicable', reason='Synthetic skip'))
        def undeclared_api(d):
            rep_path = root / 'async-extra.json'
            rep_path.write_text(json.dumps({'tool': 'audit_async_contracts', 'checked': 3, 'failed': 0, 'passed': True, 'checks': [],
                                            'binding': binding, 'reward_apis': ['createRewardedVideoAd', 'getShortcutMissionReward',
                                                                                'getEntranceMissionReward']}))
            d['checks']['ASYNC-01']['auto_reports'] = [{'path': str(rep_path), 'sha256': gate.sha(rep_path.read_bytes())}]
        probe('reward API in code without a declared entry', undeclared_api)
        def no_api(d):
            d['reward_entries'][1].pop('api')
        probe('platform entry must name its api', no_api)
        probe('COPY-01 marked pass by a test executor', lambda d: d['checks']['COPY-01'].update(reviewer='executor-agent'))
        probe('COPY-01 without the copy audit report', lambda d: d['checks']['COPY-01'].update(auto_reports=[]))
        probe('COPY-01 without the GPT phrasing review', lambda d: d['checks']['COPY-01']['observations'].pop('native_phrasing_review'))
        probe('COPY-01 cannot be waived', lambda d: d['checks']['COPY-01'].update(status='not_applicable', reason='Synthetic skip'))
        # User 2026-10-21: Weekly League (重塑) and monotonous pages.
        probe('RANK-02 may be scoped out when ranking is absent', lambda d: d['checks']['RANK-02'].update(
            status='not_applicable', reason='Synthetic fixture has no ranking module', layer='source'), 'passed')
        probe('RANK-02 without the no-ranking observation', lambda d: d['checks']['RANK-02']['observations'].pop('no_ranking_routes'))
        for cid in ('FEAT-01', 'FEAT-02'):
            probe(cid + ' waived although the user chose it', lambda d, cid=cid: d['checks'][cid].update(
                status='not_applicable', reason='Synthetic skip', layer='source'))
        def features_declined(d):
            for cid in ('FEAT-01', 'FEAT-02'):
                d['checks'][cid] = {'status': 'not_applicable', 'layer': 'source', 'reason': 'Synthetic: user said no (' + cid + ')',
                                    'observed': 'Synthetic declined ' + cid, 'evidence': [deepcopy(ref)]}
        probe_records('FEAT-01/02 may be not applicable when the user said no', features_declined, 'passed',
                      skin_bonus=False, daily_checkin=False, skins=False)
        probe_records('FEAT-01 waived although the skin module is kept', features_declined, 'blocked',
                      skin_bonus=False, daily_checkin=False, skins=True)
        # User 2026-10-22: top resource bar and the level map (both boards).
        probe('HUD-01 top bar cannot be waived', lambda d: d['checks']['HUD-01'].update(status='not_applicable', reason='Synthetic skip'))
        probe('HUD-01 without the live update observation', lambda d: d['checks']['HUD-01']['observations'].pop('counts_update_live'))
        probe('LEVEL-02 waived in a level game', lambda d: d['checks']['LEVEL-02'].update(
            status='not_applicable', reason='Synthetic skip', layer='source'))
        probe('LEVEL-02 without the limited reward observation', lambda d: d['checks']['LEVEL-02']['observations'].pop('limited_reward_once'))
        def endless_game(d):
            d['checks']['LEVEL-02'] = {'status': 'not_applicable', 'layer': 'source', 'reason': 'Synthetic: endless game, no levels',
                                       'observed': 'Synthetic endless LEVEL-02', 'evidence': [deepcopy(ref)]}
        probe_records('LEVEL-02 may be not applicable in an endless game', endless_game, 'passed', mode='endless')
        probe('INPUT-05 every button tapped cannot be waived', lambda d: d['checks']['INPUT-05'].update(status='not_applicable', reason='Synthetic skip'))
        probe('INPUT-05 without the button coverage report', lambda d: d['checks']['INPUT-05'].update(auto_reports=[]))
        # User 2026-10-22: the test stage ends only when all non-Codex rows are done (--executor-exit).
        a.executor_exit = True
        def codex_rows_pending(d):
            d['checks']['COPY-01'] = {'status': 'pending'}
            d['visual_verdict'] = {'reviewer': '', 'verdict': 'pending'}
            d['test_executor'] = 'grok'
        probe('test stage complete with only Codex rows left', codex_rows_pending, 'test_stage_complete')
        def one_test_left(d):
            codex_rows_pending(d)
            d['checks']['AD-02'] = {'status': 'pending'}
        probe('test stage not complete while a normal check is pending', one_test_left, 'test_stage_incomplete')
        a.executor_exit = False
        def league_skipped(d):
            d['checks']['RANK-02'] = {'status': 'not_applicable', 'layer': 'source', 'reason': 'Synthetic: only 12 levels, decision skip',
                                      'observed': 'Synthetic league skip', 'evidence': [deepcopy(ref)]}
        probe_records('RANK-02 may be not applicable when the league decision is skip', league_skipped, 'passed', league='skip')
        # User 2026-10-21: tests run by a cheaper AI need a GPT spot check.
        def flows(n=3, ids=('AD-02', 'GROW-01', 'FLOW-03')):
            return [{'check_id': ids[i], 'observed': 'GPT redid flow %d itself and saw the same result' % i,
                     'evidence': [deepcopy(ref)]} for i in range(n)]
        def spot(d, **change):
            d['test_executor'] = 'other-ai cheap model'
            d['gpt_spot_check'] = dict({'reviewer': 'gpt', 'locked_commit': 'abc1234', 'code_changes_reviewed': True,
                                        'rerun_auto_checks': True, 'flows': flows(), 'disagreements': []}, **change)
        probe('tests by another AI without a GPT spot check', lambda d: d.update(test_executor='other-ai cheap model'))
        probe('tests by another AI with a GPT spot check accepted', spot, 'passed')
        probe('spot check with only two flows', lambda d: spot(d, flows=flows(2)))
        probe('spot check signed by the executor', lambda d: spot(d, reviewer='other-ai'))
        probe('spot check without re-running the scripts', lambda d: spot(d, rerun_auto_checks=False))
        probe('spot check skips the platform task', lambda d: spot(d, flows=flows(3, ('AD-02', 'FLOW-03', 'FLOW-01'))))
        probe('code fixed by the test AI but not reviewed by GPT', lambda d: spot(d, code_changes_reviewed=False))
        probe('spot check without the lock commit', lambda d: spot(d, locked_commit=''))
        probe('spot check found mismatches', lambda d: spot(d, disagreements=['FLOW-01 record says pass, GPT saw no new round']))
        a.stage = 'post_package'
        probe('post-package review accepted with writer refusal evidence', lambda d: None, 'passed')
        probe('BUILD-03 without the writer refusal report', lambda d: d['checks']['BUILD-03'].update(auto_reports=[]))
        probe('BUILD-03 needs each refusal observation', lambda d: d['checks']['BUILD-03']['observations'].pop('stale_binding_refused'))
        a.stage = 'pre_scan'

        tool = root / 'execute-fixture.py'
        payload = {'passed': True, 'count': 1, 'checks': [{'passed': True}], 'binding': binding}
        tool.write_text('import json\nprint(json.dumps(' + repr(payload) + '))\n')
        command = [sys.executable, str(tool)]
        execution = subprocess.run(command, text=True, capture_output=True, check=True)
        raw = root / 'raw.json'; raw.write_text(execution.stdout)
        wrapper = root / 'current.json'
        def wrapped(d, mode):
            detail = {'schema': 'known_issue_current_result.v1', 'binding': binding, 'status': 'pass', 'failed': 0}
            if mode != 'no_trace':
                detail['execution'] = {'command': command, 'exit_code': 0,
                    'tool': {'path': str(tool), 'sha256': gate.sha(tool.read_bytes())},
                    'raw_report': {'path': str(raw), 'sha256': gate.sha(raw.read_bytes())}}
            wrapper.write_text(json.dumps(detail))
            d['checks']['AD-02']['evidence'] = [{'path': str(wrapper), 'sha256': gate.sha(wrapper.read_bytes()), 'role': 'current_result'}]
        probe('result without execution trace rejected', lambda d: wrapped(d, 'no_trace'))
        probe('trace and passing raw execution accepted', lambda d: wrapped(d, 'valid'), 'passed')
        raw.write_text(json.dumps({'passed': True, 'checks': [{'passed': True}]}))
        probe('old unbound pass cannot be repackaged as current', lambda d: wrapped(d, 'valid'))
        raw.write_text(json.dumps({**payload, 'binding': {**binding, 'native_tree_sha256': '0' * 64}}))
        probe('old Native raw result cannot be repackaged as current', lambda d: wrapped(d, 'valid'))
        raw.write_text(json.dumps({'passed': False, 'checks': [{'passed': False}]}))
        probe('pass wrapper cannot hide failed raw execution', lambda d: wrapped(d, 'valid'))
        raw.write_text(json.dumps({**payload, 'status': 'pass', 'rows': [{'id': 'restart-3', 'status': 'failed'}]}))
        probe('a failed row wins over a pass status', lambda d: wrapped(d, 'valid'))
        raw.write_text(json.dumps({**payload, 'checks': [{'id': 'a', 'passed': True}, {'id': 'a', 'passed': True}]}))
        probe('duplicate raw case IDs rejected', lambda d: wrapped(d, 'valid'))
    report = {'passed': all(x['passed'] for x in results), 'count': len(results), 'cases': results,
              'limits': 'Synthetic gate orchestration; renderer execution boundary stubbed and separately refusal-tested. Synthetic gate acceptance/rejection only. Does not validate any game, actual GUI, mobile touch, real IAA or platform result.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'count': report['count'], 'report': str(args.report.resolve())}))
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
