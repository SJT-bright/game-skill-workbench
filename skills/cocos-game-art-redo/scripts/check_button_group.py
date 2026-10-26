import json,sys,math,hashlib
from pathlib import Path

def check(d):
 errors=[]
 screenshot=Path(d.get('screenshot',''))
 if not screenshot.is_file() or hashlib.sha256(screenshot.read_bytes()).hexdigest()!=d.get('screenshot_sha256'):errors.append({'code':'missing_or_mismatched_screenshot'})
 if not d.get('bundle_sha256'):errors.append({'code':'missing_bundle_binding'})
 groups=d.get('groups',[]);v=d.get('viewport',{});W=v.get('width',0);H=v.get('height',0)
 if d.get('producer')!='real_cocos_sprite_geometry' or len(groups)<2 or not W or not H:return [{'code':'invalid_capture'}]
 boxes=[]
 for g in groups:
  ss=g.get('sprites',[])
  if not ss or any(not s.get('loaded') for s in ss):errors.append({'code':'missing_rendered_sprite','slot':g['slot']});continue
  rs=[s['rect'] for s in ss]
  if any(not all(math.isfinite(r[k]) for k in ['x','y','width','height']) or r['width']<=0 or r['height']<=0 for r in rs):errors.append({'code':'invalid_geometry','slot':g['slot']});continue
  x=min(r['x'] for r in rs);y=min(r['y'] for r in rs);right=max(r['x']+r['width'] for r in rs);bottom=max(r['y']+r['height'] for r in rs)
  b={'slot':g['slot'],'x':x,'y':y,'right':right,'bottom':bottom};boxes.append(b)
  if x < -1 or y < -1 or right>W+1 or bottom>H+1:errors.append({'code':'sprite_outside_viewport','slot':g['slot'],'bounds':b})
 for i,a in enumerate(boxes):
  for b in boxes[i+1:]:
   dx=min(a['right'],b['right'])-max(a['x'],b['x']);dy=min(a['bottom'],b['bottom'])-max(a['y'],b['y'])
   if dx>1 and dy>1:errors.append({'code':'independent_button_overlap','slots':[a['slot'],b['slot']],'intersection_css_px':{'width':round(dx,3),'height':round(dy,3)}})
 return errors
if __name__=='__main__':
 all_reports=[]
 for arg in sys.argv[1:]:
  p=Path(arg);d=json.loads(p.read_text());errors=check(d);all_reports.append({'capture':str(p),'viewport':d.get('viewport'),'passed':not errors,'errors':errors})
 print(json.dumps(all_reports,ensure_ascii=False,indent=2));sys.exit(1 if any(not r['passed'] for r in all_reports) else 0)
