#!/usr/bin/env python3
"""Timing regression fixtures: synthetic clocks and owned tiny commands, never game acceptance."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run_stage_timer', HERE/'stage_timer.py')
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
BASE = 1793548800.0


class Runs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def call(self, second, *args, code=0):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            got = T.main(['--project', str(self.root), '--at', str(BASE+second), *args])
        self.assertEqual(got, code, out.getvalue())
        return out.getvalue()

    def timeline(self, now):
        rows, bad = T.load(self.root)
        return T.Timeline(rows, BASE+now, bad)

    def test_returned_run_excludes_old_delivery_and_overnight(self):
        self.call(0, 'start', '--run-id', 'initial')
        self.call(0, 'stage', '5'); self.call(600, 'mark', '交付'); self.call(600, 'done')
        self.call(86400, 'stage', '4')
        self.call(86400, 'begin', '返工', '--span-id', 'one')
        self.call(87600, 'end', '返工', '--span-id', 'one')
        tl = self.timeline(87600)
        self.assertNotEqual(tl.run_id, 'initial')
        self.assertEqual(tl.metrics()['wall_seconds'], 1200)
        self.assertNotIn('总计10分', tl.full_report())
        allrows, _ = T.load(self.root)
        old = T.Timeline(allrows, BASE+87600, run_id='initial')
        self.assertEqual(old.metrics()['wall_seconds'], 600)

    def test_pause_does_not_become_work(self):
        self.call(0, 'start', '--run-id', 'pause')
        self.call(0, 'begin', '制作', '--span-id', 'a')
        self.call(60, 'pause', '用户暂停')
        self.call(36060, 'resume')
        self.call(36120, 'end', '制作', '--span-id', 'a')
        m = self.timeline(36120).metrics()
        self.assertEqual(m['wall_seconds'], 36120)
        self.assertEqual(m['paused_seconds'], 36000)
        self.assertEqual(m['completed_work_interval_union_seconds'], 120)
        self.assertEqual(m['steps'][0]['seconds'], 120)

    def test_parallel_same_name_keeps_both_counts_and_union(self):
        self.call(0, 'begin', '美工', '--who', 'A', '--span-id', 'a')
        self.call(60, 'begin', '美工', '--who', 'B', '--span-id', 'b')
        self.call(120, 'end', '美工', '--span-id', 'b', '--count', '图=1')
        self.call(600, 'end', '美工', '--span-id', 'a', '--count', '图=2')
        m = self.timeline(600).metrics()
        self.assertEqual([s['seconds'] for s in m['steps']], [600, 60])
        self.assertEqual(sum(s['count']['图'] for s in m['steps']), 3)
        self.assertEqual(m['completed_work_interval_union_seconds'], 600)

    def test_ambiguous_end_does_not_close_wrong_worker(self):
        self.call(0, 'begin', '美工', '--who', 'A')
        self.call(10, 'begin', '美工', '--who', 'B')
        self.assertIn('多个执行者', self.call(20, 'end', '美工', code=2))
        self.assertEqual(len(self.timeline(20).metrics()['open_spans']), 2)
        self.call(30, 'end', '美工', '--who', 'B')
        self.assertEqual(len(self.timeline(30).metrics()['open_spans']), 1)

    def test_cross_stage_span_is_clipped_without_fabricated_end(self):
        self.call(0, 'stage', '2'); self.call(0, 'begin', '跨阶段', '--span-id', 'a')
        self.call(600, 'stage', '3')
        self.assertIsNone(self.timeline(600).steps[0]['end'])
        self.call(1200, 'end', '跨阶段', '--span-id', 'a', '--count', '图=3')
        tl = self.timeline(1200)
        self.assertIn('跨阶段：10 分', tl.stage_report(0))
        self.assertIn('跨阶段：10 分', tl.stage_report(1))
        self.assertNotIn('3 张图', tl.stage_report(0))
        self.assertIn('3 张图', tl.stage_report(1))

    def test_user_wait_and_work_can_overlap(self):
        self.call(0, 'stage', '4'); self.call(0, 'link', '1')
        self.call(0, 'begin', '准备', '--span-id', 'a')
        self.call(600, 'end', '准备', '--span-id', 'a'); self.call(600, 'back')
        m = self.timeline(600).metrics()
        self.assertEqual(m['completed_work_interval_union_seconds'], 600)
        self.assertEqual(m['user_wait_seconds'], 600)
        self.assertEqual(m['user_wait_work_overlap_seconds'], 600)
        self.assertEqual(m['unrecorded_seconds'], 0)

    def test_external_wait_separate(self):
        self.call(0, 'start', '--run-id', 'queue')
        self.call(10, 'external-begin', 'image', '生图排队')
        self.call(110, 'external-end', 'image')
        m = self.timeline(120).metrics()
        self.assertEqual(m['external_wait_seconds'], 100)
        self.assertEqual(m['unrecorded_seconds'], 20)
        self.assertEqual(m['completed_work_interval_union_seconds'], 0)

    def test_abort_retains_incomplete_and_stops_report_clock(self):
        self.call(0, 'begin', '仍在做', '--span-id', 'a')
        self.call(60, 'abort', '停止')
        m = self.timeline(3660).metrics()
        self.assertEqual(m['wall_seconds'], 60)
        self.assertTrue(m['aborted'])
        self.assertEqual(m['steps'][0]['state'], 'interrupted')
        self.assertEqual(m['completed_work_interval_union_seconds'], 0)

    def test_persist_failure_never_says_recorded(self):
        with patch.object(T, 'append', return_value=False):
            out = self.call(0, 'stage', '2')
        self.assertIn('not_recorded', out)
        self.assertNotIn('记下：', out)
        self.assertFalse((self.root/T.LOG).exists())

    def test_publish_deduplicates_identity_and_separates_native_change(self):
        self.call(0, 'start', '--run-id', 'links')
        self.call(10, 'publish', 'english:web:native1')
        self.call(20, 'publish', 'english:web:native1')
        self.call(30, 'publish', 'english:web:native2')
        self.assertEqual([x['n'] for x in self.timeline(30).links], [1,2])

    def test_explicit_new_run_cannot_hide_unfinished_run(self):
        self.call(0, 'start', '--run-id', 'first')
        with self.assertRaises(SystemExit): self.call(10, 'start', '--run-id', 'second')
        self.call(10, 'abort', '明确停止')
        self.call(20, 'start', '--run-id', 'second')
        self.assertEqual(self.timeline(20).run_id, 'second')

    def test_real_command_exit_and_seconds_and_live_log(self):
        log = self.root/'command.log'
        code = T.main(['--project',str(self.root),'run','--log',str(log),'实际命令','--',sys.executable,'-c','print("stream"); raise SystemExit(7)'])
        self.assertEqual(code, 7)
        self.assertIn('stream', log.read_text())
        rows,_=T.load(self.root)
        end=rows[-1]
        self.assertEqual(end['exit_code'],7)
        self.assertEqual(end['state'],'failed')
        self.assertGreater(end['monotonic_seconds'],0)
        self.assertEqual(rows[-2]['span_id'],end['span_id'])

    def test_unwritable_timing_does_not_suppress_command(self):
        marker=self.root/'actual.txt'
        with patch.object(T,'append',return_value=False):
            code=T.main(['--project',str(self.root),'run','command','--',sys.executable,'-c',
                         'from pathlib import Path; Path(%r).write_text("executed")'%str(marker)])
        self.assertEqual(code,0)
        self.assertEqual(marker.read_text(),'executed')

    def test_unwritable_returned_run_start_does_not_suppress_command(self):
        self.call(0,'mark','交付')
        marker=self.root/'returned-actual.txt'
        with patch.object(T,'append',return_value=False):
            code=T.main(['--project',str(self.root),'run','returned-command','--',sys.executable,'-c',
                         'from pathlib import Path; Path(%r).write_text("executed"); raise SystemExit(7)'%str(marker)])
        self.assertEqual(code,7)
        self.assertEqual(marker.read_text(),'executed')

    def test_json_report_preserves_seconds_not_rounded_minutes(self):
        self.call(0,'start','--run-id','fractions');self.call(0,'begin','a','--span-id','a')
        self.call(.125,'end','a','--span-id','a');self.call(.125,'report','--all')
        m=json.loads((self.root/'docs/timing/timing-summary.json').read_text())
        self.assertEqual(m['completed_work_interval_union_seconds'],.125)
        self.assertEqual(m['stages'][0]['wall_seconds'],.125)
        self.assertEqual(m['stages'][0]['completed_work_interval_union_seconds'],.125)

    def test_unwritable_command_log_still_executes(self):
        blocked=self.root/'file';blocked.write_text('not a directory')
        marker=self.root/'actual.txt'
        code=T.main(['--project',str(self.root),'run','--log',str(blocked/'run.log'),'command','--',sys.executable,'-c',
                     'from pathlib import Path; Path(%r).write_text("executed")'%str(marker)])
        self.assertEqual(code,0)
        self.assertEqual(marker.read_text(),'executed')
        self.assertEqual(T.load(self.root)[0][-1]['state'],'completed')

    def test_repeated_command_node_has_distinct_attempt_spans(self):
        for _ in range(2):
            self.assertEqual(T.main(['--project',str(self.root),'run','--span-id','build','构建导出','--',sys.executable,'-c','pass']),0)
        rows,_=T.load(self.root)
        begins=[e for e in rows if e['ev']=='begin']
        self.assertEqual(len({e['span_id'] for e in begins}),2)
        self.assertEqual({e['node_id'] for e in begins},{'build'})
        self.assertEqual(len(T.Timeline(rows,T.time.time()).steps),2)

    def test_clock_rollback_preserves_command_monotonic_and_flags_wall_totals(self):
        events=[dict(t=BASE,ev='begin',step='command',span_id='a',kind='tool',_i=0),
                dict(t=BASE-10,ev='end',step='command',span_id='a',kind='tool',monotonic_seconds=2.5,
                     clock_discontinuity=True,state='completed',exit_code=0,_i=1)]
        tl=T.Timeline(sorted(events,key=lambda e:e['t']),BASE+20)
        m=tl.metrics()
        self.assertEqual(m['steps'][0]['seconds'],2.5)
        self.assertFalse(m['wall_interval_totals_valid'])
        self.assertEqual(m['open_spans'],[])

    def test_observation_ends_at_ready_once_not_service_shutdown(self):
        with patch.object(T.time,'time',return_value=BASE),patch.object(T.time,'monotonic',return_value=100):
            obs=T.begin_observation(self.root,'试玩服务启动',node_id='preview/ready')
        with patch.object(T.time,'time',return_value=BASE+3),patch.object(T.time,'monotonic',return_value=103):
            T.finish_observation(obs)
        with patch.object(T.time,'time',return_value=BASE+3600),patch.object(T.time,'monotonic',return_value=3700):
            T.finish_observation(obs)
        rows,_=T.load(self.root)
        self.assertEqual(len(rows),2)
        m=self.timeline(3600).metrics()
        self.assertEqual(m['steps'][0]['seconds'],3)
        self.assertEqual(m['tool_interval_union_seconds'],3)
        self.assertEqual(m['unrecorded_seconds'],3597)

    def test_observation_write_failure_does_not_claim_recorded(self):
        out=io.StringIO()
        with patch.object(T,'append',return_value=False),contextlib.redirect_stderr(out),contextlib.redirect_stdout(out):
            obs=T.begin_observation(self.root,'试玩服务启动')
            T.finish_observation(obs)
        self.assertIn('not_recorded',out.getvalue())
        self.assertNotIn('节点｜',out.getvalue())

    def test_direct_returned_service_observation_starts_own_run(self):
        self.call(0,'start','--run-id','delivered')
        self.call(10,'mark','交付')
        with patch.object(T.time,'time',return_value=BASE+20),patch.object(T.time,'monotonic',return_value=100):
            obs=T.begin_observation(self.root,'试玩服务启动')
        with patch.object(T.time,'time',return_value=BASE+25),patch.object(T.time,'monotonic',return_value=105):
            T.finish_observation(obs)
        self.call(25,'publish','english:web:native','--run-id',obs['run_id'])
        self.assertNotEqual(obs['run_id'],'delivered')
        tl=self.timeline(25)
        self.assertEqual(tl.metrics()['wall_seconds'],5)
        self.assertEqual(tl.metrics()['steps'][0]['seconds'],5)
        self.assertEqual(len(tl.links),1)
        rows,bad=T.load(self.root)
        old=T.Timeline(rows,BASE+25,bad,run_id='delivered')
        self.assertEqual(old.metrics()['wall_seconds'],10)
        self.assertEqual(old.steps,[])
        self.assertEqual(old.links,[])

    def test_failed_returned_service_start_never_writes_to_old_run(self):
        self.call(0,'start','--run-id','delivered');self.call(10,'mark','交付')
        before=(self.root/T.LOG).read_bytes()
        with patch.object(T,'append',return_value=False):
            obs=T.begin_observation(self.root,'试玩服务启动')
            T.finish_observation(obs)
        self.assertFalse(obs['recorded'])
        self.assertNotEqual(obs['run_id'],'delivered')
        self.assertEqual((self.root/T.LOG).read_bytes(),before)

    def test_no_write_without_lock(self):
        class Unlocked:
            fd=None
            def __init__(self,*a,**kw):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
        with patch.object(T,'Lock',Unlocked),contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(T.append(self.root,{'ev':'test','t':BASE}))
        self.assertFalse((self.root/T.LOG).exists())


if __name__=='__main__':unittest.main()
