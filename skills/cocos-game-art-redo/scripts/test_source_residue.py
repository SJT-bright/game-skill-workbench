import base64,json,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
import check_native_sprite_sources as tool
class ResidueCoverage(unittest.TestCase):
 def test_real_cocos_compressed_uuid(self):
  raw='4337c98fdbcb4c1a80701269a76ef8ff';s=raw[:2]+base64.b64encode(bytes.fromhex(raw[2:])).decode();self.assertEqual(tool.decode(s),'4337c98f-dbcb-4c1a-8070-1269a76ef8ff')
 def test_small_strip_below_old_area_ratio(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'small.png';im=Image.new('RGBA',(320,320));g=ImageDraw.Draw(im);g.rectangle((40,20,300,300),fill='white');g.rectangle((2,100,4,190),fill=(240,100,80,80));im.save(f);r=tool.inspect_texture(f);self.assertIn('extra_alpha_components',r['suspects']);self.assertLess(r['components'][0]['area'],r['main_component']['area']*.025)
 def test_source_and_export_captured_targets(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'project.json').write_text('{}');a=root/'assets';a.mkdir();im=Image.new('RGBA',(64,64));ImageDraw.Draw(im).ellipse((10,10,54,54),fill='white');im.save(a/'thing.png');(a/'thing.png.meta').write_text(json.dumps({'subMetas':{'thing':{}}}));self.assertEqual(tool.check(root,['thing'])['status'],'no_signals');dump=root/'dump';dump.mkdir();(dump/'ui.json').write_text(json.dumps({'nodes':[{'name':'Btn CLOSET','comps':{'sprite':{'frame':'thing'}}}]}));self.assertEqual(tool.captured_frames(dump),['thing']);self.assertEqual(tool.check(root,[])['status'],'incomplete')
 def test_rounded_top_touch_requires_review(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'tight.png';im=Image.new('RGBA',(320,140));ImageDraw.Draw(im).rounded_rectangle((20,0,300,120),radius=50,fill='white');im.save(f);self.assertIn('main_body_lacks_safety_margin',tool.inspect_texture(f)['suspects'])
 def test_review_is_pixel_binding_scoped(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'docs/art';folder.mkdir(parents=True);file=folder/'sprite-source-review.json'
   file.write_text(json.dumps({'reviews':[{'frame':'foo','sha256':'current','normal_signals':['extra_alpha_components'],'why':'intentional detached sparkle'}]}))
   result={'input':str(root),'status':'needs_review','passed':False,'errors':[],'rows':[{'name':'foo','sha256':'old','suspects':['extra_alpha_components']}]};self.assertFalse(tool.apply_review(result)['passed']);result['rows'][0]['sha256']='current';self.assertTrue(tool.apply_review(result)['passed'])
class GameplayInventory(unittest.TestCase):
 def test_gameplay_sprites_are_not_filtered_by_ui_name(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);nodes=[{'name':name,'comps':{'sprite':{'frame':name}}} for name in ['snowball','wild','block','crystal','ice','background_bg_01','icon_normal']];(root/'play.json').write_text(json.dumps({'nodes':nodes}));self.assertEqual(tool.captured_frames(root),['block','crystal','ice','icon_normal','snowball','wild'])
 def test_empty_dump_has_no_invented_coverage(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(tool.captured_frames(Path(d)),[])
if __name__=='__main__':unittest.main()
