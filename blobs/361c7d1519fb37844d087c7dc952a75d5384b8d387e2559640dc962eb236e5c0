"""Real storage approval/consumer scope controls; synthetic runner and artifacts.

The existing route-inventory fixture is isolated; the storage byte/runner/raw
validator, project QA registration and immutable snapshots are real.
"""
from pathlib import Path
import copy
import json
import os
import shutil
import unittest
from unittest.mock import patch

import audit_native_storage_contract as contract
import audit_final_storage as final
import check_known_issues as consumer
import project_qa
import storage_scoped_reuse as scoped
import test_native_storage_upgrade_contract as fixture


class StorageScope(unittest.TestCase):
    def setUp(self):
        f = self.f = fixture.UpgradeTests('test_valid_v3_and_actual_consumer')
        f.setUp(); self.addCleanup(f.doCleanups)
        self.root = f.root.resolve()
        self.source = self.root / 'Source'; (self.source / 'assets').mkdir(parents=True)
        (self.source / 'assets/store.js').write_text('// synthetic storage consumer input')
        (self.source / 'assets/icon.png').write_bytes(b'old synthetic source image')
        (f.native / 'icon.png').write_bytes(b'old synthetic Native image')
        f.trace['project'] = str(self.source)
        f.binding['source_sha256'] = consumer.snapshot(self.source)[2]
        f.binding['native_tree_sha256'] = consumer.tree_sha(f.native)
        self.report_path = self.root / 'approved.json'
        self.trace_path = self.root / 'trace.json'
        self.counter = self.root / 'helper-calls.txt'
        self.env = patch.dict(os.environ, {'COCOS_QA_TRUST_FILE': str(self.root / 'qa-trust.json')})
        self.env.start(); self.addCleanup(self.env.stop)
        self.install_profile()
        self.approve()

    def install_profile(self):
        qa = self.source / 'qa'; qa.mkdir(exist_ok=True)
        raw = qa / 'scope-reads.json'
        raw.write_text(json.dumps({'schema': 'synthetic_dependency_read_trace.v1',
            'boundary': 'The synthetic runner reads only the explicit bundle/adapter; game.js remains an additional mandatory static input.'}))
        helper = qa / 'scope.py'
        helper.write_text('''from pathlib import Path
import storage_scoped_reuse as S
def storage_dependency_scope(*,project,native,source,trace,binding):
 p=Path(%r);p.write_text(str(int(p.read_text())+1) if p.exists() else '1')
 manifests={'source':S.snapshot(source,True)[0],'package':S.snapshot(native)[0]}
 return {'schema':S.PROFILE,'complete':True,'basis':'Reviewed synthetic runner reads only explicit bundle/adapter; unrelated byte resource has no consumer in this fixture.',
 'unknown':[],'artifact_names':{k:sorted(v) for k,v in manifests.items()},
 'inputs':{k:[n for n in v if n!='assets/icon.png' and n!='icon.png'] for k,v in manifests.items()},
 'raw_evidence':[{'path':'qa/scope-reads.json','sha256':S.file_sha(Path(project)/'qa/scope-reads.json')}]}
''' % str(self.counter))
        policy = qa / 'policy.json'
        policy.write_text(json.dumps({'schema': 'cocos_project_qa.v1', 'validators': {
            scoped.PROFILE: {'path': 'qa/scope.py', 'dependencies': ['qa/scope-reads.json']}}}))
        project_qa.register(self.source, policy, reviewed=True)

    def approve(self):
        f = self.f
        self.trace_path.write_text(json.dumps(f.trace))
        self.report = contract.approve_runtime(f.trace, f.native, f.binding)
        self.assertTrue(self.report['passed'], self.report.get('errors'))
        self.assertIn('storage_scope', self.report, self.report.get('storage_scope_status'))
        self.report.update(trace=str(self.trace_path), trace_sha256=scoped.file_sha(self.trace_path))
        self.report_path.write_text(json.dumps(self.report))
        self.startup = self.root / 'startup.json'
        self.startup.write_text(json.dumps({'binding': f.binding, 'native_storage_report': {
            'path': str(self.report_path), 'sha256': scoped.file_sha(self.report_path)}}))

    def changed_binding(self, native=None):
        return dict(self.f.binding, source_sha256=consumer.snapshot(self.source)[2],
            native_tree_sha256=consumer.tree_sha(native or self.f.native), build_tag='new-art-version')

    def consume(self, native=None):
        return scoped.validate_report(self.report, native or self.f.native,
            self.changed_binding(native), project=self.source)

    def test_in_place_nonconsumer_art_reuses_original_without_helper_or_runner(self):
        original = copy.deepcopy(self.report)
        (self.source / 'assets/icon.png').write_bytes(b'new source pixels')
        (self.f.native / 'icon.png').write_bytes(b'new Native pixels')
        with patch.object(contract, 'replay', side_effect=AssertionError('no replay')), \
                patch.object(project_qa, 'module', side_effect=AssertionError('consumer must not run helper')):
            self.assertEqual(self.consume(), [])
            result = final.audit_final_storage(self.f.native, self.source, self.startup)
        self.assertFalse(result['game_executed'])
        self.assertEqual(self.report, original)
        self.assertEqual(self.counter.read_text(), '1')

    def test_distinct_native_directory_from_old_approved_baseline(self):
        new = self.root / 'Native New'
        shutil.copytree(self.f.native, new)
        (new / 'icon.png').write_bytes(b'new Native target pixels')
        oldhome = scoped.home_path(self.source, self.report)
        original_bytes = (oldhome / 'scope.json').read_bytes()
        ref = scoped.seal_approval(self.report, self.f.trace, new, self.source,
            baseline_native=self.f.native, baseline_source=self.source)
        self.assertTrue(Path(ref['path']).is_file())
        self.assertEqual((oldhome / 'scope.json').read_bytes(), original_bytes)
        self.assertNotEqual(Path(ref['path']).parent, oldhome)
        with patch.object(contract, 'replay', side_effect=AssertionError('no replay')):
            self.assertEqual(self.consume(new), [])
            self.assertEqual(final.audit_final_storage(new, self.source, self.startup)['id'], 'storage.native.contract')

    def test_real_auto_report_consumer_accepts_current_native_and_original_report(self):
        (self.f.native / 'icon.png').write_bytes(b'new pixels')
        errors = []
        with patch.object(contract, 'replay', side_effect=AssertionError('no replay')):
            consumer.auto_reports({'id': 'STORAGE-01', 'auto_check': ['audit_native_storage_contract']},
                {'auto_reports': [{'path': str(self.report_path), 'sha256': scoped.file_sha(self.report_path)}]},
                self.root, errors, self.changed_binding(), project=self.source, current_native=self.f.native)
        self.assertEqual(errors, [])

    def test_actual_storage_js_change_invalidates_only_storage_node(self):
        (self.f.native / 'game.js').write_text('localStorage.getItem("changed-consumer");')
        errors = self.consume()
        self.assertTrue(errors)
        self.assertIn('affected dependencies', str(errors))
        self.assertEqual(self.counter.read_text(), '1')

    def test_source_consumer_change_invalidates(self):
        (self.source / 'assets/store.js').write_text('localStorage.getItem("new-source-key");')
        self.assertIn('affected dependencies', str(self.consume()))

    def test_json_or_layout_binding_change_is_not_called_unrelated(self):
        self.f.native.joinpath('storage-fixture.json').write_text('{}')
        self.assertIn('affected dependencies', str(self.consume()))

    def test_new_unknown_file_requires_ownership_without_replay(self):
        (self.f.native / 'new.bin').write_bytes(b'unknown new dependency')
        self.assertIn('file ownership', str(self.consume()))
        self.assertEqual(self.counter.read_text(), '1')

    def test_fake_current_binding_cannot_relabel_old_approval(self):
        binding = self.changed_binding(); binding['native_tree_sha256'] = '0' * 64
        self.assertIn('actual artifacts', str(scoped.validate_report(self.report, self.f.native, binding, project=self.source)))

    def test_changed_helper_is_not_run_or_reused(self):
        (self.f.native / 'icon.png').write_bytes(b'changed image needs scoped reuse')
        (self.source / 'qa/scope.py').write_text('raise RuntimeError("changed")')
        self.assertTrue(self.consume())
        self.assertEqual(self.counter.read_text(), '1')

    def test_missing_frozen_raw_is_not_a_pass(self):
        home = scoped.home_path(self.source, self.report)
        record = scoped.read(home / 'scope.json')
        (home / next(iter(record['evidence'].values()))['path']).unlink()
        (self.f.native / 'icon.png').write_bytes(b'new pixels require preserved scope')
        self.assertTrue(self.consume())

    def test_changed_original_raw_is_not_a_pass(self):
        Path(self.f.trace['current']['raw_report']).write_text('{}')
        self.assertTrue(self.consume())

    def test_no_registered_helper_keeps_exact_approval_but_never_exempts_art(self):
        home = scoped.home_path(self.source, self.report)
        shutil.rmtree(home)
        (self.f.native / 'icon.png').write_bytes(b'changed')
        self.assertIn('scope_required', str(self.consume()))

    def test_failed_report_cannot_be_accepted_by_exact_or_scoped_consumer(self):
        self.report['passed'] = False
        self.assertTrue(scoped.validate_report(self.report, self.f.native, self.f.binding, project=self.source))
        self.assertTrue(self.consume())

    def test_dependency_helper_cannot_omit_a_storage_code_input(self):
        home = scoped.home_path(self.source, self.report)
        record = scoped.read(home / 'scope.json')
        scope = copy.deepcopy(record['scope'])
        scope['inputs']['package'].remove('game.js')
        with self.assertRaisesRegex(ValueError, 'mandatory code'):
            scoped.validate_scope(scope, record['manifests'])

    def test_unknown_resource_read_domain_is_not_a_suffix_exemption(self):
        home = scoped.home_path(self.source, self.report)
        record = scoped.read(home / 'scope.json')
        scope = copy.deepcopy(record['scope']);scope['unknown'] = ['dynamic resource pixel read']
        with self.assertRaisesRegex(ValueError, 'resolve every actual read domain'):
            scoped.validate_scope(scope, record['manifests'])

    def test_actual_formal28_auditor_approval_migrates_without_replay(self):
        import types
        original = Path(__file__).parent / 'tests/fixtures/storage_formal28'
        identity = scoped.read(original / 'identity.json')
        old = types.ModuleType('formal28_storage_auditor')
        old.__file__ = str(original / 'auditor.py.fixture')
        code = (original / 'auditor.py.fixture').read_bytes()
        self.assertEqual(scoped.digest(code), identity['contract_files']['audit_native_storage_contract.py'])
        exec(compile(code, old.__file__, 'exec'), old.__dict__)
        # The exact old auditor and real synthetic runner execute. Only its
        # release-file fingerprint reader uses the captured formal ZIP hashes;
        # unrelated old dependencies are not duplicated into this distribution.
        fingerprints = {k:v for k,v in identity['contract_files'].items() if k != 'numeric_snapshot_contract.py'}
        with patch.object(old, 'contract_identity', return_value=fingerprints):
            approved = old.approve_runtime(self.f.trace, self.f.native, self.f.binding)
        self.assertTrue(approved['passed'], approved.get('errors'))
        self.assertEqual(approved['execution_receipt']['identity']['contract_files'], fingerprints)
        approved.update(trace=str(self.trace_path), trace_sha256=scoped.file_sha(self.trace_path))
        self.report = approved
        self.report_path.write_text(json.dumps(approved))
        scoped.seal_approval(approved, self.f.trace, self.f.native, self.source)
        original_at = approved['execution_receipt']['verified_at']
        (self.f.native / 'icon.png').write_bytes(b'new Native pixels after formal28 approval')
        with patch.object(contract, 'replay', side_effect=AssertionError('do not replay old observation')):
            self.assertEqual(self.consume(), [])
        self.assertEqual(approved['execution_receipt']['verified_at'], original_at)
        bad = copy.deepcopy(approved)
        bad['execution_receipt']['identity']['contract_files']['audit_native_storage_contract.py'] = '0' * 64
        self.assertTrue(contract.validate_execution_receipt(bad, self.f.trace))

    def test_real_source_inventory_keeps_origin_paths_and_only_projects_source_hash(self):
        import maintenance_scope
        # This case removes the older fixture's route stub. The original route
        # validator, frozen Source hash, actual source/scene identities and two
        # recorded GUI ratios are all checked by production code.
        self.f.route_patch.stop()
        scene = self.source / 'assets/main.fire'; scene.write_text('{}')
        self.f.binding['source_sha256'] = consumer.snapshot(self.source)[2]
        def write(name, obj):
            p = self.root / name; p.write_text(json.dumps(obj));return p
        def ref(p): return {'path':str(p),'sha256':scoped.file_sha(p)}
        raw = write('route-touch.json', {'events':[{'trusted':True}]})
        ui = write('route-ui.json', {'binding':self.f.binding,
            'routes':[{'id':x,'role':x} for x in ('home','map','stage_details')], 'raw_evidence':[ref(raw)]})
        routes = {}
        for name in ('home','map','stage_details'):
            guis = [ref(write(name+str(v[0])+'.json', {'execution_binding':self.f.binding,
                'route':name,'viewport':v,'route_present':True,'actions':['reopen','retry'],
                'trusted_touch':True,'interaction_effect':'Synthetic route state changed',
                'raw_evidence':[ref(raw)]})) for v in ([393,852],[375,667])]
            routes[name] = {'present':True,'source_reason':'Explicit synthetic route inventory',
                'scene_files':[ref(scene)],'gui_evidence':guis}
        inventory = write('real-route-inventory.json', {'schema':'maintenance_source_inventory.v1',
            'binding':self.f.binding,'source_files':[ref(self.source/'assets/store.js')],
            'scene_files':[ref(scene)],'ui_route_inventory':ref(ui),'routes':routes})
        self.f.trace['route_inventory'] = ref(inventory)
        self.approve()
        (self.source/'assets/icon.png').write_bytes(b'changed source pixels only')
        (self.f.native/'icon.png').write_bytes(b'changed Native pixels only')
        self.assertEqual(self.consume(), [])
        # The projection is not a waiver for a changed path-bound source file.
        (self.source/'assets/store.js').write_text('// changed actual route/source dependency')
        self.assertIn('affected dependencies', str(self.consume()))

    def test_build_tag_only_needs_no_helper_or_new_scope(self):
        binding = dict(self.f.binding, build_tag='new-label-only')
        with patch.object(project_qa, 'lookup', side_effect=AssertionError('no scope lookup')), \
                patch.object(contract, 'replay', side_effect=AssertionError('no replay')):
            self.assertEqual(scoped.validate_report(self.report, self.f.native, binding, project=self.source), [])

    def test_web_only_metadata_change_needs_no_new_native_storage_scope(self):
        binding = dict(self.f.binding, web_tree_sha256='f' * 64, build_tag='new-web-output')
        with patch.object(project_qa, 'lookup', side_effect=AssertionError('no scope lookup')), \
                patch.object(contract, 'replay', side_effect=AssertionError('no replay')):
            self.assertEqual(scoped.validate_report(self.report, self.f.native, binding, project=self.source), [])

    def test_first_concurrent_prepare_runs_one_dependency_helper(self):
        from concurrent.futures import ThreadPoolExecutor
        # Remove only this temporary fixture's metadata to model an old approved
        # observation whose scope has not yet been registered.
        home = scoped.home_path(self.source, self.report)
        shutil.rmtree(home); self.counter.write_text('0')
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(scoped.seal_approval, self.report, self.f.trace,
                self.f.native, self.source) for _ in range(2)]
            results = [job.result() for job in jobs]
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.counter.read_text(), '1')

    def test_identical_native_in_new_directory_uses_original_observation_paths(self):
        new = self.root / 'Identical Native in new directory'
        shutil.copytree(self.f.native, new)
        with patch.object(project_qa, 'lookup', side_effect=AssertionError('whole bytes need no new scope')), \
                patch.object(contract, 'replay', side_effect=AssertionError('no replay')):
            self.assertEqual(scoped.validate_report(self.report, new, self.f.binding, project=self.source), [])
            self.assertEqual(final.audit_final_storage(new, self.source, self.startup)['id'], 'storage.native.contract')

    def test_read_only_repeat_keeps_original_execution_time(self):
        home = scoped.home_path(self.source, self.report)
        before = (home / 'scope.json').read_bytes()
        self.assertEqual(self.consume(), [])
        self.assertEqual(self.consume(), [])
        self.assertEqual((home / 'scope.json').read_bytes(), before)
        self.assertEqual(self.counter.read_text(), '1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
