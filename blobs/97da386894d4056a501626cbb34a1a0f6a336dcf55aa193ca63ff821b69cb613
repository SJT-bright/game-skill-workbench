"""Behavior checks for manual revive scope; no game, browser or fabricated game pass."""
import json,os,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
import ad_regression as ar
import runtime_regression as rr
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'remake-core/scripts'))
import regression_scope_gate as scope
class ManualRevivePolicy(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.package=self.root/'native';self.package.mkdir();(self.package/'game.js').write_text('/* synthetic policy-only fixture */')
  self.adapter=self.root/'adapter.json'
 def fixture(self,**extra):
  value={'home':'return true','request':'runGenericSDKProbe()', 'ad_entries':[{'id':'revive','role':'revive','button':'Canvas/Defeat/BtnVideo','states':[{'name':'fail','why':'manual'}]}]}
  value.update(extra);self.adapter.write_text(json.dumps(value));return value
 def test_generic_callback_matrix_is_retained_even_with_only_manual_game_entries(self):
  adapter=rr.automatic_adapter(self.fixture())
  self.assertNotIn('ad_entries',adapter)
  self.assertFalse(rr.manual_revive_request(adapter));self.assertEqual(ar.default_cases(adapter),ar.CASES)
 def test_explicit_revive_request_is_manual_but_independent_x2_remains(self):
  adapter=rr.automatic_adapter(self.fixture(request_role='revive'))
  self.assertTrue(rr.manual_revive_request(adapter));self.assertEqual(ar.default_cases(adapter),[])
  self.assertEqual(ar.default_cases(dict(adapter,double_claim={'open_js':'synthetic'})),ar.DOUBLE_CASES)
 def test_mixed_routes_preserve_ordinary_ad_results_and_metadata(self):
  raw=self.fixture();gift={'id':'gift','role':'home_gift','button':'Canvas/Gift/WatchAd','states':[{'name':'ready','why':'real non-revive route'}]};raw['ad_entries'].append(gift)
  effective=rr.automatic_adapter(raw)
  self.assertEqual(effective['ad_entries'],[gift]);self.assertEqual(len(raw['ad_entries']),2)
  self.assertFalse(rr.manual_revive_request(effective));self.assertEqual(ar.default_cases(effective),ar.CASES)
 def test_empty_automatic_matrix_has_explicit_manual_disposition_without_executor(self):
  self.fixture(request_role='revive')
  with patch.object(scope,'authorize_batch',return_value='isolated-unit-authorization'),patch.object(ar,'_run_uncached')as execute:
   result=ar.run(self.package,self.adapter)
  execute.assert_not_called();self.assertEqual(result['cases'],[])
  self.assertFalse(result['applicable']);self.assertEqual(result['disposition'],'manual_revive_only')
  self.assertTrue(result['manual_playtest_required']);self.assertEqual(result['not_run'][0]['role'],'revive')
  self.assertEqual(result['executed_units'],0)
 def test_manual_disposition_does_not_bypass_the_public_plan_boundary(self):
  self.fixture(request_role='revive')
  token=scope._active_plan.set(None);self.addCleanup(scope._active_plan.reset,token)
  with patch.dict(os.environ,{},clear=True),patch.object(ar,'_run_uncached')as execute:
   with self.assertRaisesRegex(ar.RegressionRefused,'scope_required.*执行计划'):ar.run(self.package,self.adapter)
  execute.assert_not_called()
if __name__=='__main__':unittest.main()
