"""Fail-closed validation of real Native entry/renderer browser evidence.
Node mocks remain useful unit checks but cannot satisfy this contract.
"""
from startup_business_contract import validate_business
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tree(root):
 return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

ANT_R3H_CONTROL_PROFILE='ant_scene_deserialize_r3h_v1'
ANT_R3H_RUNNER_KEY='ant-r3h-real-ego-renderer-v1'
ANT_EXACT_NATIVE_CANDIDATES={ANT_R3H_RUNNER_KEY:'reports/startup-v6/r3h-20261025/native-payload','ant-r3k-real-ego-renderer-v1':'reports/startup-v6/r3k-20261025/native-payload','ant-r3l-real-ego-renderer-v1':'reports/startup-v6/r3l-20261026/native-payload','ant-r3m-real-ego-renderer-v1':'reports/startup-v6/r3m-20261026/native-payload'}
ANT_R3H_WORKSPACE='/Users/sijunting/Downloads/！自制游戏/蚂蚁隧道'
ANT_R3H_PROJECT=ANT_R3H_WORKSPACE+'/ant'
ANT_R3H_CONTROL_MANIFEST='reports/startup-v6/r3h-20261025/renderer-controls/control-variants.json'
ANT_R3H_SCENE='subpackages/resources/import/0e/0ebdf0a6d.json'
ANT_R3H_KNOWN_BAD_BINDING={
 'source_sha256':'e95130148b367305338620c776f589d0efb47c8eafa701e23c15bb6b42185758',
 'native_tree_sha256':'ea8b02620c405fdff0076cab1016e0983704b6eb55b12af4e2e6ee9eb8e87657',
 'web_tree_sha256':'4478b310989b5084c784f6b7b0b320c83b3da771ed19ff911fa7c1779f06999d',
 'build_tag':'AntTunnel-HomeV5-20261024-r3b-no-social',
}
ANT_R3H_KNOWN_BAD_TREE='ea8b02620c405fdff0076cab1016e0983704b6eb55b12af4e2e6ee9eb8e87657'
ANT_R3H_KNOWN_BAD_SCENE_SHA='0be310704001b0e32aaccb822305cf2b3a7b42665ac269c9fc26fafa6390f549'
ANT_R3H_KNOWN_BAD_REPORT='reports/startup-v6/scene-home-load-diagnostic-r3b.json'
ANT_R3H_KNOWN_BAD_REPORT_SHA='869a56b2ab4915573ce34251f1ac62ea5c3b22423bc0848b134bd3385837613b'
ANT_R3H_KNOWN_BAD_BINDING_FILE='reports/startup-v6/execution-binding-r3b.json'
ANT_R3H_KNOWN_BAD_BINDING_FILE_SHA='42932f55a8b9ba3bfcee7acce611b51edd8dd3c5b71762aa5c2dc8016f2e5c62'
ANT_R3H_SCENE_ERROR_NAME='TypeError'
ANT_R3H_SCENE_ERROR_MESSAGE="Cannot create property '1' on number '0'"
ANT_R3H_PARSER_ERROR_MESSAGE='unpack subpackages/resources/import/0e/0ebdf0a6d.json failed! details: package data is wrong!'
def _validate_ant_engine_identity(data, native, need):
 identity=data.get('engine_identity',{})
 if not isinstance(identity,dict):identity={}
 capture=identity.get('capture',{})
 if not isinstance(capture,dict):capture={}
 base=native/'cocos/cocos2d-js-min.js';adapter=native/'adapter-min.js'
 need(base.is_file() and adapter.is_file(),'Ant r3h frozen engine or Native adapter source missing')
 if base.is_file():need(data.get('engine_source_sha256')==sha(base),'Ant renderer raw engine source SHA differs from the current Native engine')
 if adapter.is_file():
  probe=data.get('engine_probe',{})
  if not isinstance(probe,dict):probe={}
  need(data.get('adapter_source_sha256',probe.get('adapter_file_sha256'))==sha(adapter),'Ant renderer raw adapter source SHA differs from current Native adapter')
 rules={'game_run':base,'renderer':base}
 for label,path in rules.items():
  row=capture.get(label,{})
  if not isinstance(row,dict):row={}
  expected={'before_source','after_source','before_function_sha256','after_function_sha256','before_source_sha256','after_source_sha256','before_matches_native','after_matches_native_adapter'}
  need(set(row)==expected,'Ant '+label+' capture must use the exact original/wrapper identity fields')
  before=row.get('before_source');after=row.get('after_source')
  if not isinstance(before,str) or not before:need(False,'Ant '+label+' original Function#toString source missing');before=''
  if not isinstance(after,str) or not after:need(False,'Ant '+label+' adapter Function#toString source missing');after=''
  before_hash=hashlib.sha256(before.encode('utf-8')).hexdigest()
  after_hash=hashlib.sha256(after.encode('utf-8')).hexdigest()
  need(row.get('before_source_sha256')==before_hash==row.get('before_function_sha256'),'Ant '+label+' original function/source SHA mismatch')
  need(row.get('after_source_sha256')==after_hash==row.get('after_function_sha256'),'Ant '+label+' wrapper function/source SHA mismatch')
  if path.is_file():need(before.encode('utf-8') in path.read_bytes() and row.get('before_matches_native') is True,'Ant '+label+' original source does not match frozen Native engine bytes')
  if adapter.is_file():need(after.encode('utf-8') in adapter.read_bytes() and row.get('after_matches_native_adapter') is True,'Ant '+label+' wrapper source does not match current Native adapter bytes')
 need(identity.get('canvas_get_context_original') is True,'Ant Canvas getContext must remain the native browser function')
 return []

def _ant_repo_path(value, project, need, label):
 try:
  path=Path(value)
  path=path if path.is_absolute() else project.parent/path
  path=path.resolve();workspace=project.parent.resolve()
  need(path.is_relative_to(workspace),label+' escapes the Ant workspace')
  return path
 except (OSError,TypeError,ValueError):
  need(False,label+' path invalid');return None

def _ant_scene_transform(raw, need):
 try:
  data=json.loads(raw.decode('utf-8'))
  if not (isinstance(data,list) and len(data)>5 and isinstance(data[5],list) and data[5] and isinstance(data[5][0],list) and data[5][0] and isinstance(data[5][0][0],list)):
   need(False,'Ant control scene serialization shape changed');return None,None
  objects=data[5][0][0]
  anchors=[('legacy-control-01','0ePdJgqCxOB6vIh65eseba',7,-8),('legacy-control-02','310jtsz91NgajGKtps4lVF',9,-10),('legacy-control-03','ce5K3CUJ5Ijq+D18hG+7cI',11,-12)]
  roots=[row for row in objects if isinstance(row,list) and len(row)>2 and row[1]=='SceneHome' and isinstance(row[2],list)]
  need(len(roots)==1,'Ant SceneHome root-child anchor changed')
  if len(roots)!=1:return None,None
  changes=[]
  for name,token,index,child_ref in anchors:
   matches=[(i,row) for i,row in enumerate(objects) if isinstance(row,list) and len(row)>1 and token in json.dumps(row,ensure_ascii=False)]
   need(len(matches)==1,'Ant social-node token must match exactly once: '+token)
   if len(matches)!=1:return None,None
   actual_index,row=matches[0]
   need(actual_index==index and row[1]==name,'Ant social-node name/index anchor changed: '+token)
   need(roots[0][2].count(child_ref)==1,'Ant SceneHome child reference must occur once: '+str(child_ref))
   if actual_index!=index or row[1]!=name or roots[0][2].count(child_ref)!=1:return None,None
   row[1]='';roots[0][2].remove(child_ref)
   changes.append({'node_name':name,'token':token,'object_index':index,'child_ref':child_ref,'after_name':''})
  encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode('utf-8')
  return encoded,changes
 except (UnicodeDecodeError,ValueError,TypeError,IndexError,KeyError) as exc:
  need(False,'Ant control scene transform invalid: '+str(exc));return None,None

def _ant_scene_error(control, need, label, parser_mismatch=False):
 scene=control.get('scene',{})
 if not isinstance(scene,dict):scene={}
 error=scene.get('callback_error',{})
 scene_path=scene.get('path')
 if not scene_path:
  loaded=control.get('scene_load',{})
  if isinstance(loaded,dict):
   scene_path=loaded.get('request_path')
   error=loaded.get('callback_error',loaded.get('error',error))
 if not isinstance(error,dict):error={}
 need(scene_path==ANT_R3H_SCENE,label+' must fail in the SceneHome Native import')
 if parser_mismatch:
  need(error.get('name')=='Error' and error.get('message')==ANT_R3H_PARSER_ERROR_MESSAGE,label+' must reproduce the captured Cocos bundle-unpack type-mismatch error')
 else:
  need(error.get('name')==ANT_R3H_SCENE_ERROR_NAME and error.get('message')==ANT_R3H_SCENE_ERROR_MESSAGE,label+' must reproduce the captured Cocos deserialize TypeError')
 stack=error.get('stack','')
 if parser_mismatch:
  need('Object.unpack' in stack and 'cocos2d-js-min.js' in stack and 'adapter-min.js' in stack,label+' actual Cocos unpack and adapter callback stack missing')
 else:need('deserialize' in stack and 'parseImport' in stack,label+' Cocos deserialize/parseImport stack missing')
 renderer=control.get('renderer',{})
 if not isinstance(renderer,dict):renderer={}
 need(renderer.get('webgl_context') is True,label+' must reach the real WebGL renderer')

def _validate_ant_r3h_controls(report, native, binding, project, normal_raw, need, ref):
 need(report.get('control_profile')==ANT_R3H_CONTROL_PROFILE,'Ant Native renderer control profile missing or unsupported')
 variants_ref=report.get('control_variants',{})
 need(set(variants_ref)=={'path','sha256'},'Ant control-variant manifest reference must be exact {path,sha256}')
 variants_path=_ant_repo_path(variants_ref.get('path',''),project,need,'Ant control-variant manifest')
 variants={}
 if variants_path and variants_path.is_file() and sha(variants_path)==variants_ref.get('sha256'):
  try:variants=json.loads(variants_path.read_text())
  except (ValueError,OSError):need(False,'Ant control-variant manifest invalid')
 else:need(False,'Ant control-variant manifest missing or changed')
 need(variants.get('schema')=='ant-r3h-native-renderer-control-variants.v1','Ant control-variant schema mismatch')
 need(variants.get('base_binding')==binding,'Ant control variants are not bound to current source/Native/Web')
 current_tree=tree(native);current_digest=digest(current_tree)
 expected_native=ANT_EXACT_NATIVE_CANDIDATES.get(report.get('execution',{}).get('registered_runner'))
 need(expected_native is not None and Path(native).resolve()==(Path(ANT_R3H_WORKSPACE)/expected_native).resolve(),'Ant control runner/candidate directory is not an exact approved pair')
 need(variants.get('base_native')=={'path':expected_native,'files':len(current_tree),'tree_sha256':current_digest},'Ant control manifest current Native identity mismatch')
 known=variants.get('known_bad',{})
 known_path=_ant_repo_path(known.get('path',''),project,need,'Ant known-bad Native')
 known_tree=tree(known_path) if known_path and known_path.is_dir() else {}
 need(known.get('path')=='reports/startup-v6/native-payload-r3b','Ant known-bad must use the preserved r3b Native candidate')
 need(known.get('binding')==ANT_R3H_KNOWN_BAD_BINDING and len(known_tree)==241 and digest(known_tree)==ANT_R3H_KNOWN_BAD_TREE==known.get('tree_sha256'),'Ant preserved r3b Native tree/binding mismatch')
 known_scene=known_path/ANT_R3H_SCENE if known_path else None
 need(known.get('scene_path')==ANT_R3H_SCENE and known_scene is not None and known_scene.is_file() and sha(known_scene)==ANT_R3H_KNOWN_BAD_SCENE_SHA==known.get('scene_sha256'),'Ant known-bad SceneHome input changed')
 provenance_file=_ant_repo_path(ANT_R3H_KNOWN_BAD_REPORT,project,need,'Ant known-bad provenance report')
 provenance_binding=_ant_repo_path(ANT_R3H_KNOWN_BAD_BINDING_FILE,project,need,'Ant known-bad binding file')
 need(provenance_file is not None and provenance_file.is_file() and sha(provenance_file)==ANT_R3H_KNOWN_BAD_REPORT_SHA,'Ant known-bad historical failure report changed')
 need(provenance_binding is not None and provenance_binding.is_file() and sha(provenance_binding)==ANT_R3H_KNOWN_BAD_BINDING_FILE_SHA,'Ant known-bad historical binding file changed')
 if provenance_file and provenance_file.is_file():
  try:
   historical=json.loads(provenance_file.read_text());need(historical.get('binding')==ANT_R3H_KNOWN_BAD_BINDING,'Pinned r3b failure report binding mismatch')
   need(historical.get('scene_failure') is True,'Pinned r3b failure report no longer records SceneHome failure')
   probe=historical.get('loader_probe',{});events=probe.get('events',[]) if isinstance(probe,dict) else []
   rows=[x for x in events if x.get('kind')=='loadRes' and x.get('path')=='scenes/SceneHome' and isinstance(x.get('callback'),dict)]
   need(len(rows)==1,'Pinned r3b report must contain one SceneHome loadRes failure event')
   error=rows[0].get('callback',{}).get('error',{}) if rows else {}
   stack=error.get('stack','') if isinstance(error,dict) else ''
   need(isinstance(error,dict) and error.get('name')==ANT_R3H_SCENE_ERROR_NAME and error.get('message')==ANT_R3H_SCENE_ERROR_MESSAGE and 'deserialize' in stack and 'parseImport' in stack,'Pinned r3b provenance does not contain the exact captured Cocos TypeError')
  except (ValueError,OSError):need(False,'Pinned r3b failure report invalid')
 controls=report.get('controls',{})
 for name in ['known_bad','reintroduced_defect','parser_type_mismatch']:
  row=controls.get(name,{})
  path=ref(row,name+' actual execution');control={}
  if path:
   try:control=json.loads(path.read_text())
   except (ValueError,OSError):need(False,name+' result invalid')
  need(control.get('passed') is False,name+' must actually fail')
  need(control.get('control_profile')==ANT_R3H_CONTROL_PROFILE,name+' control profile mismatch')
  need(control.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' must use the same registered runner')
  need(control.get('browser_canvas')==normal_raw.get('browser_canvas') and bool(control.get('browser_canvas')),name+' real Canvas calibration differs from normal execution')
  need(control.get('viewport')==normal_raw.get('viewport') and control.get('device_metrics')==normal_raw.get('device_metrics') and control.get('touch')==normal_raw.get('touch') and control.get('user_agent')==normal_raw.get('user_agent'),name+' browser viewport/device metrics/touch/UA differs from normal execution')
  need(isinstance(control.get('errors'),list) and bool(control.get('errors')),name+' actual browser error evidence missing')
  _ant_scene_error(control,need,name,parser_mismatch=name=='parser_type_mismatch')
  native_root=_ant_repo_path(control.get('native_root',''),project,need,name+' Native root')
  observed_tree=tree(native_root) if native_root and native_root.is_dir() else {}
  observed_digest=digest(observed_tree) if observed_tree else ''
  need(control.get('native_tree_sha256')==observed_digest,name+' recorded tree hash differs from control Native root')
  if name=='known_bad':
   need(control.get('failure_kind')=='ant_scene_deserialize','Ant known-bad failure type mismatch')
   need(control.get('binding')==ANT_R3H_KNOWN_BAD_BINDING and observed_digest==ANT_R3H_KNOWN_BAD_TREE,'Ant known-bad control is not the preserved r3b candidate')
   provenance=control.get('provenance',{})
   if not isinstance(provenance,dict):provenance={}
   control_root=_ant_repo_path(control.get('native_root',provenance.get('candidate_path','')),project,need,'Ant known-bad control Native root')
   need(control_root==known_path,'Ant known-bad control root differs from preserved candidate')
   expected_provenance={'kind':'preserved_candidate_r3b','candidate_path':known.get('path'),'candidate_tree_sha256':ANT_R3H_KNOWN_BAD_TREE,'binding_file':ANT_R3H_KNOWN_BAD_BINDING_FILE,'binding_file_sha256':ANT_R3H_KNOWN_BAD_BINDING_FILE_SHA,'source_failure_report':ANT_R3H_KNOWN_BAD_REPORT,'source_failure_report_sha256':ANT_R3H_KNOWN_BAD_REPORT_SHA}
   need(control.get('provenance')==expected_provenance,'Ant known-bad preserved-candidate provenance mismatch')
  else:
   mutation_name='reintroduced_defect' if name=='reintroduced_defect' else 'parser_type_mismatch'
   mutation=variants.get(mutation_name,{})
   candidate_root=_ant_repo_path(mutation.get('root',''),project,need,name+' mutation Native')
   base_scene=native/ANT_R3H_SCENE
   if not base_scene.is_file():need(False,'Ant current SceneHome input missing')
   base_raw=base_scene.read_bytes() if base_scene.is_file() else b''
   if name=='reintroduced_defect':
    output_raw,nodes=_ant_scene_transform(base_raw,need)
    expected_bytes=output_raw or b''
    expected_sha=hashlib.sha256(expected_bytes).hexdigest() if output_raw is not None else ''
    expected_mutation=dict(mutation)
    expected_scene={'path':ANT_R3H_SCENE,'base_sha256':sha(base_scene) if base_scene.is_file() else '', 'base_bytes':len(base_raw),'output_sha256':expected_sha,'output_bytes':len(expected_bytes)}
    need(mutation.get('scene')==expected_scene and mutation.get('nodes')==nodes,'Ant reintroduced defect is not the exact old SceneHome transform')
    need(mutation.get('recipe')=='Copy exact r3h Native; in data[5][0][0], find the unique node by each provided name and token; set its name to empty string; remove its single negative child ref from SceneHome children. Preserve all import dependencies/groups/config.','Ant reintroduced-defect recipe text changed')
    expected_tree=dict(current_tree)
    if output_raw is not None:expected_tree[ANT_R3H_SCENE]=expected_sha
    expected_digest=digest(expected_tree)
   else:
    expected_bytes=b'0';expected_sha=hashlib.sha256(expected_bytes).hexdigest()
    expected_scene={'path':ANT_R3H_SCENE,'base_sha256':sha(base_scene) if base_scene.is_file() else '', 'base_bytes':len(base_raw),'output_sha256':expected_sha,'output_bytes':1,'json_input_type':'number','json_input_value':0}
    need(mutation.get('scene')==expected_scene,'Ant parser-type negative is not the exact JSON number input')
    need(mutation.get('recipe')=='Copy exact r3h Native; replace only SceneHome import JSON with the single JSON number 0; execute actual Cocos loadRes after renderer init.','Ant parser-type negative recipe text changed')
    expected_tree=dict(current_tree);expected_tree[ANT_R3H_SCENE]=expected_sha;expected_digest=digest(expected_tree)
   need(mutation.get('base_native_tree_sha256')==current_digest and mutation.get('changed_paths')==[ANT_R3H_SCENE] and mutation.get('files')==len(current_tree) and mutation.get('tree_sha256')==expected_digest,'Ant control mutation tree is not the exact one-file current-base variant')
   need(candidate_root is not None and candidate_root.is_dir() and observed_tree==expected_tree,'Ant control Native bytes differ from recomputed current-base mutation')
   need(native_root==candidate_root and control.get('base_binding')==binding and control.get('base_native_tree_sha256')==current_digest and observed_digest==expected_digest,'Ant control Native provenance/current-base mismatch')
   need(control.get('mutation')==mutation,'Ant control mutation record differs from exact manifest')
   if name=='reintroduced_defect':
    need(control.get('binding')==binding and control.get('failure_kind')=='ant_scene_deserialize','Ant reintroduced control must fail with the preserved SceneHome deserialize defect')
   else:
    parser=control.get('parser',{})
    need(control.get('binding')==binding and control.get('failure_kind')=='native_parser_type_mismatch','Ant parser-type control failure kind mismatch')
    need(parser.get('api')=="cc.loader.loadRes('scenes/SceneHome')" and parser.get('stage')=='after Cocos WebGL renderer initialization during actual SceneHome loadRes','Ant parser-type control did not exercise the actual SceneHome loadRes path')
    need(parser.get('input_type')=='number' and parser.get('input_value')==0 and parser.get('renderer_initialized') is True,'Ant parser-type negative input/renderer evidence missing')
 return []

def validate(report, native, binding, project):
 errors=[];native=Path(native).resolve();project=Path(project).resolve()
 def need(ok,msg):
  if not ok: errors.append('STARTUP-RENDERER: '+msg)
 def ref(row,label):
  try:
   p=Path(row['path'])
   if not p.is_absolute():p=(project.parent/p) if report.get('control_profile')==ANT_R3H_CONTROL_PROFILE else (project/p)
   p=p.resolve()
   allowed=project.parent if report.get('control_profile')==ANT_R3H_CONTROL_PROFILE else project
   need(p.is_relative_to(allowed),label+' path escapes its registered report root')
   need(p.is_file() and sha(p)==row['sha256'],label+' missing or changed')
   return p if p.is_file() else None
  except (KeyError,TypeError,OSError): need(False,label+' identity missing');return None
 need(report.get('schema')=='native_startup_renderer.v1','schema missing')
 need(report.get('producer')=='real_browser_native_entry','real browser producer required')
 need(report.get('binding')==binding,'final source/Native/Web binding mismatch')
 need(isinstance(binding,dict) and all(binding.get(x) for x in ['source_sha256','native_tree_sha256','web_tree_sha256','build_tag']),'complete source/Native/Web/build binding required')
 need(isinstance(binding,dict) and binding.get('native_tree_sha256')==digest(tree(native)),'binding Native tree mismatch')
 need(report.get('native_tree_sha256')==digest(tree(native)),'Native tree mismatch')
 for row in report.get('inputs',[]):
  rel=row.get('relative_path','');p=native/rel
  need(bool(rel) and p.is_file() and sha(p)==row.get('sha256'),'Native input changed: '+rel)
 inputs={r.get('relative_path') for r in report.get('inputs',[])}
 if report.get('control_profile')=='cocos24_image_recovery_v1':need({'game.js','main.js','adapter.js'}<=inputs,'entry and actual adapter identities required')
 elif report.get('control_profile')!='cocos3_systemjs_native_v1':need({'game.js','main.js','adapter-min.js'}<=inputs,'entry and real adapter identities required')
 need(any('cocos' in str(x).lower() for x in inputs),'real engine identity required')
 if report.get('control_profile')=='cocos3_systemjs_native_v1':
  try:
   settings=json.loads((native/'src/settings.json').read_text());scene=settings['launch']['launchScene'];roots=[x['root'].strip('/') for x in json.loads((native/'game.json').read_text()).get('subpackages',[])];roots+=['assets/'+x['bundle'] for x in settings.get('assets',{}).get('preloadBundles',[]) if isinstance(x,dict) and x.get('bundle')]
   scene_packs=[]
   for root in roots:
    config=native/root/'config.json'
    if not config.is_file():continue
    value=json.loads(config.read_text());index=value.get('scenes',{}).get(scene)
    if index is None:continue
    for pack,ids in value.get('packs',{}).items():
     if index in ids:scene_packs.append((config.relative_to(native).as_posix(),root+'/import/'+pack[:2]+'/'+pack+'.json'))
   need(bool(scene_packs) and any(config in inputs and pack in inputs and (native/pack).is_file() for config,pack in scene_packs),'actual declared Cocos3 launch-scene config and data pack identities required')
  except (KeyError,TypeError,ValueError,OSError):need(False,'invalid declared Cocos3 launch-scene identity')
 else:need(any(str(x).startswith('assets/') for x in inputs),'actual scene bundle identity required')
 need(ref(report.get('runner',{}),'browser runner') is not None,'runner required')
 raw=ref(report.get('raw',{}),'raw browser result');data={}
 if raw:
  try:data=json.loads(raw.read_text())
  except (ValueError,OSError):need(False,'raw result invalid')
 need(data.get('binding')==binding,'raw execution binding mismatch')
 need(data.get('native_tree_sha256')==report.get('native_tree_sha256'),'raw Native tree mismatch')
 need(data.get('browser_canvas')=={'native_api':True,'two_d_blocks_webgl':True,'fresh_webgl':True},'real Canvas mutual exclusion calibration missing')
 viewport=data.get('viewport',[])
 need(len(viewport)==2 and viewport[0]>0 and viewport[1]>viewport[0] and data.get('touch',0)>=1 and 'Mobile' in data.get('user_agent',''),'actual mobile viewport/touch/UA required')
 if report.get('control_profile')==ANT_R3H_CONTROL_PROFILE:
  metrics=data.get('device_metrics',[])
  need(metrics==[390,844,3,5] and viewport==metrics[:2] and data.get('touch')==metrics[3],'Ant r3h actual viewport/DPR/touch device metrics must be [390,844,3,5]')
 identity=data.get('engine_identity',{})
 if report.get('control_profile')==ANT_R3H_CONTROL_PROFILE:
  errors.extend(_validate_ant_engine_identity(data,native,need))
 else:
  for name in ['game_run_original','renderer_original','canvas_get_context_original']:
   need(identity.get(name) is True,'mock or replacement rejected: '+name)
 need(data.get('phase_order')==['entry','adapter','renderer','scene'],'actual Native chain incomplete')
 need(data.get('renderer',{}).get('webgl_context') is True,'real WebGL renderer missing')
 need(data.get('scene',{}).get('active') is True and bool(data.get('scene',{}).get('name')),'active actual scene missing')
 need(data.get('passed') is True and not data.get('errors'),'actual startup failed')
 errors.extend(validate_business(data))
 picture=ref(report.get('screenshot',{}),'same execution screenshot')
 if picture:need(picture.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and picture.stat().st_size>5000,'actual screenshot required')
 if report.get('control_profile')==ANT_R3H_CONTROL_PROFILE:
  errors.extend(_validate_ant_r3h_controls(report,native,binding,project,data,need,ref))
 elif report.get('control_profile')=='googly_native_recovery_v1':
  from googly_native_recovery_contract import validate as validate_googly
  validate_googly(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='native_loading_recovery_v1':
  controls=report.get('controls',{})
  for name in ['known_bad','reintroduced_defect']:
   evidence=ref(controls.get(name,{}),name+' actual Native loading failure');control={}
   if evidence:
    try:control=json.loads(evidence.read_text())
    except (ValueError,OSError):need(False,name+' invalid raw loading result')
   need(control.get('passed') is False and bool(control.get('errors')),name+' must actually fail')
   failure=control.get('failure_observation',{})
   need(failure.get('home_visible') is False and failure.get('retry_visible') is False and failure.get('sdk_failure_observed') is True and failure.get('observed_ms',0)>=8000,name+' must reproduce failed subpackage with no HOME or usable Retry')
   need(control.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' same runner required')
   need(control.get('browser_canvas')==data.get('browser_canvas'),name+' real Canvas calibration required')
   try:
    root=Path(control['input_native_root']).resolve();root.relative_to(project.resolve())
    manifest=tree(root);need(digest(manifest)==control.get('native_tree_sha256') and control.get('native_tree_sha256')!=report.get('native_tree_sha256'),name+' actual distinct Native tree required')
    if name=='known_bad':
     import zipfile
     source=ref(control.get('source_zip',{}),'preserved original Native ZIP')
     if source:
      with zipfile.ZipFile(source) as z: original={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
      need(original==manifest,'known_bad Native must match preserved original ZIP exactly')
    else:
     base=tree(native);mutation=control.get('mutation',{});file=mutation.get('file')
     need(control.get('base_native_tree_sha256')==report.get('native_tree_sha256'),'reintroduced defect must bind final Native')
     need(file=='main.js' and mutation.get('base_sha256')==base.get(file) and mutation.get('mutated_sha256')==manifest.get(file),'exact main bootstrap mutation required')
     need({k:v for k,v in manifest.items() if k!=file}=={k:v for k,v in base.items() if k!=file},'reintroduced defect changed unrelated files')
   except (KeyError,TypeError,ValueError,OSError):need(False,name+' actual input/provenance invalid')
 elif report.get('control_profile')=='runhome_native_recovery_v1':
  from runhome_native_recovery_contract import validate as validate_runhome
  validate_runhome(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='cocos24_adapter_coordinates_v1':
  from cocos24_adapter_coordinates_contract import validate as validate_adapter_coordinates
  validate_adapter_coordinates(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='cocos24_sdk_screen_input_v1':
  from cocos24_screen_input_contract import validate as validate_screen_input
  validate_screen_input(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='cocos24_tiktok_screen_input_v1':
  from cocos24_tiktok_screen_input_contract import validate as validate_screen_input
  validate_screen_input(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='duo_sdk_ui_retry_v1':
  from duo_sdk_ui_retry_contract import validate as validate_duo
  validate_duo(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='cocos24_image_recovery_v1':
  from cocos24_image_recovery_contract import validate as validate_cocos24
  validate_cocos24(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='tankace_optional_sdk_and_scene_v1':
  from tankace_native_renderer_contract import validate as validate_tankace
  validate_tankace(report,native,binding,project,data,need,ref)
 elif report.get('control_profile')=='cocos3_systemjs_native_v1':
  from cocos3_native_renderer_contract import validate as validate_cocos3
  validate_cocos3(report,native,data,need,ref)
 elif report.get('control_profile') in (None,'ember_canvas_context_conflict_v1'):
  controls=report.get('controls',{})
  for name in ['known_bad','reintroduced_defect','parser_type_mismatch']:
   row=controls.get(name,{})
   evidence=ref(row,name+' actual execution');control={}
   if evidence:
    try:control=json.loads(evidence.read_text())
    except (ValueError,OSError):need(False,name+' result invalid')
   need(control.get('passed') is False,name+' must actually fail')
   need(control.get('failure_kind')==('native_parser_type_mismatch' if name=='parser_type_mismatch' else 'canvas_context_conflict'),name+' must reproduce the same startup defect')
   need(control.get('browser_canvas')==data.get('browser_canvas') and bool(control.get('browser_canvas')),name+' same real Canvas calibration required')
   need(control.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' same runner required')
   need(bool(control.get('native_tree_sha256')) and control.get('native_tree_sha256')!=report.get('native_tree_sha256'),name+' distinct actual Native identity required')
   need(bool(control.get('errors')),name+' actual failure evidence missing')
   if name=='known_bad':need(control.get('provenance',{}).get('kind')=='preserved_original_export' and bool(control.get('provenance',{}).get('sha256')),'preserved original failure provenance required')
   else:need(control.get('base_native_tree_sha256')==report.get('native_tree_sha256') and bool(control.get('mutation')),'exact final-tree defect reintroduction required')
   if name=='parser_type_mismatch':need(control.get('renderer',{}).get('webgl_context') is True,'parser negative must reach real renderer before failing')
 else:
  need(False,'unknown Native renderer control profile')
 return errors


def execute_registered(report, native, binding, project):
 """Only Skill-reviewed fixed Python runners; never execute report-supplied argv."""
 errors=[];project=Path(project).resolve();native=Path(native).resolve()
 registry_path=Path(__file__).with_name('native_startup_trusted_runners.json')
 try:
  registry=json.loads(registry_path.read_text());key=report['execution']['registered_runner'];policy=registry[key]
  if policy['project']!=str(project):raise ValueError('registered project mismatch')
  expected_profile=policy.get('control_profile','ember_canvas_context_conflict_v1')
  if report.get('control_profile') not in (None,expected_profile):raise ValueError('control profile differs from trusted runner registration')
  if expected_profile!='ember_canvas_context_conflict_v1' and report.get('control_profile')!=expected_profile:raise ValueError('trusted runner control profile is required')
  scope=policy.get('runner_scope','project')
  if scope=='project':
   if 'workspace' in policy:raise ValueError('project-scoped runner cannot declare workspace')
   allowed_root=project
   excluded_root=None
  elif scope=='workspace_root':
   if key not in ANT_EXACT_NATIVE_CANDIDATES or expected_profile!=ANT_R3H_CONTROL_PROFILE:raise ValueError('workspace_root scope is reserved for the exact approved Ant renderer profiles')
   if native!=(Path(ANT_R3H_WORKSPACE)/ANT_EXACT_NATIVE_CANDIDATES[key]).resolve():raise ValueError('Ant registered runner/candidate Native directory mismatch')
   workspace=Path(policy.get('workspace','')).resolve()
   if str(project)!=ANT_R3H_PROJECT or str(workspace)!=ANT_R3H_WORKSPACE or project!=workspace/'ant':raise ValueError('Ant workspace_root must bind the exact workspace/ant project pair')
   if report.get('control_profile')!=ANT_R3H_CONTROL_PROFILE:raise ValueError('Ant workspace_root requires its exact control profile')
   allowed_root=workspace
   excluded_root=project
  else:raise ValueError('unknown trusted runner scope: '+str(scope))
  native_binding=policy.get('native_binding')
  if native_binding is not None:
   if not isinstance(native_binding,dict) or native_binding.get('kind')!='fixed_project_path':raise ValueError('unknown registered Native binding')
   relative=native_binding.get('relative_path')
   if not isinstance(relative,str) or not relative or relative.startswith('/') or '\\' in relative or any(part in ('','.', '..') for part in relative.split('/')):raise ValueError('invalid registered Native relative path')
   served_native=(allowed_root/relative).resolve()
   if not served_native.is_relative_to(allowed_root) or not served_native.is_dir():raise ValueError('registered served Native directory missing or outside project')
   if native!=served_native:raise ValueError('registered runner serves a different Native directory; candidate binding mismatch')
  def registered_file(raw_path, expected_sha, label):
   path=Path(raw_path).resolve()
   if not path.is_relative_to(allowed_root) or (excluded_root is not None and path.is_relative_to(excluded_root)):
    raise ValueError(label+' outside registered '+scope+' scope')
   if not path.is_file() or not isinstance(expected_sha,str) or len(expected_sha)!=64 or sha(path)!=expected_sha:
    raise ValueError(label+' changed or SHA-256 mismatch')
   return path
  runner=registered_file(policy['path'],policy['sha256'],'trusted runner')
  if report.get('runner')!={'path':str(runner),'sha256':policy['sha256']}:raise ValueError('reported runner differs from trusted registration')
  dependencies=policy.get('dependencies',{})
  if not isinstance(dependencies,dict):raise ValueError('trusted runner dependencies must be an exact path-to-SHA map')
  for dependency,expected_sha in dependencies.items():
   path=registered_file(dependency,expected_sha,'trusted runner dependency')
  expected=digest(tree(native));timeout=policy['timeout_seconds']
  if not isinstance(timeout,int) or not 1<=timeout<=120:raise ValueError('trusted timeout out of bounds')
  with tempfile.TemporaryDirectory(prefix='native-startup-replay-') as td:
   output=Path(td)/'report.json'
   command=[sys.executable,str(runner),'--native',str(native),'--expected-native-hash',expected,'--report',str(output),'--binding-json',json.dumps(binding,sort_keys=True)]
   # command from reviewed code only, shell disabled; report.command is descriptive.
   process=subprocess.run(command,capture_output=True,text=True,timeout=timeout,shell=False,cwd=project)
   if process.returncode:errors.append('STARTUP-RENDERER executable real-browser probe failed: '+process.stderr[-1000:])
   if not output.is_file():errors.append('STARTUP-RENDERER executable probe produced no report')
   else:
    actual=json.loads(output.read_text());errors+=validate(actual,native,binding,project)
    if actual.get('execution',{}).get('registered_runner')!=key:errors.append('STARTUP-RENDERER replay runner identity differs')
   if digest(tree(native))!=expected:errors.append('STARTUP-RENDERER Native changed during replay')
 except (KeyError,TypeError,ValueError,OSError,subprocess.TimeoutExpired) as e:errors.append('STARTUP-RENDERER trusted execution refused: '+str(e))
 return errors
