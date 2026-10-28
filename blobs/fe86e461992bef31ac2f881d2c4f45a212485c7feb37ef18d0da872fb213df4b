"""Portable regression suite for forbidden social features. Run alongside audit_no_social_features.py."""
import json,tempfile,unittest
from pathlib import Path
from audit_no_social_features import audit
from feature_policy import enabled,removed
class NoSocialTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'assets').mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_business_apis_and_routes(self):
  for code in ['TTMinis.game.shareAppMessage({})','TTMinis.game.shareToStory({})','TTMinis.game.onCopyUrl(()=>({}))','wx.setUserCloudStorage({})','wx.getFriendCloudStorage({})','UIMgr.openUI(RankView)']:
   with self.subTest(code=code):
    (self.root/'assets/main.ts').write_text(code);self.assertFalse(audit(self.root)['passed'])
 def test_hidden_prefab_and_chinese_friend_rank(self):
  for name in ['rank','Rankings','好友排行','share','Invite','分享给好友']:
   with self.subTest(name=name):
    (self.root/'assets/home.prefab').write_text(json.dumps([{'_name':name,'_active':False}]));self.assertFalse(audit(self.root)['passed'])
 def test_compiled_sprite_frame_name_is_not_a_ui_route(self):
  frame=[1,['texture'],['_textureSetter'],['cc.SpriteFrame'],0,[{'name':'share1','rect':[0,0,80,80],'offset':[0,0],'originalSize':[80,80],'capInsets':[0,0,0,0]}],[0],0,[0],[0],[0]]
  (self.root/'assets/sprite.json').write_text(json.dumps(frame));self.assertTrue(audit(self.root)['passed'])
  frame[5][0]['button']='Share';(self.root/'assets/sprite.json').write_text(json.dumps(frame));self.assertFalse(audit(self.root)['passed'])
 def test_node_record_inside_compiled_container_still_rejected(self):
  frame=[1,[],[],['cc.Node'],0,[{'name':'share','rect':[],'offset':[],'originalSize':[],'capInsets':[]}],[],0,[],[],[]]
  (self.root/'assets/node.json').write_text(json.dumps(frame));self.assertFalse(audit(self.root)['passed'])
 def test_sprite_shape_without_exact_type_is_not_exempt(self):
  (self.root/'assets/node.json').write_text(json.dumps({'name':'share','rect':[],'offset':[],'originalSize':[],'capInsets':[]}));self.assertFalse(audit(self.root)['passed'])
 def test_removed_sharing_texture(self):
  (self.root/'assets/share.png.meta').write_text('{}');self.assertFalse(audit(self.root)['passed'])
 def test_normal_score_progress_profile_and_shared_config(self):
  (self.root/'assets/main.ts').write_text('const score=100;const level=2;const profile="shared-test";sdk.addShortcut({});sdk.getEntranceMissionReward({});');self.assertTrue(audit(self.root)['passed'])
 def test_native_only_and_dump_residuals(self):
  native=self.root/'native';native.mkdir();(native/'main.js').write_text('TTMinis.game.shareToStory({})');self.assertFalse(audit(self.root,native=native)['passed'])
  dump=self.root/'dump';dump.mkdir();(dump/'ui.json').write_text('{"nodes":[{"name":"Rankings"}]}');self.assertFalse(audit(self.root,dumps=dump)['passed'])
 def test_historical_explicit_rank_record_no_longer_enables(self):
  p=self.root/'docs/league';p.mkdir(parents=True);(p/'decision.json').write_text('{"decision":"keep_original"}');self.assertFalse(enabled(self.root)['league']);self.assertTrue(removed('Weekly League',enabled(self.root)))
if __name__=='__main__':unittest.main(verbosity=2)
