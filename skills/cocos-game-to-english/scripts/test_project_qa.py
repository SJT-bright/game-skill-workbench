import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import project_qa as qa
import audit_native_startup_renderer as renderer


class ProjectQATests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.project=self.root/'project';(self.project/'qa').mkdir(parents=True)
        self.env=patch.dict(os.environ,{'COCOS_QA_TRUST_FILE':str(self.root/'machine-trust.json')});self.env.start();self.addCleanup(self.env.stop)
        (self.project/'qa/host.js').write_text('original host')
        self.runner=self.project/'qa/startup.py';self.runner.write_text('raise RuntimeError("fixture should be intercepted")\n')
        self.manifest=self.project/'qa/skill-qa.json'
        self.policy={'schema':'cocos_project_qa.v1','runners':{'startup':{'path':'qa/startup.py','dependencies':['qa/host.js'],'timeout_seconds':120,'control_profile':'native_startup_controls.v1'}}}
        self.save()

    def save(self):self.manifest.write_text(json.dumps(self.policy))
    def register(self):return qa.register(self.project,self.manifest,reviewed=True)

    def test_unregistered_runner_is_refused(self):
        with self.assertRaisesRegex(ValueError,'no reviewed'):qa.lookup(self.project,'runners','startup')
        with self.assertRaisesRegex(ValueError,'inspect the actual'):qa.register(self.project,self.manifest)

    def test_relative_registration_moves_without_shared_skill_edit(self):
        self.register();self.assertEqual(qa.lookup(self.project,'runners','startup')['path'],str(self.runner))
        moved=self.root/'moved';shutil.copytree(self.project,moved)
        with self.assertRaisesRegex(ValueError,'no reviewed'):qa.lookup(moved,'runners','startup')
        qa.register(moved,moved/'qa/skill-qa.json',reviewed=True)
        self.assertEqual(qa.lookup(moved,'runners','startup')['path'],str(moved/'qa/startup.py'))
        self.assertNotIn(str(self.project),json.dumps(self.policy))

    def test_related_code_changed_refuses_but_unrelated_project_file_reuses(self):
        self.register();(self.project/'unrelated.txt').write_text('new')
        qa.lookup(self.project,'runners','startup')
        (self.project/'qa/host.js').write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):qa.lookup(self.project,'runners','startup')

    def test_other_runner_dependency_does_not_invalidate_selected_runner(self):
        (self.project/'qa/other.py').write_text('other')
        self.policy['runners']['other']={'path':'qa/other.py','dependencies':[],'timeout_seconds':10,'control_profile':'native_startup_controls.v1'}
        self.save();self.register();(self.project/'qa/other.py').write_text('changed other')
        qa.lookup(self.project,'runners','startup')
        with self.assertRaisesRegex(ValueError,'changed'):qa.lookup(self.project,'runners','other')

    def test_unsupported_legacy_flags_absolute_escape_and_shell_rejected(self):
        for change in [lambda row:row.update(legacy_full_validation=True),lambda row:row.update(path=str(self.runner)),lambda row:row.update(path='../outside.py'),lambda row:row.update(command='echo pass'),lambda row:row.update(timeout_seconds=121)]:
            policy=copy.deepcopy(self.policy);change(policy['runners']['startup']);self.manifest.write_text(json.dumps(policy))
            with self.assertRaises(ValueError):self.register()

    def test_new_review_cannot_replace_common_schema(self):
        (self.project/'qa/review.py').write_text('def audit(*args):return {"status":"pass"}\n')
        self.policy['reviews']={'private:':{'path':'qa/review.py','dependencies':[],'review_schema':'private','native':'native','web':'web','review':'qa/review.json'}};self.save()
        with self.assertRaisesRegex(ValueError,'supplement schema 3'):self.register()

    def test_affected_replay_uses_fixed_python_arguments_and_validates_result(self):
        self.register();native=self.project/'native';native.mkdir();(native/'game.js').write_text('actual bytes')
        report={'execution':{'registered_runner':'startup'},'control_profile':'native_startup_controls.v1','runner':{'path':str(self.runner),'sha256':qa.sha(self.runner)}}
        commands=[]
        def run(command,**kwargs):
            commands.append((command,kwargs));output=Path(command[command.index('--report')+1]);output.write_text(json.dumps(report));return SimpleNamespace(returncode=0,stderr='')
        with patch.object(renderer.subprocess,'run',side_effect=run),patch.object(renderer,'validate',return_value=[]) as validate:
            self.assertEqual(renderer.execute_registered(report,native,{},self.project),[])
            validate.assert_called_once()
        self.assertEqual(commands[0][0][1],str(self.runner));self.assertFalse(commands[0][1]['shell'])
        forged=dict(report,execution={'registered_runner':'unknown'},command=['echo','pass'])
        with patch.object(renderer.subprocess,'run') as run:
            self.assertTrue(renderer.execute_registered(forged,native,{},self.project));run.assert_not_called()

    def test_resource_and_evidence_data_are_scoped_and_hashed(self):
        resource = self.project/'qa/resources.json';resource.write_text('{}')
        evidence = self.project/'qa/sound.json';evidence.write_text(json.dumps({'id':'synthetic'}))
        self.policy['resource_profiles']={'reviewed_resource_profiles.json':{'path':'qa/resources.json'}}
        self.policy['evidence_profiles']={'sound_settings_trace.v1':{'path':'qa/sound.json'}}
        self.save();self.register()
        self.assertEqual(qa.resource_profile_path(self.project,'reviewed_resource_profiles.json'),resource)
        self.assertEqual(qa.evidence_profile(self.project/'qa/raw.json','sound_settings_trace.v1')['project'],str(self.project))
        with self.assertRaisesRegex(ValueError,'no reviewed evidence'):
            qa.evidence_profile(self.root/'other/raw.json','sound_settings_trace.v1')
        evidence.write_text('{}')
        with self.assertRaisesRegex(ValueError,'changed'):
            qa.evidence_profile(self.project/'qa/raw.json','sound_settings_trace.v1')
        # A changed sound data file does not invalidate the independent resource scan.
        self.assertEqual(qa.resource_profile_path(self.project,'reviewed_resource_profiles.json'),resource)

    def test_evidence_profile_rejects_absolute_project_field(self):
        (self.project/'qa/sound.json').write_text(json.dumps({'project':str(self.project)}))
        self.policy['evidence_profiles']={'sound_settings_trace.v1':{'path':'qa/sound.json'}}
        self.save()
        with self.assertRaisesRegex(ValueError,'no absolute project'):self.register()

    def test_local_compatibility_adapter_is_scoped_and_refuses_changed_code(self):
        adapter=self.project/'qa/legacy.py'
        adapter.write_text('def validate_loading(data,binding,base):return []\n')
        policy={'id':'synthetic-legacy','project':str(self.project),'path':str(adapter),'sha256':qa.sha(adapter)}
        qa.write_store({'legacy_contracts':{'fixture':policy}})
        selected=qa.local_contract('synthetic-legacy',self.project/'qa/raw')
        self.assertEqual(qa.invoke(selected,'validate_loading',{}, {}, self.project),[])
        self.assertIsNone(qa.local_contract('synthetic-legacy',self.root/'unrelated'))
        adapter.write_text('def validate_loading(*args):return []\n')
        with self.assertRaisesRegex(ValueError,'changed'):
            qa.invoke(selected,'validate_loading',{}, {}, self.project)


if __name__=='__main__':unittest.main()
