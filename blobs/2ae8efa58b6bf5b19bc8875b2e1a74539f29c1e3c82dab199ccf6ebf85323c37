"""生成时预防 R4Q1 (补查3 group 1, 5 games): bind_art.py binds a whole new picture as a BUTTON SLOT (well under 1 s).

Fixtures follow the census cases: 奔跑吧巨人 x2 button (whole "x2" picture, old lbBtnMultiple still drawn and written,
grey state left on the old frame), 合成进化恐龙 (button Widget and parent Layout both moving it), 火箭三消 (a slot not
rebound: old NO THANKS showing; the RichText goal treated as a title of its own).
  1 2.4   bind on btn_x2: CJK label off (component + string kept), price "50" and the icon stay on, Widget off
          (parent Layout owns), sizeMode CUSTOM in the new ratio, Button target = slot, all transition frames = new
          frame, enableAutoGrayEffect on, the record says so. Old code: label still on, Widget on, grey frame old.
  2 3.x   same on a 3.x prefab (_enabled / _transition / _normalSprite ...); own Layout resize CONTAINER -> NONE;
          SPRITE transition -> COLOR (disabledColor greys it).
  3 list  --slots lists btn_x2 [已接] and btn_no [未接]; the RichText's generated child Label is not a slot of its
          own; exit 1 while one is 未接.
  4 modes "bg" leaves labels on; a button-less node is bound as before (no slot record).
Run: python3 test_bind_art_slot.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import bind_art as tool
from test_bind_art import node, sprite
from test_bind_art_3x import Base, n3, sp3, ut


def label(nid, text, kind='cc.Label'):
    return {'__type__': kind, 'node': {'__id__': nid}, '_enabled': True,
            ('_N$string' if kind == 'cc.RichText' else '_string'): text}


class Slot24(Base):
    def make(self):
        self.old24 = self.png24('old_btn', (200, 200), (0, 0, 200, 200)) + '-f'
        self.grey = self.png24('old_btn_grey', (200, 200), (0, 0, 200, 200)) + '-f'
        self.png24('btn_x2_en', (300, 120), (0, 0, 300, 120))
        old = {'__uuid__': self.old24}
        d = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
             node('Result', None, [2], [3, 13], 720, 1280),
             {'__type__': 'cc.Layout', 'node': {'__id__': 1}, '_enabled': True, '_N$layoutType': 1, '_resize': 0},
             node('btn_x2', {'__id__': 1}, [4, 5, 6], [7, 9, 11]),
             sprite(3, self.old24),
             {'__type__': 'cc.Button', 'node': {'__id__': 3}, '_enabled': True, '_N$interactable': True,
              '_N$enableAutoGrayEffect': False, '_N$transition': 2, '_N$normalSprite': old, '_N$pressedSprite': old,
              '_N$hoverSprite': old, '_N$disabledSprite': {'__uuid__': self.grey}, '_N$target': {'__id__': 3}},
             {'__type__': 'cc.Widget', 'node': {'__id__': 3}, '_enabled': True, '_alignFlags': 36},
             node('lbBtnMultiple', {'__id__': 3}, [8], w=150, h=50), label(7, '双倍领取'),
             node('icon', {'__id__': 3}, [10], w=40, h=40), sprite(9, self.old24),
             node('price', {'__id__': 3}, [12], w=60, h=40), label(11, '50'),
             node('btn_no', {'__id__': 1}, [14, 15], [16]), sprite(13, self.old24),
             {'__type__': 'cc.Button', 'node': {'__id__': 13}, '_N$transition': 3, '_N$target': {'__id__': 13}},
             node('goal', {'__id__': 13}, [17], [18], w=150, h=50),
             label(16, '<b>目标</b> 不用了', 'cc.RichText'),
             node('RICHTEXT_CHILD', {'__id__': 16}, [19], w=40, h=40), label(18, '目标')]
        p = self.root / 'assets' / 'Result.prefab'
        p.write_text(json.dumps(d, indent=2))
        return p

    def run_bind(self, **kw):
        b = {'prefab': 'assets/Result.prefab', 'node': 'Result/btn_x2', 'image': 'assets/ui/btn_x2_en.png'}
        b.update(kw)
        m = self.root / 'bind.json'
        m.write_text(json.dumps({'bindings': [b]}))
        return tool.run_bind(self.root, m, '', False)[0]

    def test_1_slot_24(self):
        self.make()
        rec = self.run_bind()
        d = json.loads((self.root / 'assets' / 'Result.prefab').read_text())
        self.assertFalse(d[8]['_enabled'], 'old CJK label must stop drawing')
        self.assertEqual(d[8]['_string'], '双倍领取', 'string stays for game code')
        self.assertTrue(d[12]['_enabled'], 'price number stays on')
        self.assertEqual(d[10]['_spriteFrame']['__uuid__'], self.old24, 'icon kept')
        self.assertFalse(d[6]['_enabled'], 'Widget off: parent Layout is the one layout owner')
        self.assertEqual(d[4]['_sizeMode'], tool.CUSTOM)
        self.assertEqual(d[3]['_contentSize']['width'], 200.0)
        self.assertEqual(d[3]['_contentSize']['height'], 80.0)
        new = d[4]['_spriteFrame']
        for k in ('_N$normalSprite', '_N$pressedSprite', '_N$hoverSprite', '_N$disabledSprite'):
            self.assertEqual(d[5][k], new, k)
        self.assertTrue(d[5]['_N$enableAutoGrayEffect'])
        self.assertEqual(d[5]['_N$target'], {'__id__': 3})
        self.assertIn('parent cc.Layout', rec['slot']['layout_owner'])
        self.assertTrue(rec['slot']['button']['interactable'])
        log = json.loads((self.root / 'docs' / 'art' / 'bind_log.json').read_text())
        self.assertIn('layout_owner', log['bindings']['assets/Result.prefab#Result/btn_x2']['slot'])

    def test_3_slot_list(self):
        self.make()
        rows = tool.slot_list(self.root)
        self.assertEqual([(r['slot'], r['bound']) for r in rows], [('Result/btn_x2', False), ('Result/btn_no', False)])
        self.assertEqual(rows[1]['text'], ['<b>目标</b> 不用了'], 'RichText child label is not its own entry')
        self.run_bind()
        rows = tool.slot_list(self.root)
        self.assertEqual([(r['slot'], r['bound']) for r in rows], [('Result/btn_x2', True), ('Result/btn_no', False)])
        p = subprocess.run([sys.executable, str(Path(tool.__file__)), '--project', str(self.root), '--slots'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn('[未接] assets/Result.prefab Result/btn_no', p.stdout)

    def test_4_modes(self):
        self.make()
        rec = self.run_bind(slot='bg')
        d = json.loads((self.root / 'assets' / 'Result.prefab').read_text())
        self.assertTrue(d[8]['_enabled'])
        self.assertEqual(rec['slot']['mode'], 'bg')
        with self.assertRaisesRegex(tool.BindError, 'slot'):
            self.run_bind(slot='nope')


class Slot3x(Base):
    def make(self):
        self.png3('btn_en', (300, 120), (0, 0, 300, 120))
        old = {'__uuid__': self.old, '__expectedType__': 'cc.SpriteFrame'}
        d = [{'__type__': 'cc.Prefab', '_name': 'Result', 'data': {'__id__': 1}},
             n3('Result', None, [2, 3], [4]), ut(1, 720, 1280),
             {'__type__': 'cc.Layout', 'node': {'__id__': 1}, '_enabled': True, '_layoutType': 2, '_resizeMode': 0},
             n3('btn', {'__id__': 1}, [5, 6, 7, 8, 12], [9]), ut(4, 200, 200), sp3(4, self.old),
             {'__type__': 'cc.Button', 'node': {'__id__': 4}, '_enabled': True, '_interactable': False,
              '_transition': 2, '_normalSprite': old, '_hoverSprite': old, '_pressedSprite': old,
              '_disabledSprite': old, '_target': {'__id__': 4}},
             {'__type__': 'cc.Widget', 'node': {'__id__': 4}, '_enabled': True, '_alignFlags': 18},
             n3('lbl', {'__id__': 4}, [10, 11]), ut(9, 150, 50), label(9, '领取'),
             {'__type__': 'cc.Layout', 'node': {'__id__': 4}, '_enabled': True, '_layoutType': 1, '_resizeMode': 1}]
        (self.root / 'assets' / 'Result.prefab').write_text(json.dumps(d, indent=2))

    def test_2_slot_3x(self):
        self.make()
        m = self.root / 'bind.json'
        m.write_text(json.dumps({'bindings': [{'prefab': 'assets/Result.prefab', 'node': 'Result/btn',
                                               'image': 'assets/ui/btn_en.png'}]}))
        rec = tool.run_bind(self.root, m, '', False)[0]
        d = json.loads((self.root / 'assets' / 'Result.prefab').read_text())
        self.assertFalse(d[11]['_enabled'])
        self.assertEqual(d[11]['_string'], '领取')
        self.assertFalse(d[8]['_enabled'])
        self.assertEqual(d[12]['_resizeMode'], 0)
        self.assertEqual(d[6]['_sizeMode'], tool.CUSTOM)
        self.assertEqual((d[5]['_contentSize']['width'], d[5]['_contentSize']['height']), (200.0, 80.0))
        new = d[6]['_spriteFrame']
        for k in ('_normalSprite', '_hoverSprite', '_pressedSprite', '_disabledSprite'):
            self.assertEqual(d[7][k], new, k)
        self.assertEqual(d[7]['_transition'], tool.COLOR_TRANSITION)
        self.assertNotIn('_N$enableAutoGrayEffect', d[7])
        self.assertFalse(rec['slot']['button']['interactable'])
        self.assertEqual(tool.slot_list(self.root)[0]['bound'], True)

    def test_4_plain_node_unchanged(self):
        self.prefab()
        rec = self.bind('old_skin')
        self.assertNotIn('slot', rec)


if __name__ == '__main__':
    unittest.main()
