import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ad_ui_stage_check import evaluate_plan, full_art_coverage


class AdUIStageCheck(unittest.TestCase):
    def setUp(self):
        self.plan = {
            'schema': 'art_iteration_plan.v1', 'advisory_only': True,
            'first_piece': {'current': True, 'passed': True, 'capture_verified': True,
                            'selected_cases': ['trial_narrow', 'trial_tall']},
            'visual_to_capture': {'trial_narrow': 'trial_375', 'trial_tall': 'trial_390'},
            'capture_plan': {'cases': [{'id': 'trial_375', 'action': 'fresh'},
                                       {'id': 'trial_390', 'action': 'reuse'},
                                       {'id': 'unrelated_shop', 'action': 'recapture'}]},
            'issues': [], 'remaining_visual_cases': ['unrelated_shop'],
        }
        self.required = ['trial_narrow', 'trial_tall']
        self.coverage = {'verified': True, 'checked_visual_case_ids': self.required, 'problems': []}

    def test_current_owning_checks_allow_only_required_cases(self):
        problems, checked = evaluate_plan(self.plan, self.required, self.coverage)
        self.assertEqual(problems, [])
        self.assertEqual(checked, self.required)
        self.assertEqual(self.plan['capture_plan']['cases'][-1]['action'], 'recapture')

    def test_bare_passed_does_not_replace_real_checker(self):
        problems, checked = evaluate_plan({'passed': True}, self.required)
        self.assertTrue(problems)
        self.assertEqual(checked, [])

    def test_one_representative_plus_full_case_analysis_avoids_duplicate_production(self):
        self.plan['first_piece']['selected_cases'] = ['trial_narrow']
        problems, checked = evaluate_plan(self.plan, self.required, self.coverage)
        self.assertEqual(problems, [])
        self.assertEqual(checked, self.required)
        self.coverage['checked_visual_case_ids'] = ['trial_narrow']
        problems, checked = evaluate_plan(self.plan, self.required, self.coverage)
        self.assertTrue(any('trial_tall' in p for p in problems))
        self.assertEqual(checked, [])

    def test_each_actual_check_boundary_is_required(self):
        for key in ('current', 'passed', 'capture_verified'):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan['first_piece'][key] = False
                self.assertTrue(evaluate_plan(plan, self.required, self.coverage)[0])

    def test_visual_and_capture_namespaces_are_mapped(self):
        self.plan['visual_to_capture']['trial_tall'] = 'trial_tall'
        self.assertTrue(evaluate_plan(self.plan, self.required, self.coverage)[0])

    def test_stale_capture_refuses_even_when_first_piece_says_pass(self):
        self.plan['capture_plan']['cases'][1]['action'] = 'recapture'
        self.assertTrue(evaluate_plan(self.plan, self.required, self.coverage)[0])

    def test_owning_checker_findings_are_not_erased(self):
        self.plan['issues'] = [{'layer': 'visual', 'code': 'text_outside_plate'}]
        self.assertTrue(evaluate_plan(self.plan, self.required, self.coverage)[0])

    def test_missing_collector_is_not_visual_approval(self):
        self.plan['capture_plan'] = {'error': 'collector evidence not verified'}
        self.assertTrue(evaluate_plan(self.plan, self.required, self.coverage)[0])


class FullArtReuse(unittest.TestCase):
    """Synthetic owning-output fixtures exercise binding refusal, never game approval."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root/'project'
        (self.project/'.tiktok-kit').mkdir(parents=True)
        self.dumps = self.root/'dumps'
        self.dumps.mkdir()
        self.out = self.root/'checked'
        self.out.mkdir()
        self.required = ['ad-small', 'ad-tall']
        self.plan = dict(capture_plan=dict(round='round1', version='version1', cases=[]),
                         visual_to_capture={})
        pages, slots = [], []
        for i, case in enumerate(self.required):
            identifier = 'capture-'+str(i)
            origin = 'original-'+str(i)
            self.plan['visual_to_capture'][case] = identifier
            self.plan['capture_plan']['cases'].append(dict(id=identifier, action='fresh', origin=origin))
            dump = self.dumps/('capture-ui-dump-'+identifier+'.json')
            dump.write_text(json.dumps(dict(art_capture_id=origin)))
            pages.append(dict(file=str(dump), problems=[]))
            slots.append(dict(id=case, passed=True, checks=[dict(passed=True, name='actual ink check')]))
        self.pages = dict(setup=[], pages=pages)
        self.slots = dict(cases=slots)
        self.report = dict(tool='art_check', board='localize', status='pass', checked=2, failed=0,
            rows=[dict(check='pixels', status='通过', log='page_richness.json'),
                  dict(check='slots', status='通过', log='visual-slots-result.json')],
            capture_round=copy.deepcopy(dict(self.plan['capture_plan'], ready=True)))
        self.save()

    def save(self):
        analysis = {}
        for name, value, checker in [('page_richness.json', self.pages, 'audit_page_richness.py'),
                                      ('visual-slots-result.json', self.slots, 'audit_art_slots.py')]:
            path = self.out/name
            path.write_text(json.dumps(value))
            analysis[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                checker_sha256=hashlib.sha256(Path(__file__).with_name(checker).read_bytes()).hexdigest())
        self.report['analysis_reports'] = analysis
        report_path = self.out/'art-check.json'
        report_path.write_text(json.dumps(self.report))
        (self.project/'.tiktok-kit/art-check-record.json').write_text(json.dumps(dict(
            kind='art-check-record', board='localize', last=dict(status='pass', scoped=[],
            report=str(report_path), report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest()))))

    def read(self):
        return full_art_coverage(self.project, self.plan, self.required, self.dumps, 'localize')

    def test_actual_bound_page_and_slot_results_cover_both_cases(self):
        result = self.read()
        self.assertTrue(result['verified'])
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['checked_visual_case_ids'], self.required)

    def test_scalar_pass_without_bound_subreports_refused(self):
        self.report['analysis_reports'] = {}
        path = self.out/'art-check.json'
        path.write_text(json.dumps(self.report))
        record_path = self.project/'.tiktok-kit/art-check-record.json'
        record = json.loads(record_path.read_text())
        record['last']['report_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        record_path.write_text(json.dumps(record))
        self.assertFalse(self.read()['verified'])

    def test_tampered_subreport_and_checker_rule_refused(self):
        path = self.out/'page_richness.json'
        path.write_text('{"passed":true}')
        self.assertFalse(self.read()['verified'])
        self.save()
        self.report['analysis_reports']['page_richness.json']['checker_sha256'] = '0'*64
        path = self.out/'art-check.json'
        path.write_text(json.dumps(self.report))
        record_path = self.project/'.tiktok-kit/art-check-record.json'
        record = json.loads(record_path.read_text())
        record['last']['report_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        record_path.write_text(json.dumps(record))
        self.assertFalse(self.read()['verified'])

    def test_malformed_bound_analysis_is_refused_without_crashing(self):
        self.pages['pages'] = [True]
        self.save()
        result = self.read()
        self.assertFalse(result['verified'])
        self.assertTrue(result['problems'])

    def test_missing_case_lists_precise_gap_without_discarding_other_case(self):
        self.pages['pages'].pop()
        self.save()
        result = self.read()
        self.assertEqual(result['checked_visual_case_ids'], ['ad-small'])
        self.assertTrue(any(p.startswith('ad-tall:') for p in result['problems']))

    def test_real_case_failure_not_hidden_by_full_pass_scalar(self):
        self.pages['pages'][1]['problems'] = ['overlap']
        self.save()
        self.assertTrue(any(p.startswith('ad-tall:') for p in self.read()['problems']))

    def test_inherited_quality_reference_keeps_original_page_and_sha(self):
        record = json.loads((self.project/'.tiktok-kit/art-check-record.json').read_text())
        old = record['last']
        self.plan['capture_plan'].update(round='later-round', version='later-version',
            quality_refs=[dict(path=old['report'], sha256=old['report_sha256'], original_passed=False)],
            quality_promoted=False,
            resolved_dumps=[str(self.dumps/('capture-ui-dump-capture-'+str(i)+'.json')) for i in range(2)])
        result = self.read()
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['report_sha256'], old['report_sha256'])
        self.plan['capture_plan']['quality_refs'][0]['sha256'] = '0'*64
        self.assertFalse(self.read()['verified'])

    def test_capture_origin_version_and_changed_dump_refused(self):
        for mutate in [lambda: self.plan['capture_plan'].update(version='new'),
                       lambda: self.plan['capture_plan']['cases'][1].update(origin='changed'),
                       lambda: (self.dumps/'capture-ui-dump-capture-1.json').write_text('{"art_capture_id":"wrong"}')]:
            self.setUp()
            mutate()
            self.assertTrue(self.read()['problems'])


if __name__ == '__main__':
    unittest.main()
