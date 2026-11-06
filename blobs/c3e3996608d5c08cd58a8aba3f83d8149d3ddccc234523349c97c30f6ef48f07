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
 def test_duplicate_good_names_exhaustively_inspected_without_runtime_binding(self):
  self.frame();self.frame('subpackages/other');r=tool.check(self.root,['icon'])
  self.assertEqual(r['status'],'no_signals');self.assertEqual(r['checked'],2)
  self.assertEqual(r['candidate_counts'],{'icon':2});self.assertTrue(all(x['candidate_count']==2 for x in r['rows']))
  self.assertEqual(r['runtime_binding'],'not_assessed');self.assertEqual(r['art_verdict'],'not_assessed')
 def test_duplicate_good_and_bad_candidate_cannot_pass(self):
  self.frame();bad=self.frame('subpackages/other',shape='cut')
  r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'needs_review');self.assertFalse(r['passed']);self.assertEqual(r['checked'],2)
  bad.write_bytes(b'bad png');r=tool.check(self.root,['icon'])
  self.assertEqual(r['status'],'incomplete');self.assertFalse(r['passed']);self.assertEqual(r['candidate_counts'],{'icon':2});self.assertTrue(r['errors'])
 def test_duplicate_empty_alpha_candidate_cannot_pass(self):
  self.frame();self.frame('subpackages/other',shape='empty');r=tool.check(self.root,['icon'])
  self.assertEqual(r['status'],'needs_review');self.assertTrue(any('empty_alpha' in x['suspects'] for x in r['rows']))
 def test_broken_unique_image_is_incomplete(self):
  p=self.frame(name='broken');p.write_bytes(b'bad png');self.assertEqual(tool.check(self.root,['broken'])['status'],'incomplete')
 def test_multiple_uuid_candidates_are_all_checked(self):
  p=self.frame();extra=p.parent/'nested'/p.name;extra.parent.mkdir();extra.write_bytes(p.read_bytes())
  r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'no_signals');self.assertEqual(r['checked'],2)
  extra.write_bytes(b'bad png');self.assertEqual(tool.check(self.root,['icon'])['status'],'incomplete')
 def test_missing_and_outside_candidate_still_incomplete(self):
  p=self.frame();p.unlink();self.assertEqual(tool.check(self.root,['icon'])['status'],'incomplete')
  with tempfile.TemporaryDirectory() as outside:
   external=Path(outside)/'image.png';external.write_bytes(b'outside');p.symlink_to(external)
   r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'incomplete');self.assertTrue(any('outside Native root' in x['error'] for x in r['errors']))
 def test_review_is_exact_frame_and_sha_for_each_candidate(self):
  self.frame(shape='cut');self.frame('subpackages/other',shape='parts');r=tool.check(self.root,['icon'])
  review=self.root/'docs/art/sprite-source-review.json';review.parent.mkdir(parents=True)
  row=r['rows'][0];entry={'frame':'icon','sha256':row['sha256'],'normal_signals':row['suspects'],'why':'Fixture-specific visual review'}
  review.write_text(json.dumps({'reviews':[entry]}));r=tool.apply_review(r)
  self.assertEqual(r['status'],'needs_review');self.assertEqual(sum('human_review' in x for x in r['rows']),1)
  review.write_text(json.dumps({'reviews':[dict(entry,frame='other')]}));r=tool.apply_review(tool.check(self.root,['icon']))
  self.assertEqual(sum('human_review' in x for x in r['rows']),0)
 def test_duplicate_source_names_are_all_checked(self):
  (self.root/'project.json').write_text('{}')
  for bundle,shape in [('assets/main','normal'),('assets/other','cut')]:
   p=self.frame(bundle,shape=shape);Path(str(p)+'.meta').write_text(json.dumps({'subMetas':{'icon':{}}}))
  r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'needs_review');self.assertEqual(r['candidate_counts'],{'icon':2})
 def test_illegal_texture_uuid_remains_incomplete(self):
  self.frame();p=self.root/'assets/main/import/icon.json';doc=json.loads(p.read_text());doc[1][0]='../../outside';p.write_text(json.dumps(doc))
  r=tool.check(self.root,['icon']);self.assertEqual(r['status'],'incomplete');self.assertTrue(any('unsupported texture UUID' in x['error'] for x in r['errors']))
 def test_shared_texture_analyzed_once_and_originals_unchanged(self):
  p=self.frame();folder=p.parent.parent;(folder/'import/alias.json').write_text(json.dumps([1,[UUID],None,None,None,[{'name':'alias'}]]));before=p.read_bytes()
  with patch.object(tool,'inspect_texture',wraps=tool.inspect_texture) as inspect:r=tool.check(self.root,['icon','alias'])
  self.assertTrue(r['passed']);self.assertEqual(inspect.call_count,1);self.assertEqual(p.read_bytes(),before)
if __name__=='__main__':unittest.main()
