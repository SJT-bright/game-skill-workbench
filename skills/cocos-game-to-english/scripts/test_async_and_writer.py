#!/usr/bin/env python3
"""Self-tests for audit_async_contracts.py and test_writer_refusal.py (synthetic fixtures, never a game pass).

Each check is calibrated: a known-bad fixture must fail, the fixed fixture must pass, a normal case must pass.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent

V8_BAD = """
export class Bridge {
  public getShortcutMissionReward(): Promise<boolean> {
    return new Promise((resolve) => {
      const r = TTMinis.game.getShortcutMissionReward({
        success: (res: any) => resolve(res && res.canReceiveReward === true),
        fail: () => resolve(false),
      });
      if (r) r.catch(() => resolve(false));
    });
  }
}
"""
FIXED = """
export class Bridge {
  public getShortcutMissionReward(): Promise<boolean> {
    return new Promise((resolve) => {
      let done = false;
      const settle = (res: any) => { if (done) return; done = true; resolve(!!res && res.canReceiveReward === true); };
      const r = TTMinis.game.getShortcutMissionReward({ success: settle, fail: () => settle(null) });
      if (r && typeof r.then === 'function') r.then(settle, () => settle(null));
    });
  }
}
"""
EXECUTOR_ONLY = "const q = () => new Promise(resolve => TTMinis.game.getEntranceMissionReward({ success: resolve }));\n"
PROMISE_ONLY = "async function q() { return await TTMinis.game.getEntranceMissionReward(); }\n"
DECLARED = ("function q() {\n  // async-contract: SdkQuery.run normalises callback and Promise into one settle\n"
            "  return SdkQuery.run(() => TTMinis.game.getEntranceMissionReward({ success: settle }));\n}\n")
NO_API = "const x = 1; // getShortcutMissionReward( in a comment only\nconst s = 'getEntranceMissionReward(';\n"
SHOW_RESOLVE_CATCH = """
function loadRewardedAd(tt) {
  if (!tt.createRewardedVideoAd) return;
  const ad = tt.createRewardedVideoAd({ adUnitId: 'test' });
  Promise.resolve(ad.show()).catch((error) => finish('show_failed', error));
}
"""
SHOW_RESOLVE_UNHANDLED = """
function loadRewardedAd(tt) {
  if (!tt.createRewardedVideoAd) return;
  const ad = tt.createRewardedVideoAd({ adUnitId: 'test' });
  Promise.resolve(ad.show());
}
"""


def scan(code, native=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'game'
        (root / 'assets/scripts').mkdir(parents=True)
        (root / 'assets/scripts/a.ts').write_text(code)
        out = Path(tmp) / 'r.json'
        cmd = [sys.executable, '-B', str(HERE / 'audit_async_contracts.py'), '--project', str(root), '--out', str(out)]
        if native:
            (Path(tmp) / 'native').mkdir()
            (Path(tmp) / 'native/game.js').write_text(native)
            cmd += ['--native', str(Path(tmp) / 'native')]
        code = subprocess.run(cmd, capture_output=True, text=True).returncode
        return code, json.loads(out.read_text())


class AsyncContractTests(unittest.TestCase):
    def test_v8_pattern_blocks(self):
        code, r = scan(V8_BAD)
        self.assertEqual(code, 1)
        self.assertEqual(r['failed'], 1)
        self.assertEqual(r['checks'][0]['promise'], 'catch_only')

    def test_fixed_pattern_passes(self):
        code, r = scan(FIXED)
        self.assertEqual(code, 0)
        self.assertEqual([c['status'] for c in r['checks']], ['ok'])
        self.assertEqual(r['reward_apis'], ['getShortcutMissionReward'])

    def test_promise_executor_with_callback_only_blocks(self):
        self.assertEqual(scan(EXECUTOR_ONLY)[0], 1)

    def test_promise_only_blocks(self):
        code, r = scan(PROMISE_ONLY)
        self.assertEqual(code, 1)
        self.assertIn('success', r['checks'][0]['reason'])

    def test_declared_wrapper_is_review_not_blocking(self):
        code, r = scan(DECLARED)
        self.assertEqual(code, 0)
        self.assertEqual(r['checks'][0]['status'], 'review')
        self.assertIn('SdkQuery.run', r['checks'][0]['declared'])

    def test_comments_and_strings_are_not_calls(self):
        code, r = scan(NO_API)
        self.assertEqual((code, r['checked'], r['reward_apis']), (0, 0, []))

    def test_api_only_in_native_is_still_discovered(self):
        code, r = scan(NO_API, native='n.getEntranceMissionReward({success:a})')
        self.assertEqual(r['reward_apis'], ['getEntranceMissionReward'])

    def test_rewarded_show_wrapped_with_promise_resolve_and_catch_is_handled(self):
        code, r = scan(SHOW_RESOLVE_CATCH)
        self.assertEqual(code, 0)
        shows = [row for row in r['checks'] if row['api'] == 'RewardedVideoAd.show']
        self.assertEqual(shows, [])

    def test_rewarded_show_without_handler_inside_promise_resolve_is_reviewed(self):
        code, r = scan(SHOW_RESOLVE_UNHANDLED)
        self.assertEqual(code, 0)
        shows = [row for row in r['checks'] if row['api'] == 'RewardedVideoAd.show']
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]['status'], 'review')


GOOD_WRITER = r'''
import json, sys, zipfile
from pathlib import Path
review, out = Path(sys.argv[1]), Path(sys.argv[2])
if not review.is_file():
    sys.exit(2)
d = json.loads(review.read_text())
if d['binding']['source_sha256'] != 'a' * 64 or any(r.get('status') != 'pass' for r in d['checks'].values()):
    sys.exit(2)
out.mkdir(parents=True, exist_ok=True)
n = len(list(out.glob('*.zip')))
with zipfile.ZipFile(out / ('game-%d.zip' % n), 'w') as z:
    z.writestr('game.js', '//')
'''
LAZY_WRITER = r'''
import sys, zipfile
from pathlib import Path
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
n = len(list(out.glob('*.zip')))
with zipfile.ZipFile(out / ('game-%d.zip' % n), 'w') as z:
    z.writestr('game.js', '//')
'''


def refusal(writer_source, with_storage=False):
    tmp = Path(tempfile.mkdtemp())
    review = tmp / 'review.json'
    review.write_text(json.dumps({'binding': {'source_sha256': 'a' * 64, 'build_tag': 't'},
                                  'checks': {'AD-01': {'status': 'pass'}, 'UI-01': {'status': 'pass'}}}))
    if with_storage:
        doc = json.loads(review.read_text())
        doc['checks']['STORAGE-01'] = {'status': 'pass', 'auto_reports': [{'path': 'native-storage.json'}]}
        review.write_text(json.dumps(doc))
    writer = tmp / 'writer.py'
    writer.write_text(writer_source)
    before = review.read_bytes()
    out = tmp / 'refusal.json'
    code = subprocess.run([sys.executable, '-B', str(HERE / 'test_writer_refusal.py'), '--review', str(review),
                           '--zip-dir', str(tmp / 'zips'), '--out', str(out), '--',
                           sys.executable, str(writer), str(review), str(tmp / 'zips')],
                          capture_output=True, text=True).returncode
    return code, json.loads(out.read_text()), review.read_bytes() == before, tmp


class WriterRefusalTests(unittest.TestCase):
    def test_writer_that_calls_the_gate_passes(self):
        code, r, restored, tmp = refusal(GOOD_WRITER)
        self.addCleanup(__import__('shutil').rmtree, tmp, True)
        self.assertEqual(code, 0)
        self.assertTrue(r['passed'] and restored)
        self.assertEqual(r['binding']['source_sha256'], 'a' * 64)
        self.assertEqual([c['id'] for c in r['checks']], ['missing_review', 'failed_check', 'stale_binding', 'normal'])

    def test_writer_refuses_missing_native_storage_evidence(self):
        strict = GOOD_WRITER.replace("out.mkdir(parents=True, exist_ok=True)",
            "if not d['checks']['STORAGE-01'].get('auto_reports'): sys.exit(2)\nout.mkdir(parents=True, exist_ok=True)")
        code, report, restored, tmp = refusal(strict, with_storage=True)
        self.addCleanup(__import__('shutil').rmtree, tmp, True)
        self.assertEqual(code, 0)
        self.assertTrue(restored)
        self.assertEqual([case['id'] for case in report['checks']],
                         ['missing_review', 'failed_check', 'stale_binding', 'missing_storage', 'normal'])
        self.assertTrue(all(case['passed'] for case in report['checks']))

    def test_writer_that_ignores_the_gate_fails_and_leaks_are_quarantined(self):
        code, r, restored, tmp = refusal(LAZY_WRITER)
        self.addCleanup(__import__('shutil').rmtree, tmp, True)
        self.assertEqual(code, 1)
        self.assertFalse(r['passed'])
        self.assertTrue(restored)
        self.assertEqual([c['passed'] for c in r['checks']], [False, False, False, True])
        self.assertEqual(len(list((tmp / 'zips/_refusal_test_leaks').rglob('*.zip'))), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
