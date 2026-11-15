import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from creator_asset_contract import module_meta, validate_bundle_names
from tiktok_finalize_steps.kit_sources import plugin_meta

HERE = Path(__file__).resolve().parent


class AssetProductionContract(unittest.TestCase):
    def test_normal_module_preserves_uuid_custom_fields_and_idempotence(self):
        old = json.dumps({'uuid': 'keep-me', 'isPlugin': True, 'loadPluginInEditor': True,
                          'custom': {'x': 1}, 'subMetas': {}}).encode()
        output = module_meta(old, 'assets/generated.js')
        row = json.loads(output)
        self.assertEqual(row['uuid'], 'keep-me')
        self.assertEqual(row['custom'], {'x': 1})
        self.assertFalse(row['isPlugin'])
        self.assertFalse(row['loadPluginInEditor'])
        self.assertEqual(module_meta(output, 'assets/generated.js'), output)

    def test_unknown_or_cross_engine_metadata_not_destroyed(self):
        for old in [b'bad-json', b'[]', b'{}', b'{"uuid":"x","importer":"javascript","userData":{"isPlugin":true}}']:
            with self.assertRaises(ValueError):
                module_meta(old, 'assets/generated.js')
        plugin = plugin_meta(None, 'assets/plugin.js')
        self.assertTrue(json.loads(plugin)['userData']['isPlugin'])

    def test_new_module_has_stable_uuid(self):
        self.assertEqual(module_meta(None, 'assets/generated.js'), module_meta(None, 'assets/generated.js'))
        self.assertNotEqual(module_meta(None, 'assets/other.js'), module_meta(None, 'assets/generated.js'))

    def test_generated_cli_repairs_metadata_and_check_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / 'assets/resources').mkdir(parents=True)
            (project / 'project.json').write_text('{"version":"2.4.15"}')
            cmd = [sys.executable, '-B', str(HERE / 'make_res_keys.py'), '--project', str(project), '--json']
            subprocess.run(cmd, check=True, capture_output=True)
            meta = project / 'assets/scripts/generated/ResKeys.js.meta'
            meta.write_text('{"uuid":"preserve","isPlugin":true,"loadPluginInEditor":true}')
            before = meta.read_bytes()
            result = subprocess.run(cmd + ['--check'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(json.loads(result.stdout)['metadata_stale'])
            self.assertEqual(meta.read_bytes(), before)
            subprocess.run(cmd, check=True, capture_output=True)
            self.assertEqual(json.loads(meta.read_text())['uuid'], 'preserve')
            self.assertFalse(json.loads(meta.read_text())['isPlugin'])
            self.assertEqual(subprocess.run(cmd + ['--check'], capture_output=True).returncode, 0)

    def test_engine3_plugin_metadata_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); (project / 'assets/resources').mkdir(parents=True)
            output = project / 'assets/generated.ts'
            meta = output.with_suffix('.ts.meta')
            original = plugin_meta(None, 'assets/generated.ts')
            meta.write_bytes(original)
            subprocess.run([sys.executable, '-B', str(HERE / 'make_res_keys.py'),
                            '--project', str(project), '--engine', '3', '--out', str(output)],
                           check=True, capture_output=True)
            self.assertEqual(meta.read_bytes(), original)

    def test_source_bundle_names_all_supported_metadata_forms(self):
        for fields in [{'isBundle': True, 'bundleName': 'main'},
                       {'isSubpackage': True, 'subpackageName': 'internal'},
                       {'userData': {'isBundle': True, 'bundleName': 'Main'}}]:
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as temp:
                project = Path(temp); (project / 'assets/textures').mkdir(parents=True)
                meta = project / 'assets/textures.meta'
                meta.write_text(json.dumps({'uuid': 'keep', **fields}))
                before = meta.read_bytes()
                with self.assertRaisesRegex(ValueError, 'reserved'):
                    validate_bundle_names(project)
                self.assertEqual(meta.read_bytes(), before)

    def test_valid_roots_and_duplicate_plans(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp); (project / 'assets/resources').mkdir(parents=True)
            plans = [{'directory': 'assets/resources', 'name': 'resources'},
                     {'directory': 'assets/themes', 'name': 'themes'}]
            self.assertEqual(validate_bundle_names(project, plans)['assets/themes'], 'themes')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                validate_bundle_names(project, plans + [{'directory': 'assets/other', 'name': 'THEMES'}])
            with self.assertRaisesRegex(ValueError, 'reserved'):
                validate_bundle_names(project, [{'directory': 'assets/other', 'name': 'resources'}])


if __name__ == '__main__':
    unittest.main()
