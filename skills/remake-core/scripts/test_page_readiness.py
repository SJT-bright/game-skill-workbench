#!/usr/bin/env python3
"""Validator self-tests only: synthetic traces are NOT game/runtime acceptance."""
import importlib.util,json,tempfile,hashlib,copy
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('readiness',HERE/'audit_page_readiness.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
def check(name,fn):
 try:fn();checks.append({'id':name,'passed':True})
 except Exception as e:checks.append({'id':name,'passed':False,'error':repr(e)})
with tempfile.TemporaryDirectory()as tmp:
 root=Path(tmp);(root/'assets').mkdir();(root/'raw.json').write_text('{"synthetic":true}');ref={'path':'raw.json','sha256':m.sha(root/'raw.json')};binding={k:'synthetic'for k in ['source_sha256','native_tree_sha256','web_tree_sha256','build_tag']}
 plan={'scope':'affected_routes_maintenance','inventory_evidence':[ref],'viewports':[[375,667],[390,844]],'routes':[{'id':'settings','kind':'core','loading_mode':'local_independent','reach_steps':'HOME > SETTINGS','dependency_groups':['core-ui']}]}
 runtime={'binding':binding,'producer':'real_browser_touch_trace','raw_evidence':[ref],'cases':[]}
 for v in plan['viewports']:
  for scenario in sorted(m.CASES|{m.INDEPENDENT}):runtime['cases'].append({'route':'settings','viewport':v,'scenario':scenario,'trusted_touch':True,'target_interaction_effect':'volume changed','script_errors':[],'route_download_bytes':0,'observed_network_bytes':24 if scenario==m.INDEPENDENT else None,'observed_request_count':2 if scenario==m.INDEPENDENT else None,'interaction_completed_without_wait':True if scenario==m.INDEPENDENT else None,'wait_overlay_ms':0,'resource_ready_retained':True,'latest_navigation_only':True,'no_duplicate_inflight_task':True,'reopen_usable':True,'cancel_count':3,'visible_failure':True,'retry_new_request':True,'recovered_usable':True,'stale_result_ignored':True,'background_fault_pending':True,'background_task_completed':True,'background_failure_observed':True,'background_retry_new_request':True,'background_recovered':True,'target_unaffected':True,'unrelated_bundle_pending':True,'unrelated_fault_mode':'held_http','player_internal_file_count':False,'evidence_refs':[0]})
 def assert_ok(r=runtime):assert not m.validate(plan,r,binding,root)[0]
 def reject(change):
  r=copy.deepcopy(runtime);change(r);assert m.validate(plan,r,binding,root)[0]
 check('valid-schema-normal-control-not-game-proof',assert_ok)
 check('missing-case-rejected',lambda:reject(lambda r:r['cases'].remove(next(x for x in r['cases']if x['route']=='settings' and x['viewport']==[375,667] and x['scenario']==m.INDEPENDENT))))
 check('duplicate-case-rejected',lambda:reject(lambda r:r['cases'].append(r['cases'][0])))
 check('old-binding-rejected',lambda:reject(lambda r:r.update(binding={})))
 def discarded_deferred_result():
  original=copy.deepcopy(plan);plan['routes'][0]['kind']='deferred';plan['routes'][0]['loading_mode']='deferred_resource';plan['routes'][0]['deferred_reason']='A real route-owned asset task is requested.'
  try:reject(lambda r:next(x for x in r['cases']if x['scenario']=='slow_cancel_reopen').update(resource_ready_retained=False))
  finally:plan.clear();plan.update(original)
 check('discarded-download-result-rejected',discarded_deferred_result)
 check('local-core-does-not-invent-route-retry',lambda:assert_ok())
 check('local-core-background-fault-must-be-observed',lambda:reject(lambda r:next(x for x in r['cases']if x['scenario']=='failure_retry').update(background_failure_observed=False)))
 def local_minimal_scope():
  r=copy.deepcopy(runtime);r['cases']=[x for x in r['cases']if x['scenario'] in {m.INDEPENDENT,'core_independence'}]
  assert not m.validate(plan,r,binding,root)[0]
 check('local-core-two-viewports-need-real-background-independence-only',local_minimal_scope)
 check('local-core-background-must-be-a-held-http-request',lambda:reject(lambda r:next(x for x in r['cases']if x['scenario']==m.INDEPENDENT).update(unrelated_fault_mode='none')))
 check('lazy-assets-allowed-when-interaction-finishes-without-wait',lambda:assert_ok())
 check('lazy-assets-do-not-excuse-blocked-interaction',lambda:reject(lambda r:next(x for x in r['cases']if x['scenario']==m.INDEPENDENT).update(interaction_completed_without_wait=False)))
 check('independent-route-must-measure-request-window',lambda:reject(lambda r:next(x for x in r['cases']if x['scenario']==m.INDEPENDENT).update(observed_request_count=None)))
 check('cached-page-redownload-rejected',lambda:reject(lambda r:next(x for x in r['cases']if x['scenario']=='warm').update(route_download_bytes=100)))
 check('fake-input-rejected',lambda:reject(lambda r:r['cases'][0].update(trusted_touch=False)))
 check('player-file-counter-rejected',lambda:reject(lambda r:r['cases'][0].update(player_internal_file_count=True)))
 check('no-actual-page-interaction-rejected',lambda:reject(lambda r:r['cases'][0].update(target_interaction_effect='')))
 check('raw-evidence-missing-rejected',lambda:reject(lambda r:r.update(raw_evidence=[])))
 def scanbad():
  f=root/'assets/App.js';f.write_text("n.on('click',function(){app.withArtwork(cb);}); pages=['Map','Game','Shop'];")
  hits,_=m.scan(root);assert {h['rule']for h in hits}=={'all_buttons_resource_barrier','batch_all_deferred_pages'}
 check('known-bad-shared-barrier-and-batch-detected',scanbad)
 def scantxt():
  (root/'assets/App.js').write_text("label.string='Preparing artwork: '+done+' / '+total;");assert m.scan(root)[0]
 check('internal-preparation-counter-detected',scantxt)
 spec2=importlib.util.spec_from_file_location('gate',HERE/'check_known_issues.py');g=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(g)
 def stagegate():
  report={'tool':'audit_page_readiness','stage':'source_only','binding':binding,'checked':1,'failed':0,'passed':True};path=root/'static.json';path.write_text(json.dumps(report));row={'auto_reports':[{'path':'static.json','sha256':g.sha(path.read_bytes())}]};errors=[];g.auto_reports({'id':'LOAD-01','auto_check':['audit_page_readiness']},row,root,errors,binding,'localize');assert errors
  report['stage']='runtime';path.write_text(json.dumps(report));row['auto_reports'][0]['sha256']=g.sha(path.read_bytes());errors=[];g.auto_reports({'id':'LOAD-01','auto_check':['audit_page_readiness']},row,root,errors,binding,'localize');assert not errors
 check('actual-checker-rejects-source-only-final-report',stagegate)
 def deferred_retry():
  original=copy.deepcopy(plan);plan['routes'][0]['kind']='deferred';plan['routes'][0]['loading_mode']='deferred_resource';plan['routes'][0]['deferred_reason']='Battle bundle and scene are first requested after Fight.'
  try:
   r=copy.deepcopy(runtime)
   for c in r['cases']:
    for k in ['background_failure_observed','background_retry_new_request','background_recovered','target_unaffected','retry_new_request']:c.pop(k,None)
   assert m.validate(plan,r,binding,root)[0]
  finally:plan.clear();plan.update(original)
 check('deferred-battle-still-requires-real-retry-chain',deferred_retry)
result={'scope':'Synthetic validator conformance selftest, never game acceptance','passed':sum(x['passed']for x in checks),'failed':sum(not x['passed']for x in checks),'checks':checks};print(json.dumps(result,indent=2));raise SystemExit(bool(result['failed']))
