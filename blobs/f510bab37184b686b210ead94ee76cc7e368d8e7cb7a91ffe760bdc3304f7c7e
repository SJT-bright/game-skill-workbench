#!/usr/bin/env python3
"""Returned visual request: immutable old failure, current byte binding, real HTTP handoff."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import types
import unittest
from unittest import mock
from urllib.request import urlopen
from urllib.parse import urlsplit
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[1]/'cocos-game-check/package-check/scripts'))
import returned_art_acceptance as A
import art_receipt as R
import make_tiktok_zip as W
import tiktok_finalize as F
import serve_preview as S
english_path=HERE.parents[1]/'cocos-game-to-english/scripts/serve_preview.py'
E=None
if english_path.is_file():
    spec=importlib.util.spec_from_file_location('returned_english_preview',english_path)
    E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)

@unittest.skipIf(E is None, 'English returned-delivery route is tested in the English distribution')
class Returned(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.p=self.root/'project';(self.p/'assets').mkdir(parents=True)
        (self.p/'assets/button.png').write_bytes(b'fixture-current-art')
        (self.p/'project.json').write_text('{"version":"2.4.15"}')
        (self.p/'docs/english').mkdir(parents=True)
        (self.p/'.tiktok-kit').mkdir();(self.p/'.tiktok-kit/policy.json').write_text('{"board":"localize","policy":"new"}')
        self.old={'kind':'art-receipt','status':'fail','images':{'assets/button.png':'old'},'created':'2026-10-01T00:00:00Z'}
        A.write(self.p/R.RECEIPT,self.old)
        self.web=self.p/'build/web-mobile';self.web.mkdir(parents=True)
        (self.web/'index.html').write_text('<html><head></head><body><script src="main.js"></script></body></html>')
        (self.web/'main.js').write_text('window.fixture=true;')
        self.native=self.p/'build/bytedance';self.native.mkdir()
        for name,body in {'game.json':'{"deviceOrientation":"portrait"}','game.js':'// fixture native','project.config.json':'{}'}.items():(self.native/name).write_text(body)
        self.z=self.root/'previous.zip'
        with zipfile.ZipFile(self.z,'w') as z:z.writestr('game.json','{}');z.writestr('game.js','// previous')
        self.scope=[{'path':'assets/button.png','kind':'image','request':'只修这个按钮，然后给我测试包，不重验美工'}]
    def accept(self):
        return A.record(self.p,self.web,self.native,'上个测试包按钮被打回，只修这个美工然后给我测试包',self.scope,previous_zip=self.z)
    def test_old_path_blocks_but_user_acceptance_keeps_old_failure_untouched(self):
        self.assertEqual(R.check(self.p,'localize')['level'],'block')
        old=(self.p/R.RECEIPT).read_bytes();self.accept()
        with mock.patch.object(R,'image_fingerprints',side_effect=AssertionError('no art scan')):
            got=R.check(self.p,'localize',capture_build=self.web)
        self.assertEqual(got['status'],'user_accepted');self.assertEqual(got['level'],'ok')
        self.assertFalse(got['returned_art_acceptance']['ai_art_rechecked'])
        self.assertEqual((self.p/R.RECEIPT).read_bytes(),old)
        self.assertNotEqual(got['status'],'pass')
    def test_changed_source_web_native_each_invalidates_only_acceptance_binding(self):
        for path in [self.p/'assets/button.png',self.web/'main.js',self.native/'game.js']:
            with self.subTest(path=path):
                self.accept();original=path.read_bytes();path.write_bytes(original+b'changed')
                with self.assertRaises(ValueError):A.validate(self.p)
                path.write_bytes(original)
    def test_functional_scope_not_an_art_waiver(self):
        self.scope[0]['kind']='reward_handler'
        with self.assertRaises(ValueError):self.accept()
    def test_malformed_old_identity_cannot_masquerade_as_delivery(self):
        self.accept();path=self.p/A.MANIFEST;doc=A.read(path)
        doc['previous_delivery']['sha256']='z'*64;A.write(path,doc)
        with self.assertRaises(ValueError):A.validate(self.p)
    def test_malformed_container_is_actionable_refusal_not_crash(self):
        for bad in ([], None, {'previous_delivery':[]}):
            with self.subTest(value=bad):
                self.accept();path=self.p/A.MANIFEST
                value=bad if bad is None or isinstance(bad,list) else dict(A.read(path),**bad)
                A.write(path,value)
                self.assertEqual(R.check(self.p,'localize')['state'],'returned_art_acceptance_invalid')
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    E.gate(['--directory',str(self.web),'--project',str(self.p),'--snapshot','--keep'])
        report=self.root/'bad-prior.json';A.write(report,[])
        with self.assertRaises(ValueError):A.previous_identity(delivery=report)
    def test_existing_native_origin_remains_enforced_without_art_qa(self):
        A.write(self.p/F.SOURCE_RECORD,{'source_sha256':F.source_sha256(self.p),'board':'localize','policy':'new','kit_version':'fixture'})
        F.record_prepared_native(self.p,self.native,F.prepared_source_identity(self.p))
        self.accept();self.assertEqual(A.validate(self.p)['native_origin']['status'],'verified_existing_preparation')
        proof=self.p/F.PREPARED_NATIVE/(A.native_hash(self.native)+'.json')
        stale=A.read(proof);stale['source']['source_sha256']='0'*64;A.write(proof,stale)
        with self.assertRaises(ValueError):A.validate(self.p)
    def test_existing_delivery_identity_is_supported_without_asking_again(self):
        report=self.root/'prior-delivery.json';A.write(report,{'archive':str(self.z),'sha256':A.sha(self.z)})
        A.record(self.p,self.web,self.native,'按原反馈改完图片出包',self.scope,previous_delivery=report)
        self.assertEqual(A.validate(self.p)['previous_delivery']['basis'],'existing_delivery_record')
    def test_image_writer_uses_actual_native_bytes_and_never_rereviews_art(self):
        self.accept();files={p.relative_to(self.native).as_posix():p.read_bytes() for p in self.native.rglob('*') if p.is_file()}
        import audit_image_review_record as images
        with mock.patch.object(images,'check',side_effect=AssertionError('no image review')):
            self.assertEqual(W.english_image_problems(files,self.p,'localize'),[])
            files['game.js']+=b'changed';self.assertTrue(W.english_image_problems(files,self.p,'localize'))
    def test_writer_preserves_functional_refusal_and_labels_user_acceptance(self):
        self.accept()
        with mock.patch.object(F.T,'load_manifest',return_value={}), mock.patch.object(F,'read_source_record',return_value={'board':'localize'}), mock.patch.object(F,'check_source_record',return_value=[{'id':'K5_functional','message':'current reward code has a real error'}]), mock.patch.object(F,'finalize_native') as finalize:
            _,_,problems=W.finalize_for_writer(self.native,self.p,'localize','tt123')
            self.assertTrue(any('K5_functional' in x for x in problems));finalize.assert_not_called()
        with mock.patch.object(F.T,'load_manifest',return_value={}), mock.patch.object(F,'read_source_record',return_value={'board':'localize'}), mock.patch.object(F,'check_source_record',return_value=[]), mock.patch.object(F,'finalize_native',return_value={'blocks':[],'table':[],'warnings':[]}):
            with mock.patch.object(F,'check_trial_source',side_effect=AssertionError('no repeated Sprite-art gate')):
                record,_,problems=W.finalize_for_writer(self.native,self.p,'localize','tt123')
            self.assertEqual(problems,[]);self.assertEqual(record['art_receipt']['status'],'user_accepted')
            self.assertFalse(record['art_receipt']['returned_art_acceptance']['functional_acceptance'])
    def test_wrong_writer_native_refused_before_mutation(self):
        self.accept();other=self.root/'wrong-native';shutil.copytree(self.native,other);(other/'game.js').write_text('other game')
        with mock.patch.object(F.T,'load_manifest',return_value={}), mock.patch.object(F,'read_source_record',return_value={'board':'localize'}), mock.patch.object(F,'finalize_native') as finalize:
            _,_,problems=W.finalize_for_writer(other,self.p,'localize','tt123')
            self.assertTrue(any('Native' in x for x in problems));finalize.assert_not_called()
    def test_user_acceptance_survives_zip_and_delivery_summaries(self):
        self.accept()
        import verify_native_zip as V
        import prepare_delivery as D
        raw={'kind':'finalize-native','decision':{},'art_receipt':R.summary(R.check(self.p,'localize'))}
        summary=V.finalize_summary(raw)
        receipt=self.root/'fixture.zip.receipt.json';A.write(receipt,{'finalize':summary})
        delivered=D.writer_finalize(receipt)
        self.assertEqual(delivered['art_receipt']['status'],'user_accepted')
        self.assertFalse(delivered['art_receipt']['returned_art_acceptance']['ai_art_rechecked'])
    def writer_runtime_fixture(self, fail_startup=False):
        import runtime_regression as RR
        import runtime_incremental as RI
        import check_package as CP
        import check_ledger as CL
        adapter=self.p/'qa/adapter.json';adapter.parent.mkdir();A.write(adapter,{'layout_states':[{'name':'home'},{'name':'settings'}]})
        A.write(self.p/'docs/checks/check-inputs.json',{'schema':'check-inputs.v1','checks':{
            'runtime.layout_state/@startup':{'inputs':{'package':['*'],'adapter':['/layout_states']},'basis':'Startup bytes include every actual Native resource'},
            'runtime.save_restart/@suite':{'inputs':{'package':['game.js'],'adapter':['/layout_states']},'basis':'Fixture save consumer is game.js, no image consumer'}}})
        calls=[]
        def execute(package,adapter,names,work,*args,**kwargs):
            selections=kwargs['selections'];calls.append(selections)
            rows=[];Path(work).mkdir(parents=True,exist_ok=True)
            for name in names:
                ok=not (fail_startup and name=='layout_state')
                raw=Path(work)/(name+'.json');A.write(raw,{'passed':ok,'synthetic_fixture':True})
                rows.append({'suite':name,'passed':ok,'units':{u:{'passed':ok,'cases':[{'id':u,'passed':ok}]} for u in selections[name]},
                             'cases':[{'id':u,'passed':ok} for u in selections[name]],'problems':[] if ok else ['startup size/audio failure'],
                             'evidence':{'report':str(raw),'startup':{'MiB':1,'audioBytes':0,'beforeHome':[]}},'raw_files':[str(raw)]})
            return {'suites':rows,'warnings':[],'seconds':0.01,'passed':not fail_startup}
        stack=contextlib.ExitStack()
        for target,values in [(RR,{'required_suites':lambda *a,**k:['layout_state','save_restart'], 'load_adapter':lambda *a,**k:A.read(adapter),
                                   'detect_engine':lambda *a,**k:'2.x','package_policy':lambda *a,**k:('new','fixture'),
                                   'preflight':lambda *a,**k:({},[]),'precheck':lambda *a,**k:None,'_run_uncached':execute}),
                              (RI,{'_rule':lambda *a,**k:'fixture-stable-rule'}),
                              (CL,{'project_of':lambda *a,**k:self.p})]:
            for name,value in values.items():stack.enter_context(mock.patch.object(target,name,side_effect=value))
        files=lambda:{p.relative_to(self.native).as_posix():p.read_bytes() for p in self.native.rglob('*') if p.is_file()}
        return stack,calls,lambda:CP.writer_regressions(files(),self.native,adapter,policy='new',board='localize'),CP
    def test_default_writer_accepts_visual_without_rerunning_unchanged_function(self):
        self.accept();stack,calls,run,CP=self.writer_runtime_fixture()
        with stack:
            first=run();self.assertFalse(first['blocked'],first)
            self.assertEqual(calls[0]['layout_state'],['@startup'])
            row=next(r for r in first['runtime_regression']['suites'] if r['suite']=='layout_state')
            self.assertIsNone(row['passed']);self.assertEqual(row['visual_status'],'user_accepted');self.assertFalse(row['visual_checks_executed'])
            self.assertTrue(first['runtime_regression']['complete'])
            # Only an image changes. The saved game logic node stays on its original evidence.
            (self.native/'button.png').write_bytes(b'new-image');(self.p/'assets/button.png').write_bytes(b'new-image');self.accept()
            second=run();self.assertFalse(second['blocked'],second)
            self.assertEqual(calls[1],{'layout_state':['@startup']})
            third=run();self.assertFalse(third['blocked']);self.assertEqual(len(calls),2)
            record=CP.regression_record(third['rewarded_ad_regression'],third['runtime_regression'])
            layout=next(r for r in record['runtime_regression']['suites'] if r['suite']=='layout_state')
            self.assertIsNone(layout['passed']);self.assertEqual(layout['visual_status'],'user_accepted')
            import runtime_incremental as RI
            with mock.patch.object(RI,'_rule',return_value='changed-unknown-functional-rule'):
                blocked=run()
            self.assertTrue(blocked['blocked']);self.assertEqual(len(calls),2)
            self.assertIn('scope_required',str(blocked))
    def test_default_writer_still_blocks_hidden_startup_failure(self):
        self.accept();stack,calls,run,_=self.writer_runtime_fixture(fail_startup=True)
        with stack:result=run()
        self.assertTrue(result['blocked']);self.assertEqual(calls[0]['layout_state'],['@startup'])
    def test_actual_layout_js_startup_branch_never_calls_visual_functions(self):
        import subprocess
        lib=self.root/'js-lib';lib.mkdir()
        runtime=HERE.parents[1]/'cocos-game-check/package-check/scripts/runtime_regression'
        shutil.copy2(runtime/'layout_rules.mjs',lib/'layout_rules.mjs')
        (lib/'engine_adapter.mjs').write_text("export const inPage=()=> 'hook';")
        (lib/'gates.mjs').write_text("""
export const DEVICES={iphone14:{W:390,H:844},se:{W:375,H:667}};export const MIN_FPS=10;
export async function openGame(){globalThis.opens=(globalThis.opens||0)+1;}
export async function waitHome(){return {ok:true,ms:1,scene:'home',fps:60};}
export async function sleep(){};export async function engineMajor(){return {version:'fixture'};}
export function shot(){throw Error('unexpected visual screenshot');}
export function visibleNodes(){throw Error('unexpected visual scan');}
export function runActions(){throw Error('unexpected page route');}
export function evalJs(){throw Error('unexpected after-home action');}
""")
        (lib/'lib.mjs').write_text("""
export const C=globalThis.CFG,A=globalThis.ADAPTER;
export const evidence=(name,data)=>name;
export async function suite(fn){
 const out={evidence:{},cases:[],warn(){},add(id,passed,detail){this.cases.push({id,passed,detail});}};
 const page={async evaluate(fn){return fn==='hook'?true:{subs:[],scenes:[{loading:'home',t:10}]};}};
 await fn({out,page});globalThis.result={out,opens:globalThis.opens};
}
""")
        runner=self.root/'run-layout.mjs'
        config={'lib':(lib/'lib.mjs').as_uri(),'package':str(self.native),'engine':'2.x','policy':'new','board':'localize','selection':['@startup'],'evidenceDir':str(self.root)}
        runner.write_text('globalThis.CFG='+json.dumps(config)+';globalThis.ADAPTER={after_home_js:"throw Error(1)",layout_states:[{name:"home",actions:[{}]},{name:"settings",actions:[{}]}]};\nawait import('+json.dumps((runtime/'suites/layout_state.mjs').as_uri())+');console.log(JSON.stringify(globalThis.result));')
        for case in ('good','audio','oversized'):
            with self.subTest(case=case):
                extra=self.native/('sound.mp3' if case=='audio' else 'oversized.bin')
                if case!='good':extra.write_bytes(b'x'*(1 if case=='audio' else 10*1024*1024+1))
                try:
                    run=subprocess.run(['node',str(runner)],capture_output=True,text=True,timeout=15)
                    self.assertEqual(run.returncode,0,run.stderr)
                    result=json.loads(run.stdout);self.assertEqual(result['opens'],1)
                    self.assertEqual(set(result['out']['units']),{'@startup'})
                    self.assertEqual(result['out']['units']['@startup']['passed'],case=='good')
                    self.assertTrue(result['out']['evidence']['startup'])
                    self.assertTrue(all(c['id'] in ('home','startup_size','startup_audio','invalid_run') for c in result['out']['cases']))
                finally:
                    if case!='good':extra.unlink()
    def test_invalid_snapshot_never_gets_handoff_record(self):
        self.accept();args,verify=E.gate(['--directory',str(self.web),'--project',str(self.p),'--native',str(self.native),'--snapshot','--keep'],say=lambda *a:None)
        bad=self.root/'bad';shutil.copytree(self.web,bad);(bad/'main.js').write_text('wrong revision')
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):verify(bad)
        self.assertFalse((self.p/'docs/english/returned-trial-links.json').exists())
    def test_real_http_snapshot_with_zero_art_or_browser_checks(self):
        self.accept();calls={'launch':0};url=None
        import chinese_audit as CA
        def launch(address,**kwargs):
            nonlocal url
            url=address;calls['launch']+=1
            with urlopen(address) as r:self.assertIn(b'fixed-phone-v1',r.read())
            with urlopen(address+'main.js') as r:self.assertEqual(r.read(),(self.web/'main.js').read_bytes())
            raise KeyboardInterrupt
        snapshot=self.root/'snapshot';shutil.copytree(self.web,snapshot)
        fake_slots=types.SimpleNamespace(sweep=lambda **kw:None,register=lambda *a,**kw:None)
        with mock.patch.object(CA,'evaluate',side_effect=AssertionError('no Chinese art audit')), mock.patch.object(E,'pretrial_records',side_effect=AssertionError('no repeated pretrial artwork audit')):
            args,verify=E.gate(['--directory',str(self.web),'--project',str(self.p),'--native',str(self.native),'--snapshot','--keep','--port','0'],say=lambda *a:None)
        with mock.patch.dict(sys.modules,{'browser_slots':fake_slots}), mock.patch.object(S,'make_snapshot',return_value=(snapshot,'project',True)), mock.patch.object(S,'start_check_server',side_effect=AssertionError('no automated QA port')), mock.patch.object(S,'home_shot_gate',side_effect=AssertionError('no screenshot')), mock.patch.object(S,'trial_smoke_gate',side_effect=AssertionError('no ad rerun')), mock.patch.object(S,'browser_request',side_effect=launch), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            S.main(args,verify_snapshot=verify,returned_art=verify.returned_art)
        self.assertEqual(calls['launch'],1)
        row=A.read(self.p/'docs/english/returned-trial-links.json')[-1]
        self.assertEqual(row['status'],'user_accepted');self.assertIsNone(row['passed']);self.assertFalse(row['ai_art_rechecked'])
        self.assertEqual(A.read(self.p/R.RECEIPT),self.old)
        self.assertFalse(snapshot.exists())
        with socket.socket() as s:self.assertNotEqual(s.connect_ex(('127.0.0.1',urlsplit(url).port)),0)

if __name__=='__main__':unittest.main(verbosity=2)
