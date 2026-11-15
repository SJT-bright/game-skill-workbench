"""简化.11.14.1 (Codex 英化会话 2026-11-05): art_check told an English game with no coins, random levels and no home page
to add a coin top bar, a level table and a map. Those two rows (顶部资源栏, 关卡地图) are remake-board designs. English
games without any remake-board record get 不适用 and the two sub-checks do not run; remake games, unknown boards and
English games that used those boards for new gameplay Saul asked for are checked as before.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_check  # noqa: E402
import feature_policy  # noqa: E402

RULES = ('top_bar', 'level_map')


class Policy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / 'game'
        (self.proj / 'assets').mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_english_game_without_board_records_does_not_get_the_rows(self):
        for rule in RULES:
            self.assertEqual(feature_policy.applies(rule, 'localize', self.proj), 'not_applicable')
            self.assertIn('不适用', art_check.design_row_not_applicable(self.proj, 'localize', rule))

    def test_english_game_redrawn_in_remake_style_still_adds_no_systems(self):
        (self.proj / 'docs').mkdir()
        (self.proj / 'docs/art-style.txt').write_text('remake', encoding='utf-8')
        for rule in RULES:
            self.assertEqual(feature_policy.applies(rule, 'localize', self.proj), 'not_applicable')

    def test_english_game_that_used_a_board_is_checked(self):
        for record in feature_policy.LOCALIZE_BOARD_RECORDS:
            with self.subTest(record=record):
                path = self.proj / record
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}', encoding='utf-8')
                for rule in RULES:
                    self.assertEqual(feature_policy.applies(rule, 'localize', self.proj), 'block')
                    self.assertIsNone(art_check.design_row_not_applicable(self.proj, 'localize', rule))
                path.unlink()

    def test_remake_and_unknown_boards_are_checked(self):
        for board in ('remake', None, 'something-else'):
            for rule in RULES:
                self.assertEqual(feature_policy.applies(rule, board, self.proj), 'block')

    def test_same_records_as_preflight(self):
        import preflight
        self.assertEqual(feature_policy.LOCALIZE_BOARD_RECORDS, preflight.LOCALIZE_BOARD_RECORDS)
        self.assertTrue({'顶部资源栏', '关卡地图'} <= preflight.LOCALIZE_NOT_ADDED)


class ArtCheckRows(unittest.TestCase):
    """art_check.main with every sub-tool faked: which sub-checks run and what the two rows say."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def project(self, name, board, record=None):
        proj = self.root / name
        (proj / 'assets').mkdir(parents=True)
        (proj / 'docs/art').mkdir(parents=True)
        (proj / '.tiktok-kit').mkdir()
        (proj / '.tiktok-kit/finalize-source.json').write_text(json.dumps({'board': board}), encoding='utf-8')
        if record:
            path = proj / record
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}', encoding='utf-8')
        dumps = proj / 'docs/test'
        dumps.mkdir()
        manifest = {'runtime_verified': True, 'screens': [{'id': 'home', 'name': 'Home'}, {'id': 'play', 'name': 'Play'}],
                    'required_viewports': [{'name': 'a', 'width': 390, 'height': 844}, {'name': 'b', 'width': 375, 'height': 812}]}
        (proj / 'docs/art/screens.json').write_text(json.dumps(manifest), encoding='utf-8')
        for screen in ('home', 'play'):
            for i, vp in enumerate(manifest['required_viewports']):
                shot = '%s-ui-shot-%d.png' % (screen, i)
                (dumps / shot).write_bytes(b'fixture only')
                (dumps / ('%s-ui-dump-%d.json' % (screen, i))).write_text(json.dumps(
                    {'screen': screen, 'kind': 'gameplay' if screen == 'play' else 'page', 'viewport': vp,
                     'screenshot': shot, 'nodes': []}), encoding='utf-8')
        return proj

    def run_art_check(self, proj):
        out, called = self.root / ('out-' + proj.name), []

        def fake(name, args, logs):
            called.append(name)
            return 0, '{"status": "pass", "passed": true, "checks": [], "findings": []}'
        with patch.object(sys, 'argv', ['art_check.py', '--project', str(proj), '--out', str(out)]), \
                patch.object(art_check, 'run', side_effect=fake), \
                patch('audit_no_social_features.audit', return_value={'passed': True}), \
                contextlib.redirect_stdout(io.StringIO()):
            art_check.main()
        report = json.loads((out / 'art-check.json').read_text(encoding='utf-8'))
        rows = {r['check']: r for r in report['rows']}
        return report, rows, called

    def test_english_game_without_records(self):
        report, rows, called = self.run_art_check(self.project('en', 'localize'))
        self.assertNotIn('audit_top_bar.py', called)
        self.assertNotIn('audit_level_plan.py', called)
        self.assertEqual(rows['顶部资源栏']['status'], '不适用')
        self.assertEqual(rows['关卡地图']['status'], '不适用')
        self.assertFalse(any(x.startswith('顶部资源栏') or x.startswith('关卡地图（') for x in report['look_list']))
        md = (self.root / 'out-en' / 'art-check.md').read_text(encoding='utf-8')
        self.assertNotIn('- [ ] 顶部资源栏', md)

    def test_english_game_with_records_and_remake_game_still_run_the_checks(self):
        for name, board, record in (('en-used', 'localize', 'docs/top-bar.json'), ('remake', 'remake', None)):
            with self.subTest(game=name):
                report, rows, called = self.run_art_check(self.project(name, board, record))
                self.assertIn('audit_top_bar.py', called)
                self.assertIn('audit_level_plan.py', called)
                self.assertNotEqual(rows['顶部资源栏']['status'], '不适用')
                self.assertNotEqual(rows['关卡地图']['status'], '不适用')
                self.assertTrue(any(x.startswith('顶部资源栏') for x in report['look_list']))


if __name__ == '__main__':
    unittest.main()
