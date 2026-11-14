"""Scope-only controls over copied kit inputs; no game/browser or real preparation."""
from pathlib import Path
from unittest import mock
import copy,json,shutil,tempfile,unittest
import preparation_cache as C
import tiktok_finalize_steps as T
HERE=Path(__file__).resolve().parent
class ProductionScope(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='preparation-production-scope-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.kit=self.root/'kit';shutil.copytree(HERE.parent/'assets/platform-kit',self.kit,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));self.project=self.root/'project';(self.project/'assets').mkdir(parents=True);self.native=self.root/'native';self.native.mkdir();(self.native/'game.js').write_text('const owned=1;');self.manifest=T.load_manifest(self.kit/'KIT_MANIFEST.json');self.ctx=T.Ctx('native',self.native,project=self.project,board='localize',engine=2,policy='new',manifest=self.manifest)
 def binding(self):return C.native_binding(self.ctx,('structure',))
 def test_known_maintenance_content_does_not_invalidate(self):
  before=self.binding()
  for n in ['tests/run-all.js','README_接入说明.md']:
   p=self.kit/n;p.write_bytes(p.read_bytes()+b'\nMaintenance-only content.\n')
  self.assertEqual(before,self.binding())
 def test_runtime_config_and_new_files_stay_inputs(self):
  for n in ['parts/storage-guard.js','settings/bytedance.json','assets/tiktok-platform/new-production.js','tests/new-unreviewed.js']:
   p=self.kit/n;old=p.read_bytes() if p.exists() else None;before=self.binding();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((old or b'')+b'\nNew input\n');self.assertNotEqual(before,self.binding())
   if old is None:p.unlink()
   else:p.write_bytes(old)
 def test_manifest_selected_maintenance_is_bound_as_production(self):
  document=copy.deepcopy(self.manifest.data);document['parts']['touch24']['file']['src']='tests/run-all.js';self.ctx.manifest=T.Manifest(document,self.kit);before=self.binding();p=self.kit/'tests/run-all.js';p.write_bytes(p.read_bytes()+b'\nActually selected input.\n');self.assertNotEqual(before,self.binding())
 def test_loader_aliases_and_case_variants_keep_selected_input_bound(self):
  for alias in ['tests/../tests/run-all.js','./tests//run-all.js','TESTS/run-all.js']:
   document=copy.deepcopy(self.manifest.data);part=document['parts']['touch24'];part['file']['src']=alias
   self.ctx.manifest=T.Manifest(document,self.kit);p=self.kit/'tests/run-all.js';old=p.read_bytes()
   if not alias.startswith('TESTS/'):
    part['file']['sha256']=C.hashlib.sha256(old).hexdigest();self.ctx.manifest=T.Manifest(document,self.kit)
    self.assertEqual(self.ctx.manifest.kit_bytes('touch24'),old)
   before=self.binding();p.write_bytes(old+b'\nSelected alias input.\n');self.assertNotEqual(before,self.binding());p.write_bytes(old)
 def test_physical_manifest_escape_cannot_get_scope(self):
  external=self.root/'external.js';external.write_text('const external=true;')
  for alias in ['../external.js',str(external)]:
   document=copy.deepcopy(self.manifest.data);document['parts']['touch24']['file']['src']=alias;document['parts']['touch24']['file']['sha256']=C.hashlib.sha256(external.read_bytes()).hexdigest();self.ctx.manifest=T.Manifest(document,self.kit)
   self.assertEqual(self.ctx.manifest.kit_bytes('touch24'),external.read_bytes())
   with self.assertRaises(C.Uncacheable):self.binding()
 def test_scope_does_not_assume_unix_executable_bits(self):
  with mock.patch.object(C.os,'access',return_value=True):self.assertTrue(self.binding()['tools']['production_scope'])
 def test_unknown_dynamic_kit_helper_cannot_get_scope(self):
  (self.kit/'tools/new-reader.py').write_text('from pathlib import Path\n')
  with self.assertRaises(C.Uncacheable):self.binding()
 def test_self_pin_unknown_body_and_duplicate_assignment_refused(self):
  original=Path(C.__file__).read_bytes();p=self.root/'unknown-cache.py'
  for addition in [b'\n# unknown implementation\n',b"\nPREPARATION_SELF_SHA256 = '"+b'0'*64+b"'\n"]:
   p.write_bytes(original+addition)
   with mock.patch.object(C,'__file__',str(p)),self.assertRaises(C.Uncacheable):C._scope_policy()
 def test_policy_or_finalizer_unknown_bytes_refused(self):
  scripts=self.root/'scripts';scripts.mkdir();policy=scripts/'preparation_scope_policy.json';finalizer=scripts/'tiktok_finalize.py';raw=(HERE/'preparation_scope_policy.json').read_bytes();f=(HERE/'tiktok_finalize.py').read_bytes()
  for pbytes,fbytes in [(raw+b'\n ',f),(raw,f+b'\n# unknown finalizer\n')]:
   policy.write_bytes(pbytes);finalizer.write_bytes(fbytes)
   with mock.patch.object(C,'HERE',scripts),self.assertRaises(C.Uncacheable):C._scope_policy()
if __name__=='__main__':unittest.main()
