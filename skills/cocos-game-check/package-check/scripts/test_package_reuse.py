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
        with patch.object(zipfile.ZipFile,'read',read):result=check(self.archive,APP)
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
        with patch('check_package.packed_assets',side_effect=assets):
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
        with patch('prepare_delivery.tempfile.gettempdir',return_value=str(other)), patch('prepare_delivery.audit_final_startup',return_value={'passed':True}):
            # v7.5: a hand-written ZIP without a writer receipt is an unofficial entry and is refused first.
            with self.assertRaisesRegex(ValueError,'unofficial entry'):prepare(self.archive,native,APP,self.root/'no-receipt.json',project=project,resource_manifest=manifest)
            self.assertFalse((self.root/'no-receipt.json').exists())
            # Stand-in for the official writer: the receipt binds these exact ZIP bytes and Native tree.
            digests={n:hashlib.sha256(d).hexdigest() for n,d in self.files.items()}
            stamp=verifier.make_receipt('build_checked_zip',self.archive,hashlib.sha256(self.archive.read_bytes()).hexdigest(),digests,{'blocks':[],'warnings':[],'gates':[]},None,finalize=finalize)
            verifier.receipt_path(self.archive).write_text(json.dumps(stamp))
            receipt=prepare(self.archive,native,APP,self.root/'delivery.json',project=project,resource_manifest=manifest)
            self.assertEqual(receipt['sha256'],hashlib.sha256(self.archive.read_bytes()).hexdigest())
            (native/'child.js').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'differs from actual Native'):prepare(self.archive,native,APP,self.root/'bad-delivery.json',project=project,resource_manifest=manifest)
        self.assertFalse((self.root/'bad-delivery.json').exists())
if __name__=='__main__':unittest.main()
