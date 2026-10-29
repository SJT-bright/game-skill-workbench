"""Synthetic checker calibration. Never a product or Native runtime pass."""
import copy,json,unittest
from startup_business_contract import validate_business
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.good={'business':{'home':{'visible':True,'lifecycle_complete':True,'after_draw_observed':True,'required_assets_ready':True,'loading_overlay_gone':True,'play_interactable':True,'node_path':'Canvas/UI/Menu','at_ms':10},'play':{'touch':{'transport':'ego_page_cdp','at_ms':20},'level_ready':True,'level_identity':'level1','before':{'x':0},'after':{'x':12},'effect_at_ms':30}},'first_exception':None}
 def test_normal(self):self.assertEqual(validate_business(self.good),[])
 def test_loading_only(self):self.assertTrue(validate_business({'passed':True,'scene':{'active':True,'name':'Loading'},'errors':[]}))
 def test_mutations(self):
  cases=[lambda d:d['business']['home'].pop('lifecycle_complete'),lambda d:d['business']['home'].update(after_draw_observed=False),lambda d:d['business']['home'].update(loading_overlay_gone=False),lambda d:d['business']['home'].update(required_assets_ready=False),lambda d:d['business']['home'].update(play_interactable=False),lambda d:d['business']['play'].update(after={'x':0}),lambda d:d['business']['play']['touch'].update(transport='controller_call'),lambda d:d['business']['play'].update(effect_at_ms=19),lambda d:d.update(first_exception={'message':'hidden'}),lambda d:d['business']['home'].update(at_ms=float('nan')),lambda d:d.update(business=None)]
  for change in cases:
   d=copy.deepcopy(self.good);change(d)
   with self.subTest(change=repr(change)):self.assertTrue(validate_business(d))
 def test_unknown_not_waived(self):self.assertTrue(validate_business({'business':{'not_applicable':True}}))
if __name__=='__main__':unittest.main()
