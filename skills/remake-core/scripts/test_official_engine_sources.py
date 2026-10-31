"""Synthetic unit calibration of exact official-engine classification, not game evidence."""
import hashlib,json,tempfile,unittest
from pathlib import Path
import audit_runtime_resources as audit
class ExactEngineIdentity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=audit.OFFICIAL_ENGINE_MANIFEST
  self.raw=b'var syntheticOriginalEngine = true;'
  self.path=Path(self.tmp.name)/'official.json';self.write('test-v1');audit.OFFICIAL_ENGINE_MANIFEST=self.path
 def tearDown(self):audit.OFFICIAL_ENGINE_MANIFEST=self.old;self.tmp.cleanup()
 def write(self,version):self.path.write_text(json.dumps({'schema':'official_cocos_engine_sources.v1','artifacts':[{'engine_version':version,'sha256':hashlib.sha256(self.raw).hexdigest(),'bytes':len(self.raw),'provenance':{'kind':'synthetic_unit_fixture'}}]}))
 def test_exact_bytes_any_name_and_full_source_binding(self):
  r=audit.discover({'random.js':self.raw});self.assertIn('random.js',r['verified_engine_sources']);self.assertEqual(r['source_sha256']['random.js'],hashlib.sha256(self.raw).hexdigest());self.assertEqual(r['sites'],[])
 def test_same_name_business_load_not_skipped(self):
  files={'cocos2d-js-min.js':b'cc.resources.load("missing",cc.SpriteFrame,function(){});'}
  r=audit.discover(files);self.assertFalse(r['verified_engine_sources']);self.assertEqual(r['sites'][0]['paths'],['missing'])
  with self.assertRaisesRegex(ValueError,'missing/type mismatch'):audit.required_requests(files)
 def test_appended_call_changes_identity_and_is_inventoried(self):
  files={'cocos2d-js-min.js':self.raw+b'\ncc.resources.load("missing",cc.SpriteFrame,function(){});'}
  r=audit.discover(files);self.assertFalse(r['verified_engine_sources']);self.assertEqual(r['sites'][0]['paths'],['missing'])
  with self.assertRaisesRegex(ValueError,'missing/type mismatch'):audit.required_requests(files)
 def test_other_business_sites_are_identical(self):
  business=b'cc.resources.load("a",cc.SpriteFrame,function(){});cc.resources.load("b",cc.SpriteFrame,function(){});'
  a=audit.discover({'assets/main/index.js':business});b=audit.discover({'engine.js':self.raw,'assets/main/index.js':business});self.assertEqual(a['sites'],b['sites']);self.assertEqual(len(b['sites']),2)
 def test_manifest_is_in_scanner_and_cache_identity(self):
  a=audit.discover({'engine.js':self.raw});self.write('test-v2');b=audit.discover({'engine.js':self.raw});self.assertNotEqual(a['scanner_sha256'],b['scanner_sha256']);self.assertEqual(b['verified_engine_sources']['engine.js']['engine_version'],'test-v2')
if __name__=='__main__':unittest.main(verbosity=2)
