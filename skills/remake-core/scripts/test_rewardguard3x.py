#!/usr/bin/env python3
"""生成时预防 R4G2: the 3.x rewarded-ad guard (part rewardguard3x) and the 3.x CapsuleAuto (#29) come from finalize.

问题普查 20261104: 广告关掉后锁死 33/36 款、超时口径不对 31/33、迟到发奖 14/14 (P01-2, R4A did the 2.4 side);
capsule_overlap 15/15, screen_fit_wrong 21/26 (#29). Before R4G2 a 3.x game got no parts/rewarded-guard.js and no
CapsuleAuto at all (capsule_auto was 2.4 only). Every case marked OLD fails on the 简化.11.14 + 第一波 base.
  1 OLD 3.x source     build-templates/bytedance-mini-game/game.js gets ONE guard line right after web-adapter, the
                       guard file (kit sha = 2.4 rewarded24) is in build-templates; a build made from it needs no change
  2 OLD 3.x native     a build game.js (sync --native / writer) gets the line once, after web-adapter; 2nd run no change
  3     legacy         a legacy 3.x build: no guard written
  4 OLD package check  the 3.x package made in 2 (only the kit guard calls createRewardedVideoAd) needs no rewarded-ad
                       regression (cocos-game-check ad_regression.needs_regression / runtime_regression rewarded_ads)
  5 OLD 3.x capsule    source on a new 3.x remake project installs CapsuleLayout.plugin.js + CapsuleAuto.plugin.js (kit
                       bytes) with the import-as-plugin .meta; 2nd run no change
  6     capsule warn   English (localize) 3.x project with a top bar: nothing written, K_W_capsule_auto names the bar
  7     not required   kit_sources does not install the capsule plugins and K1_plugin3x does not require them
Run: python3 test_rewardguard3x.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CHECK = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(1, str(CHECK))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import capsule_auto, kit_sources  # noqa: E402
from package_gates import kit_parts  # noqa: E402
from test_finalize_hostshim_boot import GAME3X, build, copy_templates, line_index, manifest, native, project, sha, \
    tree_sha  # noqa: E402

GUARD_LINE = "require('./rewarded-guard.js')"
ADAPTER = "require('./web-adapter')"
SCENE3X = [
    {'__type__': 'cc.SceneAsset', '_name': 'Home'},
    {'__type__': 'cc.Scene', '_name': 'Home', '_children': [{'__id__': 2}]},
    {'__type__': 'cc.Node', '_name': 'Canvas', '_parent': {'__id__': 1}, '_children': [{'__id__': 5}],
     '_lpos': {'x': 360, 'y': 640}, '_active': True, '_components': [{'__id__': 3}, {'__id__': 4}]},
    {'__type__': 'cc.UITransform', 'node': {'__id__': 2}, '_contentSize': {'width': 720, 'height': 1280},
     '_anchorPoint': {'x': 0.5, 'y': 0.5}},
    {'__type__': 'cc.Canvas', 'node': {'__id__': 2}},
    {'__type__': 'cc.Node', '_name': 'TopBar', '_parent': {'__id__': 2}, '_children': [],
     '_lpos': {'x': 0, 'y': 600}, '_active': True, '_components': [{'__id__': 6}]},
    {'__type__': 'cc.UITransform', 'node': {'__id__': 5}, '_contentSize': {'width': 720, 'height': 80},
     '_anchorPoint': {'x': 0.5, 'y': 0.5}},
]


def guard_part(m):
    parts = [n for n, p in m.parts_for(3) if p.get('step') == 'rewardguard']
    return m.parts[parts[0]] if parts else None


class RewardGuard3x(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='r4g2-'))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.m = manifest()

    def guard_once_after_adapter(self, g):
        hits, adapter = line_index(g, GUARD_LINE), line_index(g, ADAPTER)
        self.assertEqual(len(hits), 1, 'need exactly one guard line:\n' + g)
        self.assertGreater(hits[0], adapter[0], 'guard line must come after web-adapter')
        self.assertIn('(null, globalThis.TTMinis&&TTMinis.game||globalThis.tt)', g.split('\n')[hits[0]])

    def test_1_3x_source_template(self):
        p = project(self.d / 'p', 3, template_game=GAME3X)
        rec = F.finalize_source(p, 'remake', policy='new', manifest=self.m,
                                steps=('kit_sources', 'build_templates', 'startup'))
        t = p / 'build-templates' / 'bytedance-mini-game'
        self.guard_once_after_adapter((t / 'game.js').read_text())
        self.assertTrue((t / 'rewarded-guard.js').is_file(), 'source: rewarded-guard.js not in build-templates')
        kit_guard = self.m.files['parts/rewarded-guard.js']['sha256']
        self.assertEqual(sha(t / 'rewarded-guard.js'), kit_guard, 'same file as the 2.4 guard (kit_guard_hashes)')
        self.assertEqual(guard_part(self.m)['file']['sha256'], kit_guard)
        self.assertFalse([b for b in rec['blocks'] if b.get('step') == 'startup'], rec['blocks'])
        b = build(self.d / 'b', 3)
        copy_templates(p, b, 3)
        before = tree_sha(b)
        self.assertEqual(native(b, self.m)['blocks'], [])
        self.assertEqual(tree_sha(b), before, 'a build made from the wired template needs no change')

    def test_2_3x_native_once(self):
        b = build(self.d / 'b', 3)
        r = native(b, self.m)
        self.assertEqual(r['blocks'], [])
        self.guard_once_after_adapter((b / 'game.js').read_text())
        before = tree_sha(b)
        native(b, self.m)
        self.assertEqual(tree_sha(b), before, 'second run must not add a second line')
        from tiktok_finalize_steps import startup
        self.assertEqual(startup.verify(T.Ctx('native', b).files(), self.m, 'new', 3), [])

    def test_3_legacy_not_installed(self):
        b = build(self.d / 'b', 3)
        native(b, self.m, policy='legacy')
        self.assertNotIn(GUARD_LINE, (b / 'game.js').read_text())
        self.assertFalse((b / 'rewarded-guard.js').exists())

    def test_4_guard_only_3x_package_needs_no_ad_regression(self):
        import ad_regression
        import runtime_regression
        b = build(self.d / 'b', 3)
        native(b, self.m)
        files = T.Ctx('native', b).files()
        self.assertIn(b'createRewardedVideoAd', files.get('rewarded-guard.js', b''), 'guard not installed')
        self.assertFalse(ad_regression.needs_regression(files), 'kit guard alone must not require the ad regression')
        self.assertFalse(runtime_regression.predicate('rewarded_ads', files, {}))


class CapsuleAuto3x(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix='r4g2c-'))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.m = manifest()

    def proj(self):
        p = project(self.d / 'p', 3)
        (p / 'assets' / 'scenes').mkdir(parents=True)
        (p / 'assets' / 'scenes' / 'Home.scene').write_text(json.dumps(SCENE3X))
        return p

    def ctx(self, p, board='remake', policy='new'):
        return T.Ctx('source', p, board=board, engine=3, policy=policy, manifest=self.m)

    def test_5_new_3x_installs_plugins(self):
        p = self.proj()
        out = capsule_auto.apply(self.ctx(p))
        self.assertEqual(out['blocks'], [])
        for name in ('CapsuleLayout', 'CapsuleAuto'):
            dest = p / 'assets' / 'tiktok-platform' / ('%s.plugin.js' % name)
            self.assertTrue(dest.is_file(), '%s.plugin.js not installed on 3.x' % name)
            kit = T.KIT_DIR / 'plugins-3x' / ('%s.plugin.js' % name)
            self.assertEqual(dest.read_bytes(), kit.read_bytes())
            meta = json.loads((dest.parent / (dest.name + '.meta')).read_text())
            self.assertTrue(meta['userData']['isPlugin'] and meta['userData']['loadPluginInMiniGame'])
        before = tree_sha(p)
        again = capsule_auto.apply(self.ctx(p))
        self.assertEqual(again['changed'], [])
        self.assertEqual(tree_sha(p), before)

    def test_6_localize_3x_warns(self):
        p = self.proj()
        out = capsule_auto.apply(self.ctx(p, board='localize'))
        self.assertEqual(out['changed'], [])
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_capsule_auto'])
        self.assertIn('TopBar', out['warnings'][0]['message'])
        self.assertFalse((p / 'assets' / 'tiktok-platform' / 'CapsuleAuto.plugin.js').exists())

    def test_7_not_in_kit_sources_or_k1(self):
        p = self.proj()
        kit_sources.apply(self.ctx(p, board='localize'))
        self.assertFalse((p / 'assets' / 'tiktok-platform' / 'CapsuleAuto.plugin.js').exists())
        names = [n for n, _ in kit_parts.kit_plugins(self.m)]
        self.assertNotIn('CapsuleAuto', names)
        self.assertNotIn('CapsuleLayout', names)
        self.assertIn('RewardedService', names)


if __name__ == '__main__':
    unittest.main(verbosity=2)
