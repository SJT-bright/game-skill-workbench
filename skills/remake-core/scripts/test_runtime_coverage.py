import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
import audit_runtime_coverage as audit
class CoverageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.roots={k:self.root/k for k in ['source','native','web']}
  for p in self.roots.values():p.mkdir();(p/'ledger.js').write_text('localStorage.getItem(KEY);localStorage.setItem(KEY, value);')
  self.proof=self.root/'proof.log';self.proof.write_text('actual regression execution log')
  files,sites=audit.inventory(self.roots);self.doc={'schema':'runtime_coverage.v1','artifacts':files,'sites':{k:{'discovered':v,'domain':'rewards'} for k,v in sites.items()},'domains':{'rewards':{'kind':'reward','production_targets':list(files),'cases':{c:{'status':'pass','observed':'A specific observation for '+c,'evidence':{'path':'proof.log','sha256':audit.sha(self.proof)}} for c in audit.REQUIRED['reward']}}}}
 def tearDown(self):self.temp.cleanup()
 def check(self,d=None):return audit.verify(d or self.doc,self.roots,self.root)
 def test_complete_fixture_only(self):self.assertEqual(self.check(),[])
 def test_empty_domains_refused(self):self.doc['domains']={};self.assertTrue(self.check())
 def test_added_original_ledger_not_covered(self): (self.roots['native']/'original-ledger.js').write_text('tt.getStorageSync("oldReward")');self.assertTrue(self.check())
 def test_missing_empty_string_case_refused(self):del self.doc['domains']['rewards']['cases']['missing_empty_string'];self.assertTrue(self.check())
 def test_changed_final_bundle_refused(self):(self.roots['native']/'ledger.js').write_text('localStorage.getItem(NEW_KEY)');self.assertTrue(self.check())
 def test_changed_evidence_refused(self):self.proof.write_text('changed');self.assertTrue(self.check())
 def test_copied_fake_target_refused(self):self.doc['domains']['rewards']['production_targets']=['source/copied-ledger.js'];self.assertTrue(self.check())
 def test_unjustified_exclusion_refused(self):self.doc['domains']['rewards']={'kind':'excluded','reason':'not applicable'};self.assertTrue(self.check())
 def test_untested_refused(self):self.doc['domains']['rewards']['cases']['read_failure']['status']='untested';self.assertTrue(self.check())
 def test_dynamic_key_discovered(self):self.assertTrue(any(s['argument']=='KEY' for s in audit.inventory(self.roots)[1].values()))
 def test_writer_no_review_cannot_emit_zip(self):
  from unittest.mock import patch
  import make_tiktok_zip as writer,writer_proofs
  from test_single_writer import SingleWriter
  actual_consume=writer_proofs.consume
  f=SingleWriter('test_legacy_build_routes_all_parameters_once');f.setUp();self.addCleanup(f.doCleanups);f.mock_engine()
  with patch.object(writer_proofs,'consume',side_effect=actual_consume):
   with self.assertRaisesRegex(ValueError,'writer.producers: missing evidence'):
    writer.write_package(**f.kw)
  self.assertFalse(f.out.exists())
if __name__=='__main__':unittest.main()
