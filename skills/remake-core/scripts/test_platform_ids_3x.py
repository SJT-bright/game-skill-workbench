#!/usr/bin/env python3
"""生成时预防 R4R4 (R4Q5 留下的, 奔跑吧巨人 is Cocos 3.x): tiktok_finalize_steps/plugin3x_scan.py runs the same
foreign_config_findings as platform-kit/tools/check_kit_project.py on the 3.x PlatformConfig.

  1 shared   3.x game on the kit template's shared test app (Saul 2026-10-29) with its own gameId -> no finding
  2 copied   appId + ad unit of another game (peers) -> K_platform_ids_foreign block (new remake), warn (English),
             info (legacy); the old plugin3x_scan reports nothing
  3 gameId   only the gameId is shared -> K_W_platform_ids warning, no block; recorded ids -> clean
Run: python3 test_platform_ids_3x.py
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tiktok_finalize_steps import Ctx  # noqa: E402
from tiktok_finalize_steps import plugin3x_scan as P  # noqa: E402

TEMPLATE = (HERE.parent / 'assets' / 'platform-kit' / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').read_text(
    encoding='utf-8')
PLUGIN = (HERE.parent / 'assets' / 'platform-kit' / 'plugins-3x' / 'PlatformConfig.plugin.js').read_text(encoding='utf-8')


def config(text, game, app=None, ad=None):
    t = text.replace("gameId: 'change-me'", "gameId: '%s'" % game)
    if app:
        t = t.replace("appId: '7683427172773644296'", "appId: '%s'" % app)
    if ad:
        t = t.replace("ad7683064432721709074", ad)
    return t


def game(root, name, rel, text):
    p = Path(root) / name / rel
    p.parent.mkdir(parents=True)
    p.write_text(text, encoding='utf-8')
    if rel.endswith('.plugin.js'):   # imported as plugin, as sync writes it
        (p.parent / (p.name + '.meta')).write_text(
            '{"userData": {"isPlugin": true, "loadPluginInWeb": true, "loadPluginInNative": true, '
            '"loadPluginInMiniGame": true}}', encoding='utf-8')
    return Path(root) / name


def run(proj, peers, policy='new', board='remake'):
    ctx = Ctx('source', proj, engine=3, policy=policy, board=board, options={'peers': [str(peers)]})
    r = P.apply(ctx)
    return {f['id']: f.get('level') for f in r.get('blocks', []) + r.get('warnings', [])}, r


class PlatformIds3x(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.peers = Path(self.tmp) / 'games'
        # another (2.4) game on this machine with its own app and ad unit
        game(self.peers, 'OtherGame', 'assets/tiktok-platform/PlatformConfig.js',
             config(TEMPLATE, 'othergame', app='7000000000000000001', ad='ad7000000000000000002'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_shared_test_app_passes(self):
        proj = game(self.tmp, 'GiantRush', 'assets/tiktok-platform/PlatformConfig.plugin.js', config(PLUGIN, 'giantrush'))
        ids, r = run(proj, self.peers)
        self.assertEqual(ids, {}, r)

    def test_2_copied_ids_blocked_new_warn_english_info_legacy(self):
        text = config(PLUGIN, 'giantrush', app='7000000000000000001', ad='ad7000000000000000002')
        proj = game(self.tmp, 'GiantRush', 'assets/tiktok-platform/PlatformConfig.plugin.js', text)
        ids, r = run(proj, self.peers)
        self.assertEqual(ids.get('K_platform_ids_foreign'), 'block', r)
        self.assertEqual(r['state'], 'conflict')
        self.assertIn('OtherGame', str(r['blocks']))
        ids, _ = run(proj, self.peers, board='localize')
        self.assertEqual(ids.get('K_platform_ids_foreign'), 'warn')
        ids, r = run(proj, self.peers, policy='legacy')
        self.assertNotIn('K_platform_ids_foreign', ids)
        self.assertTrue(any('K_platform_ids_foreign' in x for x in r.get('info', [])))

    def test_3_shared_gameid_warns_only_record_clears(self):
        proj = game(self.tmp, 'OtherGameCopy', 'assets/tiktok-platform/PlatformConfig.plugin.js', config(PLUGIN, 'othergame'))
        ids, r = run(proj, self.peers)
        self.assertEqual(ids, {'K_W_platform_ids': 'warn'}, r)
        self.assertEqual(r['state'], 'kit_current')
        # own ids written in docs/platform/platform_ids.json are allowed
        own = game(self.tmp, 'Mine', 'assets/tiktok-platform/PlatformConfig.plugin.js',
                   config(PLUGIN, 'mine', app='7111111111111111111'))
        ids, _ = run(own, self.peers)
        self.assertEqual(ids, {'K_W_platform_ids': 'warn'})          # not recorded yet
        (own / 'docs' / 'platform').mkdir(parents=True)
        (own / 'docs' / 'platform' / 'platform_ids.json').write_text(
            '{"appId": "7111111111111111111", "source": "TikTok console"}', encoding='utf-8')
        ids, r = run(own, self.peers)
        self.assertEqual(ids, {}, r)

    def test_4_own_build_output_is_not_another_game(self):
        # 企鹅雪道 / SLS35: build/web-mobile/src/assets/tiktok-platform/PlatformConfig.plugin.js is the game's own copy
        text = config(PLUGIN, 'penguinslide', app='7222222222222222222')
        proj = game(self.tmp, 'PenguinSlide', 'assets/tiktok-platform/PlatformConfig.plugin.js', text)
        game(proj, 'build', 'web-mobile/src/assets/tiktok-platform/PlatformConfig.plugin.js', text)
        (proj / 'docs' / 'platform').mkdir(parents=True)
        (proj / 'docs' / 'platform' / 'platform_ids.json').write_text('{"appId": "7222222222222222222"}', encoding='utf-8')
        ctx = Ctx('source', proj, engine=3, policy='new', board='remake', options={'peers': [str(proj)]})
        r = P.apply(ctx)
        self.assertEqual(r.get('blocks', []) + r.get('warnings', []), [], r)


if __name__ == '__main__':
    unittest.main(verbosity=2)
