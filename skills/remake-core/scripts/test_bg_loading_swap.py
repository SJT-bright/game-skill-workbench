#!/usr/bin/env python3
"""简化.11.14 R4A (生成时预防 P07 第 2 点, 热气球 flash_frame): the loading page and the home show the same background.

热气球 v1: the loading page showed its own old picture, the home then put a stretched portrait picture over it and shrank
it to 750 wide; the player saw the background "refresh" (Saul's trial, 2026-10-30). Source step bg_cover now compares
the root background picture of a loading page (Loading / Boot / Launch / Splash / Preload file) with the home's:
  1 old way      Loading.fire bg = picture A, Home.fire bg = picture B (both project pictures, both covered):
                 new remake game -> K_bg_loading_swap block; the 11.14 step gave no finding at all
  2 same picture Loading.fire and Home.fire both show picture B -> no finding
  3 no picture   the loading page bg is an engine / official built-in frame (uuid not in any project .meta) -> none
  4 localize / legacy  the bad project gives K_W_bg_loading_swap (warning), never a block
  5 loading prefab     LoadingPanel.prefab with picture A counts as a loading page too
Run: python3 test_bg_loading_swap.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import bg_cover  # noqa: E402
import test_bg_cover as base  # noqa: E402  (fixtures: node(), script(), manifest(), SCRIPT_UUID, COVER_FIND)

PIC_A = '1a2b3c4d-0000-4000-8000-00000000000a'     # old loading picture
PIC_B = '1a2b3c4d-0000-4000-8000-00000000000b'     # home picture
BUILTIN = 'a23235d1-15db-4b95-8439-a2e005bfff91'   # engine internal frame: never in a project .meta


def page(picture, prefab=False):
    objs = json.loads(base.home_fire())
    objs[5]['_spriteFrame'] = {'__uuid__': picture}
    if prefab:   # prefab: the root node holds the bg, no Canvas
        return json.dumps([{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
                           base.node('LoadingPanel', None, 720, 1280, comps=[2]),
                           {'__type__': 'cc.Sprite', 'node': {'__id__': 1}, '_spriteFrame': {'__uuid__': picture}}])
    return json.dumps(objs)


def project(root, loading, home=PIC_B, prefab=False):
    scenes = root / 'assets' / 'scenes'
    scenes.mkdir(parents=True)
    (scenes / 'Home.fire').write_text(page(home))
    if prefab:
        (root / 'assets' / 'prefabs').mkdir(parents=True)
        (root / 'assets' / 'prefabs' / 'LoadingPanel.prefab').write_text(page(loading, prefab=True))
    else:
        (scenes / 'Loading.fire').write_text(page(loading))
    art = root / 'assets' / 'art'
    art.mkdir(parents=True)
    for name, uid in (('old_bg', PIC_A), ('home_bg', PIC_B)):
        (art / (name + '.png.meta')).write_text(json.dumps({'ver': '2.3.5', 'uuid': uid[:-1] + 'f',
                                                            'subMetas': {name: {'uuid': uid}}}))
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    # every background laid with cover (by name), so only the picture rule can fire
    base.script(root, base.COVER_FIND + "module.exports.panel = function () { ScreenFit.cover(cc, cc.find('LoadingPanel')); };\n")
    return root


def run(root, board='remake', policy='new'):
    c = T.Ctx('source', root, project=root, board=board, engine=2, policy=policy, manifest=base.manifest(True))
    return bg_cover.apply(c)


def ids(result):
    return [f['id'] for f in result['blocks'] + result['warnings']]


class LoadingSwap(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_different_loading_picture_blocks_a_new_game(self):
        r = run(project(self.tmp / 'p', PIC_A))
        self.assertIn('K_bg_loading_swap', [f['id'] for f in r['blocks']], r)
        self.assertNotIn('K_bg_cover', ids(r))

    def test_2_same_picture_passes(self):
        self.assertEqual(ids(run(project(self.tmp / 'p', PIC_B))), [])

    def test_3_builtin_frame_is_not_a_game_picture(self):
        self.assertEqual(ids(run(project(self.tmp / 'p', BUILTIN))), [])

    def test_4_localize_and_legacy_only_warn(self):
        for board, policy in (('localize', 'new'), ('remake', 'legacy')):
            with self.subTest(board=board, policy=policy):
                root = project(self.tmp / (board + policy), PIC_A)
                r = run(root, board=board, policy=policy)
                self.assertEqual(r['blocks'], [])
                self.assertIn('K_W_bg_loading_swap', ids(r))

    def test_5_loading_prefab_counts(self):
        r = run(project(self.tmp / 'p', PIC_A, prefab=True))
        self.assertIn('K_bg_loading_swap', ids(r), r)


if __name__ == '__main__':
    unittest.main()
