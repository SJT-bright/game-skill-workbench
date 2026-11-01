"""TexturePacker / Cocos .plist atlases go through the same v7.8 slice checks (format 2 and 3, rotated frames, dumps)."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,plistlib,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_atlas_slices import audit,check_project

def sheet(path):
 im=Image.new('RGBA',(256,128));d=ImageDraw.Draw(im)
 d.rounded_rectangle((10,10,69,69),10,fill='#00b5b5')   # icon body
 d.rectangle((80,10,99,69),fill='#e0a020')               # icon's neighbour
 d.ellipse((10,80,69,119),fill='#c03070')                # unprefixed piece
 d.rectangle((75,80,120,119),fill='#3070c0')             # piece's neighbour
 d.ellipse((130,10,159,89),fill='#60c040')               # rotated frame: 80x30 at runtime, 30x80 in the texture
 d.rectangle((170,10,249,49),fill='#806040')             # ground tile
 im.save(path)

def r2(x,y,w,h):return '{{%d,%d},{%d,%d}}'%(x,y,w,h)
def fmt2(frames):
 # frames: name -> (x,y,w,h,rotated) with w/h the unrotated size, as TexturePacker writes them
 out={n:{'frame':r2(x,y,w,h),'offset':'{0,0}','rotated':rot,'sourceColorRect':r2(0,0,w,h),'sourceSize':'{%d,%d}'%(w,h)} for n,(x,y,w,h,rot) in frames.items()}
 return {'frames':out,'metadata':{'format':2,'realTextureFileName':'sheet.png','textureFileName':'sheet.png','size':'{256,128}'}}
def fmt3(frames,aliases=None):
 out={n:{'aliases':(aliases or {}).get(n,[]),'spriteOffset':'{0,0}','spriteSize':'{%d,%d}'%(w,h),'spriteSourceSize':'{%d,%d}'%(w,h),'textureRect':r2(x,y,w,h),'textureRotated':rot} for n,(x,y,w,h,rot) in frames.items()}
 return {'frames':out,'metadata':{'format':3,'realTextureFileName':'sheet.png','textureFileName':'sheet.png','size':'{256,128}'}}

GOOD={'icon_star.png':(8,8,64,64,False),'ui/piece.png':(8,78,64,44,False),'piece_rot.png':(128,8,84,34,True),'ground_01.png':(168,8,84,44,False)}

class PlistAtlas(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='plist atlas ');self.p=Path(self.tmp.name);sheet(self.p/'sheet.png')
 def tearDown(self):self.tmp.cleanup()
 def run_fmt(self,maker,frames,**kw):
  f=self.p/'sheet.plist';f.write_bytes(plistlib.dumps(maker(frames,**kw)));return audit(f)
 def kinds(self,r):return {(i['frame'],i['kind']) for i in r['issues']}

 def test_complete_frames_pass_in_format_2_and_3(self):
  for maker,adapter in ((fmt2,'plist_format2_v1'),(fmt3,'plist_format3_v1')):
   r=self.run_fmt(maker,GOOD)
   self.assertTrue(r['passed'],(adapter,r['issues']));self.assertEqual(r['adapter'],adapter)
   roles={x['frame']:x['role'] for x in r['frames']}
   self.assertEqual(roles,{'icon_star.png':'single_body','ui/piece.png':'scope_body','piece_rot.png':'scope_body'})
   self.assertEqual(r['declared_frames']['piece_rot.png'],[128,8,34,84])   # texture area: w/h swapped
   self.assertEqual(r['runtime_frames']['piece_rot.png'],[128,8,84,34])    # runtime size: unrotated
   self.assertEqual({x['frame']:x['reason'] for x in r['skipped']},{'ground_01.png':'tileset/sliced name'})

 def test_split_sheet_names_are_checked_not_skipped(self):
  # FrogJump running.plist: a run cycle exported as tile000..tile011 is a character, not a tileset.
  r=self.run_fmt(fmt3,{'tile003.png':GOOD['ui/piece.png'],'ground_01.png':GOOD['ground_01.png']})
  self.assertEqual({x['frame']:x['role'] for x in r['frames']},{'tile003.png':'scope_body'});self.assertEqual([x['frame'] for x in r['skipped']],['ground_01.png'])

 def test_rotated_frame_read_unswapped_would_be_cut(self):
  # Guard that the swap matters: the same numbers as a non-rotated frame cut the ellipse.
  r=self.run_fmt(fmt2,{'piece_rot.png':(128,8,84,34,False)})
  self.assertIn(('piece_rot.png','connected_body_cut_by_rect'),self.kinds(r))

 def test_neighbour_strip_is_refused(self):
  for maker in (fmt2,fmt3):
   r=self.run_fmt(maker,dict(GOOD,**{'icon_star.png':(8,8,76,64,False),'ui/piece.png':(8,78,72,44,False)}))
   k=self.kinds(r)
   self.assertIn(('icon_star.png','foreign_alpha_island'),k);self.assertIn(('ui/piece.png','edge_fragment'),k)

 def test_cut_body_is_refused(self):
  for maker in (fmt2,fmt3):
   r=self.run_fmt(maker,dict(GOOD,**{'icon_star.png':(8,25,64,47,False),'ui/piece.png':(8,78,40,44,False)}))
   k=self.kinds(r)
   self.assertIn(('icon_star.png','connected_body_cut_by_rect'),k);self.assertIn(('ui/piece.png','connected_body_cut_by_rect'),k)

 def test_missing_texture_keeps_v78_handling(self):
  (self.p/'sheet.png').unlink()
  r=self.run_fmt(fmt2,{'ui/piece.png':GOOD['ui/piece.png']})
  self.assertEqual(r['skipped'],[{'frame':'ui/piece.png','reason':'texture missing: sheet.png'}])
  with self.assertRaises(FileNotFoundError):self.run_fmt(fmt2,{'icon_star.png':GOOD['icon_star.png']})

 def test_frames_option_matches_bare_names(self):
  f=self.p/'sheet.plist';f.write_bytes(plistlib.dumps(fmt2(GOOD)))
  self.assertEqual(set(audit(f,only=['icon_star'])['declared_frames']),{'icon_star.png'})
  with self.assertRaises(ValueError):audit(f,only=['icon_missing'])

 def project(self,maker=fmt2,frames=GOOD,**kw):
  res=self.p/'proj/assets/res';res.mkdir(parents=True);(self.p/'sheet.png').rename(res/'sheet.png')
  (res/'sheet.plist').write_bytes(plistlib.dumps(maker(frames,**kw)))
  (res/'boom.plist').write_bytes(plistlib.dumps({'maxParticles':40,'textureFileName':'boom.png','duration':-1}))
  (res/'Info.plist').write_bytes(plistlib.dumps({'CFBundleName':'x','CFBundleVersion':'1'}))
  (self.p/'proj/assets/docs').mkdir();(self.p/'proj/assets/docs/sheet.plist').write_bytes((res/'sheet.plist').read_bytes())
  (self.p/'dumps').mkdir();return self.p/'proj',self.p/'dumps'
 def dump(self,dumps,sprites,name='001-ui-dump-home.json'):
  (dumps/name).write_text(json.dumps({'nodes':[{'name':'n%d'%i,'comps':{'sprite':{'frame':f,'frame_size':s}}} for i,(f,s) in enumerate(sprites)]}))

 def test_check_project_finds_plist_and_reads_dump_frames(self):
  proj,dumps=self.project()
  self.dump(dumps,[('icon_star',[64,64]),('piece_rot',[84,34]),('ui/piece.png',[64,44]),('piece',[64,44])])
  r=check_project(proj,dumps)
  self.assertTrue(r['applicable'] and r['passed'],r['issues'])
  self.assertEqual([Path(a['manifest']).name for a in r['atlases']],['sheet.plist'])   # no particle / Info.plist / docs copy
  self.assertEqual(r['runtime_observations'],4)

 def test_check_project_reports_stale_runtime_size(self):
  proj,dumps=self.project()
  self.dump(dumps,[('icon_star.png',[64,64]),('piece_rot',[34,84])])
  r=check_project(proj,dumps)
  self.assertEqual({(i['frame'],i['kind']) for i in r['issues']},{('piece_rot','runtime_size_differs_from_manifest')})

 def test_check_project_format3_alias_in_dump(self):
  proj,dumps=self.project(fmt3,GOOD,aliases={'icon_star.png':['icon_star_alt.png']})
  self.dump(dumps,[('icon_star_alt',[64,64])])
  r=check_project(proj,dumps);self.assertTrue(r['passed'],r['issues']);self.assertEqual(r['runtime_observations'],1)

 def test_project_without_sprite_sheet_plist_is_not_applicable(self):
  proj,dumps=self.project();(proj/'assets/res/sheet.plist').unlink()
  r=check_project(proj);self.assertFalse(r['applicable']);self.assertEqual(r['checked'],0)

class PackedSheet(unittest.TestCase):
 """Calibration controls from real packer output: padding 0, extrude 1, trimmed rects."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(prefix='packed plist ');self.p=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def run_sheet(self,im,frames):
  im.save(self.p/'sheet.png');f=self.p/'sheet.plist';f.write_bytes(plistlib.dumps(fmt2(frames)));return audit(f)
 def kinds(self,r):return {(i['frame'],i['kind']) for i in r['issues']}

 def test_touching_neighbours_with_zero_padding_pass(self):
  # DessertMatch fruits.plist: 93x96 cells packed edge to edge, each body touches the next one.
  im=Image.new('RGBA',(160,40));d=ImageDraw.Draw(im)
  for i in range(4):d.rounded_rectangle((i*40,0,i*40+39,39),8,fill='#d06030')
  r=self.run_sheet(im,{'cell_%d.png'%i:(i*40,0,40,40,False) for i in range(4)})
  self.assertTrue(r['passed'],r['issues'])

 def extruded(self,spill=0):
  # BallPopParty avatar.plist: TexturePacker extrude 1 repeats every edge pixel 1 px outward.
  im=Image.new('RGBA',(240,60));d=ImageDraw.Draw(im);frames={}
  for i in range(4):
   x=10+i*56;d.rounded_rectangle((x,10,x+39,49),6,fill='#4080d0');frames['ball_%d.png'%i]=(x,10,40,40,False)
  a=im.copy()
  for x,y,w,h,_ in frames.values():
   for k in range(w):a.putpixel((x+k,y-1),im.getpixel((x+k,y)));a.putpixel((x+k,y+h),im.getpixel((x+k,y+h-1)))
   for k in range(h):a.putpixel((x-1,y+k),im.getpixel((x,y+k)));a.putpixel((x+w,y+k),im.getpixel((x+w-1,y+k)))
  if spill:ImageDraw.Draw(a).rectangle((10+40,20,10+40+spill,40),fill='#4080d0')   # ball_0 really runs past its rect
  return a,frames
 def test_extrusion_ring_is_not_a_cut(self):
  im,frames=self.extruded();r=self.run_sheet(im,frames)
  self.assertTrue(r['passed'],r['issues']);self.assertEqual({x.get('extrude') for x in r['frames']},{1})
 def test_body_running_past_the_extrusion_is_a_cut(self):
  im,frames=self.extruded(spill=3);r=self.run_sheet(im,frames)
  self.assertEqual(self.kinds(r),{('ball_0.png','connected_body_cut_by_rect')})

 def test_trimmed_sparkle_passes_but_strip_and_neighbour_sliver_fail(self):
  # effect.plist: sparkles sit on the trimmed bbox edge. A long thin strip, or pixels of a declared neighbour, do not.
  im=Image.new('RGBA',(200,80));d=ImageDraw.Draw(im)
  d.ellipse((10,14,69,69),fill='#40c0f0');d.rectangle((38,4,43,9),fill='#40c0f0')        # ring_a + its sparkle dot on top
  d.ellipse((90,14,149,69),fill='#40c0f0');d.rectangle((100,4,139,6),fill='#40c0f0')     # ring_b + a 40x3 strip on top
  d.rectangle((160,4,199,69),fill='#e08020')                                             # neighbour frame
  frames={'ring_a.png':(10,4,60,66,False),'ring_b.png':(90,4,60,66,False),'ring_c.png':(90,14,74,56,False),'box.png':(160,4,40,66,False)}
  r=self.run_sheet(im,frames);k=self.kinds(r)
  self.assertNotIn('ring_a.png',{f for f,_ in k})
  self.assertIn(('ring_b.png','edge_fragment'),k);self.assertIn(('ring_c.png','edge_fragment'),k)

if __name__=='__main__':unittest.main()
