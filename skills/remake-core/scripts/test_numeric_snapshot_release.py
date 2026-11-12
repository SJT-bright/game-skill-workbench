"""Numeric-codec data-contract controls; external execution/UI proofs are synthetic.

Use actual files, hashes and Acorn caller analysis. These unit observations never
establish a game, SDK, renderer or real-device pass.
"""
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_known_issues import tree_sha
from audit_native_storage_contract import BASE_CASES
import numeric_snapshot_contract as N


class NumericSnapshotControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / 'native'
        (self.native / 'assets/main').mkdir(parents=True)
        self.source = self.native / 'facade.js'
        self.source.write_text("var KEYS=['coin','music'];var OPTIONAL=['music'];var PREFIX='n:';\n"
                               "function typed(r){return r.schema==='scalar.v1';}\n"
                               "function missing(){return '';}\n")
        (self.native / 'game.js').write_text("require('./facade.js');require('./main.js');")
        (self.native / 'main.js').write_text('/* synthetic bootstrap */')
        (self.native / 'adapter.js').write_text('/* synthetic adapter */')
        (self.native / 'assets/main/index.js').write_text("store.getlocalStorageNum('coin');store.setlocalStorageNum('music',1);")
        self.binding = {'native_tree_sha256': tree_sha(self.native)}
        runner = self.root / 'unit-runner.cjs'
        runner.write_text('/* synthetic execution identity; not a game runner */')
        self.codec = self.write('codec.json', {'schema': 'numeric_snapshot_encoding.v1',
            'native_source': 'facade.js', 'keys': ['coin', 'music'], 'critical': ['coin'],
            'prefix': 'n:', 'record_schema': 'scalar.v1', 'key_field': 'key', 'value_field': 'value'})
        self.routes = {'routes': {'map': {'present': False}, 'stage_details': {'present': False}}}
        cases = {name: 'not_applicable' if name in ('reopen_map', 'reopen_stage_details') else 'pass'
                 for name in BASE_CASES}
        cases.update(legacy_numeric_nonbinary_typed='pass', legacy_numeric_boundary_typed='pass',
                     legacy_unreadable_preserved='pass', legacy_upgrade_touch_play='external_runtime')
        matrix = []
        for key in ['coin', 'music']:
            for kind, value in [('typed_boundary', 0), ('typed_nonbinary', 3),
                                ('metadata_unavailable', 1), ('unrecoverable', 3)]:
                before = {key: value, 'unrelated': 99}
                after = dict(before)
                if kind != 'unrecoverable':
                    after['n:' + key] = json.dumps({'schema': 'scalar.v1', 'key': key, 'value': value})
                matrix.append({'key': key, 'kind': kind, 'value': value, 'before': before, 'after': after,
                    'removed': [], 'writes': [], 'locked': kind == 'unrecoverable',
                    'error': 'unreadable' if kind == 'unrecoverable' else '', 'read': str(value),
                    'cold_read': str(value), 'cold_after': dict(after),
                    'sync_reads': [{'key': key, 'type': 'boolean', 'value': False}],
                    'reads': [{'key': key, 'value': value}]})
        runtime_rows = [
            {'id': 'typed-upgrade', 'fixture': {'coin': 3, 'music': 1},
             'reads': [{'key': 'coin', 'value': 3}], 'touches': [{'trusted': True}],
             'cold': {'coin': 3, 'raw': {'coin': 3, 'music': 1}}},
            {'id': 'isolated-music', 'raw': {'music': False}, 'afterPlay': {'music': False}},
            *[{'id': name, 'raw': {'coin': False}, 'writes': [], 'retry_visible': True,
               'loading_overlay_visible': False,
               'retry': {'before': 1, 'after': 2, 'touches': [{'trusted': True}], 'raw': {'coin': False}}}
              for name in ['critical-coin', 'metadata-unavailable']]]
        for row in runtime_rows:
            row.update(binding=self.binding, errors=[])
        self.trace = {'schema': 'native_storage_trace.v3', 'binding': self.binding,
            'project': str(self.root), 'trace_base': str(self.root), 'numeric_snapshot_encoding': self.codec,
            'execution': {'runner': str(runner), 'runner_sha256': self.sha(runner),
                          'command': ['node', str(runner), '{bundle}', '{adapter}']},
            'route_inventory': self.write('routes.json', self.routes),
            'snapshot_runtime': {'registered_runner': 'synthetic-registered-boundary',
                                 'raw': self.write('runtime.json', {'binding': self.binding, 'rows': runtime_rows})},
            'renderer_report': self.write('renderer.json', {'synthetic': True})}
        self.raws = {}
        for label in ['current', 'negative_control', 'upgrade_negative_control']:
            bundle = self.source
            row = {}
            if label != 'current':
                bundle = self.root / (label + '.js')
                change = {'before': "return ''", 'after': 'return null' if label == 'negative_control' else 'return 1'}
                bundle.write_text(self.source.read_text().replace(change['before'], change['after'], 1))
                row.update(kind='controlled_legacy_fixture', patch=change,
                    base_bundle=self.ref(self.source), provenance=self.write(label + '-provenance.json', {'synthetic': True}))
            raw = {'runner_sha256': self.sha(runner), 'bundle_sha256': self.sha(bundle),
                   'adapter_sha256': self.sha(self.native / 'adapter.js'),
                   'cases': copy.deepcopy(cases), 'matrix': copy.deepcopy(matrix),
                   'observations': {'completed_reward_once': {'after': {'watchAD': 1}},
                     'retry_after_transient_failure': {'failed': {'balance': 0}, 'after': {'balance': 200, 'creates': 1}}}}
            if label == 'negative_control':
                raw['cases']['missing_empty_string'] = 'fail'
            if label == 'upgrade_negative_control':
                next(x for x in raw['matrix'] if x['key'] == 'coin' and x['kind'] == 'typed_nonbinary')['read'] = '1'
            raw_path = self.root / (label + '.json')
            raw_path.write_text(json.dumps(raw))
            row.update(bundle=str(bundle), adapter=str(self.native / 'adapter.js'), raw_report=str(raw_path),
                       bundle_sha256=self.sha(bundle), adapter_sha256=self.sha(self.native / 'adapter.js'),
                       raw_sha256=self.sha(raw_path))
            self.trace[label] = row
            self.raws[label] = raw

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def ref(self, path):
        return {'path': str(Path(path).relative_to(self.root)), 'sha256': self.sha(path)}

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data))
        return self.ref(path)

    def check(self, *, registry=None, business=None, renderer=None):
        for label, raw in self.raws.items():
            path = Path(self.trace[label]['raw_report'])
            path.write_text(json.dumps(raw))
            self.trace[label]['raw_sha256'] = self.sha(path)
        with ExitStack() as stack:
            stack.enter_context(patch('audit_native_storage_contract.execution_identity', return_value={'synthetic': True}))
            stack.enter_context(patch('maintenance_scope.source_inventory', return_value=self.routes))
            stack.enter_context(patch('project_qa.lookup', return_value=registry or {'contract_sha256': self.codec['sha256']}))
            stack.enter_context(patch('startup_business_contract.validate_business', return_value=business or []))
            stack.enter_context(patch('audit_native_startup_renderer.validate', return_value=renderer or []))
            return N.validate(self.trace, self.native, self.binding)

    def current_row(self, kind='typed_nonbinary'):
        return next(x for x in self.raws['current']['matrix'] if x['key'] == 'coin' and x['kind'] == kind)

    def test_complete_bound_numeric_fixture(self):
        self.assertEqual(self.check(), [])

    def test_boolean_cannot_be_reported_as_integer(self):
        self.current_row()['value'] = True
        self.assertTrue(any('typed fixture invalid' in x for x in self.check()))

    def test_missing_key_case_is_not_coverage(self):
        self.raws['current']['matrix'].pop()
        self.assertTrue(any('matrix incomplete' in x for x in self.check()))

    def test_changed_original_is_refused(self):
        self.current_row()['after']['unrelated'] = 0
        self.assertTrue(any('original data changed' in x for x in self.check()))

    def test_changed_cold_original_is_refused(self):
        self.current_row()['cold_after']['unrelated'] = 0
        self.assertTrue(any('cold restart altered originals' in x for x in self.check()))

    def test_boolean_async_observation_cannot_prove_integer(self):
        self.current_row()['reads'][0]['value'] = True
        self.assertTrue(any('typed asynchronous original not observed' in x for x in self.check()))

    def test_unsafe_numeric_range_is_refused(self):
        self.current_row()['value'] = 9007199254740992
        self.assertTrue(any('typed fixture invalid' in x for x in self.check()))

    def test_unregistered_codec_is_refused(self):
        self.assertTrue(any('differs from reviewed' in x for x in self.check(registry={'contract_sha256': '0' * 64})))

    def test_negative_must_reproduce_the_actual_numeric_defect(self):
        row = next(x for x in self.raws['upgrade_negative_control']['matrix'] if x['key'] == 'coin' and x['kind'] == 'typed_nonbinary')
        row['read'] = '3'
        self.assertTrue(any('did not reproduce numeric bridge defect' in x for x in self.check()))

    def test_wrong_runner_hash_is_refused(self):
        self.raws['current']['runner_sha256'] = '0' * 64
        self.assertTrue(any('execution identity mismatch' in x for x in self.check()))

    def test_business_failure_is_retained(self):
        self.assertIn('synthetic business failure', self.check(business=['synthetic business failure']))

    def test_renderer_failure_is_retained(self):
        self.assertIn('synthetic renderer failure', self.check(renderer=['synthetic renderer failure']))


if __name__ == '__main__':
    unittest.main()
