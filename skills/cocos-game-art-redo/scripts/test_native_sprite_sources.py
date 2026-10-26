"""Synthetic PNG source signals, not runtime or art acceptance."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
import check_native_sprite_sources as tool
UUID='01234567-89ab-cdef-0123-456789abcdef'
class SpriteSourceContracts(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def frame(self,bundle='assets/main',name='icon',shape='normal',uuid=UUID):
  folder=self.root/bundle;(folder/'import').mkdir(parents=True,exist_ok=True);(folder/'native').mkdir(exist_ok=True)
  (folder/'import'/f'{name}.json').write_text(json.dumps([1,[uuid],None,None,None,[{'name':name}]]))
  im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
  if shape=='normal':d.ellipse((12,12,51,51),fill='white')
  elif shape=='cut':d.rectangle((0,8,40,55),fill='white')
  elif shape=='parts':d.rectangle((4,4,23,23),fill='white');d.rectangle((38,38,57,57),fill='white')
  im.save(folder/'native'/f'{uuid}.png');return folder/'native'/f'{uuid}.png'
 def test_main_and_nonresources_subpackage_are_supported(self):
  self.frame();self.frame('subpackages/forest','other');r=tool.check(self.root,['icon','other']);self.assertEqual(r['status'],'no_signals');self.assertEqual(r['checked'],2);self.assertEqual(r['art_verdict'],'not_assessed')
 def test_straight_edge_and_fragments_need_review_not_confirmed_defect(self):
  self.frame(shape='cut');r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'needs_review');self.assertEqual(r['art_verdict'],'not_assessed')
  self.frame(shape='parts');self.assertEqual(tool.check(self.root,['icon'])['status'],'needs_review')
 def test_legal_multiple_parts_are_not_forced_through_single_body(self):
  self.frame(shape='parts');r=tool.check(self.root,['icon'],role='multi_body');self.assertEqual(r['status'],'not_applicable');self.assertIsNone(r['passed'])
 def test_empty_or_missing_target_is_incomplete_and_cli_nonzero(self):
  self.assertFalse(tool.check(self.root,['icon'])['passed'])
  p=Path(tool.__file__);r=subprocess.run([sys.executable,'-B',str(p),str(self.root),'icon'],capture_output=True,text=True)
  self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['status'],'incomplete')
 def test_duplicate_names_and_broken_image_are_incomplete(self):
  self.frame();self.frame('subpackages/other');self.assertEqual(tool.check(self.root,['icon'])['status'],'incomplete')
  p=self.frame(name='broken');p.write_bytes(b'bad png');self.assertEqual(tool.check(self.root,['broken'])['status'],'incomplete')
 def test_shared_texture_analyzed_once_and_originals_unchanged(self):
  p=self.frame();folder=p.parent.parent;(folder/'import/alias.json').write_text(json.dumps([1,[UUID],None,None,None,[{'name':'alias'}]]));before=p.read_bytes()
  with patch.object(tool,'inspect_texture',wraps=tool.inspect_texture) as inspect:r=tool.check(self.root,['icon','alias'])
  self.assertTrue(r['passed']);self.assertEqual(inspect.call_count,1);self.assertEqual(p.read_bytes(),before)
if __name__=='__main__':unittest.main()
