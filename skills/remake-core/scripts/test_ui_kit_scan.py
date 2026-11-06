#!/usr/bin/env python3
"""生成时预防 Round 4 R4F3: source step ui_kit_scan (#36, 补查第 4 组) and frame_scan at source (#43).

Census: popups built by hand (button_covered 14 games, popup_close_dead 10, callback_missing 11, too_dark 11) and a
developer word in player text (dev_text_residue 9 times in 8 games; 回家快跑 ad toast "LOCAL PREVIEW"). frame_scan only
ran in `sync`, so its block never reached the source record and the writers let the package out. Cases:
  1 popup     new cc.Node + BlockInputEvents without GameUIKit -> K_ui_handmade_popup; the same file using
              require('GameUIKit') / UI.popup -> not reported
  2 mask      mask.opacity = 160, dim.color = cc.color(..), cc.tween(mask).to(.., {opacity: 150}) -> K_ui_mask_hardcoded;
              mask.opacity = 0 / 255 (fade ends), UI.setup({maskColor, maskOpacity}), label.opacity = 120 -> not
  3 dev text  showToast('Ad not ready (LOCAL PREVIEW)') (回家快跑), label.string = 'DEBUG', title: 'TODO', a scene
              Label '测试关卡' -> K_dev_text; console.log('DEBUG'), cc.warn('TODO'), 'Best' / 'Preview skin' not
  4 levels    new remake: K_dev_text blocks, popup + mask warn (K_W_, NEW_GAME_LEVEL); English: warnings; legacy: info
  5 skip      assets/tiktok-platform/ and `// tiktok-kit:ui-ok why` are not reported
  6 wiring    frame_scan and ui_kit_scan are in SOURCE_STEPS; finalize_source on a new game with a per-frame move and a
              hand-built popup writes K_frame_dt (block) + K_W_ui_handmade_popup (warning); K5 refuses the writer
  7 speed     200 scripts in under 1 second
Run: python3 test_ui_kit_scan.py
"""
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
from tiktok_finalize_steps import ui_kit_scan as U  # noqa: E402

# 照旧手搭的弹窗（普查里割草、花园守卫者一类写法的节选）
HANDMADE = """cc.Class({
    extends: cc.Component,
    showRevive () {
        var mask = new cc.Node('ReviveMask');
        mask.addComponent(cc.BlockInputEvents);
        mask.color = cc.color(0, 0, 0);
        mask.opacity = 160;
        this.node.addChild(mask);
        cc.tween(mask).to(0.2, {opacity: 150}).start();
        var panel = new cc.Node('Panel');
        mask.addChild(panel);
    },
});
"""
WITH_KIT = """var UI = require('GameUIKit');
UI.setup({maskColor: [24, 22, 32], maskOpacity: 130});
cc.Class({
    extends: cc.Component,
    showRevive () {
        var holder = new cc.Node('Holder');
        holder.addComponent(cc.BlockInputEvents);
        var p = UI.popup(this.node, {panelFrame: this.panel, keep: true});
        this.fade.opacity = 0;
        this.mask.opacity = 255;
        this.label.opacity = 120;
    },
});
"""
DEV = """cc.Class({
    extends: cc.Component,
    onAdFail () {
        Platform.showToast('Ad not ready (LOCAL PREVIEW)');
        this.tipLabel.string = 'DEBUG';
        UI.toast({title: 'TODO', text: 'Best'});
        console.log('DEBUG ad state', this.state);
        cc.warn('TODO: remove');
        this.best.string = 'Best';
        this.skinBtn.string = 'Preview skin';
    },
});
"""
SCENE = ('[{"__type__": "cc.SceneAsset"}, {"__type__": "cc.Label", "_string": "测试关卡"},'
         ' {"__type__": "cc.Label", "_N$string": "Level 1"}]')
EXEMPT = """cc.Class({
    showDim () {
        var n = new cc.Node('Dim');
        // tiktok-kit:ui-ok tutorial finger layer, closed by the tutorial itself
        n.addComponent(cc.BlockInputEvents);
        n.opacity = 90; // tiktok-kit:ui-ok not a mask
    },
});
"""
FRAME = """cc.Class({
    extends: cc.Component,
    update (dt) {
        this.node.x += 5;
    },
});
"""


def project(root, files):
    (root / 'assets' / 'scripts').mkdir(parents=True, exist_ok=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


def run(root, board='remake', policy='new'):
    return U.apply(T.Ctx('source', root, project=root, board=board, engine=2, policy=policy,
                         manifest=T.load_manifest()))


def ids(r):
    return {b['id'] for b in r['blocks']} | {w['id'] for w in r['warnings']}


class UiKitScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ui_kit_scan_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_popup(self):
        pops, _, _ = U.scan_text(HANDMADE, 'a.js')
        self.assertEqual([p['line'] for p in pops], [5])
        self.assertEqual(U.scan_text(WITH_KIT, 'b.js')[0], [])
        ts3 = ("import { Node, Label,\n    BlockInputEvents } from 'cc';\nexport class P {\n    open (parent: Node) {\n"
               "        const root = new Node('Popup'); root.addComponent(BlockInputEvents);\n    }\n}\n")
        self.assertEqual([p['line'] for p in U.scan_text(ts3, 'p.ts')[0]], [5])   # the import line is no popup

    def test_2_mask(self):
        _, masks, _ = U.scan_text(HANDMADE, 'a.js')
        self.assertEqual(sorted(m['line'] for m in masks), [6, 7, 9], masks)
        self.assertEqual(U.scan_text(WITH_KIT, 'b.js')[1], [])

    def test_3_dev_text(self):
        dev = U.scan_text(DEV, 'c.js')[2]
        self.assertEqual(sorted((d['line'], d['word']) for d in dev), [(4, 'PREVIEW'), (5, 'DEBUG'), (6, 'TODO')], dev)
        scene = U.scan_scene(SCENE, 'assets/Game.fire')
        self.assertEqual([d['word'] for d in scene], ['测试'])

    def test_4_levels(self):
        project(self.tmp, {'assets/scripts/Revive.js': HANDMADE, 'assets/scripts/Ad.js': DEV,
                           'assets/Game.fire': SCENE})
        new = run(self.tmp)
        self.assertEqual({b['id'] for b in new['blocks']}, {'K_dev_text'}, new['blocks'])
        # popup and mask start as warnings for new games too (NEW_GAME_LEVEL, until calibrated clean)
        self.assertEqual({w['id'] for w in new['warnings']}, {'K_W_ui_handmade_popup', 'K_W_ui_mask_hardcoded'})
        loc = run(self.tmp, board='localize')
        self.assertEqual(loc['blocks'], [])
        self.assertEqual({w['id'] for w in loc['warnings']},
                         {'K_W_ui_handmade_popup', 'K_W_ui_mask_hardcoded', 'K_W_dev_text'})
        leg = run(self.tmp, policy='legacy')
        self.assertEqual((leg['blocks'], leg['warnings']), ([], []))
        self.assertTrue(any('report only' in i for i in leg['info']))

    def test_5_skip(self):
        project(self.tmp, {'assets/tiktok-platform/Own.js': HANDMADE + DEV, 'assets/scripts/Tut.js': EXEMPT})
        r = run(self.tmp)
        self.assertEqual(ids(r), set(), r)

    def test_6_wiring_source_record_and_k5(self):
        self.assertIn('frame_scan', T.SOURCE_STEPS)
        self.assertIn('ui_kit_scan', T.SOURCE_STEPS)
        self.assertIn('ui_kit_scan', F.SOURCE_STEPS)
        self.assertLess(T.SOURCE_STEPS.index('kit_sources'), T.SOURCE_STEPS.index('ui_kit_scan'))
        project(self.tmp, {'assets/scripts/Move.js': FRAME, 'assets/scripts/Revive.js': HANDMADE})
        P.write_marker(self.tmp, 'remake', T.load_manifest().version, reason='init')
        rec = F.finalize_source(self.tmp, 'remake')
        got = {b['id'] for b in rec['blocks']}
        self.assertIn('K_frame_dt', got)
        self.assertNotIn('K_ui_handmade_popup', got)
        self.assertIn('K_W_ui_handmade_popup', {w['id'] for w in rec['warnings']})
        k5 = F.check_source_record(self.tmp)
        self.assertTrue(any('K_frame_dt' in f['message'] for f in k5), k5)

    def test_7_speed(self):
        project(self.tmp, {'assets/scripts/S%03d.js' % i: WITH_KIT * 5 for i in range(200)})
        t = time.time()
        r = run(self.tmp)
        self.assertLess(time.time() - t, 1.0)
        self.assertEqual(r['blocks'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
