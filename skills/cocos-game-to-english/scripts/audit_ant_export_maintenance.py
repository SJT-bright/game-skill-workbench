"""Strict Ant Tunnel exported-game maintenance adapter.

This game-specific branch changes production loaders, never generic acceptance
thresholds. Actual final compiled business/storage and hashed touch traces are
required. Existing Screw/Tower paths remain unchanged.
"""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import audit_native_storage_contract as storage
import audit_loading_recovery as loading
import audit_page_readiness as readiness

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())

def validate_renderer_report_reference(root,review,binding,need):
 ref=review.get('renderer_report')
 if not isinstance(ref,dict) or set(ref)!={'path','sha256'}:
  need(False,'Current renderer_report must be an exact {path,sha256} reference')
  return root/'__missing_renderer_report_reference__'
 rel=ref.get('path')
 if not isinstance(rel,str) or not rel or Path(rel).is_absolute():
  need(False,'renderer_report path must be workspace-relative')
  return root/'__missing_renderer_report_reference__'
 path=(root/rel).resolve()
 if not path.is_relative_to(root.resolve()):
  need(False,'renderer_report path escapes the workspace')
  return root/'__missing_renderer_report_reference__'
 need(path.is_file() and sha(path)==ref.get('sha256'),'renderer_report missing or SHA-256 mismatch')
 if path.is_file():
  try:
   report=read(path)
   need(report.get('schema')=='native_startup_renderer.v1','renderer_report schema must be native_startup_renderer.v1')
   need(report.get('producer')=='real_browser_native_entry','renderer_report must come from the registered real Native entry runner')
   need(report.get('binding')==binding,'renderer_report binding differs from current source/Native/Web')
   need(report.get('native_tree_sha256')==binding.get('native_tree_sha256'),'renderer_report Native tree differs from current candidate')
  except (ValueError,OSError,AttributeError) as exc:
   need(False,'renderer_report JSON invalid: '+str(exc))
 return path
UI={'home','map','play_action','settings','guide','skins','daily','skin_reward_retry','normal_clear_save','audio','reopen_home','reopen_map'}
CHECKS={'baseline','business','ui','rebuild','persistence','startup_retry','page_readiness','platform_structure','known_errors_closed','STORAGE-01'}

GROUP_SCRIPTS={'platform': 'reports/test-v5/platform_test.js', 'reward': 'reports/test-v5/runtime_reward_test.js', 'audio': 'reports/test-v5/runtime_audio_test.js', 'services': 'reports/test-v5/services-regression.cjs', 'run_items': 'reports/test-v5/run-items-regression.cjs', 'scene_economy': 'reports/test-v5/scene-economy-regression.cjs', 'skin_ads': 'reports/home-v5/test-ads.cjs'}
EXPECTED_GROUPS={'reward': ['cancel', 'error', 'truthy-isEnded', 'missing-isEnded', 'wrong-transaction', 'complete-persist-consumer-duplicate', 'grant-save-failed-same-receipt-retry-no-read', 'cold-start-completed-journal-recovery', 'stale-completion-after-restart'], 'services': ['old-v3 migration preserves paid balance/skins/run receipts,day1 once', 'seven rewards atomically delivered including chest', 'rollback blocked and next-day cycle restarts', 'failed claim before write retry once', 'after-durable claim failure reload once', 'existing purchase/equip/settle duplicate+failure preserve v4 fields'], 'run_items': ['real production run +3 debits1 and leaves plus5false', 'cold production-run resume retains itemBonus once', 'wallet debit then run-write failure retry grants3 once', 'cold recovery reconciles debit journal with uncommitted run', 'wallet durable-write interruption retry does not double-debit', 'run durable-write interruption retry does not double-add', 'restart abandons run effect,no refund,no old receipt reapplication', 'locked rejected,real hint debit once,no-pair no-debit', 'strict advertised+5 once independent of two item+3 grants,cold recover18'], 'scene_economy': ['real finishWin atomically awards then advances', 'real replay awards5 and preserves max', 'wallet write failure blocks advancement, same run retries', 'progress write failure retries without a second egg reward', '100 bound locked99 before unlock and invalid100', 'real finale100 awards38, marks completed99, no advance overflow'], 'skin_ads': ['3/5 unique completions, ownership, reload, no currency deduction', 'cancel/error/timeout/late/duplicate callbacks never credit', 'global pending prevents overlapping skin/video requests', 'wallet completion write fails; journal survives reload; retry no new video', 'journal write failure but wallet commit succeeds', 'both journal+wallet fail; live-memory retry no replay', 'post-write readback error remains idempotent on retry', 'unavailable Web neither records progress nor writes wallet', 'pending save fails before viewing: no SDK call', 'actual DataMgr native object/empty-string semantics', 'existing ownership retained, normal purchase/equip and Daily preserve ad fields', 'held SDK callback+platform timer expires through independent Cocos frame; late ignored']}

# The r3c maintenance exception is an exact, reviewed migration contract. Keep
# these full records pinned here so the candidate manifest cannot authorize its
# own edits by changing both the transform and the target bytes.
R3C_TRANSFORMS={
 'subpackages/resources/import/06/06d16a52b.json':{'path':'subpackages/resources/import/06/06d16a52b.json','before_sha256':'d4a626c3750cfca734e30cf4e35452738fcc7e4dd978c386c3bc848daf7a9365','after_sha256':'0b5342004b12a911b83b01d47ec70df244cb2a87469b2c91e062c09456a32793','reason':'Remove unused GameAudioMgr.audioBgm prefab dependency; preserve all AudioClip UUID/config and audio bytes.'},
 'subpackages/resources/config.json':{'transform_id':'no-social-r3c:config.json','path':'subpackages/resources/config.json','before_sha256':'28445c685e2dc53d00bc3af7459cc395ef25b7454e219c3229b02f3933a84cc3','after_sha256':'7cc1bbaf652e07701a848e591206a6f62d11cb0ba1b822b2e3aa50f6957afc17','reason':'Remove the unreachable PanelRank prefab path while retaining all other paths and packs.'},
 'subpackages/resources/import/0e/0ebdf0a6d.json':{'transform_id':'no-social-r3c:0ebdf0a6d.json','path':'subpackages/resources/import/0e/0ebdf0a6d.json','before_sha256':'0dc17a00fcc182f68a8caf10625ad8fb377082dee517bab272a073d6f0e958b3','after_sha256':'37cf01b5de511be5a0e1589ad0ecc269ccbb22cce3c0149a1d644ce51ecee0c7','reason':'Rename hidden social controls and rank atlas metadata only; retain nodes, component references, UUID table, groups, and dependency arrays.'},
 'subpackages/resources/import/0a/0a0d77cb7.json':{'transform_id':'no-social-r3c:0a0d77cb7.json','path':'subpackages/resources/import/0a/0a0d77cb7.json','before_sha256':'c193c04282dfc4444ebcad9396f6328c47a99c89c8e5128aa0d480d24131a693','after_sha256':'1463c725f1183ab4a0bd9f251fcfcca9f82a65eb202204ebe7ed0e6f8c6f4077','reason':'Rename the hidden share control only; retain nodes, component references, UUID table, groups, and dependency arrays.'},
 'subpackages/resources/import/22/22358bb3-9825-4007-81d1-084ee52874fe.json':{'transform_id':'no-social-r3c:22358bb3-9825-4007-81d1-084ee52874fe.json','path':'subpackages/resources/import/22/22358bb3-9825-4007-81d1-084ee52874fe.json','before_sha256':'0303096fb62f1d53a3f916ade7af4ac1f574a00f993ff929bbff21915b5db19a','after_sha256':'95ca895ac7df9247a91c89789e2b511302d5b46f7480ecea22e5b73903869210','reason':'Rename the retained share SpriteFrame metadata only; preserve its texture and references.'}}
R3C_TRANSFORM_BYTES={
 'subpackages/resources/import/06/06d16a52b.json':(9143,9117),
 'subpackages/resources/config.json':(6817,6780),
 'subpackages/resources/import/0e/0ebdf0a6d.json':(7652,7694),
 'subpackages/resources/import/0a/0a0d77cb7.json':(3585,3594),
 'subpackages/resources/import/22/22358bb3-9825-4007-81d1-084ee52874fe.json':(185,189)}
R3C_RANK_REMOVAL=('subpackages/resources/import/da/da50f3bf-ec52-4ab1-91e1-e752f96da822.json','9bff41a0aae8148ec6ee6f5eca93723810585aa739bc712b6c7df5e008cbc9f4',2677)
R3C_PNG_MOVES={
 'subpackages/resources/native/86/86ab9b2a-1758-47db-b1f1-2142f6248ae9.png':('subpackages/ant_legacy/native/86/86ab9b2a-1758-47db-b1f1-2142f6248ae9.png','ant_legacy','a48d7765a926cb6a0a0681a52f633bc1bd311a90c28ac881c319f4ca13f9d8ce',1362592),
 'subpackages/resources/native/c8/c8c6e409-5682-4d9f-af10-f6f8e4995449.png':('subpackages/ant_legacy/native/c8/c8c6e409-5682-4d9f-af10-f6f8e4995449.png','ant_legacy','9b53c3279b541ebbf7c11c148cb132683866333646ec6765f50914aff91b2ddf',1657385)}
R3C_HOME_ART={
 'subpackages/resources/home-v4/chest-day7.png':('parts/home-v4-art/images/chest-day7.png','subpackages/ant_daily/home-v4/chest-day7.png','ant_daily','63a293f061ca1419c5c4c33099ad475680ae6dcd95172a9a623c428ac21c55a3',2376480),
 'subpackages/resources/home-v4/hero-ant-garden.png':('parts/home-v4-art/images/hero-ant-garden.png','subpackages/ant_home/home-v4/hero-ant-garden.png','ant_home','6a4b03bcddb9a368fcc239640811af02582439d465d5f91e443ce11801ee56e0',1898311),
 'subpackages/resources/home-v4/item-moves.png':('parts/home-v4-art/images/item-moves.png','subpackages/ant_items/home-v4/item-moves.png','ant_items','afdc16f910c8fd1555edc7bb87b0c3551a78d4a4c1cda18c5ab85dbae6bb0563',1770181)}

def validate_r3c_migration_contract(root,native,baseline,manifest):
 errors=[]
 def need(ok,message):
  if not ok:errors.append(message)
 mapping=manifest.get('mapping',{})
 transforms=manifest.get('serialized_transforms',[])
 for rel in mapping:
  if rel.startswith('subpackages/resources/home-v4/') and not (baseline/rel).is_file():
   need(rel in R3C_HOME_ART,'Unapproved supplemental Home v4 source: '+rel)
 need(set(R3C_HOME_ART).issubset(mapping),'Required three Home v4 art mappings missing')
 targets=[row.get('path') for row in mapping.values() if isinstance(row,dict)]
 for rel,(source_rel,target_rel,group,digest_value,size) in R3C_HOME_ART.items():
  row=mapping.get(rel);source=root/source_rel;target=native/target_rel
  expected_row={'path':target_rel,'group':group,'sha256':digest_value,'bytes':size}
  need(source.is_file() and sha(source)==digest_value and source.stat().st_size==size,'Pinned Home v4 frozen source mismatch: '+source_rel)
  need(row==expected_row,'Pinned Home v4 mapping mismatch: '+rel)
  need(targets.count(target_rel)==1,'Pinned Home v4 target must be unique: '+target_rel)
  need(target.is_file() and sha(target)==digest_value and target.stat().st_size==size,'Pinned Home v4 Native target mismatch: '+target_rel)
 paths=[x.get('path') for x in transforms if isinstance(x,dict)]
 need(len(transforms)==len(R3C_TRANSFORMS) and len(paths)==len(set(paths)) and set(paths)==set(R3C_TRANSFORMS),'Serialized transform inventory differs from the five pinned r3c paths')
 for transform in transforms:
  if not isinstance(transform,dict):
   need(False,'Serialized transform record is not an object');continue
  expected=R3C_TRANSFORMS.get(transform.get('path'))
  need(expected is not None and transform==expected,'Serialized transform record differs from pinned r3c contract: '+str(transform.get('path')))
 for rel,expected in R3C_TRANSFORMS.items():
  before=baseline/rel;row=mapping.get(rel);target=(native/row.get('path','missing')) if isinstance(row,dict) else native/'missing'
  before_sha=expected['before_sha256'];after_sha=expected['after_sha256'];before_bytes,after_bytes=R3C_TRANSFORM_BYTES[rel]
  need(before.is_file() and sha(before)==before_sha and before.stat().st_size==before_bytes,'Pinned r3c transform source mismatch: '+rel)
  output_bytes_match=row.get('output_bytes')==after_bytes
  need(isinstance(row,dict) and row.get('path')==rel and row.get('sha256')==before_sha and row.get('bytes')==before_bytes and row.get('output_sha256')==after_sha and output_bytes_match,'Pinned r3c transform mapping mismatch: '+rel)
  need(target.is_file() and sha(target)==after_sha and target.stat().st_size==after_bytes,'Pinned r3c transform output mismatch: '+rel)
 rank_path,rank_sha,rank_bytes=R3C_RANK_REMOVAL;rank_source=baseline/rank_path;rank_target=native/rank_path
 need(rank_source.is_file() and sha(rank_source)==rank_sha and rank_source.stat().st_size==rank_bytes,'Pinned PanelRank source mismatch')
 need(rank_path not in mapping and not rank_target.exists(),'PanelRank removal target or mapping unexpectedly present')
 config='subpackages/resources/config.json';config_before=baseline/config;config_after=native/config
 try:
  before_config=json.loads(config_before.read_text());after_config=json.loads(config_after.read_text())
  need(before_config.get('paths',{}).get('115')==['prefabs/panels/PanelRank',4] and '115' not in after_config.get('paths',{}),'PanelRank config key 115 removal mismatch')
 except (OSError,ValueError,AttributeError):need(False,'PanelRank config JSON invalid')
 try:
  original_manifest=read(root/'reports/original-sha256.json')
 except (OSError,ValueError):original_manifest={}
 for source_rel,(target_rel,group,digest_value,size) in R3C_PNG_MOVES.items():
  row=mapping.get(source_rel);source=root/'原版源码_LineReconnect'/source_rel;target=native/target_rel;duplicate=native/source_rel
  need(original_manifest.get(source_rel)==digest_value and source.is_file() and sha(source)==digest_value and source.stat().st_size==size,'Protected original PNG source mismatch: '+source_rel)
  need(isinstance(row,dict) and row.get('path')==target_rel and row.get('group')==group and row.get('sha256')==digest_value and row.get('bytes')==size and not row.get('output_sha256'),'Protected original PNG mapping mismatch: '+source_rel)
  need(target.is_file() and sha(target)==digest_value and target.stat().st_size==size,'Protected original PNG ant_legacy target mismatch: '+target_rel)
  need(not duplicate.exists(),'Protected original PNG is duplicated under resources: '+source_rel)
 return errors

def audit(args):
 root=args.project.resolve();native=args.native.resolve();web=args.web.resolve();r=read(args.review);errors=[]
 def need(ok,msg):
  if not ok:errors.append(msg)
 def file(rel):return (root/rel).resolve()
 need(r.get('schema')=='ant_export_maintenance_review.v1' and r.get('game_id')=='ant-tunnel','Wrong Ant export review kind')
 need(r.get('authorization')=='maintain_only_available_export' and r.get('input_kind')=='existing_native_export','Actual exported-input maintenance authorization required')
 need(r.get('build_tag')==args.build_tag,'Build tag changed')
 nt,wt=tree(native),tree(web);need(r.get('native_files')==nt,'Final Native changed');need(r.get('web_files')==wt,'Final Web changed')
 source=r.get('maintenance_inputs',{});need(bool(source),'Maintenance recipe inputs missing')
 for rel,h in source.items():
  p=file(rel);need(p.is_file() and sha(p)==h,'Maintenance input changed: '+rel)
 from types import SimpleNamespace
 from check_known_issues import binding as formal_binding
 need(file(r.get('source_project_root','missing'))==root/'ant','Actual compiled source must be ant/')
 binding=formal_binding(SimpleNamespace(project=root/'ant',native=native,web=web,build_tag=args.build_tag))
 need(r.get('binding')==binding,'Source/Native/Web binding stale')
 original=file('原版源码_LineReconnect');baseline_ref=file('reports/original-sha256.json')
 need(original.is_dir() and baseline_ref.is_file(),'Protected original exported tree/manifest missing')
 if original.is_dir() and baseline_ref.is_file():
  base=read(baseline_ref);need(all((original/k).is_file() and sha(original/k)==h for k,h in base.items()) and set(tree(original))-set(base)<={'.DS_Store'},'Protected original export changed')
  need(sha(baseline_ref)==r.get('original_manifest_sha256'),'Original manifest changed')
  need(all(n in base for n in ['game.js','game.json','project.config.json']),'Original input is not a Native export')
  need(sorted(n for n,h in base.items() if nt.get(n)!=h)==r.get('changed_baseline_files'),'Unreviewed changed/deleted baseline file')
  need(sorted(set(nt)-set(base))==r.get('added_files'),'Unreviewed added Native file')
 need(set(r.get('checks',{}))==CHECKS and all(x.get('status')=='pass' and len(x.get('observed',''))>30 for x in r.get('checks',{}).values()),'Maintenance checklist incomplete')
 # Rebuild using the actual project recipe into an independent empty directory.
 recipe=file(r.get('rebuild_runner','missing'));need(recipe.is_file() and str(recipe) in r.get('rebuild_command',[]),'Actual rebuild runner required')
 if recipe.is_file():
  with tempfile.TemporaryDirectory(prefix='ant-native-rebuild ') as td:
   cmd=[p.replace('{out}',td) for p in r.get('rebuild_command',[])];need('{out}' in r.get('rebuild_command',[]),'Rebuild output placeholder missing')
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=120);need(p.returncode==0,'Independent rebuild failed: '+p.stderr[-600:]);need(tree(Path(td))==nt,'Independent Native rebuild differs')
 # Execute compiled bundle methods against the real Native adapter storage module.
 trace=file(r.get('storage_trace','missing'))
 if trace.is_file():
  try:
   t=read(trace);se=storage.validate(t,native,binding);errors+=se
   if not se:errors+=storage.replay(t)
   counter=t.get('negative_control',{});provenance=counter.get('provenance',{});proof_file=file(provenance.get('path','missing'));proof=read(proof_file)
   need(counter.get('kind')=='controlled_legacy_fixture' and sha(proof_file)==provenance.get('sha256'),'Explicit counterexample provenance required')
   base_bundle=native/'assets/main/index.js';before,after=proof.get('patch',{}).get('before'),proof.get('patch',{}).get('after')
   need(proof.get('base_sha256')==sha(base_bundle) and Path(proof.get('base_bundle','missing')).resolve()==base_bundle.resolve() and isinstance(before,str) and before and isinstance(after,str) and before!=after and base_bundle.read_text().count(before)==1 and Path(counter['bundle']).read_text()==base_bundle.read_text().replace(before,after,1),'Counterexample must be one exact documented mutation of actual final compiled ledger')
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
 if getattr(args,'stage','pre_scan')=='device':errors.append('Ant exported-input maintenance adapter has no physical-device acceptance protocol; actual device evidence must be implemented and verified separately')
 if getattr(args,'stage','pre_scan')=='post_package':
  try:
   import verify_native_zip
   report=read(file(r['zip_report']));archive=Path(report['zip']);need(report.get('passed') is True and report.get('binding')==binding and sha(archive)==report.get('zip_sha256'),'Final ZIP writer report stale')
   verify_native_zip.verify(archive,'7683427172773644296',native)
   extracted=read(file(r['post_package_runtime']));need(extracted.get('binding')==binding and extracted.get('archive_sha256')==sha(archive) and extracted.get('producer')=='real_browser_touch_trace','Actual extracted ZIP runtime evidence required')
   exroot=Path(extracted.get('extracted_root','missing'));need(exroot.is_dir() and tree(exroot)==nt,'Independently extracted ZIP tree changed')
   for case in ['native_start_first_level','subpackage_failure_retry','first_level_action']:
    cases=[x for x in extracted.get('cases',[]) if x.get('case')==case]
    need(len({tuple(x.get('viewport',[])) for x in cases})>=2,'Extracted '+case+' two ratios required')
    for row in cases:
     need(row.get('status')=='pass' and row.get('trusted_touch') is True and len(row.get('observed',''))>30,'Actual extracted runtime observation required')
     need(bool(row.get('evidence')),'Extracted raw evidence missing')
     for ref in row.get('evidence',[]):
      raw=file(ref.get('path','missing'));need(raw.is_file() and sha(raw)==ref.get('sha256'),'Extracted runtime raw stale')

   refusal=read(file(r['writer_refusal_report']));need(refusal.get('passed') is True and refusal.get('binding')==binding and refusal.get('review_restored') is True,'Current writer refusal calibration failed')
   need({x.get('id') for x in refusal.get('checks',[]) if x.get('passed') is True}=={'missing_review','failed_check','stale_binding','missing_storage','normal'},'Writer five refusal/normal controls missing')
   need(refusal.get('tool')=='test_writer_refusal' and refusal.get('checked')==5 and refusal.get('failed')==0,'Actual shared five-case writer calibration required')
   for ref in refusal.get('writer_files',[]):
    tool=Path(ref.get('path','missing'));need(tool.is_file() and sha(tool)==ref.get('sha256'),'Writer calibration tool changed')
   need(any(Path(x.get('path','')).name=='make_tiktok_zip.py' for x in refusal.get('writer_files',[])),'Official writer calibration identity missing')
  except (KeyError,ValueError,OSError) as e:errors.append('Post-package evidence invalid: '+str(e))
 # The mandatory current loading and navigation contracts retain their own validators.
 for kind in ['loading_trace','page_plan','page_runtime','runtime_ui','business_manifest']:
  need(file(r.get(kind,'missing')).is_file(),kind+' missing')
 try:errors+=loading.validate(read(file(r['loading_trace'])),binding,file(r['loading_trace']).parent)
 except (KeyError,ValueError,OSError) as e:errors.append('LOAD-03 input invalid: '+str(e))
 try:errors+=readiness.validate(read(file(r['page_plan'])),read(file(r['page_runtime'])),binding,file(r['page_runtime']).parent)[0]
 except (KeyError,ValueError,OSError) as e:errors.append('LOAD-01 input invalid: '+str(e))
 try:
  ui=read(file(r['runtime_ui']));need(ui.get('binding')==binding,'UI execution binding stale');need(ui.get('producer')=='real_browser_touch_trace','Real mobile touch UI evidence required')
  rows=ui.get('cases',[])
  for name in UI:
   matches=[x for x in rows if x.get('case')==name];need(len({round(x['viewport'][0]/x['viewport'][1],3) for x in matches if len(x.get('viewport',[]))==2 and x['viewport'][1]>0})>=2,name+' missing two actual phone ratios')
   for row in matches:
    need(row.get('status')=='pass' and row.get('trusted_touch') is True and len(row.get('observed',''))>30,name+' actual touch observation required')
    need(bool(row.get('evidence')),name+' raw evidence required');image_found=False
    for ref in row.get('evidence',[]):
     p=file(ref.get('path','missing'));need(p.is_file() and sha(p)==ref.get('sha256'),name+' raw evidence stale')
     if p.is_file():
      data=p.read_bytes();image_found=image_found or (len(data)>5000 and (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')))
    need(image_found,name+' actual screenshot missing')
 except (KeyError,ValueError,OSError) as e:errors.append('UI report invalid: '+str(e))
 try:
  manifest=read(file(r['business_manifest']));need(manifest.get('binding')==binding,'Business manifest binding stale')
  entries=manifest.get('executions',{});need(set(entries)=={'platform','reward','audio','services','run_items','scene_economy','skin_ads'},'Exact Ant production business groups required')
  for label,row in entries.items():
   runner=file(row.get('runner','missing'));raw=file(row.get('raw','missing'))
   need(runner.is_file() and sha(runner)==row.get('runner_sha256'),'Business runner changed: '+label)
   need(raw.is_file() and sha(raw)==row.get('raw_sha256'),'Business raw changed: '+label)
   cmd=row.get('command',[]);need(str(runner) in cmd and str(native) in cmd and label in cmd,'Actual Native group command required: '+label)
   p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=120)
   need(p.returncode==0,'Business execution failed: '+label)
   actual=json.loads(p.stdout);need(actual==read(raw) and actual.get('passed') is True and actual.get('mode')==label and actual.get('bundle_sha256')==sha(native/'assets/main/index.js'),'Business replay changed: '+label)
   need(actual.get('script_sha256')==source.get(GROUP_SCRIPTS.get(label,'')),'Actual test body is not pinned: '+label)
   reports=list(actual.get('reports',{}).values());need(len(reports)==1,'Exactly one real raw report per group')
   if reports:
    report=reports[0]
    if label=='platform':need(report.get('status')=='PASS' and report.get('total')==96 and report.get('failed')==0,'96 platform cases required')
    elif label=='reward':need([x.get('case') for x in report.get('cases',[])]==EXPECTED_GROUPS[label] and all(x.get('passed') is True for x in report['cases']),'Exact AntRun reward cases required')
    elif label=='audio':need(report.get('suspendAndPersistencePassed') is True and len(report.get('channels',[]))==2,'Actual music/sfx persistence required')
    elif label=='skin_ads':need([x.get('name') for x in report.get('rows',[])]==EXPECTED_GROUPS[label] and all(x.get('pass') is True for x in report['rows']),'Exact actual skin ad groups required')
    elif label=='scene_economy':need(report.get('status')=='pass' and [x.get('case') for x in report.get('rows',[])]==EXPECTED_GROUPS[label] and all(x.get('status')=='pass' for x in report.get('rows',[])),'Actual scene/economy groups incomplete')
    else:need(report.get('status')=='pass' and report.get('rows')==EXPECTED_GROUPS[label],'Actual '+label+' groups incomplete')
  win_runner=root/'reports/test-v5/win-moves.cjs';need(source.get('reports/test-v5/win-moves.cjs')==sha(win_runner),'Win used-count runner identity changed')
  proc=subprocess.run(['node',str(win_runner),str(native/'assets/main/index.js')],cwd=root,capture_output=True,text=True,timeout=60)
  result=json.loads(proc.stdout);need(proc.returncode==0 and [x.get('name') for x in result.get('rows',[])]==['normal','one+3','two+3','two+3_and+5'] and all(x.get('pass') is True and x.get('displayed')==x.get('actualSwaps') for x in result['rows']),'Actual production win counter must match swaps across item/ad bonuses')
  # Production scripts reading standalone inputs are valid only if every exact
  # production block is present once in both current bundles.
  for rel in ['parts/economy-v3/economy.js','parts/home-v4/services.js','parts/home-v5/skin-ads.js']:
   text=file(rel).read_text();need(all((p/'assets/main/index.js').read_text().count(text)==1 for p in [native,web]),'Compiled service differs: '+rel)
  production=file(r.get('production_runner','missing'))
  need(production==root/'reports/expansion-v3/verify-production-v3.cjs' and str(production.relative_to(root)) in source,'Pinned actual production replay required')
  for layer in [native,web]:
   with tempfile.TemporaryDirectory(prefix='ant-production ') as td:
    output=Path(td)/'actual.json';cmd=['node',str(production),'--runtime',str(layer),'--report',str(output),'--expect-compiled'];p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=120);need(p.returncode==0,'Actual compiled 100-level replay failed')
    if output.is_file():
     d=read(output);need(d.get('status')=='passed' and d.get('levelCount')==100 and d.get('legalSolutionSwaps')==640 and d.get('trapRejections')==95 and d.get('fixedAndCancelControls')==395 and d.get('actualCompiledTableVerified') is True,'100/640/95/395 production coverage required')
 except (KeyError,ValueError,OSError,subprocess.TimeoutExpired) as e:errors.append('Ant business report invalid: '+str(e))
 from make_tiktok_zip import native_problems
 structural,_,sizes=native_problems(native);errors+=structural
 need(not any(k.startswith('docs/') for k in nt),'Documentation is not allowed in upload payload')
 need(all(wt.get(k)==v for k,v in nt.items()),'Native shared content differs from current Web')
 # Required startup/download policy is independent of successful recovery.
 # Always replay the actual shared static size/audio check, and independently
 # revalidate timing raw frames/network plans; a written pass flag cannot replace it.
 try:
  subs=r.get('startup_subpackages');need(isinstance(subs,list) and all(isinstance(x,str) for x in subs),'Actual startup subpackage inventory required')
  content_manifest=native/'ant-content-manifest.js'
  if content_manifest.is_file():
   text=content_manifest.read_text().strip();need(text.startswith('module.exports=') and text.endswith(';'),'Native content manifest must be pure JSON data')
   actual_manifest=json.loads(text[len('module.exports='):-1]);need(actual_manifest.get('version')==6 and subs==actual_manifest.get('startup_subpackages'),'Declared startup packages differ from actual Native manifest')
   baseline=root/'reports/test-v5/native-payload'
   errors.extend(validate_r3c_migration_contract(root,native,baseline,actual_manifest))
   transforms=actual_manifest.get('serialized_transforms',[]);allowed_transform='subpackages/resources/import/06/06d16a52b.json'
   for old,row in actual_manifest.get('mapping',{}).items():
    protected_move=R3C_PNG_MOVES.get(old)
    home_art=R3C_HOME_ART.get(old)
    before=(root/'原版源码_LineReconnect'/old) if protected_move else ((root/home_art[0]) if home_art else (baseline/old))
    before_root=(root/'原版源码_LineReconnect') if protected_move else ((root/'parts/home-v4-art/images') if home_art else baseline)
    after=native/row.get('path','missing')
    paths_valid=before.resolve().is_relative_to(before_root.resolve()) and after.resolve().is_relative_to(native.resolve()) and before.is_file() and after.is_file()
    need(paths_valid,'Physical content migration path invalid: '+old)
    if not paths_valid:continue
    need(sha(before)==row.get('sha256') and before.stat().st_size==row.get('bytes'),'Original migration bytes changed: '+old)
    if old==allowed_transform and transforms:
     proof=next((x for x in transforms if x.get('path')==old),{});data=json.loads(before.read_bytes());need(data[3][14]==['2219f8EXtlKn57u100SIk5g',['node','audioBgm'],3,1,6] and data[4][39]==[14,0,1,1],'Original obsolete-audio-prefab transform anchor changed')
     data[3][14]=['2219f8EXtlKn57u100SIk5g',['node'],3,1];data[4][39]=[14,0,1];scene=data[5][6];component=scene[0][1][3][2];need(component==[39,-11,24],'Original obsolete clip component anchor changed');component.pop()
     indexes=[i for i,k in enumerate(scene[4])if k==23];need(len(indexes)==1,'Original obsolete clip reference anchor changed');index=indexes[0];need(scene[5][index]==14,'Original clip reference target changed')
     for field in [3,4,5]:scene[field].pop(index)
     expected=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode();need(after.read_bytes()==expected and sha(before)==proof.get('before_sha256') and sha(after)==proof.get('after_sha256')==row.get('output_sha256'),'Only exact calibrated unused audioBgm reference removal is permitted')
    elif old in R3C_TRANSFORMS:
     expected=R3C_TRANSFORMS[old];_,output_bytes=R3C_TRANSFORM_BYTES[old]
     need(sha(before)==expected['before_sha256'] and sha(after)==expected['after_sha256'] and after.stat().st_size==output_bytes and row.get('output_sha256')==expected['after_sha256'] and row.get('output_bytes')==output_bytes,'Only the pinned r3c serialized JSON bytes are permitted: '+old)
    elif protected_move:
     target_path,group,digest_value,size=protected_move
     need(row.get('path')==target_path and row.get('group')==group and sha(after)==digest_value and after.stat().st_size==size and not row.get('output_sha256') and not (native/old).exists(),'Protected UUID PNG must exist only at its exact ant_legacy target: '+old)
    elif home_art:
     source_rel,target_path,group,digest_value,size=home_art
     source=root/source_rel
     need(source.resolve().is_relative_to((root/'parts/home-v4-art/images').resolve()) and row=={'path':target_path,'group':group,'sha256':digest_value,'bytes':size} and sha(source)==digest_value and source.stat().st_size==size and sha(after)==digest_value and after.stat().st_size==size and not row.get('output_sha256'),'Only exact frozen Home v4 art source bytes may be mapped to the pinned Native target: '+old)
    else:need(sha(before)==sha(after) and after.stat().st_size==row.get('bytes') and not row.get('output_sha256'),'Physical content migration changed bytes: '+old)
   need(bool(actual_manifest.get('mapping')),'Physical content migration inventory missing')
  settings=(native/'src/settings.js').read_text()
  if 'hasResourcesBundle:true' in settings:need(isinstance(subs,list) and 'resources' in subs,'Actual startup resources bundle cannot be omitted')
  with tempfile.TemporaryDirectory(prefix='ant-startup-contract ') as td:
   renderer_report=validate_renderer_report_reference(root,r,binding,need)
   target=Path(td)/'actual.json';command=[sys.executable,str(Path(__file__).resolve().parent/'audit_startup_contract.py'),'--project',str(root/'ant'),'--native',str(native),'--startup-subpackages',','.join(subs or []),'--binding',str(args.review.resolve()),'--renderer-report',str(renderer_report),'--out',str(target)];proc=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=120)
   need(proc.returncode==0,'Mandatory startup size/audio/source contract failed: '+proc.stdout[-700:])
   if target.is_file():need(read(target).get('passed') is True and read(target).get('binding')==binding,'Actual startup contract report failed/stale')
  import audit_startup_loading
  startup=read(file(r.get('startup_loading_report','missing')));errors+=audit_startup_loading.validate_report(startup,binding,recheck=True)
 except (KeyError,ValueError,OSError,TypeError,IndexError) as e:errors.append('Mandatory startup timing/raw invalid: '+str(e))
 # Inventory all actual compiled storage owners and route availability.
 routes=r.get('route_inventory',{})
 need(routes.get('home') is True and routes.get('map') is True and routes.get('stage_details') is False and routes.get('room') is True,'Actual Ant route inventory required')
 need(len(routes.get('stage_details_absent_reason',''))>50,'Absent stage-details route requires a concrete source rationale')
 source_ref=routes.get('compiled_ui_evidence',{});ui_bundle=native/'assets/main/index.js'
 need(source_ref.get('path')==str(ui_bundle) and source_ref.get('sha256')==sha(ui_bundle),'Route inventory must bind actual compiled UI')
 texts=ui_bundle.read_text()
 keys=['ANT_ECONOMY_V3','ANT_SKIN_AD_COMPLETION_V1','ANT_RUN_V1','ANT_REWARD_JOURNAL_V1','ANT_PROGRESS_V1','ANT_TUT_QUEEN','ANT_TUT_SWAP','AntDaily','DataMgr:[function','ant-tunnel:v1:']
 inventory={key:texts.count(key) for key in keys}
 need(all(inventory.values()) and r.get('storage_inventory')==inventory,'All persistence domains must match actual current Native bytes')
 need(json.loads((native/'project.config.json').read_text()).get('appid')=='7683427172773644296','Wrong Ant app ID')
 for p in list(native.rglob('*.js'))+list(web.rglob('*.js')):
  result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True);need(result.returncode==0,'JavaScript syntax: '+str(p))
 return {'tool':'audit_ant_export_maintenance','passed':not errors,'status':'blocked' if errors else 'passed','errors':errors,'scope':'Authorized Ant existing-export maintenance only; physical device, real ads and platform acceptance remain separate'}
