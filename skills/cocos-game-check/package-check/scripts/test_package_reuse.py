"""One invocation reuses validated bytes; no saved report can bypass verification."""
import collections,hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from check_package import check,write_archive,verifier
from test_package_checks import fixture, runtime_patch, APP, fixture_project
_RUNTIME = runtime_patch()
setUpModule, tearDownModule = _RUNTIME.start, _RUNTIME.stop

class PackageReadReuse(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.files=fixture();self.archive=self.root/'input.zip';write_archive(self.archive,self.files)
    def tearDown(self):self.tmp.cleanup()
    def test_every_member_crc_read_once_for_startup_and_asset_check(self):
        calls=collections.Counter();original=zipfile.ZipFile.read
        def read(z,name,*a,**kw):
            calls[name.filename if isinstance(name,zipfile.ZipInfo) else name]+=1
            return original(z,name,*a,**kw)
        # This case counts archive reads. Authorization and regression evidence are
        # separate boundaries with their own fail-closed tests.
        with patch.object(zipfile.ZipFile,'read',read), \
                patch('check_package.verify_regression_scope', return_value={'unit_test': 'authorized'}), \
                patch('check_package.regression_record', return_value={'unit_test': 'regression boundary'}), \
                patch('check_package.regression_coverage_problem', return_value=None):
            result=check(self.archive,APP)
        self.assertTrue(result['packed_resource_check']['passed']);self.assertEqual(calls,collections.Counter({name:1 for name in self.files}))
    def test_wrong_target_or_nonempty_payload_output_refused(self):
        payload={}
        with self.assertRaisesRegex(ValueError,'App ID'):verifier.verify(self.archive,'other',_verified_files=payload)
        self.assertEqual(payload,{})
        with self.assertRaisesRegex(ValueError,'empty dict'):verifier.verify(self.archive,_verified_files={'pretend':b'passed'})
    def test_crc_corruption_cannot_publish_payload(self):
        with zipfile.ZipFile(self.archive,'w',zipfile.ZIP_STORED) as z:
            for n,b in self.files.items():z.writestr(n,b)
        with zipfile.ZipFile(self.archive) as z:
            i=z.getinfo('child.js');offset=i.header_offset+30+len(i.filename.encode())+len(i.extra)
        data=bytearray(self.archive.read_bytes());data[offset]^=1;self.archive.write_bytes(data);payload={}
        with self.assertRaises(zipfile.BadZipFile):verifier.verify(self.archive,_verified_files=payload)
        self.assertEqual(payload,{})
    def test_modified_during_validation_refused(self):
        import audit_upload_startup
        original=audit_upload_startup.audit_files;payload={}
        def audit(files):
            result=original(files)
            with self.archive.open('ab') as stream:stream.write(b'changed')
            return result
        with patch.object(audit_upload_startup,'audit_files',side_effect=audit):
            with self.assertRaisesRegex(ValueError,'changed during'):verifier.verify(self.archive,_verified_files=payload)
        self.assertEqual(payload,{})
    def test_changed_during_asset_analysis_refused_and_temp_removed(self):
        seen=[]
        def assets(folder):
            seen.append(Path(folder))
            with self.archive.open('ab') as stream:stream.write(b'changed')
            return {'passed':True}
        with patch('check_package.packed_assets',side_effect=assets), \
                patch('check_package.verify_regression_scope', return_value={'unit_test': 'authorized'}):
            with self.assertRaisesRegex(ValueError,'changed during package checks'):check(self.archive,APP)
        self.assertTrue(seen);self.assertTrue(all(not folder.exists() for folder in seen))
    def test_original_native_mismatch_still_refused(self):
        native=self.root/'native';native.mkdir()
        for name,data in self.files.items():
            p=native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (native/'child.js').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'differs from actual Native'):check(self.archive,APP,native)
    def test_delivery_still_rechecks_final_file_against_original_native(self):
        from prepare_delivery import prepare
        native=self.root/'native';native.mkdir()
        for name,data in self.files.items():
            p=native/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        other=self.root/'other-temp';other.mkdir()
        from audit_runtime_resources import generate
        project=fixture_project(self.root/'project')          # v7.7: current source record (K5)
        manifest=self.root/'resources.json';manifest.write_text(json.dumps(generate(self.files)))
        # v7.7 receipt schema 2: the official writer records its finalize_native run (0 changes on this build)
        import tiktok_finalize
        finalize=tiktok_finalize.finalize_native(native,project,'remake',APP)
        self.assertEqual(finalize['blocks'],[])
        self.assertEqual({n:hashlib.sha256(d).hexdigest() for n,d in self.files.items()},
                         {p.relative_to(native).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in native.rglob('*') if p.is_file()})
        # Exercise the final ZIP/Native comparison and real size/CRC readback.
        # The fixture engine is a stub; isolate the external CLI and prior-regression
        # proof boundaries rather than treating it as a runnable official build.
        def cli_boundary(actual_archive, expected_sha):
            self.assertEqual(Path(actual_archive).resolve(),self.archive.resolve())
            self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(),expected_sha)
            return {'passed':True,'errors':[],'version':'synthetic-cli-boundary'}
        prior_regressions={'reused':True,'why':'synthetic prior-regression boundary',
                           'rewarded_ad_regression':{'status':'not_applicable'},
                           'runtime_regression':{'status':'passed','passed':True}}
        with patch('prepare_delivery.tempfile.gettempdir',return_value=str(other)), \
                patch('prepare_delivery.audit_final_startup',return_value={'passed':True}), \
                patch('tiktok_cli_gate.verify',side_effect=cli_boundary) as cli, \
                patch('check_package.reusable_regressions',return_value=prior_regressions):
            # v7.5: a hand-written ZIP without a writer receipt is an unofficial entry and is refused first.
            with self.assertRaisesRegex(ValueError,'unofficial entry|official writer receipt'):prepare(self.archive,native,APP,self.root/'no-receipt.json',project=project,resource_manifest=manifest)
            self.assertFalse((self.root/'no-receipt.json').exists())
            # Stand-in for the official writer: the receipt binds these exact ZIP bytes and Native tree.
            digests={n:hashlib.sha256(d).hexdigest() for n,d in self.files.items()}
            stamp=verifier.make_receipt('build_checked_zip',self.archive,hashlib.sha256(self.archive.read_bytes()).hexdigest(),digests,{'blocks':[],'warnings':[],'gates':[]},None,finalize=finalize)
            verifier.receipt_path(self.archive).write_text(json.dumps(stamp))
            url='http://127.0.0.1:54321/'
            contract=self.root/'startup-fixture.json'
            contract.write_text(json.dumps({'binding': {'web_tree_sha256': 'a'*64}}))
            startup={'passed':True,'startup_contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest()}
            with self.assertRaisesRegex(ValueError, '只有 ZIP'):
                prepare(self.archive,native,APP,self.root/'no-preview.json',project=project,resource_manifest=manifest)
            self.assertFalse((self.root/'no-preview.json').exists())
            self.assertTrue((self.root/'no-preview.json.size.json').exists())
            with patch('prepare_delivery.audit_final_startup',return_value=startup), \
                    patch('prepare_delivery.verify_preview',return_value={'url':url}) as preview:
                receipt=prepare(self.archive,native,APP,self.root/'delivery.json',project=project,resource_manifest=manifest,
                                startup_contract=contract,preview_url=url)
            preview.assert_called_once_with(url,'a'*64)
            self.assertEqual(receipt['preview']['url'],url)
            self.assertEqual(receipt['sha256'],hashlib.sha256(self.archive.read_bytes()).hexdigest())
            self.assertFalse(receipt['fresh_size_check']['reused'])
            self.assertGreaterEqual(cli.call_count,3)
            (native/'child.js').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'differs from actual Native'):prepare(self.archive,native,APP,self.root/'bad-delivery.json',project=project,resource_manifest=manifest)
        self.assertFalse((self.root/'bad-delivery.json').exists())
if __name__=='__main__':unittest.main()
