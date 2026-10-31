"""Portable regression suite for forbidden social features. Run alongside audit_no_social_features.py."""
import json,tempfile,unittest
from pathlib import Path
from audit_no_social_features import audit
from feature_policy import enabled,removed
# 68 小熊拳击 R29 scoreboard shape (hero.js / score-info.js, local bots only); before 2026-10-31 setRank( was refused.
BEAR_SCOREBOARD='''cc.Class({extends:cc.Component,properties:{lbl_rank:cc.Label,spr_crown:cc.Sprite},
 setInfo(rank,name,score,isHero){this.setRank(rank);this.lbl_name.string=name;},
 setRank(rank){this.lbl_rank.string=rank;this.node.zIndex=rank;this.rank=rank;},
 updateRank(){var arr=this.game.scoreInfo_container.children;for(var i=this.rank-2;i>=0;i--){this.setRank(this.rank-1);}}});
cc.find('Canvas/tip').getComponent(cc.Label).string='Finding opponents';'''
class NoSocialTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'assets').mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_business_apis_and_routes(self):
  for code in ['TTMinis.game.shareAppMessage({})','TTMinis.game.shareToStory({})','TTMinis.game.onCopyUrl(()=>({}))','wx.setUserCloudStorage({})','wx.getFriendCloudStorage({})','tt.setImRankData({})','wx.getOpenDataContext().postMessage({})','UIMgr.openUI(LeagueSim)']:
   with self.subTest(code=code):
    (self.root/'assets/main.ts').write_text(code);self.assertFalse(audit(self.root)['passed'])
 def test_hidden_prefab_and_chinese_friend_rank(self):
  for name in ['friendRank','World Rankings','好友排行','排行榜','周榜','Weekly League','share','Invite','分享给好友']:
   with self.subTest(name=name):
    (self.root/'assets/home.prefab').write_text(json.dumps([{'_name':name,'_active':False}]));self.assertFalse(audit(self.root)['passed'])
 def test_scoped_board_names_any_casing(self):
  for name in ['worldRank','GlobalRanking','friendsLeaderBoard','btn_weekly_ranked','WORLD RANKED','Rank (Global)']:
   with self.subTest(name=name):
    (self.root/'assets/home.prefab').write_text(json.dumps([{'_name':name}]));self.assertFalse(audit(self.root)['passed'])
 def test_open_data_view_component(self):
  (self.root/'assets/home.prefab').write_text(json.dumps([{'__type__':'cc.Node','_name':'board'},{'__type__':'cc.WXSubContextView'}]))
  self.assertFalse(audit(self.root)['passed'])
  (self.root/'assets/home.prefab').unlink()
  # MeteorBlaster pre-stage-3 rankView.js draws the friend board canvas; adapter.js only reads it (not a hit)
  (self.root/'assets/rankView.js').write_text('if(window.sharedCanvas!=undefined&&this.tex){this.tex.initWithElement(window.sharedCanvas);}')
  self.assertFalse(audit(self.root)['passed'])
  (self.root/'assets/rankView.js').write_text('e=__globalAdapter.isSubContext?window.sharedCanvas||__globalAdapter.getSharedCanvas():null;')
  self.assertTrue(audit(self.root)['passed'])
  # vendor SDK routes bundled into index.js are not wording (FoxDenDash build)
  (self.root/'assets/rankView.js').write_text("var R={GET_FRIEND_RANK:'Home/Rank/getFriendRank',K:'worldRank'};")
  self.assertTrue(audit(self.root)['passed'])
 def test_made_up_global_place_is_refused(self):
  """Saul 2026-10-31: a locally invented 'server-wide' place is still a fake board."""
  for text in ['You are #3,512','#35120','Top 5% of all players','Better than 87% of players']:
   with self.subTest(text=text):
    (self.root/'assets/result.prefab').write_text(json.dumps([{'_name':'lbl_place'},{'__type__':'cc.Label','_string':text}]))
    self.assertFalse(audit(self.root)['passed'])
  (self.root/'assets/result.prefab').unlink()
  for code in ["label.string='You are #3,512 worldwide'","label.string='World Rank #'+n","const t='Weekly standings';"]:
   with self.subTest(code=code):
    (self.root/'assets/result.ts').write_text(code);self.assertFalse(audit(self.root)['passed'])
  dump=self.root/'dump';dump.mkdir();(self.root/'assets/result.ts').write_text('');(dump/'ui.json').write_text('{"nodes":[{"name":"lbl_place","text":"You are #3,512"}]}')
  self.assertFalse(audit(self.root,dumps=dump)['passed'])
 def test_local_match_places_pass(self):
  """Saul 2026-10-31: places vs local bots in one match, result place, trophies -> tier, stars and best score."""
  (self.root/'assets/score-info.js').write_text(BEAR_SCOREBOARD)
  (self.root/'assets/RankedProgress.js').write_text("const TIERS=['Iron','Bronze','Silver'];function tierOf(cup){return TIERS[Math.floor(cup/100)%3];} label.string='RANKED';label2.string='#'+place;")
  nodes=[{'_name':n}for n in ['rank','Rankings','lbl_rank','btn_ranked','RANKED','result_rank','place','standing','RankView','World 2','Leaderboard']]
  nodes+=[{'__type__':'cc.Label','_string':s}for s in ['#3','1st','Rank 2 / 10','Reach Silver rank','Best 1,520','color #FF3512']]
  (self.root/'assets/game.prefab').write_text(json.dumps(nodes))
  dump=self.root/'dump';dump.mkdir();(dump/'ui.json').write_text('{"nodes":[{"name":"result_rank","text":"3"},{"name":"lbl_fightLv","text":"Silver II"}]}')
  r=audit(self.root,dumps=dump);self.assertTrue(r['passed'],r['findings'])
 def test_removed_sharing_texture(self):
  (self.root/'assets/share.png.meta').write_text('{}');self.assertFalse(audit(self.root)['passed'])
 def test_normal_score_progress_profile_and_shared_config(self):
  (self.root/'assets/main.ts').write_text('const score=100;const level=2;const profile="shared-test";sdk.addShortcut({});sdk.getEntranceMissionReward({});');self.assertTrue(audit(self.root)['passed'])
 def test_native_only_and_dump_residuals(self):
  native=self.root/'native';native.mkdir();(native/'main.js').write_text('TTMinis.game.shareToStory({})');self.assertFalse(audit(self.root,native=native)['passed'])
  dump=self.root/'dump';dump.mkdir();(dump/'ui.json').write_text('{"nodes":[{"name":"Friends Rankings"}]}');self.assertFalse(audit(self.root,dumps=dump)['passed'])
 def test_historical_explicit_rank_record_no_longer_enables(self):
  p=self.root/'docs/league';p.mkdir(parents=True);(p/'decision.json').write_text('{"decision":"keep_original"}');self.assertFalse(enabled(self.root)['league']);self.assertTrue(removed('Weekly League',enabled(self.root)))
  self.assertFalse(audit(self.root)['passed'])
if __name__=='__main__':unittest.main(verbosity=2)
