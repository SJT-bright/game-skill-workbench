#!/usr/bin/env python3
"""v7.5 preflight rules (Germ2048 item 2): abnormal marker status is 需处理, new rows run, final stage turns 跳过 into 需处理.
Run: python3 -B test_preflight_v75.py"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight  # noqa: E402

NEW_TOOLS = ('audit_no_social_features.py', 'audit_share_entries.py', 'audit_sound_settings_static.py', 'logic_check.py',
             'audit_package_estimate.py', 'audit_source_appid.py', 'audit_platform_kit_required.py', 'audit_ad_entry_reachability.py')


class PreflightV75(unittest.TestCase):
    def run_preflight(self, marker_status, extra=()):
        calls = {}

        def stub(name, args, logs):
            calls[name] = [str(x) for x in args]
            payload = {'failed': 0, 'checked': 1, 'blocking': 0, 'review': 0, 'runtime_strings': 1, 'known_risks': [],
                       'found': [], 'decision': {}, 'passed': True, 'errors': [], 'problems': [], 'findings': []}
            if name == 'audit_platform_markers.py':
                payload.update(status=marker_status, source_missing=[], native_missing=None,
                               share_calls_in_source={'navigateToMiniProgram': ['assets/DockIconSc.ts']}
                               if marker_status.startswith('share') else {})
            return 0, json.dumps(payload)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'game' / 'assets').mkdir(parents=True)
            out = root / 'out'
            argv = ['preflight.py', '--project', str(root / 'game'), '--board', 'remake', '--out', str(out), *extra]
            with patch.object(sys, 'argv', argv), patch.object(preflight, 'run', side_effect=stub), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = preflight.main()
            rows = {r['check']: r for r in json.loads((out / 'preflight.json').read_text())['results']}
        return code, rows, calls

    def test_normal_status_passes_and_new_rows_run(self):
        code, rows, calls = self.run_preflight('markers_present_requires_behavior_review')
        self.assertEqual(rows['广告接入标记']['status'], '通过')
        self.assertNotIn('--features', calls['audit_platform_markers.py'], 'growth markers are always checked')
        for tool in NEW_TOOLS:
            self.assertIn(tool, calls)
        self.assertIn('final', calls['audit_no_social_features.py'])
        for title in ('互推', '分享/排行榜', '分享换奖励', '声音设置', '逻辑检查', '包体估算', 'App ID', '平台包', '广告入口'):
            self.assertIn(title, rows)
        self.assertEqual(code, 0, rows)

    def test_abnormal_marker_status_is_not_pass(self):
        for status in ('share_feature_present_remove_it', 'required_markers_missing_requires_review'):
            code, rows, _ = self.run_preflight(status)
            self.assertEqual(rows['广告接入标记']['status'], '需处理', status)
            self.assertEqual(code, 1)
        _, rows, _ = self.run_preflight('share_feature_present_remove_it')
        self.assertEqual(rows['互推']['status'], '需处理')

    def test_final_stage_skip_is_not_pass(self):
        code, rows, calls = self.run_preflight('markers_present_requires_behavior_review', ('--stage', 'final'))
        self.assertEqual(rows['上传包结构']['status'], '需处理')
        self.assertIn('最终阶段不能跳过', rows['上传包结构']['detail'])
        self.assertIn('final', calls['logic_check.py'])
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
