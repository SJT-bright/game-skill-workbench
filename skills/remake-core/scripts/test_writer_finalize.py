#!/usr/bin/env python3
"""v7.7 W-D1: the two package writers call tiktok_finalize, and the gates wired around it.

Synthetic fixtures only (never a game pass); real packages are in the W-D1 evidence. Each gate has a bad case that is
blocked and a good case that passes:
  writers   make_tiktok_zip.main() and build_checked_zip.build() run finalize_native (its adapter step is the only
            adapter_fix.apply call) and hand its policy and record to the package gates; a stale or missing source
            record (K5) and a refused finalize refuse BEFORE the build folder changes; build_checked_zip refuses
            without --project; the writers never pass --policy
  receipt   verify_native_zip receipt schema 2: official only with a passed finalize record matching the ZIP
  policy    PackageView.policy; check_package.check() given only a ZIP judges new / legacy from the artifact
  A1 / G1k  rewarded-ad and growth-mission SDK calls outside the kit: block for a new game, warning for a legacy one
  K3        3.x engine files (cocos-js/) are not scanned for a second touch layer
  delivery  prepare_delivery's record carries KIT_PARTS_PHONE_RETEST and the finalize parts table
Run: python3 test_writer_finalize.py
"""
import contextlib
import hashlib
import inspect
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
CHECK = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CHECK))
import package_gates as G  # noqa: E402
from package_gates import kit_parts  # noqa: E402
import tiktok_finalize as F  # noqa: E402
import tiktok_finalize_steps as T  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
import verify_native_zip as V  # noqa: E402
import make_tiktok_zip as M  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402
import build_checked_zip as B  # noqa: E402
import check_package as C  # noqa: E402
import prepare_delivery as D  # noqa: E402

APP = H.APP
SCENE = '1b2c3d4e-0000-4000-8000-00000000abcd'
KIT = T.KIT_DIR


def sha(data):
    return hashlib.sha256(data).hexdigest()


def kit_in_sync():
    """The real KIT_MANIFEST.json. These tests prove the WIRING, not the kit bytes (W-A1's manifest check and
    test_tiktok_finalize prove those), so a kit file another station is still editing gets its current hash here;
    when the kit is consistent this is the real manifest unchanged."""
    data = H.manifest_data()
    for spec in [p.get('file') for p in data.get('parts', {}).values()] + list(data.get('files', {}).values()):
        if isinstance(spec, dict) and spec.get('src') and (KIT / spec['src']).is_file():
            now = sha((KIT / spec['src']).read_bytes())
            if spec.get('sha256') != now:
                spec['previous_sha256'] = list(spec.get('previous_sha256') or []) + [spec.get('sha256')]
                spec['sha256'] = now
    for rel, spec in data.get('files', {}).items():
        if isinstance(spec, dict) and not spec.get('src') and (KIT / rel).is_file():
            spec['sha256'] = sha((KIT / rel).read_bytes())
    return T.Manifest(data, KIT)


class KitInSync(unittest.TestCase):
    def setUp(self):
        manifest = kit_in_sync()
        patcher = mock.patch.object(T, 'load_manifest', lambda path=None: manifest)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.d = H.tmpdir(self)

    def project(self, name='p', source=True, config=True):
        p = H.project24(self.d / name)
        if config:                                   # the kit PlatformConfig.js with this game's values set
            (p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(kit_config(), encoding='utf-8')
        if source:
            rec = F.finalize_source(p, 'remake')
            self.assertEqual(rec['blocks'], [], rec['blocks'])
        return p

    def native(self, name='b'):
        b = H.build24(self.d / name)
        (b / 'assets' / 'main').mkdir(parents=True)
        (b / 'assets' / 'main' / 'config.json').write_text(json.dumps({'scenes': {'db://assets/Main.fire': SCENE}}))
        return b


def kit_config(game_id='fixture', coins=12, plugin=False):
    """Kit PlatformConfig (2.4 module, or the 3.x plugin script) with gameId / normalLevelCoins set."""
    text = (KIT / ('plugins-3x/PlatformConfig.plugin.js' if plugin else 'assets/tiktok-platform/PlatformConfig.js')
            ).read_text(encoding='utf-8')
    text = text.replace("gameId: 'change-me'", "gameId: '%s'" % game_id)
    return text.replace('normalLevelCoins: 0,', 'normalLevelCoins: %s,' % coins)


def stop_native_problems():
    calls = []

    def spy(native, board=None, policy=None, context=None):
        calls.append({'native': native, 'board': board, 'policy': policy, 'context': context})
        return ['STOP-AFTER-FINALIZE'], {}, {}
    return calls, spy


def run_make_zip(argv):
    err = io.StringIO()
    with mock.patch.object(sys, 'argv', ['make_tiktok_zip.py'] + [str(a) for a in argv]), \
            contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = M.main()
    return code, err.getvalue()


class Writers(KitInSync):
    def zip_args(self, b, p):
        review = self.d / 'review.json'
        review.write_text('{}')
        return ['--native', b, '--app-id', APP, '--out', self.d / 'out.zip', '--project', p, '--web', b,
                '--build-tag', 't', '--review', review, '--board', 'remake']

    def test_build_checked_zip_calls_finalize_and_gates_get_its_record(self):
        p, b = self.project(), self.native()
        calls, spy = stop_native_problems()
        from package_gates import adapter_fix
        with mock.patch.object(M, 'native_problems', spy), \
                mock.patch.object(adapter_fix, 'apply', wraps=adapter_fix.apply) as fix:
            with self.assertRaisesRegex(ValueError, 'STOP-AFTER-FINALIZE'):
                B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p, board='remake')
        self.assertEqual(fix.call_count, 1)                    # only through finalize's adapter step
        self.assertEqual(len(calls), 1)
        ctx = calls[0]['context']
        self.assertEqual(calls[0]['policy'], 'new')
        self.assertTrue(ctx['writer'])
        self.assertEqual(ctx['project'], p)
        self.assertEqual(ctx['finalize_record']['kind'], 'finalize-native')
        self.assertEqual(ctx['finalize_record']['blocks'], [])
        self.assertEqual(ctx['finalize_record']['source_record']['source_sha256'], F.source_sha256(p))
        self.assertTrue((b / 'touch-coordinates.js').is_file())
        self.assertTrue((b / 'storage-guard.js').is_file())
        self.assertFalse((self.d / 'out.zip').exists())

    def test_make_tiktok_zip_calls_finalize_and_gates_get_its_record(self):
        p, b = self.project(), self.native()
        calls, spy = stop_native_problems()
        import audit_native_resource_paths
        with mock.patch.object(M, 'native_problems', spy), \
                mock.patch.object(audit_native_resource_paths, 'audit', return_value={'status': 'pass', 'errors': []}):
            code, err = run_make_zip(self.zip_args(b, p))
        self.assertEqual(code, 1)
        self.assertIn('STOP-AFTER-FINALIZE', err)
        self.assertEqual(calls[0]['policy'], 'new')
        self.assertEqual(calls[0]['context']['finalize_record']['kind'], 'finalize-native')
        self.assertTrue((b / 'touch-coordinates.js').is_file())
        self.assertFalse((self.d / 'out.zip').exists())

    def test_stale_source_record_refused_and_build_untouched(self):
        p, b = self.project(), self.native()
        (p / 'assets' / 'later.js').write_text('// changed after the source phase\n')
        before = H.tree_sha(b)
        with self.assertRaisesRegex(ValueError, 'K5_source_finalized: project changed after the source phase'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p)
        code, err = run_make_zip(self.zip_args(b, p))
        self.assertEqual(code, 1)
        self.assertIn('K5_source_finalized: project changed after the source phase', err)
        self.assertEqual(H.tree_sha(b), before)                # refused before finalize touched the build
        self.assertFalse((self.d / 'out.zip').exists())

    def test_source_record_of_another_kit_version_refused(self):
        p, b = self.project(), self.native()
        rec = json.loads((p / F.SOURCE_RECORD).read_text())
        rec['kit_version'] = '1.9'
        (p / F.SOURCE_RECORD).write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError, 'source record is for kit 1.9'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p)

    def test_missing_source_record_refused(self):
        p, b = self.project(source=False), self.native()
        with self.assertRaisesRegex(ValueError, 'K5_source_finalized: source record .* missing'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p)
        code, err = run_make_zip(self.zip_args(b, p))
        self.assertEqual(code, 1)
        self.assertIn('finalize-source.json missing', err)

    def test_build_checked_zip_without_project_refused(self):
        b = self.native()
        before = H.tree_sha(b)
        with self.assertRaisesRegex(ValueError, 'K5_source_finalized: no --project given'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json')
        self.assertEqual(H.tree_sha(b), before)
        cli = subprocess.run([sys.executable, '-B', str(CHECK / 'build_checked_zip.py'), '--native', str(b),
                              '--expected-app-id', APP, '--out', str(self.d / 'cli.zip')],
                             capture_output=True, text=True)
        self.assertEqual(cli.returncode, 2)
        self.assertIn('--project', cli.stderr)

    def test_refused_finalize_refuses_the_writer(self):
        p, b = self.project(), self.native()
        other = '7000000000000000001'                           # PlatformConfig.js says APP
        with self.assertRaisesRegex(ValueError, 'tiktok_finalize: K_appid_mismatch'):
            B.build(b, other, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p)
        self.assertFalse((self.d / 'out.zip').exists())

    def test_good_case_finalized_build_passes_kit_gates(self):
        p, b = self.project(), self.native()
        record, context, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertEqual(problems, [])
        out = G.run(F._native_files(b), b, 'remake', policy=record['policy'], context=context)
        kit_ids = {f['id'] for f in out['blocks'] if f['id'].startswith('K')}
        self.assertEqual(kit_ids, set(), out['blocks'])
        self.assertEqual(out['policy'], 'new')
        again, _, problems = M.finalize_for_writer(b, p, 'remake', APP)    # second run: nothing changes
        self.assertEqual(problems, [])
        self.assertEqual(sum(len(s['changed']) for s in again['steps']), 0)

    def test_bad_case_edited_after_finalize_blocked_by_k4(self):
        p, b = self.project(), self.native()
        record, context, problems = M.finalize_for_writer(b, p, 'remake', APP)
        self.assertEqual(problems, [])
        (b / 'touch-coordinates.js').write_text('/* edited after finalize */\n')
        out = G.run(F._native_files(b), b, 'remake', policy=record['policy'], context=context)
        self.assertIn('K4_finalize_ran', {f['id'] for f in out['blocks']})

    def test_writers_never_pass_policy_and_never_call_adapter_fix_themselves(self):
        body = inspect.getsource(M.finalize_for_writer)
        self.assertIn('F.finalize_native(native, project, board, app_id, manifest=kit, options=options)', body)
        for source in (inspect.getsource(M.main), inspect.getsource(B.build)):
            self.assertNotIn('adapter_fix.apply(', source)
            self.assertIn('finalize_for_writer(', source)
            self.assertNotIn('policy=\'new\'', source)


def write_zip(path, files):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in sorted(files.items()):
            z.writestr(name, data)
    return path


class Receipts(KitInSync):
    def receipt(self, finalize):
        files = {'game.js': b'//g', 'touch-coordinates.js': b'//t'}
        z = write_zip(self.d / 'g.zip', files)
        digests = {k: sha(v) for k, v in files.items()}
        stamp = V.make_receipt('build_checked_zip', z, sha(z.read_bytes()), digests,
                               {'blocks': [], 'warnings': [], 'gates': ['kit_parts']}, 'remake', finalize=finalize)
        V.receipt_path(z).write_text(json.dumps(stamp))
        return V.receipt_status(z, sha(z.read_bytes()), digests), stamp

    def record(self, **over):
        rec = {'kind': 'finalize-native', 'kit_version': '2.0', 'policy': 'new', 'decision': {'reason': 'r'},
               'policy_override': False, 'blocks': [], 'warnings': [], 'steps': [],
               'files_after': {'touch-coordinates.js': sha(b'//t'), 'native-load-guard.js': None}, 'table': []}
        rec.update(over)
        return rec

    def test_passed_finalize_is_official(self):
        status, stamp = self.receipt(self.record())
        self.assertEqual(status['entry'], 'official', status)
        self.assertEqual(stamp['schema'], 2)
        self.assertEqual(stamp['finalize']['policy'], 'new')
        self.assertEqual(status['receipt_policy'], 'new')

    def test_receipt_without_finalize_is_unofficial(self):
        status, _ = self.receipt(None)
        self.assertEqual(status['entry'], 'unofficial')
        self.assertIn('no finalize record', status['entry_reason'])

    def test_refused_or_test_only_or_mismatching_finalize_is_unofficial(self):
        for rec, why in ((self.record(blocks=[{'id': 'K1_kit_bytes', 'message': 'x'}]), 'refused finalize'),
                         (self.record(policy_override=True), '--policy'),
                         (self.record(files_after={'touch-coordinates.js': sha(b'other')}), 'other bytes'),
                         (self.record(files_after={'game.js': None}), 'moved game.js away')):
            status, _ = self.receipt(rec)
            self.assertEqual(status['entry'], 'unofficial', why)
            self.assertIn(why, status['entry_reason'])
            for p in self.d.glob('g.zip*'):
                p.unlink()


class Policy(KitInSync):
    def test_package_view_policy(self):
        self.assertEqual(G.PackageView({}, policy='legacy').get_policy(), ('legacy', 'given by the caller'))
        with self.assertRaises(ValueError):
            G.PackageView({}, policy='old')
        with self.assertRaises(ValueError):
            G.PackageView({}, context={'policy_override': 'legacy'})
        view = G.PackageView({'game.js': b'//'})
        self.assertEqual(view.policy, None)
        self.assertEqual(view.get_policy()[0], 'new')
        self.assertIn('judged from the package', view.get_policy()[1])
        out = G.run({'game.js': b'//'}, modules=('network',), policy='legacy')
        self.assertEqual((out['policy'], out['policy_reason']), ('legacy', 'given by the caller'))

    def legacy_list(self):
        path = self.d / 'LEGACY_GAMES.json'
        path.write_text(json.dumps({'frozen': True, 'games': [{'name': 'Fixture', 'folder': 'J/Fixture',
                                                               'scene_uuids': [SCENE]}]}))
        return mock.patch.object(P, 'LEGACY', path)

    def check_zip(self, z, policy=None):
        seen = []
        real = G.run

        def spy(*a, **k):
            out = real(*a, **k)
            seen.append(out)
            return out
        with mock.patch.object(G, 'run', spy), \
                mock.patch.object(C, 'runtime_gate', return_value={'status': 'patched'}), \
                mock.patch.object(C, 'rewarded_ad_gate', return_value={'status': 'patched'}):
            try:
                C.check(z, policy=policy)
                error = ''
            except ValueError as e:
                error = str(e)
        return seen[0], error

    def test_check_package_given_only_a_zip_judges_policy_from_the_artifact(self):
        b = self.native()
        z = write_zip(self.d / 'raw.zip', C.native_files(b))
        out, error = self.check_zip(z)                          # not listed -> new -> kit parts missing blocks
        self.assertEqual(out['policy'], 'new')
        self.assertTrue(out['policy_reason'].startswith('judged from the package'))
        self.assertIn('K1_kit_bytes', error)
        with self.legacy_list():
            out, error = self.check_zip(z)                      # its scene uuid is on the list -> legacy
            self.assertEqual(out['policy'], 'legacy')
            self.assertIn('on the legacy list', out['policy_reason'])
            self.assertNotIn('K1_kit_bytes', error)
            out, error = self.check_zip(z, policy='new')        # test-only --policy new still blocks it
            self.assertEqual(out['policy'], 'new')
            self.assertIn('K1_kit_bytes', error)

    def test_check_package_cli_policy_is_test_only_flag(self):
        help_text = subprocess.run([sys.executable, '-B', str(CHECK / 'check_package.py'), '--help'],
                                   capture_output=True, text=True).stdout
        self.assertIn('tests and calibration only', help_text)
        for writer in (CHECK / 'build_checked_zip.py', HERE / 'make_tiktok_zip.py', CHECK / 'prepare_delivery.py'):
            self.assertNotIn("'--policy'", writer.read_text(encoding='utf-8'))


def bundle(*modules):
    """A Cocos 2.4 bundle index.js: [(module name, body)]."""
    return ''.join("cc._RF.push(module, 'u%d', '%s');\n%s\ncc._RF.pop();\n" % (i, name, body)
                   for i, (name, body) in enumerate(modules)).encode()


def kit_text(name, plugin=False):
    if plugin:
        return (KIT / 'plugins-3x' / (name + '.plugin.js')).read_text(encoding='utf-8')
    return (KIT / 'assets' / 'tiktok-platform' / (name + '.js')).read_text(encoding='utf-8')


def ids(files, policy, module):
    out = G.run(files, None, 'remake', modules=(module,), policy=policy)
    return {f['id']: f['level'] for f in out['blocks'] + out['warnings']}


class OutsideKitGates(unittest.TestCase):
    OWN_AD = "var ad = tt.createRewardedVideoAd({adUnitId: 'x'}); ad.show();"
    OWN_GROWTH = "tt.addShortcut({success: function () {}});"

    def test_a1_blocks_new_warns_legacy(self):
        files = {'assets/main/index.js': bundle(('AdHelper', self.OWN_AD))}
        self.assertEqual(ids(files, 'new', 'ads_static').get('A1_rewarded_outside_kit'), 'block')
        self.assertEqual(ids(files, 'legacy', 'ads_static').get('A1_rewarded_outside_kit'), 'warn')

    def test_a1_kit_module_and_3x_plugin_pass(self):
        files = {'assets/main/index.js': bundle(('RewardedService', kit_text('RewardedService')))}
        self.assertNotIn('A1_rewarded_outside_kit', ids(files, 'new', 'ads_static'))
        files = {'src/RewardedService.plugin.js': kit_text('RewardedService', plugin=True).encode()}
        self.assertNotIn('A1_rewarded_outside_kit', ids(files, 'new', 'ads_static'))
        files = {'src/RewardedService.plugin.js': self.OWN_AD.encode()}      # the name alone is not the kit
        self.assertEqual(ids(files, 'new', 'ads_static').get('A1_rewarded_outside_kit'), 'block')

    def test_g1k_blocks_new_warns_legacy(self):
        for body in (self.OWN_GROWTH, "tt['startEntranceMission']({});", 'api.getShortcutMissionReward.call(api, {});',
                     'sdk.checkShortcut({})'):
            files = {'assets/main/index.js': bundle(('Growth', body))}
            self.assertEqual(ids(files, 'new', 'mission').get('G1k_growth_outside_kit'), 'block', body)
            self.assertEqual(ids(files, 'legacy', 'mission').get('G1k_growth_outside_kit'), 'warn', body)

    def test_g1k_kit_modules_definitions_and_strings_pass(self):
        files = {'assets/main/index.js': bundle(('MissionFlow', kit_text('MissionFlow')),
                                                ('TikTokMissionService', kit_text('TikTokMissionService')),
                                                ('Names', "var x = {addShortcut: function () {}}; "
                                                          "var s = 'getEntranceMissionReward';"))}
        self.assertNotIn('G1k_growth_outside_kit', ids(files, 'new', 'mission'))
        files = {'src/MissionFlow.plugin.js': kit_text('MissionFlow', plugin=True).encode(),
                 'src/TikTokMissionService.plugin.js': kit_text('TikTokMissionService', plugin=True).encode()}
        self.assertNotIn('G1k_growth_outside_kit', ids(files, 'new', 'mission'))
        files = {'assets/main/index.js': bundle(('TikTokMissionService', self.OWN_GROWTH))}   # kit name, own code
        self.assertEqual(ids(files, 'new', 'mission').get('G1k_growth_outside_kit'), 'block')

    def test_g1k_policy_judged_from_package_when_not_given(self):
        files = {'assets/main/index.js': bundle(('Growth', self.OWN_GROWTH))}
        out = G.run(files, None, None, modules=('mission',))
        self.assertEqual(out['policy'], 'new')
        self.assertIn('G1k_growth_outside_kit', {f['id'] for f in out['blocks']})


class K3SkipsEngine(KitInSync):
    def test_cocos_js_not_scanned_root_file_is(self):
        b = H.build3x(self.d / 'b3')
        rec = F.finalize_native(b, None, 'remake', APP, policy='new',
                                steps=('startup', 'touch', 'storage', 'login', 'appid', 'structure'))
        self.assertEqual(rec['blocks'], [], rec['blocks'])
        marker = 'marlow-touch'
        self.assertTrue(any(marker in m for m in T.load_manifest().part('touch3x')['own_markers']))
        files = F._native_files(b)
        files['cocos-js/extra.js'] = b'/* marlow-touch */ e.onTouchStart = function () {};'
        view = G.PackageView(files, policy='new')
        self.assertNotIn('K3_single_layer', {f['id'] for f in kit_parts.check(view) if f['level'] == 'block'})
        files['extra-touch.js'] = files.pop('cocos-js/extra.js')
        view = G.PackageView(files, policy='new')
        self.assertIn('K3_single_layer', {f['id'] for f in kit_parts.check(view) if f['level'] == 'block'})


class W_D4_Requests(KitInSync):
    """W-D4 requests 1, 3, 5 and the PlatformConfig template gate (parent, 2026-10-29)."""

    def test_req1_mangled_engine_name_is_recognised(self):
        import audit_upload_startup as A
        source = inspect.getsource(A)
        self.assertIn("_ccprivate\\$)?_createCallback", source)
        rx = __import__('re').compile(rb'\.onTouchStart\(this\.(?:_ccprivate\$)?_createCallback\(')
        self.assertTrue(rx.search(b'e.onTouchStart(this._ccprivate$_createCallback("touch-start"))'))
        self.assertTrue(rx.search(b'e.onTouchStart(this._createCallback("touch-start"))'))
        probe = (HERE / 'probe_cocos3_touch_coordinates.cjs').read_text(encoding='utf-8')
        self.assertIn("engine = engine.replace(/_ccprivate\\$_/g, '_');", probe)

    def test_req3_writer_view_uses_finalize_record_policy(self):
        b = self.native()
        legacy = self.d / 'LEGACY_GAMES.json'
        legacy.write_text(json.dumps({'games': [{'name': 'Fixture', 'folder': 'J/Fixture', 'scene_uuids': [SCENE]}]}))
        record = {'kind': 'finalize-native', 'policy': 'new', 'blocks': [], 'files_after': {}}
        with mock.patch.object(P, 'LEGACY', legacy):
            files = F._native_files(b)
            self.assertEqual(G.PackageView(files).get_policy()[0], 'legacy')          # package uuids: listed
            view = G.PackageView(files, context={'writer': True, 'finalize_record': record})
            self.assertEqual(view.get_policy(), ('new', "from this run's finalize record"))
            out = kit_parts.check(view)
            self.assertTrue(any(f['id'] == 'K_policy' and 'policy new' in f['message'] for f in out))
            bare = G.PackageView(files)                     # writer_auto style: attributes set after construction
            bare.writer, bare.finalize_record = True, record
            self.assertTrue(any(f['id'] == 'K_policy' and 'policy new' in f['message'] for f in kit_parts.check(bare)))

    def plugin_build(self):
        b = H.build3x(self.d / 'p3')
        dests = [d for _, d in kit_parts.kit_plugins(T.load_manifest())]
        self.assertEqual(len(dests), 5)
        (b / 'src').mkdir()
        (b / 'src' / 'settings.json').write_text(json.dumps({'plugins': {'jsList': dests}}))
        for dest in dests:
            name = dest.rsplit('/', 1)[-1][:-len('.plugin.js')]
            text = kit_config(plugin=True) if name == 'PlatformConfig' else kit_text(name, plugin=True)
            # Creator 3.8.8 re-wraps a plugin and strips whitespace; the marker and BEGIN / END lines stay
            wrapped = '(function(root){var exports=undefined;(function(){%s})()})(globalThis);' % text
            (b / 'src' / dest).parent.mkdir(parents=True, exist_ok=True)
            (b / 'src' / dest).write_text(wrapped, encoding='utf-8')
        return b, dests

    def plugin_blocks(self, files, policy='new'):
        return [f for f in kit_parts.check(G.PackageView(files, policy=policy)) if f['id'] == 'K1_plugin3x']

    def test_req5_plugins_listed_and_marked_pass(self):
        b, _ = self.plugin_build()
        self.assertEqual(self.plugin_blocks(F._native_files(b)), [])

    def test_req5_missing_jslist_entry_or_marker_blocks(self):
        b, dests = self.plugin_build()
        files = F._native_files(b)
        short = dict(files, **{'src/settings.json': json.dumps({'plugins': {'jsList': dests[1:]}}).encode()})
        found = self.plugin_blocks(short)
        self.assertEqual([f['level'] for f in found], ['block'])
        self.assertIn(dests[0], found[0]['message'])
        name = 'src/' + dests[2]
        for needle in (b'---- END', b'tiktok-kit:plugin3x:'):
            broken = dict(files, **{name: files[name].replace(needle, b'-- gone')})
            self.assertEqual([f['level'] for f in self.plugin_blocks(broken)], ['block'], needle)
        self.assertEqual(self.plugin_blocks(short, 'legacy'), [])            # legacy 3.x games: not required

    def config_findings(self, files, policy='new', **context):
        if not any(n.startswith('cocos-js/') or 'cocos2d-js' in n for n in files):
            files = dict(files, **{'cocos/cocos2d-js-min.js': b'var e;'})     # kit_parts only runs on Cocos builds
        view = G.PackageView(files, policy=policy, context=context or None)
        return [f for f in kit_parts.check(view) if f['id'] == 'K_platform_config']

    def test_platform_config_template_values_block_new_games(self):
        b, dests = self.plugin_build()
        files = F._native_files(b)
        self.assertEqual(self.config_findings(files), [])                    # 3.x plugin with values set: pass
        cfg = 'src/assets/tiktok-platform/PlatformConfig.plugin.js'
        for bad in (files[cfg].replace(b"gameId: 'fixture'", b"gameId: 'change-me'"),
                    files[cfg].replace(b'normalLevelCoins: 12,', b'normalLevelCoins: 0,')):
            found = self.config_findings(dict(files, **{cfg: bad}))
            self.assertEqual([f['level'] for f in found], ['block'])
            self.assertEqual([f['level'] for f in self.config_findings(dict(files, **{cfg: bad}), 'legacy')], ['warn'])
        # 2.4: the kit module inside a bundle (minified spacing)
        good = kit_config().replace(': ', ':')
        self.assertEqual(self.config_findings({'assets/main/index.js': bundle(('PlatformConfig', good))}), [])
        bad = kit_config(coins=0).replace(': ', ':')
        self.assertEqual(len(self.config_findings({'assets/main/index.js': bundle(('PlatformConfig', bad))})), 1)
        own = "var PlatformConfig = {endpoint: 'x'};"                       # a game module that only has the name
        self.assertEqual(self.config_findings({'assets/main/index.js': bundle(('PlatformConfig', own))}), [])

    def test_platform_config_checked_in_the_writer_path(self):
        p, b = self.project(config=False), self.native()           # project keeps H.project24's own PlatformConfig
        (p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(kit_config('change-me', 0))
        F.finalize_source(p, 'remake')
        with self.assertRaisesRegex(ValueError, 'K_platform_config: project assets/tiktok-platform/PlatformConfig.js'):
            B.build(b, APP, self.d / 'out.zip', resource_manifest=self.d / 'r.json', project=p, board='remake')
        self.assertFalse((self.d / 'out.zip').exists())
        p2, b2 = self.project('p2'), self.native('b2')
        record, context, problems = M.finalize_for_writer(b2, p2, 'remake', APP)
        self.assertEqual(problems, [])
        out = G.run(F._native_files(b2), b2, 'remake', policy=record['policy'], context=context)
        self.assertNotIn('K_platform_config', {f['id'] for f in out['blocks']})


class Delivery(KitInSync):
    def test_constant_marked_for_removal(self):
        self.assertEqual(D.KIT_PARTS_PHONE_RETEST, '标准件待真机复测')
        source = (CHECK / 'prepare_delivery.py').read_text(encoding='utf-8')
        self.assertIn('Remove this constant', source)

    def test_delivery_record_carries_retest_line_and_parts_table(self):
        native = self.d / 'native'
        native.mkdir()
        (native / 'game.js').write_text('//g')
        archive = write_zip(self.d / 'Game_v1.zip', {'game.js': b'//g'})
        digests = {'game.js': sha(b'//g')}
        record = {'kind': 'finalize-native', 'kit_version': '2.0', 'policy': 'new', 'decision': {'reason': 'r'},
                  'blocks': [], 'warnings': [], 'steps': [], 'files_after': {},
                  'table': [{'step': 'touch', 'result': '已装', 'changed': 2, 'warnings': 0}]}
        stamp = V.make_receipt('build_checked_zip', archive, sha(archive.read_bytes()), digests,
                               {'blocks': [], 'warnings': [], 'gates': []}, 'remake', finalize=record)
        V.receipt_path(archive).write_text(json.dumps(stamp))
        result = {'sha256': sha(archive.read_bytes()), 'file_sha256': digests, 'runtime_execution': 'x',
                  **V.receipt_status(archive, sha(archive.read_bytes()), digests)}
        self.assertEqual(result['entry'], 'official')
        other_temp = self.d / 'other-temp'
        other_temp.mkdir()
        with mock.patch.object(D, 'check', return_value=result), \
                mock.patch.object(D.package_obligations, 'verify', return_value={'passed': True}), \
                mock.patch.object(D.package_obligations, 'publication_guard',
                                  lambda *a, **k: contextlib.nullcontext()), \
                mock.patch.object(D, 'audit_final_startup', return_value={'passed': True}), \
                mock.patch.object(D.tempfile, 'gettempdir', return_value=str(other_temp)):
            out = D.prepare(archive, native, APP, self.d / 'delivery.json', resource_manifest=self.d / 'r.json')
        self.assertEqual(out['kit_parts_status'], '标准件待真机复测')
        self.assertIn('标准件待真机复测', out['reply_lines'])
        self.assertEqual(out['finalize']['policy'], 'new')
        self.assertIn('| touch | 已装 | 2 | 0 |', out['finalize']['table_markdown'])
        saved = json.loads((self.d / 'delivery.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['kit_parts_status'], '标准件待真机复测')


if __name__ == '__main__':
    unittest.main(verbosity=1)
