#!/usr/bin/env python3
"""Timing observes ready; synthetic service/authorization fixtures do not assert game acceptance."""
import contextlib
import importlib.util
import io
import json
import runpy
import signal
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('timed_preview',HERE/'serve_preview.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)


def events(root):
    p=root/'docs/timing/stage-timing.jsonl'
    return [json.loads(line) for line in p.read_text().splitlines()] if p.is_file() else []


class Hooks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.web=self.root/'web';self.web.mkdir()
        (self.root/'assets').mkdir()
        (self.web/'index.html').write_text('<html>fixture</html>')

    def test_chinese_only_records_ready_and_reopen_deduplicates_without_snapshot(self):
        args=['--directory',str(self.web),'--project',str(self.root),'--keep','--chinese-original']
        lines=[]
        G.gate(args,lines.append)
        self.assertEqual(events(self.root),[])
        ready=G.chinese_ready(args,lines.append)
        ready(self.web);ready(self.web)
        marks=[e for e in events(self.root) if e['ev']=='mark']
        self.assertEqual(len(marks),1)
        self.assertEqual(marks[0]['name'],'中文原版链接')
        (self.web/'index.html').write_text('<html>new identity</html>')
        ready(self.web)
        self.assertEqual(len([e for e in events(self.root) if e['ev']=='mark']),2)

    def test_returned_ready_counts_identity_not_log_length_or_authorization_timestamp(self):
        accepted={'web':{'sha256':'web1'},'native':{'sha256':'native1'},'manifest_sha256':'auth1'}
        fake=types.SimpleNamespace(validate=lambda *a,**kw:json.loads(json.dumps(accepted)),web_hash=lambda p:'web1',
            read=lambda p:json.loads(p.read_text()),write=lambda p,v:(p.parent.mkdir(parents=True,exist_ok=True),p.write_text(json.dumps(v))))
        with patch.dict(sys.modules,{'returned_art_acceptance':fake}):
            for idx in range(2):
                _,verify=G.returned_preview([],self.root,self.web,self.root/'native',lambda s:None)
                before=events(self.root)
                ready=verify(self.web)
                self.assertEqual(events(self.root),before)
                ready()
            self.assertEqual([e['n'] for e in events(self.root) if e['ev']=='link'],[1])
            accepted['manifest_sha256']='auth2'  # timestamp/evidence changes alone are not a new rendered build
            G.returned_preview([],self.root,self.web,self.root/'native',lambda s:None)[1](self.web)()
            self.assertEqual([e['n'] for e in events(self.root) if e['ev']=='link'],[1])
            accepted['native']['sha256']='native2'
            G.returned_preview([],self.root,self.web,self.root/'native',lambda s:None)[1](self.web)()
            self.assertEqual([e['n'] for e in events(self.root) if e['ev']=='link'],[1,2])

    def test_returned_failed_snapshot_never_records_ready(self):
        fake=types.SimpleNamespace(validate=lambda *a,**kw:{'web':{'sha256':'a'},'native':{'sha256':'n'},'manifest_sha256':'m'},web_hash=lambda p:'wrong')
        with patch.dict(sys.modules,{'returned_art_acceptance':fake}):
            _,verify=G.returned_preview([],self.root,self.web,self.root/'native',lambda s:None)
            with self.assertRaises(SystemExit),contextlib.redirect_stderr(io.StringIO()):verify(self.web)
        self.assertEqual(events(self.root),[])

    def shared(self,ready,entry_ok=True,bind_ok=True):
        mod=runpy.run_path(str(HERE.parents[1]/'remake-core/scripts/serve_preview.py'))
        f=mod['main']
        class Server:
            server_port=12345
            def __init__(self,*a,**kw):
                if not bind_ok:raise OSError('fixture bind failure')
            def serve_forever(self):pass
            def shutdown(self):pass
            def server_close(self):pass
        slots=types.SimpleNamespace(sweep=lambda **k:None,register=lambda *a,**k:None)
        replacements={'ThreadingHTTPServer':Server,'entry_readback':lambda *a,**k:(entry_ok,[],'fixture entry failure'),
                      'browser_request':lambda *a,**k:{'fixture':True}}
        with patch.dict(f.__globals__,replacements),patch.dict(sys.modules,{'browser_slots':slots}),patch.object(signal,'signal'),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            f(['--directory',str(self.web),'--project',str(self.root),'--keep','--no-browser','--idle-minutes','0'],chinese_original=True,on_ready=ready)

    def test_shared_hook_runs_after_entry_readback_without_snapshot(self):
        seen=[]
        self.shared(lambda directory:seen.append(Path(directory)))
        self.assertEqual(seen,[self.web.resolve()])

    def test_shared_failed_entry_or_listener_does_not_record_ready(self):
        for opts in ({'entry_ok':False},{'bind_ok':False}):
            seen=[]
            with self.assertRaises((SystemExit,OSError)):self.shared(lambda d:seen.append(d),**opts)
            self.assertEqual(seen,[])

    def test_timing_callback_failure_does_not_refuse_ready_service(self):
        def fail(d):raise OSError('fixture log failure')
        self.shared(fail)

    def test_english_entry_measures_start_to_ready_without_waiting_for_service_exit(self):
        args=['--directory',str(self.web),'--project',str(self.root),'--keep','--chinese-original']
        def service(argv,**kwargs):
            self.assertEqual([e['ev'] for e in events(self.root)],['begin'])
            kwargs['on_ready'](self.web)
            measured=[e for e in events(self.root) if e['ev']=='end']
            self.assertEqual(len(measured),1)
            self.assertEqual(measured[0]['state'],'completed')
            self.assertGreaterEqual(measured[0]['monotonic_seconds'],0)
            # Service is still executing here: duration has already been closed.
            kwargs['on_ready'](self.web)
        with patch.object(G.runpy,'run_path',return_value={'main':service}),contextlib.redirect_stdout(io.StringIO()):
            G.main(args)
        self.assertEqual(len([e for e in events(self.root) if e['ev']=='end']),1)
        self.assertEqual(len([e for e in events(self.root) if e['ev']=='mark']),1)

    def test_english_entry_failure_closes_failed_span_without_ready_link(self):
        args=['--directory',str(self.web),'--project',str(self.root),'--keep','--chinese-original']
        def service(argv,**kwargs):raise OSError('fixture bind failure')
        with patch.object(G.runpy,'run_path',return_value={'main':service}),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(OSError):
            G.main(args)
        rows=events(self.root)
        self.assertEqual([e['ev'] for e in rows],['begin','end'])
        self.assertEqual(rows[-1]['state'],'failed')

    def test_first_formal_ready_closes_stage_3_and_reports_stages(self):
        args = ['--directory',str(self.web),'--project',str(self.root),'--keep']
        G.timing(self.root,'start','--run-id','trial','--route','source')
        for stage in (1,2,3):
            G.timing(self.root,'stage',str(stage))
        def verify(snapshot):
            return lambda: G.timing(self.root,'publish','english:fixture')
        verify.report_phase_times = True
        verify.close_first_trial_phase = True
        def service(argv,**kwargs):
            self.assertNotIn('link',[row['ev'] for row in events(self.root)])
            kwargs['verify_snapshot'](self.web)()
            kwargs['on_ready'](self.web)
        output = io.StringIO()
        with patch.object(G,'gate',return_value=(args,verify)), \
             patch.object(G.runpy,'run_path',return_value={'main':service}),contextlib.redirect_stdout(output):
            G.main(args)
        self.assertEqual([e['ev'] for e in events(self.root)][-3:],['link','end','done'])
        self.assertIn('用时总表',output.getvalue())
        self.assertTrue((self.root/'docs/timing/timing-summary.json').is_file())


    def test_first_formal_stage_report_continues_after_observation_failure(self):
        args = ['--directory', str(self.web), '--project', str(self.root), '--keep']
        G.timing(self.root, 'stage', '3')
        verify = types.SimpleNamespace(report_phase_times=True, close_first_trial_phase=True)
        def service(argv, **kwargs):
            kwargs['on_ready'](self.web)

        output = io.StringIO()
        errors = io.StringIO()
        with patch.object(G, 'gate', return_value=(args, verify)), \
             patch.object(G.runpy, 'run_path', return_value={'main': service}), \
             patch('stage_timer.finish_observation', side_effect=OSError('fixture log error')), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            G.main(args)
        self.assertIn('fixture log error', errors.getvalue())
        self.assertIn('用时总表', output.getvalue())
        self.assertEqual(events(self.root)[-1]['ev'], 'done')


if __name__=='__main__':unittest.main()
