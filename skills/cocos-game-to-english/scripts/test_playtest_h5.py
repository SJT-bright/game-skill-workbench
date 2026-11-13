"""Exercise the H5 command against the real phone-shell handler and bound fixture receipts."""
from copy import deepcopy
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import build_playtest_h5 as h5

sys.path.insert(0, str(h5.CORE_TOOLS))
import browser_slots
from check_known_issues import tree_sha
from serve_preview import Handler


class Playtest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.web = self.root / 'web'
        self.web.mkdir()
        self.index = self.web / 'index.html'
        self.index.write_text('<html><head></head><body><script src="game.js"></script></body></html>')
        (self.web / 'game.js').write_text('window.booted = true;')
        self.web_sha = tree_sha(self.web)
        self.slots = self.root / 'locks' / 'browser-slots'
        mock_slots = patch.object(browser_slots, 'SLOTS', self.slots)
        mock_slots.start()
        self.addCleanup(mock_slots.stop)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(
            Handler, directory=str(self.web), phone_size=(390, 844), preview_token='fixture',
            ad_simulator=True, touch_bridge=True))
        self.addCleanup(self.server.server_close)
        Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.url = f'http://127.0.0.1:{self.server.server_port}/'
        # Sandbox ps is unavailable. Limit this process-identity probe fixture
        # to the exact PID that owns this real threaded HTTP server. Other PIDs
        # still use the production probe; no termination operation is patched.
        self.owned_pid = os.getpid()
        self.owned_identity = hashlib.sha256((str(self.root.resolve())+':'+str(self.owned_pid)).encode()).hexdigest()
        original_probe = browser_slots.process_identity
        own_probe = lambda pid: self.owned_identity if pid == self.owned_pid and browser_slots.alive(pid) else original_probe(pid)
        identity_patch = patch.object(browser_slots, 'process_identity', side_effect=own_probe)
        identity_patch.start(); self.addCleanup(identity_patch.stop)
        self.slot = browser_slots.register('preview', pid=os.getpid(), url=self.url, directory=self.web, keep=True)
        self.plan = {'schema': h5.SCHEMA, 'game': 'H5 fixture <>&', 'version': 'fixture-r2',
                     'mode': 'trial', 'preview_url': self.url, 'web_tree_sha256': self.web_sha,
                     'require_ad_simulator': True,
                     'inventory': [{'id': 'play', 'page': '首页', 'state': '已加载',
                                    'control': 'Play', 'evidence': 'fixture index.html'}],
                     'steps': [{'id': 'home', 'page': '首页', 'enter': '打开游戏',
                                'checks': [{'covers': ['play'], 'action': '点 Play', 'expected': '进入关卡',
                                            'basis': 'strict_requirement'}]}]}

    def run_cli(self, name='checklist.html', *extra):
        target = self.root / name
        plan_path = self.root / 'plan.json'
        plan_path.write_text(json.dumps(self.plan))
        # Apply the same owned-PID probe inside this isolated CLI process;
        # the H5 builder, ZIP identities and actual HTTP reads remain real.
        bootstrap = ("import sys,runpy;sys.path.insert(0,"+repr(str(h5.CORE_TOOLS))+");import browser_slots;"
            "original=browser_slots.process_identity;owned="+repr(self.owned_pid)+";identity="+repr(self.owned_identity)+";"
            "browser_slots.process_identity=lambda pid:identity if pid==owned and browser_slots.alive(pid) else original(pid);"
            "sys.argv=["+repr(str(h5.HERE/'build_playtest_h5.py'))+"]+sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')")
        return subprocess.run([sys.executable, '-B', '-c', bootstrap,
                               '--plan', str(plan_path), '--out', str(target), *map(str, extra)],
                              env={**os.environ, 'GAME_SKILL_LOCK_DIR': str(self.slots.parent)},
                              capture_output=True, text=True, timeout=15)

    def test_trial_reuses_simulated_phone_preview_and_refuses_changed_or_missing_snapshot(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (self.root / 'checklist.html').read_text()
        self.assertIn('H5 fixture \\u003c>&', html)
        self.assertIn('"ad_simulator":true', html)
        self.assertEqual(tree_sha(self.web), self.web_sha)
        self.assertNotEqual(self.run_cli('web/checklist.html').returncode, 0)
        self.index.write_text('<html><head></head>wrong build</html>')
        self.assertIn('Web 构建不同', self.run_cli('changed.html').stderr)
        (self.slots / f'{self.slot}.json').unlink()
        self.assertIn('未绑定有效', self.run_cli('closed.html').stderr)

    def test_final_split_uses_matching_english_receipts_and_scoped_zip_works_in_trial(self):
        archive = self.root / 'fixture.zip'
        with ZipFile(archive, 'w') as z:
            z.writestr('game.js', 'void 0;')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        native_sha = 'a' * 64
        receipt_path, acceptance_path = self.root / 'delivery.json', self.root / 'acceptance.json'
        receipt = {'status': 'delivery_file_verified', 'entry': 'official', 'expected_tree_exact': True,
                   'archive': str(archive), 'sha256': digest, 'native': str(self.root / 'native'),
                   'fresh_size_check': {'sha256': digest, 'run_id': 'fixture-only', 'reused': False},
                   'preview': {'url': self.url, 'web_tree_sha256': self.web_sha},
                   'final_startup_runtime': {'passed': True, 'native_tree_sha256': native_sha}}
        acceptance = {'status': 'passed', 'board': 'localize', 'stage': 'device', 'errors': [], 'catalog_checks': 1,
                      'binding': {'web_tree_sha256': self.web_sha, 'native_tree_sha256': native_sha}}
        receipt_path.write_text(json.dumps(receipt))
        acceptance_path.write_text(json.dumps(acceptance))
        package_args = ('--zip', archive, '--delivery-record', receipt_path)
        self.assertEqual(self.run_cli('scoped.html', *package_args).returncode, 0)
        self.plan['mode'] = 'package'
        self.assertEqual(self.run_cli('scoped-dual.html', *package_args).returncode, 0)
        self.assertIn('const split = Boolean(plan.preview_url)', (self.root/'scoped-dual.html').read_text())
        package_args += ('--acceptance-report', acceptance_path)
        result = self.run_cli('final.html', *package_args)
        self.assertEqual(result.returncode, 0, result.stderr)
        read = lambda name: re.search(r'"progress_key":"([^"]+)"', (self.root / name).read_text())[1]
        self.assertEqual(read('scoped.html'), read('final.html'))
        acceptance['binding']['native_tree_sha256'] = 'b' * 64
        acceptance_path.write_text(json.dumps(acceptance))
        self.assertIn('Native 或 Web', self.run_cli('wrong-native.html', *package_args).stderr)
        archive.write_bytes(b'other file')
        self.assertIn('ZIP 已变化', self.run_cli('wrong-zip.html', *package_args).stderr)

    def test_share_has_no_machine_address_or_required_live_service(self):
        self.plan['mode'] = 'share'
        self.plan['inventory'][0]['evidence'] = str(self.root / 'local-evidence.png')
        (self.slots / f'{self.slot}.json').unlink()
        result = self.run_cli('share.html')
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (self.root / 'share.html').read_text(encoding='utf-8')
        self.assertIn('可转发清单', html)
        self.assertIn(self.web_sha, html)
        self.assertNotIn(self.url, html)
        self.assertNotIn(str(self.root), html)

    def test_refuses_old_problem_without_current_fix_evidence(self):
        changed = deepcopy(self.plan)
        changed['steps'][0]['checks'][0]['problem'] = '旧版异常'
        with self.assertRaisesRegex(ValueError, '已复验修复'):
            h5.validate_plan(changed)
        self.plan['inventory'].append({'id': 'retry', 'page': '结算', 'state': '失败',
                                       'control': 'Retry', 'evidence': 'fixture route'})
        with self.assertRaisesRegex(ValueError, '缺少盘点项'):
            h5.validate_plan(self.plan)


if __name__ == '__main__':
    unittest.main()
