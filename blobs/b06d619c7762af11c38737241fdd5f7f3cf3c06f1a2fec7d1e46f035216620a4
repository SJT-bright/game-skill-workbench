#!/usr/bin/env python3
"""K6_kit_module_old (v7.8, 总表 B30 C): old platform-kit source modules inside a 2.4 script bundle.

Bundles are built here the way Cocos 2.4 merges scripts (cc._RF.push(module, "<uuid>", "<Name>") ... cc._RF.pop()),
from the real kit texts: the current files and the previous versions kept in platform-kit/tools/kit_versions/.
Real packages (全民飞车漂移 v1 / v2 refused on RewardedService + SaveStore, v3 MissionFlow text only, v3.1 clean) are in
briefs/out/W87/RESULT.md. Run: python3 -B test_kit_module_versions.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from package_gates import kit_versions as K  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402

KIT = HERE.parent / 'assets' / 'platform-kit'


def bundle(*mods):
    out = []
    for i, (name, text) in enumerate(mods):
        # a crude minifier: comments and indentation go, property names and strings stay (what Creator keeps)
        body = re.sub(r'\s+', ' ', K.strip_comments(text))
        out.append('cc._RF.push(module,"%032x","%s");%s;cc._RF.pop();' % (i, name, body))
    return {'assets/main/index.js': ''.join(out).encode()}


class KitModuleVersions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = T.load_manifest()
        cls.man = {'files': m.files, 'version': m.version}
        cls.cur = {n: (KIT / 'assets/tiktok-platform' / (n + '.js')).read_text(encoding='utf-8') for n in K.SCRIPT_MODULES}

    def old(self, name, prefix):
        return next((KIT / 'tools/kit_versions' / name).glob(prefix + '*.txt')).read_text(encoding='utf-8')

    def ids(self, findings, level=None):
        return sorted((f['id'], f['evidence']['module']) for f in findings if level is None or f['level'] == level)

    def test_fingerprints_match_the_manifest(self):
        fps = K.load()
        self.assertEqual(K.stale_modules(fps, self.man), [])
        self.assertEqual(json.dumps(K.build(self.man), ensure_ascii=False, indent=1, sort_keys=True) + '\n',
                         (KIT / 'KIT_FINGERPRINTS.json').read_text(encoding='utf-8'),
                         'KIT_FINGERPRINTS.json is stale: run platform-kit/tools/build_kit_fingerprints.py')
        for name, entry in fps['modules'].items():
            self.assertEqual(entry['previous_without_text'], [], name + ': keep every previous text in tools/kit_versions')

    def test_current_kit_bundle_is_clean(self):
        files = bundle(*[(n, self.cur[n]) for n in K.SCRIPT_MODULES])
        self.assertEqual(K.verify(files, self.man, 'new', 2), [])

    def test_old_rewarded_and_savestore_block_a_new_game_warn_a_legacy_one(self):
        files = bundle(('RewardedService', self.old('RewardedService', '04121e95')), ('SaveStore', self.old('SaveStore', '954b5649')),
                       ('TikTokMissionService', self.cur['TikTokMissionService']))
        got = K.verify(files, self.man, 'new', 2)
        self.assertEqual(self.ids(got, 'block'), [('K6_kit_module_old', 'RewardedService'), ('K6_kit_module_old', 'SaveStore')])
        self.assertIn('previous sha 04121e95', next(f['message'] for f in got if f['evidence']['module'] == 'RewardedService'))
        self.assertEqual(self.ids(K.verify(files, self.man, 'legacy', 2), 'block'), [])
        self.assertEqual(len(K.verify(files, self.man, 'legacy', 2)), 2)

    def test_display_text_only_difference_warns(self):
        got = K.verify(bundle(('MissionFlow', self.old('MissionFlow', '7ea4980b'))), self.man, 'new', 2)
        self.assertEqual([(f['id'], f['level']) for f in got], [('K6_kit_module_old', 'warn')])
        self.assertIn('only display strings differ', got[0]['message'])

    def test_edited_copy_unknown_and_other_engines(self):
        text = self.cur['RewardedService']
        for word in sorted(set(x[2:] for x in K.load()['modules']['RewardedService']['current_only'] if x.startswith('p:')))[:9]:
            text = text.replace(word, word + 'Zz')
        got = K.verify(bundle(('RewardedService', text)), self.man, 'new', 2)
        self.assertEqual([(f['id'], f['level']) for f in got], [('K6_kit_module_unknown', 'warn')])
        self.assertEqual(K.verify(bundle(('RewardedService', self.old('RewardedService', '04121e95'))), self.man, 'new', 3), [])
        self.assertEqual(K.verify({'game.js': b'x'}, self.man, 'new', 2), [])

    def test_stale_fingerprints_warn_and_skip(self):
        fps = json.loads(json.dumps(K.load()))
        fps['modules']['RewardedService']['current_sha256'] = '0' * 64
        got = K.verify(bundle(('RewardedService', self.old('RewardedService', '04121e95'))), self.man, 'new', 2, fingerprints=fps)
        self.assertEqual([(f['id'], f['level']) for f in got], [('K6_fingerprints_stale', 'warn')])

    def test_wired_into_kit_parts(self):
        text = (HERE / 'package_gates' / 'kit_parts.py').read_text(encoding='utf-8')
        self.assertIn('kit_versions.verify(files', text)


if __name__ == '__main__':
    unittest.main(verbosity=1)
