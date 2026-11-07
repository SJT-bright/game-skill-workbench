"""Exact in-game name visibility successor; original art/runtime identities stay original."""
import hashlib,json
from pathlib import Path
MANIFEST=Path('docs/art/debrand-successor.json')
SCHEMA='user_locked_debrand_successor.v1'
IDS=frozenset({'SS-UI-SKILL','SS-UI-LOBBY-HUD','SS-UI-ATLAS-INTEGRITY','SS-UI-TITLES-CONTROLS','SS-UI-POPUP-FIT','SS-UI-REWARD-CARDS','SS-PLAY-IMAGE'})
SCENE='assets/scenes/Main.scene'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def checked(ref):
 p=Path(ref['path']).resolve()
 if not p.is_file()or sha(p)!=ref.get('sha256'):raise ValueError('debrand evidence missing/changed: '+str(p))
 return p

def common(project,native,doc):
 import locked_art_maintenance as L
 import art_receipt as A
 import art_production as AP
 import audit_value_presentation as V
 import audit_ui_contract as U
 import debrand_startup_successor as T
 project=Path(project).resolve();native=Path(native).resolve()
 if doc.get('schema')!=SCHEMA or doc.get('project')!=str(project)or doc.get('current_native')!=str(native):raise ValueError('exact debrand project/schema/Native scope required')
 if Path(T.__file__).resolve()!=checked(doc['checker']):raise ValueError('canonical debrand checker changed')
 prior=doc['predecessor'];oldscopefile=checked(prior['art_scope']);old=read(oldscopefile);validation=read(checked(prior['art_validation']))
 if old.get('schema')!='user_locked_art_maintenance_successor.v1'or old.get('project')!=str(project)or validation.get('state')!='user_locked_art_maintenance_successor'or validation.get('manifest_sha256')!=sha(oldscopefile)or validation.get('full_art_verdict')!='not_established_by_this_scope':raise ValueError('actual prior R18 scoped art validation required; no invented full-art pass')
 before=read(checked(old['source_comparison']))['current_assets'];after=L.assets(project);delta=L.actual_diff(before,after)
 if set(delta)-{'assets/.DS_Store'}!={SCENE}or delta!=doc.get('source_increment'):raise ValueError('debrand changes exceed exactly one scene and explicit Finder metadata')
 original=checked(prior['original_scene'])
 if sha(original)!=before[SCENE]:raise ValueError('retained scene is not the actual R18 source bytes')
 a=read(original);b=read(project/SCENE)
 if a[27].get('_name')!='logo'or a[27].get('_active')is not True or b[27].get('_active')is not False:raise ValueError('original/hidden logo source state differs')
 b[27]['_active']=True
 if a!=b:raise ValueError('source differs beyond one logo active boolean')
 oldfp={r:h for r,h in before.items()if Path(r).suffix.lower()in V.SUFFIXES and not V.SKIP.intersection(Path(r).parts)}
 if hashlib.sha256(json.dumps(oldfp,sort_keys=True).encode()).hexdigest()!=old['binding']['source_sha256']:raise ValueError('actual original R18 source inventory fingerprint differs')
 images=A.image_fingerprints(project);display=A.display_fingerprints(project);restored=dict(display);restored['layout:'+SCENE]=A._layout_digest(original.read_bytes())
 if images!=old['binding']['images']or restored!=old['binding']['display']or AP.fingerprint(project)!=old['binding']['production']:raise ValueError('debrand cannot authorize changed artwork, other display fields or recipes')
 actual={'images':images,'display':display,'source_sha256':V.source_fingerprint(project),'production':AP.fingerprint(project),'native_tree_sha256':U.tree_digest(native)}
 if actual!=doc.get('binding'):raise ValueError('actual current debrand source/display/Native binding changed')
 oldnative=Path(prior['native']).resolve()
 if str(oldnative)!=old['current_native']or U.tree_digest(oldnative)!=old['binding']['native_tree_sha256']:raise ValueError('original R18 execution Native changed/rebound')
 # One common checker revalidates exact new source/whole-Native delta, unchanged
 # original PLAY source/native predicates in its explicit historical read view,
 # original 26 assertions and S789 on original R18, then actual current normal.
 envelopefile=checked(doc['startup_envelope']);envelope=read(envelopefile)
 if Path(envelope['native_root']).resolve()!=native:raise ValueError('debrand startup envelope belongs to another Native')
 shared=T.validate_loading_successor(envelope,envelope['binding'],project)
 if shared['predecessor_binding']['native_tree_sha256']!=old['binding']['native_tree_sha256']:raise ValueError('historical startup/art predecessor differs')
 return {'schema':'user_locked_debrand_common.checked.v1','old_art_scope':prior['art_scope'],'old_art_validation':prior['art_validation'],'old_native':str(oldnative),'source_increment':delta,'shared':shared,'historical_art_status':validation['historical_art_status'],'native_tree_sha256':actual['native_tree_sha256'],'boundary':'Original R18 art/PLAY and original R17 executions retain their identities. Only actual R19 logo-hidden/normal observations are current.'}

def validate(project,receipt=None,manifest=None):
 project=Path(project).resolve();location=Path(manifest).resolve()if manifest else project/MANIFEST;doc=read(location)
 result=common(project,doc['current_native'],doc)
 return {'state':'user_locked_debrand_successor','manifest':str(location),'manifest_sha256':sha(location),'historical_art_status':result['historical_art_status'],'full_art_verdict':'not_established_by_this_scope','native_tree_sha256':result['native_tree_sha256'],'exact_scope':result,'boundary':'Only the original loading-name node was hidden by exact source/whole-Native proof and actual two-size startup/normal evidence. No full-art, platform or new historical execution claim.'}
