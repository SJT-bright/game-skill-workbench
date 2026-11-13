"""HUD glyph support keeps actual source geometry, placement and sequence failures."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
import audit_top_bar as tool
class BitmapResourceCounts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();(self.root/'assets').mkdir();(self.root/'docs').mkdir();(self.root/'docs/board.txt').write_text('localize');self.old=tool.PROJECT_FOR_SCOPE;tool.PROJECT_FOR_SCOPE=self.root;self.oldseq=tool.ORIGINAL_SEQUENTIAL
  im=Image.new('RGBA',(48,16));d=ImageDraw.Draw(im)
  for x in [0,16,32]:d.ellipse((x+2,2,x+13,13),fill='white')
  im.save(self.root/'assets/font.png');(self.root/'assets/font.fnt').write_text('common scaleW=48 scaleH=16\npage id=0 file="font.png"\nchar id=48 x=0 y=0 width=16 height=16 page=0\nchar id=53 x=16 y=0 width=16 height=16 page=0\nchar id=47 x=32 y=0 width=16 height=16 page=0\n')
 def tearDown(self):tool.PROJECT_FOR_SCOPE=self.old;tool.ORIGINAL_SEQUENTIAL=self.oldseq;self.tmp.cleanup()
 def nodes(self):
  prefix='Canvas/Energy/Value/Number';return [{'path':prefix+'/G'+str(i),'rect':[.2+.04*i,.05,.03,.03],'order':i+2,'comps':{'sprite':{'frame':frame,'frame_size':[16,16]}}} for i,frame in enumerate(['digit_5','symbol_slash','digit_5'])]
 def test_actual_fnt_glyphs_are_read_without_a_fake_label(self):
  n=tool.bitmap_count(self.nodes(),'Canvas/Energy/Value/Number');self.assertEqual(tool.count_text(n),'5/5');self.assertNotIn('label',n['comps']);self.assertTrue(n['_bitmap_sources']);self.assertAlmostEqual(n['rect'][2],.11)
 def test_wrong_geometry_and_unknown_glyph_are_not_accepted(self):
  nodes=self.nodes();nodes[0]['comps']['sprite']['frame_size']=[15,16];self.assertIsNone(tool.bitmap_count(nodes,'Canvas/Energy/Value/Number'))
  nodes=self.nodes();nodes[0]['comps']['sprite']['frame']='digit_9';self.assertIsNone(tool.bitmap_count(nodes,'Canvas/Energy/Value/Number'))
 def test_stacked_rows_are_not_concatenated(self):
  nodes=self.nodes();nodes[1]['rect'][1]=.2;self.assertIsNone(tool.bitmap_count(nodes,'Canvas/Energy/Value/Number'))
 def test_explicit_energy_art_frame_is_found_next_to_real_value(self):
  nodes=self.nodes();nodes.append({'path':'Canvas/Energy/Value/Icon','rect':[.1,.05,.03,.03],'order':1,'comps':{'sprite':{'frame':'img_energy'}}})
  count,box,icon=tool.find({'nodes':nodes},{'kind':'energy','icon':'lightning','icon_frame':'img_energy','node':'Canvas/Energy','count':'Canvas/Energy/Value/Number'});self.assertEqual(tool.count_text(count),'5/5');self.assertEqual(icon['comps']['sprite']['frame'],'img_energy');self.assertEqual(box['path'],'Canvas/Energy')
 def test_linear_original_route_requires_real_same_source_bytes(self):
  src=self.root/'original.js';cur=self.root/'assets/levels.js';src.write_text('original records');cur.write_bytes(src.read_bytes());sha=hashlib.sha256(src.read_bytes()).hexdigest();(self.root/'docs/levels').mkdir();f=self.root/'docs/levels/level_plan.json';f.write_text(json.dumps({'mode':'levels','navigation':{'mode':'sequential','map':'none','level_selection':False},'original_data':{'source':str(src),'sha256':sha},'current_data':{'source':'assets/levels.js','sha256':sha}}));self.assertTrue(tool.original_sequential(self.root));cur.write_text('changed');self.assertFalse(tool.original_sequential(self.root))
 def sequence(self,widths,values):
  run=self.root/'run';run.mkdir();purposes=['home','result_win','home']
  for i,(w,v) in enumerate(zip(widths,values)):
   nodes=[] if v is None else [{'path':'Canvas/Count','rect':[.1,.05,.1,.05],'order':1,'comps':{'label':{'string':str(v)}}}]
   (run/('%03d-ui-dump-state.json'%i)).write_text(json.dumps({'tool':'ui_dump','schema':1,'producer':'ego_page.dump_ui','screen':'state'+str(i),'kind':'page','purpose':purposes[i],'page':{'width':w,'height':800,'dpr':1},'nodes':nodes}))
  checks=[];tool.ORIGINAL_SEQUENTIAL=False;tool.live([run],[{'kind':'currency','name':'Coins','icon':'coin','count':'Canvas/Count'}],None,lambda a,b,c:checks.append((a,b,c)));return checks
 def test_different_viewports_are_not_paired_as_one_live_sequence(self):self.assertFalse(self.sequence([375,375,390],[0,None,10])[0][1])
 def test_same_viewport_real_increase_passes(self):self.assertTrue(self.sequence([375,375,375],[0,None,10])[0][1])
 def test_same_viewport_real_drop_fails(self):self.assertFalse(self.sequence([375,375,375],[20,None,10])[0][1])
if __name__=='__main__':unittest.main()
