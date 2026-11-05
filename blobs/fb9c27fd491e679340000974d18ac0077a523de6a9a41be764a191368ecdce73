#!/usr/bin/env python3
"""生成时预防 R4J2: delegate.py gets the same bounded retry and hand-off as grok-image-review/review.py (R4I2, #39).
delegate.py with a fake grok on PATH (no model, no network, a few seconds):
- SKILL.md is the 「已停用」 page -> no Grok call, fallback.json, exit 3, no checked-result.json;
- a failed process -> one bounded retry, raw/stderr of every attempt kept, then fallback.json, exit 3;
- a reply that does not verify -> no paid retry, fallback.json, exit 3; success on the retry -> checked-result.json, exit 0.
Old delegate.py: calls Grok on the disabled page, raises a traceback (exit 1) with no hand-off -> fails.
Run: python3 -B test_delegate_fallback.py   (DELEGATE_PY=<other delegate.py> runs it against another copy)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DELEGATE = Path(os.environ.get('DELEGATE_PY') or Path(__file__).resolve().parent / 'delegate.py')
GOOD = {'items': [{'id': 'r1', 'fields': {'名称': {'value': '苹果', 'quote': '名称：苹果'}}}]}
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
home = os.environ['FAKE_GROK_HOME']
if args[:1] == ['--help']:
    print('--tools --prompt-file --verbatim --disable-web-search --no-subagents --no-plan --permission-mode '
          '--session-id --max-turns --output-format --cwd --reasoning-effort'); sys.exit(0)
calls = os.path.join(home, 'calls')
n = (int(open(calls).read()) if os.path.exists(calls) else 0) + 1
open(calls, 'w').write(str(n))
mode = os.environ['FAKE_GROK_MODE']
if mode == 'fail' or (mode == 'flaky' and n == 1):
    sys.stderr.write('boom %d\n' % n); sys.exit(1)
print(json.dumps({'text': os.environ.get('FAKE_REPLY', 'not json')}))
'''


class DelegateFallback(unittest.TestCase):
    def run_delegate(self, mode, *, disabled=False, reply=None):
        root = Path(tempfile.mkdtemp(prefix='grok_delegate_'))
        self.addCleanup(shutil.rmtree, root, True)
        skill = root / 'grok-delegate'
        (skill / 'scripts').mkdir(parents=True)
        shutil.copy(DELEGATE, skill / 'scripts' / 'delegate.py')
        (skill / 'SKILL.md').write_text('---\nname: grok-delegate\ndescription: %s\n---\n'
                                        % ('已停用。字段由主 Agent 自己搬取。' if disabled else '原文搬取'), encoding='utf-8')
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'grok').write_text(FAKE)
        (bin_dir / 'grok').chmod(0o755)
        src = root / 'notes.txt'
        src.write_text('名称：苹果\n价格：3元\n', encoding='utf-8')
        contract = root / 'contract.json'
        contract.write_text(json.dumps({'fields': ['名称'], 'items': [
            {'id': 'r1', 'source': str(src), 'start_line': 1, 'end_line': 1}]}, ensure_ascii=False), encoding='utf-8')
        prompt = root / 'ask.txt'
        prompt.write_text('搬取名称', encoding='utf-8')
        out = root / 'receipt'
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ.get('PATH', ''), FAKE_GROK_HOME=str(root),
                   FAKE_GROK_MODE=mode, FAKE_REPLY=json.dumps(reply if reply is not None else GOOD, ensure_ascii=False))
        p = subprocess.run([sys.executable, '-B', str(skill / 'scripts' / 'delegate.py'), '--prompt-file', str(prompt),
                            '--contract-file', str(contract), '--task-kind', 'explicit-field-copy',
                            '--out-dir', str(out)], capture_output=True, text=True, env=env, timeout=60,
                           stdin=subprocess.DEVNULL)
        calls = root / 'calls'
        return p, out, int(calls.read_text()) if calls.exists() else 0

    def assert_fallback(self, p, out):
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        hand = json.loads((out / 'fallback.json').read_text(encoding='utf-8'))
        self.assertEqual(hand['next'], 'main_agent_copies_fields')
        self.assertFalse((out / 'checked-result.json').exists())
        return hand

    def test_disabled_page_no_call(self):
        p, out, calls = self.run_delegate('ok', disabled=True)
        self.assertEqual(calls, 0)
        self.assertIn('disabled', self.assert_fallback(p, out)['reason'])

    def test_failed_process_one_retry_then_hand_off(self):
        p, out, calls = self.run_delegate('fail')
        self.assertEqual(calls, 2)
        hand = self.assert_fallback(p, out)
        self.assertEqual(len(hand['attempts']), 2)
        for n in (1, 2):
            self.assertIn('boom %d' % n, (out / ('stderr.%d.txt' % n)).read_text())
            self.assertTrue((out / ('raw.%d.json' % n)).exists())

    def test_retry_succeeds(self):
        p, out, calls = self.run_delegate('flaky')
        self.assertEqual((p.returncode, calls), (0, 2), p.stderr)
        self.assertTrue((out / 'checked-result.json').exists())
        self.assertFalse((out / 'fallback.json').exists())

    def test_bad_reply_not_paid_again(self):
        p, out, calls = self.run_delegate('ok', reply={'items': [{'id': 'r1', 'fields': {'名称': {'value': '香蕉', 'quote': '名称：香蕉'}}}]})
        self.assertEqual(calls, 1)
        self.assertIn('grok_reply_rejected', self.assert_fallback(p, out)['reason'])
        self.assertTrue((out / 'raw.json').exists())

    def test_good_reply_passes(self):
        p, out, calls = self.run_delegate('ok')
        self.assertEqual((p.returncode, calls), (0, 1), p.stderr)
        checked = json.loads((out / 'checked-result.json').read_text(encoding='utf-8'))
        self.assertEqual(checked['items'][0]['fields']['名称']['value'], '苹果')


if __name__ == '__main__':
    unittest.main(verbosity=2)
