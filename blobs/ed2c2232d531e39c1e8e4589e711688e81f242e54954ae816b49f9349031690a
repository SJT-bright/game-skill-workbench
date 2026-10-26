"""Fixed RunHome Native45 loading evidence adapter.
This profile is limited to one exact project/candidate and reviewed immutable raw
executions. Generic SCENARIOS and all other profiles remain unchanged. It does
not claim a Promise-only startup consumer or optional SDK TTF loader exists.
"""
import hashlib,json,math
from pathlib import Path
PROFILE='runhome_native_loading_v1'
PROJECT=Path('/Users/sijunting/Downloads/！自制游戏/1回家快跑/RunHome-English')
BINDING={'source_sha256': 'c69aa39641245f46bd45c604cd1f7106da05bdee1a908868e480b40257882fb6', 'native_tree_sha256': 'b6af99501e4cc372b9433795fa81673d7960260d5af3a4f97cf608ba2f31540e', 'web_tree_sha256': '79116aca988531a5f0cc35ae7fdab6f0610ea7878ec298128ab49d22df53e4cc', 'build_tag': 'RunHome-package-v45-20261026'}
FROZEN_REFS={'normal15': {'path': 'docs/test/resume-20261026/draw-verified/startup/report.json', 'sha256': '78f0c5fa5e2094bcdf5100587a4da37c310b3bfc269033c92a3e1bd53bf50391'}, 'normalSE': {'path': 'docs/test/final-package-20261026/startup-iphoneSE-with-SE-control.json', 'sha256': '889fe33dd2d442964e8c8af0c253447caa8d5bf1f6f8cd9a18aa9b2e19bf521f'}, 'explicit15': {'path': 'docs/test/resume-20261026/draw-verified/explicit_failure/report.json', 'sha256': '51a50226f628dbf2bbdb301f1ed1ed79c59c55cd5e6908a1181c942183617084'}, 'explicitSE': {'path': 'docs/test/final-package-20261026/explicit_failure-iphoneSE-with-SE-control.json', 'sha256': '228e6e0047f9a680648853ee7f0f511d18f1b03aeb22f6ee9fb49de629313e33'}, 'held15': {'path': 'docs/test/final-package-20261026/held-v45-final-fixed.json', 'sha256': 'a6d3a675f8c508aeffb5296f07d68a24cfcc501f20f6b157cf007f7e35ec77fc'}, 'heldSE': {'path': 'docs/test/final-package-20261026/held-v45-SE-final-fixed.json', 'sha256': '65a3de7f09efb1dd5c72d6e15979e998507a3b236392c0c17187722348c78feb'}, 'image15': {'path': 'docs/test/resume-20261026/image-inflight-v45-resume.json', 'sha256': '7659dd32d57efe520a20267359a52791df2d01742a48b2d97a790fa46044351d'}, 'imageSE': {'path': 'docs/test/resume-20261026/image-inflight-v45-SE-resume.json', 'sha256': '0d083e9c5f24cf848596eab69b1a966b9074a0aaf58ff10169d277761e347784'}, 'slow': {'path': 'docs/test/resume-20261026/slow-progress.json', 'sha256': 'ffa95ecb88378e586cb592e24a9a30775be93a7e19388561e1d2c67c5c3faae1'}, 'background': {'path': 'docs/test/resume-20261026/background.json', 'sha256': '014622a4ddcb5f2c003931197868bd4ca751d9c9bbbe7c4b0f7834df87f9fc7d'}, 'clock_warm': {'path': 'docs/test/final-package-20261026/clock-warm.json', 'sha256': '11614c5ea810205a4b67a19f7c4d0020261b2e7edffeb91b465d5a7ece7a7219'}, 'old_held': {'path': 'docs/test/package-20261026/held-v34-negative.json', 'sha256': 'b4bd32dc0663e405837417e4cf48f5cc09676f3f9540656eeb2d0bf8b3745a49'}, 'assets': {'path': 'docs/test/resume-20261026/all-native-assets.json', 'sha256': '8a473a335161eb44c9b9845728ce276a9057f0aebbbe062df204ed5b1b432ebd'}, 'fs_unit': {'path': 'docs/test/resume-20261026/fs-lifecycle-regression.json', 'sha256': '0549764d7ac8a3a6c43b3bfbd12271093e78bbb9a10b99e7d2ec7158fcf6cad9'}, 'image_unit': {'path': 'docs/test/resume-20261026/image-lifecycle-regression.json', 'sha256': '0e74f4b4271500e0e22dc1c93107ebae69e87c8c2fac9f66c0e83cfcd9bcc697'}, 'event_unit': {'path': 'docs/test/resume-20261026/image-event-lifecycle-regression.json', 'sha256': '2adb23a7b79f14d307f73e2f478536c483ec248e3009adb8f6aab9e4a01c0704'}, 'guard_unit': {'path': 'docs/test/resume-20261026/guard-contract.json', 'sha256': '2a646aa56aa337af5e7364980454bf42f46df83305c441b2ec69225a7e54b644'}}
EXECUTORS={'docs/test/final-package-20261026/clock-warm.mjs': '556ba058ed1682de80e0ddf98a1e1f79d553f549e43674e15fddf737dab0f908', 'docs/test/final-package-20261026/held15.mjs': '6b335bae5d21a0a83b3c12f084243ce4b9b68373b2edc623b01f9879604a0671', 'docs/test/final-package-20261026/heldSE.mjs': '558fc3fc32021a2f6f59ed3c44aa904669afbd126cd97705364bfe7d0c41aa49', 'docs/test/final-package-20261026/clock-warm-host/native-host.js': 'fb4e828612c7e0ec42299e572cb3ebd22f3807d33519b91dee6689c08869bfba', 'docs/test/final-package-20261026/clock-warm-host/serve.py': '0bc5abbc620b75c55b4e409c219e5fe9813fba8f27c894e8ccd7bbb8e6e42b6f', 'docs/test/final-package-20261026/clock-warm-host/host.html': '187a3e8595d7aefd93adc49e7d1dc93cdb93890513264e09721a694b64f2c87e', 'docs/test/final-package-20261026/held-host/native-host.js': '1c20b8d977c0abe10a5c8dcf31114f2b5dbf07c68765fffa84719d70cee59dba', 'docs/test/final-package-20261026/held-host/serve.py': '0bc5abbc620b75c55b4e409c219e5fe9813fba8f27c894e8ccd7bbb8e6e42b6f', 'docs/test/final-package-20261026/held-host/host.html': '187a3e8595d7aefd93adc49e7d1dc93cdb93890513264e09721a694b64f2c87e', 'docs/test/final-package-20261026/negative-SE/probe-config.json': '1695a8afc706526a48e66b527633bbd4aff7938dcfad076952ba31a3e8223274', 'docs/test/package-20261026/native-runner/trace.mjs': 'f300e048bd3d9d1dfa46f583cf6224aea7f991d8883c03f53f83c76b96b7bcd8', 'docs/test/package-20261026/native-runner/report_schema.py': '750f95be551a0118e8c37a7eb8471bd123d2380aa09a51f75d469f0940b7442f'}
APPLICABILITY={'complete':['sdk_and_watchdog_held','explicit_failure','image_inflight_retry','slow_progress','background_wait','late_success','late_failure','warm_reentry','request_local_clock','normal_control'],'partial':{'callback_promise':['callback_only','settled_once','progress_api_absent']},'not_applicable':{'callback_promise':['promise_only','both_channels'],'optional_font':'No consumed SDK TTF task; required BitmapFont remains required'}}

def validate_loading(data,binding,base):
 from audit_native_startup_renderer import tree,digest,validate as validate_renderer
 errors=[]
 def need(ok,msg):
  if not ok:errors.append('RUNHOME-LOADING: '+msg)
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def effect(before,after):
  a,b=before.get('hero'),after.get('hero');touches=after.get('sdk',after.get('touches',[]))
  return bool(a and b and a.get('id')==b.get('id') and (a.get('jump',a.get('j'))!=b.get('jump',b.get('j')) or a.get('y')!=b.get('y')) and any(t.get('trusted') for t in touches))
 def clean(state):return not any('UNCAUGHT' in str(x) or 'UNHANDLED' in str(x) for x in state.get('errors',[]))
 try:
  need(set(data)=={'profile','binding','execution_binding','native','raw_evidence','applicability','executors'},'unknown/missing runtime fields')
  need(data.get('profile')==PROFILE and binding==BINDING and data.get('binding')==binding and data.get('execution_binding')==binding,'exact reviewed candidate binding required')
  native=Path(data.get('native','')).resolve();need(native==PROJECT/'build-native-v45/bytedance','wrong native root')
  need(digest(tree(native))==BINDING['native_tree_sha256'],'Native bytes changed; profile must be re-reviewed for a new candidate')
  need(data.get('applicability')==APPLICABILITY,'missing/expanded applicability or waiver')
  need(data.get('executors')==EXECUTORS,'executor inventory changed')
  for relative,expected in EXECUTORS.items():need(sha(PROJECT/relative)==expected,'reviewed executor changed: '+relative)
  refs=data.get('raw_evidence',[]);need(isinstance(refs,list)and len(refs)==len(FROZEN_REFS),'complete evidence inventory required')
  observed={}
  for entry in refs:
   need(isinstance(entry,dict)and set(entry)=={'role','path','sha256'},'invalid reference fields')
   role=entry.get('role');expected=FROZEN_REFS.get(role)
   need(expected is not None and role not in observed,'unknown/duplicate role: '+str(role))
   if expected is None:continue
   need(entry.get('path')==expected['path']and entry.get('sha256')==expected['sha256'],'frozen reference changed: '+role)
   p=(PROJECT/expected['path']).resolve();need(p.is_relative_to(PROJECT)and sha(p)==expected['sha256'],'raw bytes changed: '+role)
   observed[role]=json.loads(p.read_text())
  need(set(observed)==set(FROZEN_REFS),'missing actual case evidence')
  if errors:return errors
  # Existing renderer validator checks HOME after-draw, original entry/adapter/
  # renderer, exact sources, trusted touch/effect, old stencil control, and hashes.
  for role in ['normal15','normalSE','explicit15','explicitSE']:
   for error in validate_renderer(observed[role],native,binding,PROJECT):need(False,role+': '+error)
   raw=json.loads(Path(observed[role]['raw']['path']).read_text());row=raw['raw_trace']
   need(raw['viewport']==([393,852]if role.endswith('15')else[375,667]),role+' viewport')
   if role.startswith('explicit'):
    f,h=row['failure'],row['home'];need(f['guard']['failed']and not f['guard']['finished'],'explicit failure not observed')
    need(row['retryTouch']['sdkTouches'][-1]['trusted']and len([t for t in row['retryTouch']['sdkTouches']if t['type']=='touchstart'])==1,'one trusted first Retry required')
    path='assets/internal/config.json';need(any(x.get('path')==path and x.get('status')==503 for x in f['requests']),'actual explicit resource failure absent')
    need(any(x.get('path')==path and x.get('status')==200 and x['at']>f['at']for x in row['after']['requests']),'fresh successful resource request absent')
    need(h['at']>f['at']and row['after']['guard']['finished'],'explicit recovery not current')
  for role,vp in [('held15',[393,852]),('heldSE',[375,667])]:
   d=observed[role];f,h,a,end=d['failed'],d['home'],d['after'],d['end'];need(f['viewport']==vp,role+' viewport')
   need(f['guard']['failed']and any(x['held']for x in f['timer'])and f['held'],role+' actual SDK and timer hold absent')
   began=next(x['at']for x in f['sdkCalls']if x['path']=='assets/main/config.json');failed=next(x['at']for x in f['errorEvents']if 'No startup progress'in x['text'])
   need(10000<=failed-began<=12000,role+' bounded frame-watchdog failure')
   need(len([t for t in h['sdk']if t['type']=='touchstart'])==1 and all(t['trusted']for t in h['sdk']),role+' first trusted Retry')
   need(any(x.get('path')=='assets/main/config.json'and x.get('status')==200 and x['at']>f['at']for x in h['requests']),role+' fresh underlying main read')
   need(h['home']and h['guard']['finished']and effect(d['before'],a),role+' recovered HOME/input')
   need([x['kind']for x in d['release']]==['release','reject','release','reject']and all(x['error']is None for x in d['release']),role+' late/duplicate success and failure')
   need(end['guard']==h['guard']and end['hero']['id']==a['hero']['id']and clean(end),role+' stale results altered current generation/scene')
  for role in ['image15','imageSE']:
   d=observed[role];f,h,end=d['failed'],d['home'],d['end'];path='assets/main/native/1e/1e223050a.png'
   imgs=lambda state:[x for x in state['requests']if x.get('type')=='image'and x.get('path')==path]
   need(f['guard']['failed']and len(imgs(f))==1 and len(imgs(h))==2,role+' same URL must issue exactly one fresh image request')
   need(len([t for t in h['sdk']if t['type']=='touchstart'])==1 and all(t['trusted']for t in h['sdk']),role+' first trusted Retry')
   need(h['guard']['finished']and h['home']and effect(d['before'],d['after']),role+' actual image recovery/play')
   need(d['release']['status']==200 and end['guard']==h['guard']and clean(end),role+' old actual image response isolation')
   need(len([x for x in end['requests']if x.get('type')=='image-loaded'and path in x.get('path','')])==2,role+' both actual HTTP images must complete')
  slow=observed['slow'];bg=observed['background'];clock=observed['clock_warm']
  need([x['viewport']for x in slow]==[[393,852],[375,667]]and [x['viewport']for x in bg]==[[393,852],[375,667]]and [x['viewport']for x in clock]==[[393,852],[375,667]],'per-case two ratios')
  for row in slow:
   samples=row['samples'];need(samples[-1]['home']and samples[-1]['at']-samples[0]['at']>10000 and not any(x['guard']['failed']or x['exceptions']for x in samples),'real slow progress incorrectly failed')
   need(len(set(x['completed']for x in samples))>=3 and effect(row['before'],row['after']),'slow actual image progress/play absent')
  for row in bg:
   need(row['hidden']['at']-row['start']['at']>10000 and not row['hidden']['guard']['failed']and row['home']['home']and effect(row['before'],row['after']),'actual SDK background exclusion/play')
  for row in clock:
   calls=row['mainStarted']['sdk'];internal=next(x['at']for x in calls if x['path']=='assets/internal/config.json');main=next(x['at']for x in calls if x['path']=='assets/main/config.json')
   need(main-internal>=7500 and row['later']['at']-main>=6500 and row['later']['at']-internal>10000 and not row['later']['guard']['failed'],'request-local clock inherited entry elapsed time')
   need(row['home']['home']and effect(row['before'],row['after']),'clock recovery/input')
   before,ready,after=row['warmBefore'],row['warmReady'],row['warmAfter']
   need(row['after']['hero']['id']!=ready['hero']['id']and ready['hero']['id']==after['hero']['id']and ready['running']and effect(ready,after),'warm replay new hero/input reset')
   need(before['sdkCalls']==after['sdkCalls']and len(before['sdkCalls'])>0,'warm replay redundantly requested filesystem resources')
   need(clean(after),'warm replay exception')
  # Known bad held-SDK+held-timer execution must actually miss its old deadline.
  old=observed['old_held'];need(old['t']-old['held'][0]['at']>12000 and not old['guard']['failed']and old['timer'][0]['held'],'old held-SDK/frame-watchdog defect absent')
  # Exact Native pin prevents adding Promise/TTF consumers while inheriting N/A.
  ttfs=[];bitmap=[]
  for p in native.rglob('config.json'):
   cfg=json.loads(p.read_text());types=cfg.get('types',[])
   for value in cfg.get('paths',{}).values():
    if not isinstance(value,list)or len(value)<2:continue
    kind=types[value[1]]if isinstance(value[1],int)and value[1]<len(types)else value[1]
    if kind=='cc.TTFFont':ttfs.append(value[0])
    if kind=='cc.BitmapFont':bitmap.append(value[0])
  need(not ttfs and bitmap==['home-hud-v1/digits']and not list(native.rglob('*.ttf')),'optional font applicability changed')
  asset=observed['assets'];need(asset['failed']==0 and asset['unmapped_source_count']==0 and asset['checked_native_assets']>=114 and asset['checked_packs']>=30,'required font/image/assets not preserved')
  for role in ['fs_unit','image_unit','event_unit']:
   need(observed[role].get('passed')is True,role+' terminal-once callback supplement failed')
  need(observed['guard_unit'].get('passed')is True and len(observed['guard_unit']['checks'])==30,'request clock/progress-before-frame supplement absent')
 except (KeyError,TypeError,ValueError,OSError,StopIteration,IndexError)as e:errors.append('RUNHOME-LOADING invalid or missing evidence: '+str(e))
 return errors
