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
_spec = importlib.util.spec_from_file_location('english_serve_preview', str(HERE / 'serve_preview.py'))
GATE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GATE)


def make_game(td, colour=(200, 120, 40, 255)):
    """A tiny English project with one picture, and a web export carrying the same bytes."""
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
    # This suite isolates the Chinese gate. Supply a scoped synthetic art receipt; live capture is tested separately.
    matrix = {'cases':[dict(id='fixture', screen='home', kind='home', width=393, height=852, dpr=1,
                            recipe='test', environment='test', stable=False, witness=[{'path':'fixture'}])]}
    (root/'docs/art').mkdir(exist_ok=True)
    (root/'docs/art/capture-plan.json').write_text(json.dumps(matrix))
    synthetic_art_review(root, web)
    import tiktok_finalize as F
    from audit_image_review_record import main as image_review
    assert not F.finalize_source(root, 'localize', steps=('art_static',))['blocks']
    F.record_prepared_native(root, native, F.prepared_source_identity(root))
    assert image_review(['write', '--directory', str(web), '--directory', str(native), '--out',
                         str(root / 'docs/english/image-review.json'), '--ocr', 'fake']) == 0
    return root, web


def native_dir(root):
    return root / 'build' / 'bytedance'


def synthetic_art_review(root, web):
    """Chinese gate tests use a test-only art receipt; real rendering is covered by capture replay."""
    capture = Path(__file__).resolve().parents[2]/'remake-core/scripts/art_capture_round.mjs'
    started = json.loads(subprocess.check_output(['node',str(capture),'start',str(root),str(web)], text=True))
    import hashlib
    import uuid
    sys.path.insert(0, str(HERE.parents[1] / 'remake-core/scripts'))
    from art_round_check import run, origin_hash, artifact_hash
    store = root/'.tiktok-kit/art-rounds/proofs'
    store.mkdir(exist_ok=True)
    dumps = root/'docs/test/captured'
    dumps.mkdir(parents=True, exist_ok=True)
    proof_id = str(uuid.uuid4())
    serial = lambda obj: json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode()
    sha = lambda data: hashlib.sha256(data).hexdigest()
    case = json.loads((root/'docs/art/capture-plan.json').read_text())['cases'][0]
    png = (web/'assets/btn.png').read_bytes()
    dump = serial(dict(art_capture_id=proof_id, screen='home',kind='home',viewport={'width':393,'height':852},
                       screenshot='fixture.png'))
    (dumps/'fixture.png').write_bytes(png)
    (dumps/'capture-ui-dump-fixture.json').write_bytes(dump)
    fields = dict(id=proof_id, caseHash=sha(serial(case)), case='fixture', version=started['version'], round=started['id'],
                  dump=sha(dump), png=sha(png), reads=['assets/btn.png'], env='unit')
    (store/(proof_id+'.json')).write_bytes(serial(dict(fields,seal=sha(serial(fields)))))
    verified = run('verify', root, web, dumps)
    assert verified.get('ready'), verified
    proof = dict(round=started['id'], version=started['version'], dumps=str(dumps), origin_hash=origin_hash(verified), artifact_hash=artifact_hash(root, dumps), ready=True)
    import art_receipt as AR
    import audit_value_presentation as VP
    AR.write(root, 'pass', {'capture_round':proof, 'value_presentation': {'revision': VP.REVISION, 'mode': 'runtime', 'passed': True,
             'pages': 2, 'source_sha256': VP.source_fingerprint(root)}})


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

    def test_formal_trial_requires_executed_sprite_check_and_actual_native_image_review(self):
        with tempfile.TemporaryDirectory() as td:
            root, web = make_game(td)
            scan(root, web, env_for(td))
            native = native_dir(root)
            args = ['--directory', str(web), '--snapshot', '--open', '--native', str(native)]
            import tiktok_finalize as F
            F.finalize_source(root, 'localize', steps=())
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(args, say=quiet()[1])
            self.assertIn('Sprite 比例', err.getvalue())

            F.finalize_source(root, 'localize', steps=('art_static',))
            F.record_prepared_native(root, native, F.prepared_source_identity(root))
            from PIL import Image
            Image.new('RGB', (48, 32), (80, 75, 50)).save(native / 'reward.jpg')
            F.record_prepared_native(root, native, F.prepared_source_identity(root))
            with self.assertRaises(SystemExit), _stderr(io.StringIO()) as err:
                GATE.gate(args, say=quiet()[1])
            self.assertIn('逐图复核未通过', err.getvalue())
            self.assertIn('reward.jpg', err.getvalue())

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
            synthetic_art_review(root, web)
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
            self.assertIn('art_receipt_sha256', log[0])
            self.assertIn('image_review_sha256', log[0])
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
            from make_tiktok_zip import pretrial_native_problems
            review = root / 'docs/english/image-review.json'
            files = {path.relative_to(native).as_posix(): path.read_bytes()
                     for path in native.rglob('*') if path.is_file()}
            self.assertIn('需要成功启动', pretrial_native_problems(files, root, review)[0])
            _, verify = GATE.gate(args, say=quiet()[1])
            commit = verify(shutil.copytree(web, Path(td) / 'first'))
            self.assertIn('需要成功启动', pretrial_native_problems(files, root, review)[0])
            commit()
            self.assertEqual(pretrial_native_problems(files, root, review), [])
            (native / 'game.js').write_text('/* layout changed, all images unchanged */')
            files['game.js'] = (native / 'game.js').read_bytes()
            self.assertIn('ART_trial_native', pretrial_native_problems(files, root, review)[0])
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


def timing_events(root):
    log = root / 'docs' / 'timing' / 'stage-timing.jsonl'
    return [json.loads(l) for l in log.read_text(encoding='utf-8').splitlines() if l.strip()] if log.is_file() else []


class TrialLinkTiming(unittest.TestCase):
    """简化.11.9 (割草 蛋壳特工队: the second trial link was never recorded, so a 6-hour "round 1" hid Saul's second
    playtest): serve_preview.py records `stage_timer.py link <N>` itself, N = different exports handed out."""

    def link(self, root, web, td, say):
        argv, verify = GATE.gate(['--directory', str(web), '--snapshot', '--keep', '--project', str(root),
                                 '--native', str(native_dir(root))], say=say)
        snap = Path(tempfile.mkdtemp(prefix='snap-', dir=td))
        shutil.rmtree(str(snap))
        shutil.copytree(str(web), str(snap))
        verify(snap)()

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
            with self.assertRaises(SystemExit), _stderr(io.StringIO()):
                self.link(root, web, td, say)  # A new export must not inherit the previous art check.
            synthetic_art_review(root, web)
            self.link(root, web, td, say)

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
