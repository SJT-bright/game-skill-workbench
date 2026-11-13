#!/usr/bin/env python3
"""english_copy_guard.py (生成时预防 R4N5, 补查2 第 2、8 组): the value glyph set comes from the copy table and the
format strings in code (`x{n}`, `{a}/{b}`, `'x' + n`, mm:ss, %), so 弹球传奇's digits.fnt (0-9 only, first round shows
x50) is reported as missing `x`; a literal \\n becomes a line break; `<color>..</c>` is caught; an ad button saying
CLAIM is caught. Run: python3 -m unittest test_english_copy_guard   (under a second, no browser, no Creator)"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_copy_guard as G  # noqa: E402


def fnt(chars):
    lines = ['info face="digits" size=40', 'common lineHeight=48 base=40 pages=1', 'page id=0 file="digits.png"',
             'chars count=%d' % len(chars)]
    lines += ['char id=%d x=0 y=0 width=20 height=40 xoffset=0 yoffset=0 xadvance=22 page=0 chnl=15' % ord(c) for c in chars]
    return '\n'.join(lines) + '\n'


def win_prefab():
    """0 Prefab, 1 Win root, 2 btnDouble node (Button + child label), 3 Button, 4 label node, 5 Label 'CLAIM x2',
    6 tip node, 7 Label with a literal \\n, 8 help node, 9 RichText with </c>."""
    return [
        {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
        {'__type__': 'cc.Node', '_name': 'WinPanel', '_parent': None, '_children': [{'__id__': 2}, {'__id__': 6}, {'__id__': 8}],
         '_components': []},
        {'__type__': 'cc.Node', '_name': 'btnDouble', '_parent': {'__id__': 1}, '_children': [{'__id__': 4}],
         '_components': [{'__id__': 3}]},
        {'__type__': 'cc.Button', 'node': {'__id__': 2}},
        {'__type__': 'cc.Node', '_name': 'txt', '_parent': {'__id__': 2}, '_children': [], '_components': [{'__id__': 5}]},
        {'__type__': 'cc.Label', 'node': {'__id__': 4}, '_string': 'CLAIM x2', '_N$string': 'CLAIM x2'},
        {'__type__': 'cc.Node', '_name': 'tip', '_parent': {'__id__': 1}, '_children': [], '_components': [{'__id__': 7}]},
        {'__type__': 'cc.Label', 'node': {'__id__': 6}, '_string': 'Play 30 minutes a day.\\nRest your eyes.',
         '_N$string': 'Play 30 minutes a day.\\nRest your eyes.'},
        {'__type__': 'cc.Node', '_name': 'help', '_parent': {'__id__': 1}, '_children': [], '_components': [{'__id__': 9}]},
        {'__type__': 'cc.RichText', 'node': {'__id__': 8}, '_N$string': 'Match <color=#ffde00>3</c> to clear'},
    ]


class Guard(unittest.TestCase):
    def test_mixed_case_copy_and_amount_enter_first_asset_list(self):
        p = self.root / 'docs/copy/copy-table.csv'
        p.write_text('zh,en,where,pointer\n领取,Claim,,\n奖励,20 COINS,,\n', encoding='utf-8')
        cs = G.charset(self.root)
        self.assertIn('Claim', cs['word_images'])
        self.assertIn('COINS', cs['word_images'])
        self.assertNotIn('20 COINS', cs['word_images'])
        self.assertEqual(cs['word_sources']['Claim'], 'docs/copy/copy-table.csv')

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='copyguard_'))
        for d in ('assets/ui', 'assets/scripts', 'assets/font', 'docs/copy'):
            (self.root / d).mkdir(parents=True)
        (self.root / 'docs/copy/copy-table.csv').write_text(
            'zh,en,where,pointer\n倍数,x{n},assets/ui/Win.prefab,/5/_string\n进度,{a}/{b},,\n领取,CLAIM,,\n'
            '不用了,NO THANKS,,\n', encoding='utf-8')
        # 弹球传奇: the first round shows "x" + count; a timer built with ':'; a percent
        (self.root / 'assets/scripts/Hud.js').write_text(
            "this.combo.string = 'x' + count;\nthis.timer.string = mm + ':' + ss;\nthis.pct.string = `${p}%`;\n"
            "node.width = w + 'px';\n", encoding='utf-8')
        (self.root / 'assets/font/digits.fnt').write_text(fnt(G.DIGITS), encoding='utf-8')
        self.prefab = self.root / 'assets/ui/Win.prefab'
        self.prefab.write_text(json.dumps(win_prefab(), indent=2), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_value_charset_from_copy_table_and_code(self):
        cs = G.charset(self.root)
        for ch in 'x/:%' + G.DIGITS:
            self.assertIn(ch, cs['value_charset'])
        self.assertNotIn('p', cs['value_charset'], "'px' is a CSS unit, not a value glyph")
        self.assertEqual(cs['word_images'], ['CLAIM', 'NO THANKS'])

    def test_digits_only_fnt_is_reported_missing_x(self):
        rec = G.run(self.root, dry_run=True)
        font = rec['charset']['fonts'][0]
        self.assertEqual(font['font'], 'assets/font/digits.fnt')
        self.assertIn('x', font['missing'], 'OLD WAY BUG: a 0-9 font passes while the first round shows x50')
        self.assertTrue(any('lacks' in b for b in rec['warnings']))
        (self.root / 'assets/font/digits.fnt').write_text(fnt(G.DIGITS + 'x/:%+'), encoding='utf-8')
        self.assertFalse(G.run(self.root, dry_run=True)['charset']['fonts'][0]['missing'])

    def test_literal_newline_becomes_a_line_break(self):
        rec = G.run(self.root)
        lab = json.loads(self.prefab.read_text(encoding='utf-8'))[7]
        self.assertEqual(lab['_string'], 'Play 30 minutes a day.\nRest your eyes.')
        self.assertEqual(lab['_N$string'], lab['_string'])
        self.assertEqual(rec['checks']['files_written'], ['assets/ui/Win.prefab'])
        self.assertTrue((self.root / 'docs/english/copy-guard/backup/assets/ui/Win.prefab').is_file())

    def test_dry_run_writes_nothing(self):
        raw = self.prefab.read_text(encoding='utf-8')
        rec = G.run(self.root, dry_run=True)
        self.assertEqual(self.prefab.read_text(encoding='utf-8'), raw)
        self.assertTrue(rec['checks']['literal_newline'] and not rec['checks']['literal_newline'][0]['fixed'])

    def test_richtext_tags_pair(self):
        self.assertEqual(G.tag_problems('Match <color=#ffde00>3</color> to <b>clear</b><br/>'), [])
        self.assertEqual(G.tag_problems('Match <color=#ffde00>3</c> to clear'), ['</c> is not a Cocos RichText tag',
                                                                                 '<color> is never closed'])
        self.assertEqual(G.tag_problems('<size=30><color=red>A</size></color>'), ['</size> closes <color>',
                                                                                 '</color> closes <size>'])
        rec = G.run(self.root, dry_run=True)
        self.assertEqual([r['where'] for r in rec['checks']['richtext_tags']], ['assets/ui/Win.prefab:WinPanel/help'])

    def test_ad_button_text(self):
        rec = G.run(self.root, dry_run=True)
        self.assertEqual([r['where'] for r in rec['checks']['ad_button_review']], ['assets/ui/Win.prefab:WinPanel/btnDouble'])
        self.assertEqual(rec['checks']['ad_button_text'], [], 'only named like an ad button: review, not blocking')
        (self.root / 'docs/game_capabilities.json').write_text(json.dumps(
            {'schema': 1, 'ad_entries': [{'role': 'double', 'button': 'WinPanel/btnDouble'}]}), encoding='utf-8')
        rec = G.run(self.root, dry_run=True)
        self.assertEqual([r['text'] for r in rec['checks']['ad_button_text']], ['CLAIM x2'])
        objs = json.loads(self.prefab.read_text(encoding='utf-8'))
        objs[5]['_string'] = objs[5]['_N$string'] = 'WATCH AD x2'
        self.prefab.write_text(json.dumps(objs), encoding='utf-8')
        self.assertEqual(G.run(self.root, dry_run=True)['checks']['ad_button_text'], [])

    def test_clean_project_passes_and_exit_codes(self):
        objs = json.loads(self.prefab.read_text(encoding='utf-8'))
        objs[5]['_string'] = objs[5]['_N$string'] = 'WATCH AD x2'
        objs[9]['_N$string'] = 'Match <color=#ffde00>3</color> to clear'
        self.prefab.write_text(json.dumps(objs), encoding='utf-8')
        (self.root / 'assets/font/digits.fnt').write_text(fnt(G.DIGITS + 'x/:%'), encoding='utf-8')
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(G.main(['--project', str(self.root)]), 0)    # fixes the \n, then nothing blocks
            self.assertEqual(G.main(['--project', str(self.root / 'nope')]), 2)
        self.assertTrue((self.root / 'docs/english/charset.json').is_file())

    def test_main_dry_run_leaves_the_project_untouched(self):
        # lead (11-05): a calibration run with --dry-run and no --out wrote docs/english/charset.json into 4 English games
        import contextlib, io
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with contextlib.redirect_stdout(io.StringIO()):
            G.main(['--project', str(self.root), '--dry-run'])
        self.assertFalse((self.root / 'docs/english/charset.json').exists())
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')), before)
        outdir = Path(tempfile.mkdtemp(prefix='copyguard_out_'))
        self.addCleanup(shutil.rmtree, outdir, True)
        out = outdir / 'guard-out.json'
        with contextlib.redirect_stdout(io.StringIO()):
            G.main(['--project', str(self.root), '--dry-run', '--out', str(out)])
        self.assertTrue(out.is_file())
        self.assertFalse((self.root / 'docs/english/charset.json').exists())


# R4P4: the format string is built on one line and put on the label on a later one
TWO_LINE = '''
showCombo(count) {
    const t = 'x' + count;
    this.combo.string = t;
}
showPct(p) {
    let txt: string = `${p}%`;
    this.pct.string = txt;
}
showRange(lo, hi) {
    const head = lo + '-';
    const full = head + hi;
    this.range.getComponent(cc.Label).setString(full);
}
load(id) {
    const url = base + '?' + id;     // built, never shown
    cc.log(url);
    this.title.string = name;        // a parameter: nothing to follow
}
'''


class TwoLineFormats(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='copyguard2_'))
        (self.root / 'assets/scripts').mkdir(parents=True)
        (self.root / 'assets/scripts/Hud.ts').write_text(TWO_LINE, encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_variable_built_on_an_earlier_line(self):
        cs = G.charset(self.root)['value_charset']
        for ch in 'x%-':
            self.assertIn(ch, cs, 'OLD WAY BUG: %r built one line above label.string = t was not in the set' % ch)
        self.assertNotIn('?', cs, 'a URL built and never shown stays out')

    def test_lookback_is_bounded(self):
        far = "const t = 'x' + n;\n" + 'a();\n' * (G.TRACK_BACK + 5) + 'this.combo.string = t;\n'
        self.assertNotIn('x', G.script_value_chars(far)[0])



class NumberFormatUnits(unittest.TestCase):
    """R4R2 (补查3 第 10 组): 方块收割者 EnglishNumbers.js -- the unit table and the 'E' never pass a label line."""
    FORMATTER = ("var UNITS = ['K', 'M', 'B', 'T', 'Q'];\n"
                 "function trim(t) { return t.replace(/0+$/, ''); }\n"
                 "function scientific(v) { var p = v.toExponential(2).split('e');\n"
                 "    return trim(p[0]) + 'E' + String(Number(p[1])); }\n"
                 "function format(v) { var unit = 0, places = 2; var scaled = v / Math.pow(1000, unit + 1);\n"
                 "    return trim(scaled.toFixed(places)) + UNITS[unit]; }\n"
                 "function show(label, v) { label.string = format(v); }\n")

    def test_unit_table_and_glued_symbols_enter_value_charset(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, text in (('assets/scripts/EnglishNumbers.js', self.FORMATTER),
                              ('assets/scripts/Settings.js', "var LEVELS = ['Off', 'Low', 'High'];\nlabel.string = LEVELS[i];\n"),
                              ('assets/font/digits.fnt', '\n'.join('char id=%d x=0' % (48 + i) for i in range(10)))):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding='utf-8')
            cs = G.charset(root)
            for ch in 'KMBTQE.':
                self.assertIn(ch, cs['value_charset'])
            for ch in 'OfLowHigh':
                self.assertNotIn(ch, cs['value_charset'].replace('0123456789', ''))
            self.assertEqual(set(cs['fonts'][0]['missing']), set('KMBTQE.'))


class FirstArtFixedCaptions(unittest.TestCase):
    """The first art list includes fixed UI words without collecting prose or names."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='copyguard_fixed_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'assets/ui').mkdir(parents=True)
        self.prefab = self.root / 'assets/ui/Rewards.prefab'

    def write_labels(self, entries):
        objects = [
            {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
            {'__type__': 'cc.Node', '_name': 'Rewards', '_parent': None,
             '_children': [], '_components': []},
        ]
        for name, text, rich in entries:
            node_id = len(objects)
            objects[1]['_children'].append({'__id__': node_id})
            objects += [
                {'__type__': 'cc.Node', '_name': name, '_parent': {'__id__': 1},
                 '_children': [], '_components': [{'__id__': node_id + 1}]},
                {'__type__': 'cc.RichText' if rich else 'cc.Label', 'node': {'__id__': node_id},
                 '_N$string': text},
            ]
        self.prefab.write_text(json.dumps(objects), encoding='utf-8')

    def test_static_score_and_mixed_case_claim_enter_original_word_list_with_sources(self):
        self.write_labels([('ScoreLabel', 'SCORE', False),
                           ('ClaimAction', '<color=#ffffff>Claim</color>', True)])
        cs = G.charset(self.root)
        self.assertEqual(cs['word_images'], ['Claim', 'SCORE'])
        self.assertEqual(cs['word_sources']['SCORE'], 'assets/ui/Rewards.prefab:Rewards/ScoreLabel')
        self.assertEqual(cs['word_sources']['Claim'], 'assets/ui/Rewards.prefab:Rewards/ClaimAction')
        self.assertEqual(set(cs['value_charset']), set(G.DIGITS))

    def test_reward_amount_keeps_digits_and_separate_unit_word(self):
        self.write_labels([('RewardAmount', '+20 COINS', False), ('ScoreValue', 'Score 125', False)])
        cs = G.charset(self.root)
        self.assertEqual(cs['word_images'], ['COINS', 'Score'])
        self.assertNotIn('+20 COINS', cs['word_images'])
        self.assertNotIn('Score 125', cs['word_images'])
        self.assertEqual(set(cs['value_charset']), set(G.DIGITS + '+'))

    def test_prose_names_placeholders_and_code_strings_stay_out(self):
        self.write_labels([('Help', 'Claim your coins after each round.', False),
                           ('Nickname', 'Alice', False), ('PlayerName', 'SCORE', False),
                           ('DisplayName', 'Claim', False), ('Title', 'ALICE', False),
                           ('Player', '{playerName}', False), ('Prompt', 'Claim {name}', False),
                           ('Summary', 'SCORE {value}', False)])
        (self.root / 'assets/Unused.js').write_text(
            "const caption = 'Claim'; const nickname = 'SCORE'; this.name.string = playerName;\n",
            encoding='utf-8')
        self.assertEqual(G.charset(self.root)['word_images'], [])

    def test_dry_run_preserves_all_project_bytes_with_new_fixed_words(self):
        self.write_labels([('ScoreLabel', 'SCORE', False), ('ClaimAction', 'Claim', False),
                           ('RewardAmount', '+20 COINS', False)])
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        rec = G.run(self.root, dry_run=True)
        self.assertEqual(rec['charset']['word_images'], ['COINS', 'Claim', 'SCORE'])
        self.assertEqual({p.relative_to(self.root).as_posix(): p.read_bytes()
                          for p in self.root.rglob('*') if p.is_file()}, before)


if __name__ == '__main__':
    unittest.main()
