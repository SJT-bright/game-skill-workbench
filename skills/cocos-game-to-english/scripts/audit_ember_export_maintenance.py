"""Strict Ember Circuit exported-game maintenance adapter.

This game-specific branch changes production loaders, never generic acceptance
thresholds. Actual final compiled business/storage and hashed touch traces are
required. Existing Screw/Tower paths remain unchanged.
"""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import audit_native_storage_contract as storage
import audit_loading_recovery as loading
import audit_page_readiness as readiness
import audit_native_startup_renderer as startup_renderer

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
UI={'home','map','room_reopen','play_action','settings','guide','skins','skin_reward_retry','normal_clear_save','audio','reopen_home','reopen_map'}
CHECKS={'baseline','business','ui','rebuild','persistence','startup_retry','page_readiness','platform_structure','known_errors_closed','STORAGE-01'}

def normalize_main(text):
 marker=' task.transportKeys=[];'
 if marker in text:
  a=text.index(marker);b=text.index(' task.finish=function',a);text=text[:a]+text[b:]
 text=text.replace('this.image("v2title",-48,110,180,106),void(this.makeLoadingSpinner()', 'this.image("v2title",-48,80,180,106),void(this.makeLoadingSpinner()').replace("this.n('AssetLoadingSpinner',0,-15,32,32)","this.n('AssetLoadingSpinner',0,40,32,32)").replace('+(this.loadState?this.loadState.progress:0)+"%",0,-70,17)', '+(this.loadState?this.loadState.progress:0)+"%",0,-40,17)').replace("this.button('CANCEL',0,-140,180,54","this.button('CANCEL',0,-120,180,54")
 return text

def normalize_skin(text):
 before="this.button(s.claimed['bonus-'+this.index]?'BONUS SAVED':'AD · +50 COINS',0,this.H/2-110,260,46,()=>ad(this,'bonus'),{size:16,enabled:!s.claimed['bonus-'+this.index]});"
 after="this.button(this.skinPendingReward?'RETRY DELIVERY':s.claimed['bonus-'+this.index]?'BONUS SAVED':'AD · +50 COINS',0,this.H/2-110,260,46,()=>{if(this.skinPendingReward){if(this.skinPendingReward())this.skinMessage='Reward saved.';this.render();}else ad(this,'bonus');},{size:16,enabled:!!this.skinPendingReward||!s.claimed['bonus-'+this.index]});"
 return text.replace(after,before)

def normalize_web_transport(text):
 a=text.index('function transport(');b=text.index('function installTransports()',a);text=text[:a]+text[b:]
 a=text.index('function startupRetry(') if 'function startupRetry(' in text else text.index('retry.onclick=function()')
 b=text.index('function frame()',a);text=text[:a]+text[b:]
 a=text.index('window.__emberWebStartup=');b=text.index(';boot();requestAnimationFrame(frame);',a)
 return text[:a]+text[b:]

def art_visual(text):
 # Required-art service is separately rerun; font construction and all rendered UI
 # must remain exact. No asset/manifest/font bytes are exempted by tree checks.
 a=text.index('function makeFont(spec)');b=text.index('function load(g)',a) if 'var artEpoch=' not in text else text.index('var artEpoch=',a)
 return (text[a:b],text[text.index('window.__artUnified={'):])

def contains_binding(value,binding):
 if isinstance(value,dict):return value.get('execution_binding')==binding or any(contains_binding(x,binding) for x in value.values())
 return isinstance(value,list) and any(contains_binding(x,binding) for x in value)

def audit(args):
 root=args.project.resolve();native=args.native.resolve();web=args.web.resolve();r=read(args.review);errors=[];reused=[];reuse_cache={}
 def need(ok,msg):
  if not ok:errors.append(msg)
 def file(rel):return (root/rel).resolve()
 need(r.get('schema')=='export_maintenance_review.v1' and r.get('game_id')=='ember-circuit','Wrong Ember export review kind')
 need(r.get('authorization')=='maintain_only_available_export' and r.get('input_kind')=='existing_native_export','Actual exported-input maintenance authorization required')
 need(r.get('build_tag')==args.build_tag,'Build tag changed')
 nt,wt=tree(native),tree(web);need(r.get('native_files')==nt,'Final Native changed');need(r.get('web_files')==wt,'Final Web changed')
 source=r.get('maintenance_inputs',{});need(bool(source),'Maintenance recipe inputs missing')
 for rel,h in source.items():
  p=file(rel);need(p.is_file() and sha(p)==h,'Maintenance input changed: '+rel)
 binding={'source_sha256':digest(source),'native_tree_sha256':digest(nt),'web_tree_sha256':digest(wt),'build_tag':args.build_tag}
 need(r.get('binding')==binding,'Source/Native/Web binding stale')
 try:
  startup=read(file(r['native_startup_renderer_report']));errors+=startup_renderer.validate(startup,native,binding,root);errors+=startup_renderer.execute_registered(startup,native,binding,root)
 except (KeyError,ValueError,OSError,TypeError) as e:errors.append('STARTUP-RENDERER evidence missing/invalid: '+str(e))
 original=file(r.get('original_zip','missing'));need(original.is_file(),'Original Native ZIP missing')
 if original.is_file():
  need(sha(original)==r.get('original_sha256'),'Original Native ZIP changed')
  try:
   with zipfile.ZipFile(original) as z:
    base={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
   need(all(n in base for n in ['game.js','game.json','project.config.json']),'Original input is not a Native export')
   need(sorted(n for n,h in base.items() if nt.get(n)!=h)==r.get('changed_baseline_files'),'Unreviewed changed/deleted baseline file')
   need(sorted(set(nt)-set(base))==r.get('added_files'),'Unreviewed added Native file')
  except (ValueError,OSError,zipfile.BadZipFile) as e:errors.append('Original Native ZIP unreadable: '+str(e))
 need(set(r.get('checks',{}))==CHECKS and all(x.get('status')=='pass' and len(x.get('observed',''))>30 for x in r.get('checks',{}).values()),'Maintenance checklist incomplete')
 # Rebuild using the actual project recipe into an independent empty directory.
 recipe=file(r.get('rebuild_runner','missing'));need(recipe.is_file() and str(recipe) in r.get('rebuild_command',[]),'Actual rebuild runner required')
 if recipe.is_file():
  with tempfile.TemporaryDirectory(prefix='ember-native-rebuild ') as td:
   cmd=[p.replace('{out}',td) for p in r.get('rebuild_command',[])];need('{out}' in r.get('rebuild_command',[]),'Rebuild output placeholder missing')
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=120);need(p.returncode==0,'Independent rebuild failed: '+p.stderr[-600:]);need(tree(Path(td))==nt,'Independent Native rebuild differs')
 # Execute compiled bundle methods against the real Native adapter storage module.
 trace=file(r.get('storage_trace','missing'))
 if trace.is_file():
  try:
   t=read(trace);se=storage.validate(t,native,binding);errors+=se
   if not se:errors+=storage.replay(t)
   counter=t.get('negative_control',{});provenance=counter.get('provenance',{});proof_file=file(provenance.get('path','missing'));proof=read(proof_file)
   need(counter.get('kind')=='controlled_same_defect_fixture' and sha(proof_file)==provenance.get('sha256'),'Explicit counterexample provenance required')
   base_bundle=native/'assets/main/index.js';before,after=proof.get('before'),proof.get('after')
   need(proof.get('base_bundle_sha256')==sha(base_bundle) and isinstance(before,str) and before and isinstance(after,str) and before!=after and base_bundle.read_text().count(before)==1 and Path(counter['bundle']).read_text()==base_bundle.read_text().replace(before,after,1),'Counterexample must be one exact documented mutation of actual final compiled ledger')
   negative_cases=read(counter['raw_report']).get('cases',{});need(all(value=='pass' for key,value in negative_cases.items() if key!='missing_empty_string'),'Counterexample unrelated cases must remain normal')
  except (ValueError,OSError,KeyError) as e:errors.append('Storage trace invalid: '+str(e))
 else:errors.append('STORAGE-01 trace missing')
 # Keep the shared five-case writer refusal protocol meaningful for this branch.
 storage_reports=r.get('checks',{}).get('STORAGE-01',{}).get('auto_reports',[])
 need(bool(storage_reports),'STORAGE-01 current automatic report missing')
 for ref in storage_reports:
  try:
   p=file(ref['path']);report=read(p);need(sha(p)==ref['sha256'] and report.get('passed') is True and report.get('binding')==binding,'STORAGE-01 automatic report stale or failed')
   need(report.get('trace_sha256')==sha(trace) and report.get('tool')=='audit_native_storage_contract','STORAGE-01 trace/report mismatch')
  except (KeyError,ValueError,OSError) as e:errors.append('STORAGE-01 report invalid: '+str(e))
 if getattr(args,'stage','pre_scan')=='device':errors.append('Ember exported-input maintenance adapter has no physical-device acceptance protocol; actual device evidence must be implemented and verified separately')
 if getattr(args,'stage','pre_scan')=='post_package':
  try:
   import verify_native_zip
   report=read(file(r['zip_report']));archive=Path(report['zip']);need(report.get('passed') is True and report.get('binding')==binding and sha(archive)==report.get('zip_sha256'),'Final ZIP writer report stale')
   verify_native_zip.verify(archive,'7683427172773644296',native)
   refusal=read(file(r['writer_refusal_report']));need(refusal.get('passed') is True and refusal.get('binding')==binding and refusal.get('review_restored') is True,'Current writer refusal calibration failed')
   need({x.get('id') for x in refusal.get('checks',[]) if x.get('passed') is True}=={'missing_review','failed_check','stale_binding','missing_storage','normal'},'Writer five refusal/normal controls missing')
  except (KeyError,ValueError,OSError) as e:errors.append('Post-package evidence invalid: '+str(e))
 # The mandatory current loading and navigation contracts retain their own validators.
 for kind in ['loading_trace','page_plan','page_runtime','runtime_ui','business_report','native_boundary_report','skin_report','groups_report','startup_report','art_loading_report','progress_report']:
  need(file(r.get(kind,'missing')).is_file(),kind+' missing')
 # Preserve original runtime executions and validate exact scoped maintenance
 # deltas; the current overlay is a separate real execution, never a re-sign.
 original_binding=binding;reuse_ok=False;delta=None
 if r.get('runtime_reuse'):
  try:
   import importlib.util
   ref=r['runtime_delta_validator'];validator=file(ref['path']);need(sha(validator)==ref['sha256'],'Runtime delta validator changed')
   spec=importlib.util.spec_from_file_location('ember_exact_runtime_delta',validator);delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
   delta_errors=delta.validate(root,native,web,r['runtime_reuse']);errors+=['Runtime reuse: '+e for e in delta_errors];reuse_ok=not delta_errors
   original_binding=r['runtime_reuse']['execution_binding']
   overlay=read(file(r['current_runtime_overlay']));need(overlay.get('binding')==binding and overlay.get('producer')=='real_browser_touch_trace','Current maintenance overlay binding/producer invalid')
   for name in ['normal_startup','progress_typed','progress_read_failure','new_clear_save','settings_restart','glyph_retry','slow_network']:
    rows=[x for x in overlay.get('cases',[])if x.get('case')==name];need(len({tuple(x.get('viewport',[]))for x in rows})>=2,'Current overlay missing dual ratios: '+name)
    for row in rows:
     need(row.get('status')=='pass' and row.get('trusted_touch')is True and len(row.get('observed',''))>30,'Current overlay observation failed: '+name)
     raw=False;picture=False
     for evidence in row.get('evidence',[]):
      q=file(evidence['path']);need(q.is_file()and sha(q)==evidence['sha256'],'Current overlay raw changed: '+str(q))
      if q.is_file():
       data=q.read_bytes();raw=raw or q.suffix=='.json'and contains_binding(read(q),binding);picture=picture or len(data)>5000 and data.startswith(b'\x89PNG\r\n\x1a\n')
     need(raw and picture,'Current overlay requires actual current raw JSON and screenshot: '+name)
  except (KeyError,ValueError,OSError,ImportError)as e:errors.append('Runtime reuse invalid: '+str(e))
 try:
  data=read(file(r['loading_trace']));execution=data.get('execution_binding',data.get('binding'));need(execution==binding or reuse_ok and execution==original_binding,'LOAD-03 original execution not proven');errors+=loading.validate(data,execution,file(r['loading_trace']).parent)
 except (KeyError,ValueError,OSError) as e:errors.append('LOAD-03 input invalid: '+str(e))
 try:
  data=read(file(r['page_runtime']));execution=data.get('binding');need(execution==binding or reuse_ok and execution==original_binding,'LOAD-01 original execution not proven');page_errors,page_cases,page_refs=readiness.validate(read(file(r['page_plan'])),data,execution,file(r['page_runtime']).parent);errors+=page_errors
 except (KeyError,ValueError,OSError) as e:errors.append('LOAD-01 input invalid: '+str(e))
 try:
  ui=read(file(r['runtime_ui']));need(ui.get('binding')==binding or reuse_ok and ui.get('binding')==original_binding,'UI execution binding stale');need(ui.get('producer')=='real_browser_touch_trace','Real mobile touch UI evidence required')
  def verify_reuse(row,name,execution):
   if execution==binding or reuse_ok and execution==original_binding:return True
   if name in {'skin_reward_retry','normal_clear_save'}:return False
   reuse=row.get('reuse',{});base_native=Path(reuse.get('baseline_native',''));base_web=Path(reuse.get('baseline_web',''))
   if reuse.get('kind')!='unchanged_ui_dependencies' or len(reuse.get('reason',''))<50 or not base_native.is_dir() or not base_web.is_dir():return False
   key=(str(base_native),str(base_web),digest(execution))
   if key not in reuse_cache:
    bn,bw=tree(base_native),tree(base_web)
    ok=digest(bn)==execution.get('native_tree_sha256') and digest(bw)==execution.get('web_tree_sha256')
    ok=ok and {p for p in set(bn)|set(nt) if bn.get(p)!=nt.get(p)} <= {'assets/main/index.js','skin-system.js','art-unified.js','native-assets.js'}
    ok=ok and {p for p in set(bw)|set(wt) if bw.get(p)!=wt.get(p)} <= {'assets/main/index.js','skin-system.js','web-start.js','art-unified.js'}
    for current,baseline in [(native,base_native),(web,base_web)]:
     current_main=(current/'assets/main/index.js').read_text();baseline_main=(baseline/'assets/main/index.js').read_text()
     if delta:
      proof=read(root/'tools/progress-patch-original.json');methods=(root/'tools/ember-progress-methods.js').read_text();current_main=delta.original_progress(current_main,proof,methods);baseline_main=delta.original_progress(baseline_main,proof,methods)
     ok=ok and normalize_main(current_main)==normalize_main(baseline_main)
     ok=ok and normalize_skin((current/'skin-system.js').read_text())==normalize_skin((baseline/'skin-system.js').read_text())
     ok=ok and art_visual((current/'art-unified.js').read_text())==art_visual((baseline/'art-unified.js').read_text())
    ok=ok and normalize_web_transport((web/'web-start.js').read_text())==normalize_web_transport((base_web/'web-start.js').read_text())
    expected_assets=(base_native/'native-assets.js').read_text().replace('record={idle:0,stamp:Date.now()}', 'record={url:url,idle:0,stamp:Date.now()}').replace('requests.push(record);if(!loop)', 'requests.push(record);if(window.__emberArtStarted)window.__emberArtStarted(url);if(!loop)').replace('downloader.register(handlers);', 'downloader.register(handlers);window.__nativeAbortURL=function(url){requests.slice().forEach(function(r){if(r.url===url)r.stop();});};')
    ok=ok and (native/'native-assets.js').read_text()==expected_assets
    reuse_cache[key]=ok
   if reuse_cache[key]:reused.append({'case':name,'viewport':row.get('viewport'),'execution_binding':execution,'scope':'Original UI execution retained; exact full historical trees and only documented loader services, loading-only coordinates, byte-progress and Bonus pending-button differences verified; exact font construction, all UI rendering tail and all image/manifest bytes retained. Startup, loading and Bonus Retry are re-executed separately.'})
   return reuse_cache[key]
  rows=ui.get('cases',[])
  for name in UI:
   matches=[x for x in rows if x.get('case')==name];need(len({round(x['viewport'][0]/x['viewport'][1],3) for x in matches if len(x.get('viewport',[]))==2 and x['viewport'][1]>0})>=2,name+' missing two actual phone ratios')
   for row in matches:
    need(row.get('status')=='pass' and row.get('trusted_touch') is True and len(row.get('observed',''))>30,name+' actual touch observation required')
    need(bool(row.get('evidence')),name+' raw evidence required');image_found=False;raw_binding_found=False;execution=row.get('execution_binding',ui.get('execution_binding',binding))
    for ref in row.get('evidence',[]):
     p=file(ref.get('path','missing'));need(p.is_file() and sha(p)==ref.get('sha256'),name+' raw evidence stale')
     if p.is_file():
      data=p.read_bytes();raw_binding_found=raw_binding_found or (p.suffix=='.json' and contains_binding(read(p),execution));image_found=image_found or (len(data)>5000 and (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')))
    need(image_found,name+' actual screenshot missing');need(raw_binding_found,name+' original raw execution binding missing');need(verify_reuse(row,name,execution),name+' dependency reuse is not proven; rerun affected case')
 except (KeyError,ValueError,OSError) as e:errors.append('UI report invalid: '+str(e))
 for label in ['business','native_boundary','skin','groups','startup','art_loading','progress']:
  try:
   report=read(file(r[label+'_report']));runner=file(report.get('runner','missing'));need(runner.is_file() and sha(runner)==report.get('runner_sha256'),label+' actual runner identity')
   need(report.get('binding')==binding and report.get('passed') is True,label+' current successful execution required')
   need(len(report.get('cases',[])) >= (58 if label=='business' else 16 if label=='skin' else 9 if label=='groups' else 5 if label=='startup' else 8 if label=='art_loading' else 15 if label=='progress' else 14) and all(x.get('passed') is True for x in report['cases']),label+' failed/missing actual cases')
   p=subprocess.run(report.get('command',[]),capture_output=True,text=True,timeout=120);need(p.returncode==0,label+' executable regression failed');actual=json.loads(p.stdout);need(actual==report.get('result') and actual.get('passed') is True and actual.get('cases')==report.get('cases'),label+' raw execution differs')
   need(str(runner) in report.get('command',[]) and (str(native) in report.get('command',[]) or label=='skin' and str(native/'skin-system.js') in report.get('command',[])),label+' must execute current Native input')
  except (KeyError,ValueError,OSError) as e:errors.append(label+' report invalid: '+str(e))
 # Re-execute the actual preserved pre-fix progress artifact with the same
 # current runner, not only an attested coverage row.
 if r.get('runtime_reuse'):
  try:
   negative=read(root/'docs/test/progress-known-bad.json');runner=root/'tools/progress_storage_runner.cjs';baseline=Path(r['runtime_reuse']['baseline_native'])
   need(negative.get('runner_sha256')==sha(runner) and negative.get('execution_binding')==original_binding,'Progress known-bad execution identity stale')
   need(negative.get('bundle_sha256')==sha(baseline/'assets/main/index.js'),'Progress known-bad bundle is not original preserved artifact')
   command=['node',str(runner),str(baseline),str(baseline/'adapter-min.js')];need(negative.get('command')==command,'Progress negative command changed')
   process=subprocess.run(command,capture_output=True,text=True,timeout=120);actual=json.loads(process.stdout);need(process.returncode!=0 and actual.get('passed')is False and actual.get('cases')==negative.get('cases'),'Progress known-bad failed to reproduce with same current runner')
   need(sum(x.get('passed')is False for x in actual.get('cases',[]))==8,'Progress original failures must reproduce precisely')
  except (ValueError,KeyError,OSError)as e:errors.append('Progress negative control invalid: '+str(e))
 # This actual export has a level-map and direct room entry, no separate
 # stage-details route. Prove that inventory; never fabricate a new source page.
 routes=r.get('route_inventory',{})
 need(routes.get('home') is True and routes.get('map') is True and routes.get('stage_details') is False and routes.get('room') is True,'Actual Ember route inventory required')
 need(len(routes.get('stage_details_absent_reason',''))>50,'Absent stage-details route requires a concrete source rationale')
 source_ref=routes.get('compiled_ui_evidence',{});ui_bundle=native/'assets/main/index.js'
 need(source_ref.get('path')==str(ui_bundle) and source_ref.get('sha256')==sha(ui_bundle),'Route inventory must bind actual compiled UI')
 need(not any(name in ui_bundle.read_text() for name in ['stageDetails:function','levelDetails:function','stage_details:function','level_details:function']),'Unexpected details route requires explicit current review')
 # Enumerate every real persistence owner; do not omit skin/progress/receipt domains.
 texts='\n'.join((native/p).read_text() for p in ['assets/main/index.js','skin-system.js'])
 inventory={key:texts.count(key) for key in ['ember-circuit.v1','ember-circuit.skins.v1','RewardLedger','PENDING_KEY']}
 need(all(inventory.values()) and r.get('storage_inventory')==inventory,'All persistence domains must match actual current Native bytes')
 need(json.loads((native/'project.config.json').read_text()).get('appid')=='7683427172773644296','Wrong Ember app ID')
 for p in list(native.rglob('*.js'))+list(web.rglob('*.js')):
  result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True);need(result.returncode==0,'JavaScript syntax: '+str(p))
 return {'tool':'audit_ember_export_maintenance','passed':not errors,'status':'blocked' if errors else 'passed','errors':errors,'reused_ui_cases':reused,'scope':'Authorized Ember existing-export maintenance only; physical device, real ads and platform acceptance remain separate'}
