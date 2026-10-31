#!/usr/bin/env python3
"""v7.8 P16 logic_check rules L-FPS-ACCUM / L-FPS-SCHEDULE / L-FPS-DT: 2.4 physics and per-frame pushes follow the screen
frame rate (全民飞车漂移 pysTouchEvent.ts:91, RunUI.ts:145). New games fail, games on the legacy list get a hint.
Run: python3 -B test_logic_frame_rate.py"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import logic_check  # noqa: E402

DRIFT_RUNUI = '''const { ccclass } = cc._decorator;
@ccclass
export default class RunUI extends cc.Component {
    onLoad() {
        cc.director.getPhysicsManager().enabled = true;
        cc.director.getPhysicsManager().gravity = cc.v2(0, 0);
    }
}
'''
DRIFT_TOUCH = '''const { ccclass, property } = cc._decorator;
@ccclass
export default class pysTouchEvent extends cc.Component {
    carBody: cc.RigidBody = null;
    gameStart() {
        this.schedule(this.run_time, 0.01)
    }
    run_time() {
        let force = 65
        let forceY = force * Math.cos(this.carBody.node.angle * 3.14159 / 180)
        this.carBody.applyForceToCenter(cc.v2(0, forceY), true)
    }
}
'''
FIXED_RUNUI = DRIFT_RUNUI.replace('gravity = cc.v2(0, 0);', 'gravity = cc.v2(0, 0);\n        '
                                  'cc.director.getPhysicsManager().enabledAccumulator = true;')
FIXED_TOUCH = '''export default class pysTouchEvent extends cc.Component {
    update(dt) {
        const k = dt * 60;
        this.carBody.applyForceToCenter(cc.v2(0, 65 * k), true)
    }
}
'''


def project(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return root


class FrameRate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def fps(self, files):
        self.n += 1
        found, _ = logic_check.scan(project(self.root / str(self.n), files))
        return sorted((f['rule'], f['severity'], f['file'], f['line']) for f in found if f['rule'].startswith('L-FPS'))

    def test_drift_shape_is_reported_on_both_lines(self):
        got = self.fps({'assets/Script/RunUI.ts': DRIFT_RUNUI, 'assets/Script/pysTouchEvent.ts': DRIFT_TOUCH})
        self.assertIn(('L-FPS-ACCUM', 'fail', 'assets/Script/RunUI.ts', 5), got)
        self.assertIn(('L-FPS-SCHEDULE', 'fail', 'assets/Script/pysTouchEvent.ts', 6), got)
        self.assertIn(('L-FPS-DT', 'fail', 'assets/Script/pysTouchEvent.ts', 6), got)

    def test_fixed_drift_passes(self):
        self.assertEqual(self.fps({'assets/Script/RunUI.ts': FIXED_RUNUI, 'assets/Script/pysTouchEvent.ts': FIXED_TOUCH}), [])

    def test_physics_through_an_alias_without_accumulator_fails(self):
        src = 'onLoad(){ const pm = cc.director.getPhysicsManager(); pm.enabled = true; }\n'
        self.assertEqual([r[0] for r in self.fps({'assets/A.js': src})], ['L-FPS-ACCUM'])
        self.assertEqual(self.fps({'assets/A.js': src.replace('}', 'pm.enabledAccumulator = true; }')}), [])

    def test_unscaled_per_frame_moves_fail(self):
        for body in ['this.node.x += this.speed;', 'this.node.y = this.node.y - 2;', 'this.body.linearVelocity.x *= 0.98;',
                     'this.rb.applyLinearImpulse(cc.v2(1, 0), cc.v2(), true);', 'node.setPosition(node.x + 3, node.y);']:
            with self.subTest(body=body):
                got = self.fps({'assets/Mover.ts': 'export class M { update(dt) { %s } }\n' % body})
                self.assertEqual([r[:2] for r in got], [('L-FPS-DT', 'fail')])
                self.assertEqual(self.fps({'assets/Mover.ts': 'export class M { update(dt) { const s = dt * 60; %s } }\n'
                                                              % body.replace(';', ' * s;')}), [])

    def test_schedule_forms(self):
        cases = {
            "this.schedule(function () { this.node.x += 4; }, 0.005);": ['L-FPS-DT', 'L-FPS-SCHEDULE'],
            "this.schedule((dt) => { this.node.x += 240 * dt; }, 0.005);": [],
            "this.schedule(this.tick, 0);": ['L-FPS-DT'],
            "this.schedule(this.tick, 1);": [],
            "this.schedule(this.count.bind(this), 0.01);": ['L-FPS-SCHEDULE'],
            "this.schedule(this.tick, this.interval);": [],
        }
        for call, rules in cases.items():
            with self.subTest(call=call):
                src = 'cc.Class({ start: function () { %s }, tick: function () { this.node.x += 4; }, ' \
                      'count: function () { this.n = this.n + 1; } });\n' % call
                self.assertEqual(sorted(r[0] for r in self.fps({'assets/S.js': src})), rules)

    def test_not_frame_rate_bugs(self):
        src = '''export class Calm extends cc.Component {
    update(dt) {
        this.icon.angle -= 20;
        let pos = this.node.getPosition(); pos.y += 40; this.bar.setPosition(pos);
        this.body.linearVelocity = cc.v2(this.runSpeed, this.body.linearVelocity.y);
        this.hurt.linearVelocity = this.weapon.linearVelocity;
        if (this.node.y < -1800) this.node.setPosition(this.node.x, this.top.y + 2000);
    }
    onLoad() { this.schedule(this.second, 1); cc.director.getPhysicsManager().enabled = false; }
    second() { this.node.x += 10; }
}
'''
        self.assertEqual(self.fps({'assets/Calm.ts': src}), [])

    def test_legacy_games_get_a_warning_not_a_block(self):
        with patch.object(logic_check, 'game_policy', return_value='legacy'):
            got = self.fps({'assets/Script/RunUI.ts': DRIFT_RUNUI, 'assets/Script/pysTouchEvent.ts': DRIFT_TOUCH})
        self.assertTrue(got)
        self.assertEqual({r[1] for r in got}, {'hint'})

    def test_policy_defaults_to_new(self):
        self.assertEqual(logic_check.game_policy(project(self.root / 'empty', {'assets/a.ts': ''})), 'new')


if __name__ == '__main__':
    unittest.main()
