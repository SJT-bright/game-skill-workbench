"""CLI scope tests; mocked execution results are not game runtime evidence."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import audit_startup_contract as contract
class RuntimeOnly(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.native=self.root/'native';self.native.mkdir();self.binding=self.root/'binding.json';self.binding.write_text(json.dumps({'binding':{'fixture':True}}));self.proof=self.root/'proof.json';self.proof.write_text('{}');self.out=self.root/'out.json'
 def tearDown(self):self.temp.cleanup()
 def invoke(self,extra,errors):
  argv=['audit_startup_contract','--runtime-only','--project',str(self.root)]+extra
  with patch('sys.argv',argv),patch.object(contract,'validate_runtime_report',return_value=errors)as run,patch.object(contract,'scan_source',side_effect=AssertionError('runtime mode must not scan unrelated source')),contextlib.redirect_stdout(io.StringIO()):status=contract.main()
  return status,run
 def args(self):return['--native',str(self.native),'--binding',str(self.binding),'--renderer-report',str(self.proof),'--out',str(self.out)]
 def test_missing_actual_proof_refuses(self):
  status,run=self.invoke([],[]);self.assertEqual(status,1);run.assert_not_called();self.assertFalse(self.out.exists())
 def test_runtime_failure_cannot_be_passed(self):
  status,run=self.invoke(self.args(),['HOME still loading']);self.assertEqual(status,1);run.assert_called_once();self.assertFalse(json.loads(self.out.read_text())['passed'])
 def test_runtime_mode_still_executes_validator(self):
  status,run=self.invoke(self.args(),[]);self.assertEqual(status,0);run.assert_called_once();d=json.loads(self.out.read_text());self.assertTrue(d['runtime_required']);self.assertEqual(d['policy_version'],2)
if __name__=='__main__':unittest.main()
