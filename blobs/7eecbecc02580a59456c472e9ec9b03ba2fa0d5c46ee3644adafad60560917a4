#!/usr/bin/env python3
"""R4O4 (R4N3 没做完的): dump_ui waits and dumps again when ui_dump.js answers {error: 引擎还没起来…, retry: true}.

No browser: chrome_touch.dump_with_retry gets a fake dump function and a fake sleep.
- retry twice, then a dump -> the dump, 3 dumps, 2 waits of 1 s;
- retry every time -> ValueError after 3 dumps with the reason and "tried 3 times";
- an error without retry (a real ui_dump failure) -> ValueError at once, 1 dump, no wait;
- the Ego runner (ego_touch_runner.js) has the same loop.
Old code: chrome_touch has no dump_with_retry -> every test fails.
Run: python3 -B chrome-mobile-testing/tests/test_r4o4_dump_retry.py
"""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import chrome_touch as ct  # noqa: E402

NOT_UP = {'error': '引擎还没起来：页面里还没有 cc', 'retry': True}


class DumpRetry(unittest.TestCase):
    def fake(self, answers):
        self.calls, self.waits = 0, []
        def grab():
            a = answers[min(self.calls, len(answers) - 1)]
            self.calls += 1
            return a
        return grab

    def test_retry_then_dump(self):
        grab = self.fake([NOT_UP, NOT_UP, {'nodes': [1, 2]}])
        dump, tried = ct.dump_with_retry(grab, 'home', sleep=self.waits.append)
        self.assertEqual(dump, {'nodes': [1, 2]})
        self.assertEqual((tried, self.calls, self.waits), (3, 3, [1.0, 1.0]))

    def test_never_up_says_why(self):
        grab = self.fake([NOT_UP])
        with self.assertRaises(ValueError) as e:
            ct.dump_with_retry(grab, 'home', sleep=self.waits.append)
        self.assertIn('引擎还没起来', str(e.exception))
        self.assertIn('tried 3 times', str(e.exception))
        self.assertEqual((self.calls, len(self.waits)), (3, 2))

    def test_real_error_fails_at_once(self):
        grab = self.fake([{'error': 'maxNodes must be a number'}])
        with self.assertRaises(ValueError) as e:
            ct.dump_with_retry(grab, 'home', sleep=self.waits.append)
        self.assertIn('maxNodes', str(e.exception))
        self.assertEqual((self.calls, self.waits), (1, []))

    def test_no_result(self):
        grab = self.fake([None])
        with self.assertRaises(ValueError) as e:
            ct.dump_with_retry(grab, 'home', sleep=self.waits.append)
        self.assertIn('no result', str(e.exception))
        self.assertEqual(self.calls, 1)

    def test_ego_runner_uses_dump_retry(self):
        self.assertIn('ego_touch_runner.js', (SCRIPTS / 'chrome_touch.py').read_text(encoding='utf-8'))
        js = (SCRIPTS / 'ego_touch_runner.js').read_text(encoding='utf-8')
        self.assertRegex(js, r'dump\.error && dump\.retry\) \|\| tries >= 3\) break;')


if __name__ == '__main__':
    unittest.main()
