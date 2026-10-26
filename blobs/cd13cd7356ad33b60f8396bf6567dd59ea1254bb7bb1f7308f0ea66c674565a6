"""Run refusal tests against an already captured real browser report (no product mocks)."""
import argparse,copy,json,tempfile
from pathlib import Path
from audit_native_startup_renderer import validate,sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,required=True);ap.add_argument('--native',type=Path,required=True);ap.add_argument('--project',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 report=json.loads(a.report.read_text());binding=report['binding'];rows=[]
 def check(name,r,expect):
  errors=validate(r,a.native,binding,a.project);rows.append({'case':name,'passed':bool(errors)==expect,'errors':errors})
 check('actual_fixed_evidence',report,False)
 for name,mutate in [('missing_report_identity',lambda r:r.pop('schema',None)),('mismatched_source',lambda r:r['binding'].update(source_sha256='changed')),('missing_screenshot',lambda r:r.pop('screenshot',None)),('missing_negative',lambda r:r.pop('controls',None))]:
  r=copy.deepcopy(report);mutate(r);check(name,r,True)
 rawpath=Path(report['raw']['path']);rawpath=rawpath if rawpath.is_absolute() else a.project/rawpath
 raw=json.loads(rawpath.read_text())
 with tempfile.TemporaryDirectory(prefix='startup-gate-negative-') as td:
  for field in ['game_run_original','renderer_original','canvas_get_context_original']:
   d=copy.deepcopy(raw);d['engine_identity'][field]=False;p=Path(td)/'raw.json';p.write_text(json.dumps(d));r=copy.deepcopy(report);r['raw']={'path':str(p),'sha256':sha(p)};check('replace_'+field,r,True)
  for name,change in [('loading_scene_only',lambda d:d.pop('business',None)),('home_covered',lambda d:d['business']['home'].update(loading_overlay_gone=False)),('no_gameplay_change',lambda d:d['business']['play'].update(after=d['business']['play']['before'])),('hidden_first_exception',lambda d:d.update(first_exception={'message':'startup failed'}))]:
   d=copy.deepcopy(raw);change(d);p=Path(td)/'business-raw.json';p.write_text(json.dumps(d));r=copy.deepcopy(report);r['raw']={'path':str(p),'sha256':sha(p)};check(name,r,True)
  r=copy.deepcopy(report);r['raw']['sha256']='changed';check('changed_raw_bytes',r,True)
 out={'tool':'selftest_native_startup_renderer','scope':'evidence validator refusal tests; actual browser old/fixed/reintroduced executions remain separately required','passed':all(x['passed'] for x in rows),'cases':rows};a.out.write_text(json.dumps(out,indent=2));print(json.dumps(out));return 0 if out['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
