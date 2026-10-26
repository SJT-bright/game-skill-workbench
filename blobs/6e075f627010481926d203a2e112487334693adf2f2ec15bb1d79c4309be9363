"""Portable scope/identity contracts; no actual game or browser is executed."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import audit_upload_startup as startup
import audit_native_startup_renderer as renderer


class EntryFamily(unittest.TestCase):
    def files(self, private=False, acknowledgement=True, prefix=''):
        declaration = ''
        if private:
            declaration = "globalThis.__bambooNativeCompat=tt;globalThis.__bambooResolvePlatform=function(){};"
        trace = "globalThis.__bambooBootstrap={build_tag:'fixture-build',phase:'before-diagnostics',entry_executed:true,first_exception:null};" if acknowledgement else ''
        failure = "__bambooBootstrap.first_exception={name:e.name,message:e.message,stack:e.stack,phase:__bambooBootstrap.phase};tt.showModal({content:e.message});" if acknowledgement else ''
        source = prefix + '(function(){' + declaration + trace + "try{require('./native-diagnostics.js');require('./native-platform.js');}catch(e){" + failure + "throw e;}require('./cocos-entry.js');})();"
        return {'game.js': source.encode(), 'game.json': b'{}',
                'project.config.json': b'{"appid":"fixture"}',
                'native-diagnostics.js': b'module.exports={};',
                'native-platform.js': b'module.exports={};',
                'cocos-entry.js': b'module.exports={};'}

    def test_same_filenames_do_not_select_private_protocol(self):
        files = self.files(prefix='// __bambooNativeCompat __bambooResolvePlatform\nconst help="__bambooNativeCompat __bambooResolvePlatform";')
        result = startup.audit_files(files)
        self.assertTrue(result['passed'], result)
        self.assertIsNone(result['native_host_boundary'])
        self.assertIsNone(result['bootstrap_boundary'])

    def test_dormant_private_example_does_not_select_protocol(self):
        files = self.files(prefix='function sample(){globalThis.__bambooNativeCompat={};globalThis.__bambooResolvePlatform=function(){};}')
        result = startup.audit_files(files)
        self.assertTrue(result['passed'], result)
        self.assertIsNone(result['bootstrap_boundary'])

    def test_unrelated_object_and_unreachable_writes_are_not_protocols(self):
        snippets = [
            'const notes={};notes.__bambooNativeCompat={};notes.__bambooResolvePlatform=function(){};',
            'if(false){globalThis.__bambooNativeCompat={};globalThis.__bambooResolvePlatform=function(){};}',
            'false&&(globalThis.__bambooNativeCompat={});false&&(globalThis.__bambooResolvePlatform=function(){});',
            '(function(globalThis){globalThis.__bambooNativeCompat={};globalThis.__bambooResolvePlatform=function(){};})({});',
        ]
        for source in snippets:
            with self.subTest(source=source):
                result = startup.audit_files(self.files(prefix=source))
                self.assertTrue(result['passed'], result)
                self.assertIsNone(result['bootstrap_boundary'])

    def test_real_global_alias_still_declares_private_protocol(self):
        source='(function(){const host=globalThis;host.__bambooNativeCompat=tt;host.__bambooResolvePlatform=function(){};})();'
        result = startup.audit_files(self.files(prefix=source, acknowledgement=False))
        self.assertIsNotNone(result['bootstrap_boundary'])

    def test_immediate_global_parameter_still_declares_protocol(self):
        source='(function(root){root.__bambooNativeCompat={};root.__bambooResolvePlatform=function(){};})(globalThis);'
        result = startup.audit_files(self.files(prefix=source, acknowledgement=False))
        self.assertIsNotNone(result['bootstrap_boundary'])

    def audit_private(self, acknowledgement):
        original = subprocess.run
        def run(command, **kwargs):
            # Host SDK/namespace calibration is a separate unchanged fixture.
            # Here isolate selection and the real bootstrap fault probe.
            if command[1].endswith('probe_native_host_boundary.cjs'):
                data = {'schema':'native_host_boundary.v1','passed':True,'rows':[{'passed':True}]}
                return subprocess.CompletedProcess(command, 0, json.dumps(data), '')
            return original(command, **kwargs)
        with patch.object(startup.subprocess, 'run', side_effect=run):
            return startup.audit_files(self.files(private=True, acknowledgement=acknowledgement))

    def test_known_protocol_missing_first_error_capture_still_refuses(self):
        result = self.audit_private(False)
        self.assertFalse(result['passed'])
        self.assertFalse(result['bootstrap_boundary']['passed'])
        self.assertTrue(any('bootstrap first-error capture' in e for e in result['errors']))

    def test_known_protocol_normal_and_original_failure_controls_pass(self):
        result = self.audit_private(True)
        self.assertTrue(result['passed'], result)
        self.assertEqual([r['mode'] for r in result['bootstrap_boundary']['rows']],
                         ['diagnostic_missing','diagnostic_parse_error','normal'])
        self.assertTrue(all(r['passed'] for r in result['bootstrap_boundary']['rows']))

    def test_acknowledgement_created_only_in_catch_is_refused(self):
        files = self.files(private=True)
        trace = "globalThis.__bambooBootstrap={build_tag:'fixture-build',phase:'before-diagnostics',entry_executed:true,first_exception:null};"
        files['game.js'] = files['game.js'].decode().replace(trace,'').replace('catch(e){','catch(e){'+trace).encode()
        result = startup.audit_files(files)
        self.assertFalse(result['bootstrap_boundary']['passed'])
        self.assertTrue(all(not r['observed']['ackBeforeDependency'] for r in result['bootstrap_boundary']['rows']))

    def test_optional_native_prompt_not_required_for_first_error_record(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'tt.showModal({content:e.message});',b'')
        result = startup.audit_files(files)
        self.assertTrue(result['bootstrap_boundary']['passed'],result)

    def test_invented_error_name_is_refused(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'name:e.name',b"name:'Invented'")
        result = startup.audit_files(files)
        self.assertFalse(result['bootstrap_boundary']['passed'])

    def test_invented_error_stack_is_refused(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'stack:e.stack',b"stack:'invented stack'")
        self.assertFalse(startup.audit_files(files)['bootstrap_boundary']['passed'])

    def test_replaced_error_with_same_message_is_refused(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'catch(e){',b'catch(e){e=new Error(e.message);')
        self.assertFalse(startup.audit_files(files)['bootstrap_boundary']['passed'])

    def test_catch_cannot_fill_missing_build_or_stage_metadata(self):
        files = self.files(private=True)
        trace = b"globalThis.__bambooBootstrap={build_tag:'fixture-build',phase:'before-diagnostics',entry_executed:true,first_exception:null};"
        files['game.js'] = files['game.js'].replace(trace,b'globalThis.__bambooBootstrap={entry_executed:true};').replace(b'catch(e){',b"catch(e){__bambooBootstrap.build_tag='fixture-build';__bambooBootstrap.phase='before-diagnostics';")
        self.assertFalse(startup.audit_files(files)['bootstrap_boundary']['passed'])

    def test_error_phase_must_match_dependency_entry_stage(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'phase:__bambooBootstrap.phase',b"phase:'invented phase'")
        self.assertFalse(startup.audit_files(files)['bootstrap_boundary']['passed'])

    def test_build_identity_cannot_change_during_fault_capture(self):
        files = self.files(private=True)
        files['game.js'] = files['game.js'].replace(b'catch(e){',b"catch(e){__bambooBootstrap.build_tag='another-build';")
        self.assertFalse(startup.audit_files(files)['bootstrap_boundary']['passed'])

    def test_generic_package_missing_dependency_still_refuses(self):
        files = self.files()
        del files['native-diagnostics.js']
        result = startup.audit_files(files)
        self.assertFalse(result['passed'])
        self.assertTrue(any('missing startup dependency' in e for e in result['errors']))


class RegisteredNativeBinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='registered native binding ')
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'; self.project.mkdir()
        self.native = self.project / 'native'; self.native.mkdir()
        (self.native / 'game.js').write_text('exports.ready=1;')
        self.other = self.project / 'other'; shutil.copytree(self.native,self.other)
        self.runner = self.project / 'runner.py'; self.runner.write_text('# isolated executor fixture\n')
        self.key = 'fixture-fixed-native'
        self.policy = {'project':str(self.project),'path':str(self.runner),
                       'sha256':renderer.sha(self.runner),'dependencies':{},'timeout_seconds':10,
                       'control_profile':'native_startup_controls.v1','native_binding':{'kind':'fixed_project_path','relative_path':'native'}}
        self.registry = self.root / 'native_startup_trusted_runners.json'
        self.save()
        self.report = {'control_profile':'native_startup_controls.v1','execution':{'registered_runner':self.key},
                       'runner':{'path':str(self.runner),'sha256':self.policy['sha256']}}

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.registry.write_text(json.dumps({self.key:self.policy}))

    def call(self, native=None):
        import project_qa
        with patch.object(project_qa,'lookup',return_value=self.policy):
            return renderer.execute_registered(self.report,native or self.native,{},self.project)

    def mock_execute(self, command, **kwargs):
        output = Path(command[command.index('--report')+1])
        output.write_text(json.dumps({'execution':{'registered_runner':self.key}}))
        return subprocess.CompletedProcess(command,0,'','')

    def test_actual_served_candidate_keeps_one_registered_execution(self):
        with patch.object(renderer.subprocess,'run',side_effect=self.mock_execute) as execute, patch.object(renderer,'validate',return_value=[]):
            self.assertEqual(self.call(),[])
            execute.assert_called_once()

    def test_byte_identical_other_directory_refused_before_execution(self):
        with patch.object(renderer.subprocess,'run') as execute:
            errors = self.call(self.other)
            self.assertTrue(any('candidate binding mismatch' in e for e in errors),errors)
            execute.assert_not_called()

    def test_malformed_or_escaping_fixed_binding_refused(self):
        for value in [None,'','../native','/absolute','native\\other','native//other','./native']:
            with self.subTest(value=value):
                self.policy['native_binding']={'kind':'fixed_project_path','relative_path':value};self.save()
                with patch.object(renderer.subprocess,'run') as execute:
                    self.assertTrue(self.call());execute.assert_not_called()

    def test_unknown_binding_kind_not_silently_ignored(self):
        self.policy['native_binding']={'kind':'unknown','relative_path':'native'};self.save()
        with patch.object(renderer.subprocess,'run') as execute:
            self.assertTrue(self.call());execute.assert_not_called()

    def test_missing_served_directory_refuses(self):
        shutil.rmtree(self.native)
        with patch.object(renderer.subprocess,'run') as execute:
            self.assertTrue(self.call(self.other));execute.assert_not_called()

    def test_unfixed_runner_contract_remains_unchanged(self):
        del self.policy['native_binding'];self.save()
        with patch.object(renderer.subprocess,'run',side_effect=self.mock_execute) as execute, patch.object(renderer,'validate',return_value=[]):
            self.assertEqual(self.call(self.other),[]);execute.assert_called_once()

    def test_changed_registered_dependency_still_refuses(self):
        self.policy['sha256']='0'*64;self.save()
        with patch.object(renderer.subprocess,'run') as execute:
            self.assertTrue(self.call());execute.assert_not_called()


if __name__=='__main__':
    unittest.main()
