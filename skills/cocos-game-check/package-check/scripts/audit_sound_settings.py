"""Reviewed sound-settings producer adapter, never a generic schema waiver.
Producer profiles are project data registered through project_qa; no machine path is distributed.
Other projects keep interaction_audio_trace.v1; this adapter does not certify drag.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"remake-core/scripts"))
import project_qa

def get_profile(trace):
 return PROFILE or project_qa.evidence_profile(trace,"sound_settings_trace.v1")

PROFILE = {}  # Only synthetic tests override this; production profiles are reviewed project data.
UNIT_CASES = (
 'OFF display and ticks are zero, remembered level retained',
 'mute scales both buses to zero',
 'zero then ON restores nonzero remembered level',
 'muted plus starts from effective zero and enables 10 percent',
 'independent all eleven levels and boundaries',
 'late BGM load cannot start after mute',
 'muted level updates cannot restore active output',
 'persisted independent state reloads without clearing other save',
 'SFX mute display, zero restoration and independent music state',
 'SFX muted decrement stays zero, tick selects audible level',
 'pause and ad reasons both must clear, mute survives resume',
)

def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
 def invalid(value):
  raise ValueError('nonfinite JSON number: '+value)
 return json.loads(Path(path).read_text(),parse_constant=invalid)

def number(value):
 return type(value) in (int,float) and math.isfinite(value)

def profile_errors(trace,native):
 trace=Path(trace).resolve();native=Path(native).resolve();profile=get_profile(trace);project=Path(profile['project']).resolve();errors=[]
 if not trace.is_relative_to(project):errors.append('sound-only producer is not registered for this project')
 for rel,h in profile['native_sha256'].items():
  p=(native/rel).resolve()
  if not p.is_relative_to(native) or not p.is_file() or sha(p)!=h:errors.append('unregistered sound-only production bytes: '+rel)
 for rel,h in profile['producer_sha256'].items():
  p=(project/rel).resolve()
  if not p.is_relative_to(project) or not p.is_file() or sha(p)!=h:errors.append('sound producer changed: '+rel)
 return errors

def is_registered_profile(trace,native):
 try:return not profile_errors(trace,native)
 except (ValueError,OSError,KeyError,TypeError):return False

def audit(trace,native):
 try:return _audit(trace,native)
 except (ValueError,KeyError,OSError,TypeError,AttributeError,IndexError,ZeroDivisionError) as exc:
  return {'tool':'audit_interaction_audio','passed':False,'errors':['invalid sound-settings evidence: '+str(exc)]}

def _audit(trace,native):
 trace=Path(trace).resolve();native=Path(native).resolve();profile=get_profile(trace);project=Path(profile['project']).resolve();d=load(trace);errors=profile_errors(trace,native)
 def need(ok,msg):
  if not ok:errors.append(msg)
 if errors:return {'tool':'audit_interaction_audio','passed':False,'errors':errors}
 def read(ref,base=trace.parent):
  p=(base/ref['path']).resolve()
  if not p.is_relative_to(base.resolve()) or not p.is_file() or sha(p)!=ref['sha256']:raise ValueError('sound raw changed: '+str(p))
  return load(p)
 need(d.get('schema')=='sound_settings_trace.v1','wrong sound schema')
 files=d.get('native_sha256',{})
 for rel,h in files.items():
  p=(native/rel).resolve();need(p.is_relative_to(native) and p.is_file() and sha(p)==h,'sound production changed: '+rel)
 need('assets/main/index.js' in files,'actual sound business binding required')
 web=d.get('web_equivalent',{});need(bool(web.get('assets/main/index.js')),'actual Web sound business binding required')
 for rel,paths in web.items():
  paths=[paths] if isinstance(paths,str) else paths
  need(isinstance(paths,list) and bool(paths),'missing Web source paths')
  for value in paths:
   p=Path(value);need(p.is_file() and sha(p)==files.get(rel),'Web and Native sound business differs')
 ui=read(d['ui']);rows=ui.get('rows',[]);need(ui.get('pass') is True and bool(rows),'current sound UI observations failed')
 for category,j in [('music',0),('sfx',1)]:
  own=[x for x in rows if x.get('category')==category];need(len(own)>=30,'sound controls insufficient for registered producer')
  need(set(range(0,101,10))<={x['expected'] for x in own},'eleven sound levels required')
  for name in ['off-zero','restore-half','off-plus-ten','zero-on-restore','lower-bound','upper-bound']:
   need(any(x['name']==name for x in own),'missing registered sound control '+name)
 previous=None
 for row in rows:
  category=row['category'];need(category in ('music','sfx'),'unknown sound category')
  j=0 if category=='music' else 1;o=row['observed'];value=row['expected']
  need(type(value) is int and value in range(0,101,10),'invalid expected sound level')
  for key in ['display','gain','levels','on']:need(isinstance(o.get(key),list) and len(o[key])==2,'missing paired sound state: '+key)
  for k in (0,1):
   need(number(o['display'][k]) and o['display'][k] in range(0,101,10),'invalid sound percentage')
   need(number(o['gain'][k]) and 0<=o['gain'][k]<=1,'invalid sound gain')
   need(type(o['levels'][k]) is int and 0<=o['levels'][k]<=10,'invalid remembered sound level')
   need(type(o['on'][k]) is bool and o['on'][k]==(o['display'][k]>0),'sound switch/effective display mismatch')
   need(abs(o['gain'][k]*100-o['display'][k])<1e-7,'paired display/effective gain mismatch')
  need(o['display'][j]==value and abs(o['gain'][j]*100-value)<1e-7,'display/effective gain mismatch')
  if previous is not None:
   other=1-j;need(all(o[k][other]==previous[k][other] for k in ['display','gain','levels','on']),'one sound category changed the other category')
  previous=o
 def cases(raw,label,expected_pass):
  observed=raw.get('observed',raw);values=observed.get('cases',[])
  need(bool(values) and len(values)==len(UNIT_CASES) and {x.get('name') for x in values}==set(UNIT_CASES),label+' compiled case coverage missing')
  flag=observed.get('all_sound_contract_cases_pass',observed.get('pass'))
  need(flag is expected_pass,label+' compiled contract result invalid')
  if expected_pass:need(all(x.get('pass') is True for x in values),label+' sound module contract failed')
  else:need(any(x.get('pass') is False and x.get('name')==UNIT_CASES[0] for x in values),'original OFF defect not reproduced')
  expected_hash=files['assets/main/index.js'] if expected_pass else profile['negative_source_sha256']
  if 'artifacts' in raw:
   artifact=raw['artifacts']['assets/main/index.js'];p=Path(artifact['path']).resolve()
   need(p.is_relative_to(project) and p.is_file() and sha(p)==artifact['sha256']==expected_hash,label+' original production artifact changed')
   need(raw.get('runner',{}).get('sha256')==profile['producer_sha256']['qa/sound-issue-runner.py'] and raw.get('case')=='all-sound-settings' and raw.get('harness_error') is False,label+' runner identity invalid')
  else:
   p=Path(raw['file']);p=p if p.is_absolute() else project/p;p=p.resolve()
   need(p.is_relative_to(project) and p.is_file() and sha(p)==expected_hash,label+' compiled source changed')
 cases(read(d['unit']),'current',True)
 cases(read(d['negative']),'negative',False)
 # This already-recorded normal control is part of this private producer profile,
 # not a new field or extra run imposed on other projects.
 cases(read(profile['normal'],project),'normal',True)
 runs=read(d['pcm'])['runs'];pcm={x['label']:x for x in runs}
 need(len(pcm)==len(runs),'duplicate PCM labels')
 for label in ['music_full','music_half','music_zero','sfx_full','sfx_half','sfx_zero','sfx_off','both_zero','music_off','music_on']:
  x=pcm.get(label,{});v=x.get('windowPeak') if label.startswith('sfx') else x.get('maxRms');muted=label in ['music_zero','sfx_zero','sfx_off','both_zero','music_off']
  need(number(v) and v>=0,'missing postgain PCM '+label)
  if number(v):need(v<=1e-5 if muted else v>1e-5,'output silence mismatch '+label)
  samples=x.get('pcm',[]);valid=bool(samples) and all(number(n) for n in samples)
  need(valid and number(x.get('sampleRate')) and x['sampleRate']>0 and x.get('state')=='running','missing finite postgain samples '+label)
  if valid:need(all(abs(n)<=1e-5 for n in samples) if muted else any(abs(n)>1e-5 for n in samples),'PCM samples contradict output summary '+label)
 for bus,metric in [('music','maxRms'),('sfx','windowPeak')]:
  full=pcm[bus+'_full'][metric];half=pcm[bus+'_half'][metric]
  if number(full) and full>0 and number(half):need(.35<half/full<.65,'half volume PCM ratio invalid')
  else:need(False,'invalid full/half PCM data')
 return {'tool':'audit_interaction_audio','profile':profile['id'],'passed':not errors,'errors':errors,'trace_sha256':sha(trace),'scope':'registered sound-settings-only raw evidence; no drag or unrelated audio-load claim'}
