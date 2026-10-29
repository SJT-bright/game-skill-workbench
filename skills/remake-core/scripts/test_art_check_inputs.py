"""Input completeness is not an art verdict; reject before expensive tools."""
import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import art_check

class ArtInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.project=self.root/'project'
        (self.project/'assets').mkdir(parents=True);(self.project/'docs/art').mkdir(parents=True)
        self.dumps=self.project/'docs/test';self.dumps.mkdir()
        self.manifest={'runtime_verified':True,'screens':[{'id':'home','name':'Home'},{'id':'play','name':'Play'}],
                       'required_viewports':[{'name':'a','width':390,'height':844},{'name':'b','width':375,'height':812}]}
        self.write_manifest()
        for screen in ['home','play']:
            for i,vp in enumerate(self.manifest['required_viewports']):
                shot=f'{screen}-ui-shot-{i}.png';(self.dumps/shot).write_bytes(b'fixture only; no visual proof')
                (self.dumps/f'{screen}-ui-dump-{i}.json').write_text(json.dumps({'screen':screen,'kind':'gameplay' if screen=='play' else 'page',
                    'viewport':vp,'screenshot':shot,'nodes':[]}))
    def tearDown(self):self.tmp.cleanup()
    def write_manifest(self):(self.project/'docs/art/screens.json').write_text(json.dumps(self.manifest))
    def inventory(self):return art_check.capture_inventory(self.project,self.dumps)
    def test_exact_complete_input_accepts_and_unreferenced_shot_not_analysed(self):
        (self.dumps/'old-ui-unrelated.png').write_bytes(b'old screenshot')
        result=self.inventory();self.assertTrue(result['ready'],result['errors']);self.assertEqual(len(result['shots']),4)
    def test_missing_screenshot_or_viewport_and_duplicate_sizes_refused(self):
        p=self.dumps/'home-ui-shot-1.png';p.unlink();self.assertFalse(self.inventory()['ready']);p.write_bytes(b'fixture')
        self.manifest['required_viewports'][1]={'name':'b','width':390,'height':844};self.write_manifest()
        self.assertTrue(any('重复视口' in x for x in self.inventory()['errors']))
    def test_empty_malformed_and_source_only_manifest_refused(self):
        for value in [None,[],{'runtime_verified':False}, {**self.manifest,'screens':[{'name':'no-id'}]}]:
            (self.project/'docs/art/screens.json').write_text(json.dumps(value));self.assertFalse(self.inventory()['ready'])
    def test_missing_inputs_do_not_launch_audit_or_mark_art_passed(self):
        (self.project/'docs/art/screens.json').unlink();out=self.root/'out'
        with patch.object(sys,'argv',['art_check.py','--project',str(self.project),'--out',str(out)]), \
             patch.object(art_check,'run',side_effect=AssertionError('expensive audit started')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(art_check.main(),1)
        report=json.loads((out/'art-check.json').read_text());self.assertEqual(report['status'],'blocked_inputs');self.assertFalse(report['passed']);self.assertEqual(report['checked'],0)
    def test_ready_input_reaches_real_analysis_not_auto_pass(self):
        out=self.root/'out'
        with patch.object(sys,'argv',['art_check.py','--project',str(self.project),'--out',str(out)]), \
             patch('audit_no_social_features.audit',return_value={'passed':True}), \
             patch.object(art_check,'run',side_effect=RuntimeError('analysis reached')),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'analysis reached'):art_check.main()
        self.assertFalse((out/'art-check.json').exists())
if __name__=='__main__':unittest.main()
