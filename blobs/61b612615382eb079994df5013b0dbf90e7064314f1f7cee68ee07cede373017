"""Evidence-bearing preservation mode. Absence of an explicit record keeps template rules."""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ADS = {'completed_once','cancel_no_reward','duplicate_callback_once','late_callback_ignored','timeout_no_reward','leave_reopen','storage_failure_no_reward','readback_ambiguity','reload_durable','ledger_balanced'}
CHECKIN = {'date_boundary','same_day_duplicate','day7_reward','clock_rollback','save_failure','readback_ambiguity','restart'}
ECONOMY = {'collection_inventory','purchase_cost','insufficient_cost','merge','equip','effect','persistence','duplicate_claim','prices_preserved'}
TRIAL = {'ad_completed','ad_cancelled','only_current_round','permanent_unlock_unchanged','effect_applied','restart_restore'}
MODULES = {'button_inventory_complete','economy_preserved','original_mechanics_preserved'}
BINDING_KEYS = ('source_sha256','web_tree_sha256','native_tree_sha256','build_tag')
SCENE_EXTS = {'.fire','.scene'}
SKIP = {'library','temp','build','node_modules','.git'}
ROUTE_PATTERN = {'map':re.compile(r'(^|[/_ -])(map|worldmap|levelmap|chaptermap)([/_ .-]|$)|地图',re.I),
                 'stage_details':re.compile(r'stage[_ -]?details?|level[_ -]?details?|关卡详情',re.I)}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def resolve(ref, base):
 p=Path(ref.get('path',''));return p.resolve() if p.is_absolute() else (Path(base)/p).resolve()
def checked_ref(ref,base):
 if not isinstance(ref,dict):raise ValueError('evidence reference must be object')
 p=resolve(ref,base)
 if not p.is_file() or sha(p)!=ref.get('sha256'):raise ValueError('missing/changed evidence '+str(p))
 return p

def gui_refs(refs,base,binding,route=None):
 """Current GUI wrapper retains original raw traces; operator must review effects."""
 if not isinstance(refs,list) or not refs:raise ValueError('current GUI evidence required')
 ratios=[]
 for ref in refs:
  p=checked_ref(ref,base);j=read(p)
  if j.get('execution_binding')!=binding or j.get('trusted_touch') is not True or not str(j.get('interaction_effect','')).strip():raise ValueError('GUI execution binding/trusted interaction required')
  if route and j.get('route')!=route:raise ValueError('GUI route mismatch '+route)
  v=j.get('viewport');raw=j.get('raw_evidence')
  if not isinstance(v,list) or len(v)!=2 or not all(type(n) is int and n>0 for n in v):raise ValueError('GUI mobile viewport required')
  if not isinstance(raw,list) or not raw:raise ValueError('GUI raw traces required')
  trusted_raw=False
  def has_trusted(value):
   if isinstance(value,dict):return value.get('trusted') is True or value.get('trusted_touch') is True or any(has_trusted(x) for x in value.values())
   return isinstance(value,list) and any(has_trusted(x) for x in value)
  for x in raw:
   q=checked_ref(x,p.parent)
   if q.suffix.lower()=='.json':trusted_raw=trusted_raw or has_trusted(read(q))
  if not trusted_raw:raise ValueError('GUI original JSON must retain trusted touch observations; wrapper alone is insufficient')
  ratios.append(round(v[0]/v[1],3))
 if len(set(ratios))<2:raise ValueError('two different mobile ratios required')

def route_candidates(scene,project):
 out=[]
 def add(pointer,value,kind):
  for route,pattern in ROUTE_PATTERN.items():
   if pattern.search(value) or (route=='map' and re.search(r'(?:open|show|enter|goto|load|reopen)(?:world|level|chapter)?map(?:$|[_A-Z])',value,re.I)):
    out.append({'route':route,'scene':str(scene.relative_to(project)),'pointer':pointer,'value':value,'kind':kind})
 add('',str(scene.relative_to(project)),'scene_path')
 def walk(value,pointer=''):
  if isinstance(value,list):
   for i,x in enumerate(value):walk(x,pointer+'/'+str(i))
  elif isinstance(value,dict):
   if value.get('__type__')=='cc.Node' and isinstance(value.get('_name'),str):add(pointer+'/_name',value['_name'],'node_name')
   if value.get('__type__') in ('cc.ClickEvent','cc.Component.EventHandler') and isinstance(value.get('handler'),str):add(pointer+'/handler',value['handler'],'click_handler')
   for k,x in value.items():
    if isinstance(x,(dict,list)):walk(x,pointer+'/'+str(k))
 walk(read(scene));return out

def source_inventory(ref,base,project,binding,require_reward=False):
 p=checked_ref(ref,base);j=read(p);project=Path(project).resolve()
 from audit_mobile_input import snapshot
 if snapshot(project)[2]!=binding.get('source_sha256'):raise ValueError('production source tree differs from binding')
 if j.get('schema')!='maintenance_source_inventory.v1' or j.get('binding')!=binding:raise ValueError('current source inventory schema/binding')
 refs=j.get('source_files',[])
 if not refs:raise ValueError('source inventory empty')
 for x in refs:
  q=checked_ref(x,p.parent)
  if not q.is_relative_to(project/'assets'):raise ValueError('source evidence outside production assets')
 if require_reward or j.get('reward_api'):
  api=j.get('reward_api')
  if not isinstance(api,str) or not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+',api):raise ValueError('actual qualified rewarded API required')
  pattern=re.compile(r'(?<![\w$])'+re.escape(api)+r'\s*\(')
  discovered=[]
  for q in sorted((project/'assets').rglob('*')):
   if not q.is_file() or q.suffix not in ('.js','.ts'):continue

   if set(q.relative_to(project).parts)&SKIP:continue
   text=q.read_text(encoding='utf-8-sig')
   for m in pattern.finditer(text):discovered.append((str(q.resolve()),text.count('\n',0,m.start())+1))
  declared_calls=j.get('reward_callsites',[])
  mapped=[]
  for call in declared_calls:
   q=checked_ref(call,p.parent)
   if not call.get('reward_entry_id') or type(call.get('line')) is not int:raise ValueError('callsite must map to fixed reward entry ID')
   mapped.append((str(q),call['line']))
  if not discovered or sorted(discovered)!=sorted(mapped):raise ValueError('reward callsite inventory incomplete/changed')
 scenes=sorted(q.resolve() for q in (project/'assets').rglob('*') if q.is_file() and q.suffix.lower() in SCENE_EXTS and not set(q.relative_to(project).parts)&SKIP)
 declared=sorted(checked_ref(x,p.parent) for x in j.get('scene_files',[]))
 if not scenes or scenes!=declared:raise ValueError('source scene inventory not exhaustive/current')
 ui_path=checked_ref(j.get('ui_route_inventory'),p.parent);ui=read(ui_path)
 if ui.get('binding')!=binding or not isinstance(ui.get('routes'),list) or not ui.get('raw_evidence'):raise ValueError('current actual UI route inventory required')
 for x in ui['raw_evidence']:checked_ref(x,ui_path.parent)
 if any(not isinstance(x,dict) or x.get('role') not in ('home','map','stage_details','other') or not x.get('id') for x in ui['routes']):raise ValueError('UI route inventory roles/IDs required')
 candidates=[x for q in scenes for x in route_candidates(q,project)]
 routes=j.get('routes',{})
 for name in ('home','map','stage_details'):
  r=routes.get(name,{})
  if type(r.get('present')) is not bool or (name=='home' and not r['present']):raise ValueError('route presence required '+name)
  if r['present']:
   if not r.get('scene_files'):raise ValueError('present route has no scene mapping '+name)
   for x in r['scene_files']:
    if checked_ref(x,p.parent) not in scenes:raise ValueError('route mapped outside current scenes')
  else:
   if any(x.get('role')==name for x in ui['routes']):raise ValueError('absent route exists in actual UI inventory '+name)
   for candidate in [x for x in candidates if x['route']==name]:
    matches=[x for x in j.get('route_candidate_explanations',[]) if x.get('candidate')==candidate]
    if len(matches)!=1:raise ValueError('absent route found in actual scene scan; unexplained candidate '+str(candidate))
    explanation=matches[0]
    if explanation.get('classification') not in ('decorative','not_navigation') or not str(explanation.get('reason','')).strip() or not explanation.get('source_evidence'):raise ValueError('route candidate explanation incomplete')
    if candidate['kind']=='click_handler' and explanation['classification']=='decorative':raise ValueError('click handler is not decorative')
    source_paths=[checked_ref(x,p.parent) for x in explanation['source_evidence']]
    if candidate['kind']=='click_handler' and not any(q.suffix in ('.js','.ts') and candidate['value'] in q.read_text(encoding='utf-8-sig') for q in source_paths):raise ValueError('click handler explanation needs actual JS implementation')
    gui_refs(explanation.get('gui_evidence'),p.parent,binding,name)
    for x in explanation['gui_evidence']:
     g=read(checked_ref(x,p.parent))
     if g.get('target_candidate')!=candidate or (candidate['kind']=='click_handler' and 'candidate_activate' not in g.get('actions',[])):raise ValueError('candidate-specific actual GUI activation/inspection required')
  if not str(r.get('source_reason','')).strip():raise ValueError('source route rationale required '+name)
  gui_refs(r.get('gui_evidence'),p.parent,binding,name)
  for x in r['gui_evidence']:
   wrapper=read(checked_ref(x,p.parent));actions=wrapper.get('actions',[])
   valid_actions=('reopen' in actions and bool({'retry','recovery'}&set(actions))) if r['present'] else 'navigation_inventory' in actions
   if wrapper.get('route_present') is not r['present'] or not valid_actions:raise ValueError('route GUI reopen/recovery or absence inspection missing '+name)
 return j

def runtime_trace(ref,base,binding,project,features):
 p=checked_ref(ref,base);t=read(p)
 if t.get('schema')!='maintenance_runtime_trace.v1' or t.get('binding')!=binding:raise ValueError('runtime trace schema/binding')
 ex=t.get('execution',{});runner=Path(ex.get('runner',''));cmd=ex.get('command')
 if not runner.is_file() or sha(runner)!=ex.get('runner_sha256') or not isinstance(cmd,list) or not all(isinstance(x,str) for x in cmd) or str(runner) not in cmd:raise ValueError('runtime runner/command identity')
 for x in ex.get('dependencies',[]):checked_ref(x,p.parent)
 raw=checked_ref(t.get('raw_report'),p.parent);j=read(raw)
 if j.get('schema')!='maintenance_runtime.v1' or j.get('binding')!=binding:raise ValueError('runtime result schema/binding')
 required={'ads.'+k for k in ADS}|{'modules.'+k for k in MODULES}
 if 'daily_checkin' in features:required|={'checkin.'+k for k in CHECKIN}
 if 'collection' in features:required|={'economy.'+k for k in ECONOMY}
 if 'hero_trial' in features:required|={'trial.'+k for k in TRIAL}
 from check_known_issues import tree_sha
 roots=t.get('artifact_roots',{})
 if Path(roots.get('source','')).resolve()!=Path(project).resolve():raise ValueError('source root differs')
 for context in ('web','native'):
  if tree_sha(Path(roots.get(context,'')))!=binding[context+'_tree_sha256']:raise ValueError('final '+context+' tree differs')
 artifacts=[]
 for context in ('source','web','native'):
  row=j.get('contexts',{}).get(context,{})
  if not isinstance(row.get('artifacts'),list) or not row['artifacts']:raise ValueError('actual production artifacts required '+context)
  if not any(str(x.get('path','')).endswith('.js') or (context=='source' and str(x.get('path','')).endswith('.ts')) for x in row['artifacts']):raise ValueError('production executable source/JS artifact required '+context)
  for x in row['artifacts']:
   q=checked_ref(x,raw.parent);artifacts.append(q)
   if not q.is_relative_to(Path(roots[context]).resolve()):raise ValueError('artifact outside declared '+context+' tree')
   if context=='source' and not q.is_relative_to(Path(project).resolve()/'assets'):raise ValueError('source artifact outside production assets')
  if any(row.get('cases',{}).get(k)!='pass' for k in required):raise ValueError('missing/failed production runtime cases '+context)
 if not j.get('raw_evidence'):raise ValueError('runtime original observations required')
 for x in j['raw_evidence']:checked_ref(x,raw.parent)
 # Explicit roots are inputs, never an opaque runner that can silently select another export.
 inputs=[Path(x).resolve() for x in cmd if Path(x).exists() and x!=str(runner)]
 if any(not any(q==x or (x.is_dir() and q.is_relative_to(x)) for x in inputs) for q in artifacts):raise ValueError('production artifacts not explicit runner inputs')
 proc=subprocess.run(cmd,capture_output=True,text=True,timeout=180,check=False)
 try:actual=json.loads(proc.stdout)
 except ValueError:raise ValueError('production runner did not emit JSON')
 if proc.returncode or actual!=j:raise ValueError('production runner replay differs/failed')
 return j

def collection_catalog(ref,base,binding):
 p=checked_ref(ref,base);j=read(p)
 if j.get('schema')!='maintenance_collection_catalog.v1' or j.get('binding')!=binding:raise ValueError('current collection catalog required')
 for side in ('original','current'):
  row=j.get(side,{})
  if not row.get('artifacts') or not row.get('groups') or not row.get('prices'):raise ValueError('actual original/current collection and prices required')
  for x in row['artifacts']:checked_ref(x,p.parent)
  for group in row['groups']:
   if not group.get('id') or not isinstance(group.get('items'),list) or not group['items'] or len(set(group['items']))!=len(group['items']):raise ValueError('collection item IDs required')
  if any(not x.get('id') or type(x.get('value')) not in (int,float) or not math.isfinite(x['value']) or x['value']<0 for x in row['prices']):raise ValueError('real sampled prices required')
 if j['original']['groups']!=j['current']['groups'] or j['original']['prices']!=j['current']['prices']:raise ValueError('preserved collection/prices changed; separate explicit economy authorization required')
 return j

def load_scope(path,project,binding):
 p=Path(path).resolve();s=read(p)
 if s.get('schema')!='maintenance_scope.v1' or s.get('mode')!='preserve_existing_gameplay' or s.get('new_modules_requested') is not False:raise ValueError('explicit preservation scope required; new module requests use template branch')
 if not isinstance(binding,dict) or any(not binding.get(k) for k in BINDING_KEYS) or s.get('binding')!=binding:raise ValueError('scope current binding required')
 if Path(s.get('project','')).resolve()!=Path(project).resolve():raise ValueError('scope project mismatch')
 auth=s.get('authorization',{});a=checked_ref(auth,p.parent)
 if not auth.get('excerpt') or auth['excerpt'] not in a.read_text(encoding='utf-8'):raise ValueError('scope authorization excerpt not in original record')
 if not s.get('original_sources'):raise ValueError('original source provenance required')
 for x in s['original_sources']:checked_ref(x,p.parent)
 features=s.get('existing_features')
 if not isinstance(features,list) or not all(isinstance(x,str) for x in features):raise ValueError('original feature inventory required')
 decision=s.get('module_decision',{})
 if not str((decision.get('currency') or {}).get('name','')).strip() or not isinstance(decision.get('button_audit'),list) or not decision['button_audit']:raise ValueError('original currency and button audit required')
 from feature_policy import removed
 for row in decision['button_audit']:
  if not isinstance(row,dict) or not all(str(row.get(k,'')).strip() for k in ('page','button','why')) or type(row.get('works')) is not bool or type(row.get('keep')) is not bool:raise ValueError('incomplete original button audit row')
  if row['keep'] and (not row['works'] or removed(row['button']+' '+row['why'],{'league':False,'checkin':'daily_checkin' in features})):raise ValueError('nonfunctional/prohibited original button retained')
 inventory=source_inventory(s.get('source_inventory'),p.parent,project,binding,require_reward=True)
 if any('trial' in str(x.get('reward_entry_id','')).lower() for x in inventory.get('reward_callsites',[])) and 'hero_trial' not in features:raise ValueError('actual trial reward entry requires trial runtime cases')
 if 'collection' in features:collection_catalog(s.get('economy_catalog'),p.parent,binding)
 gui_refs(s.get('gui_evidence'),p.parent,binding)
 runtime_trace(s.get('runtime_trace'),p.parent,binding,project,features)
 return s

def audit_scope(path,project,binding):
 try:return load_scope(path,project,binding),[]
 except (ValueError,OSError,KeyError,TypeError,AttributeError,subprocess.TimeoutExpired) as e:return None,[str(e)]

def scope_path(project,explicit=None):
 p=Path(explicit) if explicit else Path(project)/'docs/maintenance-scope.json'
 return p if explicit or p.is_file() else None


def required_map(project):
 """A source-preserved game only omits a new map after full current scope validation."""
 if project is None:return True
 path=scope_path(project)
 if path is None:return True
 try:
  scope=load_scope(path,project,read(path).get('binding'))
  inventory=source_inventory(scope['source_inventory'],path.parent,project,scope['binding'])
  return inventory['routes']['map']['present']
 except (ValueError,OSError,KeyError,TypeError,AttributeError,subprocess.TimeoutExpired):return True
