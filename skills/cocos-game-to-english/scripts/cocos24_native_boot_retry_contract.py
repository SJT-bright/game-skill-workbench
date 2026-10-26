"""Cocos 2.4 boot errors with real SDK modal Retry and pristine scene imports.
This scoped family still requires original engine/renderer, real browser touch,
normal/short business effects, failing preserved Native inputs, fresh resource
requests and exact Native/evidence hashes. It is not a static-only exception.
"""
from pathlib import Path
import json,hashlib
from startup_business_contract import validate_business
PROFILE='cocos24_native_boot_retry_v1'
POSITIVE=('normal','short','bundle_recovery','callback_hang','image_recovery','late_success')
NEGATIVE=('known_bad','reintroduced_defect')
def case_errors(raw,binding):
 e=[]
 def need(ok,msg):
  if not ok:e.append(msg)
 name=raw.get('name');need(name in POSITIVE+NEGATIVE,'unknown boot case');need(raw.get('binding')==binding,'stale execution binding');need(raw.get('browser_canvas')=={'native_api':True,'two_d_blocks_webgl':True,'fresh_webgl':True},'actual Canvas calibration missing')
 need(raw.get('touch',0)>=1 and 'Mobile' in raw.get('user_agent',''),'actual mobile SDK input environment missing')
 need(all(raw.get('engine_identity',{}).get(k)is True for k in ('game_run_original','renderer_original','canvas_get_context_original')),'engine/renderer replaced')
 if name in POSITIVE:
  need(raw.get('native_tree_sha256')==binding.get('native_tree_sha256'),'wrong final Native');need(raw.get('passed')is True and raw.get('errors')==[] and not raw.get('first_exception'),'Native boot/recovery has errors');e+=validate_business(raw)
  need(raw.get('phase_order')==['entry','adapter','renderer','scene']and raw.get('renderer',{}).get('webgl_context')is True,'actual Native chain missing')
  expected=[375,667]if name=='short'else[390,844];need(raw.get('viewport')==expected,'wrong actual phone viewport')
  touches=raw.get('touch_events',[]);need(len(touches)>=4 and all(t.get('isTrusted')is True for t in touches),'actual trusted SDK gestures missing')
  need(any(t.get('name')=='TouchMove'for t in touches),'gameplay gesture missing')
  if name not in ('normal','short'):
   r=raw.get('retry',{});events=raw.get('events',[]);confirms=[x for x in events if x.get('kind')=='sdk_modal_confirm'];need(r.get('visible')is True and r.get('trusted_touch')is True and len(confirms)==1 and confirms[0].get('trusted_touch')is True,'one visible SDK Retry touch required')
   need(type(r.get('requests_before'))is int and type(r.get('requests_after'))is int and r['requests_after']>r['requests_before'],'no fresh requests after Retry')
   if confirms:
    at=confirms[0]['t_ms'];need(r.get('at_ms',float('inf'))<=at<raw['business']['home']['at_ms'],'Retry order invalid')
    if name=='image_recovery':
     failed=[x for x in events if x.get('kind')=='image_injected_failure'];need(len(failed)==1 and bool(r.get('errors_before')),'first image failure absent')
     if failed:
      matches=[x for x in events if x.get('kind')=='image_request'and x.get('path')==failed[0].get('path')];need(len(matches)>=2 and matches[0]['t_ms']<at<matches[-1]['t_ms'],'same underlying image was not requested again')
    else:
     requests=[x for x in events if x.get('kind')=='sdk_request'and x.get('name')=='resources'];need(len(requests)>=2 and len({x['id']for x in requests})==len(requests)and requests[0]['t_ms']<at<requests[1]['t_ms'],'resources subpackage did not get a fresh SDK request')
     if name=='callback_hang':need(any(x.get('kind')=='sdk_held'for x in events)and at-requests[0]['t_ms']>=9500,'actual held callback/deadline not exercised')
     if name=='late_success':need(any(x.get('type')=='late_sdk_ignored'for x in raw.get('guard',[])),'late old callback not isolated')
 else:
  need(raw.get('passed')is False and raw.get('errors')and not raw.get('home_visible')and not raw.get('retry_visible'),'old defect did not fail at boot with no recovery')
  need(raw.get('observed_ms',0)>=8000,'negative observation ended too early')
  text=json.dumps(raw.get('errors',[]));need(('substr' in text if name=='known_bad'else'4930' in text and 'Failed to load scene' in text),'wrong negative failure boundary')
 return e

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest
 need(report.get('control_profile')==PROFILE,'boot family differs')
 raws={'normal':data}
 for name in POSITIVE[1:]+NEGATIVE:
  p=ref(report.get('controls',{}).get(name,{}),name+' real Native case')
  if p:raws[name]=json.loads(p.read_text())
 for name,raw in raws.items():
  for error in case_errors(raw,binding):need(False,name+': '+error)
  need(raw.get('runner_sha256')==report['runner']['sha256'],'runner identity differs')
  if name in NEGATIVE:
   root=Path(raw.get('input_native_root','')).resolve();need(root.is_relative_to(project.resolve())and root.is_dir(),'negative Native input missing/outside project');manifest=tree(root);need(digest(manifest)==raw.get('native_tree_sha256')and digest(manifest)!=binding['native_tree_sha256'],'negative actual Native tree changed')
   need(raw.get('provenance',{}).get('kind')=='preserved_pre_fix_native'and raw['provenance'].get('tree_sha256')==digest(manifest),'negative provenance missing')
   base=tree(native);changes={k:{'candidate':base.get(k),'control':manifest.get(k)}for k in set(base)|set(manifest)if base.get(k)!=manifest.get(k)};need(raw.get('changed_files')==changes and raw.get('base_native_tree_sha256')==binding['native_tree_sha256'],'controlled input change inventory differs')
   if name=='reintroduced_defect':need(set(changes)=={'main.js','runtime-recovery.js'},'scene defect control changed unrelated files')
  pic=ref(raw.get('screenshot',{}),name+' screenshot');need(pic is not None and pic.read_bytes().startswith(b'\x89PNG'),'raw screenshot missing')

def validate_loading(data,binding,base):
 errors=[];raws=[]
 if data.get('profile')!=PROFILE or data.get('producer')!='real_browser_touch_trace'or data.get('binding')!=binding or data.get('execution_binding')!=binding:errors.append('final real Native loading identity differs')
 for item in data.get('raw_evidence',[]):
  try:
   p=(base/item['path']).resolve();p.relative_to(base.resolve());b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==item['sha256'];raws.append(json.loads(b))
  except(Exception)as error:errors.append('invalid raw boot evidence: '+str(error))
 if sorted(x.get('name','')for x in raws)!=sorted(POSITIVE+NEGATIVE):errors.append('exactly eight scoped actual boot cases required')
 for raw in raws:
  errors+=case_errors(raw,binding)
  if raw.get('runner_sha256')!=data.get('runner_sha256'):errors.append('loading runner identity differs')
 return errors
