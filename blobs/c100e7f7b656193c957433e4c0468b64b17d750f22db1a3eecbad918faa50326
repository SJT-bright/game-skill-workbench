#!/usr/bin/env python3
"""v7.8 (总表 B21 / B30 F): serve_preview.py --keep runs the trial-link smoke before it prints the link.

The smoke itself (runtime_regression.trial_smoke, suite trial_link) is proven in a real browser on real trial pages
(briefs/out/W87/RESULT.md); here the decision around it: a failed smoke keeps the link from the user, a smoke that
could not run prints why and still gives the link, an export without rewarded ads skips it, and main() asks before it
prints. Run: python3 -B test_serve_preview_smoke.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import serve_preview  # noqa: E402


class Refused(Exception):
    pass


def fake(result=None, error=None, summary=None):
    calls = []

    def smoke(url, adapter):
        calls.append((url, adapter))
        if error:
            e = Refused(error)
            if summary is not None:
                e.summary = summary
            raise e
        return result

    smoke.refused = Refused
    smoke.calls = calls
    return smoke


class TrialSmokeGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.web = Path(self.temp.name)
        (self.web / 'index.html').write_text('<html></html>')
        (self.web / 'main.js').write_text('tt.createRewardedVideoAd({adUnitId: "x"})')

    def tearDown(self):
        self.temp.cleanup()

    def test_failed_smoke_blocks_the_link(self):
        s = fake(error='trial smoke failed: trial_link/ad_window_visible: ad_window_hidden', summary={'passed': False})
        level, message = serve_preview.trial_smoke_gate('http://127.0.0.1:9/', self.web, None, smoke=s)
        self.assertEqual(level, 'block')
        self.assertIn('不给试玩链接', message)
        self.assertEqual(s.calls, [('http://127.0.0.1:9/', None)])

    def test_could_not_run_warns_and_gives_the_link(self):
        level, message = serve_preview.trial_smoke_gate('http://127.0.0.1:9/', self.web, None,
                                                        smoke=fake(error='runtime regression needs the Ego browser'))
        self.assertEqual(level, 'warn')
        self.assertIn('没跑', message)
        level, message = serve_preview.trial_smoke_gate('http://127.0.0.1:9/', self.web, None,
                                                        smoke=fake({'passed': True, 'not_run': 'no ad entry known'}))
        self.assertEqual(level, 'warn')
        self.assertIn('no ad entry known', message)

    def test_pass_and_no_ads(self):
        self.assertEqual(serve_preview.trial_smoke_gate('http://127.0.0.1:9/', self.web, 'a.json', smoke=fake({'passed': True}))[0], 'pass')
        (self.web / 'main.js').write_text('cc.log(1)')
        s = fake({'passed': True})
        level, message = serve_preview.trial_smoke_gate('http://127.0.0.1:9/', self.web, None, smoke=s)
        self.assertEqual((level, s.calls), ('pass', []))
        self.assertIn('不涉及看广告', message)

    def test_main_runs_it_before_printing_the_link_only_for_keep(self):
        text = (HERE / 'serve_preview.py').read_text(encoding='utf-8')
        main = text[text.index('def main('):]
        self.assertLess(main.index('trial_smoke_gate(url, directory, args.adapter)'), main.index("print(f'{entry_kind}"))
        self.assertIn('if args.keep:\n        # v7.8 (总表 B21 / B30 F)', main)
        self.assertTrue((serve_preview.CHECK_SCRIPTS / 'runtime_regression.py').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=1)
