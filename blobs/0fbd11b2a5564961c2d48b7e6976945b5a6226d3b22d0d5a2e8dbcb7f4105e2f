"""Validation for user-authorized maintenance of an existing Native export.
Not a replacement for full English conversion/remake acceptance; fixed runtime
requirements remain mandatory. No fabricated editable Cocos project required.
"""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile,shutil,tempfile
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def audit(args):
 r=json.loads(args.review.read_text());root=args.project.resolve();native=args.native.resolve();web=args.web.resolve();errors=[]
 def require(ok,msg):
  if not ok:errors.append(msg)
 require(r.get('schema')=='export_maintenance_review.v1','Wrong export-maintenance schema')
 require(r.get('input_kind')=='existing_native_export','Must explicitly identify exported input; not a fabricated source project')
 require(r.get('build_tag')==args.build_tag,'Build tag changed')
 require(r.get('authorization')=='maintain_only_available_export','Missing explicit user authorization for exported-only maintenance')
 require(r.get('native_files')==tree(native),'Native fingerprint stale')
 require(r.get('web_files')==tree(web),'Web fingerprint stale')
 baseline=root/r.get('original_zip','missing');require(baseline.is_file(),'Original ZIP missing')
 if baseline.is_file():
  require(sha(baseline)==r.get('original_sha256'),'Original ZIP fingerprint mismatch')
  with zipfile.ZipFile(baseline) as z:
   original={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
  current=tree(native);changed=sorted(n for n in original if current.get(n)!=original[n]);added=sorted(set(current)-set(original))
  require(changed==sorted(r.get('changed_baseline_files',[])),'Unreviewed changed/deleted baseline file')
  require(added==sorted(r.get('added_files',[])),'Unreviewed added Native file')
 for p,h in r.get('maintenance_inputs',{}).items():
  target=root/p;require(target.is_file() and sha(target)==h,'Maintenance source/recipe changed: '+p)
 require(bool(r.get('maintenance_inputs')),'Reproducible patch inputs missing')
 expected_source=hashlib.sha256(json.dumps(r.get('maintenance_inputs',{}),sort_keys=True,separators=(',',':')).encode()).hexdigest()
 def tree_hash(p):return hashlib.sha256(json.dumps(tree(p),sort_keys=True,separators=(',',':')).encode()).hexdigest()
 require(r.get('binding')=={'source_sha256':expected_source,'native_tree_sha256':tree_hash(native),'web_tree_sha256':tree_hash(web),'build_tag':args.build_tag},'Maintenance input/Native/Web binding stale')
 required_checks={'baseline','business','ui','rebuild','persistence'}
 require(set(r.get('checks',{}))==required_checks,'Maintenance checklist missing')
 for name,row in r.get('checks',{}).items():require(row.get('status')=='pass',name+' is not passed')
 with tempfile.TemporaryDirectory(prefix='export-maintenance-rebuild ') as td:
  temp=Path(td)
  for name in ['src','tools','inputs']:shutil.copytree(root/name,temp/name)
  proc=subprocess.run([sys.executable,str(temp/'tools/assemble.py')],capture_output=True,text=True,timeout=60)
  require(proc.returncode==0,'Rebuild recipe failed')
  require(tree(temp/'build/native')==tree(native),'Independent Native rebuild differs')
  require(tree(temp/'build/web')==tree(web),'Independent Web rebuild differs')

 # Independent of written pass flags: rerun actual compiled-function probes.
 runners=[['python3',str(HERE/'run_reward_storage_probe.py'),'--native',str(native),'--web',str(web)],['node',str(root/'test/export-business-regression.cjs')],['node',str(root/'test/runtime-regression.cjs')]]
 for cmd in runners:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=60);require(p.returncode==0,'Executable regression failed: '+str(cmd)+'\n'+p.stderr[-800:])
 for rel in ['test/export-business-regression.json','test/runtime-regression.json']:
  try:
   report=json.loads((root/rel).read_text());require(report.get('passed') is True,rel+' not passed')
  except (OSError,ValueError):errors.append(rel+' missing')
 require(len(json.loads((root/'test/export-business-regression.json').read_text()).get('checks',[]))>=56,'Missing business regression cases')
 ui=r.get('runtime_ui',{})
 require(ui.get('native_bundle_sha256')==sha(native/'assets/main/index.js'),'Runtime UI evidence not bound to actual business bundle')
 require(ui.get('shared_module_sha256')==sha(native/'screw-map70.js'),'Runtime UI shared module fingerprint stale')
 required={'home_no_dead_rank','map_open_close_select','first_level_progress','remove_close_answer_close','free_restart','settings_roundtrip','loading_retry','two_phone_ratios'}
 require(set(ui.get('cases',{}))==required,'Runtime UI case inventory missing')
 for name,row in ui.get('cases',{}).items():
  require(row.get('status')=='pass' and len(row.get('observed',''))>20,name+' not actually observed')
  refs=row.get('evidence',[]);require(bool(refs),name+' evidence missing')
  for ref in refs:
   p=root/ref['path'];require(p.is_file() and sha(p)==ref.get('sha256'),name+' stale evidence')
 for p in list(native.rglob('*.js'))+list(web.rglob('*.js')):
  proc=subprocess.run(['node','--check',str(p)],capture_output=True,text=True);require(proc.returncode==0,'JS syntax: '+str(p))
 return {'tool':'audit_export_maintenance','status':'blocked' if errors else 'passed','passed':not errors,'errors':errors,'scope':'Existing exported-game maintenance and runtime regressions; not full remake acceptance or real TikTok validation'}
