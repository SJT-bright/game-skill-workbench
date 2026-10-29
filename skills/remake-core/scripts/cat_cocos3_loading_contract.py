"""CatSnackBar Cocos3 finite startup mechanisms; original SDK boundaries and raw input required.
No level/economy/art review is implied. No font assets are requested by this program;
optional audio occupies the optional-service boundary instead.
"""
from pathlib import Path
import json,hashlib
SCENARIOS=('normal','package-fail','package-hang','image-hang','slow-progress','background','promise-only','both-channels','audio-fail','audio-hang','late-success','late-failure','request-clock','warm')
def validate_loading(data,binding,base):
 errors=[]
 def need(ok,msg):
  if not ok:errors.append('CAT-LOADING: '+msg)
 need(data.get('profile')=='cat_cocos3_loading_v1' and data.get('producer')=='real_browser_touch_trace','actual finite native-loading profile required')
 need(data.get('binding')==binding and data.get('execution_binding')==binding,'same current execution binding required')
 vps=data.get('viewports',[]);need(len(vps)==2 and abs(vps[0][0]/vps[0][1]-vps[1][0]/vps[1][1])>.01,'two phone ratios required')
 refs=data.get('raw_evidence',[]);raws=[]
 for row in refs:
  try:
   p=(base/row['path']).resolve();p.relative_to(base.resolve());b=p.read_bytes();need(hashlib.sha256(b).hexdigest()==row['sha256'],'raw file changed');raws.append(json.loads(b))
  except (KeyError,ValueError,OSError) as e:need(False,'raw reference invalid '+str(e))
 need(bool(raws),'actual evidence required')
 for scenario in SCENARIOS:
  for vp in vps:
   selected=[r for r in raws if r.get('test',{}).get('scenario')==scenario and r['test'].get('viewport')==vp]
   need(len(selected)==1,scenario+str(vp)+' exact execution required')
   if len(selected)!=1:continue
   row=selected[0];raw=row.get('raw',{});business=row.get('business',{})
   need(row.get('binding')==binding,scenario+' stale Native binding')
   need(row.get('passed') is True and raw.get('ready') is True,scenario+' HOME not restored')
   need(raw.get('phases')==['entry','adapter','renderer','scene'],scenario+' original entry/adapter/renderer chain missing')
   need(any(i.get('isTrusted') and i.get('type')=='touchend' for i in raw.get('inputs',[])),scenario+' trusted input missing')
   need(business.get('before',{}).get('save')!=business.get('after',{}).get('save') and business.get('before',{}).get('save') is not None,scenario+' gameplay/save change missing')
   if row['test'].get('retry'):
    failure=row.get('failure',{});retry=row.get('retry',{});need(any(n.get('name')=='StartupRetry' for n in failure.get('nodes',[])),scenario+' visible engine Retry missing')
    need(failure.get('at_ms',1e9)<retry.get('at_ms',-1)<business.get('home',{}).get('at_ms',-1),scenario+' Retry chronology invalid')
    old=failure.get('packages',[]) if scenario in ('package-fail','package-hang') else failure.get('images',[])
    new=raw.get('packages',[]) if scenario in ('package-fail','package-hang') else raw.get('images',[])
    if scenario in ('package-fail','package-hang'):
     need(len([p for p in new if p['name']=='GameRes'])>len([p for p in old if p['name']=='GameRes']),scenario+' Retry did not create new underlying package request')
    else:
     held=[p for p in old if p.get('status')=='held'];need(bool(held),scenario+' image was not held at SDK transport')
     if held:need(len([p for p in new if p['path']==held[0]['path']])==len([p for p in old if p['path']==held[0]['path']])+1,scenario+' one Retry must create exactly one fresh same-image request')
   if scenario.startswith('late-'):need(row.get('beforeLate',{}).get('save') is not None and row['beforeLate']['save']==row.get('afterLate',{}).get('save'),scenario+' late result changed current save')
   if scenario=='slow-progress':need(any(p.get('done_ms',0)-p.get('at_ms',0)>15000 and len(p.get('progress',[]))>=5 for p in raw.get('packages',[])),scenario+' active progress did not cross old deadline')
   if scenario=='background':need(row.get('background',{}).get('ready') is False and not any(n.get('name')=='StartupRetry' for n in row.get('background',{}).get('nodes',[])),scenario+' background caused premature retry')
   if scenario in ('audio-hang','audio-fail'):
    need(any(p.get('name')=='GameAudio' for p in raw.get('packages',[])),scenario+' optional audio boundary not exercised')
    need(row.get('audioAfter',{}).get('ready') is True and row.get('audioBefore',{}).get('save') is not None and row['audioBefore']['save']==row['audioAfter']['save'] and row['audioAfter']['at_ms']-row['audioBefore']['at_ms']>=7900,scenario+' optional service terminal still blocks/restarts HOME')
   if scenario=='warm':need(row.get('warm',{}).get('ready') is True and row['warm'].get('package_count_after')==row['warm'].get('package_count_before'),scenario+' reentry restarted retained package')
   if scenario=='request-clock':need(any(p.get('delayed_at_ms') is not None and p.get('status')=='loaded' and p.get('done_ms',0)-p['at_ms']>=5500 for p in raw.get('images',[])),scenario+' no real delayed image request observed')
 # Old failure remains an actual original tree observation and is never relabelled.
 old=data.get('calibration',{});need(old.get('old_trace_sha256') and old.get('old_ready') is False and old.get('old_image_held') is True,'preserved old request-stall failure required')
 try:
  oldpath=(base/old['old_trace']['path']).resolve();oldpath.relative_to(base.resolve());oldbytes=oldpath.read_bytes();oldraw=json.loads(oldbytes)
  need(hashlib.sha256(oldbytes).hexdigest()==old['old_trace']['sha256']==old['old_trace_sha256'] and oldraw.get('passed') is False and oldraw.get('raw',{}).get('ready') is False and any(i.get('status')=='held'for i in oldraw.get('raw',{}).get('images',[])),'preserved control raw bytes do not prove actual stalled startup')
 except (KeyError,ValueError,OSError) as e:need(False,'old control reference invalid '+str(e))
 return errors
