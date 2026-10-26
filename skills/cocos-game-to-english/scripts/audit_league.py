#!/usr/bin/env python3
"""Compatibility command: enforce ranking prohibition, never enable League."""
import argparse,json,sys
from pathlib import Path
from audit_no_social_features import audit as no_social

def audit(proj, board=None, reference=None):
    project=Path(proj);result=no_social(project)
    decision=project/'docs/league/decision.json';blocked=False
    if decision.is_file():
        data=json.loads(decision.read_text());blocked=data.get('decision') not in ('none','skip')
    checks=[{'id':'ranking_disabled','passed':result['passed'] and not blocked,
             'detail':'No ranking/share code, routes or enabling decisions.' if result['passed'] and not blocked else 'Ranking/share remains or an obsolete add/keep_original decision is present.'}]
    return {'tool':'audit_league','schema':2,'status':'pass' if all(x['passed'] for x in checks) else 'fail','passed':all(x['passed'] for x in checks),'checked':len(checks),'failed':sum(not x['passed'] for x in checks),'checks':checks,'no_social':result}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--board');p.add_argument('--out',type=Path,required=True);p.add_argument('--binding');p.add_argument('--reference',type=Path,help=argparse.SUPPRESS);a=p.parse_args()
    try:r=audit(a.project,a.board,a.reference)
    except (ValueError,OSError,TypeError) as e:r={'passed':False,'errors':[str(e)]}
    if a.binding:
        r['binding']=json.loads(Path(a.binding).read_text()).get('binding')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False));sys.exit(0 if r['passed'] else 1)
