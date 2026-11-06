#!/usr/bin/env python3
"""R4O3 (补查2 第 5 组, SLS07; Saul 2026-11-04 ECON-SHORTCUT / ECON-REVISIT): check_kit_project.py, run by the package
writer, reports K_home_entries_no_reward when an English game without coins (normalLevelCoins 0 allowed by R4N1) uses
HomeGrowthEntries but passes no reward option. Block when the project recorded wallet false
(docs/economy/economy_capabilities.json), warning otherwise; nothing when the reward option is wired, when the game has
coins, or when HomeGrowthEntries is not used. Old check_kit_project.py: KIT_CHECK=<old file> python3 this file (fails).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent / 'assets' / 'platform-kit'
KIT_CHECK = Path(os.environ.get('KIT_CHECK') or KIT / 'tools' / 'check_kit_project.py')

# SLS07-like home script: the kit component with the energy replacement, and the same call without it.
HOME_WIRED = """cc.Class({ extends: cc.Component,
  start: function () {
    var entries = this.node.getComponent('HomeGrowthEntries');
    entries.init(this.save, {reward: function (kind, draft) { draft.energy = (Number(draft.energy) || 0) + 3; },
                             rewardText: '+3 Energy', onGranted: this.refreshTop.bind(this)});
  }
});
"""
HOME_BARE = """cc.Class({ extends: cc.Component,
  start: function () {
    this.node.getComponent('HomeGrowthEntries').init(this.save, {onGranted: this.refreshTop.bind(this), rewardText: '+3'});
  }
});
"""


def project(root, name, board='localize', wallet=None, home=None, coins=0):
    proj = Path(root) / name
    (proj / 'assets' / 'scripts').mkdir(parents=True)
    (proj / '.tiktok-kit').mkdir()
    (proj / '.tiktok-kit/finalize-source.json').write_text(json.dumps({'board': board}), encoding='utf-8')
    (proj / 'docs').mkdir()
    (proj / 'project.json').write_text(json.dumps({'version': '2.4.15'}), encoding='utf-8')
    if wallet is not None:
        (proj / 'docs/economy').mkdir()
        (proj / 'docs/economy/economy_capabilities.json').write_text(json.dumps(
            {'schema': 'economy_capabilities.v1', 'wallet': wallet, 'items': False, 'skins': False, 'energy': True}),
            encoding='utf-8')
    cfg = (KIT / 'assets/tiktok-platform/PlatformConfig.js').read_text(encoding='utf-8')
    cfg = cfg.replace("gameId: 'change-me'", "gameId: 'sls07'").replace('normalLevelCoins: 0,', 'normalLevelCoins: %d,' % coins)
    (proj / 'assets/PlatformConfig.js').write_text(cfg, encoding='utf-8')
    if home is not None:
        (proj / 'assets/scripts/HomeScene.js').write_text(home, encoding='utf-8')
    return proj


class NoCoinEntriesGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def lines(self, proj):
        out = Path(self.tmp.name) / (proj.name + '.json')
        subprocess.run([sys.executable, str(KIT_CHECK), '--project', str(proj), '--out', str(out)],
                       capture_output=True, text=True, timeout=60)
        rep = json.loads(out.read_text(encoding='utf-8'))
        pick = lambda xs: [x for x in xs if 'K_home_entries_no_reward' in x]  # noqa: E731
        return pick(rep.get('errors', [])), pick(rep.get('warnings', []))

    def test_recorded_no_coin_game_without_reward_is_blocked(self):
        errors, warnings = self.lines(project(self.tmp.name, 'sls07-new', wallet=False, home=HOME_BARE))
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('assets/scripts/HomeScene.js', errors[0])
        self.assertEqual(warnings, [])

    def test_unrecorded_english_game_without_reward_is_a_warning(self):
        errors, warnings = self.lines(project(self.tmp.name, 'sls07-old', home=HOME_BARE))
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)

    def test_reward_option_wired_passes(self):
        errors, warnings = self.lines(project(self.tmp.name, 'sls07-wired', wallet=False, home=HOME_WIRED))
        self.assertEqual((errors, warnings), ([], []))

    def test_not_used_or_game_with_coins_says_nothing(self):
        for name, kw in (('no-entries', {'wallet': False}),
                         ('coins', {'board': 'remake', 'home': HOME_BARE, 'coins': 12})):
            with self.subTest(game=name):
                self.assertEqual(self.lines(project(self.tmp.name, name, **kw)), ([], []))


if __name__ == '__main__':
    unittest.main()
