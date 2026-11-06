"""R4N1 (补查2 第 5 组: SLS07, SLS35, 弹球传奇): four new-game rules that an English game's original gameplay does not
follow. Same call as test_localize_design_rows.py (top_bar / level_map): English games without a record of that board
get 不适用; remake games, unknown boards and English games with the board record are checked as before.

  skin_min_levels     make_skin_table.py --levels refused --final-level < 60 (SLS35: original 6 levels)
  econ_window_levels  make_economy_config.py refused --total-levels < 10 (SLS35)
  writer_coin_reward  check_kit_project.py refused PlatformConfig normalLevelCoins 0 (SLS07: no coins)
  checkin_design      CheckinFlow design rows: ad-boost/vendor/系统库/07_签到/参考实现/test_CheckinFlow.js (node)
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import feature_policy  # noqa: E402

RULES = ('skin_min_levels', 'econ_window_levels', 'checkin_design', 'writer_coin_reward')
KIT_CHECK = HERE.parent / 'assets' / 'platform-kit' / 'tools' / 'check_kit_project.py'


def project(root, name, board, levels=None, records=(), wallet=None):
    proj = Path(root) / name
    (proj / 'assets').mkdir(parents=True)
    (proj / '.tiktok-kit').mkdir()
    (proj / '.tiktok-kit/finalize-source.json').write_text(json.dumps({'board': board}), encoding='utf-8')
    (proj / 'docs').mkdir()
    if levels is not None:
        (proj / 'docs/game_capabilities.json').write_text(json.dumps(
            {'schema': 'game_capabilities.v1', 'level_count': levels, 'evidence': {}, 'written_by': 'test'}), encoding='utf-8')
    if wallet is not None:
        (proj / 'docs/economy').mkdir(parents=True, exist_ok=True)
        (proj / 'docs/economy/economy_capabilities.json').write_text(json.dumps(
            {'schema': 'economy_capabilities.v1', 'wallet': wallet, 'items': False, 'skins': False, 'energy': False}),
            encoding='utf-8')
    for rec in records:
        p = proj / rec
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{}', encoding='utf-8')
    return proj


def run_main(mod, argv):
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        try:
            code = mod.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, err.getvalue()


class Policy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_english_not_applicable_remake_blocks(self):
        en = project(self.tmp.name, 'en', 'localize')
        for rule in RULES:
            self.assertEqual(feature_policy.applies(rule, 'localize', en), 'not_applicable', rule)
            for board in ('remake', None):
                self.assertEqual(feature_policy.applies(rule, board, en), 'block', rule)

    def test_english_with_board_record_is_checked(self):
        for rule in RULES:
            for rec in feature_policy.RULE_RECORDS[rule]:
                with self.subTest(rule=rule, record=rec):
                    proj = project(self.tmp.name, '%s-%s' % (rule, rec.replace('/', '_')), 'localize', records=[rec])
                    self.assertEqual(feature_policy.applies(rule, 'localize', proj), 'block')

    def test_skin_cli_own_output_does_not_switch_the_rule_on(self):
        proj = project(self.tmp.name, 'rerun', 'localize', records=['assets/resources/config/unlock_table.json'])
        self.assertEqual(feature_policy.applies('skin_min_levels', 'localize', proj), 'not_applicable')

    def test_english_game_with_wallet_still_needs_B(self):
        proj = project(self.tmp.name, 'coins', 'localize', wallet=True)
        self.assertEqual(feature_policy.applies('writer_coin_reward', 'localize', proj), 'block')

    def test_level_count_record(self):
        import game_capabilities
        self.assertEqual(feature_policy.game_levels(project(self.tmp.name, 'six', 'localize', levels=6))[0], 6)
        self.assertEqual(game_capabilities.validate({'schema': game_capabilities.SCHEMA, 'level_count': 0}),
                         ['level_count must be the real number of levels (>= 1) or {"none": "why: endless / no levels"}'])


class SkinCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import make_skin_table
        self.mod = make_skin_table

    def tearDown(self):
        self.tmp.cleanup()

    def test_english_6_levels_writes_a_table(self):
        proj = project(self.tmp.name, 'sls35', 'localize', levels=6)
        out = Path(self.tmp.name) / 'unlock.json'
        code, err = run_main(self.mod, ['--R', '10', '--levels', '--project', str(proj), '--out', str(out)])
        self.assertIn(code, (0, None), err)
        table = json.loads(out.read_text(encoding='utf-8'))
        self.assertTrue(any(r['group'] == 'skin' for r in table['items']))
        self.assertTrue(all((r.get('level') or 0) <= 6 for r in table['items']))   # nothing past the real last level
        self.assertIn('不适用', err)

    def test_remake_6_levels_refused(self):
        proj = project(self.tmp.name, 'remake', 'remake', levels=6)
        code, err = run_main(self.mod, ['--R', '10', '--levels', '--final-level', '6', '--project', str(proj),
                                        '--out', str(Path(self.tmp.name) / 'x.json')])
        self.assertEqual(code, 2)
        self.assertIn('60 levels or more', err)


class EconomyCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import make_economy_config
        self.mod = make_economy_config

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, proj, *more):
        return ['--B', '10', '--systems', 'checkin,shortcut,revisit', '--out-dir', str(Path(self.tmp.name) / proj.name),
                '--project', str(proj)] + list(more)

    def test_english_6_levels_window_shrinks(self):
        proj = project(self.tmp.name, 'sls35', 'localize', levels=6)
        code, err = run_main(self.mod, self.args(proj, '--kind', 'english'))
        self.assertEqual(code, 0, err)
        cfg = json.loads((Path(self.tmp.name) / 'sls35' / 'economy_config.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cfg['level_reward']['per_level']), 6)
        self.assertEqual(cfg['level_reward']['window_levels'], 6)

    def test_remake_6_levels_refused(self):
        proj = project(self.tmp.name, 'remake', 'remake', levels=6)
        code, err = run_main(self.mod, self.args(proj, '--total-levels', '6'))
        self.assertEqual(code, 2)
        self.assertIn('--total-levels must be at least 10', err)


class WriterCoinGate(unittest.TestCase):
    """check_kit_project.py (the package writer's kit gate) on a fake project whose only error would be the coin line."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def kit_project(self, name, board, wallet=None):
        proj = project(self.tmp.name, name, board, wallet=wallet)
        (proj / 'project.json').write_text(json.dumps({'version': '2.4.15'}), encoding='utf-8')
        cfg = (HERE.parent / 'assets/platform-kit/assets/tiktok-platform/PlatformConfig.js').read_text(encoding='utf-8')
        (proj / 'assets/PlatformConfig.js').write_text(cfg.replace("gameId: 'change-me'", "gameId: 'sls07'"), encoding='utf-8')
        return proj

    def coin_lines(self, proj):
        out = Path(self.tmp.name) / (proj.name + '.json')
        subprocess.run([sys.executable, str(KIT_CHECK), '--project', str(proj), '--out', str(out)],
                       capture_output=True, text=True, timeout=60)
        rep = json.loads(out.read_text(encoding='utf-8'))
        pick = lambda xs: [x for x in xs if 'normalLevelCoins' in x]  # noqa: E731
        return pick(rep.get('errors', [])), pick(rep.get('warnings', []))

    def test_english_no_coin_game_is_a_warning(self):
        errors, warnings = self.coin_lines(self.kit_project('sls07', 'localize', wallet=False))
        self.assertEqual(errors, [])
        self.assertTrue(warnings and 'allowed' in warnings[0])

    def test_remake_and_english_with_wallet_still_refused(self):
        for name, board, wallet in (('remake', 'remake', None), ('en-coins', 'localize', True)):
            with self.subTest(game=name):
                errors, _ = self.coin_lines(self.kit_project(name, board, wallet))
                self.assertTrue(errors, name)


class CheckinFlowJs(unittest.TestCase):
    def test_checkin_design_cases(self):
        js = HERE.parent.parent / 'ad-boost/vendor/系统库/07_签到/参考实现/test_CheckinFlow.js'
        if not js.is_file():
            self.skipTest('ad-boost not next to remake-core')
        r = subprocess.run(['node', str(js)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])
        self.assertIn('R4N1 英化 design original', r.stdout)


if __name__ == '__main__':
    unittest.main()
