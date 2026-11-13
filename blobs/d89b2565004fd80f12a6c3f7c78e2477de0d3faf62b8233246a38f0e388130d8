"""Cheap refusals precede runtime; moving inputs cannot receive a delivery pass.

Mocks isolate gate orchestration. These are tool tests, not game execution.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_final_startup_gate as startup_cases
from test_package_checks import fixture, runtime_patch, APP, OTHER_APP, fixture_project, prepare_writer_fixture
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
        prepare_writer_fixture(self.native, self.project)
        self.files = {p.relative_to(self.native).as_posix(): p.read_bytes() for p in self.native.rglob('*') if p.is_file()}

    def tearDown(self):
        self.temp.cleanup()

    def test_wrong_app_id_never_starts_runtime(self):
        with patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}) as run:
            # v7.7: tiktok_finalize's appid step compares the target with the project's PlatformConfig first
            with self.assertRaisesRegex(ValueError, 'K_native_preparation_required'):
                build(self.native, OTHER_APP, self.out, resource_manifest=self.manifest, project=self.project, web=self.native)
            run.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_wrong_output_suffix_refused_before_any_runtime(self):
        out = self.root / 'looks-like-source.txt'
        with patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}) as run:
            with self.assertRaisesRegex(ValueError, r'\.zip'):
                build(self.native, APP, out, resource_manifest=self.manifest, project=self.project, web=self.native)
            run.assert_not_called()
        self.assertFalse(out.exists())

    def test_missing_packed_asset_refused_before_runtime(self):
        with patch('audit_packed_assets.audit', return_value={
                'passed': False, 'errors': ['missing fixture texture']}) as assets, \
                patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}) as run:
            with self.assertRaisesRegex(ValueError, 'missing fixture texture'):
                build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project, web=self.native)
            run.assert_not_called()
            self.assertTrue(assets.called)
        self.assertFalse(self.out.exists())

    def test_manifest_changed_during_runtime_refused_without_zip(self):
        def change(*args, **kwargs):
            self.manifest.write_text('{"resources": []}')
            return {'passed': True}
        with patch('audit_final_package_startup.audit_final_startup', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'manifest.*changed|resource manifest.*changed'):
                build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project, web=self.native)
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob('.tiktok-package-*')))

    def test_normal_writer_calls_runtime_once_and_reports_phase_timings(self):
        import audit_upload_startup
        with patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}) as run, \
                patch.object(audit_upload_startup, 'audit_files', wraps=audit_upload_startup.audit_files) as dependency:
            result = build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project, web=self.native)
        run.assert_called_once()
        self.assertTrue(run.call_args.kwargs['reuse_only'])
        self.assertEqual(dependency.call_count, 2)  # Native preflight, then the actual ZIP.
        self.assertTrue(result['expected_tree_exact'])
        self.assertEqual(set(result['check_timings']), {'static_preflight_seconds', 'total_seconds'})
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

    def test_cli_runs_once_per_delivery_and_never_in_writer(self):
        with patch('tiktok_cli_gate.verify', return_value={'passed': True, 'errors': []}) as cli, \
                patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}):
            result = build(self.native, APP, self.out, resource_manifest=self.manifest, project=self.project, web=self.native)
            cli.assert_not_called()
            records = [self.root / 'delivery.json', self.root / 'redelivery.json']
            for count, record in enumerate(records, start=1):
                with patch('prepare_delivery.tempfile.gettempdir', return_value=str(self.root / 'other-temp')), \
                        patch('prepare_delivery.writer_board', side_effect=ValueError('stop after final gate')):
                    with self.assertRaisesRegex(ValueError, 'stop after final gate'):
                        prepare(self.out, self.native, APP, record, project=self.project, resource_manifest=self.manifest)
                self.assertEqual(cli.call_count, count)
                cli.assert_called_with(str(self.out.resolve()), result['sha256'])
            receipts = [json.loads(Path(str(record) + '.size.json').read_text()) for record in records]
            self.assertNotEqual(receipts[0]['run_id'], receipts[1]['run_id'])

    def test_delivery_native_mutation_during_startup_refused(self):
        archive = self.root / 'input.zip'
        with patch('audit_final_package_startup.audit_final_startup', return_value={'passed': True}):
            build(self.native, APP, archive, resource_manifest=self.manifest, project=self.project, web=self.native)
        record = self.root / 'delivery.json'
        def mutate(*args, **kwargs):
            (self.native / 'child.js').write_text('changed = true;')
            return {'passed': True}
        # Reach the mutation guard with a synthetic writer fixture. Fresh CLI and
        # writer-evidence validation have separate tests; neither is live evidence here.
        with patch('prepare_delivery.tempfile.gettempdir', return_value=str(self.root / 'other-temp')), \
                patch('tiktok_cli_gate.verify', return_value={'passed': True, 'errors': []}), \
                patch('prepare_delivery.check', return_value={'unit_test': 'writer evidence boundary'}) as checked, \
                patch('prepare_delivery.audit_final_startup', side_effect=mutate) as startup:
            with self.assertRaisesRegex(ValueError, 'Native changed'):
                prepare(archive, self.native, APP, record, project=self.project, resource_manifest=self.manifest)
        checked.assert_called_once()
        startup.assert_called_once()
        self.assertTrue(startup.call_args.kwargs['reuse_only'])
        self.assertFalse(record.exists())


class StartupIdentity(unittest.TestCase):
    # Reuse setup only; do not run the same base tests a second time.
    setUp = startup_cases.FinalStartupGate.setUp
    tearDown = startup_cases.FinalStartupGate.tearDown
    save = startup_cases.FinalStartupGate.save
    call = startup_cases.FinalStartupGate.call
    def test_runtime_cannot_replace_native_after_binding_check(self):
        import audit_final_package_startup as gate
        def mutate(*args, **kwargs):
            (self.native / 'child.js').write_text('modified during execution;')
            return []
        with patch.object(gate.renderer, 'validate', return_value=[]), \
                patch.object(gate, 'validate_recovery', return_value=[]), \
                patch.object(gate, 'validate_runtime_report', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during'):
                self.call()

    def test_runtime_cannot_replace_recovery_evidence(self):
        import audit_final_package_startup as gate
        def mutate(*args, **kwargs):
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


# This module checks the original gate's own obligations with tiny fixtures.
# Keep the strict-six production boundary in its dedicated real-auditor tests.
from pathlib import Path as _AdFixturePath
import sys as _ad_fixture_sys
_ad_fixture_core = next(p/'remake-core/scripts' for p in _AdFixturePath(__file__).resolve().parents
                        if (p/'remake-core/scripts/fixture_ad_standard_scope.py').is_file())
_ad_fixture_sys.path.insert(0,str(_ad_fixture_core))
from fixture_ad_standard_scope import isolate as _isolate_ad_fixture
_isolate_ad_fixture(globals())

if __name__ == '__main__':
    unittest.main()
