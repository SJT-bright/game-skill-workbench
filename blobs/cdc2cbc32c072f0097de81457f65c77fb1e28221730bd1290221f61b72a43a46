"""CLI failure is a repair checkpoint; completed observations remain reusable."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SKILLS=HERE.parents[1]
sys.path.insert(0,str(SKILLS/'remake-core/scripts'))
sys.path.insert(0,str(SKILLS/'cocos-game-check/package-check/scripts'))
sys.path.insert(0,str(HERE))
import make_tiktok_zip as writer
import build_checked_zip as checked_writer
import prepare_delivery as delivery
import check_package as package_check
import handoff_preview as handoff
import importlib.util
preview_spec=importlib.util.spec_from_file_location('english_preview_under_test',HERE/'serve_preview.py')
preview=importlib.util.module_from_spec(preview_spec)
preview_spec.loader.exec_module(preview)


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)
        env=patch.dict('os.environ',{'COCOS_SKILL_FEEDBACK_DIR':str(self.root/'feedback')})
        env.start();self.addCleanup(env.stop)

    def invoke(self,func,args):
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,'argv',['command',*map(str,args)]),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=func()
        return code,out.getvalue(),err.getvalue()

    def repair(self,result,stage):
        code,out,err=result
        self.assertNotEqual(code,0)
        records=[]
        for line in (out+'\n'+err).splitlines():
            try:records.append(json.loads(line))
            except ValueError:pass
        self.assertTrue(records,(out,err))
        item=records[-1]
        self.assertIs(item.get('task_terminal'),False,item)
        self.assertIs(item.get('requires_user_continue'),False,item)
        self.assertEqual(item.get('repair_status'),'repair_required',item)
        self.assertEqual(item.get('owner'),'current_agent',item)
        self.assertEqual(item.get('resume_at'),stage,item)
        self.assertEqual(item.get('verification_scope'),'affected_or_missing_only',item)

    def test_writer_missing_review_returns_repair_without_writing_zip(self):
        out=self.root/'new.zip'
        native=self.root/'native';native.mkdir()
        result=self.invoke(writer.main,['--native',native,'--app-id','tttest','--out',out,
            '--project',self.root,'--web',self.root/'missing-web','--resource-manifest',self.root/'resources.json'])
        self.repair(result,'writer')
        self.assertEqual(result[0],1)
        self.assertIn('actual current Web directory missing',result[1]+result[2])
        self.assertFalse(out.exists())

    def test_writer_missing_native_has_same_repair_contract(self):
        result=self.invoke(writer.main,['--native',self.root/'missing','--app-id','tttest','--out',self.root/'new.zip',
                                      '--review',self.root/'review.json','--project',self.root,
                                      '--web',self.root/'web','--build-tag','fixture','--resource-manifest',self.root/'resources.json'])
        self.repair(result,'writer')

    def test_checked_writer_failure_is_not_a_task_end(self):
        self.repair(self.invoke(checked_writer.main,['--native',self.root/'missing','--expected-app-id','tttest',
            '--out',self.root/'new.zip','--project',self.root,'--resource-manifest',self.root/'resources.json']),'writer')
        self.assertFalse((self.root/'new.zip').exists())

    def test_delivery_missing_artifact_routes_to_exact_gap(self):
        self.repair(self.invoke(delivery.main,['--zip',self.root/'missing.zip','--native',self.root/'native',
            '--expected-app-id','tttest','--record',self.root/'delivery.json','--project',self.root,
            '--resource-manifest',self.root/'resources.json']),'delivery')
        self.assertFalse((self.root/'delivery.json').exists())

    def test_handoff_missing_checklist_remains_in_preview_stage(self):
        with patch.object(handoff.preview_chrome,'browser_request') as chrome:
            self.repair(self.invoke(handoff.main,['--project',self.root,'--preview-url','http://127.0.0.1:1/',
                '--kind','art','--plan',self.root/'missing.json']),'preview')
            chrome.assert_not_called()

    def test_preview_refusal_keeps_the_original_error_and_resume_action(self):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),self.assertRaises(SystemExit) as stopped:
            preview.refuse('fixture missing current evidence')
        self.repair((stopped.exception.code,out.getvalue(),err.getvalue()),'preview')
        self.assertIn('fixture missing current evidence',err.getvalue())

    def test_package_check_missing_zip_requires_repair(self):
        self.repair(self.invoke(package_check.main,['--input',self.root/'missing.zip']),'package_check')

    def test_help_is_success_and_never_starts_a_repair_loop(self):
        out,err=io.StringIO(),io.StringIO()
        with patch.object(sys,'argv',['make_tiktok_zip.py','--help']),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as done:writer.main()
        self.assertEqual(done.exception.code,0)
        self.assertNotIn('repair_required',out.getvalue()+err.getvalue())


if __name__=='__main__':
    unittest.main()
