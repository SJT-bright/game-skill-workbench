import json
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_value_presentation as V
import art_receipt as R
from test_text_fit import TextFitCase, node, label

class Values(TextFitCase):
    def test_score_ttf_rejected_even_as_runtime_text(self):
        (self.root/'docs/text').mkdir(parents=True)
        (self.root/'docs/text/runtime-text.json').write_text(json.dumps({'labels':[{'path':'*','why':'dynamic'}]}))
        self.dump([node('Canvas/Failure/Score',1,100,250,240,50,label=label('Score 100',240,50))])
        self.assertIn('runtime_value_font',self.kinds(V.audit(self.root,[self.root/'dumps'])))
    def test_explanatory_sentence_allowed(self):
        self.dump([node('Canvas/Help/Text',1,20,200,360,40,label=label('Reach 100 points to win.',360,40))])
        self.assertTrue(V.audit(self.root,[self.root/'dumps'])['passed'])
    def test_bitmap_score_and_picture_word_allowed(self):
        (self.root/'docs/art').mkdir(parents=True)
        (self.root/'docs/art/longest-text.json').write_text(json.dumps({'labels':[{'path':'Canvas/Score/Value','text':'10000'}]}))
        self.dump([node('Canvas/Score/Value',2,160,200,220,40,label=label('10000',220,40,font='num',kind='bitmap'))])
        self.assertTrue(V.audit(self.root,[self.root/'dumps'])['passed'])
    def test_reward_overlap_and_separated_control(self):
        self.dump([node('Canvas/Result/Reward/Word',1,80,200,140,40,label=label('Reward:',140,40,text_w=140)),
                   node('Canvas/Result/Reward/Value',2,195,200,100,40,label=label('x200',100,40,text_w=100))],settle={'moved':0})
        self.assertIn('text_on_text',self.kinds(V.audit(self.root,[self.root/'dumps'])))
        for p in (self.root/'dumps').glob('*'):p.unlink()
        self.dump([node('Canvas/Result/Reward/Word',1,40,200,140,40,label=label('Reward:',140,40,text_w=140)),
                   node('Canvas/Result/Reward/Value',2,200,200,100,40,label=label('x200',100,40,text_w=100))],settle={'moved':0})
        self.assertNotIn('text_on_text',self.kinds(V.audit(self.root,[self.root/'dumps'])))
    def test_reward_overlap_in_gameplay(self):
        self.dump([node('Canvas/Reward/Word',1,80,200,140,40,label=label('Reward:',140,40,text_w=140)),
                   node('Canvas/Reward/Value',2,195,200,100,40,label=label('x200',100,40,text_w=100))],kind='gameplay')
        self.assertIn('text_on_text',self.kinds(V.audit(self.root,[self.root/'dumps'])))
    def test_picture_reward_word_cannot_overlap_bitmap_digits(self):
        (self.root/'docs/art').mkdir(parents=True)
        (self.root/'docs/art/longest-text.json').write_text(json.dumps({'labels':[{'path':'Canvas/Reward/Value','text':'x200'}]}))
        for x, expected in [(160, True),(260, False)]:
            for p in (self.root/'dumps').glob('*'):p.unlink()
            self.dump([node('Canvas/Reward/Word',1,70,200,150,40,sprite={'frame':'reward'}),
                       node('Canvas/Reward/Value',2,x,200,100,40,label=label('x200',100,40,font='num',kind='bitmap'))])
            self.assertEqual('value_word_on_digits' in self.kinds(V.audit(self.root,[self.root/'dumps'])),expected)

    def test_missing_runtime_does_not_pass(self):
        self.assertFalse(V.audit(self.root,[self.root/'dumps'])['passed'])
    def test_scene_ttf_reward_is_rejected(self):
        (self.root/'assets/test.fire').write_text(json.dumps([{'__type__':'cc.Node','_name':'Score'},
          {'__type__':'cc.Label','node':{'__id__':0},'_string':'Score 100'}]))
        self.assertIn('source_value_font',self.kinds(V.audit(self.root)))
    def test_missing_longest_value(self):
        self.dump([node('Canvas/Score',1,100,200,200,40,label=label('100',200,40,font='num',kind='bitmap'))])
        self.assertIn('value_longest_missing',self.kinds(V.audit(self.root,[self.root/'dumps'])))
    def test_separate_value_words_cannot_be_runtime_exempt(self):
        (self.root/'docs/text').mkdir(parents=True)
        (self.root/'docs/text/runtime-text.json').write_text(json.dumps({'labels':[{'path':'*','why':'dynamic'}]}))
        for index, word in enumerate(('Level', 'LEVEL', 'Lv.', 'Lvl', 'Goal', 'Stage', 'Score')):
            self.dump([node('Canvas/Hud/Caption',1,20,200,180,40,label=label(word,180,40))], name='word-'+str(index))
        findings=V.audit(self.root,[self.root/'dumps'])['findings']
        caught={f.get('text') for f in findings if f['kind']=='runtime_value_font'}
        self.assertEqual(caught, {'Level','LEVEL','Lv.','Lvl','Goal','Stage','Score'})

    def test_separate_separator_without_numeric_node_name_is_rejected(self):
        for index, symbol in enumerate(('/', '⁄', '∕', ':', '+', '−', '%', '×')):
            self.dump([node('Canvas/Row/Punctuation',1,150,200,30,40,label=label(symbol,30,40))], name='symbol-'+str(index))
        findings=V.audit(self.root,[self.root/'dumps'])['findings']
        self.assertEqual({f.get('text') for f in findings if f['kind']=='runtime_value_font'},
                         {'/','⁄','∕',':','+','−','%','×'})

    def test_source_level_and_separate_slash_rejected(self):
        (self.root/'assets/test.fire').write_text(json.dumps([
            {'__type__':'cc.Node','_name':'Caption'},
            {'__type__':'cc.Label','node':{'__id__':0},'_string':'Level'},
            {'__type__':'cc.Node','_name':'Separator'},
            {'__type__':'cc.RichText','node':{'__id__':2},'_string':'<b>/</b>'}]))
        findings=V.audit(self.root)['findings']
        self.assertEqual({f['text'] for f in findings if f['kind']=='source_value_font'}, {'Level','/'})

    def test_bitmap_separator_is_allowed(self):
        with (self.root/'assets/font/num.fnt').open('a') as font:
            font.write('\nchar id=47 x=0 y=0 width=30 height=100 xoffset=0 yoffset=0 xadvance=35 page=0 chnl=15')
        self.dump([node('Canvas/Row/Punctuation',1,150,200,30,40,
                        label=label('/',30,40,font='num',kind='bitmap'))])
        self.assertNotIn('runtime_value_font',self.kinds(V.audit(self.root,[self.root/'dumps'])))

    def test_r4r2_bitmap_label_glyph_missing_from_fnt(self):
        # 补查3 第 10 组: num.fnt has 0-9 only; the runtime shows 1.2K (方块收割者 units) and x50 (弹球传奇 first round)
        self.dump([node('Canvas/Hud/Coins/Value',1,100,200,200,40,label=label('1.2K',200,40,font='num',kind='bitmap')),
                   node('Canvas/Start/Reward/Value',2,100,300,200,40,label=label('x50',200,40,font='num',kind='bitmap')),
                   node('Canvas/Hud/Level/Value',3,100,400,200,40,label=label('12',200,40,font='num',kind='bitmap'))])
        r=V.audit(self.root,[self.root/'dumps'],write_charset=True)
        rows=[f for f in r['findings'] if f['kind']=='bitmap_glyph_missing']
        self.assertEqual({f['text']:f['missing'] for f in rows},{'1.2K':'.K','x50':'x'})
        self.assertIn('按这份字符集重画位图字',rows[0]['message'])
        cs=json.loads((self.root/'docs/english/charset.json').read_text())
        self.assertEqual(cs['charset']['fonts'][0]['missing'],'.Kx')
    def test_r4r2_covered_glyphs_and_dry_run_write_nothing(self):
        with (self.root/'assets/font/num.fnt').open('a') as font:
            for ch in '.Kx':
                font.write('\nchar id=%d x=0 y=0 width=30 height=100 xoffset=0 yoffset=0 xadvance=35 page=0 chnl=15'%ord(ch))
        self.dump([node('Canvas/Hud/Coins/Value',1,100,200,200,40,label=label('1.2K',200,40,font='num',kind='bitmap')),
                   node('Canvas/Start/Reward/Value',2,100,300,200,40,label=label('x50',200,40,font='num',kind='bitmap'))])
        self.assertNotIn('bitmap_glyph_missing',self.kinds(V.audit(self.root,[self.root/'dumps'],write_charset=True)))
        self.assertFalse((self.root/'docs/english/charset.json').exists())

    def test_bitmap_alphabet_cannot_replace_fixed_level_word(self):
        self.dump([node('Canvas/Caption',1,20,200,160,40,
                        label=label('Level',160,40,font='num',kind='bitmap'))])
        self.assertIn('runtime_value_font',self.kinds(V.audit(self.root,[self.root/'dumps'])))

    def test_whole_picture_word_and_picture_separator_allowed(self):
        self.dump([node('Canvas/Row/Caption',1,20,200,100,40,sprite={'frame':'txt_level'}),
                   node('Canvas/Row/Separator',2,250,200,20,40,sprite={'frame':'glyph_slash'})])
        self.assertNotIn('runtime_value_font',self.kinds(V.audit(self.root,[self.root/'dumps'])))

    def test_body_sentence_and_fraction_explanation_not_value_caption(self):
        for text in ('Reach level 5 to unlock.', 'Tap / Drag', 'Gain 50% more points.', 'Collect 12 of 24 items.'):
            self.assertFalse(V.value_text(text, 'Canvas/Help/Body'), text)

    def proof(self):
        return {'revision':V.REVISION,'mode':'runtime','passed':True,'pages':2,'source_sha256':V.source_fingerprint(self.root)}
    def test_receipt_missing_old_fail_and_uncovered_block(self):
        self.assertEqual(R.check(self.root,board='localize')['level'],'block')
        for status in ['pass','fail','not_covered_3x']:
            R.write(self.root,status)
            self.assertEqual(R.check(self.root,board='localize')['level'],'block')
    def test_current_receipt_passes_and_code_change_blocks(self):
        R.write(self.root,'pass',{'value_presentation':self.proof()})
        self.assertEqual(R.check(self.root,board='localize')['level'],'ok')
        (self.root/'assets/layout.ts').write_text('score.x=20;')
        self.assertEqual(R.check(self.root,board='localize')['level'],'block')
    def test_source_only_receipt_cannot_pass(self):
        proof=self.proof();proof['mode']='source'
        R.write(self.root,'pass',{'value_presentation':proof})
        self.assertEqual(R.check(self.root,board='localize')['level'],'block')
    def test_remake_legacy_policy_unchanged(self):
        (self.root/'assets/a.png').write_bytes(b'fixture')
        self.assertEqual(R.check(self.root,board='remake',policy='legacy')['level'],'warn')

if __name__=='__main__':unittest.main()
