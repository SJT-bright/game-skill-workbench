"""Actual Cocos 2.4 image-stall controls, including original ZIP and one-file regression."""
import json,hashlib,zipfile
from pathlib import Path

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 def sources(raw,root,label):
  observed=raw.get('executed_sources_sha256',{})
  for p in ['game.js','adapter.js','cocos/cocos2d-js.js','main.js','assets/main/index.js']:
   need(observed.get(p)==sha(root/p),label+' executed source differs: '+p)
 sources(data,native,'normal')
 for name in ['known_bad','reintroduced_defect']:
  path=ref(report.get('controls',{}).get(name,{}),name+' image-stall control')
  if not path:continue
  raw=json.loads(path.read_text());f=raw.get('failure_observation',{})
  need(raw.get('passed') is False and f.get('home_visible') is False and f.get('retry_visible') is False and f.get('image_response_held') is True and f.get('observed_ms',0)>=10000,name+' did not reproduce real image-stall/no-Retry failure')
  need(raw.get('runner_sha256')==report['runner']['sha256'],name+' runner differs')
  need(raw.get('browser_canvas')==data.get('browser_canvas') and raw.get('viewport')==data.get('viewport') and raw.get('touch')==data.get('touch'),name+' device/calibration differs')
  root=Path(raw['input_native_root']).resolve();need(root.is_relative_to(project),name+' input outside registered project')
  manifest=tree(root);need(digest(manifest)==raw.get('native_tree_sha256'),name+' input bytes changed');sources(raw,root,name)
  if name=='known_bad':
   zpath=ref(raw.get('source_zip',{}),'original ZIP')
   if zpath:
    with zipfile.ZipFile(zpath) as z:original={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
    need(manifest==original,'known-bad must be exact original ZIP')
  else:
   base=tree(native);m=raw.get('mutation',{})
   need(raw.get('base_native_tree_sha256')==digest(base),'regression base changed')
   need(m.get('file')=='main.js' and m.get('base_sha256')==base['main.js'] and m.get('mutated_sha256')==manifest['main.js'] and base['main.js']!=manifest['main.js'],'exact main.js callback regression required')
   need({k:v for k,v in base.items() if k!='main.js'}=={k:v for k,v in manifest.items() if k!='main.js'},'regression changed unrelated files')
   known_path=ref(report['controls']['known_bad'],'original callback source');known=json.loads(known_path.read_text()) if known_path else {}
   old=Path(known.get('input_native_root',''))/'main.js'
   need(old.is_file() and sha(old)==manifest['main.js'],'regression must restore original broken callback source')
