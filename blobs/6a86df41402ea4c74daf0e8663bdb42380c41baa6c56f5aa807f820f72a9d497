"""Exact PLAY-repair dependency bridge for six unchanged registered R17 defects.

Original validate_proof runs against the original frozen execution. Its return and
raw identities are retained. Only the reviewed whole-Native semantic delta plus
current two-phone PLAY recovery proof permits reuse for the successor candidate.
"""
import hashlib,json
from pathlib import Path

IDS=frozenset({'SS-UI-SKILL','SS-UI-LOBBY-HUD','SS-UI-ATLAS-INTEGRITY','SS-UI-TITLES-CONTROLS','SS-UI-POPUP-FIT','SS-UI-REWARD-CARDS'})
MANIFEST=Path('docs/art/locked-maintenance-successor.json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def checked(ref):
    p=Path(ref['path']).resolve()
    if not p.is_file() or sha(p)!=ref.get('sha256'):raise ValueError('PLAY issue successor evidence changed: '+str(p))
    return p

def anchor(project,native):
    import audit_ui_contract as U
    p=Path(project).resolve();n=Path(native).resolve();path=p/MANIFEST;doc=read(path)
    if doc.get('schema')!='user_locked_art_maintenance_successor.v1' or doc.get('project')!=str(p) or doc.get('current_native')!=str(n):raise ValueError('explicit current PLAY successor scope required')
    if U.tree_digest(n)!=doc.get('binding',{}).get('native_tree_sha256'):raise ValueError('PLAY successor Native binding changed')
    prior=doc['predecessor'];scope=read(checked(prior['scope']));old=Path(prior['executed_native']).resolve()
    if scope.get('schema')!='user_locked_art_maintenance.v1' or scope.get('project')!=str(p) or scope.get('native')!=str(old) or U.tree_digest(old)!=scope['binding']['native_tree_sha256']:raise ValueError('original frozen PLAY predecessor Native changed')
    report=read(checked(prior['writer_report']));writer=read(checked(prior['writer_receipt']));archive=checked(prior['zip'])
    if report.get('entry')!='official' or report.get('sha256')!=sha(archive) or writer.get('zip_sha256')!=sha(archive) or writer.get('gate_result',{}).get('passed')is not True:raise ValueError('actual official R17 predecessor required')
    origin=prior['copy_origin']
    if origin['zip'].get('path')!=report.get('archive') or origin['zip'].get('sha256')!=sha(archive) or origin['writer_receipt'].get('path')!=report.get('receipt') or origin['writer_receipt'].get('sha256')!=sha(checked(prior['writer_receipt'])):raise ValueError('baseline copy origin differs from actual original writer records')
    oldissues=report.get('package_obligations',{}).get('reported_issues',{})
    if oldissues.get('passed')is not True or oldissues.get('pending_external_issues'):raise ValueError('old registered issues not closed in actual official writer')
    rows={r['id']:r for r in oldissues['checked_issues']}
    if set(rows)!=IDS or set(scope['issue_ids'])!=IDS:raise ValueError('only the exact original six issue families can reuse this dependency bridge')
    return {'project':p,'native':n,'doc':doc,'scope':scope,'old_native':old,'old_rows':rows,'manifest_sha256':sha(path)}

def prepare(context):
    import importlib.util
    import locked_art_maintenance as L
    import startup_play_successor as S
    doc=context['doc'];semantic=doc['semantic_delta'];n=context['native']
    guard_path=(Path(L.__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts/play_art_delta_guard.py').resolve()
    if guard_path!=checked(semantic['tool_record']):raise ValueError('reviewed final PLAY semantic guard location differs')
    spec=importlib.util.spec_from_file_location('_final_play_art_delta_guard',guard_path)
    D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
    if Path(S.__file__).resolve()!=checked(doc['play_checker']):raise ValueError('reviewed current PLAY checker changed')
    files={p.relative_to(n).as_posix():p.read_bytes() for p in n.rglob('*') if p.is_file()}
    delta=D.validate(checked(doc['predecessor']['zip']),files,checked(semantic['adapter']),checked(semantic['scope']))
    if delta!=read(checked(semantic['proof'])):raise ValueError('PLAY semantic delta proof stale')
    current=S.validate_current_play_report(context['project'],n,doc['current_play_proof'])
    context.update(delta=delta,current_play=current)
    return context

def validate(project,contract,ref,native,original_validator,context=None):
    """Return (unaltered original proof, explicit reuse record, reusable audit context)."""
    issue_id=contract.get('id')
    if issue_id not in IDS:raise ValueError('this issue has no exact PLAY dependency successor bridge')
    # One audit invocation caches only after exact candidate/context identity is
    # established. The original validator still checks each original proof fully.
    ctx=context if context is not None else anchor(project,native)
    if ctx['project']!=Path(project).resolve() or ctx['native']!=Path(native).resolve():raise ValueError('successor audit context belongs to another candidate')
    if ref!=ctx['old_rows'][issue_id]['proof']:raise ValueError('old original registered proof was replaced')
    proof=original_validator(contract,ref,ctx['old_native'])
    if sorted(proof['cases'])!=ctx['scope']['issue_cases'][issue_id] or proof['executed_native_roots']['current']!=str(ctx['old_native']):raise ValueError('old actual case coverage/execution identity differs')
    if 'delta' not in ctx:ctx=prepare(ctx)
    current_targets={name:sha(ctx['native']/name) for name in contract['targets']}
    reuse={'mode':'exact_PLAY_semantic_delta_with_current_recovery','semantic_dependency_reused':True,'dependency_bytes_reused':False,
           'scope_manifest_sha256':ctx['manifest_sha256'],'original_executed_native_root':proof['executed_native_roots']['current'],
           'original_target_sha256':proof['target_sha256'],'current_target_sha256':current_targets,
           'semantic_delta':ctx['doc']['semantic_delta']['proof'],'current_play_report':ctx['doc']['current_play_proof'],
           'boundary':'Original execution and raw observations retained; current target bytes are distinct and checked by the exact semantic guard and actual current PLAY recovery. No replay or new observation claimed for these old cases.'}
    return proof,reuse,ctx
