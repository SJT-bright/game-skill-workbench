"""Handoff timing covers artifacts and failure paths without opening a browser."""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import importlib.util,json,tempfile,time,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('timed_handoff',HERE/'handoff_preview.py');H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
class HandoffTiming(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();(self.root/'assets').mkdir();H.stage_timer.call(self.root,'start','--route','source');H.stage_timer.call(self.root,'stage','5')
 def events(self):return [json.loads(x) for x in (self.root/'docs/timing/stage-timing.jsonl').read_text().splitlines()]
 def run_handoff(self,fail=False,telemetry_failure=False):
  url='http://127.0.0.1:39999/';slot={'kind':'preview','url':url,'project':str(self.root),'keep':True,'dir':'fixture','id':'fixture'};plan={'preview_url':url,'mode':'package','web_tree_sha256':'same','require_ad_simulator':False};now=[0.0]
  real_time=time.time();real_mono=time.monotonic()
  class Clock:
   def time(self):return real_time+now[0]
   def monotonic(self):return real_mono+now[0]
   def __getattr__(self,n):return getattr(time,n)
  def artifacts(*args):
   now[0]+=5
   if fail:raise ValueError('controlled artifact failure')
   return {'status':'team_handoff_ready','reply_lines':['test','source','evidence']}
  with ExitStack() as s:
   for obj,name,value in [(H,'time',Clock()),(H.stage_timer,'time',Clock())]:s.enter_context(patch.object(obj,name,value))
   s.enter_context(patch.object(H.browser_slots,'slots',return_value=[slot]));s.enter_context(patch.object(H,'validate_plan',side_effect=lambda x:x));s.enter_context(patch.object(H,'packaged_trial',return_value=('same',{})));s.enter_context(patch.object(H,'verify_preview',return_value={'slot_id':'fixture','ad_simulator':False}));s.enter_context(patch.object(H,'team_handoff',side_effect=artifacts));s.enter_context(patch.object(H,'render',return_value='fixture'));s.enter_context(patch.object(H,'serve_checklist',return_value=url+'__playtest/'));browser=s.enter_context(patch.object(H.preview_chrome,'browser_request',return_value={'status':'not_requested'}))
   if telemetry_failure:s.enter_context(patch.object(H.stage_timer,'begin_observation',side_effect=OSError('controlled telemetry unavailable')))
   if fail:
    with self.assertRaisesRegex(ValueError,'artifact failure'):H.handoff(self.root,url,'package',plan,self.root/'delivery.json',no_browser=True)
    browser.assert_not_called();return None
   return H.handoff(self.root,url,'package',plan,self.root/'delivery.json',no_browser=True)
 def test_artifacts_are_in_node_and_whole_handoff_time(self):
  r=self.run_handoff();self.assertAlmostEqual(r['handoff_timings']['nodes']['team.artifacts']['seconds'],5);self.assertGreaterEqual(r['handoff_timings']['total_seconds'],5)
  rows=self.events();node=next(x for x in rows if x.get('ev')=='begin' and x.get('node_id')=='handoff/team.artifacts');end=next(x for x in rows if x.get('ev')=='end' and x.get('span_id')==node['span_id']);self.assertEqual(end['state'],'completed');self.assertAlmostEqual(end['monotonic_seconds'],5);self.assertLess(rows.index(end),next(i for i,x in enumerate(rows) if x['ev']=='done'))
 def test_failure_is_closed_and_phase_not_completed(self):
  self.run_handoff(fail=True);rows=self.events();node=next(x for x in rows if x.get('node_id')=='handoff/team.artifacts');end=next(x for x in rows if x.get('ev')=='end' and x.get('span_id')==node['span_id']);self.assertEqual(end['state'],'failed');self.assertFalse(any(x['ev']=='done' for x in rows))
 def test_missing_telemetry_cannot_block_an_otherwise_valid_handoff(self):
  r=self.run_handoff(telemetry_failure=True);self.assertEqual(r['status'],'handoff_ready');self.assertEqual(r['handoff_timings']['nodes']['team.artifacts']['state'],'completed')
if __name__=='__main__':unittest.main()
