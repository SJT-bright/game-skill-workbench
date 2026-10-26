"""Googly's finite Native12 startup/required-image controls. Does not waive other projects.
The broken input is a disclosed one-PNG corruption, not a claimed historical upload.
"""
import hashlib,json
from pathlib import Path
from startup_business_contract import validate_business
PROFILE='googly_native_recovery_v1'
PROJECT=Path('/Users/sijunting/Downloads/！自制游戏/GooglyEyeRecall_StarterPack')
FINAL=PROJECT/'build/gyr_native_gate_12_20261025'
BROKEN=PROJECT/'docs/evidence/package-functional-20261026/controls/corrupt-required-image'
IMAGE='assets/main/native/e8/e851e89b-faa2-4484-bea6-5c01dd9f06e2.png'
ROLES={'normal_long','normal_short','bundle_long','bundle_short','image_long','image_short','broken_long','broken_short'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {x.relative_to(p).as_posix():sha(x)for x in sorted(p.rglob('*'))if x.is_file()}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check_raw(raw,binding,role,runner_sha):
 errors=[]
 def need(ok,msg):
  if not ok:errors.append(role+': '+msg)
 broken=role.startswith('broken');root=BROKEN if broken else FINAL
 need(raw.get('binding')==binding,'execution binding mismatch')
 need(raw.get('runner_sha256')==runner_sha,'reviewed runner differs')
 need(raw.get('input_native_root')==str(root),'actual served input root differs')
 actual=tree(root);need(raw.get('native_tree_sha256')==digest(actual),'actual Native files changed')
 expected_view=[375,812]if role.endswith('short')else[390,844]
 need(raw.get('viewport')==expected_view,'phone viewport differs')
 observed=raw.get('observed_native_identity',{})
 inventory={p:{'bytes':(root/p).stat().st_size,'sha256':h}for p,h in actual.items()}
 need(observed=={'native_root':str(root),'tree_sha256':digest(inventory)},'actual HTTP identity differs')
 sources=raw.get('executed_sources_sha256',{})
 for p in ['game.js','main.js','adapter-min.js','flower-boot.js','assets/main/index.js','cocos/cocos2d-js-min.js']:
  need(sources.get(p)==actual.get(p),'executed production source differs: '+p)
 if broken:
  expected=tree(FINAL);expected[IMAGE]=hashlib.sha256(b'controlled invalid PNG: required launch-scene image').hexdigest()
  need(actual==expected,'controlled negative must change only the specified required PNG')
  f=raw.get('failure_observation',{});events=f.get('retry_touch_events',[])
  need(raw.get('passed')is False and raw.get('errors')==[],'negative must observe application failure, not collection error')
  need(f.get('home_visible')is False and f.get('retry_visible')is True,'negative must expose Retry and still fail to reach HOME')
  need(len(events)==2 and all(x.get('trusted')is True for x in events),'negative must actually touch Retry once')
  need(f.get('sdk_failure_observed')is True,'same subpackage fault boundary not exercised')
  need(f.get('observed_ms',0)-f.get('retry_at',0)>=9000,'negative did not observe after real Retry')
  need(any(x.get('path')==IMAGE for x in f.get('image_errors',[])),'required image actually must fail decoder')
  return errors
 need(raw.get('passed')is True and raw.get('errors')==[]and not raw.get('first_exception'),'current Native did not complete actual startup')
 need(raw.get('engine_identity')=={'game_run_original':True,'renderer_original':True,'canvas_get_context_original':True},'actual engine references replaced')
 need(raw.get('browser_canvas')=={'native_api':True,'two_d_blocks_webgl':True,'fresh_webgl':True},'real Canvas context calibration required')
 trace=raw.get('after',{}).get('native',{}).get('trace',[])
 # This real bootstrap executes main.js to start loadBundle; the main bundle's
 # index.js is then required by the original adapter during that asynchronous load.
 sequence=[next((i for i,x in enumerate(trace)if x.get('kind')=='module-execute'and x.get('path')==p),-1)for p in ['game.js','adapter-min.js','cocos/cocos2d-js-min.js','main.js','assets/main/index.js']]
 need(all(i>=0 for i in sequence)and sequence==sorted(sequence),'observed entry/adapter/engine/bundle/main execution order differs')
 need(raw.get('after',{}).get('native',{}).get('engine_version')=='2.4.15','actual engine version differs')
 errors+=validate_business(raw)
 play=raw.get('business',{}).get('play',{})
 need(type(play.get('eye_before'))is int and type(play.get('eye_after'))is int and play['eye_after']==play['eye_before']-1,'actual one-eye interaction effect missing')
 events=raw.get('touch_events',[])
 need(len(events)>=4 and all(x.get('trusted')is True for x in events),'actual trusted SDK input missing')
 for event in events:
  for t in event.get('event',{}).get('changedTouches',[]):
   need('clientX'not in t and 'clientY'not in t and all(type(t.get(k))in(int,float)for k in ['screenX','screenY']),'normal must exercise screen-only SDK shape')
 if role.startswith(('bundle','image')):
  retry=raw.get('retry',{});recovery=raw.get('recovery',{});at=retry.get('at_ms',float('inf'));home=raw.get('business',{}).get('home',{})
  need(retry.get('trusted_touch')is True and at<home.get('at_ms',0),'real Retry before HOME required')
  need(type(retry.get('requests'))is int and recovery.get('requests_after',0)>retry['requests'],'Retry must issue fresh underlying requests')
  touches=[x for x in events if x.get('at',0)>=at and x.get('at',0)<home.get('at_ms',0)]
  need(len(touches)==2,'exactly one Retry touch pair required')
  trace=raw.get('after',{}).get('native',{}).get('trace',[])
  if role.startswith('bundle'):
   before=[x for x in retry.get('bundle_requests',[])if x.get('name')=='resources'];after=[x for x in recovery.get('bundle_requests',[])if x.get('name')=='resources']
   need(len(before)==4 and len(after)==5 and [x.get('attempt')for x in after]==[1,2,3,4,5],'four actual SDK failures must recover on the new fifth request')
  else:
   failures=[x for x in retry.get('errors_before',[])if x.get('fault')is True]
   need(bool(failures),'actual one-shot image decode failure required')
   path=failures[0].get('path')if failures else None
   need(any(x.get('kind')=='image-request'and x.get('path')==path and x.get('at',0)>at and x.get('attempt')==2 for x in trace),'same image needs a second real request after Retry')
   need(any(x.get('kind')=='image-ready'and x.get('path')==path and x.get('at',0)>at for x in trace),'same image must actually decode after Retry')
 return errors
def validate(report,native,binding,project,data,need,ref):
 need(Path(project).resolve()==PROJECT and Path(native).resolve()==FINAL,'Googly contract applies only to its fixed project/Native12')
 need(report.get('control_profile')==PROFILE,'Googly recovery profile required')
 need(binding.get('source_sha256')==sha(FINAL/'assets/main/index.js'),'compiled business source binding differs')
 for error in check_raw(data,binding,'normal_long',report.get('runner',{}).get('sha256')):need(False,error)
 controls=report.get('controls',{});need(set(controls)==ROLES,'complete two-ratio normal/image/bundle/broken controls required')
 for role,row in controls.items():
  if role not in ROLES:continue
  p=ref(row,role+' actual execution')
  if not p:continue
  try:
   raw=json.loads(p.read_text());picture=p.with_name('screen.png')
   need(picture.is_file()and sha(picture)==row.get('screenshot_sha256')and picture.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),'control screenshot missing/changed: '+role)
   for error in check_raw(raw,binding,role,report.get('runner',{}).get('sha256')):need(False,error)
  except (ValueError,OSError,TypeError)as e:need(False,role+' evidence invalid: '+str(e))
def validate_loading(data,binding,base):
 errors=[]
 if data.get('profile')!=PROFILE or data.get('binding')!=binding or data.get('execution_binding')!=binding or data.get('producer')!='real_browser_touch_trace':errors.append('Googly current actual execution binding required')
 rows=data.get('raw_evidence',[])
 if {r.get('role')for r in rows}!=ROLES or len(rows)!=8:return errors+['eight exact two-ratio controls required']
 for row in rows:
  try:
   p=(base/row['path']).resolve();p.relative_to(base.resolve());assert sha(p)==row['sha256']
   picture=p.with_name('screen.png');assert sha(picture)==row['screenshot_sha256']
   errors+=check_raw(json.loads(p.read_text()),binding,row['role'],data.get('runner_sha256'))
  except (ValueError,OSError,KeyError,AssertionError)as e:errors.append('Googly recovery raw evidence invalid: '+str(e))
 return errors
