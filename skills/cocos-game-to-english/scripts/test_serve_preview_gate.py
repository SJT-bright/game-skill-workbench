#!/usr/bin/env python3
"""An English trial link passes the Chinese check first (Saul 2026-11-01, 总表第 28 条).

serve_preview.py (English entry) in front of the shared server: a link a person will play (--open, --keep,
--idle-minutes 0) is refused without --snapshot, without a passing `chinese_audit.py check` on that very export, or
when the copy the server makes is not the export that was checked; --chinese-original (stage 1) and internal QA
servers start as before; --draft starts a failing build only with the problems printed. Garden Guardians case: an
export that still carries the Chinese picture is refused.
Run: python3 -B test_serve_preview_gate.py
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('english_serve_preview', str(HERE / 'serve_preview.py'))
GATE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GATE)


def make_game(td, colour=(200, 120, 40, 255)):
    """A tiny English project with one picture, and a web export carrying the same bytes."""
    from PIL import Image
    root = Path(td) / 'Game'
    (root / 'assets' / 'tex').mkdir(parents=True)
    (root / 'docs' / 'english').mkdir(parents=True)
    Image.new('RGBA', (48, 32), colour).save(str(root / 'assets' / 'tex' / 'btn.png'))
    web = root / 'build' / 'web-mobile'
    (web / 'assets').mkdir(parents=True)
    (web / 'index.html').write_text('<html><canvas id="GameCanvas"></canvas></html>', encoding='utf-8')
    shutil.copy2(str(root / 'assets' / 'tex' / 'btn.png'), str(web / 'assets' / 'btn.png'))
    # This suite isolates the Chinese gate; provide a valid synthetic art receipt first.
    sys.path.insert(0, str(HERE.parents[1] / 'remake-core/scripts'))
    import art_receipt as AR
    import audit_value_presentation as VP
    AR.write(root, 'pass', {'value_presentation': {'revision': VP.REVISION, 'mode': 'runtime', 'passed': True,
             'pages': 2, 'source_sha256': VP.source_fingerprint(root)}})
    return root, web


def pixels_sha(path):
    sys.path.insert(0, str(HERE))
    import chinese_audit as CA
    return CA.pixels_sha256(CA.open_rgba(path))


def env_for(td, fake=None):
    return dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GAME_SKILL_LOCK_DIR=str(Path(td) / 'locks'),
                CHINESE_AUDIT_FAKE_OCR=json.dumps(fake or {}, ensure_ascii=False))


def scan(root, web, env):
    r = subprocess.run([sys.executable, '-B', str(HERE / 'chinese_audit.py'), 'scan', '--project', str(root),
                        '--export', str(web), '--ocr', 'fake'], env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


def quiet():
    out = []
    return out, out.append


class GateDecisions(unittest.TestCase):
    """The gate itself, in this process."""

    def test_missing_art_blocks_every_person_mode_and_draft(self):
        for flags in (['--open'], ['--keep'], ['--idle-minutes', '0'], ['--open', '--draft']):
            with tempfile.TemporaryDirectory() as td:
                root, web = make_game(td)
                (root / '.tiktok-kit/art-receipt.json').unlink()
                err = io.StringIO()
                with self.assertRaises(SystemExit) as cm, _stderr(err):
                    GATE.gate(['--directory', str(web), '--project', str(root), '--snapshot'] + flags, say=quiet()[1])
                self.assertEqual(cm.exception.code, 1)
                self.assertIn('重跑 art_check', err.getvalue())

    def test_internal_qa_server_is_not_checked(self):
        argv = ['--directory', '/nowhere', '--snapshot', '--name', 'qa']
        self.assertEqual(GATE.gate(argv)[1], None)
        self.assertEqual(GATE.gate(['--directory', '/nowhere', '--raw', '--idle-minutes', '0'])[1], None)

    def test_chinese_original_is_not_checked_and_flag_is_not_passed_on(self):
        lines, say = quiet()
        argv, verify = GATE.gate(['--directory', '.', '--snapshot', '--open', '--idle-minutes', '0',
                                  '--chinese-original'], say=say)
        self.assertIsNone(verify)
        self.assertNotIn('--chinese-original', argv)
        self.assertIn('中文原版', ''.join(lines))

    def test_person_link_without_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            err = io.StringIO()
            with self.assertRaises(SystemExit) as cm, _stderr(err):
                GATE.gate(['--directory', str(web), '--open', '--project', str(root)], say=quiet()[1])
            self.assertEqual(cm.exception.code, 1)
            self.assertIn('--snapshot', err.getvalue())

    def test_no_audit_refuses_and_points_at_the_steps(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            (root / 'docs' / 'english' / 'image-review.json').write_text(json.dumps({'schema': 'image_review.v1', 'images': [
                {'sha256': 'x', 'status': 'done', 'chinese': 'no', 'slices_reviewed': True, 'reviewer': 'main'}]}))
            lines, say = quiet()
            err = io.StringIO()
            with self.assertRaises(SystemExit), _stderr(err):
                GATE.gate(['--directory', str(web), '--snapshot', '--idle-minutes', '0'], say=say)   # project found from build/
            text = ''.join(lines)
            self.assertIn('no_audit', text)
            self.assertIn('不是证据', text)                 # the hand-written old record does not count
            self.assertIn('scan --project', err.getvalue())

    def test_project_not_found_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            web = Path(td) / 'export'
            web.mkdir()
            (web / 'index.html').write_text('<html></html>', encoding='utf-8')
            err = io.StringIO()
            with self.assertRaises(SystemExit), _stderr(err):
                GATE.gate(['--directory', str(web), '--snapshot', '--keep'], say=quiet()[1])
            self.assertIn('--chinese-original', err.getvalue())

    def test_export_still_carrying_the_chinese_picture_is_refused(self):
        """Garden Guardians: the project picture was redrawn, the export still has the Chinese one."""
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            chinese = pixels_sha(web / 'assets' / 'btn.png')
            from PIL import Image
            Image.new('RGBA', (48, 32), (30, 160, 90, 255)).save(str(root / 'assets' / 'tex' / 'btn.png'))   # redrawn
            import art_receipt as AR
            import audit_value_presentation as VP
            AR.write(root, 'pass', {'value_presentation': {'revision': VP.REVISION, 'mode': 'runtime', 'passed': True,
                     'pages': 2, 'source_sha256': VP.source_fingerprint(root)}})
            os.utime(str(web / 'assets' / 'btn.png'), (1, 1))                                            # older export
            scan(root, web, env_for(td, {chinese: '高波来袭！'}))
            lines, say = quiet()
            with self.assertRaises(SystemExit), _stderr(io.StringIO()):
                GATE.gate(['--directory', str(web), '--snapshot', '--open', '--no-browser'], say=say)
            self.assertIn('高波来袭', ''.join(lines))

    def test_clean_export_passes_and_a_changed_copy_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            lines, say = quiet()
            argv, verify = GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--project', str(root),
                                      '--name', 'G 英文 第1轮'], say=say)
            self.assertIsNotNone(verify)
            self.assertIn('--project', argv)                 # the shared server still gets it
            self.assertIn('通过', ''.join(lines))
            good = Path(td) / 'snap-good'
            shutil.copytree(str(web), str(good))
            verify(good)
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual(len(log), 1)
            self.assertTrue(log[0]['passed'])
            self.assertEqual(log[0]['snapshot_manifest_sha256'], log[0]['export_manifest_sha256'])
            self.assertEqual(log[0]['name'], 'G 英文 第1轮')
            bad = Path(td) / 'snap-bad'
            shutil.copytree(str(web), str(bad))
            (bad / 'index.html').write_text('<html>rebuilt after the check</html>', encoding='utf-8')
            err = io.StringIO()
            with self.assertRaises(SystemExit), _stderr(err):
                verify(bad)
            self.assertFalse(bad.exists())                   # the copy that does not match is removed
            self.assertIn('不一样', err.getvalue())

    def test_draft_starts_with_the_problems_listed(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            env = env_for(td, {pixels_sha(root / 'assets' / 'tex' / 'btn.png'): '设置'})
            scan(root, web, env)
            lines, say = quiet()
            argv, verify = GATE.gate(['--directory', str(web), '--snapshot', '--open', '--draft'], say=say)
            self.assertNotIn('--draft', argv)
            text = ''.join(lines)
            self.assertIn('needs_review', text)
            self.assertIn('不能说「检查过」', text)
            snap = Path(td) / 'snap'
            shutil.copytree(str(web), str(snap))
            verify(snap)
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual((log[0]['passed'], log[0]['draft']), (False, True))
            self.assertGreater(log[0]['open_problems'], 0)


def timing_events(root):
    log = root / 'docs' / 'timing' / 'stage-timing.jsonl'
    return [json.loads(l) for l in log.read_text(encoding='utf-8').splitlines() if l.strip()] if log.is_file() else []


class TrialLinkTiming(unittest.TestCase):
    """简化.11.9 (割草 蛋壳特工队: the second trial link was never recorded, so a 6-hour "round 1" hid Saul's second
    playtest): serve_preview.py records `stage_timer.py link <N>` itself, N = different exports handed out."""

    def link(self, root, web, td, say):
        argv, verify = GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--project', str(root)], say=say)
        snap = Path(tempfile.mkdtemp(prefix='snap-', dir=td))
        shutil.rmtree(str(snap))
        shutil.copytree(str(web), str(snap))
        verify(snap)

    def test_new_export_is_a_round_same_export_is_not_and_numbers_do_not_double(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            lines, say = quiet()
            self.link(root, web, td, say)
            links = [e for e in timing_events(root) if e['ev'] == 'link']
            self.assertEqual([e['n'] for e in links], [1])
            self.assertIn('第 1 轮', ''.join(lines))
            self.link(root, web, td, say)                                  # the same export served again
            self.assertEqual([e['n'] for e in timing_events(root) if e['ev'] == 'link'], [1])
            self.assertIn('同一份导出', ''.join(lines))
            sys.path.insert(0, str(HERE))
            import stage_timer
            stage_timer.call(root, 'link', 2)                              # the session also ran T link 2 by hand
            (web / 'index.html').write_text('<html><canvas id="GameCanvas"></canvas><!-- round 2 --></html>', encoding='utf-8')
            scan(root, web, env_for(td))
            self.link(root, web, td, say)                                  # a new export: round 2, already recorded
            self.assertEqual([e['n'] for e in timing_events(root) if e['ev'] == 'link'], [1, 2])

    def test_timing_that_cannot_be_written_does_not_stop_the_link(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            (root / 'docs' / 'timing').write_text('not a folder', encoding='utf-8')
            lines, say = quiet()
            self.link(root, web, td, say)                                  # no SystemExit
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual(len(log), 1)

    def test_chinese_original_with_project_is_marked_once(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            for _ in range(2):
                lines, say = quiet()
                GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--chinese-original', '--project', str(root)], say=say)
            marks = [e for e in timing_events(root) if e['ev'] == 'mark']
            self.assertEqual([e['name'] for e in marks], ['中文原版链接'])
            GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--chinese-original'], say=quiet()[1])   # no --project: fine


class _stderr(object):
    def __init__(self, buf):
        self.buf = buf

    def __enter__(self):
        self.old, sys.stderr = sys.stderr, self.buf
        return self.buf

    def __exit__(self, *exc):
        sys.stderr = self.old
        return False


class RealServer(unittest.TestCase):
    """The real wrapper process: refused without a check, started (and the copy verified) after a clean one."""

    def start(self, td, argv, env):
        p = subprocess.Popen([sys.executable, '-B', str(HERE / 'serve_preview.py')] + argv, cwd=str(HERE), env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = []
        reader = threading.Thread(target=lambda: [lines.append(l) for l in p.stdout], daemon=True)
        reader.start()
        return p, lines, reader

    def stop(self, p, reader):
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        reader.join(timeout=5)
        p.stdout.close()

    def test_refused_without_check_then_served_after_it(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            env = env_for(td)
            argv = ['--directory', str(web), '--snapshot', '--no-browser', '--idle-minutes', '0', '--name', 'test 英文']
            p, lines, reader = self.start(td, argv, env)
            try:
                p.wait(timeout=60)
            finally:
                self.stop(p, reader)
            self.assertEqual(p.returncode, 1, ''.join(lines)[-800:])
            self.assertIn('不起英文试玩服务', ''.join(lines))
            self.assertIsNone(re.search(r'http://127\.0\.0\.1:\d+/', ''.join(lines)))

            scan(root, web, env)
            p, lines, reader = self.start(td, argv, env)
            try:
                url, deadline = None, time.time() + 60
                while url is None and time.time() < deadline and p.poll() is None:
                    found = re.search(r'http://127\.0\.0\.1:\d+/', ''.join(lines))
                    url = found.group(0) if found else None
                    time.sleep(0.1)
                self.assertIsNotNone(url, 'no trial link printed: ' + ''.join(lines)[-800:])
                body = None
                for _ in range(100):
                    try:
                        body = urllib.request.urlopen(url, timeout=5).read()
                        break
                    except OSError:
                        time.sleep(0.1)
                self.assertIsNotNone(body, 'trial link did not answer')
                text = ''.join(lines)
                self.assertIn('中文专项检查：通过', text)
                self.assertIn('一字不差', text)
            finally:
                self.stop(p, reader)
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual(log[-1]['snapshot_manifest_sha256'], log[-1]['export_manifest_sha256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
