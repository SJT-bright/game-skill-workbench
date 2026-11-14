"""Explicit Creator 1.x compatibility regression producer and read-only consumer.

This is a different engine backend, not a 2.x suite waiver. It is available only
for an immutable reviewed integration repair of a received 1.9.3 game. Existing
2.x/3.x coverage, feature-production and migration policies are unchanged.
"""
import argparse, datetime, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
SCHEMA = 'creator1_compatibility_regression.v1'
CASES = ['official_engine_identity','native_renderer_play_drag','sdk_screen_coordinates',
         'unreadable_storage_home_play_drag','loading_failure_retry_late_response',
         'source_native_ad_capability','source_native_storage_transaction']
BOUNDARY = ('Scoped existing-game Creator 1.9.3 integration regression. Actual Ego Native HOME/PLAY/drag, '
            'two phone aspect ratios, HTTP recovery and whole-game unreadable storage plus isolated actual '
            'source/compiled-module SDK tests. No claim of full gameplay regression, real advertisement, '
            'physical TikTok, released typed-save migration or platform upload acceptance.')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_bytes())
def require(value, message):
    if not value: raise ValueError('Creator1 compatibility: '+message)
def tool_inputs():
    # Bind the implementation, all imported validators and the exact parsers/VMs.
    names = ['creator1_compatibility_contract.py','cocos1_compat.py','official_engine_sources.json',
             'compatibility_scope.py','creator1_storage_contract.py','audit_native_startup_renderer.py',
             'audit_loading_recovery.py','storage_scoped_reuse.py','audit_final_storage.py',
             'audit_final_package_startup.py','make_tiktok_zip.py','writer_proofs.py','ad_standard_scope.py','audit_packed_assets.py','creator1_active_literals.cjs','project_qa.py','probe_creator1_sdk.cjs','probe_cocos1_touch_coordinates.cjs','read_cocos1_settings.cjs','vendor/acorn.cjs']
    return {str(HERE/n):sha(HERE/n) for n in names}
def reference(path):
    path=Path(path).resolve();return {'path':str(path),'sha256':sha(path)}
def collect_refs(value, base, result):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
            p=Path(value['path']);p=p if p.is_absolute() else base/p
            require(p.is_file() and sha(p)==value['sha256'],'changed raw evidence '+str(p))
            key=str(p.resolve())
            if key not in result:
                result[key]=sha(p)
                if p.suffix=='.json': collect_refs(load(p),p.parent,result)
        for item in value.values():collect_refs(item,base,result)
    elif isinstance(value,list):
        for item in value:collect_refs(item,base,result)
def artifacts(project,native,web):
    from check_known_issues import snapshot,tree_sha
    return dict(source_sha256=snapshot(project)[2],native_tree_sha256=tree_sha(native),web_tree_sha256=tree_sha(web))
def validate_base(project,native,web,startup,recovery):
    from compatibility_scope import verified,tree
    from cocos1_compat import engine_file
    import audit_native_startup_renderer as renderer
    from audit_final_storage import audit_final_storage
    from audit_loading_recovery import validate
    scope=verified(project)
    require(scope is not None and Path(scope['native'])==native,'registered exact repair scope required')
    files={n:(native/n).read_bytes() for n in tree(native)}
    require(engine_file(files),'independently reproduced genuine engine required')
    contract=load(startup);binding=contract.get('binding',{})
    require(all(binding.get(k)==v for k,v in artifacts(project,native,web).items()),'stale source/Native/Web binding')
    require(contract.get('tool')=='audit_startup_contract' and contract.get('passed') is True and contract.get('runtime_required') is True,'actual Native startup contract required')
    rp=Path(contract['startup_renderer_report']['path'])
    require(sha(rp)==contract['startup_renderer_report']['sha256'],'renderer report changed')
    errors=renderer.validate(load(rp),native,binding,project)
    require(not errors,'renderer failed: '+str(errors))
    storage=audit_final_storage(native,project,startup)
    recovery_data=load(recovery);errors=validate(recovery_data,binding,Path(recovery).parent)
    require(not errors,'loading recovery failed: '+str(errors))
    refs={}
    for p in [startup,recovery,rp]:
        refs[str(Path(p).resolve())]=sha(p);collect_refs(load(p),Path(p).parent,refs)
    return scope,binding,storage,refs

def prepare(project,native,web,startup,recovery,out):
    started=time.monotonic();project,native,web,startup,recovery,out=map(lambda p:Path(p).resolve(),[project,native,web,startup,recovery,out])
    require(not out.exists(),'never overwrite an execution record')
    scope,binding,storage,refs=validate_base(project,native,web,startup,recovery)
    source=project/'assets';reward=list(source.rglob('RewardedService.js'));save=list(source.rglob('SaveStore.js'))
    require(len(reward)==len(save)==1,'unique actual source SDK modules required')
    node=Path(shutil.which('node')).resolve();commands=[
      ['node',str(HERE/'probe_cocos1_touch_coordinates.cjs'),str(native)],
      ['node',str(HERE/'probe_creator1_sdk.cjs'),str(reward[0]),str(save[0]),str(native/'src/project.js')]]
    runs=[]
    for command in commands:
        tick=time.monotonic();p=subprocess.run(command,input=json.dumps({'files':{n:(native/n).read_text() for n in ('cocos2d-js-min.js','sdk-namespace.js','game.js','adapter-min.js','libs/weapp-adapter/EventIniter/TouchEvent.js')}}) if len(runs)==0 else None,capture_output=True,text=True,timeout=60)
        require(p.returncode==0,'actual VM probe failed: '+p.stderr+p.stdout)
        data=json.loads(p.stdout);require(data.get('passed') is True,'VM probe refused')
        runs.append(dict(command=command,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.monotonic()-tick))
    require(artifacts(project,native,web)=={k:binding[k] for k in artifacts(project,native,web)},'artifacts changed during producer')
    doc=dict(schema=SCHEMA,project=str(project),native=str(native),web=str(web),binding=binding,
             scope=reference(project/'.tiktok-kit/compatibility-scope.json'),startup=reference(startup),recovery=reference(recovery),
             tools=tool_inputs(),node=dict(path=str(node),sha256=sha(node)),evidence=refs,runs=runs,
             required_cases=CASES,cases=[dict(id=cid,passed=True) for cid in CASES],passed=True,
             observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-started,boundary=BOUNDARY)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    return consume(project,native,web,out)

def consume(project,native,web,path=None):
    project,native,web=map(lambda p:Path(p).resolve(),[project,native,web])
    path=Path(path).resolve() if path else project/'docs/checks/creator1-compatibility.json'
    doc=load(path)
    require(doc.get('schema')==SCHEMA and doc.get('project')==str(project) and doc.get('native')==str(native) and doc.get('web')==str(web),'record scope mismatch')
    require(doc.get('tools')==tool_inputs(),'producer implementation changed; revalidate affected node')
    require(sha(doc['node']['path'])==doc['node']['sha256'],'producer runtime changed')
    for ref in [doc['scope'],doc['startup'],doc['recovery']]:require(sha(ref['path'])==ref['sha256'],'changed input evidence')
    scope,binding,storage,refs=validate_base(project,native,web,doc['startup']['path'],doc['recovery']['path'])
    require(binding==doc.get('binding') and refs==doc.get('evidence'),'raw evidence closure changed')
    require(doc.get('required_cases')==CASES and doc.get('cases')==[dict(id=c,passed=True) for c in CASES] and doc.get('passed') is True,'incomplete compatibility catalogue')
    runs=doc.get('runs',[]);require(len(runs)==2 and all(r.get('returncode')==0 for r in runs),'actual producer executions required')
    touch,sdk=[json.loads(r['stdout']) for r in runs]
    require(touch.get('passed') is True and sdk.get('passed') is True,'failed producer')
    require(len(touch.get('rows',[]))==12 and all(r.get('passed') is True for r in touch['rows']),'twelve actual SDK touch conversions required')
    expected={(layer,case) for layer in ('source','native') for case in ['ad/undefined','ad/true','ad/missing','ad/false','ad/throws','storage/missing_null','storage/missing_empty_string','storage/valid_legacy','storage/read_failure','storage/write_failure','storage/readback_failure','storage/grant_once_restart','storage/malformed_backup']}
    require(len(sdk.get('rows',[]))==len(expected) and {(r.get('layer'),r.get('case')) for r in sdk['rows']}==expected and all(r.get('passed') is True for r in sdk['rows']),'actual source/Native module cases missing')
    require(all(sha(p)==h for p,h in sdk['inputs'].items()),'SDK VM actual inputs changed')
    refs.update(doc['tools']);refs[doc['node']['path']]=doc['node']['sha256'];refs[str(path)]=sha(path);refs[doc['scope']['path']]=doc['scope']['sha256']
    return dict(id='creator1.compatibility',status='passed',passed=True,complete=True,engine='1.9.3',
                required_cases=CASES,cases=doc['cases'],record=reference(path),binding=binding,
                original_at=doc['observed_at'],original_seconds=doc['seconds'],refs=refs,
                source_inputs=scope['source_inputs'],native_inputs=scope['native_inputs'],web_inputs=__import__('compatibility_scope').tree(web),boundary=BOUNDARY,
                storage=storage)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','consume'])
    for k in ['project','native','web']:p.add_argument('--'+k,type=Path,required=True)
    for k in ['startup','recovery','out']:p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    try:
        r=prepare(a.project,a.native,a.web,a.startup,a.recovery,a.out) if a.command=='prepare' else consume(a.project,a.native,a.web,a.out)
        print(json.dumps({k:v for k,v in r.items() if k not in ('refs','source_inputs','native_inputs','web_inputs')},ensure_ascii=False))
    except (ValueError,OSError,KeyError,TypeError) as e:print(json.dumps({'passed':False,'error':str(e)}));sys.exit(1)


def writer_evidence(project,native,web):
    """Consume every mandatory 1.x node; publication repeats this identity check."""
    proof=consume(project,native,web)
    scope=dict(schema='creator1_scoped_compatibility_plan.v1',mode='scoped',
               authority='registered_exact_current_integration_repair',native_tree=proof['binding']['native_tree_sha256'],
               required_cases=CASES,record=proof['record'],boundary=BOUNDARY)
    runtime=dict(id='runtime_regression',status='passed',passed=True,complete=True,engine='1.x',
                 required=['creator1_compatibility'],suites=[dict(suite='creator1_compatibility',passed=True,cases=proof['cases'],evidence=proof['record'])],
                 tool_sha256=sha(__file__),adapter_sha256=proof['record']['sha256'],seconds=0,
                 original_seconds=proof['original_seconds'],original_at=proof['original_at'],boundary=BOUNDARY)
    ads=dict(id='rewarded_ad_regression',status='not_applicable',
             reason='The 2.x/3.x host suite is incompatible with Creator 1.x. Mandatory current-source/current-compiled SDK capability cases are recorded in creator1_compatibility; full advertisement outcomes and real advertisements are untested in this scoped integration repair.')
    producer=dict(checks=[{k:proof[k] for k in ('id','status','passed','record','original_at','original_seconds','boundary')}],
                  refs=proof['refs'],creator1=dict(project=str(Path(project).resolve()),native=str(Path(native).resolve()),web=str(Path(web).resolve()),record=proof['record']))
    return producer,scope,dict(profile=SCHEMA,compatibility=proof['record'],rewarded_ad_regression=ads,runtime_regression=runtime),runtime,ads
