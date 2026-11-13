"""Verify original captures across explicitly initialized case-dependency transitions.

Capture integrity never depends on an art pass or a second identical PNG. No
original dump, PNG, proof or quality verdict is rewritten. The original producer
is unchanged; its full collector fingerprint must match across a transition.
"""
import argparse
import base64
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import time
from uuid import UUID

from art_case_dependencies import digest, file_sha, validate, snapshot_views, affected_cases, projection_bytes, project_file

MANIFEST='capture-inheritance.json'
SCHEMA='art-capture-inheritance.v1'


def read(path):
    p=Path(path)
    if p.is_symlink() or p.resolve()!=p.absolute():raise ValueError('symbolic evidence path')
    return json.loads(p.read_text())

def sealed(path):
    obj=read(path);seal=obj.get('seal');fields={k:v for k,v in obj.items() if k!='seal'}
    if seal!=digest(fields):raise ValueError('evidence seal changed: '+str(path))
    return fields

def store(project):return Path(project)/'.tiktok-kit/art-rounds'

def current_context(project,build):
    project=Path(project).resolve(strict=True);build=Path(build).resolve(strict=True)
    tool=Path(__file__).with_name('art_capture_round.mjs')
    proc=subprocess.run(['node',str(tool),'status',str(project),str(build)],capture_output=True,text=True,timeout=180)
    state=json.loads(proc.stdout) if proc.stdout else {}
    if proc.returncode or state.get('error'):raise ValueError(state.get('error') or proc.stderr)
    if not state.get('current_round_version') or any(state['changes'].values()):raise ValueError('current source/export/matrix/collector is not an initialized current round')
    active=read(store(project)/'current.json');snap=snapshot(project,active['version'])
    if snap['project']!=str(project) or snap['build']!=str(build):raise ValueError('round project/build mismatch')
    policy=read(project/'docs/art/capture-plan.json')
    if digest(policy)!=snap['policy']:raise ValueError('case matrix changed')
    return project,build,active,snap,policy

def snapshot(project,version):
    if not isinstance(version,str) or len(version)!=64 or any(c not in '0123456789abcdef' for c in version):raise ValueError('invalid snapshot version')
    snap=read(store(project)/'snapshots'/(version+'.json'))
    if digest(snap)!=version:raise ValueError('snapshot bytes changed')
    return snap

def raw_proof(project,folder,case):
    path=Path(folder)/('capture-ui-dump-'+case['id']+'.json');doc=read(path)
    uid=doc.get('art_capture_id');UUID(uid)
    proof=sealed(store(project)/'proofs'/(uid+'.json'))
    UUID(proof.get('session'))
    stamp=proof.get('timeOrigin')
    if (type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<=0
            or not re.fullmatch(r'[a-f0-9]{64}',str(proof.get('env','')))
            or not isinstance(proof.get('reads'),list) or 'index.html' not in proof['reads']):
        raise ValueError('capture browser/session dependencies missing')
    if proof.get('id')!=uid or proof.get('case')!=case['id'] or proof.get('caseHash')!=digest(case):raise ValueError('proof case identity changed')
    if doc.get('screen')!=case['screen'] or doc.get('kind')!=case['kind'] or doc.get('purpose')!=(case.get('purpose') or 'other'):raise ValueError('captured page role changed')
    if doc.get('viewport')!={'width':case['width'],'height':case['height']} or doc.get('screenshot')!=case['id']+'.png':raise ValueError('capture viewport/pair mismatch')
    png=path.parent/doc['screenshot']
    if png.is_symlink() or png.resolve()!=png.absolute():raise ValueError('symbolic PNG evidence')
    if proof.get('dump')!=file_sha(path) or proof.get('png')!=file_sha(png) or doc.get('screenshot_sha256')!=proof['png']:raise ValueError('original dump/PNG changed')
    from PIL import Image
    with Image.open(png) as im:
        if im.format!='PNG' or im.size!=(round(case['width']*case['dpr']),round(case['height']*case['dpr'])):raise ValueError('capture PNG dimensions changed')
    old=snapshot(project,proof['version'])
    if old['project']!=str(Path(project).resolve()):raise ValueError('proof belongs to another project')
    return path.resolve(),proof,old

def archive_owned(contract,project,build):
    return {e['domain']+':'+e['path']:base64.b64encode(project_file(project if e['domain']=='source' else build,e['path']).read_bytes()).decode()
            for e in contract['files']}

def validate_baseline(project,record,seen=None):
    """Recompute projected historical bytes against the original snapshot hashes."""
    seen=set() if seen is None else seen
    if record['version'] in seen:raise ValueError('cyclic inheritance checkpoint')
    seen=seen|{record['version']};snap=snapshot(project,record['version']);contract=record['contract']
    validate(contract,[c['id'] for c in record['cases']]);views={}
    if snap['project']!=str(Path(project).resolve()) or digest(record['policy'])!=snap['policy']:raise ValueError('baseline case/project snapshot changed')
    for e in contract['files']:
        key=e['domain']+':'+e['path'];raw=base64.b64decode(record['owned_bytes'][key],validate=True)
        actual=hashlib.sha256(raw).hexdigest();expected=snap['source' if e['domain']=='source' else 'exported'].get(e['path'])
        if actual!=expected:raise ValueError('archived dependency bytes do not match original snapshot')
        views[key]=projection_bytes(raw,e)
    if views!=record['views']:raise ValueError('historical dependency projection changed')
    lineage=record.get('lineage')
    if not lineage:return None
    parent_path=Path(lineage['baseline'])
    if file_sha(parent_path)!=lineage['baseline_sha256']:raise ValueError('parent checkpoint changed')
    parent=sealed(parent_path)
    if digest(parent['contract'])!=digest(contract):raise ValueError('ownership contract changed across checkpoint')
    prior_origins=validate_baseline(project,parent,seen)
    old=snapshot(project,parent['version'])
    if old['collector']!=snap['collector']:raise ValueError('unknown producer transition in checkpoint')
    changed={domain:[k for k in set(old[field])|set(snap[field]) if old[field].get(k)!=snap[field].get(k)] for domain,field in [('source','source'),('export','exported')]}
    delta=affected_cases(contract,parent['views'],views,changed)
    if delta['unknown']:raise ValueError('unknown archived dependency closure')
    fresh=set(delta['affected_cases']);old_cases={c['id']:c for c in parent['cases']}
    fresh.update(c['id'] for c in record['cases'] if digest(c)!=digest(old_cases[c['id']]))
    anchors={}
    for c in record['cases']:
        key=(c['width'],c['height'],c['dpr'])
        if key not in anchors or c.get('anchor'):anchors[key]=c['id']
    fresh.update(anchors.values())
    origins=lineage['origins']
    if set(origins)!={c['id'] for c in record['cases']}:raise ValueError('incomplete checkpoint origins')
    for c in record['cases']:
        origin=origins[c['id']];path=Path(origin['dump'])
        _,proof,_=raw_proof(project,path.parent,c)
        if proof['id']!=origin['proof']:raise ValueError('checkpoint origin changed')
        if c['id'] in fresh:
            if proof['version']!=record['version'] or proof['round']!=record['round']:raise ValueError('changed case checkpoint is not fresh')
        elif prior_origins is not None:
            if origin!=prior_origins[c['id']]:raise ValueError('checkpoint replaced an inherited origin')
        elif proof['version']!=parent['version'] or proof['round']!=parent['round'] or parent['created_ms']>proof['timeOrigin']:
            raise ValueError('checkpoint lacks a pre-capture original contract')
    return origins

def initialize(project,build,contract_path,out,inherited_evidence=None):
    project,build,active,snap,policy=current_context(project,build)
    contract=read(Path(contract_path).resolve());validate(contract,[c['id'] for c in policy['cases']])
    # Initialization must precede every origin it might later inherit. Never
    # retrofit an ownership declaration to already-captured legacy evidence.
    lineage=None
    if inherited_evidence is not None:
        history=verify(project,build,inherited_evidence)
        if not history or not history['ready'] or not (Path(inherited_evidence)/MANIFEST).is_file():raise ValueError('checkpoint needs an already verified mixed transition')
        m,parent=_manifest_inputs(project,inherited_evidence)
        if digest(parent['contract'])!=digest(contract):raise ValueError('checkpoint ownership must remain unchanged')
        lineage={'baseline':m['baseline'],'baseline_sha256':m['baseline_sha256'],
                 'origins':{row['id']:{'dump':name,'proof':row['origin']} for row,name in zip(history['cases'],history['resolved_dumps'])},
                 'quality_refs':history['quality_refs']}
    record={'schema':'art-case-baseline.v1','created_ms':time.time()*1000,'project':str(project),'build':str(build),
            'round':active['id'],'version':active['version'],'contract':contract,'cases':policy['cases'],'policy':policy,
            'views':snapshot_views(contract,project,build),'owned_bytes':archive_owned(contract,project,build),
            'lineage':lineage,'extractor_sha256':file_sha(Path(__file__).with_name('art_case_dependencies.py'))}
    record['created_ms']=time.time()*1000
    target=Path(out).resolve();target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as f:json.dump({**record,'seal':digest(record)},f,ensure_ascii=False,indent=2)
    return {'initialized':str(target),'sha256':file_sha(target),'must_precede_capture':True,'quality_promoted':False}

def _manifest_inputs(project,folder):
    manifest=read(Path(folder)/MANIFEST)
    if manifest.get('schema')!=SCHEMA or Path(manifest['project']).resolve()!=Path(project).resolve():raise ValueError('invalid inheritance project/schema')
    base_path=Path(manifest['baseline'])
    if not base_path.is_absolute() or file_sha(base_path)!=manifest.get('baseline_sha256'):raise ValueError('baseline path/hash changed')
    baseline=sealed(base_path)
    if baseline.get('schema')!='art-case-baseline.v1' or baseline.get('project')!=str(Path(project).resolve()):raise ValueError('baseline belongs to another project')
    # The exact original tool hash remains recorded. Recompute its archived
    # source bytes with today's trusted parser and require identical projections
    # in validate_baseline; a comment/CLI/report-only tool edit is not a reason
    # to rebuild or capture again. Changed projections remain a hard boundary.
    return manifest,baseline

def verify(project,build,folder):
    """Return None for ordinary non-applicable evidence; never hide an invalid manifest."""
    project,build,active,now,policy=current_context(project,build)
    folder=Path(folder).resolve(strict=True);cases=policy['cases'];manifest_path=folder/MANIFEST
    if any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('symbolic link in capture evidence directory')
    manifest=baseline=delta=None;old_cases={};base_folder=None
    if manifest_path.is_file():
        manifest,baseline=_manifest_inputs(project,folder);previous=snapshot(project,baseline['version'])
        baseline_origins=validate_baseline(project,baseline)
        if previous['collector']!=now['collector']:raise ValueError('collector changed: no producer equivalence may be inferred')
        contract=baseline['contract'];validate(contract,[c['id'] for c in baseline['cases']])
        if set(contract['cases'])!={c['id'] for c in cases}:raise ValueError('case inventory changed; initialize a forward contract for the new matrix')
        changed={domain:[k for k in set(previous[field])|set(now[field]) if previous[field].get(k)!=now[field].get(k)]
                 for domain,field in [('source','source'),('export','exported')]}
        views=snapshot_views(contract,project,build)
        delta=affected_cases(contract,baseline['views'],views,changed)
        if delta['unknown']:raise ValueError('unknown dependency closure: '+'; '.join(delta['unknown']))
        old_cases={c['id']:c for c in baseline['cases']}
        changed_policy={c['id'] for c in cases if digest(c)!=digest(old_cases[c['id']])}
        required=set(delta['affected_cases'])|changed_policy
        # One real current-version anchor for every viewport. No synthetic state
        # replay or second byte-identical screenshot is required.
        anchors={}
        for c in cases:
            key=(c['width'],c['height'],c['dpr'])
            if key not in anchors or c.get('anchor'):anchors[key]=c['id']
        required.update(anchors.values())
        if set(manifest.get('fresh_cases',[]))!=required:raise ValueError('fresh-case list must equal actual impact plus viewport anchors')
        base_folder=Path(manifest['base_dumps'])
        if not base_folder.is_absolute() or not base_folder.is_dir():raise ValueError('missing absolute original capture directory')
        quality=[]
        for ref in manifest.get('quality_refs',[])+(baseline.get('lineage') or {}).get('quality_refs',[]):
            q=Path(ref['path'])
            if not q.is_absolute() or file_sha(q)!=ref['sha256']:raise ValueError('original quality report changed')
            raw=read(q)
            quality.append({'path':str(q),'sha256':ref['sha256'],'original_passed':raw.get('passed'),'original_status':raw.get('status')})
    else:
        required=set();quality=[]
    rows=[];resolved=[];env={}
    for case in cases:
        fresh=folder/('capture-ui-dump-'+case['id']+'.json')
        if manifest and case['id'] not in required:
            if fresh.exists():raise ValueError('unexpected competing current capture for inherited case')
            inherited=baseline_origins.get(case['id']) if baseline_origins else None
            path,proof,snap=raw_proof(project,Path(inherited['dump']).parent if inherited else base_folder,old_cases[case['id']])
            if inherited and proof['id']!=inherited['proof']:raise ValueError('checkpoint inherited origin changed')
            if not inherited and (proof['version']!=baseline['version'] or proof['round']!=baseline['round'] or baseline['created_ms']>proof['timeOrigin']):
                raise ValueError('dependency contract was not initialized before the original arrival')
            if proof.get('auxiliary'):raise ValueError('specialized auxiliary evidence cannot inherit implicitly')
            mode='reuse'
        else:
            path,proof,snap=raw_proof(project,folder,case)
            if proof['version']!=active['version']:
                if manifest:raise ValueError('required new capture is not current')
                return None  # Legacy reuse logic retains authority for other transitions.
            if manifest and proof['round']!=active['id']:raise ValueError('anchor/affected capture is not fresh in the current round')
            mode='fresh' if proof['round']==active['id'] else 'reuse'
        key=(case['width'],case['height'],case['dpr'])
        if key in env and env[key]!=proof['env']:raise ValueError('browser environment changed within viewport')
        env[key]=proof['env'];resolved.append(str(path))
        rows.append({'id':case['id'],'screen':case['screen'],'viewport':list(key),'action':mode,'origin':proof['id'],
                     'originVersion':proof['version'],'currentVersion':active['version']})
    expected={('capture-ui-dump-'+c['id']+'.json') for c in cases if not manifest or c['id'] in required}
    observed={str(p.relative_to(folder)) for p in folder.rglob('*ui-dump-*.json')}
    if observed!=expected:raise ValueError('unregistered/missing capture dump in current evidence directory')
    return {'ready':True,'round':active['id'],'version':active['version'],'cases':rows,'missingAnchors':[],
            'resolved_dumps':resolved,'quality_refs':quality,'quality_promoted':False,
            'collector_chain':{'before':now['collector'],'after':now['collector'],'unchanged':True,
                'current_producer_sha256':file_sha(Path(__file__).with_name('art_capture_round.mjs'))},
            'dependency_verifier_chain':{'initialized':baseline.get('extractor_sha256') if baseline else None,
                'current':file_sha(Path(__file__).with_name('art_case_dependencies.py')),
                'archived_projections_replayed':baseline is not None},
            'dependency_transition':delta,'verification':'original-capture-integrity-only-not-art-acceptance'}

def resolve_input_files(folder,project=None):
    """Strict file enumeration shared by sub-checkers; never scans an old directory wholesale."""
    folder=Path(folder)
    if not folder.is_dir():return [folder] if folder.is_file() else []
    marker=folder/MANIFEST
    if not marker.is_file():return sorted(folder.rglob('*ui-dump*.json'))
    manifest=read(marker);owner=Path(manifest['project']).resolve()
    if project is not None and owner!=Path(project).resolve():raise ValueError('capture input belongs to another project')
    active=read(store(owner)/'current.json');snap=snapshot(owner,active['version'])
    report=verify(owner,snap['build'],folder)
    if not report or not report['ready']:raise ValueError('capture inheritance not verified')
    return [Path(p) for p in report['resolved_dumps']]

def transition_plan(project,build,baseline_path,base_dumps):
    """Read-only exact scope + manifest template, after one verified export/new round."""
    project,build,active,now,policy=current_context(project,build)
    baseline_path=Path(baseline_path).resolve(strict=True);baseline=sealed(baseline_path)
    if baseline.get('project')!=str(project):raise ValueError('baseline project mismatch')
    validate_baseline(project,baseline);old=snapshot(project,baseline['version'])
    if old['collector']!=now['collector']:raise ValueError('unknown collector transition; no equivalence inferred')
    if set(baseline['contract']['cases'])!={c['id'] for c in policy['cases']}:raise ValueError('case inventory change needs a new forward contract')
    changed={d:[k for k in set(old[f])|set(now[f]) if old[f].get(k)!=now[f].get(k)] for d,f in [('source','source'),('export','exported')]}
    delta=affected_cases(baseline['contract'],baseline['views'],snapshot_views(baseline['contract'],project,build),changed)
    if delta['unknown']:
        return {'read_only':True,'unknown':delta['unknown'],'fresh_cases':[c['id'] for c in policy['cases']],
                'use_plain_current_capture':True,'manifest':None,'reason':'Unknown closure cannot authorize inheritance. Expand the explicit scope once.'}
    before={c['id']:c for c in baseline['cases']};fresh=set(delta['affected_cases']);anchors={}
    for c in policy['cases']:
        if digest(c)!=digest(before[c['id']]):fresh.add(c['id'])
        key=(c['width'],c['height'],c['dpr'])
        if key not in anchors or c.get('anchor'):anchors[key]=c['id']
    fresh.update(anchors.values())
    manifest={'schema':SCHEMA,'project':str(project),'baseline':str(baseline_path),'baseline_sha256':file_sha(baseline_path),
              'base_dumps':str(Path(base_dumps).resolve(strict=True)),'fresh_cases':sorted(fresh),'quality_refs':[]}
    return {'read_only':True,'dependency_diff':changed,'affected_cases':delta['affected_cases'],'shared_expansions':delta['shared_expansions'],
            'anchors':sorted(anchors.values()),'fresh_cases':sorted(fresh),
            'reuse_cases':sorted(set(before)-fresh),'manifest':manifest,'quality_promoted':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init',help='Before capture, bind exact method/asset ownership; never retrofit legacy evidence')
    for p in (init,):
        p.add_argument('--project',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
        p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
        p.add_argument('--inherit-evidence',type=Path,help='After a verified local transition, checkpoint exact origins before the next edit')
    check=sub.add_parser('verify',help='Read-only strict mixed-evidence verification; no quality promotion')
    check.add_argument('--project',type=Path,required=True);check.add_argument('--build',type=Path,required=True);check.add_argument('--dumps',type=Path,required=True)
    planning=sub.add_parser('plan-transition',help='Read-only exact impact/anchor plan and mixed-manifest template')
    planning.add_argument('--project',type=Path,required=True);planning.add_argument('--build',type=Path,required=True)
    planning.add_argument('--baseline',type=Path,required=True);planning.add_argument('--base-dumps',type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.command=='init':result=initialize(a.project,a.build,a.contract,a.out,a.inherit_evidence)
        elif a.command=='plan-transition':result=transition_plan(a.project,a.build,a.baseline,a.base_dumps)
        else:result=verify(a.project,a.build,a.dumps)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ready':False,'error':str(exc)}));return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
