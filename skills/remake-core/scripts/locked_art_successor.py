"""Read-only successor to a real user-locked maintenance scope.

The predecessor keeps its original Native/raw identities. Reuse is conditional on
an exact reviewed semantic delta guard and actual current affected-state proof;
no global art verdict is created and no old proof/receipt is rewritten.
"""
import hashlib,json
from pathlib import Path

MANIFEST=Path('docs/art/locked-maintenance-successor.json')
SCHEMA='user_locked_art_maintenance_successor.v1'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def checked(ref):
    if not isinstance(ref,dict) or not isinstance(ref.get('path'),str):raise ValueError('pinned successor evidence reference required')
    p=Path(ref['path']).resolve()
    if not p.is_file() or sha(p)!=ref.get('sha256'):raise ValueError('successor evidence missing or changed: '+str(p))
    return p

def predecessor(project,doc):
    import locked_art_maintenance as L
    import art_receipt as A
    import art_production as AP
    import audit_value_presentation as V
    import audit_ui_contract as U
    import package_issue_gate as I
    project=Path(project).resolve()
    if doc.get('schema')!=SCHEMA or doc.get('project')!=str(project):raise ValueError('successor project/schema mismatch')
    anchor=doc['predecessor'];scope_path=checked(anchor['scope']);scope=read(scope_path)
    if scope.get('schema')!=L.SCHEMA or scope.get('project')!=str(project):raise ValueError('actual predecessor locked scope required')
    old_validation=read(checked(anchor['scope_validation']))
    if (old_validation.get('state')!='user_locked_art_maintenance' or old_validation.get('manifest_sha256')!=sha(scope_path) or
        old_validation.get('full_art_verdict')!='not_established_by_this_scope'):
        raise ValueError('predecessor validation identity changed or misrepresented as full ART pass')
    L.approved_event(scope['approval'])
    historical=checked(scope['historical_receipt'])
    if historical!=A.receipt_path(project).resolve():raise ValueError('historical art receipt location changed')
    for ref in scope.get('historical_reports',[]):checked(ref)
    source_path=checked(anchor['source_comparison'])
    if anchor['source_comparison']!=scope['source_comparison']:raise ValueError('predecessor source inventory differs from original locked scope')
    before=read(source_path)['current_assets'];after=L.assets(project);increment=L.actual_diff(before,after)
    if increment!=doc.get('source_increment'):raise ValueError('actual successor source increment differs from exact declared scope')
    # The play-specific semantic guard checks the precise allowed transformation;
    # here the complete tree must also equal the previous source plus that delta.
    expected={'assets/res/layer/MainLayer.prefab','assets/scripts/english/EnglishUI.ts'}
    # v4 repairs one observed late HomeLayer callback after all optional images
    # release. The shared semantic guard must prove the exact null-node check;
    # no other source file or HomeLayer behavior is authorized by this revision.
    if doc.get('repair_revision') == 'v4-three-source':
        expected.add('assets/scripts/game/compoment/layer/HomeLayer.ts')
    elif doc.get('repair_revision') not in (None, 'v2-two-source', 'v3-two-source'):
        raise ValueError('unsupported exact PLAY repair revision')
    if set(increment)-{'assets/.DS_Store'}!=expected:raise ValueError('successor source changes exceed its exact PLAY repair revision and explicit Finder metadata')
    finder={k:v for k,v in increment.items() if k=='assets/.DS_Store'}
    if finder!=doc.get('nonrendering_increment',{}):raise ValueError('Finder metadata delta must be listed honestly')
    if set(doc.get('before_source',{}))!=expected:raise ValueError('both original source files required')
    for rel,ref in doc['before_source'].items():
        if sha(checked(ref))!=before.get(rel):raise ValueError('before-source bytes do not match predecessor inventory: '+rel)
    # Reconstruct the original source fingerprint from its original per-file
    # inventory rather than substituting new source into an old report.
    fp={rel:digest for rel,digest in before.items() if Path(rel).suffix.lower() in V.SUFFIXES and not V.SKIP.intersection(Path(rel).parts)}
    if hashlib.sha256(json.dumps(fp,sort_keys=True).encode()).hexdigest()!=scope['binding']['source_sha256']:
        raise ValueError('predecessor source fingerprint does not match its real inventory')
    changed,_,_=L.source_comparison(project,doc['source_comparison'])
    if set(changed)-set(read(source_path)['changed_assets'])!=expected:
        raise ValueError('successor R14 comparison gained undeclared production changes')
    binding=doc['binding']
    actual={'images':A.image_fingerprints(project),'display':A.display_fingerprints(project),
            'source_sha256':V.source_fingerprint(project),'production':AP.fingerprint(project)}
    if any(binding.get(k)!=v for k,v in actual.items()):raise ValueError('successor current images/display/source/production binding changed')
    if actual['images']!=scope['binding']['images'] or actual['production']!=scope['binding']['production']:
        raise ValueError('PLAY recovery successor cannot authorize changed artwork or production recipes')
    display_changed=A.diff(scope['binding']['display'],actual['display'])
    allowed={'layout:assets/res/layer/MainLayer.prefab','code-text:assets/scripts/english/EnglishUI.ts'}
    if any(key not in allowed for group in display_changed for key in group):raise ValueError('display changes extend beyond exact guarded PLAY files')
    old_native=Path(anchor['executed_native']).resolve()
    if str(old_native)!=scope['native'] or U.tree_digest(old_native)!=scope['binding']['native_tree_sha256'] or anchor['native_tree_sha256']!=scope['binding']['native_tree_sha256']:
        raise ValueError('original executed Native changed or was rebound')
    archive=checked(anchor['zip']);receipt=read(checked(anchor['writer_receipt']));writer=read(checked(anchor['writer_report']))
    if (receipt.get('tool')!='build_checked_zip' or receipt.get('zip_sha256')!=sha(archive) or receipt.get('gate_result',{}).get('passed') is not True or
        writer.get('sha256')!=sha(archive) or writer.get('status')!='local_structure_checks_passed' or writer.get('entry')!='official'):
        raise ValueError('actual official predecessor writer receipt/ZIP required')
    origin=anchor['copy_origin']
    if origin['zip'].get('path')!=writer.get('archive') or origin['zip'].get('sha256')!=sha(archive) or origin['writer_receipt'].get('path')!=writer.get('receipt') or origin['writer_receipt'].get('sha256')!=sha(checked(anchor['writer_receipt'])):
        raise ValueError('immutable baseline copy origin does not match the actual original writer records')
    oldissues=writer.get('package_obligations',{}).get('reported_issues',{})
    if oldissues.get('passed') is not True or oldissues.get('pending_external_issues'):
        raise ValueError('predecessor did not close its registered issues')
    rows={row['id']:row for row in oldissues['checked_issues']}
    if set(rows)!=set(scope['issue_ids']):raise ValueError('predecessor issue family coverage differs from locked scope')
    events,_=I.load(project);states=I.issue_state(events);cases=0
    for issue_id,row in rows.items():
        state=states.get(issue_id)
        if not state or state.get('superseded') or state.get('proof')!=row['proof']:raise ValueError('original registered proof was replaced: '+issue_id)
        proof=I.validate_proof(state['contract'],row['proof'],old_native)
        if sorted(proof['cases'])!=scope['issue_cases'][issue_id]:raise ValueError('original case coverage changed')
        if proof['executed_native_roots']['current']!=str(old_native):raise ValueError('original issue execution was rebound')
        cases+=len(proof['cases'])
    return {'state':'predecessor_identity_verified_only','old_scope_sha256':sha(scope_path),'old_zip_sha256':sha(archive),
            'historical_art_status':read(historical).get('status'),'original_executed_native':str(old_native),
            'original_native_tree_sha256':scope['binding']['native_tree_sha256'],'original_issue_ids':sorted(rows),
            'original_registered_cases':cases,'source_increment':increment,
            'boundary':'Original actual evidence remains original. Current successor acceptance still requires semantic delta and actual affected-state proof.'}


def validate(project,receipt=None,manifest=None):
    import audit_ui_contract as U
    project=Path(project).resolve();location=Path(manifest).resolve() if manifest else project/MANIFEST
    doc=read(location);prior=predecessor(project,doc)
    semantic=doc['semantic_delta']
    if semantic.get('proof') is None or semantic.get('scope') is None or semantic.get('adapter') is None or doc.get('current_play_proof') is None:
        raise ValueError('successor pending actual semantic delta and current PLAY proof')
    # These shared candidates are installed by the main Agent only after review.
    import importlib.util
    import locked_art_maintenance as L
    import startup_play_successor as S
    guard_path=(Path(L.__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts/play_art_delta_guard.py').resolve()
    if guard_path!=checked(semantic['tool_record']):raise ValueError('reviewed final semantic guard location differs')
    spec=importlib.util.spec_from_file_location('_final_play_art_delta_guard',guard_path)
    D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
    native=Path(doc['current_native']).resolve()
    if not native.is_dir() or not native.is_relative_to(project) or U.tree_digest(native)!=doc['binding'].get('native_tree_sha256'):
        raise ValueError('actual successor Native changed or missing')
    files={p.relative_to(native).as_posix():p.read_bytes() for p in native.rglob('*') if p.is_file()}
    delta=D.validate(checked(doc['predecessor']['zip']),files,checked(semantic['adapter']),checked(semantic['scope']))
    if delta!=read(checked(semantic['proof'])):raise ValueError('recorded semantic delta is stale or differs from actual guarded files')
    # Shared startup/art affected-state checker, never a free-form pass boolean.
    if Path(S.__file__).resolve()!=checked(doc['play_checker']):raise ValueError('reviewed current PLAY checker identity differs')
    current=S.validate_current_play_report(project,native,doc['current_play_proof'])
    return {'state':'user_locked_art_maintenance_successor','manifest':str(location),'manifest_sha256':sha(location),
            'historical_art_status':prior['historical_art_status'],'full_art_verdict':'not_established_by_this_scope',
            'predecessor':prior,'delta_guard':delta,'affected_current_proof':current,
            'native_tree_sha256':doc['binding']['native_tree_sha256'],
            'boundary':'Original user-approved art and exact unaffected evidence reused through the reviewed semantic delta; only actual current PLAY recovery states accepted. No old observations rebound, no full ART or platform pass.'}
