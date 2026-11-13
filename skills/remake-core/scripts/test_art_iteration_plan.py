"""Art planner decisions and real-checker refusal; synthetic fixtures are never ART proof."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import art_iteration_plan as planner
import art_preflight
import test_art_first_piece_scope as fixture_scope

HERE = Path(__file__).resolve().parent


class IterationPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root/'project'
        (self.project/'assets').mkdir(parents=True)
        (self.project/'docs/art').mkdir(parents=True)
        self.build = self.root/'web'
        self.build.mkdir()
        (self.build/'index.html').write_text('<html><head></head><body></body></html>')
        self.dumps = self.root/'dumps'
        self.dumps.mkdir()
        self.visual = dict(cases=[self.slot('slot-alpha', 'alpha'), self.slot('slot-beta', 'beta')])
        self.capture = dict(cases=[self.state('capture-one', 'alpha'),
                                   self.state('capture-two', 'beta'),
                                   self.state('capture-condition', 'condition')])
        self.write_contracts()

    @staticmethod
    def slot(identifier, screen, width=375, height=667):
        return dict(id=identifier, screen=screen, viewport_width=width, viewport_height=height)

    @staticmethod
    def state(identifier, screen, width=375, height=667):
        return dict(id=identifier, screen=screen, width=width, height=height, dpr=2,
                    kind='popup', recipe='open and close each real state', environment='controlled-v1',
                    stable=False, witness=[dict(path='Canvas/'+screen)])

    def write_contracts(self):
        (self.project/'docs/art/visual-slots.json').write_text(json.dumps(self.visual))
        (self.project/'docs/art/capture-plan.json').write_text(json.dumps(self.capture))

    def decision(self, *, action='keep_round', reason='current', capture=None,
                 diagnostics=(), previous=None, source_hash='source-1', current=True, passed=True):
        status = dict(suggested_action=action, reason_code=reason, source_hash=source_hash,
                      export_hash='web-1', matrix_hash='matrix-1', collector_hash='collector-1')
        if capture is None:
            capture = dict(ready=False, cases=[dict(id=s['id'], action='recapture') for s in self.capture['cases']])
        calls = []
        def collector(command, project, build, dumps=None):
            calls.append(command)
            return copy.deepcopy(status if command == 'status' else capture)
        fp = dict(current=current, passed=passed, selected_cases=['slot-alpha'],
                  remaining_cases=['slot-beta'], binding_sha256='first-piece-1', checker_replays=0)
        with mock.patch.object(planner, 'capture_check', side_effect=collector), \
             mock.patch.object(planner, 'first_piece_state', return_value=(fp, dict(passed=passed))):
            result = planner.plan(self.project, self.build, self.dumps, diagnostics=diagnostics,
                                  previous=previous, board='localize')
        self.assertEqual(result['product_actions_executed'], 0)
        self.assertFalse(result['receipt_written'])
        self.assertIsNone(result['full_art_passed'])
        self.assertEqual(calls[0], 'status')
        return result

    def diagnostic(self, value):
        path = self.root/'diagnostic.json'
        path.write_text(json.dumps(value))
        return path

    def actions(self, result):
        return [item['action'] for item in result['next_actions']]

    def test_distinct_slot_and_capture_namespaces_do_not_guess_equal_ids(self):
        self.capture['cases'].append(self.state('slot-alpha', 'different-page'))
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertEqual(links, {'slot-alpha': 'capture-one', 'slot-beta': 'capture-two'})
        self.assertEqual(problems, [])

    def test_ambiguous_mapping_requires_exact_explicit_link(self):
        self.capture['cases'].append(self.state('same-state-other-recipe', 'alpha'))
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertNotIn('slot-alpha', links)
        self.assertIn('missing_or_ambiguous_capture_mapping', {p['code'] for p in problems})
        self.visual['cases'][0]['capture_case'] = 'same-state-other-recipe'
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertEqual(links['slot-alpha'], 'same-state-other-recipe')
        self.assertEqual(problems, [])
        self.visual['cases'][0]['capture_case'] = 'capture-two'  # Explicit wrong page cannot waive geometry.
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertNotIn('slot-alpha', links)
        self.assertTrue(problems)

    def test_mapping_uses_height_and_missing_height_can_be_ambiguous(self):
        self.capture['cases'].append(self.state('alpha-tall', 'alpha', height=812))
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertEqual(links['slot-alpha'], 'capture-one')
        self.assertEqual(problems, [])
        del self.visual['cases'][0]['viewport_height']
        links, problems = planner.mapping(self.visual, self.capture)
        self.assertNotIn('slot-alpha', links)
        self.assertTrue(problems)

    def test_duplicate_ids_and_missing_production_consumer_are_not_silent(self):
        self.visual['cases'].append(self.visual['cases'][0].copy())
        with self.assertRaises(ValueError):
            planner.mapping(self.visual, self.capture)
        self.visual['cases'].pop()
        self.visual['production_assets'] = [dict(id='shared', expected_cases=['unknown-slot'])]
        _, problems = planner.mapping(self.visual, self.capture)
        self.assertIn('production_consumer_missing_visual_rule', {p['code'] for p in problems})

    def test_empty_visual_cannot_become_empty_first_piece(self):
        self.visual['cases'] = []
        self.write_contracts()
        result = self.decision()
        self.assertEqual(self.actions(result), ['complete_scope_mapping'])
        self.assertNotIn('check_representative_first_piece', self.actions(result))

    def test_matrix_and_collector_changes_request_new_round_without_build(self):
        for why in ('matrix_changed', 'collector_changed'):
            with self.subTest(reason=why):
                result = self.decision(action='new_round', reason=why, current=False)
                self.assertEqual(self.actions(result), ['start_new_capture_round'])
                self.assertNotIn('build_web_once', self.actions(result))

    def test_changed_export_is_verified_without_unnecessary_second_build(self):
        result = self.decision(action='verify_export_then_new_round', reason='source_and_export_changed')
        self.assertEqual(self.actions(result), ['verify_export_then_new_round'])
        self.assertNotIn('build_web_once', self.actions(result))

    def test_source_changed_with_old_web_requests_one_build(self):
        result = self.decision(action='rebuild_web', reason='source_changed_export_unchanged')
        self.assertEqual(self.actions(result), ['build_web_once'])

    def test_capture_faults_do_not_become_generation_or_build_jobs(self):
        reports = [dict(reason_code='capture_not_ready', case='capture-one'),
                   dict(tool='art_input_preflight', ready=False,
                        capture_round=dict(cases=[dict(id='capture-two', action='recapture')])),
                   dict(passed=False, layout=dict(status='error', passed=False)),
                   dict(passed=False, text=dict(status='error', passed=False)),
                   dict(passed=False, slots=dict(passed=False, error='missing capture'))]
        for report in reports:
            with self.subTest(report=report):
                result = self.decision(action='rebuild_web', diagnostics=[self.diagnostic(report)])
                self.assertEqual(self.actions(result), ['repair_capture_contract'])
                self.assertFalse(any('generat' in value or 'build' in value for value in self.actions(result)))

    def test_slots_cases_results_are_integration_findings(self):
        report = dict(passed=False, slots=dict(passed=False, cases=[
            dict(id='slot-alpha', passed=False), dict(id='slot-beta', passed=True)]))
        result = self.decision(diagnostics=[self.diagnostic(report)])
        self.assertEqual(self.actions(result), ['inspect_shared_integration_cause'])
        row = next(p for p in result['issues'] if p['code'] == 'visual_slot_failed')
        self.assertEqual(row['targets'], ['slot-alpha'])

    def test_producer_failure_does_not_automatically_regenerate(self):
        report = dict(production=dict(passed=False, assets=[dict(id='shared', passed=False)]))
        result = self.decision(diagnostics=[self.diagnostic(report)])
        self.assertEqual(self.actions(result), ['inspect_production_batch'])

    def test_same_symptom_diagnoses_repeat_even_after_changed_source(self):
        path = self.diagnostic(dict(slots=dict(passed=False, cases=[dict(id='slot-alpha', passed=False)])))
        first = self.decision(diagnostics=[path])
        second = self.decision(diagnostics=[path], previous=first)
        self.assertEqual(second['same_symptom_count'], 1)
        self.assertEqual(self.actions(second)[0], 'diagnose_repeated_cause')
        self.assertTrue(second['next_actions'][0]['identical_inputs'])
        third = self.decision(diagnostics=[path], previous=second, source_hash='source-2')
        self.assertEqual(third['same_symptom_count'], 2)
        self.assertFalse(third['next_actions'][0]['identical_inputs'])
        self.diagnostic(dict(slots=dict(passed=False, cases=[dict(id='slot-beta', passed=False)])))
        changed = self.decision(diagnostics=[path], previous=third)
        self.assertNotIn('diagnose_repeated_cause', self.actions(changed))

    def test_recipe_string_never_proves_route_batching(self):
        states = self.capture['cases'][:2]
        groups = planner.capture_groups(states, ['capture-one', 'capture-two'])
        self.assertEqual([g['ids'] for g in groups], [['capture-one'], ['capture-two']])
        self.assertTrue(all(g['preserve_action_order'] for g in groups))

    def test_same_signed_route_groups_in_original_order_and_fixture_viewport_split(self):
        states = copy.deepcopy(self.capture['cases'])
        for state in states:
            state.update(planSha='a'*64, storageSha='b'*64)
        groups = planner.capture_groups(states, ['capture-two', 'capture-one', 'capture-condition'])
        self.assertEqual(groups[0]['ids'], ['capture-one', 'capture-two', 'capture-condition'])
        states[1]['storageSha'] = 'c'*64
        states[2]['height'] = 812
        groups = planner.capture_groups(states, [s['id'] for s in states])
        self.assertEqual(len(groups), 3)

    def test_original_collector_required_set_and_recapture_decisions_preserved(self):
        capture = dict(ready=False, cases=[dict(id='capture-one', action='fresh'),
            dict(id='capture-two', action='reuse'), dict(id='capture-condition', action='recapture')])
        result = self.decision(capture=capture)
        self.assertEqual(result['required_capture_cases'], [s['id'] for s in self.capture['cases']])
        self.assertEqual(result['capture_plan'], capture)
        self.assertEqual(self.actions(result), ['capture_required_cases'])
        self.assertEqual(result['next_actions'][0]['capture_cases'], ['capture-condition'])
        self.assertEqual(result['remaining_visual_cases'], ['slot-beta'])
        all_required = dict(ready=False, cases=[dict(id=s['id'], action='recapture') for s in self.capture['cases']])
        result = self.decision(capture=all_required)
        self.assertEqual(result['next_actions'][0]['capture_cases'], result['required_capture_cases'])

    def test_collector_ready_only_schedules_original_full_gates(self):
        result = self.decision(capture=dict(ready=True, cases=[dict(id=s['id'], action='fresh') for s in self.capture['cases']]))
        self.assertEqual(self.actions(result), ['run_input_then_full_art_check'])
        self.assertIsNone(result['full_art_passed'])
        self.assertFalse(result['receipt_written'])

    def captured_report(self):
        return dict(selected_cases=['slot-alpha'], input_binding=dict(documents=[
            dict(file=str(self.dumps/'capture-ui-dump-capture-one.json'))]))

    def test_first_piece_capture_fresh_or_reuse_is_required_even_when_rest_missing(self):
        data = self.captured_report()
        links = {'slot-alpha': 'capture-one', 'slot-beta': 'capture-two'}
        for action in ('fresh', 'reuse'):
            capture = dict(ready=False, cases=[dict(id='capture-one', action=action),
                                               dict(id='capture-two', action='recapture')])
            self.assertTrue(planner.first_piece_capture_current(data, links, capture, self.dumps))
        for capture in (dict(cases=[dict(id='capture-one', action='recapture')]),
                        dict(cases=[]), dict(error='changed source', cases=[]), None):
            self.assertFalse(planner.first_piece_capture_current(data, links, capture, self.dumps))

    def test_collector_verified_original_paths_are_preserved_for_mixed_evidence(self):
        data = dict(selected_cases=['slot-alpha'], input_binding=dict(documents=[dict(
            file=str(self.root/'original/capture-ui-dump-capture-one.json'))]))
        links = {'slot-alpha': 'capture-one'}
        capture = dict(cases=[dict(id='capture-one', action='reuse')],
            resolved_dumps=[str(self.root/'original/capture-ui-dump-capture-one.json')])
        self.assertTrue(planner.first_piece_capture_current(data, links, capture, self.dumps))
        capture['resolved_dumps'].append(str(self.root/'other/capture-ui-dump-capture-one.json'))
        self.assertFalse(planner.first_piece_capture_current(data, links, capture, self.dumps))

    def test_first_piece_capture_rejects_unrelated_old_or_extra_dump_paths(self):
        links = {'slot-alpha': 'capture-one', 'slot-beta': 'capture-two'}
        capture = dict(cases=[dict(id='capture-one', action='fresh')])
        data = self.captured_report()
        data['input_binding']['documents'][0]['file'] = str(self.root/'older-round/capture-ui-dump-capture-one.json')
        self.assertFalse(planner.first_piece_capture_current(data, links, capture, self.dumps))
        data = self.captured_report()
        data['input_binding']['documents'].append(dict(file=str(self.dumps/'capture-ui-dump-capture-two.json')))
        self.assertFalse(planner.first_piece_capture_current(data, links, capture, self.dumps))
        data = self.captured_report()
        data['selected_cases'] = ['capture-one']  # Capture ID is not a slot ID.
        self.assertFalse(planner.first_piece_capture_current(data, links, capture, self.dumps))

    def test_plan_never_replays_report_whose_original_capture_is_not_current(self):
        path = self.root/'old-first-piece.json'
        path.write_text(json.dumps(self.captured_report()))
        def capture(command, *args):
            if command == 'status':
                return dict(suggested_action='keep_round')
            return dict(ready=False, cases=[dict(id='capture-one', action='recapture')])
        with mock.patch.object(planner, 'capture_check', side_effect=capture), \
             mock.patch.object(art_preflight, 'run', side_effect=AssertionError('stale report must not execute')) as run:
            result = planner.plan(self.project, self.build, self.dumps, first_piece=path, board='localize')
        run.assert_not_called()
        self.assertFalse(result['first_piece']['current'])
        self.assertFalse(result['first_piece']['capture_verified'])
        self.assertEqual(result['checker_replays'], 0)
        self.assertEqual(self.actions(result), ['check_representative_first_piece'])

    def test_sealed_failure_reused_after_report_copy_and_invalidated_by_real_changes(self):
        fixture = fixture_scope.Scope()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        target = fixture.project/'docs/art/first_piece-ad-pages.json'
        manifest = fixture.project/'docs/art/ad-manifest.json'
        manifest.write_text(json.dumps({'first_piece_report': 'docs/art/first_piece-ad-pages.json'}))
        out = fixture.root/'sealed-first-piece'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(art_preflight.run(fixture.project, fixture.dumps, out,
                board='localize', case_ids=['slot-a']), 1)
        original = out/'production-preflight.json'
        target.write_bytes(original.read_bytes())
        slots = {c['id']: c for c in fixture.cases}
        def check():
            return planner.first_piece_state(fixture.project, target, slots, fixture.dumps, 'localize')
        with mock.patch.object(art_preflight, 'run', wraps=art_preflight.run) as rerun:
            state, checked = check()
            self.assertEqual(state['checker_replays'], 0)
            self.assertFalse(state['passed'])
            rerun.assert_not_called()
            state2, _ = check()
            self.assertEqual(state2['checker_replays'], 0)
        # A private cache alteration cannot manufacture a pass.
        cache_files = list((fixture.project/'.tiktok-kit/art-analysis-cache/v1').glob('*.json'))
        sealed = next(p for p in cache_files if 'first-piece-result' not in p.name and
                      isinstance(json.loads(p.read_text()).get('value', [None,None])[1], dict) and
                      'report' in json.loads(p.read_text())['value'][1])
        data = json.loads(sealed.read_text())
        data['value'][1]['report']['passed'] = True
        sealed.write_text(json.dumps(data))
        with mock.patch.object(art_preflight, 'run', wraps=art_preflight.run) as rerun:
            state, checked = check()
            self.assertEqual(state['checker_replays'], 1)
            self.assertFalse(checked['passed'])
            rerun.assert_called_once()
        # Unknown real project input must invalidate the precise first-piece result.
        (fixture.project/'docs/art/actual-new-policy.json').write_text('{"setting":1}')
        with mock.patch.object(art_preflight, 'run', wraps=art_preflight.run) as rerun:
            state, _ = check()
            self.assertEqual(state['checker_replays'], 1)
            rerun.assert_called_once()
        import art_analysis_cache
        real_hash = art_analysis_cache.file_hash
        def changed_checker(path):
            value = real_hash(path)
            return '0'*64 if Path(path).name == 'audit_art_slots.py' else value
        with mock.patch.object(art_analysis_cache, 'file_hash', side_effect=changed_checker), \
             mock.patch.object(art_preflight, 'run', wraps=art_preflight.run) as rerun:
            state, _ = check()
            self.assertEqual(state['checker_replays'], 1)
            rerun.assert_called_once()

    def test_explicit_clarity_policy_reaches_child_and_changed_project_policy_rechecks_once(self):
        from clarity_policy import resolve_policy
        fixture = fixture_scope.Scope()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        out = fixture.root/'strict-policy-first-piece'
        strict = resolve_policy(fixture.project, cli_preset='strict')
        with contextlib.redirect_stdout(io.StringIO()):
            art_preflight.run(fixture.project, fixture.dumps, out, board='localize',
                              case_ids=['slot-a'], clarity_policy=strict)
        report = json.loads((out/'production-preflight.json').read_text())
        child = json.loads((out/'pages.json').read_text())
        self.assertEqual(child['clarity_policy']['severity'], 'blocking')
        self.assertEqual(report['input_binding']['scope']['clarity_policy']['preset'], 'strict')
        self.assertEqual(child['clarity_policy']['min_ratio'], 2)
        # A project-file policy can change; an explicit CLI override remains explicit.
        policy = fixture.project/'docs/art/clarity-policy.json'
        policy.write_text(json.dumps({'preset': 'default', 'min_ratio': 0.75}))
        self.assertEqual(art_preflight.current_clarity_policy(fixture.project, strict)['min_ratio'], 2)
        project_only = resolve_policy(fixture.project)
        policy.write_text(json.dumps({'preset': 'strict', 'min_ratio': 3}))
        self.assertEqual(art_preflight.current_clarity_policy(fixture.project, project_only)['min_ratio'], 3)
        new_binding = art_preflight.first_piece_input_binding(fixture.project,
            [row['file'] for row in report['input_binding']['documents']], ['slot-a'],
            'localize', clarity_policy=project_only)
        self.assertEqual(new_binding['scope']['clarity_policy']['min_ratio'], 3)
        self.assertNotEqual(new_binding, report['input_binding'])

    def test_production_only_cli_preserves_explicit_strict_policy(self):
        fixture = fixture_scope.Scope()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        out = fixture.root/'strict-cli'
        proc = subprocess.run([sys.executable, '-B', str(HERE/'art_check.py'),
            '--project', str(fixture.project), '--board', 'localize', '--production-only',
            '--dumps', str(fixture.dumps), '--first-piece-case', 'slot-a',
            '--clarity-preset', 'strict', '--out', str(out)], capture_output=True, text=True)
        self.assertIn(proc.returncode, (0, 1), proc.stdout+proc.stderr)
        preflight = json.loads((out/'production-preflight.json').read_text())
        pages = json.loads((out/'pages.json').read_text())
        self.assertEqual(preflight['clarity_policy']['severity'], 'blocking')
        self.assertEqual(pages['clarity_policy']['severity'], 'blocking')
        self.assertEqual(pages['clarity_policy']['min_ratio'], 2)

    def test_probe_early_formal_first_piece_is_invalidated_by_later_batch_growth(self):
        """Document the real closure limit; production order avoids this extra replay."""
        from PIL import Image
        import art_analysis_cache
        fixture = fixture_scope.Scope()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        (fixture.project/'docs/art/button-set.json').write_text(json.dumps({
            'style': 'synthetic test only', 'frames': ['fixture_action']}))
        document = json.loads(fixture.a.read_text())
        document.update(kind='gameplay', purpose='gameplay')
        fixture.a.write_text(json.dumps(document))
        image = Image.new('RGB', (100, 200))
        image.putdata([(70+x, 90+y//2, 140+(x+y)%30) for y in range(200) for x in range(100)])
        image.save(fixture.dumps/'actual-capture-one.png')
        # Isolate checker files so the probe can add a real unrelated tool without
        # mutating the installed Skill or another agent's working files.
        tools = fixture.root/'isolated-tools'
        tools.mkdir()
        (tools/'pixel_helper.py').write_text('# synthetic production helper')
        out = fixture.root/'early-formal-probe'
        slots = {case['id']: case for case in fixture.cases}
        with mock.patch.object(art_analysis_cache, '__file__', str(tools/'art_analysis_cache.py')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(art_preflight.run(fixture.project, fixture.dumps, out,
                    board='localize', case_ids=['slot-a']), 0)
            def state():
                return planner.first_piece_state(fixture.project, out/'production-preflight.json',
                    slots, fixture.dumps, 'localize')[0]
            first = state()
            self.assertTrue(first['passed'])
            self.assertEqual(first['checker_replays'], 0)
            (fixture.project/'assets/unrelated-unused.txt').write_text('not referenced by selected page')
            grown_assets = state()
            self.assertTrue(grown_assets['passed'])
            self.assertEqual(grown_assets['checker_replays'], 1)
            (tools/'unrelated_upload_checker.py').write_text('# no selected-page imports')
            grown_tools = state()
            self.assertTrue(grown_tools['passed'])
            self.assertEqual(grown_tools['checker_replays'], 1)
            self.assertEqual(state()['checker_replays'], 0)

    def test_real_failed_preflight_report_cannot_pass_after_scalar_tampering(self):
        # Real checker execution over intentionally bad synthetic pages; no mocked pixels/verdict.
        fixture = fixture_scope.Scope()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        out = fixture.root/'real-first-piece'
        with contextlib.redirect_stdout(io.StringIO()):
            code = art_preflight.run(fixture.project, fixture.dumps, out,
                                     board='localize', case_ids=['slot-a'])
        data = json.loads((out/'production-preflight.json').read_text())
        self.assertEqual(code, 1)
        self.assertFalse(data['passed'])
        self.assertTrue(data['input_binding']['available'], data)
        self.assertTrue(data['pages']['findings'])
        data['passed'] = True  # Attacker/user-authored scalar cannot bypass actual pixel/layout checks.
        forged = fixture.root/'forged-first-piece.json'
        forged.write_text(json.dumps(data))
        with mock.patch.object(art_preflight, 'run', wraps=art_preflight.run) as rerun:
            state, checked = planner.first_piece_state(
                fixture.project, forged, {c['id']: c for c in fixture.cases},
                dumps=fixture.dumps, board='localize')
        rerun.assert_called_once()
        self.assertTrue(state['current'])
        self.assertFalse(state['passed'])
        self.assertEqual(state['checker_replays'], 1)
        self.assertFalse(checked['passed'])
        self.assertTrue(checked['pages']['findings'])
        self.assertTrue(json.loads(forged.read_text())['passed'])
        self.assertFalse((fixture.project/'.tiktok-kit/art-receipt.json').exists())

    def test_cli_cannot_overwrite_source_or_input_report(self):
        source = self.project/'assets/ui.js'
        source.write_text('original source')
        report = self.root/'original-report.json'
        report.write_text(json.dumps(dict(tool='art_production_preflight')))
        for target, extra in [(source, []), (report, ['--first-piece', str(report)])]:
            before = target.read_bytes()
            proc = subprocess.run([sys.executable, '-B', str(HERE/'art_iteration_plan.py'),
                '--project', str(self.project), '--board', 'localize', '--out', str(target), *extra],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, proc.stdout+proc.stderr)
            self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
