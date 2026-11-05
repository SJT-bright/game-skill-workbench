#!/usr/bin/env python3
"""生成时预防 P18 第 3 点: the 1-second static scan frame_scan (run by `sync` before every build).

Census: moves by a fixed step per frame (割草: 60 Hz vs 120 Hz differ by 50%), nodes made in update (猫咪毛球: a new
Sprite every frame, node count growing). Cases:
  1 fixtures    `this.node.x += 5` reported; `this.node.x += 300 * dt` not; a variable computed from dt not;
                update() without a parameter moving the node reported; `x = x + 4`, setPosition(x + 3, y) reported;
                an absolute place (`this.node.x = target.x`) not
  7 calibration lines from real base sources: a clamp, a follow offset, a wrap-around jump are not moves
  2 猫咪毛球    update() that makes a fur Sprite node each frame -> K_frame_new_node (the code is rebuilt from the census
                evidence "每帧新增 Sprite"; the original file is not in the census)
  3 strings     update text inside a string / comment is ignored; `// tiktok-kit:frame-ok why` skips a line
  4 levels      new remake game: blocks; English (localize): info only; legacy: warnings
  5 kit files   assets/tiktok-platform/ is not scanned
  6 speed       a project with 200 scripts is scanned in under 1 second
Run: python3 test_frame_scan.py
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
from tiktok_finalize_steps import frame_scan  # noqa: E402

FIXED = """cc.Class({
    extends: cc.Component,
    update (dt) {
        this.node.x += 5;
    },
});
"""
TIMED = """cc.Class({
    extends: cc.Component,
    properties: { speed: 300 },
    update: function (dt) {
        this.node.x += 300 * dt;
        var step = this.speed * dt;
        this.node.y -= step;
        this.node.x = this.target.x;
    },
});
"""
NO_PARAM = """export default class Mover extends cc.Component {
    update(): void {
        this.node.y += 2;
    }
}
"""
SELF_AND_SETPOS = """cc.Class({
    extends: cc.Component,
    update (dt) {
        this.bg.x = this.bg.x + 4;
        this.node.setPosition(this.node.x + 3, this.node.y);
        this.timer += dt;
    },
});
"""
CAT_FUR = """// 猫咪毛球 (rebuilt from the census evidence: a new Sprite every frame)
cc.Class({
    extends: cc.Component,
    properties: { furFrame: cc.SpriteFrame },
    update (dt) {
        this.timer += dt;
        const fur = new cc.Node('fur');
        const sp = fur.addComponent(cc.Sprite);
        sp.spriteFrame = this.furFrame;
        this.node.addChild(fur);
    },
});
"""
STRINGS = """cc.Class({
    extends: cc.Component,
    help: 'update (dt) { this.node.x += 5; }',
    // update (dt) { this.node.x += 5; }
    update (dt) {
        // tiktok-kit:frame-ok one-time build behind this.built
        if (!this.built) { this.built = cc.instantiate(this.prefab); }
        this.node.x += 1; // tiktok-kit:frame-ok scroll by one pixel on purpose (pixel art)
    },
});
"""


def project(root, scripts):
    (root / 'assets' / 'scripts').mkdir(parents=True)
    (root / 'project.json').write_text('{"engine": "cocos-creator-js", "version": "2.4.15"}')
    for name, text in scripts.items():
        p = root / 'assets' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


def run(root, board='remake', policy='new'):
    return frame_scan.apply(T.Ctx('source', root, project=root, board=board, engine=2, policy=policy,
                                  manifest=T.load_manifest()))


class FrameScan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='frame_scan_'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_fixtures(self):
        moves, made = frame_scan.scan_text(FIXED, 'Fixed.js')
        self.assertEqual([m['code'] for m in moves], ['this.node.x += 5;'])
        self.assertEqual(frame_scan.scan_text(TIMED, 'Timed.js'), ([], []))
        self.assertEqual([m['code'] for m in frame_scan.scan_text(NO_PARAM, 'Mover.ts')[0]], ['this.node.y += 2;'])
        self.assertEqual([m['line'] for m in frame_scan.scan_text(SELF_AND_SETPOS, 'S.js')[0]], [4, 5])

    def test_2_cat_fur_sprite_each_frame(self):
        moves, made = frame_scan.scan_text(CAT_FUR, 'CatFur.js')
        self.assertEqual(moves, [])
        self.assertEqual([m['line'] for m in made], [7, 8])

    def test_3_strings_comments_and_exemptions(self):
        self.assertEqual(frame_scan.scan_text(STRINGS, 'Str.js'), ([], []))

    def test_4_levels(self):
        root = project(self.tmp / 'p', {'scripts/Fixed.js': FIXED, 'scripts/CatFur.js': CAT_FUR})
        out = run(root)
        self.assertEqual(sorted(b['id'] for b in out['blocks']), ['K_frame_dt', 'K_frame_new_node'])
        loc = run(root, board='localize')
        self.assertEqual(loc['blocks'] + loc['warnings'], [])
        self.assertTrue(any(i.startswith('K_W_frame_dt') for i in loc['info']), loc['info'])
        leg = run(root, policy='legacy')
        self.assertEqual(leg['blocks'], [])
        self.assertEqual(sorted(w['id'] for w in leg['warnings']), ['K_W_frame_dt', 'K_W_frame_new_node'])
        clean = run(project(self.tmp / 'q', {'scripts/Timed.js': TIMED}))
        self.assertEqual(clean['blocks'] + clean['warnings'], [])

    def test_5_kit_folder_not_scanned(self):
        root = project(self.tmp / 'p', {'tiktok-platform/FxPool.js': FIXED})
        self.assertEqual(run(root)['blocks'], [])

    def test_7_calibration_not_moves(self):
        # lines from real Chinese base sources (两人行双人跳 clamp, 剪纸小子 follow, 战斗汽车 road wrap) are not moves;
        # 全民3d飞车漂移 / 我坦克开的贼溜 self moves without dt are
        src = """cc.Class({ update (dt) {
  targetPos.x = cc.misc.clampf(targetPos.x, -this.limitMinX, this.limitMaxX);
  this.node.position = this.floow.position.add(cc.v2(5,-5));
  if (this.road0.y < -1000) this.road0.y += ((this.road0.scale * this.road0.height) * 3 - 10);
  this.node.x = this.node.x + 0.1;
  this._pos.x = this._pos.x + this._lightSpeed;
} });"""
        self.assertEqual([m['line'] for m in frame_scan.scan_text(src, 'C.js')[0]], [5, 6])

    def test_6_speed(self):
        root = project(self.tmp / 'p', {'scripts/S%03d.js' % i: TIMED * 6 for i in range(200)})
        started = time.time()
        found = frame_scan.scan(root)
        self.assertEqual(found['files'], 200)
        self.assertLess(time.time() - started, 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
