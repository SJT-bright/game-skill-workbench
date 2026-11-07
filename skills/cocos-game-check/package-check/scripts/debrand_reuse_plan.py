"""Scoped R18 -> R19 writer plan; original generic/PLAY plans stay unchanged."""
import importlib.util,json,os
from pathlib import Path
def plan(base,old_zip,new_files,adapter,policy,board):
 import ad_regression as A,runtime_regression as R
 def need(ok,why):
  if not ok:raise ValueError('scoped debrand reuse refused: '+why)
 old_zip=Path(old_zip);oldfiles=base.read_zip(old_zip);rp,receipt,problem=base.official_record(old_zip,oldfiles);need(not problem,str(problem))
 file=Path(__file__).with_name('debrand_delta_guard.py');s=importlib.util.spec_from_file_location('_writer_debrand_delta',file);g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
 adapter=base._adapter_path(adapter);proof=g.validate(old_zip,new_files,adapter)
 ad=receipt['regressions']['rewarded_ad_regression'];rt=receipt['regressions']['runtime_regression'];catalog=R.load_suites();names=R.required_suites(new_files,adapter,catalog)
 need(sorted(names)==sorted(rt.get('required')or[]),'required suite set differs from R18')
 need(set(names)<={r.get('suite')for r in rt.get('suites',[])if r.get('passed')is True},'R18 required suite record incomplete')
 need(R.package_policy(new_files,policy)[0]==rt.get('policy'),'package policy differs')
 need((board if board in R.BOARDS else None)==(rt.get('board')or None),'board differs')
 need(R.detect_engine(new_files,R.load_adapter(adapter,catalog))==rt.get('engine'),'engine differs')
 need(A.needs_regression(new_files)and ad.get('status')=='passed','ad applicability changed')
 rerun=base._closure(names,set(proof['rerun'])&set(names),catalog);changes=base.diff(oldfiles,new_files)
 return {'schema':base.SCHEMA,'reuse':True,'why':None,'old':{'zip':str(old_zip),'zip_sha256':base._sha_file(old_zip),'name':old_zip.name,'receipt':str(rp),'written':receipt.get('created'),'tool':receipt.get('tool')},'changes':base.summary_of_changes(changes),'required':list(names),'rerun':[n for n in names if n in rerun],'reused':[n for n in names if n not in rerun],'ad':'reuse','records':{'rewarded_ad_regression':ad,'runtime_regression':rt},'debrand_delta':proof,'before_home':rt.get('startup_measured',{}).get('beforeHome'),'startup_hit':['main']}
