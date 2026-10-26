#!/usr/bin/env python3
"""Bounded regression of fused cleanup: own completed helpers close; old identity and user control survive."""
import importlib.util,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
class CleanupBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='fused-cleanup-');self.addCleanup(self.tmp.cleanup)
  spec=importlib.util.spec_from_file_location('fused_slots',HERE/'browser_slots.py');self.s=importlib.util.module_from_spec(spec)
  with patch.dict(os.environ,{'GAME_SKILL_LOCK_DIR':self.tmp.name}):spec.loader.exec_module(self.s)
 def child(self):
  p=subprocess.Popen([sys.executable,'-c','import time; print("READY", flush=True); time.sleep(20)'],stdout=subprocess.PIPE,text=True)
  self.assertEqual(p.stdout.readline().strip(),'READY')
  def finish():
   if p.poll()is None:p.terminate()
   p.wait(timeout=4);p.stdout.close()
  self.addCleanup(finish);return p
 def slot(self,kind='touch_run',**kw):return self.s.register(kind,'isolated test',**kw)
 def edit(self,sid,**fields):
  p=self.s.SLOTS/(sid+'.json');d=json.loads(p.read_text());d.update(fields);p.write_text(json.dumps(d));return d
 def test_kept_preview_does_not_expire(self):
  p=self.child();sid=self.slot('preview',pid=p.pid,keep=True);d=self.edit(sid,created_ts=time.time()-24*3600,heartbeat_ts=time.time()-24*3600);self.assertIsNone(self.s.why_free(d))
 def test_current_completed_helper_really_exits(self):
  p=self.child();sid=self.slot(pid=p.pid);self.edit(sid,state='done');r=self.s.sweep(close=True);p.wait(timeout=4);self.assertIn(sid,{x['id']for x in r['freed']});self.assertIsNotNone(p.returncode)
 def test_reused_identity_not_signalled(self):
  p=self.child();sid=self.slot(pid=p.pid);self.edit(sid,state='done',process_identity='old-process-fingerprint');r=self.s.sweep(close=True);self.assertIsNone(p.poll());self.assertIn(sid,{x['id']for x in r['review_candidates_not_closed']})
 def test_legacy_pid_without_identity_not_signalled(self):
  p=self.child();sid=self.slot(pid=p.pid);self.edit(sid,state='done',process_identity=None);self.s.sweep(close=True);self.assertIsNone(p.poll());self.assertTrue((self.s.SLOTS/(sid+'.json')).exists())
 def test_live_idle_is_candidate_not_killed(self):
  p=self.child();sid=self.slot(pid=p.pid);self.edit(sid,heartbeat_ts=time.time()-3600);r=self.s.sweep(close=True);self.assertIsNone(p.poll());self.assertIn(sid,{x['id']for x in r['review_candidates_not_closed']})
 def test_old_ego_id_not_blindly_taken_over(self):
  sid=self.slot('ego_space',space_id=123);self.edit(sid,heartbeat_ts=time.time()-3600)
  with patch.object(self.s.subprocess,'run',wraps=self.s.subprocess.run)as run:
   r=self.s.sweep(close=True)
   self.assertFalse(any('ego-browser' in str(call)for call in run.call_args_list))
  self.assertTrue((self.s.SLOTS/(sid+'.json')).exists());self.assertEqual(r['ego_spaces_to_finish_by_hand'][0]['space_id'],123)
 def test_gone_owner_record_retires(self):
  p=subprocess.Popen([sys.executable,'-c','pass']);p.wait();sid=self.slot(pid=p.pid);r=self.s.sweep(close=True);self.assertIn(sid,{x['id']for x in r['freed']})
 def test_snapshot_release_cannot_delete_external_directory(self):
  safe=Path(self.tmp.name)/'original';safe.mkdir();(safe/'keep.txt').write_text('keep');sid=self.slot('preview',directory=safe);self.s.release(sid);self.assertEqual((safe/'keep.txt').read_text(),'keep')
class LiveWriterLockTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='fused-live-lock-');self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/'game';self.project.mkdir()
  self.env={**os.environ,'GAME_SKILL_LOCK_DIR':str(self.root/'locks')}
  self.tool=HERE/'heavy_lock.py'
 def command(self,*args):
  return subprocess.run([sys.executable,str(self.tool),*args],env=self.env,text=True,capture_output=True,timeout=8)
 def live_owner(self):
  code="import importlib.util,sys,time; from pathlib import Path; spec=importlib.util.spec_from_file_location('lock',sys.argv[1]); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.LOCK=m.project_lock(sys.argv[2]);assert m.try_acquire('live writer',3);print(str(m.LOCK),flush=True);time.sleep(30)"
  p=subprocess.Popen([sys.executable,'-c',code,str(self.tool),str(self.project)],env=self.env,text=True,stdout=subprocess.PIPE)
  self.addCleanup(lambda:p.poll()is None and (p.terminate(),p.wait(timeout=4)))
  lock=Path(p.stdout.readline().strip());owner=lock/'owner.json';d=json.loads(owner.read_text());d['started_ts']=time.time()-24*3600;owner.write_text(json.dumps(d));return p,lock,owner.read_bytes()
 def test_old_live_writer_cannot_be_displaced(self):
  p,lock,before=self.live_owner();marker=self.root/'must-not-run'
  r=self.command('run','--project',str(self.project),'--kind','write','--name','contender','--no-wait','--stale','0','--',sys.executable,'-c',"from pathlib import Path;Path(__import__('sys').argv[1]).write_text('ran')",str(marker))
  self.assertEqual(r.returncode,75,r.stdout+r.stderr);self.assertFalse(marker.exists());self.assertIsNone(p.poll());self.assertEqual((lock/'owner.json').read_bytes(),before)
 def test_force_cannot_release_live_writer(self):
  p,lock,before=self.live_owner();r=self.command('release','--force','--project',str(self.project))
  self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertIsNone(p.poll());self.assertEqual((lock/'owner.json').read_bytes(),before)
 def test_exited_owner_can_be_retired(self):
  p,lock,_=self.live_owner();p.terminate();p.wait(timeout=4)
  r=self.command('run','--project',str(self.project),'--kind','write','--name','successor','--no-wait','--',sys.executable,'-c','pass')
  self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(lock.exists())
 def test_unknown_owner_is_not_retired_by_age(self):
  r=self.command('status','--project',str(self.project));self.assertEqual(r.returncode,0)
  # Locate the isolated project lock with the same helper; no global lock touched.
  spec=importlib.util.spec_from_file_location('fused_lock_unknown',self.tool);m=importlib.util.module_from_spec(spec)
  with patch.dict(os.environ,self.env):spec.loader.exec_module(m)
  lock=m.project_lock(self.project);lock.mkdir(parents=True);os.utime(lock,(1,1))
  r=self.command('release','--force','--project',str(self.project));self.assertEqual(r.returncode,1);self.assertTrue(lock.exists())
class ExplicitCloseTests(CleanupBoundaryTests):
 def test_explicit_close_checks_identity_and_keeps_failed_record(self):
  p=self.child();sid=self.slot(pid=p.pid);self.edit(sid,process_identity='reused-pid')
  r=self.s.close(sid=sid)
  self.assertIsNone(p.poll());self.assertTrue((self.s.SLOTS/(sid+'.json')).exists())
  self.assertFalse(self.s.check('isolated test')['ok']);self.assertTrue(r['cleanup_pending'])
 def test_failed_termination_cannot_make_check_pass(self):
  p=self.child();sid=self.slot(pid=p.pid)
  with patch.object(self.s,'terminate',return_value=False):r=self.s.close(sid=sid)
  self.assertFalse(self.s.check('isolated test')['ok']);self.assertTrue(r['cleanup_pending'])
  self.assertTrue((self.s.SLOTS/(sid+'.json')).exists());self.assertIsNone(p.poll())
 def test_successful_explicit_close_really_exits(self):
  p=self.child();sid=self.slot(pid=p.pid);r=self.s.close(sid=sid);p.wait(timeout=4)
  self.assertFalse(r['cleanup_pending']);self.assertEqual([x['id'] for x in r['closed']],[sid])
  self.assertTrue(self.s.check('isolated test')['ok'])
 def test_missing_ego_tool_does_not_forget_space(self):
  sid=self.slot('ego_space',space_id=123)
  with patch.object(self.s.shutil,'which',return_value=None):r=self.s.close(sid=sid)
  self.assertTrue(r['cleanup_pending']);self.assertFalse(self.s.check('isolated test')['ok'])
  self.assertTrue((self.s.SLOTS/(sid+'.json')).exists())
 def test_ego_finish_only_accepts_confirmed_absence(self):
  sid=self.slot('ego_space',space_id=123)
  with patch.object(self.s,'ego_list',return_value={'spaces':[{'id':123}]}):
   with patch.object(self.s.subprocess,'run')as run:r=self.s.ego_finish([123])
   run.assert_not_called()
  self.assertTrue(r['cleanup_pending']);self.assertTrue((self.s.SLOTS/(sid+'.json')).exists())
  with patch.object(self.s,'ego_list',return_value={'spaces':[]}):r=self.s.ego_finish([123])
  self.assertFalse(r['cleanup_pending']);self.assertFalse((self.s.SLOTS/(sid+'.json')).exists())
 def test_unknown_ego_id_never_generates_takeover_code(self):
  with patch.object(self.s,'ego_list',return_value={'spaces':[{'id':70}]}):r=self.s.ego_finish([70])
  self.assertNotIn('taskSpace(',json.dumps(r));self.assertTrue(r['cleanup_pending'])
 def test_aborted_touch_context_cannot_be_retired_as_dead_process(self):
  sid=self.slot(pid=99999999);self.edit(sid,state='cleanup_pending',cleanup_pending=True)
  r=self.s.sweep(close=True);self.assertNotIn(sid,{x['id'] for x in r['freed']})
  self.assertTrue((self.s.SLOTS/(sid+'.json')).exists());self.assertFalse(self.s.check('isolated test')['ok'])
 def test_ego_cli_error_cannot_certify_empty_inventory(self):
  result=subprocess.CompletedProcess(['ego-browser'],1,'[]','hard stop')
  with patch.object(self.s.shutil,'which',return_value='/fake/ego-browser'),patch.object(self.s.subprocess,'run',return_value=result):
   self.assertIsNone(self.s.ego_list()['spaces']);self.assertEqual(self.s.finish_ego_space(123),'manual')
 def test_identity_read_failure_is_not_exit_proof(self):
  result=subprocess.CompletedProcess(['ps'],0,'S','')
  with patch.object(self.s,'alive',return_value=True),patch.object(self.s,'process_identity',side_effect=['original']+[None]*15),patch.object(self.s.os,'kill'),patch.object(self.s.time,'sleep'),patch.object(self.s.subprocess,'run',return_value=result):
   self.assertFalse(self.s.terminate(123,'original'))
if __name__=='__main__':unittest.main(verbosity=2)
