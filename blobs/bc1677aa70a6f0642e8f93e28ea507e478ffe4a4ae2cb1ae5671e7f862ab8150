#!/usr/bin/env python3
"""R4O6: preflight runs cocos-game-to-english/scripts/english_copy_guard.py --dry-run on an English project that has
docs/copy/copy-table.csv. A RichText `</c>` and a recorded ad button saying CLAIM are listed as 提示 (calibrated
11-05: blocking would stop 火箭三消, a game in progress); the project is not written. The other tools are stubbed,
the guard runs for real. Run: python3 -B test_preflight_copy_guard.py   (about a second)"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight  # noqa: E402

ENGLISH = HERE.parent.parent / 'cocos-game-to-english'
GUARD = ENGLISH / 'scripts' / 'english_copy_guard.py'
REAL_RUN = preflight.run


def prefab(rich, button_text):
    return [
        {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
        {'__type__': 'cc.Node', '_name': 'WinPanel', '_parent': None, '_children': [{'__id__': 2}, {'__id__': 6}],
         '_components': []},
        {'__type__': 'cc.Node', '_name': 'btnDouble', '_parent': {'__id__': 1}, '_children': [{'__id__': 4}],
         '_components': [{'__id__': 3}]},
        {'__type__': 'cc.Button', 'node': {'__id__': 2}},
        {'__type__': 'cc.Node', '_name': 'txt', '_parent': {'__id__': 2}, '_children': [], '_components': [{'__id__': 5}]},
        {'__type__': 'cc.Label', 'node': {'__id__': 4}, '_string': button_text, '_N$string': button_text},
        {'__type__': 'cc.Node', '_name': 'help', '_parent': {'__id__': 1}, '_children': [], '_components': [{'__id__': 7}]},
        {'__type__': 'cc.RichText', 'node': {'__id__': 6}, '_N$string': rich},
    ]


# 简化.11.16 发版（英化skill）：remake-core 两包共用；重塑对照树旁边没有英化入口，这组只在英化包里跑。英化包里缺了 guard 照样失败。
@unittest.skipUnless(ENGLISH.is_dir(), 'cocos-game-to-english 不在 remake-core 旁边（重塑包），这组只查英化包')
class PreflightCopyGuard(unittest.TestCase):
    def run_preflight(self, board='localize', table=True, rich='Match <color=#ffde00>3</c> to clear',
                      button='CLAIM x2'):
        calls = {}

        def stub(name, args, logs):
            calls[Path(name).name] = [str(x) for x in args]
            if Path(name).name == 'english_copy_guard.py':
                return REAL_RUN(name, args, logs)
            payload = {'failed': 0, 'checked': 1, 'blocking': 0, 'review': 0, 'runtime_strings': 1, 'known_risks': [],
                       'found': [], 'decision': {}, 'passed': True, 'errors': [], 'problems': [], 'findings': [],
                       'status': 'markers_present_requires_behavior_review', 'source_missing': [],
                       'share_calls_in_source': {}}
            return 0, json.dumps(payload)

        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / 'game'
            for d in ('assets/ui', 'docs/copy'):
                (game / d).mkdir(parents=True)
            (game / 'assets/ui/Win.prefab').write_text(json.dumps(prefab(rich, button), indent=2), encoding='utf-8')
            (game / 'docs/game_capabilities.json').write_text(json.dumps({'schema': 1, 'ad_entries': [{'role': 'double', 'button': 'WinPanel/btnDouble'}]}))
            if table:
                (game / 'docs/copy/copy-table.csv').write_text('zh,en,where,pointer\n领取,CLAIM,,\n', encoding='utf-8')
            before = sorted(p.relative_to(game).as_posix() for p in game.rglob('*'))
            out = Path(tmp) / 'out'
            argv = ['preflight.py', '--project', str(game), '--board', board, '--out', str(out)]
            with patch.object(sys, 'argv', argv), patch.object(preflight, 'run', side_effect=stub), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = preflight.main()
            rows = {r['check']: r for r in json.loads((out / 'preflight.json').read_text())['results']}
            after = sorted(p.relative_to(game).as_posix() for p in game.rglob('*'))
            record = json.loads((out / 'copy_guard.json').read_text()) if (out / 'copy_guard.json').is_file() else None
        return code, rows, calls, before == after, record

    def test_guard_installed_next_to_preflight(self):
        self.assertTrue(GUARD.is_file(), GUARD)

    def test_unpaired_richtext_and_claim_button_are_hints(self):
        code, rows, calls, untouched, record = self.run_preflight()
        self.assertIn('--dry-run', calls['english_copy_guard.py'])
        row = rows['文案写入校验']
        self.assertEqual(row['status'], '提示', row)
        self.assertIn('2处要改', row['detail'])
        self.assertIn('RichText tags', row['detail'])
        self.assertIn('CLAIM x2', row['detail'])
        self.assertTrue(untouched, 'preflight must not write into the project')
        self.assertFalse(record['passed'])
        self.assertEqual(code, 0, 'calibration: a hint only, not 需处理')

    def test_clean_copy_passes(self):
        _, rows, _, _, record = self.run_preflight(rich='Match <color=#ffde00>3</color> to clear', button='WATCH AD x2')
        self.assertEqual(rows['文案写入校验']['status'], '通过', rows['文案写入校验'])
        self.assertTrue(record['passed'])

    def test_not_run_without_copy_table_or_on_remake(self):
        for kw in ({'table': False}, {'board': 'remake'}):
            _, rows, calls, _, record = self.run_preflight(**kw)
            self.assertNotIn('english_copy_guard.py', calls, kw)
            self.assertNotIn('文案写入校验', rows, kw)
            self.assertIsNone(record)


if __name__ == '__main__':
    unittest.main()
