"""Cocos 2.4 actual converter + real Native renderer, with exact entry negative."""
import hashlib,json,zipfile
from pathlib import Path

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 def source_check(raw,root,label):
  state=raw.get('after') or raw.get('afterPlay') or raw.get('initial') or raw
  observed=state.get('executed_sources_sha256',{})
  for name in ['game.js','main.js','adapter-min.js','cocos/cocos2d-js-min.js','assets/main/index.js']:
   need(observed.get(name)==sha(root/name),label+' executed production source differs: '+name)
  capture=state.get('engine_capture',{})
  for phase,source in [('before',root/'cocos/cocos2d-js-min.js'),('after',root/'adapter-min.js')]:
   code=source.read_text()
   for name in ['run','renderer']:
    value=capture.get(phase,{}).get(name)
    need(isinstance(value,str) and bool(value) and value in code,label+' original/adapter function identity missing: '+phase+'/'+name)
  return state
 source_check(data,native,'normal')
 for label in ['known_bad','reintroduced_defect']:
  path=ref(report.get('controls',{}).get(label,{}),label+' actual screen-coordinate negative')
  if not path:continue
  raw=json.loads(path.read_text());root=Path(raw['input_native_root']).resolve()
  need(root.is_relative_to(project),label+' Native outside project')
  actual=tree(root);need(digest(actual)==raw.get('native_tree_sha256'),label+' Native changed')
  state=source_check(raw,root,label)
  need(raw.get('passed') is False and not raw.get('harness_error') and raw.get('failure_kind')=='screen-coordinates-no-gameplay',label+' must reproduce real input failure, not collection error')
  need(raw.get('initial',{}).get('phase')=='home' and state.get('phase')=='home' and state.get('engine',{}).get('status')=='ready',label+' must reach real HOME and fail the delivered PLAY input')
  events=raw.get('playTouch',{}).get('events',[])
  need(len(events)==2 and all(e.get('trusted') is True for e in events),label+' trusted start/end required')
  for event in events:
   for touch in event.get('event',{}).get('changedTouches',[]):
    need('clientX' not in touch and 'clientY' not in touch and all(type(touch.get(k)) in (int,float) for k in ['screenX','screenY']),label+' must use actual screen-only SDK shape')
  need(raw.get('runner_sha256')==report['runner']['sha256'],label+' reviewed runner mismatch')
  if label=='known_bad':
   archive=ref(raw.get('source_zip',{}),'preserved known-bad ZIP')
   if archive:
    with zipfile.ZipFile(archive) as z:original={i.filename:hashlib.sha256(z.read(i)).hexdigest() for i in z.infolist() if not i.is_dir()}
    need(actual==original,'known-bad must equal the preserved delivered ZIP')
  else:
   before=tree(native);entry=(native/'game.js').read_text();line=" require('./touch-coordinates').install(cc);\n"
   need(entry.count(line)==1,'current entry must install the coordinate adapter exactly once')
   expected=dict(before);expected['game.js']=hashlib.sha256(entry.replace(line,'').encode()).hexdigest()
   need(actual==expected,'reintroduced defect must remove only the real pre-input coordinate installation')
