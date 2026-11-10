"""Plan real runtime executions before opening Ego. Receipts remain tied to original runs.

The existing validators execute unchanged. Independent startup faults, lifecycle cases,
ad-entry states and layout page/viewports have separate IDs. Other suites are explicitly
atomic until an independently executable unit is available; an unmapped edit never
falls back to running the complete suite matrix.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import uuid
import os
import runtime_timing as RT

CORE=Path(__file__).resolve().parents[3]/'remake-core/scripts'
sys.path.insert(0,str(CORE))
import check_ledger as CL

DOMAINS={'layout_state':'image','dead_shell':'image','image_stall':'image','popin':'image',
         'startup':'startup','startup3x':'startup','network':'platform','growth_entry':'platform',
         'ad_entries':'platform','ad_outcome':'platform','resume_play':'gameplay','save_restart':'gameplay'}

def unit_ids(name, meta, adapter, prechecked=False):
    if prechecked:return ['@suite']
    if name in ('startup','startup3x'):
        text=meta['script'].read_text()
        sections=re.findall(r'const (?:CASES|LIFE) = \[(.*?)\n\];',text,re.S)
        return re.findall(r"^\s*\['([^']+)'",'\n'.join(sections),re.M)
    if name=='resume_play':
        return ['background','finger_held','finger_held_new_id','pause_background','ad_background','ad_background_close_first']
    if name=='ad_entries':
        return [str(e['id'])+'/'+str(s['name']) for e in adapter.get('ad_entries',[]) for s in e['states']]
    if name=='layout_state':
        return [d+'/'+str(s['name']) for d in ('iphone14','se') for s in (adapter.get('layout_states') or [{'name':'home'}])]
    return ['@suite']

def _rule(rr,meta,engine):
    host=rr.HOST3 if engine=='3.x' else rr.HOST2
    common=[p for p in rr.TOOL.glob('*.mjs') if p.name!='frame_rate_compare.mjs']
    return RT.rule_fingerprint(CL, [Path(rr.__file__),meta['script'],meta['script'].with_suffix('.json'),*common,host,
                                Path(__file__),CORE/'check_ledger.py'])

def _unit_row(row,unit):
    if unit=='@suite':return row
    units=row.get('units') or {}
    if unit in units:
        item=units[unit]
        cases=item.get('cases') or []
        ok=item.get('passed') is True
    else:
        cases=[c for c in row.get('cases',[]) if c.get('id')==unit]
        ok=bool(cases) and all(c.get('passed') is True for c in cases)
    if row.get('batch_problems') or row.get('fatal'):ok=False
    return dict(suite=row['suite'],unit=unit,passed=ok,cases=cases,
                problems=[] if ok else row.get('batch_problems') or [row['suite']+'/'+unit+': '+str(cases or 'planned unit produced no evidence')],
                proof_error=bool(row.get('batch_problems') or row.get('fatal')),
                browser=row.get('browser',True),
                warnings=row.get('warnings',[]),evidence=row.get('evidence'),raw_files=row.get('raw_files',[]),seconds=row.get('seconds',0))

def run(rr,package_dir,adapter_path,suites=None,work=None,timeout=None,suites_dir=None,policy=None,board=None,
        trial_url=None,capabilities=None,*,plan_only=False):
    """Plan with the production ledger, or execute that exact validated scope."""
    started=time.monotonic();package=Path(package_dir).resolve()
    if not (package/'game.js').is_file():raise rr.RuntimeRefused('runtime regression: no game.js at package root '+str(package))
    if board is not None and board not in rr.BOARDS:raise rr.RuntimeRefused('runtime regression board must be remake or localize, not %r'%(board,))
    catalog=rr.load_suites(suites_dir);adapter=rr.load_adapter(adapter_path,catalog)
    files=rr.package_files(package);engine=rr.detect_engine(files,adapter)
    policy,reason=rr.package_policy(files,policy)
    caps=rr.load_capabilities(capabilities if capabilities is not None else os.environ.get(rr.ENV_CAPABILITIES))
    required=rr.required_suites(files,adapter,catalog,trial_url)
    names=list(suites) if suites is not None else required
    unknown=[n for n in names if n not in catalog]
    if unknown:raise rr.RuntimeRefused('unknown runtime suites: '+', '.join(unknown))
    early_rows,input_warnings=rr.preflight(files,adapter,adapter_path,names,catalog,engine,policy,reason,
                                          board,trial_url,caps,full_run=suites is None)
    # Diagnostic filters cannot silently reduce the package's coverage catalogue.
    if adapter.get('startup_cases') or isinstance(adapter.get('resume_play'),dict) and adapter['resume_play'].get('cases'):
        raise rr.RuntimeRefused('诊断 cases 不能缩减完整清单；用检查项依赖计划选择要执行的节点，原通过项自动沿用')
    project=CL.project_of(package,adapter_path);ledger=CL.Ledger(project)
    returned_art = None
    if board == 'localize':
        from returned_art_acceptance import MANIFEST, validate
        if (project/MANIFEST).is_file():
            try: returned_art = validate(project, native=package)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                ledger.close(); raise rr.RuntimeRefused('返工视觉授权绑定无效：'+str(exc))
    def runtime_units(name, meta, prechecked):
        if returned_art and name == 'layout_state' and not prechecked:
            return ['@startup']  # Hidden startup bytes/audio remain real checks, not visual acceptance.
        return unit_ids(name, meta, adapter, prechecked)
    root=lambda:{'package':CL.manifest(package),'adapter':CL.json_manifest(json.loads(Path(adapter_path).read_text()))}
    roots=root(); plans=[];index={};pre={};selected=set(names)
    # Resolve all needed evidence first. A manually requested subset may reuse prior
    # passes for the rest, but it does not manufacture missing coverage.
    coverage=rr.ordered(list(dict.fromkeys(required+names)),catalog)
    try:
        for name in coverage:
            meta=catalog[name]
            pre[name]=rr.precheck(name,meta,adapter,engine,policy)
            units=runtime_units(name,meta,pre[name] is not None)
            # An unselected legacy suite with no entries stays in planned_not_run;
            # it is neither an executable node nor permission to expand this run.
            if not units and name not in selected:continue
            if len(units)!=len(set(units)) or not units:raise CL.NeedsScope(name+'：节点 ID 为空或重复，先修复适配清单')
            rules=_rule(rr,meta,engine)
            for unit in units:
                cid='runtime.'+name+'/'+unit
                p=ledger.prepare(cid,roots,{'engine':engine,'policy':policy,'board':board if name=='layout_state' else None,
                    'trial_url':trial_url if name=='trial_link' else None,
                    'capabilities':caps if name in ('ad_outcome','ad_entries') else None},rules,
                    label=name+' / '+unit,domain='startup' if unit=='@startup' else DOMAINS.get(name,'gameplay'))
                if returned_art and p['action']=='run' and unit!='@startup':
                    previous=ledger.previous(cid)
                    if previous and all(r['binding']['tool_sha256']!=rules for r in previous):
                        raise CL.NeedsScope(cid+'：历史判定器版本不同，先核对具体规则变化/等价证据，不自动重跑所有功能')
                index[cid]=(name,unit)
                if name in selected or p['action']=='reuse':plans.append(p)
        if plan_only:
            return plans
        from regression_scope_gate import authorize_batch
        plan_sha = authorize_batch(project,roots,plans,operation='runtime',
                                   native=package,adapter=adapter_path)
        blocked=[p for p in plans if p['action'] not in ('run','reuse')]
        if blocked:raise CL.NeedsScope('；'.join(p['check_id']+'：'+p['why'] for p in blocked))
        cached_evidence={}
        for p in plans:
            if p['action']=='reuse':
                ev=p['record']['result'].get('evidence')
                if ev:cached_evidence[index[p['check_id']][0]]=ev
        batch_report={};after_roots={}
        def execute(ids):
            selections={}
            for cid in ids:
                name,unit=index[cid];selections.setdefault(name,[]).append(unit)
            if not selections or root()!=roots:
                raise CL.NeedsScope('运行回归没有明确用例，或候选输入已变化，重新生成检查计划')
            authorize_batch(project,roots,plans,operation='runtime',expected_sha256=plan_sha)
            try:
                run_work=work or ledger.home/'runs'/uuid.uuid4().hex
                result=rr._run_uncached(package,adapter_path,list(selections),run_work,timeout,suites_dir,policy,board,
                    trial_url,capabilities,selections=selections,prior_evidence=cached_evidence)
            except rr.RuntimeRefused as exc:
                result=getattr(exc,'summary',None)
                if not result:raise
            batch_report.update(result)
            batch_report['_timing_batch_id'] = uuid.uuid4().hex
            after_roots.update(root())
            missing_owner=CL.unmapped_changes(project,roots,after_roots)
            if missing_owner:raise CL.NeedsScope('执行期间出现未归属变化：'+', '.join(missing_owner))
            rows={r['suite']:r for r in result.get('suites',[])}
            if any(index[cid][0] not in rows for cid in ids):
                error=rr.RuntimeRefused('原检查器未完成计划：'+' | '.join(result.get('problems') or ['no suite result']))
                error.summary=dict(result,passed=False,proof_error=True)
                raise error
            return {cid:_unit_row(rows[index[cid][0]],index[cid][1]) for cid in ids if index[cid][0] in rows}
        results,proofs=ledger.execute_batch(plans,execute,lambda r:r.get('passed') is True,
            verify_inputs=lambda p:CL.select_inputs(after_roots,p['scope']))
        rows=[]
        for name in coverage:
            members=[cid for cid in results if index[cid][0]==name]
            if not members:continue
            parts=[results[cid] for cid in members]
            expected=runtime_units(name,catalog[name],pre[name] is not None)
            missing=set(expected)-{index[cid][1] for cid in members}
            row={'suite':name,'passed':not missing and all(r['passed'] for r in parts),
                 'cases':[c for r in parts for c in r.get('cases',[])],
                 'problems':[x for r in parts for x in r.get('problems',[])]+(['missing units: '+','.join(sorted(missing))] if missing else []),
                 'warnings':list(dict.fromkeys(w for r in parts for w in r.get('warnings',[]))),
                 'evidence':next((r.get('evidence') for r in parts if r.get('evidence')),None),
                 'seconds':RT.suite_seconds(batch_report, name, all(proofs[c]['reused'] for c in members)),
                 'incremental':{cid:proofs[cid] for cid in members}}
            row['browser']=any(not proofs[cid]['reused'] and results[cid].get('browser',True) for cid in members)
            row['timing']=RT.suite_metadata(batch_report, name, all(proofs[c]['reused'] for c in members))
            if all(proofs[c]['reused'] for c in members):row['reused_from']={'ledger':str(ledger.home),'checks':members}
            if returned_art and name == 'layout_state' and pre[name] is None:
                row.update(functional_passed=row['passed'], accepted_for_delivery=row['passed'],
                           passed=None if row['passed'] else False,
                           visual_status='user_accepted', visual_checks_executed=False,
                           visual_acceptance=returned_art,
                           accepted_visual_units=unit_ids(name,catalog[name],adapter))
            rows.append(row)
        have={r['suite'] for r in rows if r['passed'] or r.get('accepted_for_delivery') is True}
        missing=[n for n in required if n not in have]
        problems=[x for r in rows for x in r['problems']]
        summary=dict(id='runtime_regression',passed=not problems,complete=not missing,planned_not_run=missing,
            engine=engine,policy=policy,policy_reason=reason,board=board,required=required,suites=rows,
            not_run=rr.not_run(files,adapter,[r['suite'] for r in rows],catalog,trial_url),problems=problems,
            warnings=list(dict.fromkeys(input_warnings+batch_report.get('warnings',[])+[w for r in rows for w in r['warnings']])),startup_measured=rr._startup_measured(rows),
            tool_sha256=rr.tool_digest(catalog),adapter_sha256=hashlib.sha256(Path(adapter_path).read_bytes()).hexdigest(),
            seconds=round(time.monotonic()-started,3),executed_units=sum(not p['reused'] for p in proofs.values()),
            reused_units=sum(p['reused'] for p in proofs.values()),ledger=str(ledger.home))
        summary['accepted_visual_suites']=[r['suite'] for r in rows if r.get('visual_status')=='user_accepted']
        summary['proof_error']=any(r.get('proof_error') or r.get('fatal') for r in results.values())
        if problems:
            exc=rr.RuntimeRefused('runtime regression failed: '+' | '.join(problems));exc.summary=summary;raise exc
        return summary
    except CL.NeedsScope as exc:
        error=rr.RuntimeRefused(str(exc));error.summary={'id':'runtime_regression','passed':False,'status':'scope_required',
            'problems':[str(exc)],'stopped_before_browser':True,'proof_error':True,'ledger':str(ledger.home)};raise error
    finally:ledger.close()
