#!/usr/bin/env python3
"""R4N3 (补查2 第 1 组 1d): host stalls remain untested and are diagnosed within Ego, separately from game failures.

Texts as the Codex sessions printed them (方块收割者、火箭三消 -10005; 合成进化恐龙 webContents null, CDP
Runtime.evaluate timeout, two "aborted before dispatch"). Game errors must not match.  python3 test_r4n3_env_stuck.py
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_env as B  # noqa: E402

STALLS = [
    'Computer Use error: request timed out (code -10005)',
    'Error -10005: The operation couldn’t be completed.',
    "TypeError: Cannot read properties of null (reading 'webContents')",
    'webContents is null',
    'CDP Runtime.evaluate timed out after 30000ms',
    'tool call aborted before dispatch',
]
GAME_ERRORS = [
    'Uncaught TypeError: Cannot read properties of null (reading \'getComponent\')',
    'ad_regression: case nocallback FAILED (reward paid after 15 s)',
    'Error 3121: load image failed',
    'value -100050 out of range',
]


class EnvStuck(unittest.TestCase):
    def test_host_stalls_remain_untested_and_stay_in_ego(self):
        for text in STALLS:
            self.assertIsNotNone(B.ego_stuck_reason(1, text, None), text)
            message = B.env_stuck(text) or ''
            self.assertIn('保留未测', message, text)
            self.assertIn('在 Ego 内排查', message, text)

    def test_game_errors_stand(self):
        for text in GAME_ERRORS:
            self.assertIsNone(B.ego_stuck_reason(1, text, None), text)
            self.assertIsNone(B.env_stuck(text), text)

    def test_success_is_never_stuck(self):
        self.assertIsNone(B.ego_stuck_reason(0, STALLS[0], None))


if __name__ == '__main__':
    unittest.main(verbosity=2)
