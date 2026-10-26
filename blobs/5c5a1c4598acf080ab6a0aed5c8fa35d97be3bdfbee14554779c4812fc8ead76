"""Validate measured phone-content bounds. No project-specific paths or accepted failures."""
import argparse,hashlib,json,math,struct
from pathlib import Path

def inspect(path):
 d=json.loads(Path(path).read_text());invalid=[];issues=[]
 def rect(r):return isinstance(r,list)and len(r)==4 and all(isinstance(v,(int,float))and math.isfinite(v)for v in r)and r[2]>0 and r[3]>0
 def inside(a,b,t=1):return a[0]>=b[0]-t and a[1]>=b[1]-t and a[0]+a[2]<=b[0]+b[2]+t and a[1]+a[3]<=b[1]+b[3]+t
 if d.get('producer')!='real_cocos_phone_boundary' or not d.get('calibrated_to_full_screenshot'):invalid.append('unverified coordinate producer')
 s=Path(d.get('screenshot',''))
 if not s.is_file()or hashlib.sha256(s.read_bytes()).hexdigest()!=d.get('screenshot_sha256'):invalid.append('missing/changed screenshot')
 if s.is_file():
  raw=s.read_bytes()
  if raw[:8]!=b'\x89PNG\r\n\x1a\n':invalid.append('screenshot must be original PNG')
  else:
   pixels=list(struct.unpack('>II',raw[16:24]));v=d.get('viewport',{});scale=d.get('screenshot_css_scale',[1,1])
   if pixels!=d.get('screenshot_pixel_size',pixels)or len(scale)!=2 or not v.get('width')or not v.get('height') or abs(scale[0]-pixels[0]/v['width'])>.001 or abs(scale[1]-pixels[1]/v['height'])>.001 or abs(scale[0]-scale[1])>.005:invalid.append('PNG pixels/viewport coordinate calibration mismatch')
 if not d.get('bundle_sha256')or len(d['bundle_sha256'])!=64:invalid.append('missing bundle identity')
 if not d.get('requested_viewport') or d['requested_viewport']!=d.get('viewport'):invalid.append('requested/actual viewport mismatch')
 if d.get('render_ready') is not True or d.get('loading_guards') or d.get('pending_assets') or any('/ArtworkLoadingGuard/'in x.get('path','')or'/GameLoadingGuard/'in x.get('path','')for x in d.get('labels',[])):invalid.append('page not proven ready or active loading guard/assets')
 stage=d.get('content_rect');canvas=d.get('canvas_rect');targets=d.get('targets',[])
 if not rect(stage)or not rect(canvas):invalid.append('missing measurable game/background bounds')
 if not targets:invalid.append('empty interactive targets')
 for target in targets:
  if not target.get('loaded')or not rect(target.get('rect')):invalid.append('unloaded/invalid target '+target.get('path','?'))
 if len(d.get('samples',[]))<3 or d.get('maximum_target_drift_css_px',999)>1:invalid.append('layout not stable')
 if not invalid:
  for target in targets:
   if not inside(target['rect'],stage):issues.append({'code':'control_outside_game_content','path':target['path'],'rect':target['rect'],'content_rect':stage})
   if not inside(target['rect'],canvas):issues.append({'code':'control_outside_canvas','path':target['path']})
  phone=d.get('phone_rect')
  if d.get('delivery_preview')and d['viewport']['width']>d.get('preview_max_css_width',430):
   if not rect(phone):issues.append({'code':'desktop_delivery_missing_phone_frame'})
   elif phone[2]>d.get('preview_max_css_width',430)+1 or phone[2]>=phone[3]:issues.append({'code':'delivery_frame_not_phone_sized','rect':phone})
  if rect(phone) and not inside(canvas,phone):issues.append({'code':'canvas_outside_phone_frame'})
 return {'capture':str(Path(path).resolve()),'bundle_sha256':d.get('bundle_sha256'),'status':'not_inspectable'if invalid else 'fail'if issues else 'pass','invalid':invalid,'issues':issues,'passed':not invalid and not issues}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('captures',nargs='+');a.add_argument('--out',required=True);o=a.parse_args();rows=[inspect(p)for p in o.captures];result={'tool':'check_phone_boundary','passed':all(r['passed']for r in rows),'rows':rows};Path(o.out).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['passed']else 1)
