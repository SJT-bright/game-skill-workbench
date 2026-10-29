#!/usr/bin/env python3
"""Synthetic validator/scanner tests, not game QA. Leaves no fixture behind."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import logic_check
import logic_regressions as reg
from test_button_state_check import save_fixture_report


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='logic-regression-selftest-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'assets/main.js').write_text('const synthetic = true;\n')
        self.evidence = self.root / 'synthetic.txt'
        self.evidence.write_text('Synthetic validator fixture; no browser or real game was run.\n')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('logic_check.py')),
                               '--project', str(self.root), *args], capture_output=True, text=True)

    def doc(self):
        rows = reg.templates()
        by_id = {x[0]: x for x in reg.CASES}
        for row in rows:
            spec = by_id[row['id']]
            row.update(status='pass', layer=spec[3][0],
                       observations={key: 'Synthetic observation for ' + key + '; validator test only' for key in spec[4]},
                       evidence=[{'path': 'synthetic.txt', 'sha256': hashlib.sha256(self.evidence.read_bytes()).hexdigest()}])
            if row['id'] == 'R07':
                row.update(drag_applicable=False, drag_absence_reason='Synthetic constant-only fixture has no drag mechanism')
            if row['id'] == 'R09':
                row['audio_channels'] = ['music', 'sfx']
                row['audio_samples'] = [dict(viewport=view, channel=channel, mode=mode,
                    signal_id='synthetic fixed segment ' + channel, trusted_touch=True,
                    rms_samples=[{'zero':0., 'mid':.05, 'full':.1, 'off':0., 'on':.1}[mode]] * 3)
                    for view in ([390,844], [375,667]) for channel in ('music','sfx')
                    for mode in ('zero','mid','full','off','on')]
            if row['id'] == 'R06':
                row['button_check'] = save_fixture_report(self.root)
        return {'schema': 'logic_flows.v1',
                'flows': [{'id': i, 'status': 'n/a', 'note': 'Synthetic CLI acceptance fixture only'} for i, *_ in logic_check.FLOWS],
                'regression_binding': {'source_sha256': reg.source_digest(self.root)}, 'regressions': rows}

    def errors(self, doc):
        return reg.validate(doc, self.root, reg.source_digest(self.root))[1]

    def write_doc(self, doc):
        p = self.root / 'docs/logic/flows.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc))
        return p

    def test_detects_negative_remainder_and_preserves_line(self):
        findings = reg.static_suspects([('assets/list.ts', '// line one\nconst item = items[(index + items.length) % items.length];')])
        self.assertEqual((findings[0]['rule'], findings[0]['line']), ('L-CYCLIC', 2))

    def test_normalized_modulo_not_flagged(self):
        for expr in ['((index % n) + n) % n', '((index + n) % n + n) % n']:
            self.assertFalse(reg.static_suspects([('assets/list.ts', 'const i = ' + expr)]))

    def test_whole_json_state_writer_not_memory_only_failure(self):
        (self.root / 'assets/main.js').write_text('const defaults = {musicOn:true};\nfunction save(s) { const text=JSON.stringify(s); localStorage.setItem(KEY,text); }')
        findings, _ = logic_check.scan(self.root)
        sound = [f for f in findings if f['rule'] == 'L-SAVE' and 'musicOn' in f['message']]
        self.assertTrue(sound)
        self.assertEqual(sound[0]['severity'], 'hint')
        self.assertNotIn('only lives in memory', sound[0]['message'])

    def test_read_and_loading_patterns_remain_suspects(self):
        code = 'const s=JSON.parse(storage.getItem(KEY)); setInterval(check,250); resources.load(name,cb);'
        self.assertEqual({f['rule'] for f in reg.static_suspects([('assets/io.js', code)])},
                         {'L-SAVE-RECOVERY', 'L-LOAD-RETRY'})

    def test_init_adds_current_untested_cases(self):
        result = self.run_cli('--init')
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads((self.root / 'docs/logic/flows.json').read_text())
        self.assertEqual(len(doc['regressions']), len(reg.CASES))
        self.assertEqual({r['status'] for r in doc['regressions']}, {'untested'})

    def test_init_migrates_old_record_without_resetting_or_rebinding(self):
        doc = self.doc()
        doc['regressions'] = doc['regressions'][:1]
        p = self.write_doc(doc)
        before = doc['regression_binding']
        (self.root / 'assets/main.js').write_text('const changed = true;')
        result = self.run_cli('--init')
        self.assertEqual(result.returncode, 0, result.stderr)
        got = json.loads(p.read_text())
        self.assertEqual(got['flows'], doc['flows'])
        self.assertEqual(got['regressions'][0], doc['regressions'][0])
        self.assertEqual(got['regression_binding'], before)
        self.assertEqual(len(got['regressions']), len(reg.CASES))
        self.assertTrue(self.errors(got))

    def test_init_idempotent(self):
        self.run_cli('--init')
        p = self.root / 'docs/logic/flows.json'
        first = p.read_bytes()
        self.run_cli('--init')
        self.assertEqual(first, p.read_bytes())

    def test_init_does_not_overwrite_malformed_records(self):
        p = self.write_doc({})
        p.write_text('{broken')
        result = self.run_cli('--init')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(p.read_text(), '{broken')

    def test_old_twenty_flows_cannot_bypass_new_cases(self):
        doc = self.doc()
        doc.pop('regressions')
        self.write_doc(doc)
        result = self.run_cli('--mode', 'build')
        report = json.loads((self.root / 'docs/logic/logic-check.json').read_text())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['regression_problems'], len(reg.CASES))
        self.assertFalse(report['passed'])

    def test_r06_missing_disabled_states_rejected(self):
        doc = self.doc()
        row = next(x for x in doc['regressions'] if x['id'] == 'R06')
        row['observations'].pop('disabled_state_outcomes')
        _, problems = reg.validate(doc, self.root, reg.source_digest(self.root))
        self.assertTrue(any('disabled_state_outcomes' in str(x) for x in problems))

    def test_r06_prose_cannot_replace_scoped_button_report(self):
        doc = self.doc()
        row = next(x for x in doc['regressions'] if x['id'] == 'R06')
        row.pop('button_check')
        row['observations']['disabled_state_outcomes'] = 'All disabled controls tested.'
        self.assertTrue(any(x['id'] == 'R06' for x in self.errors(doc)))

    def test_r06_generic_na_cannot_bypass_button_coverage(self):
        doc = self.doc()
        row = next(x for x in doc['regressions'] if x['id'] == 'R06')
        row.update(status='n/a', note='Not applicable.')
        self.assertTrue(any(x['id'] == 'R06' for x in self.errors(doc)))

    def test_complete_synthetic_records_accept_but_are_not_a_game_pass(self):
        self.assertFalse(self.errors(self.doc()))
        self.write_doc(self.doc())
        self.assertEqual(self.run_cli('--mode', 'build').returncode, 0)

    def test_main_gate_rechecks_hashed_evidence_and_legacy_report_version(self):
        self.write_doc(self.doc())
        self.run_cli('--mode', 'build')
        report = json.loads((self.root / 'docs/logic/logic-check.json').read_text())
        self.assertTrue(reg.current_report(report, self.root / 'docs/logic'))
        self.evidence.write_text('modified after report creation')
        self.assertFalse(reg.current_report(report, self.root / 'docs/logic'))
        report.pop('regression_version')
        self.assertFalse(reg.current_report(report, self.root / 'docs/logic'))

    def test_missing_observation_and_boolean_placeholder_rejected(self):
        doc = self.doc()
        row = doc['regressions'][0]
        row['observations'][next(iter(row['observations']))] = True
        self.assertTrue(self.errors(doc))
        row['observations'] = {}
        self.assertTrue(self.errors(doc))

    def test_static_layer_cannot_replace_browser_touch(self):
        doc = self.doc()
        doc['regressions'][0]['layer'] = 'source'
        self.assertTrue(self.errors(doc))

    def test_untested_and_failed_block_build(self):
        for status in ('untested', 'fail'):
            doc = self.doc()
            doc['regressions'][0]['status'] = status
            self.assertTrue(self.errors(doc))

    def test_evidence_missing_empty_directory_and_changed_rejected(self):
        doc = self.doc()
        self.evidence.write_text('changed')
        self.assertTrue(self.errors(doc))
        self.evidence.write_text('')
        self.assertTrue(self.errors(doc))
        self.evidence.unlink()
        self.assertTrue(self.errors(doc))
        doc['regressions'][0]['evidence'] = [{'path': 'assets', 'sha256': 'not-a-file'}]
        self.assertTrue(self.errors(doc))

    def test_source_and_runtime_data_change_invalidate_old_passes(self):
        doc = self.doc()
        (self.root / 'assets/levels.json').write_text('{"levels":[1,2]}')
        self.assertEqual(len(self.errors(doc)), len(reg.CASES))

    def test_duplicate_id_rejected(self):
        doc = self.doc()
        doc['regressions'].append(doc['regressions'][0].copy())
        self.assertTrue(self.errors(doc))

    def test_na_requires_reason_and_does_not_require_absent_feature(self):
        doc = self.doc()
        doc['regressions'][0] = {'id': 'R01', 'status': 'n/a', 'note': ''}
        self.assertTrue(self.errors(doc))
        doc['regressions'][0]['note'] = 'Synthetic game has no cyclic list; not a game QA conclusion'
        self.assertFalse(self.errors(doc))

    def test_review_reports_problems_without_claiming_build_pass(self):
        self.write_doc({'flows': []})
        result = self.run_cli('--mode', 'review')
        report = json.loads((self.root / 'docs/logic/logic-check.json').read_text())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report['status'], 'review')
        self.assertFalse(report['passed'])
        self.assertEqual(report['regression_problems'], len(reg.CASES))


    def test_production_touch_owner_cannot_be_omitted_from_button_plan(self):
        (self.root/'assets/input.ts').write_text('const id = event.getID(); node.on(TOUCH_START, onStart);')
        doc=self.doc()
        errors=self.errors(doc)
        self.assertTrue(any(x['id']=='R06' and 'production touch owners' in x['problem'] for x in errors),errors)

    def test_input_inventory_is_not_triggered_by_non_touch_code(self):
        (self.root/'assets/menu.ts').write_text('const touchId = 3; /* no event registration */')
        self.assertEqual(reg.input_owner_sources(self.root),[])



    def drag_doc(self):
        doc = self.doc()
        row = next(x for x in doc['regressions'] if x['id'] == 'R07')
        row.update(drag_applicable=True, drag_samples=[dict(viewport=view, kind=kind,
            trusted_touch=True, picked=True, held_after=False, before={'moves':0},
            after={'moves':1 if kind=='legal' else 0})
            for view in ([390,844], [375,667]) for kind in ('legal','system_cancel','invalid')])
        return doc, row

    def test_drag_legal_cancel_and_invalid_outcomes_accept(self):
        doc, row = self.drag_doc()
        self.assertFalse(self.errors(doc))

    def test_original_no_effect_drag_is_rejected(self):
        doc, row = self.drag_doc()
        row['drag_samples'][0]['after'] = row['drag_samples'][0]['before']
        self.assertTrue(any('no business effect' in x['problem'] for x in self.errors(doc)))

    def test_cancel_commits_and_missing_viewport_rejected(self):
        for defect in ('cancel_commit', 'one_viewport'):
            doc, row = self.drag_doc()
            if defect == 'cancel_commit': row['drag_samples'][1]['after'] = {'moves':1}
            else: row['drag_samples'] = row['drag_samples'][:3]
            self.assertTrue(any(x['id']=='R07' for x in self.errors(doc)))

    def test_legacy_pointer_observations_without_measured_effects_rejected(self):
        doc, row = self.drag_doc()
        row.pop('drag_samples')
        self.assertTrue(any(x['id']=='R07' for x in self.errors(doc)))

    def test_old_eight_regressions_migrate_r09_as_untested(self):
        doc=self.doc();doc['regressions']=[r for r in doc['regressions'] if r['id']!='R09']
        p=self.write_doc(doc);self.assertTrue(any(x['id']=='R09' for x in self.errors(doc)))
        self.assertEqual(self.run_cli('--init').returncode,0)
        got=json.loads(p.read_text());self.assertEqual(next(r for r in got['regressions'] if r['id']=='R09')['status'],'untested')
        self.assertEqual(got['regressions'][:8],doc['regressions'])

    def test_silent_and_unchanged_volume_outputs_rejected(self):
        for defect in ('silent', 'same_gain', 'no_pcm', 'nan', 'false_touch', 'different_segment'):
            doc=self.doc();row=next(x for x in doc['regressions'] if x['id']=='R09')
            if defect=='silent':
                for x in row['audio_samples']:x['rms_samples']=[0.,0.,0.]
            elif defect=='same_gain':
                for x in row['audio_samples']:
                    if x['mode']=='mid':x['rms_samples']=[.1,.1,.1]
            elif defect=='no_pcm':row.pop('audio_samples')
            elif defect=='nan':row['audio_samples'][0]['rms_samples']=[float('nan')]*3
            elif defect=='false_touch':row['audio_samples'][0]['trusted_touch']=False
            else:row['audio_samples'][1]['signal_id']='different music segment'
            self.assertTrue(any(x['id']=='R09' for x in self.errors(doc)),defect)

    def test_main_gate_rechecks_mutated_audio_measurement(self):
        self.write_doc(self.doc());self.run_cli('--mode','build')
        report=json.loads((self.root/'docs/logic/logic-check.json').read_text())
        self.assertTrue(reg.current_report(report,self.root/'docs/logic'))
        row=next(x for x in report['regressions'] if x['id']=='R09')
        row['audio_samples'][1]['rms_samples']=[0.,0.,0.]
        self.assertFalse(reg.current_report(report,self.root/'docs/logic'))

    def test_rescaled_same_aspect_ratio_cannot_count_as_two(self):
        doc, row = self.drag_doc()
        for x in row['drag_samples']:
            if x['viewport']==[375,667]: x['viewport']=[780,1688]
        self.assertTrue(any(x['id']=='R07' for x in self.errors(doc)))
        doc=self.doc();row=next(x for x in doc['regressions'] if x['id']=='R09')
        for x in row['audio_samples']:
            if x['viewport']==[375,667]: x['viewport']=[780,1688]
        self.assertTrue(any(x['id']=='R09' for x in self.errors(doc)))

    def test_malformed_effect_observations_fail_closed(self):
        for row, ident in [({'audio_channels':[{}]},'R09'),({'drag_applicable':True,'drag_samples':[{}]},'R07')]:
            self.assertTrue(reg.observable_effects(row,ident))


if __name__ == '__main__':
    unittest.main(verbosity=2)
