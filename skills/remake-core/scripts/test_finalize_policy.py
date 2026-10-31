#!/usr/bin/env python3
"""New game or legacy game (v7.7 W-B, design D77 section 2 + finding [4]).

Synthetic: not on the list = new; a new-game marker beats a list match (a marker only makes things stricter, and
there is no way to write a legacy marker); unique asset uuids need >= ASSET_MIN and >= ASSET_SHARE of the stored ones.
Real (read only, skipped when the folders are missing):
  - scene uuids read from the source and from the build are the same set for MergeShot2048 pkg85
    (_src/EnglishProject vs pkg85), Marlows R6 (source ZIP vs TikTok ZIP) and SorensRivet r22 (source ZIP vs
    native ZIP);
  - against the draft KIT/LEGACY_GAMES.json those three are legacy, while a starter pack that only shares template
    uuids (projects/duo-jump, 11 packs share its scene) is new.
Run: python3 test_finalize_policy.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402

J = H.J
WORKSHOP = Path('/Users/sijunting/Downloads/！自制游戏/启动包工坊')
U1 = '1b2c3d4e-0000-4000-8000-00000000abcd'


def listed(scenes=(), assets=()):
    return {'games': [{'name': 'g', 'folder': 'J/g', 'scene_uuids': list(scenes), 'asset_uuids': list(assets)}]}


def project(root, scene=U1):
    (root / 'assets').mkdir(parents=True)
    (root / 'assets' / 'Main.fire.meta').write_text(json.dumps({'uuid': scene, 'importer': 'scene'}))
    return root


class Rules(unittest.TestCase):
    def test_not_listed_is_new(self):
        p = project(H.tmpdir(self) / 'p')
        self.assertEqual(P.decide(project=p, legacy={'games': []})['policy'], 'new')
        self.assertEqual(P.decide(uuids=[], legacy={'games': []})['policy'], 'new')
        self.assertEqual(P.decide(uuids=[], legacy={'games': [], 'unlisted_policy': 'marker_only'})['policy'], 'new')

    def test_listed_scene_is_legacy_marker_makes_new(self):
        p = project(H.tmpdir(self) / 'p')
        self.assertEqual(P.decide(project=p, legacy=listed([U1]))['policy'], 'legacy')
        P.write_marker(p, 'remake', '2.0')
        self.assertEqual(P.decide(project=p, legacy=listed([U1]))['policy'], 'new')

    def test_no_legacy_marker_exists(self):
        p = project(H.tmpdir(self) / 'p')
        data = P.write_marker(p, 'localize', '2.0', reason='adopt')
        self.assertEqual(data['policy'], 'new')
        (p / '.tiktok-kit' / 'policy.json').write_text(json.dumps({'policy': 'legacy'}))
        out = P.decide(project=p, legacy={'games': []})
        self.assertEqual(out['policy'], 'new')                  # a "legacy" marker is ignored, not obeyed

    def test_marker_survives_reinit_created_kept(self):
        p = project(H.tmpdir(self) / 'p')
        first = P.write_marker(p, 'remake', '2.0')
        again = P.write_marker(p, 'remake', '2.0', reason='adopt')
        self.assertEqual(first['created'], again['created'])

    def test_asset_threshold(self):
        stored = ['00000000-0000-4000-8000-%012d' % i for i in range(20)]
        legacy = listed(assets=stored)
        self.assertEqual(P.decide(uuids=[], assets=stored[:P.ASSET_MIN - 1], legacy=legacy)['policy'], 'new')
        self.assertEqual(P.decide(uuids=[], assets=stored[:P.ASSET_MIN], legacy=legacy)['policy'], 'legacy')
        big = listed(assets=stored * 1 + ['10000000-0000-4000-8000-%012d' % i for i in range(80)])
        self.assertEqual(P.decide(uuids=[], assets=stored[:P.ASSET_MIN], legacy=big)['policy'], 'new')

    def test_compressed_uuid_decoding(self):
        self.assertEqual(P.decode_uuid('47wB6R' + 'A' * 16)[:8], '47c01e91')
        self.assertEqual(P.decode_uuid('A1B2C3D4-0000-4000-8000-00000000ABCD'), 'a1b2c3d4-0000-4000-8000-00000000abcd')
        self.assertIsNone(P.decode_uuid('not-a-uuid'))

    def test_source_record_new_stays_new(self):
        out = F.decide_policy(legacy=listed([U1]), record={"policy": "new"},
                              files={'assets/main/config.json': json.dumps({'scenes': {'db://x.fire': U1}}).encode()})
        self.assertEqual(out['policy'], 'new')

    def test_recorded_last_source_folder_is_legacy_exactly_there(self):
        """v7.7.5 (总表 B27): no uuid matches, but the project IS the folder the list recorded as the entry's last
        source package -> legacy. A child or parent folder, a native last package, or a new-game marker -> new."""
        root = H.tmpdir(self)
        other = '2b2c3d4e-0000-4000-8000-00000000abcd'           # a scene uuid the list does not hold
        game = project(root / 'game', scene=other)
        entry = {'name': 'g', 'folder': 'J/g', 'scene_uuids': [], 'asset_uuids': [],
                 'last_package': {'kind': 'source', 'path': str(game)}}
        legacy = {'games': [entry]}
        out = P.decide(project=game, legacy=legacy)
        self.assertEqual(out['policy'], 'legacy', out['reason'])
        self.assertIn('same folder', out['reason'])
        self.assertEqual(P.decide(project=project(game / 'v2', scene=other), legacy=legacy)['policy'], 'new')
        self.assertEqual(P.decide(project=project(root / 'outer', scene=other).parent, legacy=legacy)['policy'], 'new')
        native = {'games': [dict(entry, last_package={'kind': 'native', 'path': str(game)})]}
        self.assertEqual(P.decide(project=game, legacy=native)['policy'], 'new')
        self.assertEqual(P.decide(uuids=[], legacy=legacy)['policy'], 'new')       # no project given: no path rule
        P.write_marker(game, 'localize', '2.0')
        self.assertEqual(P.decide(project=game, legacy=legacy)['policy'], 'new')   # a marker still wins


SUBS = ['3c000000-0000-4000-8000-%012d' % i for i in range(10)]


def sprite_project(root):
    """A project whose own scene / top-level uuids are not listed; only its sprite-frame subMetas are."""
    root = project(root, scene='4d000000-0000-4000-8000-000000000001')
    meta = {'uuid': '4d000000-0000-4000-8000-000000000002', 'importer': 'texture',
            'subMetas': {'f%d' % i: {'uuid': u, 'importer': 'sprite-frame'} for i, u in enumerate(SUBS[:6])}}
    (root / 'assets' / 'atlas.png.meta').write_text(json.dumps(meta))
    return root


class SubAssets(unittest.TestCase):
    """v7.8 B27 second half: sub-asset uuids count, but never for a game opened from a starter pack or a remake."""
    legacy = {'games': [{'name': 'g', 'folder': 'J/g', 'board': 'localize', 'scene_uuids': [], 'asset_uuids': SUBS}]}

    def test_moved_legacy_project_is_legacy_by_sub_assets(self):
        p = sprite_project(H.tmpdir(self) / 'moved' / 'Game')
        out = P.decide(project=p, legacy=self.legacy)
        self.assertEqual(out['policy'], 'legacy', out['reason'])
        self.assertEqual(out['legacy_match'][0]['by'], 'sub-asset uuids')
        self.assertEqual(P.decide(project=p, legacy=self.legacy, board='localize')['policy'], 'legacy')

    def test_remake_board_is_never_legacy_by_sub_assets(self):
        p = sprite_project(H.tmpdir(self) / 'moved' / 'Game')
        out = P.decide(project=p, legacy=self.legacy, board='remake')
        self.assertEqual(out['policy'], 'new', out['reason'])
        self.assertEqual(out['auto_new'], '--board remake')
        self.assertEqual(out['sub_asset_match'][0]['folder'], 'J/g')

    def test_inside_or_next_to_a_starter_pack_is_new(self):
        root = H.tmpdir(self)
        pack = root / 'inside' / 'X_StarterPack'
        pack.mkdir(parents=True)
        (pack / 'START_HERE.md').write_text('x')
        (pack / 'GAME_DESIGN.md').write_text('x')
        out = P.decide(project=sprite_project(pack / 'source'), legacy=self.legacy)
        self.assertEqual(out['policy'], 'new', out['reason'])
        self.assertIn('inside starter pack', out['auto_new'])
        game = root / 'next' / '新150_Game'
        (game / 'Game_StarterPack').mkdir(parents=True)
        (game / 'Game_StarterPack' / 'workshop.json').write_text('{}')
        out = P.decide(project=sprite_project(game / '工程' / 'Proj'), legacy=self.legacy)
        self.assertEqual(out['policy'], 'new', out['reason'])
        self.assertIn('next to starter pack', out['auto_new'])
        many = root / 'collection'
        for i in range(3):
            (many / ('G%d_StarterPack' % i)).mkdir(parents=True)
        out = P.decide(project=sprite_project(many / 'old' / 'Game'), legacy=self.legacy)
        self.assertEqual(out['policy'], 'legacy', out['reason'])     # a folder holding many packs is no trace

    def test_top_level_match_and_marker_still_first(self):
        p = sprite_project(H.tmpdir(self) / 'p')
        top = {'games': [dict(self.legacy['games'][0], scene_uuids=['4d000000-0000-4000-8000-000000000001'])]}
        self.assertEqual(P.decide(project=p, legacy=top, board='remake')['policy'], 'legacy')   # unchanged rule
        P.write_marker(p, 'remake', '2.0')
        self.assertEqual(P.decide(project=p, legacy=self.legacy)['policy'], 'new')

    def test_source_writes_the_marker_so_later_callers_agree(self):
        p = sprite_project(H.tmpdir(self) / 'moved' / 'Game')
        self.assertIsNone(P.read_marker(p))
        record = F.finalize_source(p, 'remake', engine=2, legacy=self.legacy, steps=())
        self.assertEqual(record['policy'], 'new')
        self.assertTrue(record['decision'].get('marker_written'))
        self.assertIn('source (auto', P.read_marker(p)['by'])
        self.assertEqual(P.decide(project=p, legacy=self.legacy)['policy'], 'new')     # no board needed any more
        q = sprite_project(H.tmpdir(self) / 'en' / 'Game')
        F.finalize_source(q, 'localize', engine=2, legacy=self.legacy, steps=())
        self.assertIsNone(P.read_marker(q))                                            # an English legacy game

    def test_source_zip_reads_sub_assets(self):
        import zipfile
        p = sprite_project(H.tmpdir(self) / 'z' / 'Game')
        z = p.parent / 'src.zip'
        with zipfile.ZipFile(z, 'w') as out:
            for f in p.rglob('*'):
                if f.is_file():
                    out.write(f, 'Game/' + f.relative_to(p).as_posix())
        ident = P.identity_from_zip(z)
        self.assertEqual(ident['sub_assets'], set(SUBS[:6]))
        kw = dict(uuids=ident['scenes'], assets=ident['assets'], legacy=self.legacy, sub_assets=ident['sub_assets'])
        self.assertEqual(P.decide(**kw)['policy'], 'legacy')
        self.assertEqual(P.decide(board='remake', **kw)['policy'], 'new')


SCISSORS_V30 = Path('/Users/sijunting/Downloads/！自制游戏/启动包工坊/_内部/maintenance/updates/release-selftest/corpus/'
                    '6141967d9c28/ScissorsMaster-v30')


@unittest.skipUnless(SCISSORS_V30.is_dir(), 'release-selftest corpus not on this machine')
class RealSubAssets(unittest.TestCase):
    def test_scissors_v30_moved_project_is_legacy(self):
        legacy = P.load_legacy()
        out = P.decide(project=SCISSORS_V30, legacy=legacy)
        self.assertEqual(out['policy'], 'legacy', out['reason'])
        self.assertEqual([h['name'] for h in out['legacy_match']], ['剪刀达人'])
        self.assertEqual(P.decide(project=SCISSORS_V30, legacy=legacy, board='remake')['policy'], 'new')


@unittest.skipUnless(J.is_dir(), 'real packages not on this machine')
class RealIdentity(unittest.TestCase):
    def test_pkg85_source_and_build_agree(self):
        src = P.identity_from_project(J / '1香吉士-射击高手2048/_src/EnglishProject')['scenes']
        native = P.scene_uuids_from_dir(J / '1香吉士-射击高手2048/检测修复_20261029/pkg85')
        self.assertTrue(src)
        self.assertEqual(src, native)

    def test_marlows_r6_and_sorens_r22_source_and_build_agree(self):
        pairs = [(J / '4周燎原-Marlows（自制）/MarlowsMarbleCut_PortionV2_R6_Source_20261029.zip',
                  J / '4周燎原-Marlows（自制）/MarlowsMarbleCut_PortionV2_R6_TikTok_Test_20261029.zip'),
                 (J / '1林子健-SorensRivet（自制）/SorensRivetRack_Source_20261028_r22.zip',
                  J / '1林子健-SorensRivet（自制）/SorensRivetRack_NativeTest_20261028_r22_存档广告难度.zip')]
        for source, build in pairs:
            s, n = P.identity_from_zip(source), P.identity_from_zip(build)
            self.assertEqual((s['kind'], n['kind']), ('source', 'native'))
            self.assertTrue(s['scenes'])
            self.assertEqual(s['scenes'], n['scenes'], source.name)

    def test_draft_list_recognises_delivered_games(self):
        legacy = P.load_legacy()
        if legacy.get('missing'):
            self.skipTest('KIT/LEGACY_GAMES.json not generated')
        cases = [J / '4周燎原-Marlows（自制）/MarlowsMarbleCut_PortionV2_R6_TikTok_Test_20261029.zip',
                 J / '1林子健-SorensRivet（自制）/SorensRivetRack_NativeTest_20261028_r22_存档广告难度.zip',
                 J / '1段家祐-Nanas（自制）/NanasSockDrawer_Complete_Game_TikTok_20261028.zip']
        for z in cases:
            ident = P.identity_from_zip(z)
            out = P.decide(uuids=ident['scenes'], assets=ident['assets'], legacy=legacy)
            self.assertEqual(out['policy'], 'legacy', (z.name, out['reason']))
        out = P.decide(native=J / '1香吉士-射击高手2048/检测修复_20261029/pkg85', legacy=legacy)
        self.assertEqual(out['policy'], 'legacy', out['reason'])

    def test_recorded_folders_of_scissors_and_scraping_fruit_are_legacy(self):
        """v7.7.5 (总表 B27, 剪刀达人 skill-feedback 10-30): under v7.7.4 both recorded projects were judged new."""
        legacy = P.load_legacy()
        if legacy.get('missing'):
            self.skipTest('KIT/LEGACY_GAMES.json not generated')
        seen = 0
        for game in legacy['games']:
            if game.get('name') not in ('剪刀达人', '欢乐刮水果'):
                continue
            path = Path((game.get('last_package') or {}).get('path') or '/nonexistent')
            if not path.is_dir() or P.read_marker(path):
                continue
            seen += 1
            out = P.decide(project=path, legacy=legacy)
            self.assertEqual(out['policy'], 'legacy', (game['name'], out['reason']))
            self.assertEqual([h['name'] for h in out['legacy_match']], [game['name']])
        if not seen:
            self.skipTest('neither recorded project is on this machine')

    def test_shared_template_is_new(self):
        legacy = P.load_legacy()
        pack = WORKSHOP / 'projects' / 'duo-jump'
        if legacy.get('missing') or not pack.is_dir():
            self.skipTest('list or template missing')
        import make_legacy_list as M
        scenes, assets = set(), set()
        for cand, hint in M.candidates(pack, 5):
            ident = M.identity(cand, hint)
            scenes |= ident['scenes']
            assets |= ident['assets']
        self.assertTrue(scenes)
        self.assertEqual(P.decide(uuids=scenes, assets=assets, legacy=legacy)['policy'], 'new')


if __name__ == '__main__':
    unittest.main(verbosity=1)
