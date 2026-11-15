"""Read-only PLAY affected-state proof shared by startup and locked-art successors.
No execution, rebinding, boolean-only passes, or old result rewriting.
"""
from pathlib import Path
import hashlib,json,math
from PIL import Image
import audit_native_startup_renderer as R
from startup_business_contract import validate_business
TARGET='0d9b9cf2-a987-4be9-9f66-08629044a336'
PLATE='8e0aad79-556b-4a79-bed9-81abd32bb286@f9941'
ALL_TARGETS={TARGET,'8e0aad79-556b-4a79-bed9-81abd32bb286','99948f7a-712f-45bd-b9eb-1a2237a5a287','da7f85e7-16e0-4786-8eeb-917efafe1ea2'}
OLD_TREE='729ace2cb023bdba2ade698c4976c803a47b35c43c565ada2235fbae054eee58'
VPS={(393,852),(375,667)}
def need(ok,message):
 if not ok:raise ValueError('PLAY current proof: '+message)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked(project,ref):
 need(isinstance(ref,dict)and isinstance(ref.get('path'),str)and isinstance(ref.get('sha256'),str),'file reference needs path and SHA')
 p=Path(ref['path']);p=(p if p.is_absolute()else Path(project)/p).resolve()
 need(p.is_relative_to(Path(project).resolve())and p.is_file()and sha(p)==ref['sha256'],'original reference missing, outside project, or changed: '+str(p));return p
def point(value):return isinstance(value,(int,float))and not isinstance(value,bool)and math.isfinite(value)and value>=0
def rect(n):return n.get('screen',n.get('rect'))
def inside(a,b):
 x,y,w,h=rect(a);bx,by,bw,bh=rect(b);return x>=bx-.002 and y>=by-.002 and x+w<=bx+bw+.002 and y+h<=by+bh+.002
def overlap(a,b):
 x,y,w,h=rect(a);bx,by,bw,bh=rect(b);return min(x+w,bx+bw)-max(x,bx)>.002 and min(y+h,by+bh)-max(y,by)>.002

def _capture(project,record,vp,state):
 dumpfile=checked(project,record['dump']);png=checked(project,record.get('screenshot',record.get('png')));d=read(dumpfile)
 need(not d.get('error')and not d.get('errors')and not d.get('truncated'),state+' dump contains errors/truncation')
 need((d.get('page',{}).get('width'),d.get('page',{}).get('height'))==vp,state+' actual viewport differs')
 need(d.get('origin')=='strict-native-host'and Path(d.get('screenshot','')).resolve()==png,state+' screenshot/dump original pair differs')
 image=Image.open(png).convert('RGB');need(image.width>=vp[0]and image.height>=vp[1]and abs(image.width/image.height-vp[0]/vp[1])<.01,state+' PNG dimensions differ')
 ns=d.get('nodes',[]);need(bool(ns),state+' actual rendered nodes missing')
 if state=='held_gameplay':
  need(any('/MapLayer/'in n['path']for n in ns)and not any('/LoadingLayer/'in n['path']for n in ns),'held image did not reach actual gameplay without loading overlay');return {'dump':str(dumpfile),'screenshot':str(png),'viewport':list(vp),'state':state}
 buttons=[n for n in ns if n['path'].endswith('/MainLayer/btnGo')and n.get('comps',{}).get('button')]
 need(len(buttons)==1 and buttons[0]['comps']['button'].get('interactable')is True,state+' actual PLAY button missing/disabled');button=buttons[0]
 need(inside(button,{'screen':[0,0,1,1]}),state+' PLAY button outside viewport')
 children=[n for n in ns if button['id']in n.get('ancestor_ids',[])]
 fallback=[n for n in children if n['name']=='ArtLoadFallback']
 art=[n for n in children if n['name']=='EnglishActionArt'and n.get('comps',{}).get('sprite',{}).get('image_uuid')==TARGET]
 if state=='held_home':
  need(len(fallback)==1 and inside(fallback[0],button),'held PLAY fallback plate missing or outside button')
  plate=fallback[0];caption=[n for n in children if plate['id']in n.get('ancestor_ids',[])and n['name']=='Caption'and n.get('comps',{}).get('label',{}).get('string')=='PLAY']
  need(len(caption)==1 and inside(caption[0],plate),'held readable PLAY caption missing or outside its plate')
  need(not art,'held PLAY image is already decoded instead of held')
  need(not plate.get('comps',{}).get('sprite'),'all-image held fallback unexpectedly has a decoded plate')
  pr=rect(plate);actual_aspect=pr[2]*vp[0]/(pr[3]*vp[1]);need(abs(actual_aspect-813/216)<.04,'fallback plate is not contained in the normal PLAY artwork frame')
  need(not button.get('comps',{}).get('sprite'),'oversized legacy root Sprite is still rendered')
  chapter=[n for n in ns if '/MainLayer/Map/btnChapter/'in n['path']and n.get('comps',{}).get('sprite',{}).get('frame')=='chapter_rewards']
  need(bool(chapter)and not any(overlap(plate,n)for n in chapter),'fallback plate intrudes into chapter rewards row')
  r=rect(caption[0]);crop=image.crop((round(r[0]*image.width),round(r[1]*image.height),round((r[0]+r[2])*image.width),round((r[1]+r[3])*image.height)))
  bright=sum(1 for red,green,blue in crop.getdata()if min(red,green,blue)>=215);need(bright>=max(8,crop.width*crop.height*.002),'held fallback has no actual readable light glyph pixels')
 else:
  need(len(art)==1 and inside(art[0],button),'normal/recovered PLAY artwork missing or outside button')
  need(not fallback,'normal/recovered fallback still rendered over original art')
 return {'dump':str(dumpfile),'screenshot':str(png),'viewport':list(vp),'state':state,'play_button_rect':rect(button)}

def validate_renderer_reference(project,native,binding,ref):
 p=checked(project,ref);report=read(p);rawfile=checked(project,report['raw']);raw=read(rawfile)
 need(report.get('schema')=='native_startup_renderer.v1'and report.get('producer')=='real_browser_native_entry','current normal report is not actual renderer evidence')
 need(report.get('binding')==binding and report.get('native_tree_sha256')==binding['native_tree_sha256']and raw.get('binding')==binding and raw.get('native_tree_sha256')==binding['native_tree_sha256']and Path(raw.get('input_native_root','')).resolve()==Path(native).resolve(),'current normal report/raw Native root or binding differs')
 checked(project,report['runner'])
 need(report.get('passed')is True and raw.get('passed')is True and not raw.get('errors')and not raw.get('first_exception')and not raw.get('console_errors'),'current normal execution failed')
 need(not validate_business(raw),'current normal HOME/trusted input/business chain failed')
 need(raw.get('phase_order')==['entry','adapter','renderer','scene']and raw.get('browser_canvas')=={'native_api':True,'two_d_blocks_webgl':True,'fresh_webgl':True},'current original renderer/Canvas chain missing')
 source=b''.join(p.read_bytes()for p in Path(native).glob('cocos-js/_virtual_cc-*.js'))
 for key in ('game_run','renderer'):
  text=raw.get('engine_identity',{}).get('functions',{}).get(key,'');need(len(text)>30 and text.encode()in source,'current normal engine function changed: '+key)
 for row in report.get('inputs',[]):
  f=Path(native)/row['relative_path'];need(f.is_file()and sha(f)==row['sha256'],'current normal Native input changed')
 need({r['relative_path']for r in report.get('inputs',[])}==set(R.tree(Path(native))),'current normal input inventory is incomplete')
 need(any(e.get('isTrusted')and e.get('type')in('touchend','pointerup')for e in raw.get('raw',{}).get('inputs',[])),'current normal actual trusted event missing')
 checked(project,report['screenshot']);return report,raw

def validate_current_play_report(project,native,report_ref):
 project=Path(project).resolve();native=Path(native).resolve();report_file=checked(project,report_ref);d=read(report_file);binding=d.get('binding',{})
 need(d.get('schema')=='shellstrike_play_image_recovery.v1','affected PLAY report schema differs')
 need(d.get('expected_viewports')==[[393,852],[375,667]],'expected two phone viewports differ')
 need(Path(d.get('native_root','')).resolve()==native and binding.get('native_tree_sha256')==R.digest(R.tree(native)),'actual current Native root/tree changed')
 normals=d.get('normal',[]);faults=d.get('fault',[]);need(len(normals)==2 and len(faults)==2,'exactly two normal and two fault executions required')
 need({tuple(r.get('viewport',[]))for r in normals}==VPS and {tuple(r.get('viewport',[]))for r in faults}==VPS,'normal/fault coverage differs')
 executions=[]
 for row in normals:
  _,raw=validate_renderer_reference(project,native,binding,row['renderer_report']);need(tuple(raw['viewport'])==tuple(row['viewport']),'normal actual viewport differs')
  capture=raw.get('home',{}).get('capture',{});need(bool(capture),'same normal execution has no actual home capture')
  normal_pair={'dump':{'path':capture['file'],'sha256':capture['dump_sha256']},'screenshot':{'path':capture['png'],'sha256':capture['screenshot_sha256']}}
  normal_capture=_capture(project,normal_pair,tuple(row['viewport']),'normal_home')
  normal_dump=read(checked(project,normal_pair['dump']));need('startup_case=normal'in normal_dump.get('url',''),'normal HOME capture was not collected on a normal startup host')
  executions.append({'kind':'normal','viewport':row['viewport'],'renderer':row['renderer_report'],'home_capture':normal_capture})
 for row in faults:
  vp=tuple(row['viewport']);rawfile=checked(project,row['raw']);r=read(rawfile)
  need(r.get('schema')=='shellstrike_play_image_raw.v1'and r.get('binding')==binding and Path(r.get('native_root','')).resolve()==native and tuple(r.get('viewport',[]))==vp and bool(r.get('run_id')),'fault actual execution identity differs')
  need(r.get('passed')is True and not r.get('errors')and not r.get('first_exception')and not r.get('exception_stack')and not r.get('exception_events')and not any(len(e)>=2 and e[1]in('console.error','window.error')for e in r.get('phase_events',[])),'actual PLAY fault execution failed or contains runtime/console error')
  f=r.get('fault',{});h=r.get('home',{});play=r.get('play',{});rec=r.get('recovered',{});release=f.get('release',{});held=f.get('before_release',{}).get('held',[])
  need(f.get('target')==TARGET and set(f.get('targets',[]))==ALL_TARGETS and len(f.get('targets',[]))==4 and f.get('mode')=='permanent'and set(f.get('before_release',{}).get('targets',[]))==ALL_TARGETS and f.get('before_release',{}).get('released')is False and bool(held),'actual permanent target image hold missing')
  need(all(sum(t in str(x.get('url',''))for t in ALL_TARGETS)==1 and point(x.get('t_ms'))and x.get('loaded_at')is None for x in held)and {t for t in ALL_TARGETS if any(t in str(x.get('url',''))for x in held)}==ALL_TARGETS,'held transport must actually reach each of the four exact undecoded images')
  need(h.get('visible')is True and h.get('play_interactable')is True and h.get('fallback_visible')is True and h.get('fallback_text')=='PLAY'and h.get('art_ready')is False and h.get('plate_uuid')is None and h.get('root_plate_uuid')is None,'actual held HOME/PLAY fallback observations missing')
  need(play.get('fault_still_held')is True and play.get('level_ready')is True and play.get('after',{}).get('map_visible')is True and play.get('touch_transport')=='ego_page_cdp'and play.get('before')!=play.get('after'),'held PLAY did not use actual input to enter level')
  need(rec.get('home_visible')is True and rec.get('art_ready')is True and rec.get('fallback_visible')is False,'original artwork/fallback did not recover')
  times=[min(x['t_ms']for x in held),h.get('at_ms'),play.get('at_ms'),release.get('at_ms'),rec.get('at_ms')]
  need(all(point(t)for t in times)and times==sorted(times)and play['at_ms']<release['at_ms'],'held HOME -> real PLAY -> release -> restored HOME chronology differs')
  need(isinstance(release.get('count'),int)and not isinstance(release.get('count'),bool)and release['count']>=len(held),'held image was never actually released')
  need(any(e.get('isTrusted')and e.get('type')in('touchend','pointerup')and play['at_ms']<=e.get('t_ms',-1)<release['at_ms']for e in r.get('inputs',[])),'actual trusted PLAY event absent from held phase')
  need(bool(r.get('phase_events'))and all(any(len(e)>=3 and e[1]=='fault-imghang'and t in str(e[2])for e in r['phase_events'])for t in ALL_TARGETS),'actual host transport hold trace must include all four images')
  captures=r.get('captures',{});states=[_capture(project,captures[state],vp,state)for state in ('held_home','held_gameplay','recovered_home')]
  button_rect=states[0]['play_button_rect'];x,y,w,h=button_rect
  need(any(e.get('isTrusted')and e.get('type')=='touchend'and play['at_ms']<=e.get('t_ms',-1)<release['at_ms']and any(x*vp[0]<=t.get('x',-1)<=(x+w)*vp[0]and y*vp[1]<=t.get('y',-1)<=(y+h)*vp[1]for t in e.get('touches',[]))for e in r.get('inputs',[])),'trusted held-phase input did not land on the actual PLAY button')
  executions.append({'kind':'held_and_recovered','viewport':list(vp),'raw':row['raw'],'captures':states})
 negative=d.get('negative',{});old_report=checked(project,negative['original_report']);old=read(old_report);oldroot=Path(negative.get('native_root','')).resolve()
 need(oldroot.is_relative_to(project)and oldroot.is_dir()and R.digest(R.tree(oldroot))==OLD_TREE and negative.get('native_tree_sha256',negative.get('nativeHash'))==OLD_TREE,'preserved negative Native identity differs')
 need(old.get('suite')=='image_stall'and any(e.get('kind')=='play'and e.get('path','').endswith('/MainLayer/btnGo')and e.get('result')=='fail'and e.get('after',{}).get('on')is False and TARGET in e.get('files',[])for e in old.get('entries',[])),'preserved negative does not show target PLAY failure')
 need(any(e[1]=='fault-imghang'and TARGET in str(e[2])for e in old.get('hits',[])if len(e)>=3),'preserved target fault transport trace missing')
 picture=checked(project,negative.get('screenshot',negative.get('png')));need(Image.open(picture).width>100,'preserved negative screenshot missing')
 return {'schema':'shellstrike_play_image_recovery.checked.v1','report':str(report_file),'report_sha256':sha(report_file),'binding':binding,'native_root':str(native),'normal_executions':2,'fault_executions':2,'executions':executions,'original_negative':{'report':negative['original_report'],'screenshot':negative.get('screenshot',negative.get('png')),'native_tree_sha256':OLD_TREE},'scope':'Current normal and permanent four-image hold (PLAY, yellow plate, profile, add-home) -> readable contained Caption without plate -> trusted gameplay -> release/recovery only. Original R17 negative remains original.'}

# Frozen predecessor identities: original raw/index remain R17 observations.
OLD_BINDING={'build_tag':'ShellStrike-R17','native_tree_sha256':OLD_TREE,'web_tree_sha256':'a45c9bda57b3bea0891c9d0d547f4d111fb07066ce675c68fab5f6e496bb287c','source_sha256':'b0e216127d20f7e93e576150dbe1f106a9dbb0e1b00d996e73a95ffab6723260'}
OLD_INDEX_SHA='514cc893ef02598c6ceff53a98bc152f86ab8b0a3757f6c17ae8c3e72f113ada'
OLD_CONTROLS_SHA='8989f8695837283aedccc20b532ae520c496d2c79c6d1d648f7f9d0747eb17ac'
OLD_VALIDATOR_SHA='0050214b1693f7e03b3f4f6f94bdc0fcb7a06486952d0b3ab6ee42301f65ea9e'
SUCCESSOR_SCHEMA='shellstrike_loading_successor.v1'
SUCCESSOR_PATH='docs/startup/loading-runtime-r18-successor.json'
DELTA_TOOL=Path('/Users/sijunting/.codex/skills/cocos-game-check/package-check/scripts/play_art_delta_guard.py')

def _fixed_module(file,name):
 import importlib.util
 spec=importlib.util.spec_from_file_location(name,file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate_loading_successor(data,binding,project):
 """Validate exact delta + original strict R17 matrix + fresh affected R18 proof.
 Current Native keeps a current whole-tree identity. Old observations are never
 compared to the successor binding or described as executions on the successor.
 """
 import zipfile
 project=Path(project).resolve()
 need(data.get('schema')==SUCCESSOR_SCHEMA and data.get('profile')=='shellstrike_native_startup_v1','loading successor schema/profile differs')
 need(data.get('binding')==binding,'loading successor current binding differs')
 native=Path(data.get('native_root','')).resolve();need(native.is_relative_to(project)and native.is_dir(),'current successor Native root missing/outside project')
 need(R.digest(R.tree(native))==binding.get('native_tree_sha256'),'current successor whole Native tree changed')
 prior=data.get('predecessor',{});need(prior.get('binding')==OLD_BINDING,'predecessor execution binding was changed')
 indexfile=checked(project,prior['loading_index']);need(sha(indexfile)==OLD_INDEX_SHA,'original 26-case loading index changed')
 oldindex=read(indexfile);need(oldindex.get('binding')==OLD_BINDING and oldindex.get('execution_binding')==OLD_BINDING,'old matrix was rebound')
 controlsfile=checked(project,prior['controls']);need(sha(controlsfile)==OLD_CONTROLS_SHA,'original fail/hang controls changed')
 oldnative=Path(prior.get('native_root','')).resolve();need(oldnative.is_relative_to(project)and oldnative.is_dir()and R.digest(R.tree(oldnative))==OLD_TREE,'original executed R17 Native changed')
 legacy_path=project/'qa/startup-contract-r17-locked.py';need(legacy_path.is_file()and sha(legacy_path)==OLD_VALIDATOR_SHA,'frozen original strict validator missing/changed')
 legacy=_fixed_module(legacy_path,'shellstrike_original_r17_startup_validator')
 prior_errors=legacy.validate_loading(oldindex,OLD_BINDING,indexfile.parent);need(not prior_errors,'original strict 26-case matrix failed: '+'; '.join(prior_errors))
 # Preserve the original project renderer/control assertions using its original
 # Native and original normal raw. The old official contract records the old
 # common renderer pass; its runner files are not relabelled as the new runner.
 oldproof=checked(project,prior['renderer_report']);oldreport=read(oldproof);oldraw=read(checked(project,oldreport['raw']))
 oldcontract=read(checked(project,prior['startup_contract']))
 need(oldcontract.get('tool')=='audit_startup_contract'and oldcontract.get('passed')is True and oldcontract.get('binding')==OLD_BINDING,'original official startup contract failed or rebound')
 need(oldcontract.get('startup_renderer_report',{}).get('sha256')==sha(oldproof),'original official renderer identity differs')
 need(oldreport.get('binding')==OLD_BINDING and oldraw.get('binding')==OLD_BINDING,'original normal proof was rebound')
 errors=[]
 def required(ok,message):
  if not ok:errors.append(message)
 def oldref(row,label):
  try:return checked(project,row)
  except (ValueError,KeyError,TypeError,OSError)as e:errors.append(label+': '+str(e));return None
 legacy.validate(oldreport,oldnative,OLD_BINDING,project,oldraw,required,oldref)
 need(not errors,'original strict renderer/control assertions failed: '+'; '.join(errors))
 semantic=data.get('semantic_delta',{});toolref=semantic.get('tool_record',{});tool=Path(toolref.get('path','')).resolve();need(tool==DELTA_TOOL.resolve()and tool.is_file()and sha(tool)==toolref.get('sha256'),'semantic delta tool identity is not the reviewed canonical tool')
 delta_module=_fixed_module(DELTA_TOOL,'shellstrike_play_semantic_guard')
 archive=checked(project,prior['zip']);adapter=checked(project,semantic['adapter']);scope=checked(project,semantic['scope'])
 files={p.relative_to(native).as_posix():p.read_bytes()for p in native.rglob('*')if p.is_file()}
 delta=delta_module.validate(archive,files,adapter,scope)
 need(delta==read(checked(project,semantic['proof'])),'recorded exact semantic delta differs from actual files')
 with zipfile.ZipFile(archive)as z:
  oldmap={n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if not n.endswith('/')}
 need(R.digest(oldmap)==OLD_TREE,'official predecessor ZIP differs from original executed R17 tree')
 need(delta.get('source',{}).get('semantic_changed')==sorted(['assets/res/layer/MainLayer.prefab','assets/scripts/english/EnglishUI.ts','assets/scripts/game/compoment/layer/HomeLayer.ts']),'unexpected source scope')
 # The common guard additionally proves every other compiled module, engine,
 # entry, adapter, SDK file, bundle and asset unchanged, including packed data.
 current=validate_current_play_report(project,native,data['current_play_proof']);need(current['binding']==binding,'current affected-state proof binds another successor')
 return {'schema':'shellstrike_loading_successor.checked.v1','current_binding':binding,'current_native_root':str(native),'predecessor_binding':OLD_BINDING,'predecessor_cases_checked':26,'predecessor_control_assertions':'original fail/hang and actual normal renderer assertions retained','original_loading_index':prior['loading_index'],'exact_delta':delta,'current_affected_state':current,'reuse_semantics':'Original R17 executions retain original identity; current R18 normal/PLAY observations are independently current. No 26-case replay or rebind.'}
