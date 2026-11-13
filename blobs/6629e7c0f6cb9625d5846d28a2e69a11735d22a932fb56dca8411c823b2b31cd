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
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'remake-core/scripts'))
_spec = importlib.util.spec_from_file_location('english_serve_preview', str(HERE / 'serve_preview.py'))
GATE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GATE)


def make_game(td, colour=(200, 120, 40, 255), art='pass'):
    """A tiny English project with one picture, and a web export carrying the same bytes.

    art: 'pass' writes a passing full art_check record (11.17.14 first-trial requirement), 'fail' a failing one,
    None writes nothing."""
    from PIL import Image
    root = Path(td) / 'Game'
    (root / 'assets' / 'tex').mkdir(parents=True)
    (root / 'docs' / 'english').mkdir(parents=True)
    (root / 'project.json').write_text('{"engine":"cocos-creator-js","version":"2.4.15"}')
    Image.new('RGBA', (48, 32), colour).save(str(root / 'assets' / 'tex' / 'btn.png'))
    web = root / 'build' / 'web-mobile'
    (web / 'assets').mkdir(parents=True)
    (web / 'index.html').write_text('<html><canvas id="GameCanvas"></canvas></html>', encoding='utf-8')
    shutil.copy2(str(root / 'assets' / 'tex' / 'btn.png'), str(web / 'assets' / 'btn.png'))
    native = native_dir(root)
    native.mkdir()
    for name in ('game.js', 'game.json', 'project.config.json'):
        (native / name).write_text('{}')
    Image.new('RGB', (48, 32), (35, 50, 80)).save(native / 'reward.jpg')
    import tiktok_finalize as F
    assert not F.finalize_source(root, 'localize', steps=())['blocks']
    F.record_prepared_native(root, native, F.prepared_source_identity(root))
    if art:
        import art_check_record
        rows = [{'check': '深色粗字（永久禁止）', 'status': '需处理' if art == 'fail' else '通过'}]
        art_check_record.write(root, art, {'rows': rows, 'failed': int(art == 'fail')}, None, 'localize')
    return root, web


def native_dir(root):
    return root / 'build' / 'bytedance'


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


class PreviewOnlyCase(unittest.TestCase):
    def setUp(self):
        # Isolate Chinese-audit, Native and preview lifecycle rules. Strict-six
        # production is tested by test_ad_standard_english_entry and shared gates.
        import ad_standard_scope
        guard = patch.object(ad_standard_scope, 'requirement', return_value={'required': False})
        guard.start()
        self.addCleanup(guard.stop)


class GateDecisions(PreviewOnlyCase):
    """The gate itself, in this process."""

    def test_person_modes_use_existing_candidate_without_an_art_receipt(self):
        for flags in (['--open'], ['--keep'], ['--idle-minutes', '0'], ['--open', '--draft']):
            with tempfile.TemporaryDirectory() as td:
                root, web = make_game(td)
                scan(root, web, env_for(td))
                args = ['--directory', str(web), '--native', str(native_dir(root)), '--snapshot'] + flags
                _, verify = GATE.gate(args, say=quiet()[1])
                self.assertTrue(callable(verify))
                self.assertFalse((root / '.tiktok-kit/art-receipt.json').exists())

    def test_internal_qa_server_is_not_checked(self):
        argv = ['--directory', '/nowhere', '--snapshot', '--name', 'qa']
        self.assertEqual(GATE.gate(argv)[1], None)
        self.assertEqual(GATE.gate(['--directory', '/nowhere', '--raw', '--idle-minutes', '0'])[1], None)

    def test_formal_trial_still_requires_actual_prepared_native(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            args = ['--directory', str(web), '--snapshot', '--open']
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(args, say=quiet()[1])
            self.assertIn('需要 --native', err.getvalue())
            native = native_dir(root)
            (native / 'game.js').write_text('changed startup')
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(args + ['--native', str(native)], say=quiet()[1])
            self.assertIn('缺少同版准备证据', err.getvalue())

    def test_direct_shared_open_cannot_skip_the_english_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            shared = HERE.parents[1] / 'remake-core/scripts/serve_preview.py'
            result = subprocess.run([sys.executable, '-B', str(shared), '--directory', str(web), '--snapshot',
                                     '--open', '--no-browser', '--project', str(root)],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('英化正式试玩请用', result.stderr)
            self.assertNotIn('http://127.0.0.1:', result.stdout)

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
            # The export still contains the old image but represents a new build of the test page.
            with (web/'index.html').open('a') as f:
                f.write('<!-- refreshed test export -->')
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
                                      '--native', str(native_dir(root)), '--name', 'G 英文 第1轮'], say=say)
            self.assertIsNotNone(verify)
            self.assertIn('--project', argv)                 # the shared server still gets it
            self.assertIn('通过', ''.join(lines))
            good = Path(td) / 'snap-good'
            shutil.copytree(str(web), str(good))
            record = verify(good)
            self.assertFalse((root / "docs/english/chinese-audit/trial-links.json").exists())
            record()
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual(len(log), 1)
            self.assertTrue(log[0]['passed'])
            self.assertNotIn('art_receipt_sha256', log[0])
            self.assertNotIn('image_review_sha256', log[0])
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

    def test_reopen_only_checks_the_passed_records(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            args = ['--directory', str(web), '--project', str(root), '--native', str(native_dir(root)),
                    '--snapshot', '--keep']
            _, verify = GATE.gate(args, say=quiet()[1])
            verify(shutil.copytree(web, Path(td) / 'first'))()
            with patch('chinese_audit.evaluate', side_effect=AssertionError('reopen must not rerun the check')):
                _, verify = GATE.gate(args + ['--reopen'], say=quiet()[1])
                verify(shutil.copytree(web, Path(td) / 'second'))()
                result = root / 'docs/english/chinese-audit/check-result.json'
                result.write_text('{}')
                with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                    GATE.gate(args + ['--reopen'], say=quiet()[1])
                self.assertIn('找不到与当前导出和回执一致的已通过试玩记录', err.getvalue())

    def test_same_chinese_result_does_not_invalidate_the_earlier_ready_trial(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            args = ['--directory', str(web), '--native', str(native_dir(root)), '--snapshot', '--open']
            _, verify = GATE.gate(args, say=quiet()[1])
            verify(shutil.copytree(web, Path(td) / 'first'))()
            path = root / 'docs/english/chinese-audit/check-result.json'
            before = path.read_bytes()

            with patch('chinese_audit.now', return_value='2099-01-01T00:00:00Z'):
                # Begin an identical regular trial without committing it.
                GATE.gate(args, say=quiet()[1])

            self.assertEqual(path.read_bytes(), before)
            _, reopen = GATE.gate(args + ['--reopen'], say=quiet()[1])
            reopen(shutil.copytree(web, Path(td) / 'reopened'))()

    def test_native_layout_changes_without_image_changes_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            native = native_dir(root)
            args = ['--directory', str(web), '--native', str(native), '--snapshot', '--open']
            _, verify = GATE.gate(args, say=quiet()[1])
            verify(shutil.copytree(web, Path(td) / 'first'))()
            (native / 'game.js').write_text('/* layout changed, all images unchanged */')
            for mode in ([], ['--reopen']):
                with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                    GATE.gate(args + mode, say=quiet()[1])
                self.assertIn('缺少同版准备证据', err.getvalue())

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
            verify(snap)()
            log = json.loads((root / 'docs' / 'english' / 'chinese-audit' / 'trial-links.json').read_text(encoding='utf-8'))
            self.assertEqual((log[0]['passed'], log[0]['draft']), (False, True))
            self.assertGreater(log[0]['open_problems'], 0)


class FirstTrialArtRecord(PreviewOnlyCase):
    """11.17.14: one full art_check run before the first formal trial; no image fingerprints, no forced re-runs."""

    def args(self, root, web):
        return ['--directory', str(web), '--native', str(native_dir(root)), '--snapshot', '--open']

    def test_first_formal_trial_without_art_check_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td, art=None)
            scan(root, web, env_for(td))
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(self.args(root, web), say=quiet()[1])
            self.assertIn('art_check', err.getvalue())

    def test_latest_run_with_blocking_rows_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td, art='fail')
            scan(root, web, env_for(td))
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(self.args(root, web), say=quiet()[1])
            self.assertIn('深色粗字', err.getvalue())

    def test_changed_images_after_a_pass_do_not_force_a_rerun(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            from PIL import Image
            import tiktok_finalize as F
            # A small art fix after the full art_check: new button bytes, normal source preparation, no art re-run.
            Image.new('RGBA', (48, 32), (10, 200, 90, 255)).save(str(root / 'assets' / 'tex' / 'btn.png'))
            shutil.copy2(str(root / 'assets' / 'tex' / 'btn.png'), str(web / 'assets' / 'btn.png'))
            assert not F.finalize_source(root, 'localize', steps=())['blocks']
            F.record_prepared_native(root, native_dir(root), F.prepared_source_identity(root))
            scan(root, web, env_for(td))
            _, verify = GATE.gate(self.args(root, web), say=quiet()[1])
            self.assertTrue(callable(verify))

    def test_project_that_already_had_a_formal_trial_only_gets_a_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td, art=None)
            scan(root, web, env_for(td))
            log = root / 'docs/english/chinese-audit/trial-links.json'
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(json.dumps([{'passed': True, 'draft': False}]), encoding='utf-8')
            said, say = quiet()
            _, verify = GATE.gate(self.args(root, web), say=say)
            self.assertTrue(callable(verify))
            self.assertTrue(any('警告' in line for line in said))

    def test_draft_starts_without_art_check_and_says_so(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td, art=None)
            scan(root, web, env_for(td))
            said, say = quiet()
            _, verify = GATE.gate(['--directory', str(web), '--snapshot', '--open', '--draft'], say=say)
            self.assertTrue(callable(verify))
            self.assertTrue(any('美术技术检查未完成' in line for line in said))


def timing_events(root):
    log = root / 'docs' / 'timing' / 'stage-timing.jsonl'
    return [json.loads(l) for l in log.read_text(encoding='utf-8').splitlines() if l.strip()] if log.is_file() else []


class TrialLinkTiming(PreviewOnlyCase):
    """简化.11.9 (割草 蛋壳特工队: the second trial link was never recorded, so a 6-hour "round 1" hid Saul's second
    playtest): serve_preview.py records `stage_timer.py link <N>` itself, N = different exports handed out."""

    def link(self, root, web, td, say):
        argv, verify = GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--project', str(root),
                                 '--native', str(native_dir(root))], say=say)
        snap = Path(tempfile.mkdtemp(prefix='snap-', dir=td))
        shutil.rmtree(str(snap))
        shutil.copytree(str(web), str(snap))
        verify(snap)()

    def test_prepared_candidates_do_not_start_user_wait_or_record_a_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            lines, say = quiet()
            self.link(root, web, td, say)
            self.link(root, web, td, say)
            self.assertFalse([event for event in timing_events(root) if event['ev'] == 'link'])
            self.assertFalse((root / '.tiktok-kit/art-receipt.json').exists())

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
                args = ['--directory', str(web), '--snapshot', '--keep', '--chinese-original', '--project', str(root)]
                before = list(timing_events(root))
                GATE.gate(args, say=say)
                self.assertEqual(timing_events(root), before)  # gate is earlier than an actual ready service
                GATE.chinese_ready(args, say)(web)
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


class RealServer(PreviewOnlyCase):
    """The real wrapper process: refused without a check, started (and the copy verified) after a clean one."""

    def start(self, td, argv, env):
        # Child-process isolation, without a production bypass flag.
        bootstrap = ("import sys,runpy;sys.path.insert(0," + repr(str(HERE.parents[1] / 'remake-core/scripts')) +
                     ");import ad_standard_scope;ad_standard_scope.requirement=lambda *a,**k:{'required':False};" +
                     "sys.argv=[" + repr(str(HERE / 'serve_preview.py')) + "]+sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')")
        p = subprocess.Popen([sys.executable, '-B', '-c', bootstrap] + argv, cwd=str(HERE), env=env,
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

    def test_failed_service_prerequisites_do_not_record_pass(self):
        shared = runpy.run_path(str(HERE.parents[1] / 'remake-core/scripts/serve_preview.py'))
        serve = shared['main']
        for failure in ('bind', 'entry', 'home', 'smoke'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as td:
                root, web = make_game(td)
                scan(root, web, env_for(td))
                argv = ['--directory', str(web), '--native', str(native_dir(root)), '--snapshot', '--keep', '--no-browser']
                argv, verify = GATE.gate(argv, say=quiet()[1])
                log = root / 'docs/english/chinese-audit/trial-links.json'
                snapshot = Path(td) / 'snap'

                def make_copy(*args):
                    return shutil.copytree(web, snapshot), 'project', True

                def no_listener(*args):
                    raise OSError('test: cannot bind trial listener')

                replacements = {'make_snapshot': make_copy,
                                'entry_readback': lambda *a, **kw: (failure != 'entry', [], 'entry check failed'),
                                'home_shot_gate': lambda *a, **kw: ('block' if failure == 'home' else 'ok', 'home check', {}),
                                'trial_smoke_gate': lambda *a, **kw: ('block' if failure == 'smoke' else 'ok', 'smoke check')}
                if failure == 'bind':
                    replacements['ThreadingHTTPServer'] = no_listener
                import browser_slots
                with patch.dict(serve.__globals__, replacements), patch.object(browser_slots, 'sweep'), \
                        patch.object(browser_slots, 'register', return_value=None), _stderr(io.StringIO()), \
                        self.assertRaises(OSError if failure == 'bind' else SystemExit):
                    serve(argv, verify_snapshot=verify)
                self.assertFalse(log.exists(), 'a failed launch left formal trial evidence')
                self.assertFalse(snapshot.exists(), 'a failed launch leaked its snapshot')

    def test_refused_without_check_then_served_after_it(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            env = env_for(td)
            argv = ['--directory', str(web), '--snapshot', '--no-browser', '--idle-minutes', '0',
                    '--native', str(native_dir(root)), '--name', 'test 英文']
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


class UserHandoff(PreviewOnlyCase):
    """Real retained HTTP shell, synthetic game evidence, intercepted Chrome launch."""

    def test_only_completed_art_or_bound_package_can_request_chrome(self):
        from functools import partial
        from zipfile import ZipFile
        import handoff_preview as H
        import verify_delivery_preview

        with tempfile.TemporaryDirectory(prefix='英化交接 ') as td:
            project, web = make_game(td)
            scan(project, web, env_for(td))
            GATE.timing(project, 'start', '--run-id', 'trial', '--route', 'source')
            GATE.timing(project, 'stage', '3')
            native = native_dir(project)
            snapshot = shutil.copytree(web, Path(td) / 'snapshot')
            _, verify = GATE.gate(['--directory', str(web), '--snapshot', '--keep',
                                   '--native', str(native)], timing_run_id='trial', say=quiet()[1])
            verify(snapshot)()
            shared = runpy.run_path(str(HERE.parents[1] / 'remake-core/scripts/serve_preview.py'))
            handler = partial(shared['Handler'], directory=str(snapshot), phone_size=(390, 844),
                              preview_token='fixture')
            server = shared['ThreadingHTTPServer'](('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}/'
            # This HTTP server belongs to this test PID. Substitute only its
            # ps-derived identity when sandbox process listings are unavailable.
            owned_pid = os.getpid()
            owned_identity = __import__('hashlib').sha256((str(project.resolve())+':'+str(owned_pid)).encode()).hexdigest()
            original_probe = H.browser_slots.process_identity
            own_probe = lambda pid: owned_identity if pid == owned_pid and H.browser_slots.alive(pid) else original_probe(pid)
            slot = {'id': '1110-090000-preview-abcdef', 'kind': 'preview', 'url': url, 'keep': True, 'dir': str(snapshot),
                    'pid': owned_pid, 'process_identity': own_probe(owned_pid),
                    'project': str(project.resolve()), 'phone_size': [390, 844]}
            plan = {'schema': 'english-playtest-plan.v1', 'game': 'Same game', 'version': 'R1',
                    'mode': 'trial', 'preview_url': url, 'web_tree_sha256': H.tree_sha(web),
                    'inventory': [{'id': 'play', 'page': 'Home', 'state': 'ready',
                                   'control': 'Play', 'evidence': 'fixture'}],
                    'steps': [{'id': 'home', 'page': 'Home', 'enter': 'Open the game',
                               'checks': [{'covers': ['play'], 'basis': 'strict_requirement',
                                           'action': 'Tap Play', 'expected': 'Game starts'}]}]}
            try:
                with patch.object(H.browser_slots, 'process_identity', side_effect=own_probe), \
                        patch.object(verify_delivery_preview, 'process_identity', side_effect=own_probe), \
                        patch.object(H.browser_slots, 'SLOTS', Path(td) / 'slots'), \
                        patch.object(H.browser_slots, 'slots', return_value=[slot]), \
                        patch.object(verify_delivery_preview, 'slots', return_value=[slot]), \
                        patch.object(H.preview_chrome, 'open_chrome_window',
                                     return_value={'status': 'launch_requested'}) as launch:
                    GATE.timing(project, 'begin', '未结束的检查')
                    with self.assertRaisesRegex(ValueError, '开放步骤'):
                        H.handoff(project, url, 'art', plan)
                    GATE.timing(project, 'end', '未结束的检查')
                    with self.assertRaisesRegex(ValueError, '同页清单尚不可用'):
                        H.handoff(project, url, 'art', plan)
                    launch.assert_not_called()
                    self.assertNotIn('done', [event['ev'] for event in timing_events(project)])
                    server.playtest_html = H.browser_slots.playtest_html_path(slot['id'])
                    result = H.handoff(project, url, 'art', plan)
                    self.assertEqual(result['label'], '英文美工试玩')
                    self.assertEqual(launch.call_count, 1)
                    self.assertEqual(launch.call_args.args[0], url + '__playtest/')
                    self.assertIn('完成与沿用', result['stage_report'])
                    self.assertIn('阶段结算', result['stage_report'])
                    page = urllib.request.urlopen(result['playtest_url'], timeout=3).read().decode()
                    self.assertIn(f'"preview_url":"{url}"', page)
                    self.assertIn('game-frame', page)
                    self.assertNotIn('在新标签页打开游戏', page)
                    self.assertEqual([event['ev'] for event in timing_events(project)][-2:], ['done', 'link'])

                    GATE.timing(project, 'stage', '5')
                    with self.assertRaisesRegex(ValueError, '第 3 阶段完成'):
                        H.handoff(project, url, 'art', plan)
                    with self.assertRaisesRegex(ValueError, '交付回执'):
                        H.handoff(project, url, 'package', plan)
                    self.assertEqual(launch.call_count, 1)

                    archive = (Path(td) / 'Final.zip').resolve()
                    with ZipFile(archive, 'w') as z:
                        for path in native.iterdir():
                            z.write(path, path.name)
                    digest = H.chinese_audit.sha_file(archive)
                    delivery = Path(td) / 'delivery.json'
                    size = Path(td) / 'delivery.json.size.json'
                    size.write_text(json.dumps({'archive': str(archive), 'passed': True, 'sha256': digest,
                                                'run_id': 'new-size'}))
                    proof = {'status': 'delivery_file_verified', 'archive': str(archive), 'entry': 'official',
                             'expected_tree_exact': True, 'sha256': digest, 'native': str(native),
                             'fresh_size_check': {'reused': False, 'sha256': digest,
                                                  'run_id': 'new-size', 'report': str(size)},
                             'final_startup_runtime': {'passed': True, 'native_tree_sha256':
                                                       H.startup_renderer.digest(H.startup_renderer.tree(native))},
                             'preview': {'url': url, 'web_tree_sha256': H.tree_sha(web), 'slot_id': slot['id']}}
                    delivery.write_text(json.dumps(proof))
                    # 2026-11-12: the final hand-over is four things together. The source ZIP and the evidence ZIP are
                    # made by remake-core game_handoff.deliver (its own tests use real files); here: it is called by
                    # default, a failure records nothing and opens nothing, and the reply lists all four.
                    import game_handoff
                    made = {'status': 'team_handoff_ready', 'test_zip': str(archive), 'source_zip': str(Path(td) / 'Final_源码.zip'),
                            'evidence_zip': str(Path(td) / 'Final_交接证据.zip'),
                            'reply_lines': ['测试包：' + str(archive), '源码包：' + str(Path(td) / 'Final_源码.zip'),
                                            '交接证据包：' + str(Path(td) / 'Final_交接证据.zip')]}
                    events_before = [event['ev'] for event in timing_events(project)]
                    with patch.object(game_handoff, 'deliver', side_effect=ValueError('工程里有账号、密码或密钥')) as deliver:
                        with self.assertRaisesRegex(ValueError, '最终交接未完成.*账号、密码或密钥'):
                            H.handoff(project, url, 'package', plan, delivery)
                    self.assertEqual(deliver.call_args.args, (delivery, project.resolve(), None))
                    self.assertEqual(launch.call_count, 1, 'Chrome is not opened when the four things are not ready')
                    self.assertEqual([event['ev'] for event in timing_events(project)], events_before, 'and nothing is recorded')
                    with patch.object(game_handoff, 'deliver', return_value=made) as deliver:
                        result = H.handoff(project, url, 'package', plan, delivery)
                    self.assertEqual(deliver.call_count, 1)
                    self.assertEqual(result['label'], '测试包同版试玩')
                    self.assertEqual(launch.call_count, 2)
                    self.assertEqual(result['playtest_url'], url + '__playtest/')
                    self.assertIn('核对本次实际 ZIP', result['stage_report'])
                    self.assertEqual(result['team_handoff'], made)
                    self.assertEqual([line.split('：')[0] for line in result['reply_lines'][:4]], ['测试包', '源码包', '试玩链接', '交接证据包'])
                    self.assertEqual(result['reply_lines'][2], '试玩链接：' + url + '__playtest/')
                    self.assertIn('四样', result['reply_lines'][4])
                    # only an explicit, stated reason leaves the source ZIP and the evidence ZIP out
                    with patch.object(game_handoff, 'deliver', side_effect=AssertionError('must not be called')):
                        with self.assertRaisesRegex(ValueError, '写明原因'):
                            H.handoff(project, url, 'package', plan, delivery, skip_team_handoff=' ')
                        result = H.handoff(project, url, 'package', plan, delivery, no_browser=True,
                                           skip_team_handoff='用户原话：这次只要测试包，源码先不用')
                    self.assertEqual(result['team_handoff']['status'], 'team_handoff_skipped')
                    self.assertEqual(result['reply_lines'], ['测试包：' + str(archive), '试玩链接：' + url + '__playtest/',
                                                              '这次没有附源码包和交接证据包：用户原话：这次只要测试包，源码先不用'])
                    self.assertEqual(launch.call_count, 2)

                    (native / 'game.js').write_text('changed after the final check')
                    with patch.object(game_handoff, 'deliver', side_effect=AssertionError('checked before the team hand-off')):
                        with self.assertRaisesRegex(ValueError, 'Native.*变化'):
                            H.handoff(project, url, 'package', plan, delivery)
                        archive.write_bytes(b'changed ZIP')
                        with self.assertRaisesRegex(ValueError, 'ZIP 已变化'):
                            H.handoff(project, url, 'package', plan, delivery)
                    self.assertEqual(launch.call_count, 2)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
