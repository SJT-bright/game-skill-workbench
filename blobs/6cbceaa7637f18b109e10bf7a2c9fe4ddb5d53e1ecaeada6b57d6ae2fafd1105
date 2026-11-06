#!/usr/bin/env python3
"""check_machine.py --project: engine version vs the support table (R4N3, 补查2 第 1 组 1a).

方块收割者 (Creator 2.1.2, no TikTok build target, no cc.assetManager for ResLoader / ResKeys) and 合成进化恐龙
(3.5.0, not installed) lost their first hour before anyone said which engine to use. Fake project.json /
package.json only: no Creator, no browser.  python3 test_engine_route.py
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_machine as CM  # noqa: E402


def project(tmp, version, style='2x'):
    p = Path(tmp) / ('p_' + version.replace('.', '_') + '_' + style)
    (p / 'assets').mkdir(parents=True)
    if style == '2x':
        (p / 'project.json').write_text(json.dumps({'engine': 'cocos-creator-js', 'packages': 'packages',
                                                    'version': version}), encoding='utf-8')
    elif style == '3x_package':
        (p / 'package.json').write_text(json.dumps({'name': 'g', 'creator': {'version': version}}), encoding='utf-8')
    else:  # 3.x project.json written with creator.version
        (p / 'project.json').write_text(json.dumps({'creator': {'version': version}}), encoding='utf-8')
    return p


def names(rows):
    return [r['part'] for r in rows]


class EngineRoute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, version, style='2x'):
        return CM.engine_check(project(self.tmp.name, version, style))

    def test_2_1_2_upgrades_a_copy_to_2_4_15(self):
        e = self.check('2.1.2')
        self.assertEqual(e['status'], 'route')
        self.assertEqual(e['route'], 'upgrade_copy_to_2.4.15')
        self.assertEqual(e['build_as'], '2.4.15')
        self.assertIn('2.4.15', e['say'])
        self.assertIn('副本', e['say'])
        self.assertIn('ResLoader', names(e['install']))  # after the upgrade the 2.4 parts apply
        self.assertIn('startup24', names(e['install']))

    def test_2_3_also_routes(self):
        self.assertEqual(self.check('2.3.4')['route'], 'upgrade_copy_to_2.4.15')

    def test_3_5_0_installs_same_minor_and_marks_untested_parts(self):
        for style in ('3x_package', '3x_project'):
            e = self.check('3.5.0', style)
            self.assertEqual(e['status'], 'route', style)
            self.assertEqual(e['route'], 'install_same_minor_then_table')
            self.assertIn('3.5.x', e['say'])
            self.assertEqual(e['build_as'], '3.5.0')
            self.assertTrue(e['install'] and all(p['untested'] for p in e['install'] if p['part'].endswith('3x')))
            self.assertNotIn('touch24', names(e['install']))  # 2.4 parts never go on a 3.x project

    def test_2_4_15_is_supported_with_every_2_4_part(self):
        e = self.check('2.4.15')
        self.assertEqual(e['status'], 'supported')
        got = names(e['install'])
        for part in ('startup24', 'touch24', 'rewarded', 'ResLoader', 'ResKeys', 'AudioService'):
            self.assertIn(part, got)
        self.assertEqual(e['skip'], [])

    def test_2_4_3_keeps_its_main_js(self):
        e = self.check('2.4.3')
        self.assertEqual(e['status'], 'supported')
        self.assertIn('startup24', names(e['skip']))
        self.assertIn('ResLoader', names(e['install']))

    def test_3_8_x_is_supported_and_tested(self):
        e = self.check('3.8.8', '3x_package')
        self.assertEqual(e['status'], 'supported')
        self.assertIn('rewarded3x', names(e['install']))
        self.assertIn('ResLoader', names(e['install']))
        self.assertFalse(any(p['untested'] for p in e['install']))
        self.assertNotIn('startup24', names(e['install']) + names(e['skip']))

    def test_no_asset_manager_means_no_resloader(self):
        m = CM.kit_manifest()
        install, skip = CM.part_plan('2.1.2', m)  # what would go on the original without the upgrade
        self.assertNotIn('ResLoader', names(install))
        self.assertNotIn('ResKeys', names(install))
        self.assertIn('ResLoader', names(skip))
        self.assertIn('cc.assetManager', [s['why'] for s in skip if s['part'] == 'ResKeys'][0])

    def test_unsupported_major(self):
        e = self.check('1.10.2')
        self.assertEqual(e['status'], 'unsupported')
        self.assertIsNone(e['build_as'])

    def test_collect_puts_the_route_first(self):
        p = project(self.tmp.name, '2.1.2')
        rows = CM.collect(p, quick=True)
        self.assertEqual(rows[0]['name'], '引擎版本和平台零件')
        self.assertFalse(rows[0]['ok'])
        self.assertIn('引擎路线', CM.say(rows).splitlines()[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
