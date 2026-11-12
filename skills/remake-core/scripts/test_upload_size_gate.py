"""Final ZIP partition boundaries and fresh delivery receipts; no browser/CI."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from upload_size_gate import enforce, enforce_files, inspect_files, inspect_final_zip, inspect_zip
from tiktok_cli_gate import invoke


def payload():
    return {'game.js':b'boot();', 'game.json':json.dumps({'subpackages':[{'name':'res','root':'subpackages/res'}]}).encode(),
            'project.config.json':b'{"appid":"test"}',
            'src/settings.json':b'{"subpackages":["res"],"bundleVers":{}}',
            'subpackages/res/game.js':b'load();', 'subpackages/res/config.json':b'{"name":"res"}',
            'subpackages/res/native/image.png':b'image'}


class SizeGate(unittest.TestCase):
    def test_trailing_slash_has_identical_partition_without_mutating_configuration(self):
        sizes={'game.js':12,'subpackages/res/file':50,'subpackages/resources/file':8}
        results=[]
        for root in ('subpackages/res','subpackages/res/'):
            game={'subpackages':[{'name':'res','root':root}]}
            snapshot=json.dumps(game)
            results.append(enforce(sizes,game))
            self.assertEqual(json.dumps(game),snapshot)
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[1]['main_bytes'],20)

    def test_trailing_slash_is_accepted_by_writer_and_final_inspection(self):
        f=payload()
        f['game.json']=b'{"subpackages":[{"name":"res","root":"subpackages/res/"}]}'
        snapshot=dict(f)
        written=enforce_files(f);checked=inspect_files(f)
        for key in ('main_bytes','total_bytes','normal_subpackages','independent_subpackages'):
            self.assertEqual(written[key],checked[key])
        self.assertEqual(f,snapshot)
        self.assertIn('Trailing slash accepted',checked['warnings'][0])
        del f['subpackages/res/game.js']
        with self.assertRaisesRegex(ValueError,'Missing/empty subpackage'):
            inspect_files(f)

    def test_trailing_slash_does_not_hide_overlapping_roots(self):
        for other in ('subpackages/res','subpackages/res/','subpackages/res/nested/'):
            with self.subTest(other=other), self.assertRaisesRegex(ValueError,'Overlapping/duplicate'):
                enforce({'subpackages/res/file':1,'subpackages/res/nested/file':1},
                        {'subpackages':[{'name':'a','root':'subpackages/res/'},{'name':'b','root':other}]})

    def test_unsafe_paths_are_rejected_before_normalization(self):
        for root in ('','/','/subpackages/res/','../res/','subpackages/../res/',
                     'subpackages//res/','./res/','C:/res/','subpackages\\res/'):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError,'Unsafe archive path'):
                enforce({'subpackages/res/file':1},{'subpackages':[{'name':'res','root':root}]})

    def test_trailing_slash_does_not_relax_independent_limit(self):
        with self.assertRaisesRegex(ValueError,'Independent'):
            enforce({'subpackages/res/file':4_000_001},
                    {'subpackages':[{'name':'res','root':'subpackages/res/','independent':True}]})

    def test_trailing_slash_zip_keeps_platform_rejection_and_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix='upload-size-slash-') as tmp:
            root=Path(tmp);p=root/'original.zip';f=payload()
            f['game.json']=b'{"subpackages":[{"name":"res","root":"subpackages/res/"}]}'
            with zipfile.ZipFile(p,'w') as z:
                for n,b in f.items():z.writestr(n,b)
            original=p.read_bytes();a=inspect_zip(p)
            self.assertTrue(a['passed'],a['errors'])
            feedback=root/'feedback.json'
            feedback.write_text(json.dumps({'platform':'tiktok','rejected_sha256':a['sha256']}))
            b=inspect_zip(p,feedback=feedback)
            self.assertFalse(b['passed'])
            self.assertIn('This exact ZIP was rejected',b['errors'][0])
            self.assertEqual(p.read_bytes(),original)

    def test_main_exact_boundary_then_over(self):
        self.assertEqual(enforce({'game.js':4_000_000},{})['main_bytes'],4_000_000)
        with self.assertRaisesRegex(ValueError,'main package'):
            enforce({'game.js':4_000_001},{})

    def test_normal_subpackage_and_total_boundary(self):
        g={'subpackages':[{'name':'res','root':'subpackages/res'}]}
        r=enforce({'game.js':1,'subpackages/res/file':29_999_999},g)
        self.assertEqual((r['main_bytes'],r['total_bytes']),(1,30_000_000))
        with self.assertRaisesRegex(ValueError,'total package'):
            enforce({'game.js':2,'subpackages/res/file':29_999_999},g)

    def test_independent_boundary_then_over(self):
        g={'subpackages':[{'name':'res','root':'subpackages/res','independent':True}]}
        enforce({'subpackages/res/file':4_000_000},g)
        with self.assertRaisesRegex(ValueError,'Independent'):
            enforce({'subpackages/res/file':4_000_001},g)

    def test_wrong_case_is_not_silently_ignored(self):
        for key in ('subPackages','SubPackages'):
            with self.assertRaisesRegex(ValueError,'wrong/ambiguous'):
                enforce({'subpackages/res/file':1},{key:[]})

    def test_nested_duplicate_empty_and_case_mismatched_roots(self):
        for rows in ([{'name':'x','root':'missing'}],
                     [{'name':'x','root':'subpackages/res'},{'name':'y','root':'subpackages/res/nested'}],
                     [{'name':'x','root':'subpackages/res'},{'name':'x','root':'other'}],
                     [{'name':'x','root':'Subpackages/res'}]):
            with self.assertRaises(ValueError):
                enforce({'subpackages/res/file':1,'subpackages/res/nested/file':1,'other/file':1},
                        {'subpackages':rows})

    def test_prefix_exclusion_is_directory_scoped(self):
        r=enforce({'res/file':1,'resources/file':12},{'subpackages':[{'name':'res','root':'res'}]})
        self.assertEqual(r['main_bytes'],12)

    def test_engine_bundle_configuration_required_and_version_selected(self):
        f=payload();inspect_files(f)
        del f['subpackages/res/config.json']
        with self.assertRaisesRegex(ValueError,'Missing Cocos'):
            inspect_files(f)
        f['src/settings.json']=b'{"subpackages":["res"],"bundleVers":{"res":"abc"}}'
        f['subpackages/res/config.abc.json']=b'{"name":"other"}'
        with self.assertRaisesRegex(ValueError,'name differs'):
            inspect_files(f)
        f['subpackages/res/config.abc.json']=b'{"name":"res"}'
        inspect_files(f)

    def test_custom_code_subpackage_is_allowed_but_engine_name_must_exist(self):
        f=payload();f['subpackages/custom/game.js']=b'code();'
        f['game.json']=b'{"subpackages":[{"name":"res","root":"subpackages/res"},{"name":"custom","root":"subpackages/custom"}]}'
        inspect_files(f)
        f['src/settings.json']=b'{"subpackages":["missing"]}'
        with self.assertRaisesRegex(ValueError,'do not match'):
            inspect_files(f)

    def test_duplicate_json_and_orphan_files_are_refused(self):
        f=payload();f['game.json']=b'{"subpackages":[],"subpackages":[]}'
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):
            inspect_files(f)
        f=payload();f['subpackages/forgotten/file']=b'x'
        with self.assertRaisesRegex(ValueError,'Unregistered'):
            inspect_files(f)

    def test_same_bytes_rechecked_renamed_and_known_rejection(self):
        with tempfile.TemporaryDirectory(prefix='upload-size-') as tmp:
            root=Path(tmp);p=root/'original.zip'
            with zipfile.ZipFile(p,'w') as z:
                for n,b in payload().items():z.writestr(n,b)
            a=inspect_zip(p);b=inspect_zip(p)
            self.assertTrue(a['passed']);self.assertTrue(b['passed'])
            self.assertNotEqual(a['run_id'],b['run_id']);self.assertEqual(a['sha256'],b['sha256'])
            q=root/'renamed.zip';q.write_bytes(p.read_bytes());c=inspect_zip(q)
            self.assertTrue(c['passed']);self.assertEqual(c['archive'],str(q.resolve()))
            feedback=root/'feedback.json'
            feedback.write_text(json.dumps({'platform':'tiktok','rejected_sha256':a['sha256']}))
            d=inspect_zip(q,feedback=feedback)
            self.assertFalse(d['passed']);self.assertIn('rejected',d['errors'][0])
            feedback.write_text(json.dumps({'platform':'tiktok','rejected_sha256':a['sha256'].upper()}))
            self.assertFalse(inspect_zip(q,feedback=feedback)['passed'])

    def test_green_size_and_cli_cannot_certify_project_local_or_changed_zip(self):
        import hashlib
        from verify_native_zip import make_receipt
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'game.zip';files=payload()
            with zipfile.ZipFile(archive,'w') as z:
                for name,data in files.items():z.writestr(name,data)
            cli={'passed':True,'errors':[]}
            with patch('tiktok_cli_gate.verify',return_value=cli):
                refused=inspect_final_zip(archive)
                self.assertTrue(refused['size_passed']);self.assertFalse(refused['passed'])
                self.assertFalse(refused['delivery_ready']);self.assertIn('delivery.writer_receipt',refused['errors'][0])
                # Explicit receipt-schema unit fixture, not a game acceptance record.
                receipt=make_receipt('build_checked_zip',archive,hashlib.sha256(archive.read_bytes()).hexdigest(),
                    {n:hashlib.sha256(v).hexdigest() for n,v in files.items()}, {'blocks':[]},'localize',
                    finalize={'kind':'finalize-native','policy':'new','files_after':{},'blocks':[]})
                (root/'game.zip.receipt.json').write_text(json.dumps(receipt))
                accepted=inspect_final_zip(archive);self.assertTrue(accepted['passed'])
                self.assertFalse(accepted['delivery_ready']) # final runtime/preview handoff is still separate
                renamed=root/'renamed.zip';renamed.write_bytes(archive.read_bytes())
                self.assertTrue(inspect_final_zip(renamed)['passed'])
                with zipfile.ZipFile(renamed,'a') as z:z.writestr('extra.js','changed();')
                self.assertFalse(inspect_final_zip(renamed)['passed'])
                (root/'game.zip.receipt.json').write_text('{"passed":true}')
                self.assertFalse(inspect_final_zip(archive)['passed'])

    def test_final_gate_binds_cli_to_zip_and_preserves_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'candidate.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                for name, data in payload().items():
                    zipped.writestr(name, data)
            cli_failure = {'passed': False, 'errors': ['ttmg build failed']}
            with patch('tiktok_cli_gate.verify', return_value=cli_failure) as cli:
                result = inspect_final_zip(archive)
                cli.assert_called_once_with(str(archive.resolve()), result['sha256'])
            self.assertTrue(result['size_passed'])
            self.assertFalse(result['passed'])
            self.assertEqual(result['errors'], ['ttmg build failed'])
            feedback = root / 'feedback.json'
            feedback.write_text(json.dumps({'platform': 'tiktok', 'rejected_sha256': result['sha256']}))
            with patch('tiktok_cli_gate.verify') as cli:
                rejected = inspect_final_zip(archive, feedback=feedback)
                cli.assert_not_called()
            self.assertFalse(rejected['passed'])
            self.assertTrue(rejected['platform_feedback']['same_rejected_archive'])

    def test_cli_check_and_build_have_different_success_statuses(self):
        for command, status in [('check', 'passed'), ('build', 'succeeded')]:
            with self.subTest(command=command):
                for exit_code in (0, 1):
                    stdout = json.dumps({'command': command, 'status': status, 'summary': {'errors': 0}})
                    completed = subprocess.CompletedProcess([], exit_code, stdout, '')
                    with patch('tiktok_cli_gate.run', return_value=(completed, 0.1)):
                        result = invoke(('node', 'cli.js'), command, Path('game'), Path('.'))
                    self.assertEqual(result['passed'], exit_code == 0)



class HostCompatibility(unittest.TestCase):
    def test_current_standard_sdk_sources_are_accepted(self):
        from upload_size_gate import enforce_tiktok_host
        kit=Path(__file__).resolve().parent.parent/'assets/platform-kit'
        for name in ['RewardedService','SaveStore','MissionFlow','HomeGrowthEntries','TikTokMissionService']:
            source=kit/'assets/tiktok-platform'/(name+'.js')
            with self.subTest(name=name):
                enforce_tiktok_host({'assets/main/'+name+'.js':source.read_bytes()})
        enforce_tiktok_host({'rewarded-guard.js':(kit/'parts/rewarded-guard.js').read_bytes()})

    def test_unguarded_host_calls_are_rejected_in_any_bundle(self):
        from upload_size_gate import enforce_tiktok_host
        for path in ['game.js','assets/main/index.js','subpackages/assets/game.js']:
            for code in ['wx.login({});', 'window.wx.getStorageSync("x");',
                         'var sdk=wx;sdk.login({});', 'globalThis["wx"].login({});']:
                with self.subTest(path=path,code=code), self.assertRaisesRegex(ValueError,'legacy WeChat'):
                    enforce_tiktok_host({path:code.encode()})

    def test_source_text_and_local_objects_are_not_host_calls(self):
        from upload_size_gate import enforce_tiktok_host
        enforce_tiktok_host({'code.js':b'// wx.login();\nvar text="typeof wx";function f(wx){wx.test();} '})

    def test_tiktok_first_fallback_is_structurally_checked(self):
        from upload_size_gate import enforce_tiktok_host
        enforce_tiktok_host({'code.js':b'var sdk=root.TTMinis&&root.TTMinis.game||root.tt||root.wx;'})
        with self.assertRaisesRegex(ValueError,'legacy WeChat'):
            enforce_tiktok_host({'code.js':b'var sdk=root.wx||root.tt||root.TTMinis.game;'})

class HostLexicalScopes(unittest.TestCase):
    def accepts(self, codes):
        from upload_size_gate import enforce_tiktok_host
        for code in codes:
            with self.subTest(code=code):
                enforce_tiktok_host({'code.js':code.encode()})

    def rejects(self, codes):
        from upload_size_gate import enforce_tiktok_host
        for code in codes:
            with self.subTest(code=code), self.assertRaisesRegex(ValueError,'legacy WeChat'):
                enforce_tiktok_host({'code.js':code.encode()})

    def test_block_lexical_declaration_never_hides_external_global(self):
        self.rejects(['{let wx={};} wx.login();',
                      'function f(){ {let wx={};wx.local();} wx.login();}',
                      'switch(x){case 1:let wx={};wx.local();}wx.login();'])
        self.accepts(['{let wx={};wx.local();}',
                      'function f(){wx.local();if(x){var wx={};}}'])

    def test_parameter_patterns_and_named_function_are_local(self):
        self.accepts(['function f({wx}){wx.local();}',
                      'function f([wx]){wx.local();}',
                      'function f({...wx}){wx.local();}',
                      'function f({wx={}}={}){wx.local();}',
                      '(function wx(){wx();})();',
                      'import {wx as local} from "./local.js";local();',
                      'class Local {wx(){return 1;}}',
                      'wx: for(;;){break wx;}'])

    def test_parameter_default_cannot_see_body_var(self):
        self.rejects(['function f(x=wx.login()){var wx={};}'])
        self.accepts(['function f(wx,x=wx.local()){var local=1;}'])

    def test_catch_bindings_do_not_escape_catch(self):
        self.accepts(['try{}catch(wx){wx.local();}',
                      'try{}catch({wx}){wx.local();}'])
        self.rejects(['try{}catch(wx){wx.local();}wx.login();'])

    def test_loop_bindings_do_not_escape_loop(self):
        self.accepts(['for(let wx of values){wx.local();}',
                      'for(let {wx} of values){wx.local();}'])
        self.rejects(['for(let wx of values){wx.local();}wx.login();'])

    def test_program_var_alias_is_not_assumed_local(self):
        self.rejects(['var wx=window.wx;wx.login();',
                      'var wx;wx.login();'])
        self.accepts(['var wx={local(){}};var wx;wx.local();',
                      'import {wx} from "./local.js";wx.local();'])

    def test_host_parse_error_refuses_instead_of_pass(self):
        from upload_size_gate import enforce_tiktok_host
        with self.assertRaisesRegex(ValueError,'host-reference check did not run'):
            enforce_tiktok_host({'code.js':b'wx.login(;'})

    def test_missing_node_refuses_when_host_parse_is_required(self):
        from upload_size_gate import enforce_tiktok_host
        with patch('upload_size_gate.shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'needs Node.js'):
                enforce_tiktok_host({'code.js':b'wx.login();'})

    def test_escaped_identifiers_and_constant_computed_hosts_are_rejected(self):
        self.rejects([r'w\u0078.login();',
                      r'globalThis["w\u0078"].login();',
                      'globalThis["w"+"x"].login();',
                      'window[`wx`].login();',
                      'self["w"+`x`].login();'])
        self.accepts([r'var text="w\u0078.login";',
                      'var local={wx:{login(){}}};local["w"+"x"].login();',
                      'var sdk=root.TTMinis&&root.TTMinis.game||root.tt||root["w"+"x"];'])

    def test_all_business_js_is_parsed_without_a_raw_wx_text_filter(self):
        from upload_size_gate import enforce_tiktok_host
        with self.assertRaisesRegex(ValueError,'host-reference check did not run'):
            enforce_tiktok_host({'code.js':b'var broken = ;'})
        # The two actual Cocos multiplatform engine paths retain their existing exception.
        enforce_tiktok_host({'cocos/cocos2d-js-min.js':b'wx.login();'})


if __name__=='__main__':
    unittest.main()
