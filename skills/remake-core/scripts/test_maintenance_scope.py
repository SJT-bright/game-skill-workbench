#!/usr/bin/env python3
"""Gate calibration in temporary toy projects; never game acceptance evidence."""
import copy,json,subprocess,sys,tempfile
from pathlib import Path
from maintenance_scope import sha, ADS, CHECKIN, MODULES, ECONOMY, TRIAL, audit_scope, source_inventory, route_candidates
from audit_mobile_input import snapshot
from check_known_issues import tree_sha
from audit_game_modules import audit, REFERENCE
from audit_native_storage_contract import CASES, validate, replay

def run():
 with tempfile.TemporaryDirectory(prefix='maintenance-gate-') as tmp:
  d=Path(tmp);proj=d/'project';(proj/'assets').mkdir(parents=True);(proj/'docs').mkdir()
  main=proj/('assets/main.ts' if '--typescript' in sys.argv else 'assets/main.js');main.write_text('const BO={playVideo:()=>1}; BO.playVideo(); exports.claim=x=>x+1;\n')
  scene=proj/'assets/main.fire';scene.write_text('{}')
  web=d/'web';native=d/'native';web.mkdir();native.mkdir()
  for x in (web,native):(x/'main.js').write_bytes(main.read_bytes())
  binding={'source_sha256':snapshot(proj)[2],'web_tree_sha256':tree_sha(web),'native_tree_sha256':tree_sha(native),'build_tag':'isolated-calibration'}
  def ref(p):return {'path':str(p),'sha256':sha(p)}
  def write(name,obj):p=d/name;p.write_text(json.dumps(obj));return p
  original=d/'original.js';original.write_bytes(main.read_bytes());auth=d/'authorization.txt';auth.write_text('Preserve existing gameplay; repair and test only.')
  rawgui=write('real-format-touch.json',{'events':[{'trusted':True,'effect':'changed'}]})
  def guis(route,present=True):
   return [ref(write(route+'-'+str(v[0])+'.json',{'execution_binding':binding,'route':route,'viewport':v,'route_present':present,'actions':['reopen','retry'] if present else ['navigation_inventory'],'trusted_touch':True,'interaction_effect':'isolated gate calibration effect','raw_evidence':[ref(rawgui)]})) for v in ([393,852],[375,667])]
  inventory={'schema':'maintenance_source_inventory.v1','binding':binding,'source_files':[ref(main)],'scene_files':[ref(scene)],'reward_api':'BO.playVideo','reward_callsites':[{**ref(main),'line':1,'reward_entry_id':'fixture-reward'}], 'routes':{n:{'present':n=='home','source_reason':'isolated scene inventory calibration','gui_evidence':guis(n,n=='home'),**({'scene_files':[ref(scene)]} if n=='home' else {})} for n in ('home','map','stage_details')}}
  uip=write('ui-inventory.json',{'binding':binding,'routes':[{'id':'home','role':'home'},{'id':'settings','role':'other'}],'raw_evidence':[ref(rawgui)]});inventory['ui_route_inventory']=ref(uip)
  ip=write('inventory.json',inventory)
  cases={**{'ads.'+k:'pass' for k in ADS},**{'checkin.'+k:'pass' for k in CHECKIN},**{'modules.'+k:'pass' for k in MODULES},**{'economy.'+k:'pass' for k in ECONOMY},**{'trial.'+k:'pass' for k in TRIAL}}
  result={'schema':'maintenance_runtime.v1','binding':binding,'contexts':{n:{'artifacts':[ref(q)],'cases':cases.copy()} for n,q in [('source',main),('web',web/'main.js'),('native',native/'main.js')]},'raw_evidence':[ref(rawgui)]}
  runner=d/'runtime.py';runner.write_text('import json,subprocess,sys\nfor root in sys.argv[1:4]:\n p=root+"/assets/' + main.name + '" if root.endswith("project") else root+"/main.js"\n subprocess.run(["node","-e","if(require(process.argv[1]).claim(1)!==2)process.exit(1)",p],check=True)\nprint('+repr(json.dumps(result))+')\n')
  raw=write('runtime.json',result);trace={'schema':'maintenance_runtime_trace.v1','binding':binding,'artifact_roots':{'source':str(proj),'web':str(web),'native':str(native)},'execution':{'runner':str(runner),'runner_sha256':sha(runner),'command':[sys.executable,str(runner),str(proj),str(web),str(native)],'dependencies':[]},'raw_report':ref(raw)};tp=write('runtime-trace.json',trace)
  scope={'schema':'maintenance_scope.v1','mode':'preserve_existing_gameplay','new_modules_requested':False,'project':str(proj),'binding':binding,'authorization':{**ref(auth),'excerpt':auth.read_text()},'original_sources':[ref(original)],'existing_features':['daily_checkin','collection','hero_trial'],'source_inventory':ref(ip),'gui_evidence':guis('all'),'runtime_trace':ref(tp),'module_decision':{'currency':{'name':'Coins'},'button_audit':[{'page':'home','button':'Fight','works':True,'keep':True,'why':'working original combat'}]}};catalog={'schema':'maintenance_collection_catalog.v1','binding':binding,'original':{'artifacts':[ref(original)],'groups':[{'id':'toy-items','items':['one','two']}],'prices':[{'id':'one','value':100},{'id':'two','value':200}]},'current':{'artifacts':[ref(main)],'groups':[{'id':'toy-items','items':['one','two']}],'prices':[{'id':'one','value':100},{'id':'two','value':200}]}};cp=write('catalog.json',catalog);scope['economy_catalog']=ref(cp);sp=write('scope.json',scope)
  assert not audit_scope(sp,proj,binding)[1]
  checks,_=audit(proj,'localize',REFERENCE,sp,binding);assert all(x['passed'] for x in checks)
  assert any(not x['passed'] for x in audit(proj,'localize',REFERENCE)[0]) # no scope keeps template/default refusal
  passed=['valid_runtime_replayed','existing_js_modules','missing_scope_template_refusal']
  def reject(label,edit):
   bad=copy.deepcopy(scope);edit(bad);bp=write('bad-scope.json',bad);assert audit_scope(bp,proj,binding)[1],label;passed.append(label)
  reject('stale_binding',lambda s:s['binding'].update(build_tag='old'))
  reject('new_modules_requested',lambda s:s.update(new_modules_requested=True))
  reject('missing_authorization',lambda s:s['authorization'].update(excerpt='not in record'))
  reject('missing_gui',lambda s:s.update(gui_evidence=[]))
  reject('changed_inventory_sha',lambda s:s['source_inventory'].update(sha256='bad'))
  changed=copy.deepcopy(result);changed['contexts']['native']['cases']['checkin.clock_rollback']='fail';raw.write_text(json.dumps(changed));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert audit_scope(sp,proj,binding)[1];passed.append('real_case_failure_refused')
  del changed['contexts']['native']['cases']['checkin.clock_rollback'];raw.write_text(json.dumps(changed));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert audit_scope(sp,proj,binding)[1];passed.append('missing_case_refused')
  changed=copy.deepcopy(result);changed['extra']='forged';raw.write_text(json.dumps(changed));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert audit_scope(sp,proj,binding)[1];passed.append('forged_raw_replay_refused')
  raw.write_text(json.dumps(result));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert not audit_scope(sp,proj,binding)[1]
  bindingp=write('binding.json',{'binding':binding});acqreport=d/'acquisition-report.json'
  proc=subprocess.run([sys.executable,str(Path(__file__).with_name('audit_acquisition_progression.py')),'--project',str(proj),'--maintenance-scope',str(sp),'--binding',str(bindingp),'--report',str(acqreport)],capture_output=True,text=True)
  assert proc.returncode==0,(proc.stdout,proc.stderr);assert json.loads(acqreport.read_text())['checked']==2;passed.append('actual_collection_maintenance_branch')
  # The CLI maintenance branches must accept a preserved JavaScript check-in without asking for new TS templates.
  (proj/'docs/features.json').write_text(json.dumps({'schema':'optional_features.v1','asked':'preserve existing check-in','skin_bonus':False,'daily_checkin':True}))
  module_report=d/'module-maintenance.json'
  proc=subprocess.run([sys.executable,str(Path(__file__).with_name('audit_game_modules.py')),'--project',str(proj),
                       '--board','localize','--maintenance-scope',str(sp),'--binding',str(bindingp),'--out',str(module_report)],capture_output=True,text=True)
  assert proc.returncode==0,(proc.stdout,proc.stderr)
  mod=json.loads(module_report.read_text());assert mod['passed'] and mod['implementation']=='production_js'
  assert not (proj/'docs/modules.json').exists() and not (proj/'assets/DailyCheckin.ts').exists()
  passed.append('game_modules_cli_preserves_production_js_without_new_module_templates')
  feature_report=d/'optional-maintenance.json'
  proc=subprocess.run([sys.executable,str(Path(__file__).with_name('audit_optional_features.py')),'--project',str(proj),
                       '--maintenance-scope',str(sp),'--binding',str(bindingp),'--out',str(feature_report)],capture_output=True,text=True)
  assert proc.returncode==0,(proc.stdout,proc.stderr)
  optional=json.loads(feature_report.read_text());assert optional['passed'] and optional['implementation']=='production_js'
  assert not (proj/'assets/DailyCheckin.ts').exists() and not (proj/'assets/checkin-config.json').exists()
  passed.append('checkin_cli_accepts_verified_existing_js_without_skill_ts_template')
  catalog['current']['prices'][0]['value']=101;cp.write_text(json.dumps(catalog));scope['economy_catalog']=ref(cp);sp.write_text(json.dumps(scope));assert audit_scope(sp,proj,binding)[1];passed.append('changed_original_prices_refused')
  catalog['current']['prices'][0]['value']=100;cp.write_text(json.dumps(catalog));scope['economy_catalog']=ref(cp);sp.write_text(json.dumps(scope))
  changed=copy.deepcopy(result);del changed['contexts']['web']['cases']['trial.only_current_round'];raw.write_text(json.dumps(changed));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert audit_scope(sp,proj,binding)[1];passed.append('existing_trial_unverified_refused')
  raw.write_text(json.dumps(result));trace['raw_report']=ref(raw);tp.write_text(json.dumps(trace));scope['runtime_trace']=ref(tp);sp.write_text(json.dumps(scope));assert not audit_scope(sp,proj,binding)[1]
  scope['module_decision']['button_audit'][0].update(button='Share');sp.write_text(json.dumps(scope));assert any(not x['passed'] for x in audit(proj,'localize',REFERENCE,sp,binding)[0]);passed.append('sharing_still_refused')
  # Actual toy loader defect, executed with the exact same runner for both inputs.
  fixed=native/'storage.js';fixed.write_text("exports.read=x=>x == null || x === '' ? {} : JSON.parse(x);\n")
  faulty=d/'fixture.js';faulty.write_text("exports.read=x=>x == null ? {} : JSON.parse(x);\n")
  provenance=d/'fixture-provenance.txt';provenance.write_text('Controlled toy loader fixture: removal of the empty-string missing-key branch, not a historical release.')
  store=d/'storage-runner.py';store.write_text('import sys,json,hashlib,subprocess\nh=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()\nc={k:"pass" for k in '+repr(CASES)+'}\nc["reopen_map"]=c["reopen_stage_details"]="not_applicable"\np=subprocess.run(["node","-e","require(process.argv[1]).read(String())",sys.argv[1]],capture_output=True)\nc["missing_empty_string"]="pass" if p.returncode==0 else "fail"\nprint(json.dumps({"runner_sha256":h(__file__),"bundle_sha256":h(sys.argv[1]),"adapter_sha256":h(sys.argv[2]),"cases":c}))\n')
  def store_record(bundle,name):
   r=d/(name+'.json');r.write_text(subprocess.check_output([sys.executable,str(store),str(bundle),str(fixed)]).decode());return {'bundle':str(bundle),'bundle_sha256':sha(bundle),'adapter':str(fixed),'adapter_sha256':sha(fixed),'raw_report':str(r),'raw_sha256':sha(r)}
  # Source binding remains unchanged; Native bytes update is explicitly rebound for storage calibration.
  sb=copy.deepcopy(binding);sb['native_tree_sha256']=tree_sha(native);si=copy.deepcopy(inventory);si['binding']=sb
  for r in si['routes'].values():
   for refg in r['gui_evidence']:
    gp=Path(refg['path']);g=json.loads(gp.read_text());g['execution_binding']=sb;gp.write_text(json.dumps(g));refg['sha256']=sha(gp)
  ui=json.loads(uip.read_text());ui['binding']=sb;uip.write_text(json.dumps(ui));si['ui_route_inventory']=ref(uip)
  sip=write('storage-inventory.json',si)
  st={'schema':'native_storage_trace.v2','binding':sb,'project':str(proj),'trace_base':str(d),'route_inventory':ref(sip),'execution':{'runner':str(store),'runner_sha256':sha(store),'command':[sys.executable,str(store),'{bundle}','{adapter}']},'current':store_record(fixed,'current'),'negative_control':{**store_record(faulty,'negative'),'kind':'controlled_legacy_fixture','base_bundle':ref(fixed),'patch':{'before':fixed.read_text().strip(),'after':faulty.read_text().strip()},'mechanism':'empty string reaches JSON.parse rather than missing-key branch','provenance':ref(provenance)}}
  assert not validate(st,native,sb),validate(st,native,sb);assert not replay(st);passed.append('storage_verified_absent_routes_and_exact_defect_replay')
  bad=copy.deepcopy(st);bad['negative_control']['patch']['after']='unrelated crash';assert validate(bad,native,sb);passed.append('unrelated_fixture_refused')
  forged=json.loads(Path(st['current']['raw_report']).read_text());forged['cases']['reopen_map']='pass';Path(st['current']['raw_report']).write_text(json.dumps(forged));st['current']['raw_sha256']=sha(st['current']['raw_report']);assert validate(st,native,sb) and replay(st);passed.append('absent_route_silent_pass_and_forged_raw_refused')
  scene2=proj/'assets/map.fire';scene2.write_text('{}');si['binding']['source_sha256']=snapshot(proj)[2];si['scene_files'].append(ref(scene2));
  for r in si['routes'].values():
   for refg in r['gui_evidence']:
    gp=Path(refg['path']);g=json.loads(gp.read_text());g['execution_binding']=si['binding'];gp.write_text(json.dumps(g));refg['sha256']=sha(gp)
  ui['binding']=si['binding'];uip.write_text(json.dumps(ui));si['ui_route_inventory']=ref(uip)
  sip.write_text(json.dumps(si));
  try:source_inventory(ref(sip),d,proj,si['binding']);raise AssertionError('existing map accepted as absent')
  except ValueError as exc:
   assert 'absent route found' in str(exc),str(exc)
   passed.append('actual_map_scene_cannot_be_absent')
  scene2.unlink()
  def refresh(content):
   scene.write_text(content);si['binding']['source_sha256']=snapshot(proj)[2];si['scene_files']=[ref(scene)];si['routes']['home']['scene_files']=[ref(scene)]
   for r in si['routes'].values():
    for refg in r['gui_evidence']:
     gp=Path(refg['path']);g=json.loads(gp.read_text());g['execution_binding']=si['binding'];gp.write_text(json.dumps(g));refg['sha256']=sha(gp)
   ui['binding']=si['binding'];uip.write_text(json.dumps(ui));si['ui_route_inventory']=ref(uip);sip.write_text(json.dumps(si))
  for content,label in [('[{"__type__":"cc.Node","_name":"panel-map"}]','nested_map_panel_refused'),('[{"__type__":"cc.ClickEvent","handler":"openMap"}]','nested_map_handler_refused'),('[{"__type__":"cc.Node","_name":"btn-level-details"}]','nested_stage_details_refused')]:
   refresh(content)
   try:source_inventory(ref(sip),d,proj,si['binding']);raise AssertionError(label)
   except ValueError as exc:
    assert 'unexplained candidate' in str(exc),str(exc)
    passed.append(label)
  refresh('[{"__type__":"cc.Node","_name":"map-art"}]')
  candidate=route_candidates(scene,proj)[0]
  for refg in si['routes']['map']['gui_evidence']:
   gp=Path(refg['path']);g=json.loads(gp.read_text());g['target_candidate']=candidate;gp.write_text(json.dumps(g));refg['sha256']=sha(gp)
  si['route_candidate_explanations']=[{'candidate':candidate,'classification':'decorative','reason':'Toy art node has no button or navigation event; explicit calibration evidence','source_evidence':[ref(scene)],'gui_evidence':si['routes']['map']['gui_evidence']}];sip.write_text(json.dumps(si))
  assert source_inventory(ref(sip),d,proj,si['binding']);passed.append('explicit_decorative_map_candidate_mapped')
  ui['routes'].append({'id':'route-map-panel','role':'map'});uip.write_text(json.dumps(ui));si['ui_route_inventory']=ref(uip);sip.write_text(json.dumps(si))
  try:source_inventory(ref(sip),d,proj,si['binding']);raise AssertionError('actual UI map role ignored')
  except ValueError as exc:
   assert 'actual UI inventory' in str(exc),str(exc)
   passed.append('actual_ui_map_route_cannot_be_absent')
  print(json.dumps({'passed':True,'checked':len(passed),'cases':passed,'boundary':'isolated toy gate calibration, not actual game runtime acceptance'},indent=2))
if __name__=='__main__':run()
