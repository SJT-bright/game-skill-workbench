#!/usr/bin/env python3
"""生成时预防 R4L1 (R4F1 leftover): the package gate kit_parts refuses a NEW remake package (Cocos 2.4 and 3.x) that
does not load the rewarded-ad guard parts/rewarded-guard.js; English, legacy and unknown-board packages are reported.

Census (P01-2): 广告关掉后锁死 33/36 款、超时口径不对 31/33、迟到发奖 14/14. R4A / R4F1 / R4G2 made finalize native
install the guard, but kit_parts never asked for it, so a build that skipped native (or an old build) went out
without it. Every OLD case fails on the 11.15 candidate base (kit_parts has no guard finding there).
  1 OLD 2.4 own main   2.4.9 build with its own main.js, before native: K_rewarded_guard block (remake);
                       English / unknown board / legacy: K_W_rewarded_guard warning only
  2     2.4 after      the same build after tiktok_finalize native: no guard finding (one game.js line, kit file)
  3 OLD 2.4 kit main   2.4.15 build with the editor main.js: block; after native (kit main.js v1.7 requires the guard):
                       no guard finding
  4 OLD 3.x            3.x build before native: block; after the startup step installs rewardguard3x: none
  5 OLD gate wiring    kit_parts.check on the un-natived 3.x build carries K_rewarded_guard; board read from the view,
                       the finalize record or the project marker
Run: python3 test_r4l1_guard_gate.py
"""
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
from package_gates import kit_parts  # noqa: E402
import test_finalize_sync as S  # noqa: E402  (project24 / build24 fixtures)
from test_finalize_hostshim_boot import build, native  # noqa: E402
from test_r4f1_sync_closure import own_main_build  # noqa: E402


def files(b):
    return T.Ctx('native', b).files()


def guard_ids(items):
    return sorted(i['id'] for i in items if 'rewarded_guard' in i['id'])


class GuardGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4l1-guard-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.m = T.load_manifest()

    def gate(self, b, engine, policy='new', board='remake'):
        self.assertTrue(hasattr(kit_parts, 'guard_findings'), 'old code: kit_parts has no guard check')
        return guard_ids(kit_parts.guard_findings(files(b), self.m, policy, engine, board))

    def test_1_24_own_main_before_native(self):
        b = own_main_build(self.tmp / 'build')
        self.assertEqual(self.gate(b, 2), ['K_rewarded_guard'])
        for policy, board in (('new', 'localize'), ('new', None), ('legacy', 'remake')):
            self.assertEqual(self.gate(b, 2, policy, board), ['K_W_rewarded_guard'], (policy, board))

    def test_2_24_own_main_after_native(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build')
        F.finalize_native(b, p, 'remake')
        self.assertEqual(self.gate(b, 2), [])

    def test_3_24_kit_main(self):
        p = S.project24(self.tmp / 'p')
        b = own_main_build(self.tmp / 'build', '2.4.15')
        self.assertEqual(self.gate(b, 2), ['K_rewarded_guard'])
        F.finalize_native(b, p, 'remake')
        self.assertEqual(self.gate(b, 2), [])

    def test_4_3x(self):
        b = build(self.tmp / 'b3', 3)
        self.assertEqual(self.gate(b, 3), ['K_rewarded_guard'])
        native(b, self.m)
        self.assertEqual(self.gate(b, 3), [])

    def test_5_check_wiring_and_board(self):
        b = build(self.tmp / 'b3', 3)
        import package_gates
        view = package_gates.PackageView(files(b), b, 'remake', 'new')
        self.assertEqual(view.engine_major, 3)
        self.assertIn('K_rewarded_guard', [i['id'] for i in kit_parts.check(view)])
        rec_view = types.SimpleNamespace(board=None, finalize_record={'board': 'localize'})
        self.assertEqual(kit_parts._board(rec_view), 'localize')
        proj = self.tmp / 'proj'
        proj.mkdir()
        P.write_marker(proj, 'remake', '2.0')
        self.assertEqual(kit_parts._board(types.SimpleNamespace(board=None, project=proj)), 'remake')
        native(b, self.m)
        view = package_gates.PackageView(files(b), b, 'remake', 'new')
        self.assertNotIn('K_rewarded_guard', [i['id'] for i in kit_parts.check(view)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
