#!/usr/bin/env python3
"""Check declared real collection geometry and screenshot preview neutrality."""
import json,sys,hashlib
from pathlib import Path
from PIL import Image

def _check(path):
 d=json.loads(Path(path).read_text()); errors=[]
 if d.get('producer')!='real_cocos_collection_geometry' or not d.get('rows'):
  return {'passed':False,'errors':[{'kind':'missing_runtime_capture'}]}
 if not d.get('bundle_file') or not d.get('bundle_sha256') or hashlib.sha256(Path(d['bundle_file']).read_bytes()).hexdigest()!=d['bundle_sha256']:
  errors.append({'kind':'missing_or_stale_bundle_binding'})
 im=Image.open(d['screenshot']).convert('RGB')
 if hashlib.sha256(Path(d['screenshot']).read_bytes()).hexdigest()!=d['screenshot_sha256']:
  errors.append({'kind':'stale_screenshot'})
 p=d['panel'];s=d['sourceSafe'];safe={'x':p['x']+s['x']/s['sourceWidth']*p['w'],'y':p['y']+s['y']/s['sourceHeight']*p['h'],'w':s['w']/s['sourceWidth']*p['w'],'h':s['h']/s['sourceHeight']*p['h']}
 sx=im.width/d['viewport']['width'];sy=im.height/d['viewport']['height'];metrics=[]
 for row in d['rows']:
  if not row['loaded']:errors.append({'id':row['id'],'kind':'unloaded_preview'})
  for role in ['preview','action']:
   r=row.get(role)
   if not r:errors.append({'id':row['id'],'kind':'missing_'+role});continue
   if r['x']<safe['x']-.5 or r['y']<safe['y']-.5 or r['x']+r['w']>safe['x']+safe['w']+.5 or r['y']+r['h']>safe['y']+safe['h']+.5:
    errors.append({'id':row['id'],'kind':'outside_painted_inner_area','role':role})
  if not row.get('preview'):continue
  r=row['preview'];box=(round((r['x']+r['w']*.05)*sx),round((r['y']+r['h']*.1)*sy),round((r['x']+r['w']*.50)*sx),round((r['y']+r['h']*.9)*sy))
  pixels=list(im.crop(box).convert('HSV').getdata());neutral=sum(v[1]<45 for v in pixels)/len(pixels)
  metrics.append({'id':row['id'],'neutral_fraction':round(neutral,4)})
  if neutral>.90:errors.append({'id':row['id'],'kind':'neutral_placeholder_suspect','neutral_fraction':neutral})
 return {'passed':not errors,'capture':str(path),'painted_safe_area':safe,'rows_checked':len(d['rows']),'metrics':metrics,'errors':errors,'boundary':'Neutrality is a review trigger, not automatic image semantics; calibrated safe rect is supplied by project visual review.'}
def check(path):
 try:return _check(path)
 except (OSError,ValueError,KeyError,TypeError,ZeroDivisionError,IndexError) as exc:
  return {'passed':False,'errors':[{'kind':'invalid_capture','detail':str(exc)}]}

if __name__=='__main__':
 r=check(sys.argv[1]);print(json.dumps(r,indent=2));sys.exit(0 if r['passed'] else 1)
