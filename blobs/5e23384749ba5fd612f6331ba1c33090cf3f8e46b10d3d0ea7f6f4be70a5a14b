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
    def test_missing_runtime_does_not_pass(self):
        self.assertFalse(V.audit(self.root,[self.root/'dumps'])['passed'])
    def test_scene_ttf_reward_is_rejected(self):
        (self.root/'assets/test.fire').write_text(json.dumps([{'__type__':'cc.Node','_name':'Score'},
          {'__type__':'cc.Label','node':{'__id__':0},'_string':'Score 100'}]))
        self.assertIn('source_value_font',self.kinds(V.audit(self.root)))
    def test_missing_longest_value(self):
        self.dump([node('Canvas/Score',1,100,200,200,40,label=label('100',200,40,font='num',kind='bitmap'))])
        self.assertIn('value_longest_missing',self.kinds(V.audit(self.root,[self.root/'dumps'])))
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
