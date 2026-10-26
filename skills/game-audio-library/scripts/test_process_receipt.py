#!/usr/bin/env python3
"""Actual ffmpeg/CLI receipt contracts in a disposable local library and game.

Uses two existing downloaded short WAVs. No download, install, game, browser or
real-library write occurs. Set GAME_AUDIO_TEST_ZIP to the local MoreSounds.zip.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ZIP=Path(os.environ.get('GAME_AUDIO_TEST_ZIP',str(HERE.parents[1]/'source-cache/02f7a88db259b2c77a18.zip')))


def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as target:
        writer=csv.DictWriter(target,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)


def read_csv(path):
    with path.open(encoding='utf-8',newline='') as source:return list(csv.DictReader(source))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ActualProcessContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ZIP.is_file():raise unittest.SkipTest('Existing local short-SFX source ZIP unavailable; set GAME_AUDIO_TEST_ZIP')
        with zipfile.ZipFile(ZIP) as archive:
            cls.samples=[(name,archive.read(name)) for name in ('Camera/Camera_01.wav','Camera/Camera_02.wav')]

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name).resolve();self.project=root/'game';self.work=self.project/'audio_work';self.work.mkdir(parents=True)
        self.library=root/'library';self.raw=self.library/'raw/test/receipt';self.raw.mkdir(parents=True)
        self.sources=[]
        for name,data in self.samples:
            path=self.raw/Path(name).name;path.write_bytes(data);self.sources.append(path)
        self.needs=self.work/'needs.csv';self.selection=self.work/'selection.csv';self.receipt=self.work/'process-result.json'
        self.env={**os.environ,'GAME_AUDIO_LIB':str(self.library),'PYTHONDONTWRITEBYTECODE':'1'}
        self.env['PATH']=os.pathsep.join(['/opt/homebrew/bin','/usr/local/bin',self.env.get('PATH','')])
        self.set_needs([{'id':'camera','type':'sfx','required':'yes','variants':'1','gen':'','tags':'click','volume':'1','max_sec':''}])
        self.set_selection([{'id':'camera','path':str(self.sources[0])}])
        rows=[];credits=[]
        for source in self.sources:
            rows.append({'path':str(source),'name':source.stem,'source':'test','pack':'receipt','kind':'sfx','tags':'click',
                         'quality':'100','duration':'.5','license':'CC0','attribution':'no','file_sha256':sha(source),
                         'audio_id':'fixture-source:'+sha(source),'family_id':'family:test/receipt/'+source.stem})
            credits.append({'file':str(source),'source':'test','title':source.stem,'author':'Existing downloaded test fixture',
                            'license':'CC0','license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
                            'url':'https://opengameart.org/sites/default/files/MoreSounds.zip','attribution_required':'no','download_date':'2026-10-26'})
        write_csv(self.library/'index.csv',rows,list(rows[0]));write_csv(self.library/'credits_master.csv',credits,list(credits[0]))

    def set_needs(self,rows):write_csv(self.needs,rows,['id','type','required','variants','gen','tags','volume','max_sec'])
    def set_selection(self,rows):write_csv(self.selection,rows,['id','path'])
    def run_pipeline(self):
        return subprocess.run([sys.executable,'-B',str(HERE/'audio_pipeline.py'),'--project',str(self.project),'--engine','3.x','--no-fetch','--no-code'],
                              env=self.env,cwd=self.work,capture_output=True,text=True,timeout=120)
    def run_process(self,*extra):
        return subprocess.run([sys.executable,'-B',str(HERE/'process_audio.py'),'--project',str(self.project),'--engine','3.x','--needs',str(self.needs),
                               '--selection',str(self.selection),'--receipt',str(self.receipt),*extra],
                              env=self.env,cwd=self.work,capture_output=True,text=True,timeout=120)
    def usage(self):return list((self.library/'usage').glob('*.json'))

    def test_real_pipeline_success_records_actual_source_and_hash(self):
        before=self.selection.read_bytes();result=self.run_pipeline()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.selection.read_bytes(),before)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],True)
        self.assertEqual(receipt['needs_sha256'],sha(self.needs));self.assertEqual(receipt['selection_sha256'],sha(self.selection))
        self.assertEqual(receipt['sources'][0]['source_path'],str(self.sources[0]))
        for relative in receipt['sources'][0]['outputs']:
            self.assertEqual(receipt['sources'][0]['output_sha256'][relative],sha(self.project/relative))
        self.assertEqual(len(self.usage()),1)
        usage=json.loads(self.usage()[0].read_text());self.assertEqual(usage['paths'],[str(self.sources[0])])
        self.assertEqual(usage['asset_ids'],['fixture-source:'+sha(self.sources[0])])
        self.assertEqual(len(usage['family_ids']),1)

    def test_multi_source_receipt_and_credits_use_disjoint_outputs(self):
        self.set_selection([{'id':'camera','path':str(source)} for source in self.sources]);result=self.run_pipeline()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        receipt=json.loads(self.receipt.read_text());self.assertTrue(receipt['success'])
        self.assertEqual(len(receipt['sources']),2)
        left,right=[set(row['outputs']) for row in receipt['sources']]
        self.assertTrue(left);self.assertTrue(right);self.assertFalse(left&right)
        self.assertEqual(len({sha(self.project/relative) for relative in left|right}),2)
        credits=read_csv(self.project/'docs/audio/credits.csv')
        self.assertEqual(len(credits),2)
        self.assertEqual({frozenset(row['outputs'].split(';')) for row in credits},{frozenset(left),frozenset(right)})
        usage=json.loads(self.usage()[0].read_text());self.assertEqual(set(usage['paths']),set(map(str,self.sources)))

    def test_disallowed_optional_source_not_recorded_as_used(self):
        self.set_needs([{'id':'camera','type':'sfx','required':'yes'}, {'id':'optional','type':'sfx','required':'no'}])
        self.set_selection([{'id':'camera','path':str(self.sources[0])},{'id':'optional','path':str(self.sources[1])}])
        credits=read_csv(self.library/'credits_master.csv');credits[1]['license']='CC-BY-NC'
        write_csv(self.library/'credits_master.csv',credits,list(credits[0]))
        result=self.run_pipeline();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        receipt=json.loads(self.receipt.read_text());self.assertEqual([row['id'] for row in receipt['sources']],['camera'])
        usage=json.loads(self.usage()[0].read_text());self.assertEqual(usage['paths'],[str(self.sources[0])])

    def test_optional_decode_failure_does_not_block_required_audio(self):
        self.set_needs([{'id':'camera','type':'sfx','required':'yes'}, {'id':'optional','type':'sfx','required':'no'}])
        self.set_selection([{'id':'camera','path':str(self.sources[0])},{'id':'optional','path':str(self.sources[1])}])
        self.sources[1].write_bytes(b'bad optional audio')
        result=self.run_pipeline();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],True)
        self.assertEqual([row['id'] for row in receipt['sources']],['camera'])
        config=(self.project/'assets/scripts/audio/GameAudioConfig.ts').read_text()
        self.assertIn('camera:',config);self.assertNotIn('optional:',config)
        self.assertEqual(json.loads(self.usage()[0].read_text())['paths'],[str(self.sources[0])])

    def test_optional_partial_variants_are_not_published_or_counted_as_used(self):
        self.set_needs([{'id':'camera','type':'sfx','required':'yes'}, {'id':'optional','type':'sfx','required':'no','variants':'2'}])
        self.set_selection([{'id':'camera','path':str(self.sources[0])},*({'id':'optional','path':str(source)} for source in self.sources)])
        self.sources[1].write_bytes(b'bad second variant')
        result=self.run_pipeline();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],True)
        self.assertEqual([row['id'] for row in receipt['sources']],['camera'])
        self.assertNotIn('optional:',(self.project/'assets/scripts/audio/GameAudioConfig.ts').read_text())
        self.assertEqual([row['id'] for row in read_csv(self.project/'docs/audio/credits.csv')],['camera'])
        self.assertEqual(json.loads(self.usage()[0].read_text())['paths'],[str(self.sources[0])])

    def test_required_partial_variants_remain_failure(self):
        self.set_selection([{'id':'camera','path':str(source)} for source in self.sources])
        self.sources[1].write_bytes(b'bad second variant')
        result=self.run_pipeline();self.assertNotEqual(result.returncode,0)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],False)
        self.assertTrue(any('未完整' in item for item in receipt['errors']));self.assertFalse(self.usage())

    def test_optional_only_failure_does_not_create_false_history_or_block(self):
        self.set_needs([{'id':'camera','type':'sfx','required':'no'}])
        self.sources[0].write_bytes(b'bad optional audio')
        result=self.run_pipeline();self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],True)
        self.assertEqual(receipt['sources'],[]);self.assertFalse(self.usage())
        self.assertNotIn('camera:',(self.project/'assets/scripts/audio/GameAudioConfig.ts').read_text())

    def test_required_missing_is_failure_and_no_usage(self):
        self.set_selection([]);result=self.run_pipeline()
        self.assertNotEqual(result.returncode,0)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],False)
        self.assertTrue(any('必需' in item for item in receipt['errors']))
        self.assertFalse(self.usage())

    def test_decode_failure_is_failure_and_no_usage(self):
        self.sources[0].write_bytes(b'not an audio file');result=self.run_pipeline()
        self.assertNotEqual(result.returncode,0)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],False)
        self.assertEqual(receipt['sources'],[]);self.assertFalse(self.usage())

    def test_budget_failure_cannot_commit_usage_or_reuse_old_receipt(self):
        result=self.run_process('--budget-kb','0');self.assertNotEqual(result.returncode,0)
        receipt=json.loads(self.receipt.read_text());self.assertIs(receipt['success'],False)
        self.assertTrue(any('预算' in item for item in receipt['errors']));self.assertFalse(self.usage())
        # Exercise the pipeline validator against the real failed processor receipt.
        code="import sys,pathlib;sys.path.insert(0,sys.argv[1]);import audio_pipeline as p;root=pathlib.Path(sys.argv[2]);w=root/'audio_work';p.commit_usage(root,w/'needs.csv',w/'selection.csv',w/'process-result.json',{'needs_sha256':p.file_sha256(w/'needs.csv'),'selection_sha256':p.file_sha256(w/'selection.csv')})"
        checked=subprocess.run([sys.executable,'-B','-c',code,str(HERE),str(self.project)],env=self.env,capture_output=True,text=True,timeout=30)
        self.assertNotEqual(checked.returncode,0);self.assertFalse(self.usage())
        # A subsequent process error removes an earlier success receipt before work.
        receipt['success']=True;self.receipt.write_text(json.dumps(receipt));self.sources[0].write_bytes(b'bad')
        rerun=self.run_pipeline();self.assertNotEqual(rerun.returncode,0)
        self.assertIs(json.loads(self.receipt.read_text())['success'],False);self.assertFalse(self.usage())

    def test_original_processing_standards_functions_unchanged(self):
        baseline=Path.home()/'.codex/skills/game-audio-library/scripts/process_audio.py'
        if not baseline.is_file():self.skipTest('Live baseline unavailable')
        names={'gain_for','trim_filter','process_one','ts_config','js_config'}
        def definitions(path):
            tree=ast.parse(path.read_text());result={}
            for node in tree.body:
                if isinstance(node,ast.FunctionDef) and node.name in names:result[node.name]=ast.dump(node,include_attributes=False)
                elif isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in {'SPEC','LIMIT'} for target in node.targets):
                    result[node.targets[0].id]=ast.dump(node.value,include_attributes=False)
            return result
        self.assertEqual(definitions(HERE/'process_audio.py'),definitions(baseline))


if __name__=='__main__':unittest.main(verbosity=2)
