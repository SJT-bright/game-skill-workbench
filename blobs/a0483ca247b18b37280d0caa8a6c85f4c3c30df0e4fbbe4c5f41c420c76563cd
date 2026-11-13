"""Portable synthetic controls for one-time storage production and JSON recovery.

Actual validator, subprocess runner, immutable scope and consumer are exercised;
this is not evidence of a real game, SDK or physical-device pass.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_native_storage_contract as gate
import storage_scoped_reuse as scoped
import test_storage_scoped_reuse as scopes
import test_native_storage_upgrade_contract as fixtures


class ProducedOnceTests(unittest.TestCase):
    def setUp(self):
        self.f = scopes.StorageScope('test_in_place_nonconsumer_art_reuses_original_without_helper_or_runner')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.trace = copy.deepcopy(self.f.f.trace)
        for label in ('current', 'negative_control', 'upgrade_negative_control'):
            self.trace[label]['raw_report'] = str(self.f.root / ('produced-' + label + '.json'))
            self.trace[label].pop('raw_sha256', None)
        self.target = self.f.root / 'produced-trace.json'

    def produce(self):
        original = gate.subprocess.run
        with patch.object(gate, 'replay', side_effect=AssertionError('producer must not replay')), \
                patch.object(gate.subprocess, 'run', wraps=original) as runner:
            report = gate.produce_runtime_once(self.trace, self.f.f.native, self.f.f.binding, self.target)
        self.assertEqual(sum(str(self.f.f.runner) in call.args[0] for call in runner.call_args_list), 3)
        self.assertTrue(report['passed'], report.get('errors'))
        self.assertEqual(report['execution_receipt']['mode'], 'produced-once')
        self.assertIn('storage_scope', report, report.get('storage_scope_status'))
        self.assertEqual(gate.validate_execution_receipt(report, json.loads(self.target.read_text())), [])
        return report

    def test_final_receipt_scope_consumes_after_nonconsumer_art_without_rerunning(self):
        report = self.produce(); original = copy.deepcopy(report)
        count = self.f.counter.read_text()
        (self.f.f.native / 'icon.png').write_bytes(b'new isolated nonconsumer art')
        with patch.object(gate, 'replay', side_effect=AssertionError('consumer must not replay')), \
                patch.object(scoped, 'profile', wraps=scoped.profile):
            errors = scoped.validate_report(report, self.f.f.native, self.f.changed_binding(), project=self.f.source)
        self.assertEqual(errors, [])
        self.assertEqual(self.f.counter.read_text(), count)
        self.assertEqual(report, original)

    def test_mutated_raw_and_repeated_output_are_refused(self):
        report = self.produce()
        Path(self.trace['current']['raw_report']).write_text('{}')
        self.assertTrue(scoped.validate_report(report, self.f.f.native, self.f.f.binding, project=self.f.source))
        with patch.object(gate.subprocess, 'run', side_effect=AssertionError('no duplicate execution')):
            with self.assertRaisesRegex(ValueError, 'already exists'):
                gate.produce_runtime_once(self.trace, self.f.f.native, self.f.f.binding, self.target)


class JsonRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='json-retry-evidence-')
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name) / 'trusted-event.json'
        self.raw.write_text('{"transport":"ego_page_cdp","event":{"isTrusted":true}}')
        b = fixtures.business()['business']
        row = {'key': 'save', 'fixture_installed_before_entry': True,
            'storage_before': {'save': '{"coins":45,"nested":{"one":1}}', 'unrelated':'keep'},
            'sync_read': {'type':'boolean','value':True},
            'outcome':gate.JSON_RETRY_OUTCOME,
            'storage_after_fault': {'save': '{"coins":45,"nested":{"one":1}}', 'unrelated':'keep'},
            'writes_fault':[], 'removed_keys_fault':[], 'runtime_initialized_fault':False,
            'unsafe_grant_or_spend':False, 'first_exception':None,
            'recovery':{'visible':True,'retry_visible':True,'retry_interactable':True,'node_path':'LoadingRecovery/Retry','at_ms':1},
            'recovery_action':{'transport':'ego_page_cdp','event':{'isTrusted':True},'at_ms':3},
            'fault_observed_at_ms':0,'sdk_restored_at_ms':2,
            'storage_after_retry':{'save':'{"coins":45,"nested":{"one":1,"new":2}}','unrelated':'keep'},
            'restored_data':{'coins':45,'nested':{'one':1,'new':2}},
            'business':b,'raw_evidence':[{'path':str(self.raw),'sha256':gate.digest(self.raw)}]}
        self.result={'cases':{'legacy_unreadable_preserved':'pass'},'upgrade_observations':{
            'legacy_unreadable_preserved':row,'legacy_upgrade_touch_play':{'fixture_case':'legacy_unreadable_preserved','business':b}}}
        self.fields={'save':{'encoding':'json_object','legacy_encodings':['json_object']}}

    def test_real_ref_and_recovered_original_pass_but_early_write_untrusted_and_lost_data_fail(self):
        self.assertEqual(gate.json_retry_upgrade_errors(self.result,self.fields),[])
        for change in ('write','touch','lost','missing_ref'):
            with self.subTest(change=change):
                bad=copy.deepcopy(self.result);row=bad['upgrade_observations']['legacy_unreadable_preserved']
                if change=='write':row['writes_fault']=[{'key':'save','value':'{}'}]
                elif change=='touch':row['recovery_action']['event']['isTrusted']=False
                elif change=='lost':row['restored_data']['coins']=0
                else:row['raw_evidence'][0]['sha256']='0'*64
                self.assertTrue(gate.json_retry_upgrade_errors(bad,self.fields))

    def test_negative_requires_actual_original_overwrite(self):
        bad=copy.deepcopy(self.result);bad['cases']['legacy_unreadable_preserved']='fail'
        row=bad['upgrade_observations']['legacy_unreadable_preserved']
        row['failure_kind']='unreadable_original_overwritten';row['storage_after_fault']['save']='{}';row['writes_fault']=[{'key':'save','value':'{}'}]
        self.assertEqual(gate.json_retry_upgrade_errors(bad,self.fields,negative=True),[])
        row['storage_after_fault']=copy.deepcopy(row['storage_before'])
        self.assertTrue(gate.json_retry_upgrade_errors(bad,self.fields,negative=True))

if __name__ == '__main__': unittest.main()
