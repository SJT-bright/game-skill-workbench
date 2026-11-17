import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mouse_gate',HERE/'preview_mouse_gate.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
PLAN={'schema':'preview_mouse_plan.v1','ready':'true','start':{'click':[10,10]},'started':'window.gameStarted','operations':[{'drag':[[20,20],[40,40]]}],'operation_state':'window.score','operation_ok':'window.score>0'}
class GateTests(unittest.TestCase):
 def test_missing_gameplay_fails(self):
  with self.assertRaises(ValueError):M.validate_plan(dict(PLAN,operations=[]))
 def test_touch_only_plan_fails(self):
  with self.assertRaises(ValueError):M.validate_plan(dict(PLAN,start={'touch':[10,10]}))
 def test_nonlocal_target_fails(self):
  with self.assertRaises(ValueError):M.check('https://example.com','missing','missing')
 def test_missing_plan_blocks_handoff(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):M.handoff_check('http://127.0.0.1:1/',Path(d))
 def simulate(self,**changes):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'plan.json';p.write_text(json.dumps(PLAN));o=root/'out.json'
   def run(argv,**kw):
    script=argv[-1];config=json.loads(script.split('const CFG = ',1)[1].split(';\n',1)[0]);r={'passed':True,'space_closed':True,'input_transport':'ego_page_mouse','url':config['url']};r.update(changes);o.write_text(json.dumps(r));o.with_suffix('.png').write_bytes(b'unit-image');return SimpleNamespace(returncode=0,stderr='')
   return M.check('http://127.0.0.1:1/',p,o,run=run,executable='ego-browser')
 def test_mouse_result_accepted(self):self.assertTrue(self.simulate()['passed'])
 def test_touch_substitution_rejected(self):
  with self.assertRaises(ValueError):self.simulate(input_transport='ego_page_cdp')
 def test_no_business_change_rejected(self):
  with self.assertRaises(ValueError):self.simulate(passed=False,error='no gameplay change')
 def test_unclosed_test_space_rejected(self):
  with self.assertRaises(ValueError):self.simulate(space_closed=False)
 def test_serve_gate_before_link_and_browser(self):
  s=(HERE/'serve_preview.py').read_text();gate=s.index('mouse_result = handoff_check');self.assertLess(gate,s.index('if record_ready_trial is not None:',gate));self.assertIn("raise SystemExit('不给试玩链接：真实鼠标检查未通过：'",s)
 def test_h5_gate_before_chrome(self):
  p=HERE.parents[1]/'cocos-game-to-english/scripts/handoff_preview.py'
  if not p.exists():self.skipTest('English H5 is not bundled in this installation')
  s=p.read_text();self.assertLess(s.index('mouse_observation = handoff_check'),s.index('browser = preview_chrome.browser_request'))
if __name__=='__main__':unittest.main()
