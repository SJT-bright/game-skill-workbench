"""Scoped real Native SDK-screen touch regression and first-Retry evidence.
No scene, renderer or game code is replaced by the host. Static probes supplement browser observations.
"""
import json,hashlib,zipfile
from pathlib import Path
PROFILE='cocos24_adapter_coordinates_v1'
def recovery_errors(raw,binding):
 from startup_business_contract import validate_business
 e=[]
 if raw.get('binding')!=binding or raw.get('native_tree_sha256')!=binding.get('native_tree_sha256'):e.append('recovery Native binding changed')
 if raw.get('passed')is not True or raw.get('errors')or raw.get('first_exception'):e.append('recovery not ready/error')
 touch=raw.get('retry',{})
 if touch.get('trusted_touch')is not True or type(touch.get('at_ms'))not in(int,float):e.append('one actual SDK Retry gesture required')
 if not raw.get('touch_events')or not all(x.get('trusted')for x in raw['touch_events']):e.append('untrusted input')
 before=touch.get('requests');after=raw.get('recovery',{}).get('requests_after')
 if not isinstance(before,int)or not isinstance(after,int)or after<=before:e.append('Retry did not issue fresh underlying request')
 if touch.get('at_ms',float('inf'))>raw.get('business',{}).get('home',{}).get('at_ms',0):e.append('Retry after HOME')
 e+=validate_business(raw);return e

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 need(report.get('control_profile')==PROFILE,'SDK screen profile mismatch')
 need(data.get('business',{}).get('home',{}).get('social_absent')is True,'sharing/rank HOME residual')
 base=tree(native)
 for name in['known_bad','reintroduced_defect','short','image_recovery','bundle_recovery']:
  p=ref(report.get('controls',{}).get(name,{}),name+' actual execution')
  if not p:continue
  raw=json.loads(p.read_text());need(raw.get('runner_sha256')==report['runner']['sha256']and raw.get('binding')==binding,name+' executor/binding changed')
  if name in['known_bad','reintroduced_defect']:
   root=Path(raw.get('input_native_root','')).resolve();need(root.is_relative_to(project.resolve())and root.is_dir(),name+' invalid control root');manifest=tree(root)
   need(digest(manifest)==raw.get('native_tree_sha256')and digest(manifest)!=digest(base),name+' distinct Native required')
   obs=raw.get('failure_observation',{});need(raw.get('passed')is False and raw.get('failure_kind')=='sdk_screen_coordinates'and obs.get('home_still_visible')is True,name+' must actually fail to enter gameplay after trusted touch')
   touches=obs.get('touches',[]);need(len(touches)>=2 and all(x.get('trusted')for x in touches),name+' actual SDK touches missing')
   if name=='known_bad':
    z=ref(raw.get('source_zip',{}),'preserved prior uploaded ZIP')
    if z:
     with zipfile.ZipFile(z)as f:old={n:hashlib.sha256(f.read(n)).hexdigest()for n in f.namelist()if not n.endswith('/')}
     need(old==manifest,'known bad input differs from preserved ZIP')
   else:
    m=raw.get('mutation',{});needle="var point=pair(raw,'clientX','clientY'),source='client';\n      if (!point) {point=pair(raw,'screenX','screenY');source='screen';}";replacement="var point=pair(raw,'screenX','screenY'),source='screen';\n      if (!point) {point=pair(raw,'clientX','clientY');source='client';}";text=(native/'adapter-min.js').read_text();expected=dict(base);expected['adapter-min.js']=hashlib.sha256(text.replace(needle,replacement).encode()).hexdigest();need(text.count(needle)==1 and manifest==expected and m.get('file')=='adapter-min.js' and m.get('base_sha256')==base['adapter-min.js']and raw.get('base_native_tree_sha256')==digest(base),'control must change only actual adapter coordinate priority')
  else:
   need(raw.get('native_tree_sha256')==digest(base)and raw.get('passed')is True and raw.get('errors')==[],name+' final Native failed')
   from startup_business_contract import validate_business
   for error in validate_business(raw):need(False,name+': '+error)
   if name=='short':need(raw.get('viewport')==[375,667], 'short actual viewport required')
   else:
    for error in recovery_errors(raw,binding):need(False,name+': '+error)
    if name=='image_recovery':need(raw.get('retry',{}).get('errors_before')and raw.get('recovery',{}).get('images_after',0)>raw.get('retry',{}).get('image_requests',0),'actual first image decode failure and fresh image requests required')
    if name=='bundle_recovery':need(len(raw.get('retry',{}).get('bundle_requests',[]))>=1 and len(raw.get('recovery',{}).get('bundle_requests',[]))>len(raw.get('retry',{}).get('bundle_requests',[])),'actual subpackage failure/new request required')

def validate_loading(data,binding,base):
 from startup_business_contract import validate_business
 errors=[];rows=[]
 if data.get('binding')!=binding or data.get('execution_binding')!=binding or data.get('producer')!='real_browser_touch_trace':errors.append('current real execution binding required')
 for ref in data.get('raw_evidence',[]):
  try:
   p=(base/ref['path']).resolve();p.relative_to(base.resolve());b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==ref['sha256'];rows.append(json.loads(b))
  except(Exception)as e:errors.append('raw evidence invalid '+str(e))
 if len(rows)!=6:return errors+['six actual raw controls required']
 if [x.get('viewport')for x in rows[:2]]!=[[390,844],[375,667]]:errors.append('two phone ratios required')
 for raw in rows[:2]:
  if raw.get('passed')is not True or raw.get('binding')!=binding:errors.append('normal failed')
  errors+=validate_business(raw)
 for raw in rows[2:4]:errors+=recovery_errors(raw,binding)
 for raw in rows[4:]:
  if raw.get('passed')is not False or raw.get('failure_observation',{}).get('home_still_visible')is not True:errors.append('actual old input failure absent')
 return errors
