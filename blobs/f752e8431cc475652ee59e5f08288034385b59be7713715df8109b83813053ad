"""Calibration only: Chrome Retry must carry original trusted start/end receipts."""
import copy,unittest
from duo_sdk_ui_retry_contract import image_recovery_errors
class ChromeRetry(unittest.TestCase):
 def raw(self):
  return {'binding':{'native_tree_sha256':'a'},'native_tree_sha256':'a','passed':True,'home_ready':True,'failure_kind':'image_decode_error','errors_before':['image transport error'],'errors_after':[],'first_exception':None,'retry_visible':True,'retry_group':'ui','attempt_before':1,'attempt_after':2,'request_count_before':1,'request_count_after':2,'retry_touch':{'transport':'playwright_cdp_touch','trusted_touch':True,'at_ms':10},'observed':{'touches':[{'type':'touchstart','trusted':True,'t':11},{'type':'touchend','trusted':True,'t':12}]},'business':{'home':{'visible':True,'required_assets_ready':True,'loading_overlay_gone':True,'play_interactable':True,'node_path':'HOME','lifecycle_complete':True,'after_draw_observed':True,'at_ms':20},'play':{'touch':{'transport':'playwright_cdp_touch','at_ms':30},'level_ready':True,'level_identity':'level1','before':{'cut':False},'after':{'cut':True},'effect_at_ms':40}}}
 def errors(self,r):return image_recovery_errors(r,r['binding'])
 def test_chrome_original_receipts(self):self.assertEqual(self.errors(self.raw()),[])
 def test_missing_receipts(self):
  r=self.raw();r['observed']['touches']=[];self.assertTrue(any('Chrome Retry' in e for e in self.errors(r)))
 def test_untrusted_receipts(self):
  r=self.raw()
  for e in r['observed']['touches']:e['trusted']=False
  self.assertTrue(any('Chrome Retry' in e for e in self.errors(r)))
 def test_unrelated_later_touches(self):
  r=self.raw()
  for e in r['observed']['touches']:e['t']+=100
  self.assertTrue(any('Chrome Retry' in e for e in self.errors(r)))
 def test_reversed_receipts(self):
  r=self.raw();r['observed']['touches'][1]['t']=10;self.assertTrue(any('Chrome Retry' in e for e in self.errors(r)))
 def test_ego_unchanged(self):
  r=self.raw();r['retry_touch']['transport']='ego_page_cdp';r['business']['play']['touch']['transport']='ego_page_cdp';r.pop('observed');self.assertEqual(self.errors(r),[])
 def test_missing_retry_truth_rejected(self):
  r=self.raw();r['retry_touch']['trusted_touch']=False;self.assertTrue(self.errors(r))
if __name__=='__main__':unittest.main()
