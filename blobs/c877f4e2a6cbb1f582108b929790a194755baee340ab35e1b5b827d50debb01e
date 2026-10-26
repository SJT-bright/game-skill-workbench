import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('accounting',Path(__file__).with_name('production_accounting.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
T='2026-10-26T00:00:00+00:00'
def base(): return [dict(type='project',name='game',at=T)]
def usage(rid='r1',owner='owner',**kw): return a.usage_record(dict(response_id=rid,usage=dict(input_tokens=100,cached_input_tokens=80,output_tokens=20,reasoning_output_tokens=5,total_tokens=120),model='m',**kw),'2026-10-26T00:01:00+00:00',owner,{})
class Accounting(unittest.TestCase):
 def test_overlapping_time_is_union(self):
  self.assertEqual(a.union([(0,10),(5,15),(15,20)]),20)
 def test_cache_reasoning_not_added(self):
  r=a.summary(base()+[usage()], '2026-10-26T00:02:00+00:00');self.assertEqual(r['usage']['known']['total_tokens'],120);self.assertEqual(r['usage']['known']['uncached_input_tokens'],20)
 def test_no_usage_is_unknown(self):
  self.assertEqual(a.summary(base(),T)['usage']['status'],'unknown_no_per_response_records')
 def test_invalid_subset_rejected(self):
  with self.assertRaises(ValueError): a.usage_record(dict(response_id='r',usage=dict(input_tokens=1,output_tokens=1,cached_input_tokens=2)),T,'o',{})
 def test_wrong_payload_owner_not_charged(self): self.assertIsNone(a.usage_record(dict(response_id='r',thread_id='other',usage=dict(input_tokens=1,output_tokens=1)),T,'owner',{}))
 def test_unallocated_not_duplicated(self):
  es=base()+[usage()]
  for phase in ['art','test']:
   es += [dict(type='start',id=phase,at=T,owner='owner',kind='work',phase=phase,task='task'),dict(type='stop',id=phase,at='2026-10-26T00:02:00+00:00',result='pass',tested=[],evidence=[])]
  r=a.summary(es,'2026-10-26T00:03:00+00:00');self.assertEqual(r['usage']['unallocated_tokens'],120);self.assertEqual(r['recorded_interval_union_seconds'],120)
 def test_price_table_not_bill(self):
  r=a.price_usage([usage()],dict(currency='USD',as_of='2026-10-26',source='controlled test rates',models={'m':dict(input_per_million=1,cached_input_per_million=.1,output_per_million=2)}));self.assertAlmostEqual(r['estimated_amount'],68/1000000);self.assertIsNone(r['actual_billed'])
 def test_missing_pricing_stays_unknown(self):
  r=a.price_usage([usage()],dict(currency='USD',as_of='x',source='test',models={}));self.assertEqual(r['unpriced_calls'],1)
 def test_incremental_dedup_inherited_and_partial(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'log.jsonl';meta=dict(type='session_meta',payload=dict(id='owner',timestamp=T))
   def event(rid,at=T): return dict(type='event_msg',timestamp=at,payload=dict(type='token_usage_record',response_id=rid,usage=dict(input_tokens=2,output_tokens=1),model='m'))
   p.write_text('\n'.join(map(json.dumps,[meta,event('inherited','2026-10-25T00:00:00Z'),event('r'),event('r'),dict(type='event_msg',timestamp=T,payload=dict(type='token_count'))]))+'\n'+json.dumps(event('later'))[:10])
   es=a.import_usage(p,[],'owner');self.assertEqual(len([e for e in es if e['type']=='usage']),1);self.assertEqual(es[-1]['legacy_events_ignored'],1)
   self.assertEqual(len(a.import_usage(p,es,'owner')),1)
   with p.open('r+') as f: f.seek(es[-1]['offset']); f.truncate();f.write(json.dumps(event('later'))+'\n')
   more=a.import_usage(p,es,'owner');self.assertEqual([e['id'] for e in more if e['type']=='usage'],['later'])
 def test_bound_window_excludes_other_project_and_post_close(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'log';meta=dict(type='session_meta',payload=dict(id='o',timestamp=T))
   def ev(rid,minute): return dict(type='event_msg',timestamp=f'2026-10-26T00:{minute:02}:00+00:00',payload=dict(type='token_usage_record',response_id=rid,usage=dict(input_tokens=2,output_tokens=1)))
   p.write_text('\n'.join(map(json.dumps,[meta,ev('before',1),ev('inside',3),ev('unbound',5),ev('postclose',9)]))+'\n')
   events=base()+[dict(type='bind',owner='o',at='2026-10-26T00:02:00+00:00'),dict(type='unbind',owner='o',at='2026-10-26T00:04:00+00:00'),dict(type='close',at='2026-10-26T00:08:00+00:00')]
   self.assertEqual([e['id'] for e in a.import_usage(p,events,'o') if e['type']=='usage'],['inside'])
 def test_missing_cache_is_not_zero_and_no_usage_no_price(self):
  u=a.usage_record(dict(response_id='r',usage=dict(input_tokens=3,output_tokens=1)),T,'o',{})
  r=a.summary(base()+[u],T);self.assertIsNone(r['usage']['known']['cached_input_tokens']);self.assertIsNone(r['usage']['known']['uncached_input_tokens'])
  price=a.price_usage([],dict(models={},as_of='x',source='test',currency='USD'));self.assertIsNone(price['estimated_amount'])
 def test_owner_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'l';p.write_text(json.dumps(dict(type='session_meta',payload=dict(id='other',timestamp=T)))+'\n')
   with self.assertRaises(ValueError): a.import_usage(p,[],'owner')
 def test_run_records_failed_exit(self):
  with tempfile.TemporaryDirectory() as d:
   script=str(Path(__file__).with_name('production_accounting.py'))
   def run(*args): return subprocess.run([sys.executable,script,'--project',d,*args],capture_output=True,text=True)
   run('init','--name','game');run('bind','--owner','o')
   result=run('run','--owner','o','--phase','test.input','--task','negative exit','--tested','controlled failure','--',sys.executable,'-c','raise SystemExit(3)')
   self.assertEqual(result.returncode,3)
   rows=a.read(Path(d)/'docs/production/accounting.jsonl');self.assertEqual(rows[-1]['exit_code'],3);self.assertEqual(rows[-1]['result'],'fail')
 def test_cli_lifecycle_and_close_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   script=str(Path(__file__).with_name('production_accounting.py'));root=Path(d)
   def run(*args): return subprocess.run([sys.executable,script,'--project',d,*args],capture_output=True,text=True)
   self.assertEqual(run('init','--name','game','--at',T).returncode,0)
   self.assertEqual(run('bind','--owner','o').returncode,0)
   self.assertEqual(run('start','--id','t','--phase','test.touch','--task','cancel and resume','--owner','o','--at',T).returncode,0)
   self.assertNotEqual(run('close').returncode,0)
   self.assertEqual(run('stop','--id','t','--result','pass','--tested','cancel does not commit','--at','2026-10-26T00:01:00Z').returncode,0)
   self.assertEqual(run('close','--at','2026-10-26T00:02:00Z').returncode,0)
   self.assertEqual(run('close').returncode,0)
   r=json.loads((root/'docs/production/summary.json').read_text());self.assertTrue(r['closed']);self.assertEqual(r['wall_seconds'],120);self.assertEqual(r['tasks'][0]['tested'],['cancel does not commit']);self.assertIsNone(r['phases']['test.touch']['tokens'])

if __name__=='__main__': unittest.main()
