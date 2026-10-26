"""Exact controlled-Native startup negatives for the registered TankAce runner.
This profile supplements, never replaces, the common HOME/actual-input contract.
"""
import hashlib,json,zipfile
from pathlib import Path

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 need(report.get('diagnostic_only') is False,'TankAce diagnostic-only renderer report is not a final proof')
 need(report.get('execution',{}).get('registered_runner')=='tankace-real-native-renderer-v1','TankAce registered executor mismatch')
 def module(source,name):
  a=source.index('],'+name+':[function')+2;b=source.index('}],',a)+3
  return a,b,source[a:b]
 from startup_business_contract import validate_business
 positive_path=ref(report.get('positive_controls',{}).get('minis_only',{}),'TTMinis-only actual positive control')
 positive={}
 if positive_path:
  try:positive=json.loads(positive_path.read_text())
  except (ValueError,OSError):need(False,'TTMinis-only raw result invalid')
 for label,raw in [('tt-only',data),('TTMinis-only',positive)]:
  need(raw.get('passed') is True and not raw.get('errors') and not raw.get('first_exception'),label+' real startup must succeed cleanly')
  need(raw.get('binding')==binding and raw.get('native_tree_sha256')==digest(tree(native)) and raw.get('runner_sha256')==report.get('runner',{}).get('sha256'),label+' final Native/executor binding mismatch')
  need(raw.get('engine_identity')==data.get('engine_identity') and raw.get('phase_order')==['entry','adapter','renderer','scene'] and raw.get('renderer',{}).get('webgl_context') is True,label+' original adapter/engine/renderer identity required')
  executed=ref(raw.get('input_manifest',{}),label+' actual Native manifest')
  if executed:need(json.loads(executed.read_text())==tree(native),label+' actual Native manifest mismatch')
  for error in validate_business(raw):need(False,label+' '+error)
  if any(p.suffix.lower()=='.webp' for p in native.rglob('*') if p.is_file()):
   codec=raw.get('codec',{});requests=codec.get('probe_requests',[])
   need(codec.get('webp_capability') is True and any(q.get('boundary')=='image' and q.get('path')=='startup/webp-decode.webp' and any(e.get('event')=='success' and e.get('width')==2 and e.get('height')==2 for e in q.get('events',[])) for q in requests),label+' actual SDK Image WebP decoding is required')
 original_root=project/'native-original'
 zip_path=project/'inputs/TankAce-original.zip'
 need(zip_path.is_file(),'TankAce preserved original ZIP required')
 original=tree(original_root);base=tree(native)
 if zip_path.is_file():
  with zipfile.ZipFile(zip_path) as z:
   archive={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
  need(original==archive,'TankAce preserved Native differs from original ZIP')
 for name,kind in [('known_bad','optional_sdk_startup_exception'),('reintroduced_defect','optional_sdk_startup_exception'),('parser_type_mismatch','native_parser_type_mismatch'),('canvas_context_conflict','canvas_context_conflict')]:
  proof=ref(report.get('controls',{}).get(name,{}),name+' actual execution');control={}
  if proof:
   try:control=json.loads(proof.read_text())
   except (ValueError,OSError):need(False,name+' invalid raw result')
  need(control.get('passed') is False and bool(control.get('errors')),name+' must actually fail')
  need(control.get('failure_kind')==kind,name+' failure kind mismatch')
  need(control.get('binding')==binding and control.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' runner/current-base binding mismatch')
  need(control.get('browser_canvas')==data.get('browser_canvas'),name+' different real Canvas calibration')
  manifest_path=ref(control.get('input_manifest',{}),name+' executed Native manifest');manifest={}
  if manifest_path:
   try:manifest=json.loads(manifest_path.read_text())
   except (ValueError,OSError):need(False,name+' executed Native manifest invalid')
  expected=dict(original if name=='known_bad' else base)
  if name=='known_bad':
   provenance=control.get('provenance',{})
   need(provenance.get('kind')=='preserved_original_export' and provenance.get('tree_sha256')==digest(original),'TankAce original provenance mismatch')
  else:
   need(control.get('base_native_tree_sha256')==digest(base),name+' does not derive from current Native')
   mutation=control.get('mutation',{})
   if name=='reintroduced_defect':
    file='assets/start-scene/index.js';source=(native/file).read_text();old=(original_root/file).read_text()
    for mod in ['RewardAd','TTRewardAd']:
     a,b,_=module(source,mod);_,_,text=module(old,mod);source=source[:a]+text+source[b:]
    expected[file]=hashlib.sha256(source.encode()).hexdigest()
   elif name=='parser_type_mismatch':
    file='assets/main/import/09/095e595fb.json';expected[file]=hashlib.sha256(b'0').hexdigest()
   else:
    file='main.js';expected[file]=hashlib.sha256(b'window.canvas.getContext("2d");\n'+(native/file).read_bytes()).hexdigest()
   need(mutation.get('file')==file and mutation.get('base_sha256')==base[file] and mutation.get('mutated_sha256')==expected[file],name+' exact mutation SHA mismatch')
  need(manifest==expected,name+' executed Native is not the exact original/current-base mutation')
  need(control.get('native_tree_sha256')==digest(expected) and digest(expected)!=digest(base),name+' Native identity mismatch')
  errors=json.dumps(control.get('errors',[]))
  if kind=='optional_sdk_startup_exception':
   need('createRewardedVideoAd' in errors and ('not a function' in errors or 'undefined' in errors),name+' does not reproduce the actual missing optional SDK API exception')
   need(control.get('renderer',{}).get('webgl_context') is True,name+' must reach original Native renderer')
  elif kind=='native_parser_type_mismatch':
   need(control.get('renderer',{}).get('webgl_context') is True and any(x in errors.lower() for x in ['unpack','package data','property','invalid']),name+' actual post-renderer scene parser error missing')
  else:
   contexts=control.get('contexts',[])
   need(any(x.get('sharedScreen') and x.get('type')=='2d' and x.get('returned') for x in contexts) and not control.get('renderer',{}).get('webgl_context'),name+' must demonstrate actual shared Canvas context exclusion')
