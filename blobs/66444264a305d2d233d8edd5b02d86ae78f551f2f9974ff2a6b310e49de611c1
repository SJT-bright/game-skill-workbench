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

def validate(report, native, binding, project):
 import project_qa
 try:
  policy=project_qa.lookup(project,'runners',report.get('execution',{}).get('registered_runner'))
  if policy.get('legacy_full_validation'):
   return project_qa.invoke(policy,'validate',report,native,binding,project,field='validator_path')
 except (ValueError,KeyError,TypeError,OSError) as exc:
  return ['STARTUP-RENDERER trusted project validation refused: '+str(exc)]
 errors=[];native=Path(native).resolve();project=Path(project).resolve()
 def need(ok,msg):
  if not ok: errors.append('STARTUP-RENDERER: '+msg)
 def ref(row,label):
  try:
   p=Path(row['path'])
   if not p.is_absolute():p=(project/p)
   p=p.resolve()
   allowed=project
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
 if report.get('control_profile')!='cocos3_systemjs_native_v1':need({'game.js','main.js','adapter-min.js'}<=inputs,'entry and real adapter identities required')
 need(any('cocos' in str(x).lower() for x in inputs),'real engine identity required')
 scene_inputs=[x for x in inputs if str(x).startswith('assets/')]
 if report.get('control_profile')=='cocos3_systemjs_native_v1':
  for name in inputs:
   if str(name).startswith('subpackages/') and str(name).endswith('/config.json'):
    try:
     config=json.loads((native/name).read_text())
     if isinstance(config,dict) and config.get('scenes'):scene_inputs.append(name)
    except (ValueError,OSError):pass
 need(bool(scene_inputs),'actual scene bundle identity required')
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
 identity=data.get('engine_identity',{})
 for name in ['game_run_original','renderer_original','canvas_get_context_original']:
  need(identity.get(name) is True,'mock or replacement rejected: '+name)
 need(data.get('phase_order')==['entry','adapter','renderer','scene'],'actual Native chain incomplete')
 need(data.get('renderer',{}).get('webgl_context') is True,'real WebGL renderer missing')
 need(data.get('scene',{}).get('active') is True and bool(data.get('scene',{}).get('name')),'active actual scene missing')
 need(data.get('passed') is True and not data.get('errors'),'actual startup failed')
 errors.extend(validate_business(data))
 picture=ref(report.get('screenshot',{}),'same execution screenshot')
 if picture:need(picture.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and picture.stat().st_size>5000,'actual screenshot required')
 if report.get('control_profile')=='native_loading_recovery_v1':
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
 elif report.get('control_profile')=='cocos3_systemjs_native_v1':
  from cocos3_native_renderer_contract import validate as validate_cocos3
  validate_cocos3(report,native,data,need,ref)
 elif report.get('control_profile') in ('native_startup_controls.v1','canvas_context_conflict_v1'):
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
  try:
   extension=project_qa.lookup(project,'validators',report.get('control_profile'))
   project_qa.invoke(extension,'validate',report,native,binding,project,data,need,ref)
  except (ValueError,KeyError,TypeError,OSError) as exc:
   need(False,'unknown or unreviewed Native renderer control profile: '+str(exc))
 return errors


def execute_registered(report, native, binding, project):
 """Only Skill-reviewed fixed Python runners; never execute report-supplied argv."""
 errors=[];project=Path(project).resolve();native=Path(native).resolve()
 import project_qa
 try:
  key=report['execution']['registered_runner'];policy=project_qa.lookup(project,'runners',key)
  if policy['project']!=str(project):raise ValueError('registered project mismatch')
  expected_profile=policy.get('control_profile','canvas_context_conflict_v1')
  if report.get('control_profile') not in (None,expected_profile):raise ValueError('control profile differs from trusted runner registration')
  if not policy.get('allow_legacy_missing_profile') and report.get('control_profile')!=expected_profile:raise ValueError('trusted runner control profile is required')
  scope=policy.get('runner_scope','project')
  allowed_root=Path(policy.get('allowed_root',project)).resolve()
  excluded_root=Path(policy['excluded_root']).resolve() if policy.get('excluded_root') else None
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
