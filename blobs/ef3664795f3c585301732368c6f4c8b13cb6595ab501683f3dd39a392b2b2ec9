"""v7.8: which runner inputs prove the scene bundle (audit_native_startup_renderer.scene_bundle_inputs).

A Cocos 3.x SystemJS TikTok build can keep its start scene in subpackages/<name>/ with no scene under assets/; the
renderer evidence check then refused it ("actual scene bundle identity required"). A Codex game session fixed this by
editing the installed English pack directly (2026-10-30 09:52); v7.8 merges that fix with these cases.
"""
import json
import tempfile
import unittest
from pathlib import Path

from audit_native_startup_renderer import scene_bundle_inputs

PROFILE_3X = {'control_profile': 'cocos3_systemjs_native_v1'}


class SceneBundleInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='scene inputs ')
        self.native = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, rel, data):
        path = self.native / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')
        return rel

    def test_assets_bundle_counts_for_every_profile(self):
        inputs = {'game.js', 'assets/main/index.js'}
        self.assertEqual(scene_bundle_inputs({}, self.native, inputs), ['assets/main/index.js'])
        self.assertEqual(scene_bundle_inputs(PROFILE_3X, self.native, inputs), ['assets/main/index.js'])

    def test_3x_start_scene_in_a_subpackage_counts(self):
        rel = self.config('subpackages/start/config.json', {'scenes': [{'url': 'db://assets/start.scene'}]})
        self.assertEqual(scene_bundle_inputs(PROFILE_3X, self.native, {'game.js', rel}), [rel])

    def test_subpackage_without_scenes_does_not_count(self):
        rel = self.config('subpackages/audio/config.json', {'scenes': [], 'paths': {}})
        self.assertEqual(scene_bundle_inputs(PROFILE_3X, self.native, {'game.js', rel}), [])

    def test_unreadable_subpackage_config_does_not_count(self):
        bad = self.native / 'subpackages' / 'start' / 'config.json'
        bad.parent.mkdir(parents=True)
        bad.write_text('{not json', encoding='utf-8')
        self.assertEqual(scene_bundle_inputs(PROFILE_3X, self.native, {'subpackages/start/config.json'}), [])

    def test_2x_profile_keeps_requiring_assets(self):
        rel = self.config('subpackages/start/config.json', {'scenes': [{'url': 'db://assets/start.scene'}]})
        self.assertEqual(scene_bundle_inputs({'control_profile': 'cocos24_tiktok_v1'}, self.native, {rel}), [])
        self.assertEqual(scene_bundle_inputs({}, self.native, {rel}), [])


if __name__ == '__main__':
    unittest.main()
