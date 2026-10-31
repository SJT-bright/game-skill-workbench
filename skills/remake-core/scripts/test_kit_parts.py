#!/usr/bin/env python3
"""package_gates.kit_parts (v7.7 W-B): a removed load line, one changed byte, a second touch layer, a kit main.js
that is never loaded each refuse the package; a finalized package passes. Real: pkg81 after finalize with its touch
line deleted (design 3.1 reverse case), Marlows R6 own touch layer.
Run: python3 test_kit_parts.py
"""
import shutil
import sys
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import package_gates as G  # noqa: E402
from package_gates import kit_parts  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402

STEPS = ('startup', 'touch', 'storage', 'login', 'appid', 'structure')


def files_of(root):
    return T.Ctx('native', root).files()


def gate(files, policy=None, **attrs):
    view = G.PackageView(files)
    if policy:
        view.policy = policy
    for k, v in attrs.items():
        setattr(view, k, v)
    out = kit_parts.check(view)
    return {f['id'] for f in out if f['level'] == 'block'}, {f['id'] for f in out if f['level'] == 'warn'}, out


def finalized(test, engine, policy='new'):
    d = H.tmpdir(test) / 'b'
    (H.build24 if engine == 2 else H.build3x)(d)
    if engine == 3:            # v7.7 K1_plugin3x: Creator copies the kit plugin scripts from the finalized project
        H.add_plugins3x(d)
    rec = F.finalize_native(d, None, 'remake', H.APP, policy=policy, steps=STEPS)
    test.assertEqual(rec['blocks'], [], rec['blocks'])
    return d, rec


def without_line(text, needle):
    return '\n'.join(l for l in text.split('\n') if needle not in l)


class Gate(unittest.TestCase):
    def setUp(self):
        # the real KIT_MANIFEST.json, with parts-3x included when W-A1 has not added the include yet
        patcher = mock.patch.object(T, 'load_manifest', lambda path=None: H.manifest())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_finalized_packages_pass(self):
        for engine in (2, 3):
            d, _ = finalized(self, engine)
            blocks, _, out = gate(files_of(d), 'new')
            self.assertEqual(blocks, set(), (engine, out))

    def test_removed_load_line_blocks(self):
        d, _ = finalized(self, 3)
        files = files_of(d)
        files['game.js'] = without_line(files['game.js'].decode(), 'tiktok-kit:touch3x').encode()
        self.assertIn('K2_kit_wiring', gate(files, 'new')[0])
        self.assertIn('K2_kit_wiring', gate(files, 'legacy')[0] | gate(files, 'new')[0])

    def test_one_changed_byte_blocks(self):
        d, _ = finalized(self, 2)
        files = files_of(d)
        data = bytearray(files['touch-coordinates.js'])
        data[-2] ^= 1
        files['touch-coordinates.js'] = bytes(data)
        self.assertIn('K1_kit_bytes', gate(files, 'new')[0])

    def test_second_touch_layer_blocks_new_warns_legacy(self):
        d, _ = finalized(self, 3)
        files = files_of(d)
        files['assets/main/index.js'] = b'tt.onTouchStart = function (e) { e; };\n'
        self.assertIn('K3_single_layer', gate(files, 'new')[0])
        blocks, warns, _ = gate(files, 'legacy')
        self.assertNotIn('K3_single_layer', blocks)
        self.assertIn('K3_single_layer', warns)

    def test_kit_main_never_loaded_blocks(self):
        d, _ = finalized(self, 2)
        files = files_of(d)
        files['game.js'] = without_line(files['game.js'].decode(), "require('./main')").encode()
        self.assertIn('K2_kit_wiring', gate(files, 'new')[0])
        d2, _ = finalized(self, 2)
        files = files_of(d2)
        files['game.js'] = files['game.js'].replace(b"require('./main');", b"require('./main');\nrequire('./main');")
        self.assertIn('K2_kit_wiring', gate(files, 'new')[0])

    def test_legacy_line_finalize_inserted_is_held(self):
        d, _ = finalized(self, 3, policy='legacy')
        files = files_of(d)
        self.assertIn('tiktok-kit:touch3x', files['game.js'].decode())
        del files['tiktok-touch-3x.js']
        self.assertIn('K1_kit_bytes', gate(files, 'legacy')[0])

    def test_policy_from_package_defaults_new(self):
        d = H.build24(H.tmpdir(self) / 'raw')
        blocks, warns, out = gate(files_of(d))
        self.assertIn('K1_kit_bytes', blocks)
        self.assertTrue(any(f['id'] == 'K_policy' and 'policy new' in f['message'] for f in out))

    def test_writer_view_needs_records(self):
        d, rec = finalized(self, 2)
        files = files_of(d)
        self.assertIn('K4_finalize_ran', gate(files, 'new', writer=True)[0])
        blocks = gate(files, 'new', writer=True, finalize_record=rec)[0]
        self.assertNotIn('K4_finalize_ran', blocks)
        self.assertIn('K5_source_finalized', blocks)        # no --project given

    def test_runs_through_package_gates(self):
        d, _ = finalized(self, 2)
        out = G.run(files_of(d), d, 'remake', modules=('kit_parts',))
        self.assertIn('kit_parts', out['gates'])


@unittest.skipUnless(H.J.is_dir(), 'real packages not on this machine')
class RealGate(unittest.TestCase):
    def test_pkg81_finalized_then_touch_line_deleted(self):
        # v7.7 W-D3: 2.4.13 now gets the kit main.js (no touch line in game.js). The design 3.1 reverse case is kept
        # on an engine version outside startup24's list (2.4.3), where finalize inserts the touch line in game.js.
        b = H.tmpdir(self) / 'pkg81'
        shutil.copytree(H.J / '1香吉士-射击高手2048/检测修复_20261029/pkg81', b)
        self.assertIn('K1_kit_bytes', gate(files_of(b), 'new')[0])          # original: no touch layer
        engine = b / 'cocos' / 'cocos2d-js.js'
        engine.write_bytes(engine.read_bytes().replace(b'engineVersion = "2.4.13"', b'engineVersion = "2.4.3"', 1))
        rec = F.finalize_native(b, None, 'localize', H.APP, policy='new', steps=STEPS)
        self.assertEqual(rec['blocks'], [])
        files = files_of(b)
        self.assertIn('tiktok-kit:touch24', files['game.js'].decode())
        self.assertEqual(gate(files, 'new')[0], set())
        files['game.js'] = without_line(files['game.js'].decode(), 'tiktok-kit:touch24').encode()
        self.assertIn('K2_kit_wiring', gate(files, 'new')[0])

    def test_pkg81_kit_main_then_main_require_deleted(self):
        # the real 2.4.13 path: finalize installs the kit main.js; game.js no longer loading it is K2
        b = H.tmpdir(self) / 'pkg81'
        shutil.copytree(H.J / '1香吉士-射击高手2048/检测修复_20261029/pkg81', b)
        rec = F.finalize_native(b, None, 'localize', H.APP, policy='new', steps=STEPS)
        self.assertEqual(rec['blocks'], [])
        files = files_of(b)
        self.assertEqual(T.sha256(files['main.js']), T.kit_main_current(H.manifest()))
        self.assertEqual(gate(files, 'new')[0], set())
        self.assertEqual(gate(files)[0], set())                             # real policy: legacy (listed)
        files['game.js'] = without_line(files['game.js'].decode(), "require('./main')").encode()
        self.assertIn('K2_kit_wiring', gate(files, 'new')[0])

    def test_marlows_r6_own_layer(self):
        z = H.J / '4周燎原-Marlows（自制）/MarlowsMarbleCut_PortionV2_R6_TikTok_Test_20261029.zip'
        d = H.unzip(self, z, 'r6')
        blocks, _, _ = gate(files_of(d), 'new')
        self.assertTrue({'K1_kit_bytes', 'K2_kit_wiring', 'K3_single_layer'} <= blocks, blocks)
        blocks, warns, _ = gate(files_of(d))
        self.assertNotIn('K3_single_layer', blocks)
        self.assertIn('K3_single_layer', warns)


if __name__ == '__main__':
    unittest.main(verbosity=1)
