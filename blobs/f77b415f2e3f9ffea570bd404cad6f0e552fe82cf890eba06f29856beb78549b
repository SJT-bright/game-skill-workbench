#!/usr/bin/env python3
"""Offline check of the Ego route of chrome_touch.py (2026-10-27).

bin/ego-browser is a FAKE that implements only the API documented by `ego-browser skill` v2.1.0 on top of Playwright
Chromium, so the runner logic can be tested without Ego. Real Ego is calibrated with the same plans:
  python3 -m http.server 8765 --directory <this folder>/site &
  python3 ../scripts/chrome_touch.py --url http://127.0.0.1:8765/ --plan calibration-plan.json --out <new dir> --name "ego calibration"
Needs node with the playwright package (NODE_PATH) for the fake only."""
import json, os, shutil, subprocess, sys, tempfile, threading, unittest, functools, http.server
from pathlib import Path
HERE = Path(__file__).resolve().parent
TOUCH = HERE.parent / 'scripts' / 'chrome_touch.py'


class EgoRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE / 'site'))
        cls.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:%d/' % cls.httpd.server_address[1]
        cls.tmp = Path(tempfile.mkdtemp(prefix='ego-route-'))

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); shutil.rmtree(cls.tmp, True)

    def run_plan(self, plan, name, extra=()):
        out = self.tmp / ('out-' + name)
        log = self.tmp / ('log-' + name + '.json')
        env = dict(os.environ, PATH=str(HERE / 'bin') + os.pathsep + os.environ['PATH'], FAKE_EGO_LOG=str(log))
        if 'NODE_PATH' not in env:
            env['NODE_PATH'] = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
        p = self.tmp / (name + '.json'); p.write_text(json.dumps(plan) if isinstance(plan, dict) else plan.read_text())
        r = subprocess.run([sys.executable, str(TOUCH), '--url', self.url, '--plan', str(p), '--out', str(out), '--name', name, *extra],
                           capture_output=True, text=True, env=env, timeout=170)
        report = json.loads((out / 'report.json').read_text()) if (out / 'report.json').is_file() else None
        return r, report, json.loads(log.read_text()) if log.is_file() else None

    def test_calibration_plan_touch_and_phone_mode(self):
        r, rep, log = self.run_plan(HERE / 'calibration-plan.json', 'calib')
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual((rep['browser_route'], rep['input_transport']), ('ego_taskspace', 'ego_page_cdp'))
        last = rep['steps'][-1]['observed']
        self.assertEqual((last['dpr'], last['maxTouchPoints']), (3, 5))
        self.assertEqual(last['bodyText'].split()[:2], ['2', '2'])          # tap + drag reached the page
        self.assertTrue(any(e['type'] == 'touchmove' and e['trusted'] for e in last['events']))
        self.assertTrue(rep['space_finished']); self.assertEqual(log['finished'][0]['keep'], [])

    def test_timing_plan_records_requests(self):
        r, rep, _ = self.run_plan(HERE / 'timing-plan.json', 'timing')
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertIn('home_usable', rep['marks'])
        self.assertTrue(any(q['url'].endswith('big.png') and q['bytes'] > 0 for q in rep['requests']))

    def test_failure_still_finishes_own_space(self):
        r, rep, log = self.run_plan({'actions': [{'type': 'assert_text', 'selector': '#count', 'equals': '99'}]}, 'fail')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(rep['status'], 'failed'); self.assertTrue(rep['space_finished'])

    def test_same_name_runs_get_different_spaces(self):
        a = self.run_plan(HERE / 'calibration-plan.json', 'same')[1]['space_name']
        b = self.run_plan(HERE / 'calibration-plan.json', 'same2')[1]['space_name']
        self.assertNotEqual(a, b)

    def test_record_writes_timed_frames(self):
        r, rep, _ = self.run_plan({'device': 'iphone_se', 'actions': [{'type': 'tap', 'selector': '#c'}, {'type': 'wait', 'ms': 1500}]}, 'rec', ('--record',))
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        frames = sorted((self.tmp / 'out-rec' / 'frames').glob('*ms.png'))
        self.assertGreater(len(frames), 2); self.assertEqual(rep['recording']['method'], 'sequential_screenshots')

    def test_hang_urls_refused_with_alternative(self):
        r, _, _ = self.run_plan({'hang_urls': ['*big*'], 'actions': []}, 'hang')
        self.assertNotEqual(r.returncode, 0); self.assertIn('init_js', r.stderr + r.stdout)

    def test_cdp_url_refused(self):
        r, _, _ = self.run_plan(HERE / 'calibration-plan.json', 'cdp', ('--cdp-url', 'http://127.0.0.1:9222'))
        self.assertNotEqual(r.returncode, 0); self.assertIn('--cdp-url was removed', r.stderr + r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
