from pathlib import Path
from PIL import Image,ImageDraw
import tempfile,json,sys
sys.path.insert(0,str(Path(__file__).parent))
from audit_atlas_slices import audit

def run():
 checks={}
 with tempfile.TemporaryDirectory(prefix='slice positive and negative controls ') as tmp:
  p=Path(tmp);im=Image.new('RGBA',(128,180));draw=ImageDraw.Draw(im);draw.rounded_rectangle((10,10,69,69),10,fill='#00b5b5');draw.rounded_rectangle((10,90,69,149),10,fill='#00b5b5');draw.ellipse((90,20,100,30),fill='yellow');draw.ellipse((90,50,100,60),fill='yellow');im.save(p/'sheet.png')
  m={'textures':{'sheet':{'width':128,'height':180}},'frames':{'icon_normal':{'texture':'sheet','rect':[8,8,64,64]},'digit_:':{'slice_role':'two_marks','texture':'sheet','rect':[88,18,15,45]}}};f=p/'frames.json';f.write_text(json.dumps(m));checks['complete_icon_and_intentional_colon_pass']=audit(f)['passed']
  m['frames']['icon_normal']['rect']=[8,8,64,100];f.write_text(json.dumps(m));checks['foreign_neighbour_strip_refused']=any(i['kind']=='foreign_alpha_island' for i in audit(f)['issues'])
  m['frames']['icon_normal']['rect']=[8,25,64,47];f.write_text(json.dumps(m));checks['rounded_top_cut_refused']=any(i['kind']=='connected_body_cut_by_rect' for i in audit(f)['issues'])
  m['frames']['icon_normal']['rect']=[8,8,64,64];m['frames']['digit_:']['rect']=[88,18,15,15];f.write_text(json.dumps(m));checks['missing_intended_colon_mark_refused']=not audit(f)['passed']
 print(json.dumps({'passed':all(checks.values()),'cases':checks}));assert all(checks.values())
if __name__=='__main__':run()
