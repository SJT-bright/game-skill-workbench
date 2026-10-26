"""Calibrate the explicit-source-maintenance gate against real supplied artifacts.
Does not create a ZIP or count as gameplay evidence. All mutations are isolated
review copies; production artifacts and original review stay unchanged.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from audit_source_maintenance import audit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['project','native','web','review','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--build-tag',required=True)
    a=p.parse_args();original=json.loads(a.review.read_text());rows=[]
    def trial(name,change,expected):
        review=deepcopy(original);change(review)
        with tempfile.TemporaryDirectory(prefix='source-maintenance-gate-') as td:
            target=Path(td)/'review.json';target.write_text(json.dumps(review))
            args=SimpleNamespace(project=a.project,native=a.native,web=a.web,review=target,build_tag=a.build_tag,stage='pre_scan')
            try:result=audit(args);actual=result['status']=='passed';errors=result['errors']
            except (ValueError,OSError,KeyError,TypeError,AttributeError) as e:actual=False;errors=[str(e)]
        rows.append(dict(id=name,passed=actual==expected,expected_accept=expected,actual_accept=actual,errors=errors))
    trial('current_actual_evidence',lambda r:None,True)
    trial('authorization_missing',lambda r:r.update(authorization=''),False)
    trial('stale_source_binding',lambda r:r['binding'].update(source_sha256='0'*64),False)
    trial('source_change_not_reviewed',lambda r:r.update(reviewed_source_changes=[]),False)
    trial('missing_storage_report',lambda r:r['checks']['STORAGE-01'].update(auto_reports=[]),False)
    trial('missing_loading_report',lambda r:r['checks']['LOAD-03'].update(auto_reports=[]),False)
    trial('failed_audio_observation',lambda r:r['checks']['AUDIO'].update(status='fail'),False)
    trial('missing_check_domain',lambda r:r['checks'].pop('PAGES'),False)
    trial('reduced_business_inventory',lambda r:r['business_execution'].update(required_cases=[]),False)
    trial('changed_coverage_evidence',lambda r:r['runtime_coverage'].update(sha256='0'*64),False)
    trial('missing_startup_matrix',lambda r:r.update(startup_runs=[]),False)
    trial('changed_startup_plan',lambda r:r['startup_plan'].update(sha256='0'*64),False)
    trial('changed_visual_evidence',lambda r:r['visual_review'].update(sha256='0'*64),False)
    trial('changed_historical_package',lambda r:r['baseline_zip'].update(sha256='0'*64),False)
    report=dict(passed=all(r['passed']for r in rows),binding=original['binding'],checked=len(rows),failed=sum(not r['passed']for r in rows),cases=rows)
    a.out.write_text(json.dumps(report,indent=2));print(json.dumps(dict(passed=report['passed'],checked=len(rows),failed=report['failed'])));return not report['passed']

if __name__=='__main__':raise SystemExit(main())
