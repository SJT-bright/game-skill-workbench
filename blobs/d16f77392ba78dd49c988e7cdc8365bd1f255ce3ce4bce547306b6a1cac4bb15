"""Executable review for PaperCutKid's exported Cocos2 production modules.
Requires unchanged original gameplay assets, exact rebuild, live touch evidence,
calibrated storage failures and replayed business/loading/Native-adapter checks.
"""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,shutil,zipfile
from audit_packed_assets import audit as assets_audit

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(Path(p).rglob('*')) if f.is_file()}
def hashj(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
REQUIRED={'baseline','rebuild','assets','persistence','loading','platform','ui','LOAD-03'}
def audit(args):
 root=args.project.resolve();native=args.native.resolve();web=args.web.resolve();review=json.loads(args.review.read_text());errors=[]
 def require(ok,message):
  if not ok:errors.append(message)
 def readref(ref):
  p=Path(ref.get('path',''));p=p if p.is_absolute() else root/p
  if not p.is_file() or sha(p)!=ref.get('sha256'):raise ValueError('missing/stale evidence '+str(p))
  return p
 try:
  require(review.get('game_id')=='paper-cut-kid' and review.get('schema')=='export_maintenance_review.v1','unsupported export identity')
  require(review.get('input_kind')=='existing_native_export' and review.get('authorization')=='maintain_only_available_export','export maintenance authorization')
  require(review.get('build_tag')==args.build_tag,'build tag changed')
  baseline=readref(review['original_zip']);require(sha(baseline)==review['original_sha256'],'baseline changed')
  with zipfile.ZipFile(baseline) as z:
   baseline_files={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
  ns,ws=tree(native),tree(web);require(ns==review['native_files'] and ws==review['web_files'],'final runtime files changed')
  changed=sorted(n for n,h in baseline_files.items() if ns.get(n)!=h);added=sorted(set(ns)-set(baseline_files))
  require(changed==review['changed_baseline_files'] and added==review['added_files'],'unreviewed file delta')
  require(all(n in {'main.js','game.js','assets/main/index.js'} or n.startswith('preview-ui/') for n in changed),'original level/scene/audio/engine/adapter assets changed')
  inputs=review['maintenance_inputs'];require(bool(inputs),'maintenance sources missing')
  for n,h in inputs.items():require((root/n).is_file() and sha(root/n)==h,'maintenance source changed: '+n)
  binding={'source_sha256':hashj(inputs),'native_tree_sha256':hashj(ns),'web_tree_sha256':hashj(ws),'build_tag':args.build_tag}
  require(binding==review['binding'],'review fingerprint stale')
  require(set(review.get('checks',{}))==REQUIRED,'review incomplete')
  for n,row in review.get('checks',{}).items():
   require(row.get('status')=='pass',n+' not passed')
   for ref in row.get('evidence',[]):readref(ref)
   require(bool(row.get('evidence')),n+' evidence missing')
  with tempfile.TemporaryDirectory(prefix='papercut exact rebuild ') as tmp:
   tmp=Path(tmp)
   for n in ['src','tools','inputs']:shutil.copytree(root/n,tmp/n)
   result=subprocess.run([sys.executable,str(tmp/'tools/assemble.py')],capture_output=True,text=True,timeout=90)
   require(result.returncode==0,'independent build failed')
   require(tree(tmp/'build/native')==ns and tree(tmp/'build/web')==ws,'independent rebuilt bytes differ')
  require(assets_audit(native)['passed'],'packed asset references or atlas fingerprints failed')
  for layer,folder in [('source',root/'src/native'),('native',native),('web',web)]:
   for name in ['storage','platform','boot','guard','settings','codec']:
    cmd=['node',str(root/f'test/{name}-regression.cjs'),str(folder)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    require(p.returncode==0,'actual '+layer+' '+name+' regression failed: '+p.stdout[-500:]+p.stderr[-300:])
    result=json.loads(p.stdout);require(result.get('passed') is True and bool(result.get('checks')),'empty regression '+name)
  codec=json.loads(readref(review['checks']['LOAD-03']['evidence'][0]).read_text())
  require(len(codec.get('results',[]))==135 and all(x.get('decoded') is True for x in codec.get('results',[])),'original texture decode evidence missing')
  contract=review['storage_contract']
  for name in ['current','negative']:
   rec=contract[name];bundle=readref(rec['bundle']);adapter=readref(rec['adapter']);raw=readref(rec['raw']);runner=readref(contract['runner'])
   p=subprocess.run(['node',str(runner),str(bundle),str(adapter)],capture_output=True,text=True,timeout=60)
   result=json.loads(p.stdout);require(p.returncode==0 and result==json.loads(raw.read_text()),'storage-contract replay changed '+name)
   require(result['runner_sha256']==sha(runner) and result['bundle_sha256']==sha(bundle) and result['adapter_sha256']==sha(adapter),'storage execution identity '+name)
   from audit_native_storage_contract import CASES
   require(set(result['cases'])==set(CASES),'storage matrix missing')
   for n,status in result['cases'].items():
    expected='not_applicable' if n=='reopen_stage_details' else 'fail' if name=='negative' and n=='missing_empty_string' else 'pass'
    require(status==expected,name+' storage case '+n+' '+status)
  original=readref(contract['negative']['base_bundle']);negative=readref(contract['negative']['bundle']);before,after=contract['negative']['patch']
  require(original.read_bytes().count(before.encode())==1 and original.read_bytes().replace(before.encode(),after.encode(),1)==negative.read_bytes(),'negative control not exact documented defect')
  require(bool(review['runtime_ui']),'current GUI evidence missing')
  for ratio in ['long','short']:
   raw=json.loads(readref(review['runtime_ui'][ratio]).read_text());require(raw['viewport']==([390,844] if ratio=='long' else [375,667]),'viewport mismatch')
   require(raw['native_bundle_sha256']==sha(native/'assets/main/index.js'),'GUI bundle stale')
   require(raw['web_main_sha256']==sha(web/'main.js'),'GUI loader stale')
   require(raw['end']['errors']==[] and any(x.get('trusted') for x in raw['touches']),'GUI errors/untrusted touch')
   require(raw['routes']['home']['reopen'] and raw['routes']['home']['recovery'] and raw['routes']['map']['reopen'] and raw['routes']['map']['recovery'],'actual route reopen/recovery missing')
   for ref in raw['screenshots']:readref(ref)
   recovery=json.loads(readref(review['loading_ui'][ratio]).read_text())
   require(recovery['native_bundle_sha256']==sha(native/'assets/main/index.js') and recovery['web_main_sha256']==sha(web/'main.js'),'loading execution stale')
   require(recovery['ready']['ready'] is True and recovery['failed']['boot']['ready'] is False,'failure to ready missing')
   require(len(recovery['server_events'])>=2 and recovery['server_events'][0]['held'] is True and recovery['server_events'][1]['held'] is False,'same image transport retry not proved')
   require(any(x.get('trusted') for x in recovery['touches']),'loading retry/input untrusted')
   require(len(recovery['rounds'])==3 and all(x['before']['cuts']==3 and x['after']['cuts']==2 for x in recovery['rounds']),'three playable restarts missing')
  if args.stage=='post_package':
   from verify_native_zip import verify
   delivery=review['delivery'];archive=readref(delivery['zip']);report=json.loads(readref(delivery['report']).read_text());refusal=json.loads(readref(delivery['refusal']).read_text())
   actual=verify(archive,'7683427172773644296')
   require(actual['file_sha256']==ns,'final ZIP differs from reviewed Native')
   require(report.get('tool')=='make_tiktok_zip' and report.get('passed') is True,'not produced by formal writer')
   require(refusal.get('passed') is True and refusal.get('review_restored') is True,'writer refusal control missing')
   require(refusal.get('binding')==binding,'writer control stale')
   require(delivery.get('missing_storage_refused') is True,'missing storage contract not proved refused')
 except (KeyError,ValueError,OSError,TypeError,subprocess.SubprocessError,zipfile.BadZipFile) as error:errors.append('invalid maintenance review: '+str(error))
 return {'tool':'audit_papercut_export_maintenance','passed':not errors,'status':'passed' if not errors else 'blocked','errors':errors,'boundary':'compiled production modules, controlled Native/SDK and real browser touch; no physical device/real IAA/platform acceptance'}
