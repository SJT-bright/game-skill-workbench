"""Gate wiring tests. Mocked validator success is not a game's runtime evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_package_checks import fixture
from build_checked_zip import build
import audit_final_package_startup as gate

class FinalStartupGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.native=self.root/'native';self.native.mkdir();self.project=self.root/'project';self.project.mkdir()
        from package_issue_gate import initialize
        initialize(self.project)
        files=fixture();c=json.loads(files['assets/main/config.json']);c.update(paths={'0':['fixture',0]},types=['cc.JsonAsset']);files['assets/main/config.json']=json.dumps(c).encode()
        for name,data in files.items():
            p=self.native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.manifest=self.root/'resources.json';self.manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'fixture','type':'cc.JsonAsset'}]}))
        self.binding={'native_tree_sha256':gate.renderer.digest(gate.renderer.tree(self.native))}
        self.proof=self.root/'proof.json';self.proof.write_text('{}')
        self.contract=self.root/'contract.json';self.recovery=self.root/'recovery.json';self.recovery.write_text('{}')
        self.data={'tool':'audit_startup_contract','passed':True,'policy_version':2,'runtime_required':True,'native':str(self.native),'project':str(self.project),'binding':self.binding,'startup_renderer_report':{'path':str(self.proof),'sha256':gate.renderer.sha(self.proof)}}
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):self.contract.write_text(json.dumps(self.data))
    def call(self):return gate.audit_final_startup(self.native,self.project,self.contract,self.recovery)
    def test_no_runtime_proof_no_zip(self):
        out=self.root/'test.zip'
        with self.assertRaisesRegex(ValueError,'startup evidence required'):
            build(self.native,'test-target',out,resource_manifest=self.manifest,project=self.project)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
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
        with patch.object(gate.renderer,'validate',return_value=[]),patch.object(gate,'validate_recovery',return_value=[]),patch.object(gate,'validate_runtime_report',return_value=[]) as execute:
            self.assertTrue(self.call()['registered_renderer_replayed']);execute.assert_called_once()
            self.assertFalse(gate.audit_final_startup(self.native,self.project,self.contract,self.recovery,replay=False)['registered_renderer_replayed']);execute.assert_called_once()

if __name__=='__main__':unittest.main()
