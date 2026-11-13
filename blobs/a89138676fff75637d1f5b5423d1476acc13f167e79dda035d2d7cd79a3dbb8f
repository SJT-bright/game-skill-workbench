"""Explicit plist parts preserve semantics while connected clipping remains checked."""
import tempfile,unittest,plistlib
from pathlib import Path
from PIL import Image,ImageDraw
from audit_atlas_slices import audit
class DeclaredPlistParts(unittest.TestCase):
 def test_default_rejects_parts_explicit_reason_allows_and_cut_still_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);im=Image.new('RGBA',(100,60));d=ImageDraw.Draw(im);d.rectangle((10,10,35,45),fill='white');d.rectangle((45,10,65,45),fill='white');im.save(p/'sheet.png')
   raw={'frames':{'btn_words.png':{'frame':'{{8,8},{60,40}}','sourceSize':'{60,40}','offset':'{0,0}','rotated':False}},'metadata':{'format':2,'textureFileName':'sheet.png'}};f=p/'sheet.plist'
   def run():f.write_bytes(plistlib.dumps(raw));return audit(f)
   self.assertIn('foreign_alpha_island',{x['kind'] for x in run()['issues']})
   v=raw['frames']['btn_words.png'];v['slice_role']='multi_body';self.assertIn('multipart_reason_missing',{x['kind'] for x in run()['issues']})
   v['part_reason']='Two intentional letters in the exact source word';self.assertTrue(run()['passed'])
   v['frame']='{{8,20},{60,28}}';self.assertIn('connected_body_cut_by_rect',{x['kind'] for x in run()['issues']})
if __name__=='__main__':unittest.main()
