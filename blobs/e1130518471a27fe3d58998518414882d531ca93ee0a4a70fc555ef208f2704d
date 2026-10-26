"""Update-writer contracts using real resource discovery, no game execution."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import publish_resource_profile as writer


class ProfilePublication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='profile update ')
        self.root = Path(self.temp.name)
        self.native = self.root / 'native'
        self.native.mkdir()
        self.source = b"cc.resources.load('icons/'+chosen,cc.SpriteFrame)"
        (self.native / 'main.js').write_bytes(self.source)
        (self.native / 'config.json').write_text(json.dumps({
            'name': 'resources', 'types': ['cc.SpriteFrame'], 'paths': {'0': ['icons/a', 0]}}))
        (self.native / 'items.json').write_bytes(b'["cc.JsonAsset",{"id":"a"}]')
        self.profile = {'source_sha256': {'main.js': writer.sha(self.source)},
                        'resolutions': {'main.js:0': {'bundles': ['resources'], 'paths': ['icons/a'],
                            'kind': 'load', 'type': 'cc.SpriteFrame', 'unknown_receiver': False,
                            'reason': 'Synthetic exact finite choice table.'}}, 'escapes': {}}
        self.profile_path = self.root / 'profile.json'
        self.profile_path.write_text(json.dumps(self.profile))
        self.registry = self.root / 'registry.json'
        self.registry.write_text(json.dumps({'unrelated': {'source_sha256': {}, 'metadata': 'keep'}}))

    def tearDown(self):
        self.temp.cleanup()

    def publish(self):
        return writer.publish(self.profile_path, self.native, 'fixture', self.registry)

    def assert_clean(self):
        self.assertFalse(self.registry.with_suffix('.json.lock').exists())
        self.assertEqual(list(self.root.glob('.registry.json-*')), [])

    def test_two_consecutive_updates_are_portable_and_idempotent(self):
        first = self.publish()
        before = self.registry.read_bytes()
        modified = self.registry.stat().st_mtime_ns
        second = self.publish()
        value = json.loads(before)['fixture']
        self.assertTrue(first['changed'])
        self.assertFalse(second['changed'])
        self.assertEqual(first['registry_sha256'], second['registry_sha256'])
        self.assertNotIn('profile_ref', value)
        self.assertEqual(value['data_digest_kind'], 'serialized-json-assets-v1')
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(self.registry.stat().st_mtime_ns, modified)
        self.assertEqual(json.loads(before)['unrelated']['metadata'], 'keep')
        self.assert_clean()

    def test_updated_source_keeps_existing_constraint_and_other_entry(self):
        self.publish()
        entries = json.loads(self.registry.read_text())
        entries['fixture']['review_note'] = {'reviewer': 'original'}
        digest = entries['fixture']['data_digest']
        self.registry.write_text(json.dumps(entries))
        source = self.source + b';// unrelated edit'
        (self.native / 'main.js').write_bytes(source)
        self.profile['source_sha256']['main.js'] = writer.sha(source)
        self.profile_path.write_text(json.dumps(self.profile))
        self.publish()
        updated = json.loads(self.registry.read_text())
        self.assertEqual(updated['fixture']['data_digest'], digest)
        self.assertEqual(updated['fixture']['review_note'], {'reviewer': 'original'})
        self.assertEqual(updated['unrelated'], entries['unrelated'])

    def test_changed_semantic_data_refuses_without_resigning(self):
        self.publish()
        before = self.registry.read_bytes()
        (self.native / 'items.json').write_bytes(b'["cc.JsonAsset",{"id":"b"}]')
        with self.assertRaisesRegex(ValueError, 'semantic data changed'):
            self.publish()
        self.assertEqual(self.registry.read_bytes(), before)
        self.assert_clean()

    def test_stale_source_and_missing_path_cannot_publish(self):
        original = self.registry.read_bytes()
        for kind in ('stale_source', 'missing_resource'):
            with self.subTest(kind=kind):
                value = copy.deepcopy(self.profile)
                if kind == 'stale_source':
                    value['source_sha256']['main.js'] = '0' * 64
                else:
                    value['resolutions']['main.js:0']['paths'] = ['missing']
                self.profile_path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    self.publish()
                self.assertEqual(self.registry.read_bytes(), original)
                self.assert_clean()

    def test_profile_ref_input_refused_and_matching_old_ref_migrates(self):
        old = self.root / 'old-profile.json'
        old.write_text(json.dumps(self.profile))
        entries = json.loads(self.registry.read_text())
        entries['fixture'] = {'source_sha256': self.profile['source_sha256'],
                              'profile_ref': {'path': str(old), 'sha256': writer.sha(old.read_bytes())}}
        self.registry.write_text(json.dumps(entries))
        self.publish()
        self.assertNotIn('profile_ref', json.loads(self.registry.read_text())['fixture'])
        before = self.registry.read_bytes()
        self.profile_path.write_text(json.dumps(entries['fixture']))
        with self.assertRaisesRegex(ValueError, 'complete reviewed profile'):
            self.publish()
        self.assertEqual(before, self.registry.read_bytes())

    def test_conflicting_metadata_and_unknown_call_stay_refused(self):
        self.publish()
        entries = json.loads(self.registry.read_text())
        entries['fixture']['review_note'] = 'original'
        self.registry.write_text(json.dumps(entries))
        before = self.registry.read_bytes()
        value = dict(self.profile, review_note='replacement')
        self.profile_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'constraint changed'):
            self.publish()
        self.profile_path.write_text(json.dumps(self.profile))
        (self.native / 'extra.js').write_bytes(b'cc.resources.load(unknown,cc.SpriteFrame)')
        with self.assertRaisesRegex(ValueError, 'unresolved dynamic'):
            self.publish()
        self.assertEqual(before, self.registry.read_bytes())

    def test_noncooperating_registry_change_is_not_overwritten(self):
        original_prepare = writer.prepare
        replacement = b'{"someone-else":{"value":123}}'
        def concurrent(*args):
            result = original_prepare(*args)
            self.registry.write_bytes(replacement)
            return result
        with patch.object(writer, 'prepare', side_effect=concurrent):
            with self.assertRaisesRegex(ValueError, 'registry changed'):
                self.publish()
        self.assertEqual(self.registry.read_bytes(), replacement)
        self.assert_clean()

    def test_profile_or_native_change_during_validation_leaves_registry(self):
        original_prepare = writer.prepare
        before = self.registry.read_bytes()
        for target in ('profile', 'native'):
            with self.subTest(target=target):
                self.profile_path.write_text(json.dumps(self.profile))
                (self.native / 'main.js').write_bytes(self.source)
                def concurrent(*args):
                    result = original_prepare(*args)
                    path = self.profile_path if target == 'profile' else self.native / 'main.js'
                    path.write_bytes(path.read_bytes() + b' ')
                    return result
                with patch.object(writer, 'prepare', side_effect=concurrent):
                    with self.assertRaisesRegex(ValueError, 'changed during'):
                        self.publish()
                self.assertEqual(self.registry.read_bytes(), before)
                self.assert_clean()

    def test_busy_writer_fails_without_removing_other_lock(self):
        lock = self.registry.with_suffix('.json.lock')
        lock.write_text('another writer')
        with self.assertRaises(FileExistsError):
            self.publish()
        self.assertEqual(lock.read_text(), 'another writer')
        lock.unlink()

    def test_two_registered_profiles_preserve_both_entries(self):
        self.publish()
        original = json.loads(self.registry.read_text())['fixture']
        # Two names for the same source remain ambiguous, as in the auditor.
        with self.assertRaisesRegex(ValueError, 'ambiguous reviewed'):
            writer.publish(self.profile_path, self.native, 'duplicate', self.registry)
        changed = self.source + b';// another exact program'
        (self.native / 'main.js').write_bytes(changed)
        self.profile['source_sha256']['main.js'] = writer.sha(changed)
        self.profile_path.write_text(json.dumps(self.profile))
        result = writer.publish(self.profile_path, self.native, 'second', self.registry)
        self.assertEqual(result['resources'], 1)
        self.assertEqual(set(json.loads(self.registry.read_text())), {'unrelated', 'fixture', 'second'})
        self.assertEqual(json.loads(self.registry.read_text())['fixture'], original)

    def test_cli_reports_real_receipt(self):
        run = subprocess.run([sys.executable, str(Path(writer.__file__)), '--profile', str(self.profile_path),
                              '--native', str(self.native), '--name', 'fixture', '--registry', str(self.registry)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        receipt = json.loads(run.stdout)
        self.assertTrue(receipt['portable'])
        self.assertEqual(receipt['resources'], 1)

    def test_existing_live_data_domain_is_not_frozen(self):
        domain = {'path': 'items.json', 'kind': 'mira-cosmetics-unlock-v1', 'asset_name': 'unlock_table'}
        self.profile['data_domains'] = {'items': domain}
        self.profile['resolutions']['main.js:0']['data_domain'] = 'items'
        self.profile_path.write_text(json.dumps(self.profile))
        for ids in [['hero_01', 'hero_02'], ['hero_01', 'hero_02', 'hero_03']]:
            data = ['cc.JsonAsset', 0, 0, 0, 0, [[0, 'unlock_table', {'items': [{'id': value} for value in ids]}]]]
            (self.native / 'items.json').write_text(json.dumps(data))
            catalog = {'name': 'resources', 'types': ['cc.SpriteFrame'],
                       'paths': {str(i): [value, 0] for i, value in enumerate(ids)}}
            (self.native / 'config.json').write_text(json.dumps(catalog))
            result = self.publish()
            self.assertEqual(result['resources'], len(ids) - 1)
            row = json.loads(self.registry.read_text())['fixture']
            self.assertEqual(row['data_domains'], {'items': domain})
            self.assertNotIn('data_digest', row)


if __name__ == '__main__':
    unittest.main()
