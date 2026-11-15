"""The ad callback matrix uses the same durable ledger as art and runtime checks."""
import hashlib
import json
from pathlib import Path
import time
import uuid
from runtime_incremental import CL

def run(ar,package_dir,adapter_path,cases=None,work=None,timeout=None,*,plan_only=False):
    """Plan with the production ledger, or execute that exact validated scope."""
    started=time.monotonic();package=Path(package_dir).resolve();adapter=ar.load_adapter(adapter_path)
    required=ar.default_cases(adapter);selected=list(cases) if cases is not None else required
    if any(c in ar.DOUBLE_CASES for c in selected) and 'double_claim' not in adapter:
        raise ar.RegressionRefused('ad regression cases %s need adapter "double_claim"'%','.join(c for c in selected if c in ar.DOUBLE_CASES))
    if set(selected)-set(required):raise ar.RegressionRefused('unknown ad cases: '+str(sorted(set(selected)-set(required))))
    ledger=CL.Ledger(CL.project_of(package,adapter_path))
    root=lambda:{'package':CL.manifest(package),'adapter':CL.json_manifest(json.loads(Path(adapter_path).read_text()))}
    roots=root();plans=[];after={};batch={}
    try:
        for case in required:
            p=ledger.prepare('ads.'+case,roots,{},ar.tool_digest(),label='广告回调 / '+case,domain='platform')
            if case in selected or p['action']=='reuse':plans.append(p)
        if plan_only:
            return plans
        from regression_scope_gate import authorize_batch
        plan_sha = authorize_batch(ledger.project,roots,plans,operation='ads',
                                   native=package,adapter=adapter_path)
        def execute(ids):
            actual=[cid[4:] for cid in ids]
            if not actual or root()!=roots:
                raise CL.NeedsScope('广告回归没有明确用例，或候选输入已变化，重新生成检查计划')
            authorize_batch(ledger.project,roots,plans,operation='ads',expected_sha256=plan_sha)
            try:result=ar._run_uncached(package,adapter_path,actual,work or ledger.home/'runs'/uuid.uuid4().hex,timeout)
            except ar.RegressionRefused as exc:
                result=getattr(exc,'summary',None)
                if not result:raise
            batch.update(result);after.update(root())
            missing_owner=CL.unmapped_changes(ledger.project,roots,after)
            if missing_owner:raise CL.NeedsScope('执行期间出现未归属变化：'+', '.join(missing_owner))
            return {'ads.'+r['case']:{'row':r,'fatal':result.get('fatal'),'boot':result.get('boot'),
                    'raw_files':result.get('raw_files',[]),'warnings':result.get('warnings',[])} for r in result.get('cases',[]) if r['case'] in actual}
        rows,proofs=ledger.execute_batch(plans,execute,lambda r:ar.judge({'fatal':r.get('fatal'),'cases':[r['row']]},[r['row']['case']])[0],
            verify_inputs=lambda p:CL.select_inputs(after,p['scope']))
        items=[rows['ads.'+c]['row'] for c in required if 'ads.'+c in rows]
        missing=[c for c in required if 'ads.'+c not in rows]
        fatal=next((r['fatal'] for r in rows.values() if r.get('fatal')),None)
        ok,problems=ar.judge({'cases':items,'fatal':fatal},[r['case'] for r in items])
        summary=dict(id='rewarded_ad_regression',passed=ok,cases=items,complete=not missing,planned_not_run=missing,
            warnings=list(dict.fromkeys(w for r in rows.values() for w in r.get('warnings',[]))),
            boot=next((r.get('boot') for r in rows.values() if r.get('boot')),None),fatal=fatal,proof_error=bool(fatal),
            tool_sha256=ar.tool_digest(),adapter_sha256=hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
            seconds=round(time.monotonic()-started,3),incremental=proofs,
            executed_units=sum(not p['reused'] for p in proofs.values()),reused_units=sum(p['reused'] for p in proofs.values()))
        if not required:
            summary.update(applicable=False, disposition='manual_revive_only',
                manual_playtest_required=True,
                not_run=[{'role':'revive','reason':'The configured request exclusively exercises rewarded revive; cover it in the first manual playtest after art, not final automation.'}])
        if not ok:
            error=ar.RegressionRefused('rewarded-ad regression failed: '+' | '.join(problems));error.summary=summary;raise error
        return summary
    except CL.NeedsScope as exc:
        error=ar.RegressionRefused(str(exc));error.summary={'id':'rewarded_ad_regression','passed':False,'status':'scope_required',
            'problems':[str(exc)],'stopped_before_browser':True,'proof_error':True,'ledger':str(ledger.home),
            'task_terminal':False,'next_action':'repair_and_replan'};raise error
    finally:ledger.close()
