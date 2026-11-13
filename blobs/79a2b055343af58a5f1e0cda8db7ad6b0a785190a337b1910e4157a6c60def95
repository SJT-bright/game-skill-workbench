"""Exact surface/content semantics retain card bounds and all unrelated overlaps."""
import copy,json,tempfile,unittest
from pathlib import Path
from audit_ui_coverage import check_box
from extract_ui_layout import load_overrides,Screen
class CardContainers(unittest.TestCase):
 def box(self):
  card='Canvas/Popup/Day1/CardSurface';return {'safe':[0,0,400,600],'decorations':[],'contents':[{'name':card,'rect':[50,50,140,140],'container_for':['Canvas/Popup/Day1/DayNumber','Canvas/Popup/Day1/Rewards']},{'name':'Canvas/Popup/Day1/DayNumber/G0','rect':[90,65,20,20],'container_owner':card},{'name':'Canvas/Popup/Day1/Rewards/Coin','rect':[90,110,40,40],'container_owner':card}]}
 def check(self,b):
  problems=[];check_box(b,'fixture',[0,0,400,600],problems,8);return problems
 def test_exact_intended_surface_nesting_passes(self):self.assertEqual(self.check(self.box()),[])
 def test_child_crossing_own_card_is_still_refused(self):
  b=self.box();b['contents'][1]['rect']=[45,65,20,20];self.assertTrue(any('crosses its card' in p for p in self.check(b)))
 def test_two_children_still_must_not_overlap(self):
  b=self.box();b['contents'][2]['rect']=[90,65,30,30];self.assertTrue(any('overlaps' in p for p in self.check(b)))
 def test_unrelated_control_overlapping_card_is_refused(self):
  b=self.box();b['contents'].append({'name':'Canvas/Popup/BtnClaim','rect':[50,50,40,40]});self.assertTrue(any('CardSurface overlaps' in p for p in self.check(b)))
 def test_unknown_content_owner_is_refused(self):
  b=self.box();b['contents'][1]['container_owner']='another';self.assertRaises(ValueError,self.check,b)
 def test_not_declared_descendant_is_refused(self):
  b=self.box();b['contents'][1]['name']='Canvas/Popup/Day2/Number';self.assertRaises(ValueError,self.check,b)
 def test_core_ammo_is_excluded_only_from_hud_extraction(self):
  ammo='Canvas/GameView/Game_Container/pao/num';pause='Canvas/EnglishUI/HUD/BtnPause'
  raw={'screen':'level','page':{'width':375,'height':667,'dpr':1},'canvas_css':[0,0,375,667],'nodes':[{'name':'num','path':ammo,'rect':[.45,.4,.1,.05],'comps':{'label':{'string':'3'}},'order':1},{'name':'BtnPause','path':pause,'rect':[.01,.05,.1,.05],'comps':{'button':{}},'order':2}]}
  before=copy.deepcopy(raw);normal=Screen('probe-ui-dump.json',raw,{})
  self.assertIn(ammo,{n['path'] for n in normal.nodes})
  selected=Screen('probe-ui-dump.json',raw,{'exclude':[ammo]})
  self.assertNotIn(ammo,{n['path'] for n in selected.nodes});self.assertIn(pause,{n['path'] for n in selected.nodes});self.assertEqual(raw,before)
 def test_cross_card_annotation_is_not_allowed(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'overrides.json';p.write_text(json.dumps({'tags':{'Canvas/Day1/CardSurface':{'role':'container','contains':['Canvas/Day2/Rewards']}}}));self.assertRaises(ValueError,load_overrides,p)
if __name__=='__main__':unittest.main()
