"""Gate wiring tests. Mocked validator success is not a game's runtime evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_package_checks import fixture, APP, fixture_project
from build_checked_zip import build
import audit_final_package_startup as gate
import native_startup_ledger as startup
import regression_scope_gate as scope

class FinalStartupGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.native=self.root/'native';self.native.mkdir()
        self.project=fixture_project(self.root/'project')     # v7.7: current source record (K5)
        files=fixture();c=json.loads(files['assets/main/config.json']);c.update(paths={'0':['fixture',0]},types=['cc.JsonAsset']);files['assets/main/config.json']=json.dumps(c).encode()
        for name,data in files.items():
            p=self.native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.manifest=self.root/'resources.json';self.manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'fixture','type':'cc.JsonAsset'}]}))
        self.binding={'native_tree_sha256':gate.renderer.digest(gate.renderer.tree(self.native)),
                      'source_sha256':'source-one', 'web_tree_sha256':'web-one', 'build_tag':'one'}
        self.proof=self.root/'proof.json';self.proof.write_text('{}')
        self.contract=self.root/'contract.json';self.recovery=self.root/'recovery.json';self.recovery.write_text('{}')
        self.data={'tool':'audit_startup_contract','passed':True,'policy_version':2,'runtime_required':True,'native':str(self.native),'project':str(self.project),'binding':self.binding,'startup_renderer_report':{'path':str(self.proof),'sha256':gate.renderer.sha(self.proof)}}
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):self.contract.write_text(json.dumps(self.data))
    def call(self):return gate.audit_final_startup(self.native,self.project,self.contract,self.recovery)
    def test_no_runtime_proof_no_zip(self):
        from test_single_writer import SingleWriter
        actual_startup=gate.audit_final_startup
        f=SingleWriter('test_legacy_build_routes_all_parameters_once');f.setUp();self.addCleanup(f.doCleanups);f.mock_engine()
        with patch.object(gate,'audit_final_startup',side_effect=actual_startup), self.assertRaisesRegex(ValueError,'final Native startup evidence required'):
            build(**f.kw)
        self.assertFalse(f.out.exists());self.assertFalse(list(f.home.glob('.tiktok-package-*')))
    def test_failed_contract_rejected(self):
        self.data['passed']=False;self.save()
        with self.assertRaisesRegex(ValueError,'missing or failed'):self.call()
    def test_source_only_contract_rejected(self):
        self.data['runtime_required']=False;self.save()
        with self.assertRaisesRegex(ValueError,'source-only'):self.call()
    def test_other_native_rejected(self):
        self.data['native']=str(self.root/'other');self.save()
        with self.assertRaisesRegex(ValueError,'identity mismatch'):self.call()
    def test_old_native_binding_rejected(self):
        (self.native/'child.js').write_text('changed=true;')
        with self.assertRaisesRegex(ValueError,'stale'):self.call()
    def test_changed_renderer_proof_rejected(self):
        self.proof.write_text('{"passed":true}')
        with self.assertRaisesRegex(ValueError,'missing or changed'):self.call()
    def test_bare_pass_flags_cannot_substitute_for_runtime(self):
        with self.assertRaisesRegex(ValueError,'startup/Retry refused'):self.call()
    def test_home_without_business_effect_rejected(self):
        with patch.object(gate.renderer,'validate',return_value=['STARTUP-BUSINESS: observable gameplay change after touch required']),patch.object(gate,'validate_recovery',return_value=[]),patch.object(gate,'validate_runtime_report') as execute:
            with self.assertRaisesRegex(ValueError,'gameplay change'):self.call()
            execute.assert_not_called()
    def test_retry_validation_cannot_be_skipped(self):
        with patch.object(gate.renderer,'validate',return_value=[]),patch.object(gate,'validate_recovery',return_value=['Retry reused abandoned request']),patch.object(gate,'validate_runtime_report') as execute:
            with self.assertRaisesRegex(ValueError,'abandoned request'):self.call()
            execute.assert_not_called()
    def test_real_runner_failure_blocks(self):
        with patch.object(gate.renderer,'validate',return_value=[]),patch.object(gate,'validate_recovery',return_value=[]),patch.object(gate,'validate_runtime_report',return_value=['trusted replay failed']):
            with self.assertRaisesRegex(ValueError,'replay refused'):self.call()
    def test_success_calls_registered_replay_and_delivery_reuses_validation(self):
        runner = self.project/'probe.py'
        runner.write_text(
            'import argparse, json\nfrom pathlib import Path\n'
            'p=argparse.ArgumentParser()\n'
            'for n in ("native","expected-native-hash","report","binding-json"): p.add_argument("--"+n)\n'
            'a=p.parse_args()\n'
            'c=Path("calls");c.write_text(c.read_text()+"1" if c.exists() else "1")\n'
            'Path(a.report).write_text(json.dumps(dict(execution={"registered_runner":"fixture"}, binding=json.loads(a.binding_json))))\n')
        self.proof.write_text(json.dumps({'execution':{'registered_runner':'fixture'},
                                          'control_profile':'canvas_context_conflict_v1',
                                          'runner':{'path':str(runner.resolve()), 'sha256':gate.renderer.sha(runner)}}))
        self.data['startup_renderer_report']['sha256']=gate.renderer.sha(self.proof)
        self.save()
        policy={'project':str(self.project.resolve()), 'path':str(runner.resolve()), 'sha256':gate.renderer.sha(runner), 'timeout_seconds':5}
        with patch.object(gate.renderer,'validate',return_value=[]),patch.object(gate,'validate_recovery',return_value=[]),patch.object(startup.project_qa,'lookup',return_value=policy):
            # The LOAD contract is the first entry; the writer and delivery share its actual execution.
            first = {}
            self.assertEqual(gate.validate_runtime_report(self.data, self.binding, detail=first), [])
            self.assertEqual(first['action'], 'rerun')
            cached = self.call()['checks'][1]
            self.assertEqual(cached['action'], 'reused')
            self.assertEqual(cached['source_key'], first['key'])
            self.assertEqual((self.project/'calls').read_text(), '1')
            # Source/Web/build labels alone do not cause a second Native replay.
            self.binding.update(web_tree_sha256='web-two', source_sha256='source-two', build_tag='two')
            self.save()
            self.assertEqual(self.call()['checks'][1]['original_build_tag'], 'one')
            self.assertEqual((self.project/'calls').read_text(), '1')
            # A changed adapter cannot use the old successful observation even if the same folder is used.
            (self.native/'adapter-min.js').write_text('changed = true;')
            with self.assertRaisesRegex(ValueError, 'stale'):
                self.call()
            self.binding['native_tree_sha256']=gate.renderer.digest(gate.renderer.tree(self.native))
            self.save()
            with self.assertRaisesRegex(ValueError, '正式交付只能回读启动证据'):
                gate.audit_final_startup(self.native,self.project,self.contract,self.recovery,reuse_only=True)
            with self.assertRaisesRegex(ValueError, '写包前未核准'):
                self.call()
            self.assertEqual((self.project/'calls').read_text(), '1')
            plan = {'mode': 'scoped', 'startup_run': True, 'native_tree': scope.ledger.sha(scope.ledger.manifest(self.native))}
            token = scope._active_plan.set('test-plan')
            try:
                with patch.object(scope, '_load_plan', return_value=(plan, 'test-plan')):
                    changed = self.call()['checks'][1]
            finally:
                scope._active_plan.reset(token)
            self.assertEqual(changed['action'], 'rerun')
            self.assertIn('Native 内容', changed['reason'])
            self.assertEqual((self.project/'calls').read_text(), '11')
            # A pass flag without the actual preserved replay cannot be reused.
            Path(changed['evidence'][0]).unlink()
            with self.assertRaisesRegex(ValueError, '原通过证据丢失'):
                self.call()
            self.assertEqual((self.project/'calls').read_text(), '11')

# This module checks the original gate's own obligations with tiny fixtures.
# Keep the strict-six production boundary in its dedicated real-auditor tests.
from pathlib import Path as _AdFixturePath
import sys as _ad_fixture_sys
_ad_fixture_core = next(p/'remake-core/scripts' for p in _AdFixturePath(__file__).resolve().parents
                        if (p/'remake-core/scripts/fixture_ad_standard_scope.py').is_file())
_ad_fixture_sys.path.insert(0,str(_ad_fixture_core))
from fixture_ad_standard_scope import isolate as _isolate_ad_fixture
_isolate_ad_fixture(globals())

if __name__=='__main__':unittest.main()
