#!/usr/bin/env python3
"""Exercise chrome_touch.py against a loopback fixture in real Ego Lite."""
import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
TOUCH = HERE.parent / 'scripts' / 'chrome_touch.py'
SPACE_LIST_PREFIX = 'EGO_ROUTE_SPACE_IDS='


class EgoRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ego = shutil.which('ego-browser')
        if not cls.ego:
            raise RuntimeError('Ego Lite is required for the browser regression')
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE / 'site'))
        cls.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.close_fixture)
        cls.url = 'http://127.0.0.1:%d/' % cls.httpd.server_address[1]
        tmp = tempfile.TemporaryDirectory(prefix='ego-route-')
        cls.addClassCleanup(tmp.cleanup)
        cls.tmp = Path(tmp.name)
        cls.owned_spaces = set()

    @classmethod
    def close_fixture(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    @classmethod
    def tearDownClass(cls):
        if not cls.owned_spaces:
            return
        result = subprocess.run(
            [cls.ego, 'nodejs', '-e',
             f'console.log({json.dumps(SPACE_LIST_PREFIX)} + JSON.stringify((await listTaskSpaces()).map(s => s.id)))'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20, check=True)
        rows = [line.removeprefix(SPACE_LIST_PREFIX) for line in result.stdout.splitlines()
                if line.startswith(SPACE_LIST_PREFIX)]
        if len(rows) != 1:
            raise AssertionError('Ego Lite did not return a unique TaskSpace listing')
        space_ids = json.loads(rows[0])
        if not isinstance(space_ids, list) or any(type(value) is not int for value in space_ids):
            raise AssertionError(f'Ego Lite returned invalid TaskSpace IDs: {space_ids!r}')
        remaining = cls.owned_spaces.intersection(space_ids)
        if remaining:
            raise AssertionError(f'Ego test spaces still present: {sorted(remaining)}')
        print(f'Ego Lite verified closure of {len(cls.owned_spaces)} test spaces', flush=True)

    def run_plan(self, plan, name, extra=()):
        run_dir = Path(tempfile.mkdtemp(prefix='case-', dir=self.tmp))
        out = run_dir / 'out'
        p = run_dir / 'plan.json'
        p.write_text(json.dumps(plan) if isinstance(plan, dict) else plan.read_text())
        r = subprocess.run([sys.executable, str(TOUCH), '--url', self.url, '--plan', str(p), '--out', str(out), '--name', name, *extra],
                           capture_output=True, text=True, timeout=170)
        report = json.loads((out / 'report.json').read_text()) if (out / 'report.json').is_file() else None
        if report and report.get('space_id') is not None:
            self.assertIs(type(report['space_id']), int)
            self.assertEqual(report['space_ownership'], 'agent')
            self.owned_spaces.add(report['space_id'])
            self.assertTrue(report['space_finished'], report.get('cleanup_error'))
            self.assertFalse(report['cleanup_pending'])
        return r, report, out

    def test_calibration_plan_touch_and_phone_mode(self):
        r, rep, _ = self.run_plan(HERE / 'calibration-plan.json', 'calib')
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual((rep['browser_route'], rep['input_transport']), ('ego_taskspace', 'ego_page_cdp'))
        last = rep['steps'][-1]['observed']
        self.assertEqual((last['dpr'], last['maxTouchPoints']), (3, 5))
        self.assertEqual(last['bodyText'].split()[:2], ['2', '2'])          # tap + drag reached the page
        self.assertTrue(any(e['type'] == 'touchmove' and e['trusted'] for e in last['events']))
        self.assertTrue(rep['space_finished'])

    def test_timing_plan_records_requests(self):
        r, rep, _ = self.run_plan(HERE / 'timing-plan.json', 'timing')
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertIn('home_usable', rep['marks'])
        image_bytes = [q['bytes'] for q in rep['requests']
                       if q['url'] == self.url + 'big.png' and q['status'] == 200 and q['bytes'] > 0]
        self.assertTrue(image_bytes)
        self.assertTrue(rep['timing_valid'])
        self.assertGreaterEqual(rep['frame_rate']['lowest_fps_in_window'], rep['frame_rate']['min_fps'])
        print(f"Ego Lite timing: {rep['marks']['home_usable']} ms, "
              f"{rep['frame_rate']['lowest_fps_in_window']} fps minimum, image {image_bytes[0]} bytes", flush=True)

    def test_failure_still_finishes_own_space(self):
        r, rep, _ = self.run_plan({'actions': [{'type': 'assert_text', 'selector': '#count', 'equals': '99'}]}, 'fail')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(rep['status'], 'failed'); self.assertTrue(rep['space_finished'])

    def test_same_name_runs_get_different_spaces(self):
        spaces = []
        for _ in range(2):
            r, rep, _out = self.run_plan({'actions': [{'type': 'snapshot'}]}, 'same')
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            spaces.append((rep['space_id'], rep['space_name']))
        self.assertNotEqual(spaces[0][0], spaces[1][0])
        self.assertNotEqual(spaces[0][1], spaces[1][1])

    def test_record_writes_timed_frames(self):
        r, rep, out = self.run_plan({'device': 'iphone_se', 'actions': [{'type': 'tap', 'selector': '#c'}, {'type': 'wait', 'ms': 1500}]}, 'rec', ('--record',))
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        frames = [path for path in (out / 'frames').glob('*ms.*')
                  if path.suffix in {'.png', '.jpg'} and path.stat().st_size > 0]
        self.assertGreater(len(frames), 2); self.assertEqual(rep['recording']['method'], 'sequential_screenshots')

    def test_hang_urls_refused_with_alternative(self):
        r, _, _ = self.run_plan({'hang_urls': ['*big*'], 'actions': []}, 'hang')
        self.assertNotEqual(r.returncode, 0); self.assertIn('init_js', r.stderr + r.stdout)

    def test_legacy_chrome_flag_refused_before_capture(self):
        r, report, out = self.run_plan(HERE / 'calibration-plan.json', 'chrome-refused', ('--user-approved-chrome',))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--user-approved-chrome 已停用', r.stderr + r.stdout)
        self.assertIsNone(report)
        self.assertFalse(out.exists())

    def test_cdp_url_refused(self):
        r, _, _ = self.run_plan(HERE / 'calibration-plan.json', 'cdp', ('--cdp-url', 'http://127.0.0.1:9222'))
        self.assertNotEqual(r.returncode, 0); self.assertIn('--cdp-url was removed', r.stderr + r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
