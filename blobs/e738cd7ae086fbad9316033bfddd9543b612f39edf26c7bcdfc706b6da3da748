import json,tempfile,unittest
from pathlib import Path
from no_social_package_obligation import verify
class ObligationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.native=self.root/'native';self.native.mkdir();(self.native/'game.js').write_text('const score=10;');(self.native/'game.json').write_text('{}')
 def tearDown(self):self.tmp.cleanup()
 def source(self,name='a'):
  p=self.root/'source'/name;(p/'assets').mkdir(parents=True);(p/'project.json').write_text('{}');return p
 def test_source_root_unique(self):
  p=self.source();self.assertEqual(verify(self.root,self.native)['source_provenance']['source_root'],str(p.resolve()))
 def test_source_missing_refused(self):
  (self.root/'source').mkdir()
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_source_multiple_refused(self):
  self.source('a');self.source('b')
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_native_only_rank_refused(self):
  (self.native/'game.js').write_text('sdk.getRank()')
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_native_only_provenance_supported(self):
  r=verify(self.root,self.native);self.assertEqual(r['source_provenance']['mode'],'native_only');self.assertTrue(r['passed'])
 def test_normal_personal_progress_collection(self):
  p=self.source();(p/'assets/main.ts').write_text('const score=20,clevelMax=4; sdk.getEntranceMissionReward({}); const collectionState={owned:[]}; const config="shared_test_app";');self.assertTrue(verify(self.root,self.native)['passed'])
 def test_workspace_root_decision_refused(self):
  self.source();p=self.root/'docs/league';p.mkdir(parents=True);(p/'decision.json').write_text('{"decision":"keep_original"}')
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_source_decision_refused(self):
  p=self.source()/'docs/league';p.mkdir(parents=True);(p/'decision.json').write_text('{"decision":"keep_original"}')
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_native_rank_json_refused(self):
  self.source();(self.native/'ui.json').write_text('[{"_name":"btn_rank","_active":false}]')
  with self.assertRaises(ValueError):verify(self.root,self.native)
 def test_package_verify_mandatory_gate_runs_before_other_evidence(self):
  from package_obligations import verify as package_verify
  p=self.source();(p/'assets/main.ts').write_text('sdk.getRank()')
  with self.assertRaisesRegex(ValueError,'forbidden social package features'):
   package_verify({},self.native,self.root,'unused-resource-manifest.json')
 def test_source_symlink_refused(self):
  p=self.root/'external';p.mkdir();(self.root/'source').symlink_to(p,target_is_directory=True)
  with self.assertRaises(ValueError):verify(self.root,self.native)
if __name__=='__main__':unittest.main(verbosity=2)
