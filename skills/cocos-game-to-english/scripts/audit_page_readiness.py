#!/usr/bin/env python3
"""LOAD-01 page dependency and cancel/reopen audit. Source-only is NOT runtime acceptance.
See references/page-readiness-and-cancel.md. Final run:
--project GAME --plan PLAN --runtime RUNS --binding REVIEW --out REPORT
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
TOOL='audit_page_readiness'
INDEPENDENT='independent_interaction_under_unrelated_load'
CASES={'cold','warm','slow_cancel_reopen','closed_completion','failure_retry','offline_warm','core_independence'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def scan(project):
 hits=[];files=list((project/'assets').rglob('*.js'))+list((project/'assets').rglob('*.ts'))
 for f in files:
  if any(x in {'node_modules','library','temp'}for x in f.parts):continue
  text=f.read_text(encoding='utf-8',errors='replace');rel=f.relative_to(project).as_posix()
  # These are risk patterns for review, not an exhaustive recognizer of all loaders.
  patterns=[('all_buttons_resource_barrier',r'\.on\([\'\"]click[\'\"][^\n]{0,450}\.with(?:Artwork|Assets)\(\s*(?:cb|callback|done)\s*\)'),
   ('batch_all_deferred_pages',r'pages\s*=\s*\[((?:\s*[\'\"][^\'\"]+[\'\"]\s*,?){3,})\]'),
   ('player_internal_file_count',r'(?:\.string\s*=|text\([^\n]{0,100})[^\n]{0,250}[\'\"]Preparing artwork: ')]
  for rule,pattern in patterns:
   for m in re.finditer(pattern,text):hits.append({'rule':rule,'path':rel,'line':text.count('\n',0,m.start())+1,'excerpt':m.group()[:240]})
 return hits,len(files)
def validate(plan,runtime,binding,base):
 errors=[];seen=set();refs=0
 routes=plan.get('routes',[]);views=plan.get('viewports',[])
 if not routes or len({x.get('id')for x in routes})!=len(routes):errors.append('plan requires nonempty unique route IDs')
 if len(views)<2 or len({tuple(v)for v in views})!=len(views):errors.append('two distinct actual mobile viewports required')
 if runtime.get('binding')!=binding:errors.append('runtime binding is stale or missing')
 if runtime.get('producer')!='real_browser_touch_trace':errors.append('runtime producer must be real_browser_touch_trace; doubles do not qualify')
 scope=plan.get('scope')
 if scope not in {'full_existing_game','affected_routes_maintenance'}:errors.append('explicit full or affected-route maintenance scope required')
 if not plan.get('inventory_evidence'):errors.append('actual route inventory evidence is required')
 for ref in plan.get('inventory_evidence',[])+runtime.get('raw_evidence',[]):
  try:
   p=(base/ref['path']).resolve();p.relative_to(base.resolve())
   if sha(p)!=ref['sha256']:raise ValueError('SHA mismatch')
   refs+=1
  except Exception as e:errors.append('evidence invalid: '+str(e))
 if not runtime.get('raw_evidence'):errors.append('raw action/network evidence is required')
 route_map={x.get('id'):x for x in routes}
 for c in runtime.get('cases',[]):
  key=(c.get('route'),tuple(c.get('viewport',[])),c.get('scenario'));seen.add(key)
  prefix=str(key)+': '
  if c.get('route')not in route_map:errors.append(prefix+'undeclared route');continue
  if c.get('scenario')not in CASES and c.get('scenario')!=INDEPENDENT:errors.append(prefix+'unknown scenario');continue
  if not c.get('trusted_touch') or not c.get('target_interaction_effect'):errors.append(prefix+'trusted touch and actual target interaction effect required')
  if c.get('script_errors'):errors.append(prefix+'script errors remain')
  if c.get('scenario')in {'warm','offline_warm'}:
   if c.get('route_download_bytes')!=0 or c.get('wait_overlay_ms')!=0:errors.append(prefix+'ready page still waits or downloads its dependencies')
  route_mode=route_map[c['route']].get('loading_mode')
  if route_mode not in {'local_independent','deferred_resource'}:errors.append(prefix+'route loading_mode must describe actual local independence or deferred resource task')
  if route_mode=='local_independent' and c.get('scenario') in {'cold','warm','offline_warm','slow_cancel_reopen','closed_completion','failure_retry',INDEPENDENT,'core_independence'}:
   if c.get('wait_overlay_ms')!=0:errors.append(prefix+'local route must remain interactive without a blocking wait overlay')
   if c.get('scenario')==INDEPENDENT:
    if not isinstance(c.get('observed_network_bytes'),int) or c['observed_network_bytes']<0:errors.append(prefix+'observed network bytes must be measured, including lazy asset loads')
    if c.get('interaction_completed_without_wait')is not True:errors.append(prefix+'route interaction must complete before waiting for its lazy assets')
    if not isinstance(c.get('observed_request_count'),int) or c['observed_request_count']<0:errors.append(prefix+'request count in the interaction window must be measured')
   elif c.get('route_download_bytes')!=0:errors.append(prefix+'this scenario requires no route-owned download bytes')
  if c.get('scenario')=='cold' and route_mode=='local_independent' and route_map[c['route']].get('kind')=='core' and c.get('wait_overlay_ms')!=0:errors.append(prefix+'core page blocked by lazy resource barrier')
  if c.get('scenario')in {'slow_cancel_reopen','closed_completion'}:
   if route_mode=='local_independent':
    required=['background_fault_pending','latest_navigation_only','no_duplicate_inflight_task','reopen_usable'] if c.get('scenario')=='slow_cancel_reopen' else ['background_task_completed','latest_navigation_only','reopen_usable']
    for field in required:
     if c.get(field)is not True:errors.append(prefix+field+' failed or missing')
   else:
    for field in ['resource_ready_retained','latest_navigation_only','no_duplicate_inflight_task','reopen_usable']:
     if c.get(field)is not True:errors.append(prefix+field+' failed or missing')
   if c.get('scenario')=='slow_cancel_reopen' and (not isinstance(c.get('cancel_count'),int)or c['cancel_count']<3):errors.append(prefix+'must cancel/reopen at least three times')
  if c.get('scenario')=='failure_retry':
   fields=['background_failure_observed','background_retry_new_request','background_recovered','target_unaffected'] if route_mode=='local_independent' else ['visible_failure','retry_new_request','recovered_usable','stale_result_ignored']
   for field in fields:
    if c.get(field)is not True:errors.append(prefix+field+' failed or missing')
  if c.get('scenario') in {INDEPENDENT,'core_independence'}:
   if c.get('unrelated_bundle_pending')is not True:errors.append(prefix+'unrelated bundle must actually remain pending')
   if route_mode=='local_independent' and c.get('unrelated_fault_mode')not in {'held_http','active_slow_http'}:errors.append(prefix+'local independence must be tested while a real unrelated HTTP task is held or progressing')
  if c.get('player_internal_file_count')is not False:errors.append(prefix+'internal file counters must not reach player UI')
  if not c.get('evidence_refs') or not all(isinstance(i,int)and 0<=i<len(runtime.get('raw_evidence',[]))for i in c['evidence_refs']):errors.append(prefix+'references to raw evidence required')
 for route in routes:
  if route.get('kind')not in {'core','deferred'}:errors.append(str(route.get('id'))+': kind must be core or deferred')
  if route.get('loading_mode')not in {'local_independent','deferred_resource'}:errors.append(str(route.get('id'))+': loading_mode must be explicit and based on the actual route dependency graph')
  if route.get('kind')=='deferred' and route.get('loading_mode')!='deferred_resource':errors.append(str(route.get('id'))+': deferred route must retain real deferred-resource loading checks')
  if route.get('kind')=='core' and route.get('loading_mode')!='local_independent':errors.append(str(route.get('id'))+': core route must prove local interaction remains independent of deferred tasks')
  if not route.get('reach_steps')or not isinstance(route.get('dependency_groups'),list):errors.append(str(route.get('id'))+': actual reach steps and dependency groups required')
  if route.get('kind')=='deferred' and not route.get('deferred_reason'):errors.append(str(route.get('id'))+': deferred download reason required')
  for v in views:
   required=CASES if route.get('loading_mode')=='deferred_resource' else {INDEPENDENT}
   for scenario in required:
    if (route.get('id'),tuple(v),scenario)not in seen:errors.append(str((route.get('id'),v,scenario))+': missing case')
 if len(seen)!=len(runtime.get('cases',[])):errors.append('duplicate case cannot fill missing coverage')
 return errors,len(seen),refs

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--source-only',action='store_true');p.add_argument('--plan',type=Path);p.add_argument('--runtime',type=Path);p.add_argument('--binding',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();errors=[]
 project=a.project.resolve()
 if not (project/'assets').is_dir():p.error('project must contain assets/')
 hits,files=scan(project);checked=files;binding=None
 if a.source_only:
  errors=[h['rule']+': '+h['path']+':'+str(h['line'])for h in hits]
 else:
  try:
   if not all([a.plan,a.runtime,a.binding]):raise ValueError('final acceptance needs --plan --runtime --binding; source scan cannot substitute')
   b=load(a.binding);binding=b.get('binding',b)
   if not all(binding.get(k)for k in ['source_sha256','native_tree_sha256','web_tree_sha256','build_tag']):raise ValueError('complete current build binding required')
   plan=load(a.plan);runtime=load(a.runtime);errors,n,_=validate(plan,runtime,binding,a.runtime.parent);checked+=n
   # Batch loading is always visible in the final risk list; actual route evidence must demonstrate impact was removed.
   if hits:errors+=['unresolved static risk '+h['rule']+': '+h['path']for h in hits]
  except (ValueError,OSError,KeyError,TypeError)as e:errors.append(str(e))
 report={'tool':TOOL,'stage':'source_only'if a.source_only else'runtime','binding':binding,'checked':checked,'failed':len(errors),'passed':not errors,'source_risks':hits,'errors':errors,'limits':'Pattern/coverage/hash checks only. Raw evidence and actual UI outcomes require Codex review; no physical device, SDK or subjective UX proof.'}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'tool':TOOL,'stage':report['stage'],'checked':checked,'failed':len(errors),'passed':not errors,'source_risks':hits[:5]},ensure_ascii=False));return bool(errors)
if __name__=='__main__':sys.exit(main())
