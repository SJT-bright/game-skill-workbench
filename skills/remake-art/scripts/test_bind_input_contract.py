import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import bind_art as B


class InputContract(unittest.TestCase):
    def test_map_and_rows_need_explicit_object_shape(self):
        for data in [[], {}, {'bindings': {}}, {'bindings': [1]},
                     {'bindings': [{'prefab': 3, 'node': 'Panel', 'image': 'assets/a.png'}]}]:
            with self.subTest(data=data), self.assertRaises(B.BindError):
                B.resolve_bindings(data, None, Path('.'))

    def test_cli_bad_shape_and_bad_json_report_no_write_not_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp);(project/'assets').mkdir();mapfile=project/'bind.json'
            for text in ['[]', '{broken']:
                mapfile.write_text(text);before={p.relative_to(project).as_posix():p.read_bytes() for p in project.rglob('*') if p.is_file()}
                result=subprocess.run([sys.executable,'-B',str(Path(B.__file__)),'--project',str(project),'--map',str(mapfile)],text=True,capture_output=True)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertIn('nothing written',result.stdout)
                self.assertNotIn('Traceback',result.stderr)
                self.assertEqual(before,{p.relative_to(project).as_posix():p.read_bytes() for p in project.rglob('*') if p.is_file()})

    def test_help_exposes_accepted_input_shape(self):
        result=subprocess.run([sys.executable,'-B',str(Path(B.__file__)),'--help'],text=True,capture_output=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('"bindings":[{"prefab":',result.stdout)


if __name__=='__main__':
    unittest.main()
