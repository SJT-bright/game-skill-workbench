"""Real subprocess exit/timeout and timing contract, no game/browser execution."""
import json,tempfile,unittest
from pathlib import Path
from check_runner import run_tool,read_timings
class RunnerTests(unittest.TestCase):
    def test_success_failure_timeout_are_distinct_and_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);logs=p/'logs';logs.mkdir()
            for name,body in [('ok.py','print("ok")'),('bad.py','raise SystemExit(3)'),('slow.py','import time;time.sleep(1)')]:
                (p/name).write_text(body)
            self.assertEqual(run_tool('ok.py',[],logs,p,2)[0],0)
            self.assertEqual(run_tool('bad.py',[],logs,p,2)[0],3)
            self.assertEqual(run_tool('slow.py',[],logs,p,.05)[0],-1)
            rows=read_timings(logs);self.assertEqual([r['exit_code'] for r in rows],[0,3,-1]);self.assertTrue(all(r['elapsed_seconds']>=0 for r in rows))
            self.assertIn('elapsed_seconds=',(logs/'ok.log').read_text())
if __name__=='__main__':unittest.main()
