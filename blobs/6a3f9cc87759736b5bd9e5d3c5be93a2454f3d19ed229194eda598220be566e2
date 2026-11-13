"""Actual FNT geometry routing, including missing/ambiguous negative controls."""
import json,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
import check_native_sprite_sources as tool
class BitmapGlyphRoutes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'assets').mkdir();(self.root/'project.json').write_text('{}');self.dumps=self.root/'dumps';self.dumps.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def font(self,name='numbers',parts=False,offset=0):
  d=self.root/'assets'/name;d.mkdir();im=Image.new('RGBA',(64,64));draw=ImageDraw.Draw(im);draw.ellipse((16+offset,16,44+offset,44),fill='white')
  if parts:draw.rectangle((49,49,52,52),fill='white')
  im.save(d/'digits.png');(d/'digits.fnt').write_text('common lineHeight=48 scaleW=64 scaleH=64 pages=1\npage id=0 file="digits.png"\nchar id=48 x=8 y=8 width=48 height=48 page=0\n');return d/'digits.fnt'
 def run_route(self,size=(48,48)):
  (self.dumps/'ui-dump-real.json').write_text(json.dumps({'nodes':[{'comps':{'sprite':{'frame':'digit_0','frame_size':list(size)}}}]}))
  return tool.route_other_sources(tool.check(self.root,['digit_0']),self.dumps,None)
 def test_real_page_geometry_and_pixel_identity_resolve(self):
  self.font();r=self.run_route();self.assertEqual(r['missing'],[]);self.assertTrue(r['passed']);row=r['rows'][0];self.assertEqual(row['rect'],[8,8,48,48]);self.assertEqual(row['char_id'],48);self.assertEqual(len(row['manifest_sha256']),64);self.assertEqual(row['resource_kind'],'bitmap_font_glyph')
 def test_name_without_matching_observed_size_stays_missing(self):
  self.font();r=self.run_route((47,48));self.assertEqual(r['missing'],['digit_0']);self.assertFalse(r['passed'])
 def test_invalid_page_dimensions_stay_missing(self):
  f=self.font();f.write_text(f.read_text().replace('scaleW=64','scaleW=63'));self.assertEqual(self.run_route()['missing'],['digit_0'])
 def test_outside_rectangle_stays_missing(self):
  f=self.font();f.write_text(f.read_text().replace('x=8','x=32'));self.assertEqual(self.run_route()['missing'],['digit_0'])
 def test_distinct_same_size_candidates_are_not_guessed(self):
  self.font();self.font('other',offset=2);self.assertEqual(self.run_route()['missing'],['digit_0'])
 def test_identical_candidates_exhaustively_recorded(self):
  self.font();self.font('other');r=self.run_route();self.assertTrue(r['passed']);self.assertEqual(len(r['rows']),2);self.assertTrue(all(x['candidate_count']==2 for x in r['rows']))
 def test_real_source_signals_are_retained(self):
  self.font(parts=True);r=self.run_route();self.assertEqual(r['missing'],[]);self.assertEqual(r['status'],'needs_review');self.assertIn('extra_alpha_components',r['rows'][0]['suspects'])
 def test_missing_page_stays_missing(self):
  f=self.font();(f.parent/'digits.png').unlink();self.assertEqual(self.run_route()['missing'],['digit_0'])
if __name__=='__main__':unittest.main()
