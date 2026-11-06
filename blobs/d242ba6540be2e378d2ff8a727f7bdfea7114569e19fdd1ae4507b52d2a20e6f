#!/usr/bin/env python3
"""生成时预防 R4L1 (R4G1 leftover): a new Cocos 3.x game with HomeEntrySlots installed whose home script writes the
profile-revisit / add-to-desktop coordinates itself (and never calls HomeEntrySlots.place / placeLater) gets a
source warning K_W_home_entry_coords. Census: element_overlap 64 games / 99 times, the entries put on a button by
hand-written coordinates. Cases:
  1 hand      profileBtn.setPosition(-220, -760), shortcut.position = v3(220, -760), find('Canvas/AddDesktop').x = 0
              and button factories this.button(.profile., base, .ProfileRevisit., 165, -top + 128, ..) (CloverCourier)
              -> 3 lines reported (old code: no step, nothing reported)
  2 kit way   the same nodes and TikTokKit.HomeEntrySlots.placeLater(cc, this, {...}) -> nothing; other buttons with
              literal positions (playBtn) -> nothing; `// tiktok-kit:ui-ok` skips
  3 levels    new 3.x + plugin: K_W_home_entry_coords warning; legacy: info only; no plugin or Cocos 2.4: nothing
  4 wiring    home_entry_scan is in SOURCE_STEPS; finalize_source on a new 3.x game writes the warning in the record
  5 speed     200 scripts in under 1 second
Run: python3 test_r4l1_home_entry_coords.py
"""
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize_steps as T  # noqa: E402

PLUGIN = 'assets/tiktok-platform/HomeEntrySlots.plugin.js'

# 照旧做法：首页组件自己给两个平台入口写死坐标（普查 element_overlap 一类的写法节选，3.x）
HAND = """import { _decorator, Component, Node, v3, find } from 'cc';
const { ccclass } = _decorator;
@ccclass('HomePage')
export class HomePage extends Component {
    profileBtn: Node = null!;
    shortcut: Node = null!;
    playBtn: Node = null!;
    start () {
        this.playBtn.setPosition(0, -300);
        this.profileBtn.setPosition(-220, -760);
        this.shortcut.position = v3(220, -760, 0);
        find('Canvas/AddDesktop')!.x = 0;
    }
}
"""
KIT_WAY = HAND.replace("        find('Canvas/AddDesktop')!.x = 0;\n",
                       "        TikTokKit.HomeEntrySlots.placeLater(cc, this, {root: this.node, "
                       "entries: [this.profileBtn, this.shortcut]});\n")
# 按钮工厂写死入口坐标（CloverCourier assets/Script/EnglishUI.ts 110-111 行的写法）
FACTORY = """export class EnglishUI {
    buildHome (top: number) {
        this.button('addHome', this.base, 'AddShortcut', -165, -top + 128, 300, 96, () => this.mission('shortcut'));
        this.button('profile', this.base, 'ProfileRevisit', 165, -top + 128, 300, 96, () => this.mission('profile'));
        this.button('play', this.base, 'Play', 0, -200, 400, 120, () => this.play());
        this.button(p, 'mission-guide', kind === 'home' ? 'ADD SHORTCUT' : 'OPEN PROFILE GUIDE', 0, -160, 520, 96);
    }
}
"""
EXEMPT = """export class Tut {
    show (profileHint) {
        profileHint.setPosition(-220, -760); // tiktok-kit:ui-ok tutorial arrow, not the entry
    }
}
"""


def project(root, files, engine3=True, plugin=True):
    (root / 'assets' / 'scripts').mkdir(parents=True, exist_ok=True)
    (root / 'package.json').write_text('{"creator": {"version": "3.8.6"}}' if engine3 else '{}')
    if not engine3:
        (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    if plugin:
        (root / PLUGIN).parent.mkdir(parents=True, exist_ok=True)
        (root / PLUGIN).write_text('// HomeEntrySlots\n')
    for rel, text in files.items():
        (root / rel).write_text(text, encoding='utf-8')
    return root


class HomeEntryCoords(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4l1_entry_'))
        from tiktok_finalize_steps import home_entry_scan as H   # old code: ModuleNotFoundError -> test errors
        self.H = H

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_step(self, policy='new', engine=3):
        return self.H.apply(T.Ctx('source', self.tmp, project=self.tmp, board='remake', engine=engine,
                                  policy=policy, manifest=T.load_manifest()))

    def test_1_hand_written(self):
        hits, calls = self.H.scan_text(HAND, 'Home.ts')
        self.assertEqual([h['line'] for h in hits], [10, 11, 12], hits)
        self.assertFalse(calls)
        hits, _ = self.H.scan_text(FACTORY, 'EnglishUI.ts')
        self.assertEqual([h['line'] for h in hits], [3, 4], hits)   # not the play button, not the 'ADD SHORTCUT' label

    def test_2_kit_way_and_exempt(self):
        _, calls = self.H.scan_text(KIT_WAY, 'Home.ts')
        self.assertTrue(calls)
        project(self.tmp, {'assets/scripts/Home.ts': KIT_WAY, 'assets/scripts/Tut.ts': EXEMPT})
        self.assertEqual(self.run_step()['warnings'], [])
        self.assertEqual(self.H.scan_text(EXEMPT, 'Tut.ts')[0], [])

    def test_3_levels(self):
        project(self.tmp, {'assets/scripts/Home.ts': HAND})
        new = self.run_step()
        self.assertEqual([w['id'] for w in new['warnings']], ['K_W_home_entry_coords'])
        self.assertEqual(new['blocks'], [])
        leg = self.run_step(policy='legacy')
        self.assertEqual(leg['warnings'], [])
        self.assertTrue(any('report only' in i for i in leg['info']))
        self.assertEqual(self.run_step(engine=2)['state'], 'n/a')
        (self.tmp / PLUGIN).unlink()
        self.assertEqual(self.run_step()['warnings'], [])

    def test_4_wiring(self):
        import tiktok_finalize as F
        self.assertIn('home_entry_scan', T.SOURCE_STEPS)
        self.assertIn('home_entry_scan', F.SOURCE_STEPS)
        project(self.tmp, {'assets/scripts/Home.ts': HAND})
        rec = F.finalize_source(self.tmp, 'remake', policy='new')
        step = next(s for s in rec['steps'] if s.get('step') == 'home_entry_scan')
        self.assertIn('K_W_home_entry_coords', {w['id'] for w in step['warnings']}, step)

    def test_5_speed(self):
        project(self.tmp, {'assets/scripts/S%03d.ts' % i: KIT_WAY * 5 for i in range(200)})
        t = time.time()
        self.run_step()
        self.assertLess(time.time() - t, 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
