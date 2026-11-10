"""Input completeness is not an art verdict; reject before expensive tools."""
import contextlib,copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import art_check
import art_check_record

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

    def test_resume_rechecks_only_failed_group_and_publishes_covered_record(self):
        capture = {'ready': True, 'round': 'test', 'version': 'one', 'cases': []}
        from art_round_check import origin_hash
        captured = dict(capture, origin_hash=origin_hash(capture))
        rows = [{'check': '读到的页面', 'status': '通过', 'log': ''}]
        for group, logs in art_check_record.TRIAL_GROUPS.items():
            if group == 'slots':
                continue
            layout = group == 'layout'
            rows.append({'check': '布局（玩法区、弹窗、按钮分布）' if layout else group,
                         'status': '需处理' if layout else '通过', 'detail': 'original',
                         'log': logs[0]})
        raw = {'tool': 'art_check', 'board': 'localize', 'checked': len(rows), 'failed': 1,
               'status': 'fail', 'passed': False, 'rows': rows, 'capture_round': captured,
               'assets_fingerprint': art_check.tree_fingerprint(self.project), 'base_generated': {}}
        report_path = self.root/'old.json'
        report_path.write_text(json.dumps(raw))
        previous = art_check_record.write(self.project, 'fail', raw, report_path, 'localize')
        refused = art_check_record.check(self.project)
        self.assertEqual(refused['level'], 'block')
        self.assertIn('--plan-trial', refused['message'])
        self.assertIn('--resume-trial', refused['message'])
        out = self.root/'out'
        argv = ['art_check.py','--project',str(self.project),'--out',str(out),'--board','localize',
                '--dumps',str(self.dumps),'--build',str(self.root/'web'),'--resume-trial']
        moved_report = self.root/'moved folder'/'old.json'
        moved_report.parent.mkdir()
        report_path.rename(moved_report)
        argv += ['--prior-report',str(moved_report)]
        stale = dict(capture, version='changed')
        stale_args = argv.copy()
        stale_args[stale_args.index('--out')+1] = str(self.root/'stale')
        with patch.object(sys,'argv',stale_args), patch('art_input_check.verify_capture',return_value=stale), \
             patch.object(art_check,'run',side_effect=AssertionError('quality replay started')), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as refused:
            art_check.main()
        self.assertEqual(refused.exception.code,3)
        with patch.object(sys,'argv',argv), patch('art_input_check.verify_capture',return_value=dict(capture)), \
             patch.object(art_check,'run',return_value=(0,'{}')) as called, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(art_check.main(),0)
        self.assertEqual([c.args[0] for c in called.call_args_list], ['extract_ui_layout.py','audit_ui_coverage.py'])
        result = json.loads((out/'art-check.json').read_text())
        self.assertEqual(result['trial_recheck']['rechecked_groups'], ['layout'])
        self.assertIn('atlas', result['trial_recheck']['reused_rows'])
        self.assertEqual(art_check_record.check(self.project)['level'], 'ok')
        with self.assertRaisesRegex(ValueError, '另一轮'):
            art_check_record.write(self.project, 'fail', raw, report_path, 'localize',
                                   previous_sha=previous['last']['report_sha256'])

    def test_failed_partial_report_points_to_actual_work(self):
        rows = [{'check': '制作素材', 'status': '需处理'}]
        report = {'tool': 'art_check', 'board': 'localize', 'status': 'blocked_inputs',
                  'failed': 1, 'checked': 0, 'rows': rows}
        path = self.root/'blocked.json'
        path.write_text(json.dumps(report))
        for scope, expected in ((None, '采集缺口'), (['english_visual_scope'], '原局部检查范围')):
            with self.subTest(scope=scope):
                art_check_record.write(self.project, 'fail', report, path, 'localize', scoped=scope)
                result = art_check_record.check(self.project)
                self.assertEqual(result['level'], 'block')
                self.assertIn(expected, result['message'])
                self.assertNotIn('--resume-trial', result['message'])

    def test_missing_pending_row_cannot_be_merged_into_a_pass(self):
        old = {'check':'旧图集','status':'需处理','log':'atlas_slices/report.json'}
        rows = []
        art_check_record.merge_trial_rows({'rows':[old]}, rows,
                                          {'rechecked_groups':['atlas'],'from_report':'old.json'})
        self.assertEqual(rows, [dict(old,origin_report='old.json')])
if __name__=='__main__':unittest.main()
