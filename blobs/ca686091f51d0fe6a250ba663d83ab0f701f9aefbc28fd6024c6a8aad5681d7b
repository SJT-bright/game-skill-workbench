"""RunHome actual Cocos 2.4-min renderer contract.
Independent profile: never changes another project's control assumptions.
Recovery scenarios remain governed by audit_loading_recovery, not waived here.
"""
import json
from pathlib import Path

CORE=('game.js','main.js','adapter-min.js','cocos/cocos2d-js-min.js','assets/main/index.js','native-startup-guard.js')

def validate(report,native,binding,project,data,need,ref):
 from audit_native_startup_renderer import tree,digest,sha
 def sources(raw,root,label):
  observed=raw.get('executed_sources_sha256',{})
  need(isinstance(observed,dict),label+' executed-source map missing')
  for name in CORE:
   p=root/name
   need(p.is_file() and p.stat().st_size>0 and observed.get(name)==sha(p),label+' actual source mismatch: '+name)
  engine=root/CORE[3];adapter=root/CORE[2]
  need(engine.is_file() and engine.stat().st_size>1000000,label+' actual engine is empty/replaced')
  need(adapter.is_file() and adapter.stat().st_size>10000,label+' actual adapter is empty/replaced')
 need(set(report)=={'schema','producer','binding','native_tree_sha256','control_profile','execution','runner','raw','inputs','screenshot','controls'},'RunHome report has unknown/missing fields')
 need(set(report.get('controls',{}))=={'known_bad','normal'},'RunHome controls have unknown/missing cases')
 sources(data,native,'startup')
 for name in ('native-touch-coordinates.js','touch-coordinates.js','native-request-lifecycle.js'):
  p=native/name
  need(p.is_file() and data.get('executed_sources_sha256',{}).get(name)==sha(p),'RunHome actual bridge source missing/changed: '+name)
 need(report.get('control_profile')=='runhome_native_recovery_v1','RunHome profile required')
 # The actual normal input must preserve the Native field mismatch being tested.
 touches=data.get('native_screen_only_touch',{})
 need(touches.get('sdk_event_has_client_coordinates') is False and touches.get('sdk_event_has_screen_coordinates') is True and touches.get('trusted_dom_touch') is True,'RunHome actual trusted screen-only SDK input missing')
 need(data.get('commonjs_entry_executed') is True,'RunHome actual CommonJS entry not executed')
 for name in ('known_bad','normal'):
  path=ref(report.get('controls',{}).get(name,{}),name+' RunHome stencil control')
  if path is None:continue
  try:
   raw=json.loads(path.read_text());root=Path(raw['input_native_root']).resolve()
   need(root.is_relative_to(project) and root.is_dir(),name+' control outside project/missing')
   need(raw.get('native_tree_sha256')==digest(tree(root)),name+' control Native bytes changed')
   sources(raw,root,name)
   need(raw.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' different runner')
   need(raw.get('browser_canvas')==data.get('browser_canvas') and raw.get('viewport')==data.get('viewport') and raw.get('touch')==data.get('touch'),name+' actual device/Canvas calibration differs')
   o=raw.get('observed',{})
   if name=='known_bad':
    need(raw.get('native_tree_sha256')!=binding['native_tree_sha256'] and raw.get('passed') is False and bool(raw.get('errors')),'known_bad must be actual distinct failed Native')
    need(o.get('stencilBits')==0 and o.get('map_visible') is False and o.get('hero_visible') is False,'known_bad did not reproduce actual zero-stencil white gameplay')
   else:
    need(root==native and raw.get('binding')==binding and raw.get('passed') is True and not raw.get('errors'),'normal control must pass exact candidate')
    need(type(o.get('stencilBits')) is int and o['stencilBits']>=8 and o.get('draw_calls',0)>0 and o.get('map_visible') is True and o.get('hero_visible') is True and o.get('home_visible') is True and o.get('play_effect_observed') is True,'normal actual stencil/render/HOME/PLAY control missing')
  except (KeyError,TypeError,ValueError,OSError):need(False,name+' RunHome control invalid')
