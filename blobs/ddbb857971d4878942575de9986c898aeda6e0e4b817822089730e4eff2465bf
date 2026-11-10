#!/usr/bin/env python3
"""简化.11.15 (Saul 2026-11-04): after a test package passed, a rework checks only what the change touches.

rework_scope.plan compares the new package with the last passed one (an official writer receipt with the regression
record), file by file: only pictures, sounds or fonts changed (same code, settings, adapter, tools, policy, board,
required suites) -> only the browser suites that can see the change run again and the rest keep the old pass
(reused_from the old receipt); other changes require precise node dependencies, never an automatic full run. check_package's two gates and both
writer paths take the plan; the receipt record keeps what was reused; prepare_delivery still reuses the new receipt for
the same bytes. The AI's own hand checks follow the same plan (a picture change never re-checks sound). The preview
before packaging (--native) finalizes a copy of the build first, like the writers do to the build itself, and the
writers write the docs/checks/ record themselves after publishing.

Synthetic packages; the browser suites themselves are replaced by recorders (their own tests cover them).
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_rework_scope.py
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ad_regression as AD  # noqa: E402
import check_package as C  # noqa: E402
import rework_scope as RS  # noqa: E402
import runtime_regression as RR  # noqa: E402
sys.path.insert(0, str(HERE.parents[2] / 'remake-core' / 'scripts'))
import verify_native_zip as VNZ  # noqa: E402

PNG_UUID = '5b2c0c34-1111-4aaa-8bbb-0123456789ab'
HOME_PNG_UUID = '7c3d1d45-2222-4ccc-9ddd-0123456789cd'
MP3_UUID = '0df071ca-3df4-4116-a43e-832cc2fb51de'
SPRITE_JSON = json.dumps([1, ['abc'], [], [['cc.SpriteFrame', ['content'], 1]], [[0, 0, 1, 3]], [[0, 'sf', {}]]])
PREFAB_JSON = json.dumps([1, [], [], [['cc.Node', ['_name'], 1], ['cc.Prefab', ['data'], 1], ['cc.Button', ['x'], 1]],
                          [[0, 0, 1, 3]], [[0, 'home']]])
TABLE_JSON = json.dumps([1, 0, 0, [['cc.JsonAsset', ['_name', 'json'], 1]], [[0, 0, 1, 3]], [[0, 'unlock', {}]]])
AUDIO_JSON = json.dumps([1, 0, 0, [['cc.AudioClip', ['_name', '_native'], 1]], [[0, 0, 1, 3]], [[0, 'bgm', '.mp3']]])
ADAPTER = {'home': "window.__home === true", 'request': 'game.ad()', 'state': 'game.state()'}


def package(**changes):
    files = {
        'game.js': b"require('./adapter-min.js'); tt.createRewardedVideoAd({adUnitId: 'x'});",
        'game.json': b'{"deviceOrientation": "portrait", "subpackages": [{"name": "resources", "root": "subpackages/resources/"}]}',
        'project.config.json': b'{"appid": "tt0000000000000000"}',
        'adapter-min.js': b'/* adapter */',
        'assets/main/index.js': b'cc._RF.push(module, "main"); /* game code */',
        'assets/main/config.json': b'{"name": "main", "uuids": []}',
        'assets/main/native/7c/%s.png' % HOME_PNG_UUID: b'\x89PNG home',
        'subpackages/resources/config.json': b'{"name": "resources"}',
        'subpackages/resources/import/5b/%s.json' % PNG_UUID: SPRITE_JSON.encode(),
        'subpackages/resources/import/02/02fcf9b0c.json': PREFAB_JSON.encode(),
        'subpackages/resources/import/29/2910f707-34e8-4d9a-a179-88107c934f8e.json': TABLE_JSON.encode(),
        'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'\x89PNG button v1',
        'subpackages/game-audio/config.json': b'{"name": "game-audio"}',
        'subpackages/game-audio/import/0d/%s.json' % MP3_UUID: AUDIO_JSON.encode(),
        'subpackages/game-audio/native/0d/%s.mp3' % MP3_UUID: b'ID3 bgm v1',
    }
    files.update(changes)
    return {k: v for k, v in files.items() if v is not None}


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.out = self.root / '出包'
        self.out.mkdir()
        self.adapter = self.root / 'ad-regression.json'
        self.adapter.write_text(json.dumps(ADAPTER), encoding='utf-8')
        env = mock.patch.dict(os.environ, {AD.ENV_ADAPTER: ''})
        env.start()
        self.addCleanup(env.stop)

    def official(self, files, name='Game_v015.zip', before_home=('resources',), **record):
        """Write `files` as a ZIP with an official writer receipt and the regression record, plus 最新.txt."""
        path = self.out / name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for n in sorted(files):
                z.writestr(n, files[n])
        file_sha = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
        zip_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        catalog = RR.load_suites()
        names = RR.required_suites(files, str(self.adapter), catalog)
        adapter_sha = hashlib.sha256(self.adapter.read_bytes()).hexdigest()
        ad = {'status': 'passed', 'passed': True, 'tool_sha256': AD.tool_digest(), 'adapter_sha256': adapter_sha,
              'seconds': 75.0, 'warnings': [], 'cases': ['complete', 'cancel']}
        rt = {'status': 'passed', 'passed': True, 'tool_sha256': RR.tool_digest(catalog), 'adapter_sha256': adapter_sha,
              'seconds': 700.0, 'warnings': ['button_sweep: old warning', 'save_restart: kept warning'],
              'required': names, 'engine': '2.x', 'policy': 'new', 'board': 'localize',
              'suites': [{'suite': n, 'passed': True} for n in names],
              'startup_measured': {'MiB': 3.1, 'beforeHome': list(before_home)} if before_home is not None else None}
        rt.update(record.pop('runtime', {}))
        ad.update(record.pop('ad', {}))
        regressions = {'schema': RS.REUSE_SCHEMA, 'rewarded_ad_regression': ad, 'runtime_regression': rt}
        finalize = {'kind': 'finalize-native', 'blocks': [], 'policy': 'new', 'policy_override': False, 'files_after': {}}
        receipt = VNZ.make_receipt('build_checked_zip', path, zip_sha, file_sha, {'blocks': [], 'warnings': []},
                                   'localize', {'regressions': regressions}, finalize=finalize)
        VNZ.receipt_path(path).write_text(json.dumps(receipt, ensure_ascii=False), encoding='utf-8')
        (self.out / RS.LATEST).write_text('%s（写包入口自动写，每次出包更新；不要手改）\n上传 TikTok 用这个：%s\nsha256：%s\n'
                                          '大小：%d 字节\n' % (RS.LATEST_MARK, path, zip_sha, path.stat().st_size),
                                          encoding='utf-8')
        return path, names

    def plan(self, old, new, **kw):
        return RS.plan(old, new, str(self.adapter), kw.get('policy'), kw.get('board', 'localize'))


class WhatChanged(Base):
    def test_kinds_of_files(self):
        self.assertEqual(RS.kinds_of('assets/main/index.js', b''), {'code'})
        self.assertEqual(RS.kinds_of('game.json', b'{}'), {'config'})
        self.assertEqual(RS.kinds_of('subpackages/resources/config.json', b'{}'), {'config'})
        self.assertEqual(RS.kinds_of('a/b/native/0d/x.mp3', b''), {'audio'})
        self.assertEqual(RS.kinds_of('a/b/native/0d/x.png', b''), {'image'})
        self.assertEqual(RS.kinds_of('a/b/native/0d/x.ttf', b''), {'font'})
        self.assertEqual(RS.kinds_of('a/b/import/5b/x.json', SPRITE_JSON.encode()), {'image'})
        self.assertEqual(RS.kinds_of('a/b/import/0d/x.json', AUDIO_JSON.encode()), {'audio'})
        self.assertEqual(RS.kinds_of('a/b/import/02/x.json', PREFAB_JSON.encode()), {'structure'})
        self.assertEqual(RS.kinds_of('a/b/import/29/x.json', TABLE_JSON.encode()), {'data'})
        self.assertEqual(RS.kinds_of('a/b/import/02/x.json', b'{"type":"cc.Texture2D","data":"0,1"}'), {'image'})
        self.assertEqual(RS.kinds_of('a/b/import/02/x.json', b'not json'), {'structure'})
        self.assertEqual(RS.kinds_of('a/b/import/02/x.cconb', b'\0'), {'structure'})
        self.assertEqual(RS.kinds_of('src/settings.json', b'{}'), {'data'})

    def test_md5_suffix_is_the_same_file(self):
        old = {'assets/main/native/5b/%s.abcde.png' % PNG_UUID: b'v1'}
        new = {'assets/main/native/5b/%s.12f45.png' % PNG_UUID: b'v2'}
        d = RS.diff(old, new)
        self.assertEqual(d['changed'], ['assets/main/native/5b/%s.png' % PNG_UUID])
        self.assertEqual(d['added'], [])
        self.assertEqual(set(d['kinds']), {'image'})
        self.assertEqual(d['bundles'], ['main'])


class Plans(Base):
    def test_revive_picture_change_reruns_ad_return(self):
        self.adapter.write_text(json.dumps({**ADAPTER, 'ad_entries': [{'role': 'revive'}]}), encoding='utf-8')
        old, names = self.official(package(), before_home=('internal',))
        new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'\x89PNG revived board'})
        plan = self.plan(old, new)
        self.assertTrue(plan['reuse'], plan['why'])
        self.assertIn('ad_outcome', names)
        self.assertIn('ad_outcome', plan['rerun'])

    def test_picture_in_a_later_bundle_reruns_only_the_visual_suites(self):
        old, names = self.official(package(), before_home=('internal',))
        new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'\x89PNG button v2'})
        p = self.plan(old, new)
        self.assertTrue(p['reuse'], p['why'])
        self.assertEqual(p['ad'], 'reuse')
        self.assertEqual(p['rerun'], [n for n in names if n in RS.VISUAL])
        for suite in ('startup', 'network', 'save_restart', 'resume_play', 'frame_rate', 'popin'):
            if suite in names:
                self.assertIn(suite, p['reused'], suite)
        self.assertEqual(sorted(p['rerun'] + p['reused']), sorted(names))
        self.assertIn('startup', names)

    def test_picture_in_a_bundle_before_home_also_reruns_startup(self):
        old, names = self.official(package(), before_home=('resources',))
        new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'\x89PNG button v2'})
        p = self.plan(old, new)
        self.assertTrue(p['reuse'], p['why'])
        self.assertIn('startup', p['rerun'])
        self.assertIn('network', p['rerun'])
        self.assertEqual(p['startup_hit'], ['resources'])

    def test_main_bundle_counts_as_before_home(self):
        old, _ = self.official(package(), before_home=())
        p = self.plan(old, package(**{'assets/main/native/7c/%s.png' % HOME_PNG_UUID: b'\x89PNG home v2'}))
        self.assertTrue(p['reuse'], p['why'])
        self.assertIn('startup', p['rerun'])

    def test_no_measurement_means_every_bundle_is_before_home(self):
        old, _ = self.official(package(), before_home=None)
        p = self.plan(old, package(**{'subpackages/game-audio/native/0d/%s.mp3' % MP3_UUID: b'ID3 bgm v2'}))
        self.assertTrue(p['reuse'], p['why'])
        self.assertIn('startup', p['rerun'])

    def test_sound_reruns_layout_state_only(self):
        old, names = self.official(package(), before_home=('resources',))
        p = self.plan(old, package(**{'subpackages/game-audio/native/0d/%s.mp3' % MP3_UUID: b'ID3 bgm v2'}))
        self.assertTrue(p['reuse'], p['why'])
        self.assertEqual(p['rerun'], [n for n in names if n == 'layout_state'])
        self.assertNotIn('button_sweep', p['rerun'])

    def test_nothing_changed_reuses_everything(self):
        files = package()
        old, names = self.official(files)
        p = self.plan(old, files)
        self.assertTrue(p['reuse'], p['why'])
        self.assertEqual(p['rerun'], [])
        self.assertEqual(p['reused'], names)

    def test_code_settings_structure_and_data_require_precise_scope(self):
        old, _ = self.official(package())
        for label, change in (
                ('code', {'assets/main/index.js': b'cc._RF.push(module, "main"); /* fixed */'}),
                ('config', {'subpackages/resources/config.json': b'{"name": "resources", "paths": {}}'}),
                ('config', {'game.json': b'{"deviceOrientation": "landscape"}'}),
                ('structure', {'subpackages/resources/import/02/02fcf9b0c.json': PREFAB_JSON.replace('home', 'x').encode()}),
                ('data', {'subpackages/resources/import/29/2910f707-34e8-4d9a-a179-88107c934f8e.json':
                          TABLE_JSON.replace('unlock', 'unlock2').encode()})):
            p = self.plan(old, package(**change))
            self.assertFalse(p['reuse'], label)
            self.assertIn(label, p['why'], label)
            self.assertIn('scope_required', p['why'])

    def test_adapter_tool_policy_and_board_must_match(self):
        new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'v2'})
        old, _ = self.official(package(), ad={'tool_sha256': '0' * 64})
        self.assertIn('rewarded-ad regression tool differs', self.plan(old, new)['why'])
        old, _ = self.official(package(), name='b.zip', runtime={'tool_sha256': '0' * 64})
        self.assertIn('runtime regression tools differ', self.plan(old, new)['why'])
        old, _ = self.official(package(), name='c.zip', runtime={'policy': 'legacy'})
        self.assertIn('checked as a legacy game', self.plan(old, new)['why'])
        old, _ = self.official(package(), name='d.zip')
        self.assertIn('board differs', RS.plan(old, new, str(self.adapter), None, 'remake')['why'])
        self.adapter.write_text(json.dumps(dict(ADAPTER, home='window.__home === 1')), encoding='utf-8')
        self.assertIn('adapter differs', self.plan(old, new)['why'])

    def test_required_suites_must_match_and_all_have_passed(self):
        new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'v2'})
        old, names = self.official(package(), runtime={'required': ['startup']})
        self.assertIn('suites this package needs differ', self.plan(old, new)['why'])
        old, names = self.official(package(), name='e.zip')
        receipt = VNZ.receipt_path(old)
        doc = json.loads(receipt.read_text(encoding='utf-8'))
        doc['regressions']['runtime_regression']['suites'][0]['passed'] = False
        receipt.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
        self.assertIn('every required suite passed', self.plan(old, new)['why'])

    def test_unofficial_or_failed_old_package_runs_everything(self):
        path = self.out / 'hand.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for n, b in package().items():
                z.writestr(n, b)
        p = self.plan(path, package())
        self.assertFalse(p['reuse'])
        self.assertIn('not official', p['why'])
        old, _ = self.official(package(), name='f.zip', ad={'status': 'failed'})
        self.assertIn('did not pass', self.plan(old, package())['why'])
        bad = self.out / 'broken.zip'
        bad.write_bytes(b'PK not a zip')
        p = self.plan(bad, package())
        self.assertFalse(p['reuse'])
        self.assertIn('rework plan failed', p['why'])

    def test_after_dependencies_join_the_rerun(self):
        catalog = {'resume_play': {'after': ['button_sweep']}, 'ad_outcome': {'after': ['button_sweep', 'resume_play']},
                   'button_sweep': {}}
        names = ['button_sweep', 'resume_play', 'ad_outcome']
        self.assertEqual(RS._closure(names, {'ad_outcome'}, catalog), set(names))
        self.assertEqual(RS._closure(names, {'button_sweep'}, catalog), {'button_sweep'})


class FindTheOldPackage(Base):
    def test_auto_reads_latest_and_finds_a_renamed_copy(self):
        old, _ = self.official(package())
        self.assertEqual(RS.resolve('auto', self.out / 'Game_v016.zip')[0], old)
        renamed = self.out / '割草小能手.zip'
        old.rename(renamed)
        self.assertEqual(RS.resolve('auto', self.out / 'Game_v016.zip')[0], renamed.resolve())
        (self.out / RS.OLD_FOLDER).mkdir()
        moved = self.out / RS.OLD_FOLDER / 'Game_v015.zip'
        renamed.rename(moved)
        self.assertEqual(RS.resolve(str(self.out), None)[0], moved)
        self.assertEqual(RS.resolve(str(moved), None)[0], moved)

    def test_no_latest_none_and_missing(self):
        self.assertIsNone(RS.resolve('auto', self.out / 'x.zip')[0])
        self.assertIsNone(RS.resolve('none', self.out / 'x.zip')[0])
        self.assertIsNone(RS.resolve(None, self.out / 'x.zip')[0])
        self.assertIsNone(RS.resolve(str(self.root / 'nope.zip'))[0])
        (self.out / RS.LATEST).write_text('hand written\n', encoding='utf-8')
        self.assertIsNone(RS.resolve('auto', self.out / 'x.zip')[0])


class Gates(Base):
    def setUp(self):
        super().setUp()
        self.old, self.names = self.official(package(), before_home=('internal',))
        self.new = package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'\x89PNG button v2'})
        self.p = self.plan(self.old, self.new)
        self.assertTrue(self.p['reuse'], self.p['why'])
        self.folder = self.root / 'staged'
        for n, b in self.new.items():
            (self.folder / n).parent.mkdir(parents=True, exist_ok=True)
            (self.folder / n).write_bytes(b)

    def fake_run(self, calls):
        def run(folder, adapter, names, policy=None, board=None, **kw):
            calls.append(list(names))
            catalog = RR.load_suites()
            return {'id': 'runtime_regression', 'passed': True, 'engine': '2.x', 'required': list(names),
                    'suites': [{'suite': n, 'passed': True, 'seconds': 30.0, 'problems': [], 'warnings': [],
                                'cases': ['c']} for n in names],
                    'not_run': [], 'board': board, 'problems': [], 'policy': 'new', 'policy_reason': 'x',
                    'startup_measured': {'MiB': 3.2, 'beforeHome': ['internal']}, 'warnings': ['layout_state: new'],
                    'not_run': [{'suite': n, 'reason': 'applies, but not selected in this run (--suites)'}
                                for n in RR.required_suites(self.new, str(self.adapter)) if n not in names] +
                               [{'suite': 'trial_link', 'reason': 'no trial link given'}],
                    'tool_sha256': RR.tool_digest(catalog),
                    'adapter_sha256': hashlib.sha256(Path(adapter).read_bytes()).hexdigest(), 'seconds': 90.0}
        return run

    def test_runtime_gate_runs_only_the_rerun_suites(self):
        calls = []
        with mock.patch.object(RR, 'run', self.fake_run(calls)):
            out = C.runtime_gate(self.new, self.folder, str(self.adapter), policy='new', board='localize', rework=self.p)
        self.assertEqual(calls, [self.p['rerun']])
        self.assertTrue(out['passed'])
        self.assertEqual([r['suite'] for r in out['suites']], self.names)
        reused = {r['suite']: r for r in out['suites'] if r.get('reused_from')}
        self.assertEqual(sorted(reused), sorted(self.p['reused']))
        self.assertEqual(Path(reused['startup']['reused_from']), VNZ.receipt_path(self.old))
        self.assertIn('save_restart: kept warning', out['warnings'])
        self.assertNotIn('button_sweep: old warning', out['warnings'])     # button_sweep ran again
        self.assertIn('layout_state: new', out['warnings'])
        self.assertEqual(out['rework']['reran'], self.p['rerun'])
        self.assertEqual([r['suite'] for r in out['not_run']], ['trial_link'])     # reused suites are not "not run"

    def test_ad_gate_keeps_the_old_pass(self):
        with mock.patch.object(AD, 'run', side_effect=AssertionError('must not run')):
            out = C.rewarded_ad_gate(self.new, self.folder, str(self.adapter), rework=self.p)
        self.assertEqual(out['status'], 'passed')
        self.assertTrue(out['reused_from'])

    def test_nothing_to_rerun_opens_no_browser(self):
        p = self.plan(self.old, package())
        with mock.patch.object(RR, 'run', side_effect=AssertionError('must not run')):
            out = C.runtime_gate(package(), self.folder, str(self.adapter), policy='new', board='localize', rework=p)
        self.assertTrue(all(r.get('reused_from') for r in out['suites']))

    def test_writer_reuse_keeps_original_case_evidence(self):
        p = self.plan(self.old, package())
        original = p['records']['runtime_regression']['suites'][0]
        original.update(cases=[{'case':'original-observation','passed':True}],
                        evidence='original-runtime.json',seconds=12.5)
        with mock.patch.object(RR,'run',side_effect=AssertionError('must not run')):
            out=C.runtime_gate(package(),self.folder,str(self.adapter),policy='new',board='localize',rework=p)
        kept=next(r for r in out['suites'] if r['suite']==original['suite'])
        self.assertEqual(kept['cases'],original['cases'])
        self.assertEqual(kept['original_seconds'],12.5)
        ad=C.rewarded_ad_gate(self.new,self.folder,str(self.adapter),rework=self.p)
        record=C.regression_record(ad,out)
        row=next(r for r in record['runtime_regression']['suites'] if r['suite']==original['suite'])
        self.assertEqual(row['cases'],original['cases'])
        self.assertEqual(row['evidence'],'original-runtime.json')

    def test_receipt_with_incomplete_legacy_cases_cannot_be_delivered(self):
        calls = []
        with mock.patch.object(RR, 'run', self.fake_run(calls)):
            rt = C.runtime_gate(self.new, self.folder, str(self.adapter), policy='new', board='localize', rework=self.p)
        ad = C.rewarded_ad_gate(self.new, self.folder, str(self.adapter), rework=self.p)
        record = C.regression_record(ad, rt)
        self.assertIsNotNone(record)
        self.assertEqual(record['runtime_regression']['rework']['reused'], self.p['reused'])
        self.assertTrue(record['rewarded_ad_regression']['reused_from'])
        self.assertTrue(any(r.get('reused_from') for r in record['runtime_regression']['suites']))
        receipt = self.root / 'new.zip.receipt.json'
        receipt.write_text(json.dumps({'regressions': record}), encoding='utf-8')
        reuse = C.reusable_regressions(receipt, self.new, str(self.adapter), 'new')
        self.assertFalse(reuse['reused'])
        self.assertIn('every required case', reuse['why'])

    def test_writer_regressions_requires_plan_even_with_rework_of(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(RR, 'run') as runtime, mock.patch.object(AD, 'run') as ads:
            for prior in (str(self.old), None):
                out = C.writer_regressions(self.new, self.folder, str(self.adapter),
                                           policy='new', board='localize', rework_of=prior)
                self.assertTrue(out['blocked'])
                self.assertEqual(out['status'], 'scope_required')
            runtime.assert_not_called()
            ads.assert_not_called()

    def test_a_failing_rerun_still_refuses(self):
        def failing(folder, adapter, names, **kw):
            error = RR.RuntimeRefused('runtime regression failed: button_sweep: PLAY does not react')
            error.summary = {'id': 'runtime_regression', 'passed': False, 'required': list(names)}
            raise error
        with mock.patch.object(RR, 'run', failing), \
                mock.patch.object(C, 'verify_regression_scope', return_value={'plan_sha256': 'test-plan'}), \
                mock.patch.object(AD, 'run', return_value={'passed': True}):
            out = C.writer_regressions(self.new, self.folder, str(self.adapter), policy='new', board='localize',
                                       rework_of=str(self.old))
        self.assertTrue(out['blocked'])
        self.assertIn('PLAY does not react', ' '.join(out['problems']))


class HandChecks(Base):
    def test_a_picture_change_never_rechecks_sound(self):
        """Saul 2026-11-04「比如我修改了贴图，之后出包甚至又要检查一遍音频，这种情况不要发生」."""
        old, _ = self.official(package())
        p = self.plan(old, package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'v2'}))
        todo, skip = RS.ai_checks(p)
        self.assertIn('音效和音乐', skip)
        self.assertIn('存档关掉重开', skip)
        self.assertIn('广告流程（看完、取消、失败、超时）', skip)
        self.assertTrue(any('页面美工' in t for t in todo))
        self.assertTrue(any('图片复核' in t for t in todo))
        self.assertFalse(any('音效、音乐' in t for t in todo))

    def test_a_sound_change_rechecks_sound_not_pages(self):
        old, _ = self.official(package())
        p = self.plan(old, package(**{'subpackages/game-audio/native/0d/%s.mp3' % MP3_UUID: b'ID3 v2'}))
        todo, skip = RS.ai_checks(p)
        self.assertTrue(any('音效、音乐' in t for t in todo))
        self.assertIn('其余页面的美工', skip)
        self.assertNotIn('音效和音乐', skip)

    def test_a_code_change_checks_the_feature_only(self):
        old, _ = self.official(package())
        p = self.plan(old, package(**{'assets/main/index.js': b'/* fixed */'}))
        todo, skip = RS.ai_checks(p)
        self.assertTrue(any('这次改的功能就地验证' in t for t in todo))
        self.assertTrue(skip and '只有这次改的代码就是它们时才查' in skip[0])

    def run_cli(self, project):
        new_zip = self.root / 'new.zip'
        with zipfile.ZipFile(new_zip, 'w') as z:
            for n, b in package(**{'subpackages/resources/native/5b/%s.png' % PNG_UUID: b'v2'}).items():
                z.writestr(n, b)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = RS.main(['--old', str(self.out), '--new', str(new_zip), '--project', str(project),
                            '--ad-regression', str(self.adapter), '--board', 'localize'])
        self.assertEqual(code, 0)
        records = sorted((project / 'docs' / 'checks').glob('rework-*.json'))
        self.assertEqual(len(records), 1)
        return buf.getvalue(), json.loads(records[0].read_text(encoding='utf-8'))

    def test_describe_and_record_list_the_pages_that_use_the_picture(self):
        self.official(package(), before_home=('internal',))
        project = self.root / 'project'
        (project / 'assets' / 'ui').mkdir(parents=True)
        (project / 'assets' / 'ui' / 'btn_play.png.meta').write_text(json.dumps(
            {'uuid': PNG_UUID, 'subMetas': {'btn_play': {'uuid': '9e8d7c6b-3333-4eee-8fff-0123456789ef'}}}), encoding='utf-8')
        (project / 'assets' / 'ui' / 'Home.prefab').write_text(
            '[{"__type__":"cc.Sprite","_spriteFrame":{"__uuid__":"9e8d7c6b-3333-4eee-8fff-0123456789ef"}}]', encoding='utf-8')
        (project / 'assets' / 'ui' / 'Shop.prefab').write_text('[{"__type__":"cc.Node"}]', encoding='utf-8')
        text, doc = self.run_cli(project)
        for phrase in ('返工范围｜和上一个交付包 Game_v015.zip 比', '- 改了：图片 1 个', '用到改动的页面：assets/ui/Home.prefab',
                       '写包时重跑：', '沿用上一个包的通过结果：激励广告回归 10 例', '不用再查的：音效和音乐'):
            self.assertIn(phrase, text)
        self.assertNotIn('Shop.prefab', text)
        self.assertTrue(doc['reuse'])
        self.assertEqual(doc['pages'], ['assets/ui/Home.prefab'])
        self.assertIn('音效和音乐', doc['ai']['skip'])
        self.assertNotIn('records', doc)

    def test_a_picture_loaded_by_path_from_code_is_listed(self):
        self.official(package(), before_home=('internal',))
        project = self.root / 'project'
        (project / 'assets' / 'resources' / 'art').mkdir(parents=True)
        (project / 'assets' / 'resources' / 'art' / 'icon.png.meta').write_text(json.dumps({'uuid': PNG_UUID}),
                                                                               encoding='utf-8')
        (project / 'assets' / 'scripts').mkdir()
        (project / 'assets' / 'scripts' / 'Shop.ts').write_text("cc.resources.load('art/icon', cc.SpriteFrame, cb);",
                                                                encoding='utf-8')
        (project / 'assets' / 'scripts' / 'Other.ts').write_text("cc.resources.load('art/iconic', cb);", encoding='utf-8')
        text, doc = self.run_cli(project)
        self.assertIn('用到改动的页面：assets/scripts/Shop.ts（代码按路径加载）', text)
        self.assertNotIn('Other.ts', text)                 # 'art/iconic' is another picture
        self.assertEqual(doc['pages'], ['assets/scripts/Shop.ts（代码按路径加载）'])

    def test_cli_usage_errors(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(RS.main(['--old', 'auto', '--native', str(self.root), '--project', str(self.root)]), 2)
            self.assertEqual(RS.main(['--old', str(self.out), '--native', str(self.root), '--project', str(self.root)]),
                             2)                                                                   # no 最新.txt


PNG = 'subpackages/resources/native/5b/%s.png' % PNG_UUID
RAW_ADAPTER = b'/* adapter as Cocos Creator wrote it */'


class PreviewBeforePackaging(Base):
    """--native: the writers finalize the build folder before anything else (kit parts, App ID, PNG compression), so
    a raw build differs from the delivered package in its code; the preview finalizes a copy first (11-05: 割草小能手
    raw build vs its v015 ZIP = 3 code files and 66 PNGs)."""

    def build(self, **changes):
        folder = self.root / 'build' / 'bytedance'
        for name, data in package(**dict({'adapter-min.js': RAW_ADAPTER}, **changes)).items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(data)
        return folder

    def project(self, board='localize'):
        project = self.root / 'project'
        (project / '.tiktok-kit').mkdir(parents=True)
        (project / '.tiktok-kit' / 'finalize-source.json').write_text(json.dumps(
            {'kind': 'finalize-source', 'board': board, 'options': {'keep_webp_exception': ''}, 'blocks': []}),
            encoding='utf-8')
        return project

    def fake_finalize(self, calls, blocks=()):
        def finalize_native(native, project=None, board=None, app_id=None, options=None, **kw):
            calls.append({'native': Path(native), 'project': project, 'board': board, 'app_id': app_id,
                          'options': options})
            (Path(native) / 'adapter-min.js').write_bytes(b'/* adapter */')      # the kit adapter, as delivered
            return {'blocks': list(blocks), 'warnings': []}
        return finalize_native

    def run_preview(self, folder, project, calls, blocks=()):
        import tiktok_finalize
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(tiktok_finalize, 'finalize_native', self.fake_finalize(calls, blocks)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = RS.main(['--old', str(self.out), '--native', str(folder), '--project', str(project),
                            '--ad-regression', str(self.adapter), '--json'])
        return code, out.getvalue(), err.getvalue()

    def test_preview_finalizes_a_copy_and_plans_like_the_writer(self):
        self.official(package())
        folder, project, calls = self.build(**{PNG: b'\x89PNG button v2'}), self.project(), []
        code, out, _ = self.run_preview(folder, project, calls)
        self.assertEqual(code, 0)
        doc = json.loads(out[:out.rindex('}') + 1])
        self.assertTrue(doc['reuse'], doc['why'])                  # the raw adapter is not read as a code change
        self.assertEqual(list(doc['changes']['kinds']), ['image'])
        self.assertEqual(doc['changes']['changed'], 1)
        self.assertEqual(doc['preview'], 'native, finalized on a copy')
        call = calls[0]
        self.assertNotEqual(call['native'].resolve(), folder.resolve())
        self.assertFalse(call['native'].exists())                   # the copy is gone again
        self.assertEqual((folder / 'adapter-min.js').read_bytes(), RAW_ADAPTER)   # the build folder is not touched
        self.assertEqual((call['board'], call['app_id'], call['options']),
                         ('localize', 'tt0000000000000000', {'png_cache_read_only': True}))
        self.assertEqual(len(list((project / 'docs' / 'checks').glob('rework-*.json'))), 1)

    def test_without_finalize_the_raw_build_would_read_as_a_code_change(self):
        old, _ = self.official(package())
        folder = self.build(**{PNG: b'\x89PNG button v2'})
        p = self.plan(old, RS.native_files(folder))
        self.assertFalse(p['reuse'])
        self.assertIn('code', p['changes']['kinds'])

    def test_a_finalize_refusal_is_reported_not_planned(self):
        self.official(package())
        calls = []
        code, _, err = self.run_preview(self.build(), self.project(), calls,
                                        blocks=[{'id': 'K_engine_unknown', 'message': 'not a Cocos build'}])
        self.assertEqual(code, 2)
        self.assertIn('tiktok_finalize refused a copy of the build', err)
        self.assertIn('K_engine_unknown', err)

    def test_native_preview_needs_the_project(self):
        self.official(package())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(RS.main(['--old', str(self.out), '--native', str(self.build())]), 2)
        self.assertIn('--native 要带 --project', err.getvalue())

    def test_board_comes_from_the_source_record_unless_given(self):
        project = self.project(board='remake')
        self.assertEqual(RS.source_settings(project)[0], 'remake')
        self.assertEqual(RS.source_settings(project, 'localize')[0], 'localize')
        self.assertEqual(RS.source_settings(self.root / 'nowhere'), (None, {}))

    def test_build_files_leave_out_junk_like_the_writer(self):
        folder = self.root / 'b'
        for name in ('game.js', '.DS_Store', 'Thumbs.db', '._game.js', '__MACOSX/x.js', 'assets/main/.DS_Store'):
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(b'x')
        self.assertEqual(list(RS.native_files(folder)), ['game.js'])


class WriterRecord(Base):
    """The writers write docs/checks/rework-<time>.json themselves after publishing (the AI cannot forget it)."""

    def test_record_for_writer(self):
        old, _ = self.official(package())
        p = RS.public(self.plan(old, package(**{PNG: b'v2'})))
        project = self.root / 'project'
        project.mkdir()
        rec = RS.record_for_writer(project, p)
        doc = json.loads(Path(rec['path']).read_text(encoding='utf-8'))
        self.assertTrue(doc['reuse'])
        self.assertIn('音效和音乐', doc['ai']['skip'])
        self.assertEqual(rec['pages'], [])
        self.assertTrue(RS.writer_lines(p, rec)[-1].startswith('（返工记录：'))
        self.assertIsNone(RS.record_for_writer(project, None))
        self.assertIsNone(RS.record_for_writer(None, p))
        self.assertIsNone(RS.record_for_writer(project, {'reuse': False, 'why': 'no 最新.txt'}))   # nothing compared
        not_a_folder = self.root / 'file'
        not_a_folder.write_text('x', encoding='utf-8')
        rec = RS.record_for_writer(not_a_folder, p)                  # never raises: the ZIP is already published
        self.assertIn('error', rec)
        self.assertIn('包已经出好', RS.writer_lines(p, rec)[-1])

    def test_both_writers_write_it_after_publishing(self):
        import inspect
        import build_checked_zip as B
        body = inspect.getsource(B.build)
        self.assertLess(body.index('delivery_folder.tidy('),
                        body.index("rework_scope.record_for_writer(project, result.get('rework'))"))
        self.assertIn("rework_scope.writer_lines(rework, result.get('rework_record'))", inspect.getsource(B.main))
        sys.path.insert(0, str(HERE.parents[2] / 'remake-core' / 'scripts'))
        import make_tiktok_zip as M
        body = inspect.getsource(M.main)
        record = "rework_record(a.project, regressions.get('rework'))"
        self.assertLess(body.index('delivery_folder.tidy(out'), body.index(record))
        self.assertLess(body.index(record), body.index('report_path.write_text('))
        self.assertIn("rework_lines(regressions['rework'], rework_rec)", body)


class StandardLibraryOnly(unittest.TestCase):
    def test_imports(self):
        import ast
        tree = ast.parse((HERE / 'rework_scope.py').read_text(encoding='utf-8'))
        names = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertLessEqual(names, {'argparse', 'hashlib', 'importlib', 'json', 'os', 're', 'shutil', 'sys', 'tempfile', 'time',
                                     'zipfile', 'datetime', 'pathlib', 'ad_regression', 'runtime_regression',
                                     'verify_native_zip', 'tiktok_finalize', 'tiktok_finalize_steps'})


if __name__ == '__main__':
    unittest.main()
