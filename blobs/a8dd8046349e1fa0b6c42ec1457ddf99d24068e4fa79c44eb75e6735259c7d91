#!/usr/bin/env python3
"""Behavioral calibration: defect fixtures + real missing-engine regression."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from check_package import check, write_archive, SHARED
from build_checked_zip import build
from audit_upload_startup import audit_files


def fixture():
    return {'game.js':b"require('./adapter');require('cocos/cocos2d-js-min.js');require('./main');require('./src/settings');",
            'adapter.js':b'exports.ok=true;', 'cocos/cocos2d-js-min.js':b'var engine=true;',
            'main.js':b"require('./child');", 'child.js':b'exports.ok=true;',
            'game.json':b'{"subpackages":[{"name":"resources","root":"subpackages/resources"}]}',
            'project.config.json':b'{"appid":"test-target"}',
            'src/settings.js':b'window._CCSettings={subpackages:["resources"],jsList:[],launchScene:"db://assets/start.fire"};',
            'assets/main/config.json':b'{"scenes":{"db://assets/start.fire":0},"importBase":"import","packs":{"aa123":[0]}}',
            'assets/main/import/aa/aa123.json':b'[]',
            'subpackages/resources/game.js':b''}


class PackageChecks(unittest.TestCase):
    def setUp(self):
        self.files = fixture()
        config=json.loads(self.files['assets/main/config.json'])
        config.update(name='main', paths={'0':['runtime-fixture',0]}, types=['cc.JsonAsset'])
        self.files['assets/main/config.json']=json.dumps(config).encode()
        self.temp = tempfile.TemporaryDirectory(prefix='package gate tests ')
        self.root = Path(self.temp.name)
        from package_issue_gate import initialize
        self.project=self.root/"project";self.project.mkdir();initialize(self.project)
    def build_with_resources(self, native, app_id, out, report=None):
        manifest=self.root/'runtime-resources.json'
        manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'runtime-fixture','type':'cc.JsonAsset'}]}))
        # Runtime gate has its own rejection tests; isolate archive/resource tests here.
        from unittest.mock import patch
        with patch('build_checked_zip.audit_final_startup', return_value={'passed': True}):
            return build(native,app_id,out,report,resource_manifest=manifest,project=self.project)
    def test_missing_runtime_manifest_refused_without_zip(self):
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'manifest required'):build(self.native(),'test-target',out)
        self.assertFalse(out.exists())
    def test_runtime_resource_missing_refused_without_zip(self):
        manifest=self.root/'bad-resources.json'
        manifest.write_text(json.dumps({'resources':[{'bundle':'main','path':'not-in-catalog','type':'cc.JsonAsset'}]}))
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'resources missing'):build(self.native(),'test-target',out,resource_manifest=manifest,project=self.project)
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
        self.assertTrue(check(self.archive(),'test-target')['startup_dependency_check']['passed'])
    def test_webp_runtime_requirement_is_not_static_pass(self):
        self.files['subpackages/resources/native/ab/ab.webp'] = b'fixture-webp'
        result = check(self.archive(), 'test-target')
        row = result['runtime_requirements'][0]
        self.assertEqual(row['id'], 'webp_decode_capability')
        self.assertEqual(row['status'], 'requires_runtime_evidence')
        self.assertEqual(row['resource_count'], 1)
        self.assertIn('decoder_timeout_not_enabled', row['cases'])
        self.assertEqual(result['runtime_execution'], 'not_executed_by_static_package_checker')
    def test_no_webp_no_unrelated_runtime_requirement(self):
        self.assertEqual(check(self.archive(), 'test-target')['runtime_requirements'], [])
    def test_missing_engine(self):
        del self.files['cocos/cocos2d-js-min.js'];self.refuse()
    def test_empty_engine(self):
        self.files['cocos/cocos2d-js-min.js']=b'';self.refuse()
    def test_case_mismatch(self):
        self.files['cocos/Cocos2d-js-min.js']=self.files.pop('cocos/cocos2d-js-min.js');self.refuse()
    def test_transitive(self):
        del self.files['child.js'];self.refuse()
    def test_parent_relative(self):
        self.files['main.js']=b"require('./nested/m');";self.files['nested/m.js']=b"require('../child');"
        self.assertTrue(audit_files(self.files)['passed'])
    def test_module_cycle(self):
        self.files['child.js']=b"require('./main');";self.assertTrue(audit_files(self.files)['passed'])
    def test_internal_bundle_require(self):
        self.files['main.js']=b"({PlatformConfig:[function(require,module,exports){require('InternalModule');},{}]});require('./child');"
        self.assertTrue(audit_files(self.files)['passed'])
        del self.files['child.js'];self.refuse()
    def test_comment_not_dependency(self):
        self.files['main.js']=b"// require('missing')\n/*require('missing2')*/require('./child');"
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
        with self.assertRaisesRegex(ValueError,'App ID'):check(self.archive(),'other-target')
    def test_path_traversal(self):
        self.files['../escape.js']=b'bad'
        with self.assertRaisesRegex(ValueError,'Unsafe'):check(self.archive(),'test-target')
    def test_main_limit(self):
        self.files['too-large.bin']=b'x'*4_000_001
        with self.assertRaisesRegex(ValueError,'main package'):check(self.archive(),'test-target')
    def test_source_file_refused(self):
        self.files['code.ts']=b'let x=1;'
        with self.assertRaisesRegex(ValueError,'source-project'):check(self.archive(),'test-target')
    def test_native_byte_mismatch(self):
        native=self.native();archive=self.archive();(native/'child.js').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'differs'):check(archive,'test-target',native)
    def test_writer_refuses_missing_engine_without_output(self):
        del self.files['cocos/cocos2d-js-min.js'];out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'missing startup'):self.build_with_resources(self.native(),'test-target',out)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
    def test_writer_refuses_wrong_id_without_output(self):
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'App ID'):self.build_with_resources(self.native(),'wrong',out)
        self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.tiktok-package-*')))
    def test_writer_publishes_and_preserves_existing(self):
        native=self.native();out=self.root/'delivery.zip';result=self.build_with_resources(native,'test-target',out)
        self.assertTrue(result['expected_tree_exact']);before=out.read_bytes()
        with self.assertRaises(ValueError):self.build_with_resources(native,'test-target',out)
        self.assertEqual(before,out.read_bytes())
    def test_dynamic_not_claimed_verified(self):
        self.files['main.js']=b'require(variable);'
        result=audit_files(self.files);self.assertTrue(result['dynamic_requires']);self.assertTrue(result['warnings'])
    def test_forwarded_require_iife(self):
        self.files['main.js']=b"(function(require){require('./missing-external.js');})(require);";self.refuse()
    def test_regex_not_require(self):
        self.files['main.js']=b"var p=/require('ghost')/;require('./child');"
        self.assertTrue(audit_files(self.files)['passed'])
    def test_division_does_not_hide_require(self):
        self.files['main.js']=b"var a=1/2;require('./missing');var b=3/4;";self.refuse()
    def test_template_expression_require(self):
        self.files['main.js']=b"var p=`hello${require('./missing')}`;";self.refuse()
    def test_json_parse_failure(self):
        self.files['main.js']=b"require('./data.json');";self.files['data.json']=b'{broken';self.refuse()
    def test_js_syntax_failure(self):
        self.files['child.js']=b'function {';self.refuse()
    def test_unknown_local_require_is_explicit(self):
        self.files['main.js']=b"(function(require){require('virtual');})(customResolver);"
        self.assertTrue(audit_files(self.files)['dynamic_requires'])
    def test_report_failure_no_final_zip(self):
        parent=self.root/'report-parent';parent.write_bytes(b'not a directory');out=self.root/'delivery.zip'
        with self.assertRaises(OSError):self.build_with_resources(self.native(),'test-target',out,parent/'result.json')
        self.assertFalse(out.exists())
    def test_report_success_bound_to_output(self):
        out=self.root/'delivery.zip';report=self.root/'evidence.json';self.build_with_resources(self.native(),'test-target',out,report)
        result=json.loads(report.read_text());self.assertEqual(result['archive'],str(out.resolve()))


    def test_compressible_main_oversize_refused_before_archive(self):
        self.files['large.bin'] = b'0' * 4_000_001
        native = self.native(); out = self.root/'delivery.zip'
        from unittest.mock import patch
        with patch('build_checked_zip.write_archive') as writer:
            with self.assertRaisesRegex(ValueError, 'main package'):
                self.build_with_resources(native, 'test-target', out)
            writer.assert_not_called()
        self.assertFalse(out.exists())
    def test_large_normal_subpackage_allowed(self):
        self.files['subpackages/resources/large.bin'] = b'0' * 4_000_001
        out=self.root/'delivery.zip'
        result=self.build_with_resources(self.native(),'test-target',out)
        self.assertLess(result['main_bytes'],4_000_000)
        self.assertGreater(result['uncompressed_total_bytes'],4_000_000)
    def test_large_independent_subpackage_refused(self):
        game=json.loads(self.files['game.json']);game['subpackages'][0]['independent']=True
        self.files['game.json']=json.dumps(game).encode()
        self.files['subpackages/resources/large.bin']=b'0'*4_000_001
        out=self.root/'delivery.zip'
        with self.assertRaisesRegex(ValueError,'(?i)independent subpackage'):
            self.build_with_resources(self.native(),'test-target',out)
        self.assertFalse(out.exists())
    def test_total_oversize_refused_before_archive(self):
        self.files['subpackages/resources/large.bin']=b'0'*30_000_001
        out=self.root/'delivery.zip'
        from unittest.mock import patch
        with patch('build_checked_zip.write_archive') as writer:
            with self.assertRaisesRegex(ValueError,'total'):
                self.build_with_resources(self.native(),'test-target',out)
            writer.assert_not_called()
        self.assertFalse(out.exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
