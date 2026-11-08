"""Observable evidence/reuse boundaries; no real browser or production project."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import art_receipt
import art_recheck_guard
import audit_value_presentation
import check_ledger as C
import check_workflow as W
import preview_check_once as P
import serve_preview as SP

PKG=Path(__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts'
sys.path.insert(0,str(PKG))
import runtime_regression as RR

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.project=self.root/'game';(self.project/'assets').mkdir(parents=True)
        (self.project/'project.json').write_text('{"version":"2.4.15"}')
        (self.project/'assets/input.txt').write_text('current-v2')
    def tearDown(self):self.temp.cleanup()

    def art_fixture(self):
        (self.project/'assets/a.png').write_bytes(b'fixture image')
        report={'passed':True,'status':'pass','checked':1,'failed':0,'rows':[{'check':'fixture','status':'通过'}],
                'value_presentation':{'revision':audit_value_presentation.REVISION,'mode':'runtime','passed':True,
                    'pages':1,'source_sha256':audit_value_presentation.source_fingerprint(self.project)}}
        file=self.root/'art.json';file.write_text(json.dumps(report))
        art_receipt.after_art_check(self.project,report,file)
        args=SimpleNamespace(project=self.project,board='localize',capture_build=None,build=None,out=None,
                             maintenance_scope=None,english_visual_scope=None)
        return args,file

    def test_art_original_report_must_exist_and_match(self):
        args,file=self.art_fixture();raw=file.read_bytes()
        self.assertEqual(art_recheck_guard.resolve(args),0)
        file.unlink()
        with self.assertRaises(ValueError):art_recheck_guard.resolve(args)
        file.write_text('{"passed":false}')
        with self.assertRaises(ValueError):art_recheck_guard.resolve(args)
        file.write_bytes(raw);self.assertEqual(art_recheck_guard.resolve(args),0)

    def test_art_receipt_cannot_promote_failed_original_report(self):
        args,file=self.art_fixture();file.write_text('{"passed":false,"failed":1}')
        receipt,_=art_receipt.read(self.project)
        receipt['art_check']['report_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
        art_receipt.receipt_path(self.project).write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):art_recheck_guard.resolve(args)

    def workflow(self,code,outputs=()):
        script=self.root/'checker.py';script.write_text(code)
        verdict=self.project/'report.json'
        doc={'schema':W.SCHEMA,'route':'source','roots':{'assets':'${PROJECT}/assets'},'nodes':[{
            'id':'probe','label':'probe','domain':'gameplay','phase':2,'basis':'one isolated input file',
            'inputs':{'assets':['input.txt']},'command':['${PYTHON}',str(script),str(verdict)],
            'tool_files':[str(script)],'verdict':{'file':str(verdict),'pointer':'/passed','equals':True},
            'outputs':list(outputs)}]}
        return doc,verdict

    def run_workflow(self,doc):
        ledger=C.Ledger(self.project)
        try:return W.run_node(ledger,doc,self.project,'probe')
        finally:ledger.close()

    def test_touching_stale_verdict_cannot_pass_and_original_is_recoverable(self):
        doc,verdict=self.workflow('import os,sys\nos.utime(sys.argv[1],None)\n')
        old=b'{"passed":true,"tested_input":"old-v1"}';verdict.write_bytes(old)
        result,_=self.run_workflow(doc)
        self.assertFalse(result['passed']);self.assertFalse(result['fresh_verdict'])
        backup=Path(result['previous_outputs_backup'])
        manifest=json.loads((backup/'manifest.json').read_text())
        self.assertEqual(Path(manifest[0]['backup']).read_bytes(),old)
        self.assertFalse(verdict.exists())

    def test_declared_output_missing_prevents_pass(self):
        doc,_=self.workflow('import sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(\'{"passed":true}\')\n',
                            [str(self.project/'required.png')])
        result,_=self.run_workflow(doc)
        self.assertFalse(result['passed']);self.assertEqual(result['missing_outputs'],[str(self.project/'required.png')])

    def test_real_new_report_reuses_without_process_and_restores_destination(self):
        doc,verdict=self.workflow('import sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(\'{"passed":true}\')\n')
        first,_=self.run_workflow(doc);self.assertTrue(first['passed']);verdict.unlink()
        with patch.object(W.subprocess,'run',side_effect=AssertionError('reuse must not execute')):
            second,proof=self.run_workflow(doc)
        self.assertTrue(second['passed']);self.assertTrue(proof['reused']);self.assertTrue(verdict.is_file())

    def preview_fixture(self):
        export=self.project/'export';export.mkdir();(export/'index.html').write_text('<script src="main.js"></script>')
        (export/'main.js').write_text('tt.createRewardedVideoAd({})')
        work=self.root/'preview-work';calls=[]
        def run_suite(name,meta,package,adapter,adapter_path,engine,browser,folder,*args,**kwargs):
            calls.append(name);folder=Path(folder)/name;folder.mkdir(parents=True,exist_ok=True)
            raw={'suite':name,'passed':True,'cases':[{'id':'response','passed':True}],'evidence':{}}
            result=folder/'result.json';result.write_text(json.dumps(raw))
            return {'suite':name,'passed':True,'problems':[],'warnings':[],'cases':raw['cases'],
                    'evidence':{'report':str(result)},'seconds':0.01}
        def perform():
            return P.run(self.project,'ad-response',export,{'ad_simulator':False},
                         lambda:SP.trial_smoke_gate('http://127.0.0.1:9999/',export,evidence_dir=work))
        return export,work,calls,run_suite,perform

    def test_actual_preview_gate_freezes_raw_proof_and_reuses(self):
        export,work,calls,run_suite,perform=self.preview_fixture()
        with patch.object(RR,'find_browser',return_value='never-launched'),patch.object(RR,'run_suite',side_effect=run_suite):
            first=perform();shutil.rmtree(work);second=perform()
        self.assertEqual(first[0],'pass');self.assertEqual(second[0],'pass');self.assertEqual(calls,['trial_link'])
        raw=Path(second[2]['raw_files'][0]);self.assertTrue(raw.is_file());self.assertIn('original_at',second[2])
        raw.unlink()
        with self.assertRaises(C.NeedsScope):perform()

    def test_preview_summary_without_raw_result_cannot_pass(self):
        export,work,calls,run_suite,perform=self.preview_fixture()
        def no_artifact(*args,**kwargs):return {'passed':True,'evidence':{},'cases':[{'id':'response','passed':True}]}
        with patch.object(RR,'trial_smoke',side_effect=no_artifact):result=perform()
        self.assertEqual(result[0],'block')

    def test_preview_rule_closure_invalidates_after_python_rule_change(self):
        export,work,calls,run_suite,perform=self.preview_fixture()
        original_file=Path(P.__file__);candidate=original_file.resolve().parents[2]
        isolated=self.root/'rules'
        for path in P.rule_files('ad-response'):
            target=isolated/path.relative_to(candidate);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        with patch.object(P,'__file__',str(isolated/original_file.relative_to(candidate))):
            with patch.object(RR,'find_browser',return_value='never-launched'),patch.object(RR,'run_suite',side_effect=run_suite):
                perform()
            rule=isolated/'cocos-game-check/package-check/scripts/runtime_regression.py'
            rule.write_text(rule.read_text()+'\n# changed validation rule\n')
            calls_before=len(calls)
            def revised(*args,**kwargs):return ('block','revised real checker rejects this input')
            result=P.run(self.project,'ad-response',export,{'ad_simulator':False},revised)
        self.assertEqual(result[0],'block');self.assertEqual(len(calls),calls_before)

if __name__=='__main__':unittest.main()
