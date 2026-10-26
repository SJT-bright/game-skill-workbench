#!/usr/bin/env python3
"""Regression tests for forwarding preservation/build inputs through preflight."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import preflight


class PreflightMaintenanceTests(unittest.TestCase):
    def test_cli_forwards_scope_binding_board_visual_policy_and_external_copy_docs(self):
        with tempfile.TemporaryDirectory(prefix='preflight-maintenance-') as tmp:
            root = Path(tmp)
            project = root / 'game'
            (project / 'assets').mkdir(parents=True)
            (project / 'docs').mkdir()
            screens = root / 'screens'
            screens.mkdir()
            (screens / 'home-ui-shot.png').write_bytes(b'synthetic screen placeholder intercepted by the test runner')
            (project / 'docs/ui-layout.json').write_text('{}', encoding='utf-8')
            (project / 'docs/features.json').write_text(json.dumps({
                'schema': 'optional_features.v1', 'asked': 'preserve original game',
                'skin_bonus': False, 'daily_checkin': True,
            }), encoding='utf-8')
            scope = root / 'maintenance-scope.json'
            binding = root / 'review.json'
            visual_policy = root / 'visual-policy.json'
            copy_table = root / 'copy-table.csv'
            glossary = root / 'glossary.json'
            for path in (scope, binding, visual_policy, copy_table, glossary):
                path.write_text('{}', encoding='utf-8')
            out = root / 'preflight'
            calls = {}

            def stub_run(name, args, logs):
                calls[name] = [str(x) for x in args]
                # Minimal valid summaries exercise the preflight result routing while
                # the focused CLI integration tests cover the actual maintenance audits.
                payload = {
                    'failed': 0, 'blocking': 0, 'review': 0, 'checked': 1,
                    'runtime_strings': 1, 'known_risks': [], 'dev_text': [],
                    'placeholder_art': 0, 'worst': [], 'problems': [], 'found': [],
                    'source_missing': [], 'native_missing': [], 'unreadable_text': 0,
                    'text_candidates': 0, 'unique_images_requiring_review': 0,
                    'attribution_required': 0, 'reward_apis': [],
                    'decision': {'skins': False, 'currency': 'Coins'},
                    'passed': True, 'implementation': 'production_js', 'mode': 'endless',
                    'errors': [], 'warnings': [], 'dev_text': [],
                }
                return 0, json.dumps(payload)

            argv = [
                'preflight.py', '--project', str(project), '--board', 'localize',
                '--maintenance-scope', str(scope), '--binding', str(binding),
                '--maintenance-visual-policy', str(visual_policy),
                '--copy-table', str(copy_table), '--glossary', str(glossary),
                '--screens', str(screens), '--recheck-earlier',
                '--out', str(out),
            ]
            with patch.object(sys, 'argv', argv), patch.object(preflight, 'run', side_effect=stub_run), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = preflight.main()

            self.assertEqual(code, 0, (out / 'preflight.md').read_text(encoding='utf-8'))

            def has(name, *items):
                args = [str(Path(x).resolve()) if x.startswith('/') else x for x in calls[name]]
                for item in items:
                    expected = str(item.resolve()) if isinstance(item, Path) else str(item)
                    self.assertIn(expected, args, (name, args))

            has('audit_copy_quality.py', '--copy-table', copy_table, '--glossary', glossary, '--binding', binding)
            has('audit_game_modules.py', '--maintenance-scope', scope, '--binding', binding, '--board', 'localize')
            has('audit_optional_features.py', '--maintenance-scope', scope, '--binding', binding)
            has('audit_acquisition_progression.py', '--maintenance-scope', scope, '--binding', binding, '--project', project)
            has('audit_league.py', '--board', 'localize', '--binding', binding)
            has('audit_level_plan.py', '--board', 'localize', '--binding', binding)
            has('audit_page_richness.py', '--maintenance-scope', scope, '--maintenance-visual-policy', visual_policy,
                '--binding', binding)

            rows = {row['check']: row['status'] for row in json.loads((out / 'preflight.json').read_text())['results']}
            self.assertEqual(rows['关卡地图'], '通过')  # an endless plan's no-map result stays valid
            self.assertEqual(rows['签到扩展'], '通过')  # existing JS behavior is handled by the bound maintenance branch
            details = {row['check']: row['detail'] for row in json.loads((out / 'preflight.json').read_text())['results']}
            self.assertIn('生产版 JavaScript', details['内置板块'])
            self.assertIn('没有要求 DailyCheckin.ts 模板', details['签到扩展'])

    def test_default_skips_earlier_tools_but_keeps_functional_failures(self):
        earlier = {'audit_image_clarity.py', 'audit_dark_area.py', 'audit_ui_coverage.py',
                   'audit_acquisition_progression.py', 'audit_game_modules.py', 'audit_league.py',
                   'audit_optional_features.py', 'audit_top_bar.py', 'audit_level_plan.py',
                   'audit_page_richness.py'}
        for recheck, functional_failure in ((False, False), (False, True), (True, False)):
            with self.subTest(recheck=recheck, functional_failure=functional_failure), \
                    tempfile.TemporaryDirectory(prefix='preflight-scope-') as tmp:
                root = Path(tmp)
                project = root / 'game'
                (project / 'assets').mkdir(parents=True)
                (project / 'docs').mkdir()
                (project / 'docs/features.json').write_text('{}')
                (project / 'docs/ui-layout.json').write_text('{}')
                shots = project / 'docs/test'
                shots.mkdir()
                (shots / 'home-ui-shot.png').write_bytes(b'intercepted synthetic image')
                economy = project / 'docs/economy'
                economy.mkdir()
                (economy / 'unlock_table.json').write_text('{}')
                calls = []

                def stub(name, args, logs):
                    calls.append(name)
                    payload = {'failed': 0, 'checked': 1, 'blocking': 0, 'review': 0,
                               'runtime_strings': 1, 'known_risks': [], 'found': [],
                               'decision': {}, 'passed': True, 'errors': []}
                    if name == 'audit_startup_contract.py' and functional_failure:
                        payload.update(failed=1, problems=['required startup request failed'])
                    if name == 'audit_image_clarity.py':
                        payload.update(upscaled=1)
                    return 0, json.dumps(payload)

                out = root / 'out'
                argv = ['preflight.py', '--project', str(project), '--board', 'remake', '--out', str(out)]
                if recheck:
                    argv.append('--recheck-earlier')
                with patch.object(sys, 'argv', argv), patch.object(preflight, 'run', side_effect=stub), \
                        contextlib.redirect_stdout(io.StringIO()):
                    code = preflight.main()
                rows = {r['check']: r for r in json.loads((out / 'preflight.json').read_text())['results']}
                self.assertIn('audit_startup_contract.py', calls)
                if not recheck:
                    self.assertFalse(earlier.intersection(calls), calls)
                    for title in preflight.EARLIER_ROWS:
                        self.assertEqual(rows[title]['status'], '提示')
                        self.assertIn('本次未执行', rows[title]['detail'])
                else:
                    self.assertTrue(earlier.issubset(calls), calls)
                    self.assertEqual(rows['清晰度']['status'], '需处理')
                self.assertEqual(code, 1 if functional_failure or recheck else 0)

    def test_maintenance_scope_requires_current_binding(self):
        with tempfile.TemporaryDirectory(prefix='preflight-binding-') as tmp:
            root = Path(tmp)
            project = root / 'game'
            (project / 'assets').mkdir(parents=True)
            scope = root / 'scope.json'
            scope.write_text('{}', encoding='utf-8')
            with patch.object(sys, 'argv', ['preflight.py', '--project', str(project),
                                           '--maintenance-scope', str(scope), '--out', str(root / 'out')]):
                with self.assertRaises(SystemExit) as result:
                    preflight.main()
            self.assertEqual(result.exception.code, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
