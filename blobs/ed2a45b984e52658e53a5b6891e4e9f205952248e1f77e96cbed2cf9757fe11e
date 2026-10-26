#!/usr/bin/env python3
"""Isolated selection and processing-history contracts; never modifies the real library."""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import audio_identity as ident
import search_index as search
import audition
import audio_pipeline as pipeline


def asset(name, *, audio_id=None, family_id=None, kind='bgm', tags='music|cute', themes='', quality=85,
          duration=None, license='CC0', pack='pack', **extra):
    path = str(common.LIB / 'raw' / 'test' / pack / name)
    row = {'path':path, 'name':Path(name).stem, 'source':'test', 'pack':pack, 'kind':kind,
           'tags':tags, 'themes':themes, 'quality':str(quality), 'duration':str(duration if duration is not None else 30 if kind == 'bgm' else .2),
           'license':license, 'attribution':'no', 'audio_id':audio_id or 'pcm-sha256:' + name,
           'family_id':family_id or 'family:test/' + pack + '/' + Path(name).stem}
    row.update(extra)
    return row


def need(nid='bgm_menu', *, kind='bgm', tags='music|cute', themes='', required='yes', **extra):
    return {'id':nid, 'type':kind, 'tags':tags, 'themes':themes, 'required':required, 'variants':'1', **extra}


def rank(index, needs, recent=()):
    return search.rank_candidates(index, needs, 'cute', 'game-A', recent=recent, per_id=12,
                                  themes={'space', 'cooking', 'beach', 'puzzle'})[0]


class EligibilityContracts(unittest.TestCase):
    def test_original_base_score_function_unchanged(self):
        live = Path.home()/'.codex/skills/game-audio-library/scripts/search_index.py'
        if not live.exists():
            self.skipTest('live baseline unavailable')
        def function(path):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            return ast.dump(next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'base_score'), include_attributes=False)
        self.assertEqual(function(Path(search.__file__)), function(live))

    def test_original_quality_license_kind_and_duration_boundaries(self):
        bgm = need()
        self.assertIsNotNone(search.base_score(asset('good.wav', quality=70), bgm, 'cute'))
        for changes in ({'quality':69.999}, {'license':'CC-BY-NC'}, {'license':'unknown'}, {'license':'CC-BY-ND'}, {'license':'CC-BY-SA'}, {'kind':'sfx'}, {'duration':11.999}, {'duration':600.001}):
            self.assertIsNone(search.base_score(asset('bad.wav', **changes), bgm, 'cute'), changes)
        for kind, lo, hi in (('bgm',12,600), ('jingle',.8,10), ('sfx',.03,2.5)):
            request = need(kind=kind, tags='music|cute')
            for duration in (lo, hi):
                self.assertIsNotNone(search.base_score(asset('boundary.wav', kind=kind, duration=duration), request, 'cute'))
            for duration in (lo-.001, hi+.001):
                self.assertIsNone(search.base_score(asset('outside.wav', kind=kind, duration=duration), request, 'cute'))
        self.assertIsNone(search.base_score(asset('too-long.wav', duration=.401, kind='sfx'), need(kind='sfx', max_sec='.4'), 'cute'))
        self.assertIsNone(search.base_score(asset('too-long.wav', duration=270.001), need(max_sec='90'), 'cute'))

    def test_nonfinite_index_values_are_not_candidates(self):
        rows = rank([asset('nan.wav', quality='nan'), asset('infinite.wav', duration='inf'), asset('good.wav')], [need()])
        self.assertEqual([row['name'] for row in rows], ['good'])


class IdentityContracts(unittest.TestCase):
    def test_priority_and_portable_relative_key(self):
        row = {'path':'raw/test/pack/click.wav', 'file_sha256':'abc'}
        self.assertEqual(ident.identity(row), 'file-sha256:abc')
        self.assertEqual(ident.identity({**row, 'audio_id':'pcm-sha256:def'}), 'pcm-sha256:def')
        self.assertEqual(ident.identity({'path':row['path']}), 'path:raw/test/pack/click.wav')
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder).resolve()
            self.assertEqual(ident.relative_asset_path(library/'raw'/'a.wav', library), 'raw/a.wav')
            for path in ('../outside.wav', '/outside.wav'):
                with self.assertRaises(ValueError):
                    ident.relative_asset_path(path, library)

    def test_family_preserves_bgm_track_numbers_and_groups_known_formats(self):
        base = {'source':'s', 'pack':'p', 'kind':'bgm'}
        self.assertEqual(ident.family({**base,'name':'Track1.wav'}), ident.family({**base,'name':'Track1_loop.ogg'}))
        self.assertNotEqual(ident.family({**base,'name':'Track1.wav'}), ident.family({**base,'name':'Track2.wav'}))
        self.assertEqual(ident.family({**base,'kind':'sfx','name':'click_001.wav'}), ident.family({**base,'kind':'sfx','name':'click_009.wav'}))
        self.assertNotEqual(ident.family({**base,'name':'Loop1.wav'}), ident.family({**base,'name':'Loop2.wav'}))

    def test_subalbums_with_same_track_name_are_different_families(self):
        base = {'source':'test', 'pack':'pack', 'kind':'bgm', 'name':'Track1.wav'}
        one = {**base,'path':str(common.LIB/'raw/test/pack/album-a/Track1.wav')}
        two = {**base,'path':str(common.LIB/'raw/test/pack/album-b/Track1.wav')}
        self.assertNotEqual(ident.family(one), ident.family(two))
        self.assertIn('/album-a/',ident.family(one))
        self.assertEqual(ident.family(one),ident.family({**one,'path':'/other/computer/GameAudioLibrary/raw/test/pack/album-a/Track1.wav'}))

    def test_same_name_different_audio_retained_same_audio_formats_collapsed(self):
        rows = rank([asset('one/theme.wav', audio_id='pcm:1', family_id='family:1'),
                     asset('two/theme.wav', audio_id='pcm:2', family_id='family:2'),
                     asset('two/theme.ogg', audio_id='pcm:2', family_id='family:2')], [need()])
        self.assertEqual({row['asset_id'] for row in rows}, {'pcm:1','pcm:2'})
        self.assertEqual(len(rows), 2)

    def test_different_encoded_bgm_same_composition_family_collapsed(self):
        rows = rank([asset('Track1.wav', audio_id='pcm:a', family_id='family:track1'),
                     asset('Track1_loop.ogg', audio_id='pcm:b', family_id='family:track1'),
                     asset('Track2.wav', audio_id='pcm:c', family_id='family:track2')], [need()])
        self.assertEqual({row['family_id'] for row in rows}, {'family:track1','family:track2'})
        self.assertEqual(len(rows), 2)


class SuitabilityContracts(unittest.TestCase):
    def test_explicit_theme_beats_generic_and_other_theme_without_lowering_gates(self):
        data = [asset('generic.wav', quality=100), asset('space.wav', themes='space', quality=70),
                asset('beach.wav', themes='beach', quality=100), asset('low-space.wav', themes='space', quality=69),
                asset('nc-space.wav', themes='space', license='CC-BY-NC')]
        space = rank(data, [need(themes='space')])
        beach = rank(data, [need(themes='beach')])
        self.assertEqual(space[0]['name'], 'space')
        self.assertEqual(beach[0]['name'], 'beach')
        self.assertEqual(space[0]['match_mode'], 'theme_match')
        self.assertEqual(space[1]['match_mode'], 'fallback_unclassified')
        self.assertEqual(space[2]['match_mode'], 'fallback_other_theme')
        self.assertNotIn('low-space', {row['name'] for row in space})
        self.assertNotIn('nc-space', {row['name'] for row in space})

    def test_missing_theme_is_reported_as_fallback(self):
        rows, missing, details = search.rank_candidates([asset('generic.wav')], [need(themes='cooking')], 'cute','g',themes={'cooking'})
        self.assertEqual(rows[0]['match_mode'], 'fallback_unclassified')
        self.assertTrue(details[0]['fallback'])
        self.assertEqual(details[0]['theme_matches'], 0)
        self.assertEqual(details[0]['requested_themes'], ['cooking'])

    def test_sfx_action_and_material_cannot_be_replaced_by_theme(self):
        request = need('click', kind='sfx', tags='click|cute', themes='space', keywords='metal button click')
        data = [asset('laser.wav',kind='sfx',tags='shoot|cute',themes='space',quality=100),
                asset('wood-click.wav',kind='sfx',tags='click|wood|cute',themes='space',quality=100),
                asset('metal-click.wav',kind='sfx',tags='click|metal',quality=70)]
        rows = rank(data,[request])
        self.assertEqual(rows[0]['name'],'metal-click')
        self.assertNotIn('laser',{row['name'] for row in rows})
        self.assertEqual({row['name'] for row in rows}, {'metal-click','wood-click'})

    def test_family_spreading_stays_within_semantic_fit(self):
        rows = rank([asset('metal1.wav',kind='sfx',tags='click|metal',family_id='metal',quality=99),
                     asset('metal2.wav',kind='sfx',tags='click|metal',family_id='metal',quality=98),
                     asset('wood.wav',kind='sfx',tags='click|wood',family_id='wood',quality=100)],
                    [need('click',kind='sfx',tags='click',keywords='metal click')])
        self.assertEqual({row['name'] for row in rows[:2]},{'metal1','metal2'})
        self.assertEqual(rows[-1]['name'],'wood')

    def test_legacy_paths_and_new_identity_history_apply_same_penalty(self):
        data=[asset('Track1.wav',family_id='track1'),asset('Track1_loop.wav',family_id='track1'),asset('Track2.wav',family_id='track2')]
        row=data[0]
        legacy=[{'paths':[row['path']], 'packs':['test/pack']}]
        modern=[{'asset_ids':[ident.identity(row)],'family_ids':[ident.family(row)],'packs':['test/pack']}]
        self.assertEqual(rank(data,[need()],legacy),rank(data,[need()],modern))
        a,b=search.history_counts(data,[{'paths':['/old/computer/GameAudioLibrary/raw/test/pack/Track1.wav']}])
        self.assertEqual(a[ident.identity(row)],1)
        self.assertEqual(b['track1'],1)
        baseline={r['family_id']:r['score'] for r in rank(data,[need()])}
        used={r['family_id']:r['score'] for r in rank(data,[need()],modern)}
        self.assertGreater(baseline['track1']-used['track1'],baseline['track2']-used['track2'])

    def test_auto_selection_prefers_distinct_bgm_family_but_preserves_best_fit(self):
        requests=[need('menu'),need('game'),need('optional',required='no')]
        cands=[]
        for req in requests:
            for i,(audio,group) in enumerate((('a','one'),('b','one'),('c','two')),1):
                cands.append({'id':req['id'],'rank':str(i),'path':str(common.LIB/'raw'/f'{audio}.wav'),
                              'asset_id':audio,'family_id':group,'fit_priority':'2|1|0','match_mode':'theme_match'})
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            out=Path(folder)/'selection.csv'
            audition.auto_select(cands,{r['id']:r for r in requests},out)
            result=common.read_csv(out)
            self.assertEqual([r['asset_id'] for r in result],['a','c'])
            # A wrong-theme candidate cannot be selected merely because it is unused.
            lower={**cands[2],'id':'game','rank':'3','fit_priority':'1|0|0','match_mode':'fallback_other_theme'}
            audition.auto_select(cands[:1]+[{**cands[0],'id':'game'},lower],{r['id']:r for r in requests[:2]},out)
            self.assertEqual([r['asset_id'] for r in common.read_csv(out)],['a','a'])


class PipelineContracts(unittest.TestCase):
    def setup_paths(self, folder):
        root=Path(folder).resolve();proj=root/'game';work=proj/'audio_work';work.mkdir(parents=True)
        lib=root/'library';lib.mkdir();index=lib/'index.csv'
        common.write_csv(index,[asset('test.wav')],list(asset('test.wav')))
        needs=work/'needs.csv';selection=work/'selection.csv'
        common.write_csv(needs,[need()],list(need()))
        return root,proj,work,lib,index,needs,selection

    def test_no_fetch_empty_library_does_not_start_download_or_install(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(pipeline,'INDEX',Path(folder)/'absent.csv'),patch.object(pipeline,'RAW',Path(folder)/'raw'),patch.object(pipeline,'run') as run,patch.object(pipeline,'need_ffmpeg') as setup,patch.object(sys,'argv',['audio_pipeline.py','--project',folder,'--no-fetch']):
                with self.assertRaisesRegex(SystemExit,'--no-fetch 不下载'):
                    pipeline.main()
                run.assert_not_called();setup.assert_not_called()

    def test_no_fetch_missing_tools_never_auto_installs(self):
        with tempfile.TemporaryDirectory() as folder:
            _,proj,work,lib,index,needs,selection=self.setup_paths(folder)
            with patch.object(pipeline,'INDEX',index),patch.object(pipeline,'have_ffmpeg',return_value=False),patch.object(pipeline,'run') as run,patch.object(pipeline,'need_ffmpeg') as setup,patch.object(sys,'argv',['audio_pipeline.py','--project',str(proj),'--no-fetch','--engine','3.x']):
                with self.assertRaisesRegex(SystemExit,'--no-fetch 不自动安装'):
                    pipeline.main()
                run.assert_not_called();setup.assert_not_called()

    def test_failed_search_stops_before_old_candidate_can_be_used(self):
        with tempfile.TemporaryDirectory() as folder:
            _,proj,work,lib,index,needs,selection=self.setup_paths(folder)
            (work/'candidates.csv').write_text('STALE CANDIDATES')
            calls=[]
            def run(*args,**kwargs):
                calls.append(Path(args[0]).name)
                return 9 if Path(args[0]).name=='search_index.py' else 0
            with patch.object(pipeline,'INDEX',index),patch.object(pipeline,'have_ffmpeg',return_value=True),patch.object(pipeline,'need_ffmpeg'),patch.object(pipeline,'run',side_effect=run),patch.object(sys,'argv',['audio_pipeline.py','--project',str(proj),'--no-fetch','--engine','3.x']):
                with self.assertRaisesRegex(SystemExit,'search_index.py 失败'):
                    pipeline.main()
            self.assertEqual(calls,['build_index.py','search_index.py'])
            self.assertFalse(selection.exists())

    def test_existing_selection_is_not_automatically_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            _,proj,work,lib,index,needs,selection=self.setup_paths(folder)
            selection.write_text('id,path\nbgm_menu,approved.wav\n')
            original=selection.read_bytes();calls=[]
            def run(*args,**kwargs):calls.append(Path(args[0]).name);return 8
            with patch.object(pipeline,'INDEX',index),patch.object(pipeline,'have_ffmpeg',return_value=True),patch.object(pipeline,'need_ffmpeg'),patch.object(pipeline,'run',side_effect=run),patch.object(sys,'argv',['audio_pipeline.py','--project',str(proj),'--no-fetch','--theme','space','--engine','3.x']):
                with self.assertRaises(SystemExit):pipeline.main()
            self.assertEqual(calls,['process_audio.py'])
            self.assertEqual(selection.read_bytes(),original)

    def test_theme_reaches_bgm_and_sfx_without_replacing_action_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            _,proj,work,lib,index,needs,selection=self.setup_paths(folder)
            records=[need(),need('click',kind='sfx',tags='click|pop')]
            common.write_csv(needs,records,list(records[0]))
            with patch.object(pipeline,'INDEX',index),patch.object(pipeline,'have_ffmpeg',return_value=True),patch.object(pipeline,'need_ffmpeg'),patch.object(pipeline,'run',return_value=1),patch.object(sys,'argv',['audio_pipeline.py','--project',str(proj),'--no-fetch','--theme','space','--engine','3.x']):
                with self.assertRaises(SystemExit):pipeline.main()
            rows=common.read_csv(needs)
            self.assertTrue(all(row['themes']=='space' for row in rows))
            self.assertEqual(rows[1]['tags'],'click|pop')

    def test_only_verified_successful_outputs_commit_usage(self):
        with tempfile.TemporaryDirectory() as folder:
            root,proj,work,lib,index,needs,selection=self.setup_paths(folder)
            source=lib/'raw'/'good.wav';source.parent.mkdir();source.write_bytes(b'source')
            row=asset('good.wav',audio_id='pcm:good',family_id='family:good');row['path']=str(source)
            common.write_csv(index,[row],list(row))
            common.write_csv(selection,[{'id':'bgm_menu','path':str(source)}],['id','path'])
            output=proj/'assets'/'audio'/'menu.mp3';output.parent.mkdir(parents=True);output.write_bytes(b'encoded')
            relative=output.relative_to(proj).as_posix()
            expected={'needs_sha256':pipeline.file_sha256(needs),'selection_sha256':pipeline.file_sha256(selection)}
            payload={'schema':1,'project':str(proj),**expected,'success':True,
                     'sources':[{'id':'bgm_menu','source_path':str(source),'outputs':[relative],
                                 'output_sha256':{relative:pipeline.file_sha256(output)}}]}
            receipt=work/'process-result.json';receipt.write_text(json.dumps(payload))
            with patch.object(pipeline,'INDEX',index),patch.object(pipeline,'LIB',lib):
                record=pipeline.commit_usage(proj,needs,selection,receipt,expected)
                result=json.loads(record.read_text())
                self.assertEqual(result['paths'],[str(source)])
                self.assertEqual(result['asset_ids'],['pcm:good'])
                self.assertEqual(result['family_ids'],['family:good'])
                original=record.read_bytes()
                for change in ('failed','wrong-project','wrong-input','missing-output','corrupt-output','unselected-source','missing-required'):
                    bad=json.loads(json.dumps(payload));output.write_bytes(b'encoded')
                    if change=='failed':bad['success']=False
                    elif change=='wrong-project':bad['project']=str(root/'other')
                    elif change=='wrong-input':bad['selection_sha256']='old'
                    elif change=='missing-output':output.unlink()
                    elif change=='corrupt-output':output.write_bytes(b'bad')
                    elif change=='unselected-source':bad['sources'][0]['source_path']=str(lib/'raw'/'other.wav')
                    elif change=='missing-required':bad['sources'][0]['id']='not-required'
                    receipt.write_text(json.dumps(bad))
                    with self.assertRaises(SystemExit,msg=change):pipeline.commit_usage(proj,needs,selection,receipt,expected)
                    self.assertEqual(record.read_bytes(),original,change)
                output.write_bytes(b'encoded');receipt.write_text(json.dumps(payload));selection.write_text('changed')
                with self.assertRaises(SystemExit):pipeline.commit_usage(proj,needs,selection,receipt,expected)
                self.assertEqual(record.read_bytes(),original)


class KnownMusicVersionContracts(unittest.TestCase):
    def test_known_no_vocal_version_is_not_a_new_composition(self):
        original = asset("Three_Red_Hearts_Go.ogg")
        variant = asset("Three_Red_Hearts_Go_No_Vocal.ogg")
        self.assertEqual(ident.family(original), ident.family(variant))
        for row in (original, variant):
            row.pop("family_id")
        self.assertEqual(ident.family(original), ident.family(variant))
        self.assertNotEqual(ident.family(asset("Track1.ogg")), ident.family(asset("Track2.ogg")))
        explicit = asset("Different_No_Vocal.ogg", family_id="artist:separate-composition")
        self.assertEqual(ident.family(explicit), "artist:separate-composition")


if __name__=='__main__':
    unittest.main(verbosity=2)
