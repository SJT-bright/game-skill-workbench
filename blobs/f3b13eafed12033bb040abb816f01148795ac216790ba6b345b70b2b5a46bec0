"""English entry routing; the shared gate owns the full business/UI audit."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[1]/'remake-core/scripts'))
import test_serve_preview_gate as F
import ad_nodes_gate
class AdStandardEnglishEntry(unittest.TestCase):
 def test_missing_six_refuses_before_a_formal_trial(self):
  with tempfile.TemporaryDirectory() as td:
   root,web=F.make_game(td)
   with self.assertRaises(SystemExit) as caught, patch('sys.stderr',new_callable=io.StringIO) as err:
    F.GATE.gate(['--directory',str(web),'--native',str(F.native_dir(root)),'--snapshot','--keep'],say=lambda x:None)
   self.assertEqual(caught.exception.code,1)
   self.assertIn('六标准广告',err.getvalue())
   self.assertFalse((root/'docs/english/chinese-audit/trial-links.json').exists())
 def test_trial_route_calls_same_bundle_stage_then_existing_checks(self):
  with tempfile.TemporaryDirectory() as td:
   root,web=F.make_game(td)
   F.scan(root,web,F.env_for(td))
   with patch.object(ad_nodes_gate,'check_project',return_value={'passed':True,'problems':[],
     'scope':'synthetic route-only callback, no visual approval'}) as check:
    _,verify=F.GATE.gate(['--directory',str(web),'--native',str(F.native_dir(root)),'--snapshot','--keep'],say=lambda x:None)
   self.assertTrue(callable(verify))
   self.assertEqual(check.call_args.kwargs['stage'],'trial')
   self.assertEqual(Path(check.call_args.args[0]).resolve(),root.resolve())
 def test_internal_and_explicit_draft_can_continue_work(self):
  with patch.object(ad_nodes_gate,'check_project',side_effect=AssertionError('internal is not formal')):
   self.assertIsNone(F.GATE.gate(['--directory','/nowhere','--snapshot','--name','qa'])[1])
   with tempfile.TemporaryDirectory() as td:
    root,web=F.make_game(td)
    _,verify=F.GATE.gate(['--directory',str(web),'--snapshot','--keep','--draft'],say=lambda x:None)
    self.assertTrue(callable(verify))
if __name__=='__main__':unittest.main()
