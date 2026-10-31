"""Cheap refusals precede runtime; moving inputs cannot receive a delivery pass.

Mocks isolate gate orchestration. These are tool tests, not game execution.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_final_startup_gate as startup_cases
from test_package_checks import fixture, runtime_patch, APP, OTHER_APP, fixture_project
_RUNTIME = runtime_patch()
setUpModule, tearDownModule = _RUNTIME.start, _RUNTIME.stop
from check_package import write_archive
from build_checked_zip import build
from prepare_delivery import prepare


class WriterOrder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project=fixture_project(self.root/"project")     # v7.7: current source record (K5)
        (self.root / 'other-temp').mkdir()
        self.native = self.root / 'native'
        self.native.mkdir()
        files = fixture()
        config = json.loads(files['assets/main/config.json'])
        config.update(paths={'0': ['fixture', 0]}, types=['cc.JsonAsset'])
        files['assets/main/config.json'] = json.dumps(config).encode()
        for name, data in files.items():
            target = self.native / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.files = files
        self.manifest = self.root / 'resources.json'
        self.manifest.write_text(json.dumps({'resources': [
            {'bundle': 'main', 'path': 'fixture', 'type': 'cc.JsonAsset'}]}))
        self.out = self.root / 'new.zip'

    def tearDown(self):
        self.temp.cleanup()

    def test_wrong_app_id_never_starts_runtime(self):
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True}) as run:
            # v7.7: tiktok_finalize's appid step compares the target with the project's PlatformConfig first
            with self.assertRaisesRegex(ValueError, 'K_appid_mismatch: --app-id %s differs' % OTHER_APP):
                build(self.native, OTHER_APP, self.out, resource_manifest=self.manifest, project=self.project)
            run.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_wrong_output_suffix_refused_before_any_runtime(self):
        out = self.root / 'looks-like-source.txt'
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True}) as run:
            with self.assertRaisesRegex(ValueError, r'\.zip'):
                build(self.native, APP, out, resource_manifest=self.manifest, project=self.project)
            run.assert_not_called()
        self.assertFalse(out.exists())

    def test_missing_packed_asset_refused_before_runtime(self):
        with patch('check_package.packed_assets', return_value={
                'passed': False, 'errors': ['missing fixture texture']}) as assets, \
                patch('build_checked_zip.audit_final_startup', return_value={'passed': True}) as run:
            with self.assertRaisesRegex(ValueError, 'missing fixture texture'):
                build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project)
            run.assert_not_called()
            self.assertTrue(assets.called)
        self.assertFalse(self.out.exists())

    def test_manifest_changed_during_runtime_refused_without_zip(self):
        def change(*args, **kwargs):
            self.manifest.write_text('{"resources": []}')
            return {'passed': True}
        with patch('build_checked_zip.audit_final_startup', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'manifest changed'):
                build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project)
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob('.tiktok-package-*')))

    def test_normal_writer_calls_runtime_once_and_reports_phase_timings(self):
        import audit_upload_startup
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True}) as run, \
                patch.object(audit_upload_startup, 'audit_files', wraps=audit_upload_startup.audit_files) as dependency:
            result = build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project)
        run.assert_called_once()
        self.assertEqual(dependency.call_count, 2)  # Native preflight, then the actual ZIP.
        self.assertTrue(result['expected_tree_exact'])
        self.assertEqual(set(result['check_timings']), {
            'static_preflight_seconds', 'startup_runtime_seconds',
            'archive_validation_seconds', 'total_seconds'})
        self.assertTrue(all(n >= 0 for n in result['check_timings'].values()))

    def test_existing_delivery_record_stops_before_full_check(self):
        archive = self.root / 'input.zip'
        write_archive(archive, self.files)
        record = self.root / 'already-checked.json'
        record.write_text('{"original": true}')
        with patch('prepare_delivery.tempfile.gettempdir', return_value=str(self.root / 'other-temp')), \
                patch('prepare_delivery.check') as check:
            with self.assertRaisesRegex(ValueError, 'record already exists'):
                prepare(archive, self.native, APP, record, project=self.project, resource_manifest=self.manifest)
            check.assert_not_called()
        self.assertEqual(json.loads(record.read_text()), {'original': True})

    def test_delivery_native_mutation_during_startup_refused(self):
        archive = self.root / 'input.zip'
        write_archive(archive, self.files)
        record = self.root / 'delivery.json'
        def mutate(*args, **kwargs):
            (self.native / 'child.js').write_text('changed = true;')
            return {'passed': True}
        with patch('prepare_delivery.tempfile.gettempdir', return_value=str(self.root / 'other-temp')), \
                patch('prepare_delivery.audit_final_startup', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'Native changed'):
                prepare(archive, self.native, APP, record, project=self.project, resource_manifest=self.manifest)
        self.assertFalse(record.exists())


class StartupIdentity(unittest.TestCase):
    # Reuse setup only; do not run the same base tests a second time.
    setUp = startup_cases.FinalStartupGate.setUp
    tearDown = startup_cases.FinalStartupGate.tearDown
    save = startup_cases.FinalStartupGate.save
    call = startup_cases.FinalStartupGate.call
    def test_runtime_cannot_replace_native_after_binding_check(self):
        import audit_final_package_startup as gate
        def mutate(*args):
            (self.native / 'child.js').write_text('modified during execution;')
            return []
        with patch.object(gate.renderer, 'validate', return_value=[]), \
                patch.object(gate, 'validate_recovery', return_value=[]), \
                patch.object(gate, 'validate_runtime_report', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during'):
                self.call()

    def test_runtime_cannot_replace_recovery_evidence(self):
        import audit_final_package_startup as gate
        def mutate(*args):
            self.recovery.write_text('{"replacement": true}')
            return []
        with patch.object(gate.renderer, 'validate', return_value=[]), \
                patch.object(gate, 'validate_recovery', return_value=[]), \
                patch.object(gate, 'validate_runtime_report', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during'):
                self.call()

    def test_null_renderer_reference_is_a_typed_refusal(self):
        self.data['startup_renderer_report'] = None
        self.save()
        with self.assertRaisesRegex(ValueError, 'renderer evidence reference'):
            self.call()

    def test_invalid_identity_types_are_typed_refusals(self):
        original = dict(self.data)
        for key in ('native', 'project'):
            for value in (None, 42, [], {}, ''):
                with self.subTest(key=key, value=value):
                    self.data = dict(original)
                    self.data[key] = value
                    self.save()
                    with self.assertRaisesRegex(ValueError, 'identity paths'):
                        self.call()


if __name__ == '__main__':
    unittest.main()
