#!/usr/bin/env python3
"""Validate raw interaction/audio observations and current production hashes; does not execute a browser.
Trace schema interaction_audio_trace.v1: native_sha256 map of relative production files,
runs [{path,sha256}] with viewport, drag [{before,state,cancel,picked,held}],
audio [{label,maxRms,windowPeak,music,sfx}], result {win,errors}.
Known defect calibration points at untouched drag-negative and audio-negative raw JSON.
"""
import argparse,hashlib,json,math
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def _audit(trace,native):
 trace=Path(trace).resolve();native=Path(native).resolve();d=json.loads(trace.read_text());errors=[]
 def need(ok,msg):
  if not ok:errors.append(msg)
 def read(ref):
  p=(trace.parent/ref['path']).resolve();need(p.is_file() and sha(p)==ref['sha256'],'raw evidence hash mismatch: '+str(p));return json.loads(p.read_text())
 need(d.get('schema')=='interaction_audio_trace.v1','wrong trace schema')
 files=d.get('native_sha256',{});need(bool(files),'missing production binding')
 for rel,h in files.items():
  p=(native/rel).resolve();need(p.is_relative_to(native) and p.is_file() and sha(p)==h,'production bytes changed: '+rel)
 for rel,paths in d.get('web_equivalent',{}).items():
  for web in paths:need(Path(web).is_file() and sha(Path(web))==files.get(rel),'actual Web business differs from Native: '+web)
 recovery=read(d['recovery']);need(bool(recovery.get('failed',{}).get('error')) and recovery.get('recovered',{}).get('playing') is True and recovery['recovered'].get('error') is None,'audio failure/retry did not recover')
 bounds=read(d['boundaries']);need(bounds.get('pickedInvalid') is True and bounds['invalid'].get('held') is False and bounds['before']==bounds['invalid'].get('state'),'invalid drop mutated game')
 multi=read(d['multitouch']);need(multi['afterOther'].get('held') is True and multi['afterCancel'].get('held') is False and multi['afterOther']['state']==multi['afterCancel']['state'],'pointer ownership/cancel changed business')
 views=set()
 for ref in d.get('runs',[]):
  r=read(ref);views.add(tuple(r.get('viewport',[])));drags=r.get('drag',[]);need(bool(drags),'no trusted drag observations')
  for c in drags:
   need(c.get('picked') is True and c.get('held') is False,'drag not acquired/released')
   need((c.get('before')==c.get('state')) if c.get('cancel') else (c.get('before')!=c.get('state')),'cancel committed or legal drag had no effect')
  need(any(c.get('cancel') for c in drags),'missing real cancel control')
  need(any(not c.get('cancel') and c.get('before')!=c.get('state') for c in drags),'missing successful legal drop')
  need(r.get('result',{}).get('win') is True,'no normal completion observed')
  need(not r.get('result',{}).get('errors'),'runtime exception')
  a={x['label']:x for x in r.get('audio',[])}
  for label in ['music_full','music_half','music_zero','sfx_full','sfx_half','both_zero','music_off','music_on']:
   x=a.get(label,{});v=x.get('windowPeak') if label.startswith('sfx_') else x.get('maxRms');need(type(v) in (float,int) and math.isfinite(v),'missing PCM output: '+label)
   if type(v) in (float,int) and math.isfinite(v):need(v<=1e-5 if label in ('music_zero','both_zero','music_off') else v>1e-5,'silent/audible output mismatch: '+label)
  if all(k in a for k in ['music_full','music_half']):need(0<a['music_half'].get('maxRms',0)<a['music_full'].get('maxRms',0)*.8,'music volume does not change actual output')
  if all(k in a for k in ['sfx_full','sfx_half']):need(0<a['sfx_half'].get('windowPeak',0)<a['sfx_full'].get('windowPeak',0)*.8,'SFX volume does not change actual output')
 need(len(views)>=2 and all(len(v)==2 and all(type(n) in (int,float) and math.isfinite(n) and n>0 for n in v) and v[1]>v[0] for v in views),'two real portrait viewports required')
 n=d.get('negative_control',{});drag=read(n['drag']);audio=read(n['audio'])
 need(drag.get('picked',{}).get('picked') is True and drag['before']['moves']==drag['after']['moves'],'old drag defect was not reproduced')
 need(audio.get('playing') is False and audio.get('music')==1 and bool(audio.get('runtime',{}).get('audioError')),'old audio load defect was not reproduced')
 return {'tool':'audit_interaction_audio','passed':not errors,'errors':errors,'viewports':[list(v) for v in views],'trace_sha256':sha(trace),'scope':'raw postconditions/hash validation; observer and SDK boundary require human review'}
def audit(trace,native):
 try:
  if json.loads(Path(trace).read_text()).get('schema')=='sound_settings_trace.v1':
   from audit_sound_settings import audit as sound_audit, is_registered_profile
   if not is_registered_profile(trace,native):
    return {'tool':'audit_interaction_audio','passed':False,'errors':['unregistered sound-only evidence scope; schema does not replace interaction/audio obligations']}
   return sound_audit(trace,native)
  return _audit(trace,native)
 except (ValueError,KeyError,OSError,TypeError,AttributeError,IndexError) as exc:
  return {'tool':'audit_interaction_audio','passed':False,'errors':['invalid interaction/audio evidence: '+str(exc)]}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',required=True);p.add_argument('--native',required=True);p.add_argument('--out');a=p.parse_args()
 try:r=audit(a.trace,a.native)
 except (ValueError,KeyError,OSError,TypeError) as e:r={'passed':False,'errors':[str(e)]}
 if a.out:Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(r,ensure_ascii=False));raise SystemExit(0 if r['passed'] else 1)
