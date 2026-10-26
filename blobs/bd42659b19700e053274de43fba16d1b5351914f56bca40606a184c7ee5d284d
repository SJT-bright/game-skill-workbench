#!/usr/bin/env python3
"""Synthetic rejection tests only; never gameplay/device evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_loading_recovery import SCENARIOS, RETRY, validate, POLICY_VERSION
from check_known_issues import auto_reports


class RecoveryGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='loading-gate-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        evidence = self.base / 'synthetic.txt'
        evidence.write_text('Synthetic gate fixture only, never game evidence.')
        self.binding = {k: 'synthetic-' + k for k in ('source_sha256', 'native_tree_sha256', 'web_tree_sha256', 'build_tag')}
        self.data = dict(binding=self.binding, producer='real_browser_touch_trace', viewports=[[390, 844], [360, 640]],
                         image_format_change=False, native_boundary_verified=True, native_boundary_description='Synthetic adapter boundary',
                         raw_evidence=[dict(path=evidence.name, sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())],
                         calibration=dict(old_failed=True, fixed_passed=True, evidence_refs=[0]), cases=[])
        for scenario, fields in SCENARIOS.items():
            row = dict(scenario=scenario, evidence_refs=[0], injection_boundary='synthetic SDK', production_code_unchanged=True,
                       trusted_touch=True, interaction_effect='synthetic moves 0 to 1', **{k: True for k in fields})
            if scenario == 'image_inflight_retry':
                row.update(retry_gesture_count=1, manual_intervention=False, request_count_before=1, request_count_after=2, resource_id='/same/image.png')
            if scenario in RETRY:
                row['events'] = [dict(kind=k, t_ms=t, request_id=req, trusted_touch=True, effect='synthetic move') for k, t, req in (
                    ('request', 0, 'old'), ('retry_visible', 10000, 'old'), ('retry_touch', 10100, 'old'),
                    ('new_request', 10101, 'new'), ('ready', 10200, 'new'), ('input_effect', 10300, 'new'))]
            row.update(observed_viewports=[[390, 844], [360, 640]], idle_budget_ms=10000, last_progress_ms=0)
            self.data['cases'].append(row)

    def test_main_gate_reopens_evidence_not_pass_stamp(self):
        runtime = self.base / 'runtime-current.json'
        runtime.write_text(json.dumps(self.data))
        report = self.base / 'report-current.json'
        report.write_text(json.dumps(dict(tool='audit_loading_recovery', policy_version=POLICY_VERSION, binding=self.binding, stage='runtime', checked=len(SCENARIOS), passed=True, failed=0, runtime_file=str(runtime), runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest())))
        item = dict(id='LOAD-03', auto_check=['audit_loading_recovery'])
        row = dict(auto_reports=[dict(path=str(report), sha256=hashlib.sha256(report.read_bytes()).hexdigest())])
        errors=[]
        auto_reports(item,row,self.base,errors,self.binding)
        self.assertFalse(errors)
        (self.base / 'synthetic.txt').write_text('changed after pass')
        errors=[]
        auto_reports(item,row,self.base,errors,self.binding)
        self.assertTrue(errors)

    def test_duplicate_retry_event_rejected(self):
        def mutate(d):
            row=next(r for r in d['cases'] if r['scenario']=='image_inflight_retry')
            row['events'].append(dict(kind='retry_touch',t_ms=10150,trusted_touch=True))
        self.assertTrue(self.errors(mutate))

    def test_second_manual_retry_rejected(self):
        self.assertTrue(self.errors(lambda d: next(r for r in d['cases'] if r['scenario']=='image_inflight_retry').update(retry_gesture_count=2)))

    def test_relabelled_execution_rejected(self):
        self.assertTrue(self.errors(lambda d: d.update(execution_binding={'source_sha256':'old'})))

    def test_header_viewports_are_not_observations(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0].update(observed_viewports=[])))

    def test_codec_encoding_is_not_decode(self):
        self.assertTrue(self.errors(lambda d: d.update(image_format_change=True)))

    def test_unchanged_format_cannot_skip_claimed_codec_reference_validation(self):
        self.assertTrue(self.errors(lambda d: d.update(image_format_change=False, native_codec_verified=True, codec_evidence_refs=[999])))

    def test_manual_rescue_rejected(self):
        self.assertTrue(self.errors(lambda d: next(r for r in d['cases'] if r['scenario']=='image_inflight_retry').update(manual_intervention=True)))

    def errors(self, mutate=None):
        d = deepcopy(self.data)
        if mutate:
            mutate(d)
        return validate(d, self.binding, self.base)

    def test_valid_synthetic_schema(self):
        self.assertEqual([], self.errors())

    def test_every_missing_case_rejected(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertTrue(self.errors(lambda d: d.update(cases=[r for r in d['cases'] if r['scenario'] != scenario])))

    def test_every_failed_condition_rejected(self):
        for index, (scenario, fields) in enumerate(SCENARIOS.items()):
            for field in fields:
                with self.subTest(scenario=scenario, field=field):
                    self.assertTrue(self.errors(lambda d: d['cases'][index].update({field: False})))

    def test_previous_ten_case_report_rejected(self):
        self.assertTrue(self.errors(lambda d: d.update(cases=[r for r in d['cases'] if r['scenario'] not in {'optional_font', 'request_local_clock'}])))

    def test_main_gate_rejects_old_ten_case_pass(self):
        path = self.base / 'old-ten.json'
        path.write_text(json.dumps(dict(tool='audit_loading_recovery', binding=self.binding, stage='runtime', checked=10, failed=0, passed=True)))
        row = dict(auto_reports=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())])
        errors = []
        auto_reports(dict(id='LOAD-03', auto_check=['audit_loading_recovery']), row, self.base, errors, self.binding)
        self.assertTrue(errors)

    def test_image_retry_without_new_underlying_request(self):
        self.assertTrue(self.errors(lambda d: next(r for r in d['cases'] if r['scenario'] == 'image_inflight_retry').update(request_count_after=1)))

    def test_image_retry_missing_resource_identity(self):
        self.assertTrue(self.errors(lambda d: next(r for r in d['cases'] if r['scenario'] == 'image_inflight_retry').update(resource_id='')))

    def test_abandoned_request_reuse(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][3].update(request_id='old')))

    def test_ready_from_old_request(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][4].update(request_id='old')))

    def test_no_actual_input(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][-1].update(trusted_touch=False)))

    def test_no_input_effect(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][-1].update(effect='')))

    def test_unbounded_retry(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][1].update(t_ms=15000)))

    def test_premature_timeout(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0]['events'][1].update(t_ms=100)))

    def test_missing_trace(self):
        self.assertTrue(self.errors(lambda d: d['cases'][0].update(events=[])))

    def test_stale_binding(self):
        self.assertTrue(self.errors(lambda d: d.update(binding={'build_tag': 'old'})))

    def test_no_raw_evidence(self):
        self.assertTrue(self.errors(lambda d: d.update(raw_evidence=[])))

    def test_changed_evidence(self):
        (self.base / 'synthetic.txt').write_text('changed')
        self.assertTrue(self.errors())

    def test_no_native_boundary(self):
        self.assertTrue(self.errors(lambda d: d.update(native_boundary_verified=False)))

    def test_source_only(self):
        self.assertTrue(self.errors(lambda d: d.update(producer='source_scan')))

    def test_missing_normal_control_effect(self):
        self.assertTrue(self.errors(lambda d: d['cases'][-1].update(interaction_effect='')))

    def test_no_calibration(self):
        self.assertTrue(self.errors(lambda d: d.update(calibration={})))

    def test_single_aspect_ratio(self):
        self.assertTrue(self.errors(lambda d: d.update(viewports=[[390, 844]])))

    def test_main_gate_requires_runtime_report(self):
        item = dict(id='LOAD-03', auto_check=['audit_loading_recovery'])
        errors = []
        auto_reports(item, {}, self.base, errors, self.binding)
        self.assertTrue(errors)
        path = self.base / 'audit.json'
        report = dict(tool='audit_loading_recovery', policy_version=POLICY_VERSION, binding=self.binding, stage='source_only', checked=len(SCENARIOS), failed=0, passed=True)
        for stage, allowed in [('source_only', False), ('runtime', True)]:
            report['stage'] = stage
            runtime_path = self.base / 'runtime.json'
            runtime_path.write_text(json.dumps(self.data))
            report['runtime_file'] = str(runtime_path)
            report['runtime_sha256'] = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
            path.write_text(json.dumps(report))
            row = dict(auto_reports=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())])
            errors = []
            auto_reports(item, row, self.base, errors, self.binding)
            self.assertEqual(not errors, allowed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
