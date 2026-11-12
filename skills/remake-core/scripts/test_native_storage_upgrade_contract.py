#!/usr/bin/env python3
"""Schema/consumer unit fixtures, not Cocos, phone, SDK or actual game acceptance."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

# A staged test may borrow unchanged installed dependencies; never copy them
# into the patch or modify the installation while evaluating a candidate.
HERE = Path(__file__).resolve().parent
DEPENDENCIES = os.environ.get('SKILL_TEST_DEPS')
if DEPENDENCIES:
    sys.path.insert(1, str(Path(DEPENDENCIES).resolve()))
import audit_native_storage_contract as contract
import check_known_issues as consumer
import maintenance_scope


def business():
    return {'fixture_case': 'legacy_numeric_nonbinary_typed', 'business': {
        'home': {'visible': True, 'required_assets_ready': True, 'loading_overlay_gone': True,
                 'play_interactable': True, 'node_path': 'Root/Home', 'lifecycle_complete': True,
                 'after_draw_observed': True, 'at_ms': 10},
        'play': {'touch': {'transport': 'ego_page_cdp', 'at_ms': 20}, 'level_ready': True,
                 'level_identity': 'Stage1', 'before': {'score': 0}, 'after': {'score': 1},
                 'effect_at_ms': 30}}}


def observations():
    out = {}
    for name, value in [('legacy_numeric_nonbinary_typed', 45), ('legacy_numeric_boundary_typed', 0),
                        ('legacy_unreadable_preserved', 45)]:
        key = 'ProjectSpecific.Number'  # deliberately not Coin
        row = {'key': key, 'fixture_installed_before_entry': True,
               'storage_before': {key: value, 'unrelated': 'keep'},
               'storage_after': {key: str(value), 'unrelated': 'keep'},
               'sync_read': {'type': 'boolean', 'value': value != 0},
               'async_read': {'type': 'number', 'value': value},
               'writes': [{'key': key, 'value': str(value)}], 'removed_keys': [],
               'first_exception': None}
        if name == 'legacy_unreadable_preserved':
            row.update(storage_after=copy.deepcopy(row['storage_before']), writes=[],
                       async_read={'status': 'unreadable'}, recovery_feedback_visible=True,
                       loading_overlay_visible=False, retry_or_exit_available=True)
        out[name] = row
    out['legacy_upgrade_touch_play'] = business()
    return out


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='storage-upgrade-schema-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.native = self.root / 'Native'; self.native.mkdir()
        # Keep real JS parseable; the explicit synthetic runner payload is JSON.
        (self.native / 'game.js').write_text('// Native boundary fixture; no raw storage consumers\n')
        self.runner = self.root / 'synthetic_runner.py'
        self.runner.write_text('import argparse,hashlib,json\np=argparse.ArgumentParser();p.add_argument("--bundle");p.add_argument("--adapter");a=p.parse_args()\nh=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()\nr=json.load(open(a.bundle));r.update(runner_sha256=h(__file__),bundle_sha256=h(a.bundle),adapter_sha256=h(a.adapter));print(json.dumps(r))\n')
        self.raw = {'cases': {k: 'pass' for k in contract.CASES}, 'upgrade_observations': observations()}
        old = {'cases': {'missing_empty_string': 'fail'}}
        upgrade = copy.deepcopy(self.raw); upgrade['cases']['legacy_numeric_nonbinary_typed'] = 'fail'
        upgrade['upgrade_observations']['legacy_numeric_nonbinary_typed'].update(
            storage_after={'ProjectSpecific.Number': '0', 'unrelated': 'keep'},
            failure_kind='legacy_numeric_bridge', first_exception='type mismatch', loading_overlay_visible=True)
        self.trace = {'schema': 'native_storage_trace.v3', 'trace_base': str(self.root),
                      'project': str(self.root), 'execution': {'runner': str(self.runner),
                      'runner_sha256': contract.digest(self.runner), 'dependencies': [],
                      'command': [sys.executable, str(self.runner), '--bundle', '{bundle}', '--adapter', '{adapter}']}}
        for key, name, value in [('current', 'Native/storage-fixture.json', self.raw),
                                 ('negative_control', 'old.json', old),
                                 ('upgrade_negative_control', 'upgrade-old.json', upgrade)]:
            path = self.root / name; path.write_text(json.dumps(value))
            self.trace[key] = self.record(path, key)
        self.binding = {'native_tree_sha256': consumer.tree_sha(self.native)}
        self.trace['binding'] = self.binding
        routes = {'routes': {k: {'present': True} for k in ('home', 'map', 'stage_details')}}
        # Explicit unit boundary: unchanged source/GUI route inventory has its own
        # suite. The storage raw validator, byte bindings and runner replay are real.
        self.route_patch = patch.object(maintenance_scope, 'source_inventory', return_value=routes)
        self.route_patch.start(); self.addCleanup(self.route_patch.stop)

    def record(self, path, name):
        raw = self.root / (name + '-raw.json')
        r = subprocess.run([sys.executable, str(self.runner), '--bundle', str(path), '--adapter', str(path)],
                           capture_output=True, text=True, check=True)
        raw.write_text(r.stdout)
        return {'bundle': str(path), 'bundle_sha256': contract.digest(path), 'adapter': str(path),
                'adapter_sha256': contract.digest(path), 'raw_report': str(raw), 'raw_sha256': contract.digest(raw),
                'kind': 'historical_release', 'provenance': {'path': str(path), 'sha256': contract.digest(path)}}

    def change(self, fn, which='current'):
        path = Path(self.trace[which]['bundle']); value = json.loads(path.read_text()); fn(value)
        path.write_text(json.dumps(value)); self.trace[which] = self.record(path, which)
        self.binding['native_tree_sha256'] = consumer.tree_sha(self.native)

    def validate(self):
        return contract.validate(self.trace, self.native, self.binding)

    def accept_consumer(self, version=3):
        trace_path = self.root / 'trace.json'; trace_path.write_text(json.dumps(self.trace))
        report = self.root / 'report.json'
        approval = contract.approve_runtime(self.trace, self.native, self.binding)
        approval.update(policy_version=version, trace=str(trace_path), trace_sha256=contract.digest(trace_path))
        report.write_text(json.dumps(approval))
        errors = []
        consumer.auto_reports({'id': 'STORAGE-01', 'auto_check': ['audit_native_storage_contract']},
                              {'auto_reports': [{'path': str(report), 'sha256': contract.digest(report)}]},
                              self.root, errors, self.binding)
        return not errors

    def enable_json_only(self):
        def current(r):
            for name in contract.UPGRADE_CASES[:2]:
                r['cases'][name] = 'not_applicable'
                r['upgrade_observations'].pop(name)
            r['upgrade_observations']['legacy_upgrade_touch_play']['fixture_case'] = 'valid_legacy_record'
            r['upgrade_observations']['valid_legacy_record'] = {
                'key': 'save', 'fixture_installed_before_entry': True,
                'storage_before': {'save': '{"schema":1,"coins":45}'},
                'storage_after': {'save': '{"schema":1,"coins":45}'}}
            r['upgrade_observations']['legacy_unreadable_preserved'] = {
                'key': 'save', 'fixture_installed_before_entry': True,
                'storage_before': {'save': '{"schema":1,"coins":45}'},
                'storage_after': {'save': '{"schema":1,"coins":45}'},
                'sync_read': {'type': 'boolean', 'value': True}, 'async_read': {'status': 'unreadable'},
                'writes': [], 'removed_keys': [], 'recovery_feedback_visible': True,
                'loading_overlay_visible': False, 'retry_or_exit_available': True}
        self.change(current)
        def negative(r):
            r['cases'] = {'json_unreadable_preserved': 'fail'}
            r['upgrade_observations'] = {'json_unreadable_preserved': {
                'key': 'save', 'fixture_installed_before_entry': True,
                'storage_before': {'save': '{"schema":1,"coins":45}'}, 'storage_after': {'save': '{}'},
                'sync_read': {'type': 'boolean', 'value': True},
                'failure_kind': 'existing_json_silently_reset'}}
        self.change(negative, 'upgrade_negative_control')
        assets = self.root / 'assets'; assets.mkdir()
        source = assets / 'store.js'; source.write_text('var a=storage.getItem("save"); storage.setItem("save",JSON.stringify(data));')
        schema = self.root / 'schema.json'; schema.write_text(json.dumps({'schema': 'storage_value_schema.v1',
            'fields': {'save': {'encoding': 'json_object', 'legacy_encodings': ['json_object']}}}))
        inventory = self.root / 'accesses.json'; ref = {'path': str(source), 'sha256': contract.digest(source)}
        inventory.write_text(json.dumps({'schema': 'storage_access_inventory.v1', 'binding': self.binding,
            'schema_sha256': contract.digest(schema), 'complete': True, 'unknown_or_dynamic_keys': [],
            'keys': [{'key': 'save', 'read': [{'source': ref, 'expression': 'storage.getItem("save")'}],
                     'write': [{'source': ref, 'expression': 'storage.setItem("save",JSON.stringify(data))'}]}]}))
        self.trace['numeric_scope'] = {'mode': 'json_only',
            'schema': {'path': str(schema), 'sha256': contract.digest(schema)},
            'access_inventory': {'path': str(inventory), 'sha256': contract.digest(inventory)}}

    def test_json_only_evidenced_scope_and_consumer(self):
        self.enable_json_only()
        self.assertEqual(self.validate(), [])
        self.assertEqual(contract.replay(self.trace), [])
        self.assertTrue(self.accept_consumer())

    def test_json_only_reason_without_actual_schema_refused(self):
        self.trace['numeric_scope'] = {'mode': 'json_only', 'reason': 'no numeric fields'}
        self.assertTrue(any('numeric_not_applicable refused' in e for e in self.validate()))

    def test_json_only_primitive_legacy_schema_refused(self):
        self.enable_json_only()
        ref = self.trace['numeric_scope']['schema']; path = Path(ref['path']); value = json.loads(path.read_text())
        value['fields']['save']['legacy_encodings'] = ['number']; path.write_text(json.dumps(value))
        ref['sha256'] = contract.digest(path)
        self.assertTrue(any('every current and legacy field' in e for e in self.validate()))

    def test_json_only_changed_source_refused(self):
        self.enable_json_only()
        (self.root / 'assets/store.js').write_text('changed')
        self.assertTrue(any('numeric_not_applicable refused' in e for e in self.validate()))

    def test_fractional_schema_value_and_boundary_one(self):
        def adjust(r):
            for name, value, text in [('legacy_numeric_nonbinary_typed', 0.7, '0.70'),
                                      ('legacy_numeric_boundary_typed', 1, '1')]:
                row = r['upgrade_observations'][name]
                row.update(expected_numeric=value, expected_text=text)
                row['storage_before'][row['key']] = value
                row['storage_after'][row['key']] = text
                row['async_read'] = {'type': 'number', 'value': value}
                row['writes'] = [{'key': row['key'], 'value': text}]
        self.change(adjust)
        def adjust_negative(r):
            row = r['upgrade_observations']['legacy_numeric_nonbinary_typed']
            row.update(expected_numeric=0.7, expected_text='0.70')
            row['storage_before'][row['key']] = 0.7
        self.change(adjust_negative, 'upgrade_negative_control')
        self.assertEqual(self.validate(), [])
        self.assertTrue(self.accept_consumer())

    def test_expected_numeric_bool_and_infinite_refused(self):
        for value in (True, float('inf')):
            self.change(lambda r: r['upgrade_observations']['legacy_numeric_boundary_typed'].update(
                expected_numeric=value))
            self.assertTrue(any('project-valid numeric fixture' in e for e in self.validate()))

    def test_valid_v3_and_actual_consumer(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(contract.replay(self.trace), [])
        self.assertTrue(self.accept_consumer())

    def test_v1_and_v2_need_upgrade_and_consumer_refuses(self):
        for schema in ('native_storage_trace.v1', 'native_storage_trace.v2'):
            self.trace['schema'] = schema
            self.assertTrue(any('needs_upgrade' in e for e in self.validate()))
            self.assertFalse(self.accept_consumer(version=int(schema[-1])))

    def test_missing_case_rejected(self):
        self.change(lambda r: r['cases'].pop('legacy_numeric_nonbinary_typed'))
        self.assertTrue(self.validate()); self.assertFalse(self.accept_consumer())

    def test_forged_typed_boolean_rejected(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_boundary_typed'].update(
            async_read={'type': 'number', 'value': False}))
        self.assertTrue(any('typed async' in e for e in self.validate()))

    def test_declared_type_must_match_observed_type(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_nonbinary_typed'].update(
            async_read={'type': 'number', 'value': '45'}))
        self.assertTrue(any('typed async' in e for e in self.validate()))

    def test_exact_original_must_not_reset(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_nonbinary_typed']['storage_after'].update(
            {'ProjectSpecific.Number': '0'}))
        self.assertTrue(any('default reset' in e for e in self.validate()))

    def test_unreadable_original_cannot_overwrite(self):
        self.change(lambda r: r['upgrade_observations']['legacy_unreadable_preserved'].update(
            writes=[{'key': 'ProjectSpecific.Number', 'value': '0'}]))
        self.assertTrue(any('unreadable data' in e for e in self.validate()))

    def test_play_must_have_touch_business_result(self):
        self.change(lambda r: r['upgrade_observations']['legacy_upgrade_touch_play']['business']['play'].update(
            after={'score': 0}))
        self.assertTrue(any('gameplay change' in e for e in self.validate()))

    def test_label_only_negative_is_not_failure(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_nonbinary_typed'].update(
            storage_after={'ProjectSpecific.Number': '45', 'unrelated': 'keep'}, first_exception=None),
                    'upgrade_negative_control')
        self.assertTrue(any('did not reproduce' in e for e in self.validate()))

    def test_negative_must_use_same_runner(self):
        raw = Path(self.trace['upgrade_negative_control']['raw_report'])
        value = json.loads(raw.read_text()); value['runner_sha256'] = '0' * 64; raw.write_text(json.dumps(value))
        self.trace['upgrade_negative_control']['raw_sha256'] = contract.digest(raw)
        self.assertTrue(any('identity mismatch' in e for e in self.validate()))

    def test_raw_stamp_not_matching_reexecution_refused(self):
        raw = Path(self.trace['current']['raw_report'])
        value = json.loads(raw.read_text()); value['fake'] = True; raw.write_text(json.dumps(value))
        self.trace['current']['raw_sha256'] = contract.digest(raw)
        self.assertTrue(contract.replay(self.trace))
        self.assertFalse(self.accept_consumer())

    def test_missing_empty_string_negative_still_required(self):
        self.change(lambda r: r['cases'].update(missing_empty_string='pass'), 'negative_control')
        self.assertTrue(any('missing-empty-string' in e for e in self.validate()))

    def test_preentry_fixture_required(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_nonbinary_typed'].update(
            fixture_installed_before_entry=False))
        self.assertTrue(any('precede Native entry' in e for e in self.validate()))

    def enable_non_numeric(self, encoding='boolean', value=True, source_dir='packages'):
        self.enable_json_only()
        self.trace['numeric_scope']['mode'] = 'schema_backed_non_numeric'
        schema_path = Path(self.trace['numeric_scope']['schema']['path'])
        schema = json.loads(schema_path.read_text())
        schema['fields']['save'] = {'encoding': encoding, 'legacy_encodings': [encoding]}
        schema_path.write_text(json.dumps(schema)); self.trace['numeric_scope']['schema']['sha256'] = contract.digest(schema_path)
        def current(r):
            for name in ('valid_legacy_record', 'legacy_unreadable_preserved'):
                r['upgrade_observations'][name]['storage_before'] = {'save': value}
                r['upgrade_observations'][name]['storage_after'] = {'save': value}
        self.change(current)
        def negative(r):
            row = r['upgrade_observations'].pop('json_unreadable_preserved')
            row['storage_before'] = {'save': value}; row['storage_after'] = {'save': 'WRONG_RESET'}
            row['failure_kind'] = 'existing_non_numeric_silently_reset'
            r['upgrade_observations']['non_numeric_unreadable_preserved'] = row
            r['cases'] = {'non_numeric_unreadable_preserved': 'fail'}
        self.change(negative, 'upgrade_negative_control')
        source = self.root / source_dir / 'storage.js'; source.parent.mkdir(exist_ok=True)
        source.write_text('var a=storage.getItem("save"); storage.setItem("save",data);')
        inventory_path = Path(self.trace['numeric_scope']['access_inventory']['path']); inventory = json.loads(inventory_path.read_text())
        inventory.update(binding=self.binding, schema_sha256=contract.digest(schema_path))
        inventory['keys'] = [{'key': 'save', 'read': [{'source': {'path': str(source), 'sha256': contract.digest(source)}, 'expression': 'storage.getItem("save")'}],
                              'write': [{'source': {'path': str(source), 'sha256': contract.digest(source)}, 'expression': 'storage.setItem("save",data)'}]}]
        inventory_path.write_text(json.dumps(inventory)); self.trace['numeric_scope']['access_inventory']['sha256'] = contract.digest(inventory_path)

    def test_boolean_only_schema_in_packages(self):
        self.enable_non_numeric('boolean', False)
        self.assertEqual(self.validate(), []); self.assertTrue(self.accept_consumer())

    def test_string_only_schema_in_build_templates(self):
        self.enable_non_numeric('string', 'keep me', 'build-templates')
        self.assertEqual(self.validate(), []); self.assertTrue(self.accept_consumer())

    def test_boolean_legacy_to_text_preserves_semantics(self):
        self.enable_non_numeric('boolean', False)
        self.change(lambda r: r['upgrade_observations']['valid_legacy_record']['storage_after'].update(save='false'))
        # Source-bound inventory binding is refreshed by the existing fixture recorder.
        inventory_path=Path(self.trace['numeric_scope']['access_inventory']['path'])
        inventory=json.loads(inventory_path.read_text());inventory['binding']=self.binding
        inventory_path.write_text(json.dumps(inventory));self.trace['numeric_scope']['access_inventory']['sha256']=contract.digest(inventory_path)
        self.assertEqual(self.validate(), []);self.assertTrue(self.accept_consumer())

    def test_non_numeric_unreadable_case_cannot_opt_out(self):
        self.enable_json_only()
        self.change(lambda r: r['cases'].update(legacy_unreadable_preserved='not_applicable'))
        self.assertTrue(self.validate())

    def test_huge_numeric_fixture_is_rejected_without_overflow(self):
        self.change(lambda r: r['upgrade_observations']['legacy_numeric_nonbinary_typed'].update(expected_numeric=10**2000))
        self.assertTrue(self.validate())

    def test_current_raw_missing_is_diagnostic(self):
        self.trace['current'].pop('raw_report')
        self.assertTrue(self.validate())

    def test_malformed_current_record_is_diagnostic(self):
        self.trace['current'] = []
        self.assertTrue(self.validate())

    def test_malformed_current_paths_are_diagnostic(self):
        self.trace['current']['raw_report'] = None
        self.assertTrue(self.validate())

    def report_file(self):
        trace_path = self.root / 'trace.json'; trace_path.write_text(json.dumps(self.trace))
        approved = contract.approve_runtime(self.trace, self.native, self.binding)
        self.assertTrue(approved['passed'], approved['errors'])
        approved.update(trace=str(trace_path), trace_sha256=contract.digest(trace_path))
        path = self.root / 'approved.json'; path.write_text(json.dumps(approved))
        return path

    def consume_report(self, path):
        errors = []
        consumer.auto_reports({'id':'STORAGE-01','auto_check':['audit_native_storage_contract']},
                              {'auto_reports':[{'path':str(path),'sha256':contract.digest(path)}]},
                              self.root,errors,self.binding)
        return errors

    def test_consumer_rejudges_without_execution(self):
        path = self.report_file()
        with patch.object(contract,'replay', side_effect=AssertionError('must not rerun')):
            self.assertEqual(self.consume_report(path), [])

    def test_missing_receipt_is_not_a_pass(self):
        path = self.report_file(); report=json.loads(path.read_text()); report.pop('execution_receipt'); path.write_text(json.dumps(report))
        self.assertTrue(self.consume_report(path))

    def test_changed_runner_dependency_invalidates_receipt(self):
        dependency=self.root/'host.js';dependency.write_text('current host')
        self.trace['execution']['dependencies']=[{'path':str(dependency),'sha256':contract.digest(dependency)}]
        path=self.report_file();dependency.write_text('new host')
        self.assertTrue(self.consume_report(path))

    def test_changed_raw_invalidates_receipt_without_execution(self):
        path=self.report_file();raw=Path(self.trace['current']['raw_report']); raw.write_text('{}')
        self.assertTrue(self.consume_report(path))

    def test_missing_dependencies_is_refused(self):
        self.trace['execution'].pop('dependencies')
        self.assertTrue(self.validate())

if __name__ == '__main__':
    unittest.main(verbosity=2)
