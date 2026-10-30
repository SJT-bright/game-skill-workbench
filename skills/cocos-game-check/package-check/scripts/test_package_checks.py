#!/usr/bin/env python3
"""Behavioral calibration: defect fixtures + real missing-engine regression."""
import copy
import os
import shutil
import sys
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from check_package import check, write_archive, SHARED
from build_checked_zip import build
from audit_upload_startup import audit_files


# v7.5: check() runs the mandatory runtime regression (Ego browser) on every package with game.js. These fixtures
# test the static checks, so the runtime gate is patched (as test_ad_regression patches rewarded_ad_gate); its
# fail-closed behaviour is tested in test_ad_regression.RuntimeGateFailClosed and test_runtime_regression.py.
def runtime_patch():
    return patch('check_package.runtime_gate',
                 return_value={'id': 'runtime_regression', 'status': 'patched_in_unit_test'})


_RUNTIME = runtime_patch()


def setUpModule():
    _RUNTIME.start()


def tearDownModule():
    _RUNTIME.stop()


sys.path.insert(0, str(SHARED))
import tiktok_finalize as F  # noqa: E402
import test_tiktok_finalize as H  # noqa: E402
from test_tiktok_touch_coordinates import ENGINE_245  # noqa: E402

# v7.7: the fixture is a NEW game (not on the legacy list) as the v7.7 writers expect it: numeric App ID, a project
# with a current source record (K5), and a build that tiktok_finalize has already processed once. The two writers
# run finalize again on it (0 changes).
# Engine: the shared fixture uses an engine version outside startup24's list (DECISIONS 13:57: such builds keep their
# own main.js and get the touch and storage load lines in game.js), to keep the v7.6 static fixture: the static
# resource tests below use a loader-free main.js as in v7.6. (Since W-G2 the static expansion also reads the kit
# main.js's loadScript(settings.jsList) as script_files; see remake-core/scripts/test_kit_main_resources.py.) The
# 2.4.15 kit-main.js path is covered by KitMainFixture below.
ENGINE_OWN_MAIN = '2.4.3'
ENGINE_KIT_MAIN = '2.4.15'
APP = H.APP                                       # 7683427172773644296
OTHER_APP = '7000000000000000001'                 # numeric, but not this game's App ID
KIT = SHARED.parent / 'assets' / 'platform-kit'


def kit_module(name):
    """The kit's own 2.4 module text; PlatformConfig with this game's gameId / normalLevelCoins (K_platform_config)."""
    text = (KIT / 'assets' / 'tiktok-platform' / (name + '.js')).read_text(encoding='utf-8')
    if name == 'PlatformConfig':
        text = text.replace("gameId: 'change-me'", "gameId: 'fixture'").replace('normalLevelCoins: 0,', 'normalLevelCoins: 12,')
    return text


def kit_bundle(*names, extra=''):
    """A Cocos 2.4 bundle index.js holding the named kit modules (as Creator writes assets/main/index.js)."""
    return (''.join("cc._RF.push(module, 'u%d', '%s');\n%s\ncc._RF.pop();\n" % (i, n, kit_module(n))
                    for i, n in enumerate(names)) + extra).encode()


def raw_fixture(engine=ENGINE_OWN_MAIN):
    """The editor build before tiktok_finalize: game.js with the __globalAdapter.adaptEngine() anchor, an engine stub
    carrying the real 2.4.5+ touch converter shape (the touch-coordinate probe runs it), the game's modules loaded
    after './main' (game.js -> child.js -> leaf.js; root JS loaded before './main' is an own startup layer that
    finalize takes out), and the growth missions only through the kit TikTokMissionService / MissionFlow modules
    (G1 present, no G1k). With its own main.js the game logs in itself (K2_login)."""
    login = '' if engine == ENGINE_KIT_MAIN else "cc._RF.push(module, 'u9', 'Login');\ntt.login({});\ncc._RF.pop();\n"
    return {'game.js':b"\"use strict\";\nrequire('./adapter');\n__globalAdapter.init();\nrequire('cocos/cocos2d-js-min.js');\n"
                      b"__globalAdapter.adaptEngine();\nrequire('./src/settings');\nrequire('./main');\nrequire('./child');\nwindow.boot();\n",
            'adapter.js':b'exports.ok=true;', 'cocos/cocos2d-js-min.js':b'var ENGINE_VERSION="%s";' % engine.encode()+ENGINE_245,
            'main.js':b"window.boot=function(){};",
            'child.js':b"require('./leaf');",
            'leaf.js':b'exports.ok=true;',
            'game.json':b'{"subpackages":[{"name":"resources","root":"subpackages/resources"}]}',
            'project.config.json':b'{"appid":"%s"}' % APP.encode(),
            'src/settings.js':b'window._CCSettings={subpackages:["resources"],jsList:[],launchScene:"db://assets/start.fire"};',
            'assets/main/config.json':b'{"scenes":{"db://assets/start.fire":0},"importBase":"import","packs":{"aa123":[0]}}',
            'assets/main/import/aa/aa123.json':b'[]',
            'assets/main/index.js':kit_bundle('PlatformConfig', 'TikTokMissionService', 'MissionFlow', extra=login),
            'subpackages/resources/game.js':b'// resources entry\n'}


_FINALIZED = {}


def fixture(engine=ENGINE_OWN_MAIN):
    """raw_fixture(engine) after one tiktok_finalize.finalize_native run (computed once, copied per call)."""
    if engine not in _FINALIZED:
        tmp = Path(tempfile.mkdtemp(prefix='pkg-fixture-', dir=os.environ.get('KIROCREW_SCRATCH') or None))
        try:
            native = tmp / 'native'
            for name, data in raw_fixture(engine).items():
                f = native / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
            record = F.finalize_native(native, None, 'remake', APP)
            if record['blocks'] or record['policy'] != 'new':
                raise AssertionError('fixture finalize: %s %s' % (record['policy'], record['blocks']))
            _FINALIZED[engine] = F._native_files(native)
        finally:
            shutil.rmtree(tmp, True)
    return dict(_FINALIZED[engine])


def finalize_project(project):
    """Make `project` a 2.4.15 project with the kit PlatformConfig values set and a current source record
    (tiktok_finalize source, board remake). Leaves the package issue log alone. Returns the project."""
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    H.project24(project)
    (project / 'assets' / 'tiktok-platform' / 'PlatformConfig.js').write_text(kit_module('PlatformConfig'), encoding='utf-8')
    record = F.finalize_source(project, 'remake')
    if record['blocks']:
        raise AssertionError('fixture source finalize: %s' % record['blocks'])
    return project


def fixture_project(project):
    """finalize_project() plus a fresh package issue log (package_issue_gate.initialize)."""
    from package_issue_gate import initialize
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    initialize(project)
    return finalize_project(project)


class PackageChecks(unittest.TestCase):
    def setUp(self):
        self.files = fixture()
        config=json.loads(self.files['assets/main/config.json'])
        config.update(name='main', paths={'0':['runtime-fixture',0]}, types=['cc.JsonAsset'])
        self.files['assets/main/config.json']=json.dumps(config).encode()
        self.temp = tempfile.TemporaryDirectory(prefix='package gate tests ')
        self.root = Path(self.temp.name)
        self.project=fixture_project(self.root/"project")
    def build_with_resources(self, native, app_id, out, report=None):
        manifest=self.root/'runtime-resources.json'
        manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'runtime-fixture','type':'cc.JsonAsset'}]}))
        # Runtime gate has its own rejection tests; isolate archive/resource tests here.
        from unittest.mock import patch
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True}):
            return build(native,app_id,out,report,resource_manifest=manifest,project=self.project)
    def test_missing_runtime_manifest_refused_without_zip(self):
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'manifest required'):build(self.native(),APP,out)
        self.assertFalse(out.exists())
    def test_runtime_resource_missing_refused_without_zip(self):
        manifest=self.root/'bad-resources.json'
        manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'not-in-catalog','type':'cc.JsonAsset'}]}))
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'resources missing'):build(self.native(),APP,out,resource_manifest=manifest,project=self.project)
        self.assertFalse(out.exists())
    def tearDown(self):
        self.temp.cleanup()
    def refuse(self):
        self.assertFalse(audit_files(self.files)['passed'])
    def archive(self):
        path=self.root/'input.zip';write_archive(path,self.files);return path
    def native(self):
        path=self.root/'native';path.mkdir()
        for name,data in self.files.items():
            f=path/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        return path
    def test_normal(self):
        self.assertTrue(check(self.archive(),APP)['startup_dependency_check']['passed'])
    def test_webp_runtime_requirement_is_not_static_pass(self):
        self.files['subpackages/resources/native/ab/ab.webp'] = b'fixture-webp'
        # v7.5 G4_webp_probe: WebP art needs a startup decode probe of a main-package .webp (static gate only;
        # the runtime requirement below still has to be met by real decoding evidence).
        self.files['probe/webp-probe.webp'] = b'fixture-webp'
        # The probe must be a root file; tt['createImage'] keeps this root file free of a literal tt.X.
        self.files['webp-probe.js'] = (b"module.exports=function(done){var i=tt['createImage']();i.onload=function(){"
                                       b"cc.sys.capabilities.webp=i.width>0;done()};i.src='probe/webp-probe.webp'};")
        self.files['game.js'] = b"require('./webp-probe');" + self.files['game.js']
        # v7.7: a NEW game ships no .webp (K_S_webp) unless --keep-webp-exception installed the kit probe part;
        # a legacy game keeps its WebP art and its own probe (G4), which is what this runtime requirement is for.
        with self.assertRaisesRegex(ValueError, 'K_S_webp'):
            check(self.archive(), APP)
        result = check(self.archive(), APP, policy='legacy')
        row = result['runtime_requirements'][0]
        self.assertEqual(row['id'], 'webp_decode_capability')
        self.assertEqual(row['status'], 'requires_runtime_evidence')
        self.assertEqual(row['resource_count'], 2)          # the art file and the probe's own sample
        self.assertIn('decoder_timeout_not_enabled', row['cases'])
        self.assertEqual(result['runtime_execution'], 'not_executed_by_static_package_checker')
    def test_no_webp_no_unrelated_runtime_requirement(self):
        self.assertEqual(check(self.archive(), APP)['runtime_requirements'], [])
    def test_missing_engine(self):
        del self.files['cocos/cocos2d-js-min.js'];self.refuse()
    def test_empty_engine(self):
        self.files['cocos/cocos2d-js-min.js']=b'';self.refuse()
    def test_case_mismatch(self):
        self.files['cocos/Cocos2d-js-min.js']=self.files.pop('cocos/cocos2d-js-min.js');self.refuse()
    def test_transitive(self):
        del self.files['leaf.js'];self.refuse()
    def test_parent_relative(self):
        self.files['child.js']=b"require('./nested/m');";self.files['nested/m.js']=b"require('../leaf');"
        self.assertTrue(audit_files(self.files)['passed'])
    def test_module_cycle(self):
        self.files['leaf.js']=b"require('./child');";self.assertTrue(audit_files(self.files)['passed'])
    def test_internal_bundle_require(self):
        self.files['child.js']=b"({PlatformConfig:[function(require,module,exports){require('InternalModule');},{}]});require('./leaf');"
        self.assertTrue(audit_files(self.files)['passed'])
        del self.files['leaf.js'];self.refuse()
    def test_comment_not_dependency(self):
        self.files['child.js']=b"// require('missing')\n/*require('missing2')*/require('./leaf');"
        self.assertTrue(audit_files(self.files)['passed'])
    def test_jslist_missing(self):
        self.files['src/settings.js']=b'window._CCSettings={jsList:["missing.js"]};';self.refuse()
    def test_launch_registration(self):
        self.files['assets/main/config.json']=b'{"scenes":{}}';self.refuse()
    def test_pack_missing(self):
        del self.files['assets/main/import/aa/aa123.json'];self.refuse()
    def test_subpackage_missing(self):
        del self.files['subpackages/resources/game.js'];self.refuse()
    def test_subpackage_undeclared(self):
        self.files['game.json']=b'{"subpackages":[]}';self.refuse()
    def test_custom_extra_subpackage(self):
        self.files['game.json']=b'{"subpackages":[{"name":"resources","root":"subpackages/resources"},{"name":"custom","root":"art"}]}';self.files['art/game.js']=b''
        self.assertTrue(audit_files(self.files)['passed'])
    def test_duplicate_subpackage(self):
        self.files['game.json']=b'{"subpackages":[{"name":"resources","root":"art"},{"name":"resources","root":"art"}]}';self.refuse()
    def test_wrong_app_id(self):
        with self.assertRaisesRegex(ValueError,'App ID'):check(self.archive(),OTHER_APP)
    def test_path_traversal(self):
        self.files['../escape.js']=b'bad'
        with self.assertRaisesRegex(ValueError,'Unsafe'):check(self.archive(),APP)
    def test_main_limit(self):
        self.files['too-large.bin']=b'x'*4_000_001
        with self.assertRaisesRegex(ValueError,'main package'):check(self.archive(),APP)
    def test_source_file_refused(self):
        self.files['code.ts']=b'let x=1;'
        with self.assertRaisesRegex(ValueError,'source-project'):check(self.archive(),APP)
    def test_native_byte_mismatch(self):
        native=self.native();archive=self.archive();(native/'leaf.js').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'differs'):check(archive,APP,native)
    def test_writer_refuses_missing_engine_without_output(self):
        # v7.7: tiktok_finalize runs before the startup check and already refuses a build without an engine
        del self.files['cocos/cocos2d-js-min.js'];out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'K_engine_unknown: not a Cocos 2.4'):self.build_with_resources(self.native(),APP,out)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
    def test_writer_refuses_missing_startup_dependency_without_output(self):
        del self.files['leaf.js'];out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'missing startup'):self.build_with_resources(self.native(),APP,out)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
    def test_writer_refuses_wrong_id_without_output(self):
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'App ID'):self.build_with_resources(self.native(),'wrong',out)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
    def test_writer_publishes_and_preserves_existing(self):
        native=self.native();out=self.root/'delivery.zip';result=self.build_with_resources(native,APP,out)
        self.assertTrue(result['expected_tree_exact']);before=out.read_bytes()
        with self.assertRaises(ValueError):self.build_with_resources(native,APP,out)
        self.assertEqual(before,out.read_bytes())
    def test_dynamic_not_claimed_verified(self):
        self.files['child.js']=b'require(variable);'
        result=audit_files(self.files);self.assertTrue(result['dynamic_requires']);self.assertTrue(result['warnings'])
    def test_forwarded_require_iife(self):
        self.files['child.js']=b"(function(require){require('./missing-external.js');})(require);";self.refuse()
    def test_regex_not_require(self):
        self.files['child.js']=b"var p=/require('ghost')/;require('./leaf');"
        self.assertTrue(audit_files(self.files)['passed'])
    def test_division_does_not_hide_require(self):
        self.files['child.js']=b"var a=1/2;require('./missing');var b=3/4;";self.refuse()
    def test_template_expression_require(self):
        self.files['child.js']=b"var p=`hello${require('./missing')}`;";self.refuse()
    def test_json_parse_failure(self):
        self.files['child.js']=b"require('./data.json');";self.files['data.json']=b'{broken';self.refuse()
    def test_js_syntax_failure(self):
        self.files['leaf.js']=b'function {';self.refuse()
    def test_unknown_local_require_is_explicit(self):
        self.files['child.js']=b"(function(require){require('virtual');})(customResolver);"
        self.assertTrue(audit_files(self.files)['dynamic_requires'])
    def test_report_failure_no_final_zip(self):
        parent=self.root/'report-parent';parent.write_bytes(b'not a directory');out=self.root/'delivery.zip'
        with self.assertRaises(OSError):self.build_with_resources(self.native(),APP,out,parent/'result.json')
        self.assertFalse(out.exists())
    def test_report_success_bound_to_output(self):
        out=self.root/'delivery.zip';report=self.root/'evidence.json';self.build_with_resources(self.native(),APP,out,report)
        result=json.loads(report.read_text());self.assertEqual(result['archive'],str(out.resolve()))


    def test_compressible_main_oversize_refused_before_archive(self):
        self.files['large.bin'] = b'0' * 4_000_001
        native = self.native(); out = self.root/'delivery.zip'
        from unittest.mock import patch
        with patch('build_checked_zip.write_archive') as writer:
            with self.assertRaisesRegex(ValueError, 'main package'):
                self.build_with_resources(native, APP, out)
            writer.assert_not_called()
        self.assertFalse(out.exists())
    def test_large_normal_subpackage_allowed(self):
        self.files['subpackages/resources/large.bin'] = b'0' * 4_000_001
        out=self.root/'delivery.zip'
        result=self.build_with_resources(self.native(),APP,out)
        self.assertLess(result['main_bytes'],4_000_000)
        self.assertGreater(result['uncompressed_total_bytes'],4_000_000)
    def test_large_independent_subpackage_refused(self):
        game=json.loads(self.files['game.json']);game['subpackages'][0]['independent']=True
        self.files['game.json']=json.dumps(game).encode()
        self.files['subpackages/resources/large.bin']=b'0'*4_000_001
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'(?i)independent subpackage'):
            self.build_with_resources(self.native(),APP,out)
        self.assertFalse(out.exists())
    def test_total_oversize_refused_before_archive(self):
        self.files['subpackages/resources/large.bin']=b'0'*30_000_001
        out=self.root/'delivery.zip'
        from unittest.mock import patch
        with patch('build_checked_zip.write_archive') as writer:
            with self.assertRaisesRegex(ValueError,'total'):
                self.build_with_resources(self.native(),APP,out)
            writer.assert_not_called()
        self.assertFalse(out.exists())


class KitMainFixture(unittest.TestCase):
    """v7.7, 2.4.15 new game: finalize installs the kit main.js (with webp-decode-probe.js next to it), which loads
    the touch and storage parts and logs in itself; game.js gets no touch / storage line."""
    def setUp(self):
        self.files = fixture(ENGINE_KIT_MAIN)
        self.temp = tempfile.TemporaryDirectory(prefix='kit main fixture ')
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def archive(self):
        path = self.root/'input.zip'; write_archive(path, self.files); return path
    def test_kit_main_installed_and_static_check_passes(self):
        import tiktok_finalize_steps as T
        self.assertEqual(T.sha256(self.files['main.js']), T.kit_main_current(T.load_manifest()))
        for part in ('touch-coordinates.js', 'storage-guard.js', 'webp-decode-probe.js'):
            self.assertIn(part, self.files)
        self.assertNotIn(b'tiktok-kit:touch24:', self.files['game.js'])
        result = check(self.archive(), APP)
        self.assertTrue(result['startup_dependency_check']['passed'])
        self.assertEqual(result['policy'], 'new')
        self.assertEqual(result['runtime_requirements'], [])
    def test_raw_editor_build_refused_by_kit_gates(self):
        # the same game before finalize: no kit main.js, no touch / storage parts
        files = raw_fixture(ENGINE_KIT_MAIN)
        path = self.root/'raw.zip'; write_archive(path, files)
        with self.assertRaisesRegex(ValueError, 'K1_kit_bytes'):
            check(path, APP)
    def test_kit_main_not_loaded_refused(self):
        self.files['game.js'] = self.files['game.js'].replace(b"require('./main');", b'')
        with self.assertRaisesRegex(ValueError, 'K2_kit_wiring'):
            check(self.archive(), APP)


if __name__=='__main__':
    unittest.main(verbosity=2)
