"""Scoped actual Native facade/input and first subpackage Retry observations."""
import hashlib,json
from pathlib import Path
from startup_business_contract import validate_business
PROFILE='dessert_cocos24_facade_retry_v1'

def rows_errors(rows,binding,native=None):
 errors=[]
 if len(rows)!=4:return ['four actual normal/short/recovery/coordinate-negative observations required']
 for index,row in enumerate(rows):
  if row.get('binding')!=binding:errors.append('execution binding mismatch')
  touches=row.get('touch_events',[])
  if any(not t.get('raw')for t in touches):errors.append('raw SDK changed touches missing')
  if not {'touchstart','touchend'}.issubset({t.get('type')for t in touches}):errors.append('SDK start/end missing')
  if len(touches)<2 or not all(t.get('trusted') is True for t in touches):errors.append('trusted SDK input missing')
  if any('clientX' in p or 'clientY'in p or not all(type(p.get(k))in(int,float)for k in ['screenX','screenY']) for t in touches for p in t.get('raw',[])):errors.append('SDK input must use screen-only payloads')
  if index<3:
   if row.get('native_tree_sha256')!=binding['native_tree_sha256'] or row.get('passed')is not True or row.get('errors'):errors.append('positive Native failed')
   errors+=validate_business(row)
  else:
   if row.get('passed')is not False or row.get('failure_observation',{}).get('home_still_visible')is not True or row.get('failure_observation',{}).get('game_absent')is not True or row.get('errors'):errors.append('coordinate negative must reach HOME then fail trusted PLAY without harness exception')
 if rows[0].get('viewport')!=[390,844]or rows[1].get('viewport')!=[360,800]:errors.append('two actual phone ratios required')
 retry=rows[2].get('retry')or{};recovery=rows[2].get('recovery')or{}
 if retry.get('trusted_touch')is not True or not retry.get('errors_before')or not isinstance(retry.get('requests'),int)or recovery.get('requests_after',0)<=retry.get('requests',0):errors.append('actual failed subpackage and trusted Retry fresh request required')
 if not isinstance(retry.get('at_ms'),(int,float))or retry.get('at_ms',float('inf'))>=rows[2].get('business',{}).get('home',{}).get('at_ms',0):errors.append('Retry must precede recovered HOME')
 return errors

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 rows=[data]
 for name in ['short','recovery','negative']:
  p=ref(report.get('controls',{}).get(name,{}),name+' execution')
  if not p:return
  rows.append(json.loads(p.read_text()))
 for error in rows_errors(rows,binding,native):need(False,error)
 for index,row in enumerate(rows):
  root=native if index<3 else Path(row['input_native_root']).resolve()
  need(root.is_relative_to(project),'executed input outside project')
  need(row.get('runner_sha256')==report['runner']['sha256'],'raw runner identity changed')
  need(row.get('native_tree_sha256')==digest(tree(root)),'executed tree identity changed')
  executed=row.get('executed_sources_sha256',{})
  critical=['game.js','main.js','adapter-min.js','cocos/cocos2d-js-min.js','assets/main/index.js']+(['tiktok-touch-bridge.js']if index<3 else [])
  if index==3:need('tiktok-touch-bridge.js'not in executed,'negative must not execute removed facade')
  for name in critical:
   need(executed.get(name)==sha(root/name),'actual executed source changed '+name)
  for phase,name in [('before','cocos/cocos2d-js-min.js'),('after','adapter-min.js')]:
   code=(root/name).read_text()
   for method in ['run','renderer']:
    value=row.get('engine_capture',{}).get(phase,{}).get(method)
    need(isinstance(value,str)and bool(value)and value in code,'original engine/adapter method missing '+phase+'/'+method)
 base=tree(native);negative=tree(Path(rows[3]['input_native_root']));entry=(native/'game.js').read_text();needle="require('./tiktok-touch-bridge')(TTMinis.game)";expected=dict(base);expected['game.js']=hashlib.sha256(entry.replace(needle,'TTMinis.game').encode()).hexdigest()
 need(entry.count(needle)==1 and negative==expected,'coordinate negative must remove only actual facade installation')

def validate_loading(data,binding,base):
 errors=[];rows=[]
 if data.get('producer')!='real_browser_touch_trace'or data.get('binding')!=binding or data.get('execution_binding')!=binding:errors.append('current real loading trace required')
 for ref in data.get('raw_evidence',[]):
  try:
   p=Path(ref['path']);p=p if p.is_absolute()else base/p;p=p.resolve();p.relative_to(base.resolve());raw=p.read_bytes()
   if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('changed raw trace')
   rows.append(json.loads(raw))
  except(Exception)as e:errors.append('loading raw invalid: '+str(e))
 return errors+rows_errors(rows,binding)
