#!/usr/bin/env python3
"""v7.8 (总表 P16 第 1 步): source step tiktok_finalize_steps/physics_clock.py gives a NEW Cocos 2.4 game that switches
physics on (without enabledAccumulator) the platform-kit physics clock assets/tiktok-platform/PhysicsClock.js; legacy games,
games that set the accumulator themselves, games without physics and Cocos 3.x get nothing written. After the install
logic_check's L-FPS-ACCUM is satisfied (the kit file sets the accumulator); L-FPS-DT (pushes without dt) still reports.
Synthetic projects only; calibration on real projects is in briefs/out/W92/RESULT.md. Run: python3 -B test_physics_clock.py"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import logic_check  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import physics_clock as PC  # noqa: E402

RUN_UI = "cc.director.getPhysicsManager().enabled = true;\ncc.director.getPhysicsManager().gravity = cc.v2(0, 0);\n"
PUSH = ("export default class Car extends cc.Component {\n  gameStart() { this.schedule(this.run_time, 0.01); }\n"
        "  run_time() { this.body.applyForceToCenter(cc.v2(0, 65), true); }\n}\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='physics clock ')
        self.root = Path(self.temp.name) / 'Game'
        (self.root / 'assets' / 'Script').mkdir(parents=True)
        self.manifest = T.load_manifest()
        self.kit = (self.manifest.kit_dir / PC.KIT_KEY).read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def step(self, policy='new', engine=2):
        ctx = T.Ctx('source', self.root, engine=engine, policy=policy, manifest=self.manifest)
        return PC.apply(ctx), ctx

    @property
    def dest(self):
        return self.root / PC.DEST


class Install(Base):
    def test_new_physics_game_gets_the_clock(self):
        self.write('assets/Script/RunUI.ts', RUN_UI)
        out, ctx = self.step()
        self.assertEqual(out['blocks'], [])
        self.assertEqual(self.dest.read_bytes(), self.kit)
        self.assertEqual([c['file'] for c in out['changed']], [PC.DEST])
        self.assertEqual(PC.detect(ctx), 'kit_current')
        again, _ = self.step()                                  # second run: nothing to do
        self.assertEqual((again['state'], again['changed']), ('kit_current', []))
        self.assertTrue(any('L-FPS-DT' in i for i in out['info']))

    def test_alias_form_and_own_copy_restored(self):
        self.write('assets/Script/Game.js', 'var pm = cc.director.getPhysicsManager();\npm.enabled = true;\n')
        self.write(PC.DEST, '// an edited copy\n')
        out, _ = self.step()
        self.assertEqual(self.dest.read_bytes(), self.kit)
        self.assertEqual(out['state'], 'own')
        self.assertTrue(any(i.startswith('moved own') for i in out['info']), out['info'])
        self.assertTrue((self.root / '.tiktok-kit' / 'removed' / PC.DEST).is_file())

    def test_logic_check_accum_rule_satisfied_after_install_dt_rule_still_reports(self):
        self.write('assets/Script/RunUI.ts', RUN_UI)
        self.write('assets/Script/Car.ts', PUSH)
        rules = lambda: sorted({f['rule'] for f in logic_check.frame_rate_suspects(logic_check.scripts(self.root))})
        self.assertEqual(rules(), ['L-FPS-ACCUM', 'L-FPS-DT', 'L-FPS-SCHEDULE'])
        self.step()
        self.assertEqual(rules(), ['L-FPS-DT', 'L-FPS-SCHEDULE'])


class LeftAlone(Base):
    def test_legacy_game_is_never_changed(self):
        self.write('assets/Script/RunUI.ts', RUN_UI)
        out, _ = self.step(policy='legacy')
        self.assertFalse(self.dest.exists())
        self.assertEqual(out['changed'], [])
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_physics_clock_legacy'])

    def test_game_sets_the_accumulator_itself(self):
        self.write('assets/Script/RunUI.ts', RUN_UI + 'cc.director.getPhysicsManager().enabledAccumulator = true;\n')
        out, _ = self.step()
        self.assertEqual((out['state'], out['changed'], out['warnings']), ('n/a', [], []))
        self.assertFalse(self.dest.exists())

    def test_no_physics_and_cocos3(self):
        self.write('assets/Script/Menu.ts', 'cc.log("no physics here"); this.node.x += 5;\n')
        out, _ = self.step()
        self.assertEqual((out['state'], out['changed']), ('n/a', []))
        self.write('assets/Script/RunUI.ts', RUN_UI)
        out, _ = self.step(engine=3)
        self.assertEqual((out['state'], out['changed']), ('n/a', []))
        self.assertFalse(self.dest.exists())

    def test_kit_folder_and_comments_do_not_count(self):
        self.write('assets/tiktok-platform/Other.js', RUN_UI)        # the kit folder is not the game's code
        self.write('assets/Script/Note.ts', '// cc.director.getPhysicsManager().enabled = true;\n')
        out, _ = self.step()
        self.assertEqual(out['state'], 'n/a')

    def test_own_module_name_is_not_overwritten(self):
        self.write('assets/Script/RunUI.ts', RUN_UI)
        self.write('assets/Script/PhysicsClock.ts', 'export const x = 1;\n')
        out, _ = self.step()
        self.assertFalse(self.dest.exists())
        self.assertEqual([w['id'] for w in out['warnings']], ['K_W_physics_clock_name'])


class Wiring(Base):
    def test_in_the_source_phase_and_manifest(self):
        self.assertIn('physics_clock', T.SOURCE_STEPS)
        self.assertIn('physics_clock', F.SOURCE_STEPS)
        self.assertLess(T.SOURCE_STEPS.index('kit_sources'), T.SOURCE_STEPS.index('physics_clock'))
        spec = self.manifest.files[PC.KIT_KEY]
        self.assertEqual((spec['reference'], spec['optional'], spec['project_path']), (True, True, PC.DEST))
        self.assertEqual(T.sha256(self.kit), spec['sha256'])
        self.assertNotIn(PC.DEST, self.manifest.files)            # kit_sources never copies it into every game

    def test_finalize_source_new_and_legacy(self):
        self.write('assets/Script/RunUI.ts', RUN_UI)
        record = F.finalize_source(self.root, 'remake', engine=2, policy='new', manifest=self.manifest, write_record=False)
        step = [s for s in record['steps'] if s['step'] == 'physics_clock'][0]
        self.assertEqual([c['file'] for c in step['changed']], [PC.DEST])
        self.assertTrue(self.dest.is_file())
        shutil.rmtree(self.root / 'assets' / 'tiktok-platform')
        record = F.finalize_source(self.root, 'remake', engine=2, policy='legacy', manifest=self.manifest, write_record=False)
        step = [s for s in record['steps'] if s['step'] == 'physics_clock'][0]
        self.assertEqual(step['changed'], [])
        self.assertFalse(self.dest.exists())


if __name__ == '__main__':
    unittest.main(verbosity=1)
