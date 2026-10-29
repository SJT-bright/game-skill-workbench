import json,sys,hashlib
from pathlib import Path

def inspect(data,verify=True):
 errors=[];metrics=[]
 policy=data.get('layout_policy',{})
 if not all(k in policy for k in ['min_subject_height_ratio','max_content_gap_ratio','tolerance_css']):return {'passed':False,'errors':[{'code':'uninspectable','why':'Declare project layout policy; do not infer global aesthetic thresholds'}]}
 tol=policy['tolerance_css']
 if data.get('producer')!='real_cocos_card_geometry' or not data.get('cards'):return {'passed':False,'errors':[{'code':'uninspectable','why':'Missing real populated capture'}]}
 if verify:
  p=Path(data.get('screenshot',''))
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=data.get('screenshot_sha256'):return {'passed':False,'errors':[{'code':'uninspectable','why':'Screenshot missing or not bound'}]}
  if len(data.get('bundle_sha256',''))!=64:return {'passed':False,'errors':[{'code':'uninspectable','why':'Bundle fingerprint missing'}]}
 def axis(v,src,dst,lo,hi,sliced):
  if not sliced:return v/src*dst
  if dst<lo+hi:raise ValueError('Slice borders exceed destination')
  if v<=lo:return v
  if v>=src-hi:return dst-(src-v)
  return lo+(v-lo)*(dst-lo-hi)/(src-lo-hi)
 for card in data['cards']:
  panel=card['panel'];pr=panel['rect'];frame=panel['frame'];sz=panel['node_size'];insets=panel.get('insets') or {};ss=card['source_safe'];slot=card['slot'];items=card['items']
  if not panel['loaded'] or not items or any(not i['loaded'] for i in items):errors.append({'slot':slot,'code':'uninspectable'});continue
  try:
   x0=axis(ss['x'],frame['width'],sz['width'],insets.get('left',0),insets.get('right',0),panel['sliced']);x1=axis(ss['x']+ss['width'],frame['width'],sz['width'],insets.get('left',0),insets.get('right',0),panel['sliced'])
   y0=axis(ss['y'],frame['height'],sz['height'],insets.get('top',0),insets.get('bottom',0),panel['sliced']);y1=axis(ss['y']+ss['height'],frame['height'],sz['height'],insets.get('top',0),insets.get('bottom',0),panel['sliced'])
  except (ValueError,ZeroDivisionError):errors.append({'slot':slot,'code':'invalid_slice_mapping'});continue
  safe={'x':pr['x']+x0/sz['width']*pr['width'],'y':pr['y']+y0/sz['height']*pr['height'],'width':(x1-x0)/sz['width']*pr['width'],'height':(y1-y0)/sz['height']*pr['height']}
  roles={i['role']:i for i in items};missing=set(['character','name','condition','action'])-roles.keys()
  if missing:errors.append({'slot':slot,'code':'uninspectable','missing_roles':sorted(missing)})
  for it in items:
   r=it['rect']
   for exclusion in data.get('known_art_exclusions',[]):
    f=it.get('frame') or {};bad=dict(exclusion['rect'])
    if f.get('name')==exclusion['frame_name'] and exclusion.get('coordinate_space')=='source_frame':
     origin=it.get('source_origin_in_texture')
     if not origin:errors.append({'slot':slot,'code':'uninspectable','why':'Map source-local exclusion into packed texture coordinates'});continue
     bad['x']+=origin['x'];bad['y']+=origin['y']
    if f.get('name')==exclusion['frame_name'] and min(f.get('x',0)+f['width'],bad['x']+bad['width'])>max(f.get('x',0),bad['x']) and min(f.get('y',0)+f['height'],bad['y']+bad['height'])>max(f.get('y',0),bad['y']):errors.append({'slot':slot,'code':'known_source_fragment_included','role':it['role'],'frame':f['name']})
   overflow=max(safe['x']-r['x'],safe['y']-r['y'],r['x']+r['width']-safe['x']-safe['width'],r['y']+r['height']-safe['y']-safe['height'])
   if overflow>tol:errors.append({'slot':slot,'code':'content_crosses_ornament','role':it['role'],'overflow_css':round(overflow,2)})
  if not missing:
   ratio=roles['character']['rect']['height']/pr['height']
   if ratio<policy['min_subject_height_ratio']:errors.append({'slot':slot,'code':'subject_too_small_for_compact_card','ratio':round(ratio,3)})
   ordered=[roles[k] for k in ['character','name','condition','action']]
   gaps=[ordered[j+1]['rect']['y']-ordered[j]['rect']['y']-ordered[j]['rect']['height'] for j in range(3)]
   if max(gaps)>pr['height']*policy['max_content_gap_ratio']:errors.append({'slot':slot,'code':'unbalanced_content_gap','gap_ratio':round(max(gaps)/pr['height'],3)})
   if min(gaps)<-tol:errors.append({'slot':slot,'code':'content_overlap','gap_css':round(min(gaps),2)})
   metrics.append({'slot':slot,'safe':safe,'character_ratio':ratio,'gaps_css':gaps})
  vp=data['viewport']
  if pr['x']<-1 or pr['y']<-1 or pr['x']+pr['width']>vp['width']+1 or pr['y']+pr['height']>vp['height']+1:errors.append({'slot':slot,'code':'card_outside_viewport'})
 return {'passed':not errors,'errors':errors,'metrics':metrics}
if __name__=='__main__':
 try:
  data=json.loads(Path(sys.argv[1]).read_text());result=inspect(data)
 except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
  result={'passed':False,'errors':[{'code':'uninspectable','why':str(exc)}]}
 print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 1)
