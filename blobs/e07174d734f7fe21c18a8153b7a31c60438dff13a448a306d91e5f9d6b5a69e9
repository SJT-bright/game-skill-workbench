#!/usr/bin/env python3
"""Read-only next-step planner. Never builds, captures, starts rounds or accepts evidence.

Use --status-json from art_capture_round.mjs status, or let this command read status
with --project/--build. An impact declaration alone is advisory. --baseline
uses the owning versioned dependency planner; --dumps verifies actual original
proofs before declaring the current evidence ready.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

HASH=re.compile(r'^[a-f0-9]{64}$')
DOMAINS=('source','export')


def failure_inventory(reports):
    """Return every reported blocker in one pass; no first-failure short circuit."""
    out=[]
    for name,report in reports:
        for row in report.get('rows',[]):
            if row.get('status') in ('需处理','fail','error') or row.get('passed') is False:
                out.append({'report':name,'check':row.get('check') or row.get('id'),
                            'detail':row.get('detail') or row.get('error'), 'log':row.get('log')})
        for key in ('errors','blocking_rows'):
            for item in report.get(key,[]):out.append({'report':name,'check':key,'detail':item})
        # Keep each page's failures: one failed row can cover many distinct fixes.
        for page in report.get('pages',[]):
            for issue in page.get('problems',[]):
                out.append({'report':name,'check':page.get('screen') or page.get('id'), 'detail':issue})
    return out

def current_complete_report(report, verified):
    """A passed scalar/empty report is not an analysis bound to current originals."""
    if not verified or not verified.get('ready') or verified.get('error'):return False
    if report.get('tool')!='art_check' or report.get('status') not in ('pass','fail'):return False
    rows=report.get('rows')
    if not isinstance(rows,list) or not rows or report.get('checked')!=len(rows):return False
    if any(k in report for k in ('maintenance_mapping','english_visual_scope')):return False
    capture=report.get('capture_round',{})
    if not capture.get('ready') or any(capture.get(k)!=verified.get(k) for k in ('round','version')):return False
    origins=lambda c:sorted((r['id'],r['origin']) for r in c['cases'])
    try:
        if origins(capture)!=origins(verified):return False
        from art_check_record import TRIAL_GROUPS,trial_group
        required=(set(TRIAL_GROUPS)-{'slots'})|{'inputs'}
        return required<={trial_group(r) for r in rows}
    except (KeyError,TypeError,ValueError):return False


def impact_blockers(status,impact,case_ids):
    problems=[]
    if not isinstance(impact,dict):return ['source/export changes have no explicit impact manifest']
    for key in ('source_hash','export_hash','matrix_hash','collector_hash'):
        if impact.get('after',{}).get(key)!=status.get(key):problems.append('impact after identity mismatch: '+key)
    if impact.get('before',{}).get('version')!=status.get('current_round_version'):
        problems.append('impact before version does not name the actual baseline snapshot')
    for key in ('source_hash','export_hash','matrix_hash','collector_hash'):
        if not HASH.fullmatch(str(impact.get('before',{}).get(key,''))):problems.append('missing baseline hash: '+key)
    expected={(domain,name) for domain in DOMAINS for name in status.get('changed_files',{}).get(domain,[])}
    seen=set()
    for item in impact.get('files',[]):
        if not isinstance(item,dict):problems.append('invalid impact file');continue
        pair=(item.get('domain'),item.get('path'))
        if pair in seen:problems.append('duplicate impact file: '+str(pair))
        seen.add(pair)
        for key in ('before_sha256','after_sha256'):
            value=item.get(key)
            if value is not None and not HASH.fullmatch(str(value)):problems.append('invalid file hash: '+str(pair))
        if item.get('before_sha256')==item.get('after_sha256'):problems.append('changed file lacks a real hash delta: '+str(pair))
        cases=item.get('cases')
        if item.get('scope')!='local':problems.append('shared or unknown dependency: '+str(pair))
        if not isinstance(cases,list) or not cases or not all(isinstance(c,str) for c in cases) or not set(cases)<=case_ids:
            problems.append('missing/unknown affected cases: '+str(pair))
        if not item.get('basis'):problems.append('missing dependency-review basis: '+str(pair))
    if expected!=seen:problems.append('impact file inventory does not exactly cover actual source/export diff')
    if not case_ids:problems.append('current capture case matrix is missing')
    return problems


def plan(status,reports=(),changed_rules=(),impact=None,case_ids=(),rule_hashes_before=None,rule_hashes_after=None,
         history_plan=None, verified_history=None, history_error=None):
    failures=failure_inventory(reports)
    blockers=[]
    result={'tool':'art_change_plan','schema':1,'read_only':True,'evidence_acceptance':False,
            'executes':[], 'all_reported_blockers':failures,
            'build':{'required':None},'capture':{'required':None},'analyze':{'required':None},
            'planning_blockers':blockers,
            'guard':'This is a plan, never a receipt, proof transition, evidence reuse approval or full ART pass.'}
    if status.get('error') or not isinstance(status.get('changes'),dict):
        blockers.append(status.get('error') or 'actual capture identity status unavailable')
        return result
    if not status.get('current_round_version'):
        result['capture']={'required':True,'scope':'initial complete matrix'}
        blockers.append('no baseline round; verify an actual source/export binding before the first complete capture')
    else:
        changes=status['changes'];source=changes.get('source');exported=changes.get('export')
        if any(changes.get(k) not in (True,False) for k in ('source','export','matrix','collector')):
            blockers.append('incomplete before/after identity comparison');return result
        if not source and not exported:
            result['build']={'required':False,'reason':'source and actual export hashes unchanged'}
            if changes['matrix'] or changes['collector']:
                result['capture']={'required':None,'reason':'capture contract/collector changed; map exact affected cases before deciding'}
                blockers.append('capture contract changes need case-level compatibility; do not automatically rebuild or recapture everything')
            else:
                result['capture']={'required':False,'reason':'source/export/matrix/collector unchanged; preserve current round and original evidence'}
        elif source and not exported:
            result['build']={'required':True,'reason':'source changed while actual export is unchanged'}
            result['capture']={'required':None,'reason':'wait for the verified actual export and exact impact map'}
            blockers.append('do not recapture stale export')
        else:
            result['build']={'required':None,'reason':'export already changed; verify source/export correspondence, do not build a second time by default'}
            result['capture']={'required':None,'reason':'changed export requires an explicit closed impact transition'}
        if source or exported:
            problems=impact_blockers(status,impact,set(case_ids));blockers.extend(problems)
            if not problems:
                affected=sorted({c for row in impact['files'] for c in row['cases']})
                result['capture'].update(candidate_affected_cases=affected,
                    candidate_unaffected_cases=sorted(set(case_ids)-set(affected)))
                blockers.append('impact declaration alone is not authority; supply an actual pre-change baseline/current round and verify original captures')
    if history_plan is not None:
        # Supplied by the owning history module after it reads the real current
        # round and recomputes the archived baseline; never by an impact flag.
        result['build']={'required':False,'reason':'history planner verified the actual initialized current source/export round'}
        result['capture']={'required':True,'scope':'verified forward dependency contract',
                           'fresh_cases':history_plan['fresh_cases'],
                           'candidate_reuse_cases':history_plan.get('reuse_cases',[]),
                           'anchors':history_plan.get('anchors',[]),'verified_current_ready':False}
        blockers[:]=[b for b in blockers if not b.startswith(('source/export changes have no explicit impact manifest',
            'impact declaration alone','do not recapture stale export'))]
        if history_plan.get('unknown'):
            blockers.extend(history_plan['unknown'])
            result['status']='scope_required'
            result['capture'].update(required=None,
                scope='repair explicit dependency ownership; no capture authorized')
    if verified_history is not None:
        if verified_history.get('ready') is True and not verified_history.get('error'):
            result['capture']={'required':False,'reason':'owning verifier validated all current original proofs and required anchors',
                               'verified_current_ready':True,'resolved_dumps':verified_history['resolved_dumps'],
                               'quality_promoted':False}
        else: blockers.append(verified_history.get('error') or 'capture history is incomplete')
    if history_error:
        blockers.append('owning capture history rejected inputs: '+history_error)
        result['capture']={'required':None,'verified_current_ready':False,'reason':'repair the precise provenance/dependency error before authorizing reuse'}
    rule_changes=set(changed_rules)
    rules_bound=all(isinstance(x,dict) and x and all(isinstance(k,str) and HASH.fullmatch(str(v)) for k,v in x.items())
                    for x in (rule_hashes_before,rule_hashes_after))
    if rules_bound:
        rule_changes.update(k for k in set(rule_hashes_before)|set(rule_hashes_after)
                            if rule_hashes_before.get(k)!=rule_hashes_after.get(k))
    bound_report=any(current_complete_report(report,verified_history) for _,report in reports)
    current_delta=any(status['changes'].get(k) for k in ('source','export','matrix','collector'))
    historical_delta=bool(history_plan and any(history_plan.get('dependency_diff',{}).values()))
    visual_change=current_delta or (historical_delta and not bound_report)
    result['analyze']={'required':True if failures or rule_changes or visual_change or reports and not bound_report else False if rules_bound else None,
                       'scope':'all reported blockers plus all changed-rule dependents',
                       'current_complete_report_verified':bound_report,
                       'changed_rules':sorted(rule_changes),
                       'reason':'reuse unchanged captures for tool/report-only changes; retain every prior failed item until fresh analysis resolves it'}
    if not rules_bound and not rule_changes:
        blockers.append('checker before/after fingerprints missing; an unchanged capture does not prove unchanged analysis rules')
    if reports and not bound_report:
        blockers.append('no complete analysis report is bound to the currently verified original case proofs')
    if not reports:
        result['analyze']['required']=None
        blockers.append('prior complete reports missing; initial full analysis must run once, not be inferred')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',type=Path);ap.add_argument('--build',type=Path)
    ap.add_argument('--status-json',type=Path)
    ap.add_argument('--report',type=Path,action='append',default=[])
    ap.add_argument('--changed-rule',action='append',default=[])
    ap.add_argument('--impact',type=Path);ap.add_argument('--matrix',type=Path)
    ap.add_argument('--rules-before',type=Path);ap.add_argument('--rules-after',type=Path)
    ap.add_argument('--baseline',type=Path,help='Actual pre-change initialized case baseline, not an impact assertion')
    ap.add_argument('--base-dumps',type=Path);ap.add_argument('--dumps',type=Path,help='Existing current capture directory to verify before declaring capture ready')
    args=ap.parse_args(argv)
    read=lambda p:json.loads(p.read_text())
    if args.status_json:status=read(args.status_json)
    elif args.project and args.build:
        proc=subprocess.run(['node',str(Path(__file__).with_name('art_capture_round.mjs')),'status',str(args.project),str(args.build)],capture_output=True,text=True,timeout=180)
        status=json.loads(proc.stdout) if proc.stdout else {'error':proc.stderr.strip() or 'capture status unavailable'}
    else:ap.error('provide --status-json or both --project and --build')
    reports=[(str(p),read(p)) for p in args.report]
    matrix=read(args.matrix) if args.matrix else {}
    history_plan=verified_history=history_error=None
    if args.baseline or args.dumps:
        if not args.project or not args.build:ap.error('history planning/verification requires actual --project and --build')
        try:
            from art_capture_history import transition_plan, verify
            if args.baseline:
                if not args.base_dumps:ap.error('--baseline requires --base-dumps')
                history_plan=transition_plan(args.project,args.build,args.baseline,args.base_dumps)
            if args.dumps:verified_history=verify(args.project,args.build,args.dumps)
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:history_error=str(exc)
    result=plan(status,reports,args.changed_rule,read(args.impact) if args.impact else None,
                [c['id'] for c in matrix.get('cases',[])],
                read(args.rules_before) if args.rules_before else None,
                read(args.rules_after) if args.rules_after else None,
                history_plan,verified_history,history_error)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
