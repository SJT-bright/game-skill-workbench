#!/usr/bin/env python3
"""生成时预防 #39 (问题普查 20261104 helper_grok_failed 14/14 receipts, 11 games: 10 CLI runs past 180 s, 4 exit 1).
review.py with a fake grok on PATH (no model, no network, a few seconds):
- SKILL.md is the 「已停用」 page -> no Grok call, fallback.json, exit 3, no result.json;
- a failed or timed-out process -> one bounded retry, raw/stderr of every attempt kept, then fallback.json, exit 3;
- a reply that does not validate -> no paid retry, fallback.json, exit 3; success on the retry -> result.json, exit 0.
Old review.py: calls Grok on the disabled page, raises a traceback (exit 1) with no hand-off -> fails.
Run: python3 -B test_review_fallback.py   (REVIEW_PY=<other review.py> runs it against another copy)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REVIEW = Path(os.environ.get('REVIEW_PY') or Path(__file__).resolve().parent / 'review.py')
GOOD = {'status': 'pass', 'observations': 'PLAY', 'issues': [], 'uncertainties': []}
FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
home = os.environ['FAKE_GROK_HOME']
if args[:1] == ['--help']:
    print('--prompt-file --verbatim --no-subagents --no-plan --tools --disable-web-search --permission-mode '
          '--max-turns --output-format --session-id --reasoning-effort --cwd'); sys.exit(0)
if args[:1] == ['export']:
    open(args[2], 'w').write('## Assistant\n\n' + os.environ.get('FAKE_REPLY', '{}')); sys.exit(0)
calls = os.path.join(home, 'calls')
n = (int(open(calls).read()) if os.path.exists(calls) else 0) + 1
open(calls, 'w').write(str(n))
mode = os.environ['FAKE_GROK_MODE']
if mode == 'slow':
    time.sleep(5)
if mode == 'fail' or (mode == 'flaky' and n == 1):
    sys.stderr.write('boom %d\n' % n); sys.exit(1)
print(json.dumps({'text': os.environ.get('FAKE_REPLY', 'not json')}))
'''


class ReviewFallback(unittest.TestCase):
    def run_review(self, mode, *, disabled=False, reply=None, extra=()):
        root = Path(tempfile.mkdtemp(prefix='grok_review_'))
        self.addCleanup(shutil.rmtree, root, True)
        skill = root / 'grok-image-review'
        (skill / 'scripts').mkdir(parents=True)
        shutil.copy(REVIEW, skill / 'scripts' / 'review.py')
        (skill / 'SKILL.md').write_text('---\nname: grok-image-review\ndescription: %s\n---\n'
                                        % ('已停用。所有图片由 Codex 自己读取。' if disabled else '清晰文字转录'), encoding='utf-8')
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'grok').write_text(FAKE)
        (bin_dir / 'grok').chmod(0o755)
        image = root / 'shot.png'
        image.write_bytes(b'\x89PNG fake')
        prompt = root / 'ask.txt'
        prompt.write_text('读按钮文字', encoding='utf-8')
        out = root / 'receipt'
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ.get('PATH', ''), FAKE_GROK_HOME=str(root),
                   FAKE_GROK_MODE=mode, FAKE_REPLY=json.dumps(reply) if reply is not None else 'not json')
        done = subprocess.run([sys.executable, '-B', str(skill / 'scripts' / 'review.py'), '--image', str(image),
                               '--prompt-file', str(prompt), '--out-dir', str(out), *extra],
                              capture_output=True, text=True, env=env, timeout=60)
        calls = int((root / 'calls').read_text()) if (root / 'calls').exists() else 0
        return done, out, calls

    def assert_fallback(self, done, out):
        self.assertEqual(done.returncode, 3, done.stderr[-400:])
        hand_off = json.loads((out / 'fallback.json').read_text(encoding='utf-8'))
        self.assertEqual(hand_off['next'], 'main_agent_reads_image')
        self.assertFalse((out / 'result.json').exists(), 'a failed Grok run must not leave a result')
        self.assertEqual(json.loads((out / 'receipt.json').read_text(encoding='utf-8'))['status'], 'fallback_required')
        return hand_off

    def test_disabled_page_never_calls_grok(self):
        done, out, calls = self.run_review('fail', disabled=True)
        self.assertEqual(calls, 0, 'SKILL.md says 已停用: Grok must not be called')
        self.assertIn('disabled', self.assert_fallback(done, out)['reason'])

    def test_failed_process_bounded_retry_keeps_raw(self):
        done, out, calls = self.run_review('fail')
        hand_off = self.assert_fallback(done, out)
        self.assertEqual(calls, 2)
        self.assertEqual(len(hand_off['attempts']), 2)
        for n in (1, 2):
            self.assertIn('boom %d' % n, (out / ('stderr.%d.txt' % n)).read_text())
            self.assertTrue((out / ('raw.%d.json' % n)).exists())

    def test_timeout_then_fallback(self):
        done, out, calls = self.run_review('slow', extra=('--timeout', '1'))
        hand_off = self.assert_fallback(done, out)
        self.assertEqual([a.get('timeout') for a in hand_off['attempts']], [1, 1])

    def test_bad_reply_not_paid_twice(self):
        done, out, calls = self.run_review('bad')
        self.assert_fallback(done, out)
        self.assertEqual(calls, 1)

    def test_success_on_retry(self):
        done, out, calls = self.run_review('flaky', reply=GOOD)
        self.assertEqual(done.returncode, 0, done.stderr[-400:])
        self.assertEqual(calls, 2)
        self.assertEqual(json.loads((out / 'result.json').read_text(encoding='utf-8'))['status'], 'pass')
        self.assertFalse((out / 'fallback.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=1)
