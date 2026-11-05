#!/usr/bin/env python3
"""fit_english_labels.py (生成时预防 P06 1/5): a 2.4 settings prefab whose "MUSIC 100%" overflows its 120-wide box
the old way (audit_text_fit.py reports text_cut) and fits after the tool; a label that fits stays byte-for-byte the
same; a three-line description goes on the to-fix list; same-name siblings get a suffix unless a script names them;
a 3.x prefab; a countdown measured as 00:00:00; a BMFont; an unreadable TTF still measured (no fontTools needed).
Run: python3 -m unittest test_fit_english_labels   (a few seconds, no browser, no Creator)"""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit_english_labels as F  # noqa: E402

AUDIT_DIR = HERE.parent.parent / 'remake-core' / 'scripts'
DESC = 'Tap anywhere to jump over the logs and collect every shiny coin on the long way home'


def node24(name, parent, size, comps=(), children=()):
    return {'__type__': 'cc.Node', '_name': name, '_objFlags': 0, '_parent': parent, '_children': list(children),
            '_active': True, '_components': [{'__id__': c} for c in comps], '_opacity': 255,
            '_contentSize': {'__type__': 'cc.Size', 'width': size[0], 'height': size[1]},
            '_anchorPoint': {'__type__': 'cc.Vec2', 'x': 0.5, 'y': 0.5}}


def label24(node, text, size, overflow, wrap=False, line_h=None, font=None):
    return {'__type__': 'cc.Label', '_name': '', 'node': {'__id__': node}, '_enabled': True, '_string': text,
            '_N$string': text, '_fontSize': size, '_lineHeight': line_h or size * 1.25, '_enableWrapText': wrap,
            '_N$file': {'__uuid__': font} if font else None, '_isSystemFontUsed': not font, '_spacingX': 0,
            '_styleFlags': 0, '_N$horizontalAlign': 1, '_N$verticalAlign': 1, '_N$fontFamily': 'Arial',
            '_N$overflow': overflow, '_N$cacheMode': 0}


def settings_prefab():
    """0 Prefab, 1 root, 2 music node, 3 music label, 4 play node, 5 play label, 6 desc node, 7 desc label,
    8 Btn, 9 Btn (same name), 10 title, 11 title (same name, named by the script), 12 timer node, 13 timer label."""
    o = [{'__type__': 'cc.Prefab', 'data': {'__id__': 1}}]
    o.append(node24('SettingPanel', None, (600, 900), children=[{'__id__': i} for i in (2, 4, 6, 8, 9, 10, 11, 12)]))
    o.append(node24('musicLabel', {'__id__': 1}, (120, 40), comps=[3]))
    o.append(label24(2, 'MUSIC 100%', 24, overflow=1))                     # CLAMP, one line
    o.append(node24('playLabel', {'__id__': 1}, (200, 50), comps=[5]))
    o.append(label24(4, 'PLAY', 30, overflow=1))
    o.append(node24('descLabel', {'__id__': 1}, (220, 60), comps=[7]))
    o.append(label24(6, DESC, 22, overflow=1, wrap=True, line_h=28))      # two lines of room, needs more
    o.append(node24('Btn', {'__id__': 1}, (100, 60)))
    o.append(node24('Btn', {'__id__': 1}, (100, 60)))
    o.append(node24('title', {'__id__': 1}, (100, 60)))
    o.append(node24('title', {'__id__': 1}, (100, 60)))
    o.append(node24('timer', {'__id__': 1}, (60, 30), comps=[13]))
    o.append(label24(12, '05:00', 24, overflow=1))
    return o


def prefab3x():
    return [
        {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
        {'__type__': 'cc.Node', '_name': 'Home', '_parent': None, '_children': [{'__id__': 2}], '_components': []},
        {'__type__': 'cc.Node', '_name': 'coinText', '_parent': {'__id__': 1}, '_children': [],
         '_components': [{'__id__': 3}, {'__id__': 4}]},
        {'__type__': 'cc.UITransform', 'node': {'__id__': 2},
         '_contentSize': {'__type__': 'cc.Size', 'width': 110, 'height': 40}},
        {'__type__': 'cc.Label', 'node': {'__id__': 2}, '_string': 'Free Coins', '_fontSize': 24, '_lineHeight': 30,
         '_overflow': 1, '_enableWrapText': True, '_font': None, '_isSystemFontUsed': True, '_isBold': True,
         '_enableOutline': True, '_outlineWidth': 2},
    ]


class FitCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fitlabels_'))
        (self.root / 'assets/ui').mkdir(parents=True)
        (self.root / 'assets/scripts').mkdir(parents=True)
        (self.root / 'assets/scripts/Setting.js').write_text("var t = this.node.getChildByName('title');\n", encoding='utf-8')
        self.prefab = self.root / 'assets/ui/SettingPanel.prefab'
        self.prefab.write_text(json.dumps(settings_prefab(), indent=2), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def objs(self, path=None):
        return json.loads((path or self.prefab).read_text(encoding='utf-8'))

    def by(self, rec, part, name):
        return next(r for r in rec[part] if r['where'].endswith('/' + name))

    # ---------------------------------------------------------------------------------------------- the P06 cases
    def test_music_100_percent_shrinks_into_its_box(self):
        before = self.objs()[3]
        need = F.table_width('MUSIC 100%', 24)
        self.assertGreater(need, 120, 'fixture: the old way the text is wider than the box')
        rec = F.run(self.root)
        lab = self.objs()[3]
        self.assertEqual(before['_N$overflow'], 1)
        self.assertEqual(lab['_N$overflow'], 2, 'overflow = SHRINK')
        self.assertFalse(lab['_enableWrapText'])
        ch = self.by(rec, 'changed', 'musicLabel')
        self.assertLessEqual(ch['shrunk_width'], 120)
        self.assertGreaterEqual(ch['min_font_size'], 24 * F.MIN_SHRINK)
        self.assertEqual(ch['longest'], 'MUSIC 100%')
        self.assertIn('assets/ui/SettingPanel.prefab', rec['files_written'])
        self.assertTrue((self.root / 'docs/english/fit-labels/backup/assets/ui/SettingPanel.prefab').is_file())

    def test_a_label_that_fits_is_not_touched(self):
        before = self.objs()[5]
        F.run(self.root)
        self.assertEqual(self.objs()[5], before)

    def test_three_line_description_goes_on_the_to_fix_list(self):
        rec = F.run(self.root)
        t = self.by(rec, 'todo', 'descLabel')
        self.assertGreaterEqual(t['lines'], 3)
        self.assertEqual(t['capacity'], 2)
        self.assertEqual(self.objs()[7]['_N$overflow'], 1, 'multi-line is not rewritten, only listed')
        self.assertFalse(rec['passed'])

    def test_countdown_is_measured_as_00_00_00(self):
        rec = F.run(self.root)
        t = self.by(rec, 'todo', 'timer')
        self.assertEqual(t['longest'], '00:00:00')
        self.assertLess(t['ratio'], F.MIN_SHRINK, 'shrinking below 70 % is not allowed: listed instead')

    def test_same_name_siblings_get_a_suffix_unless_a_script_names_them(self):
        rec = F.run(self.root)
        names = [o.get('_name') for o in self.objs() if o.get('__type__') == 'cc.Node']
        self.assertIn('Btn', names)
        self.assertIn('Btn_2', names)
        self.assertEqual(names.count('title'), 2, 'getChildByName("title") in a script: kept, only reported')
        kept = next(r for r in rec['same_name'] if r['name'] == 'title')
        self.assertIn('script', kept['kept'])

    def test_dry_run_writes_nothing(self):
        raw = self.prefab.read_text(encoding='utf-8')
        rec = F.run(self.root, dry_run=True)
        self.assertEqual(self.prefab.read_text(encoding='utf-8'), raw)
        self.assertTrue(rec['changed'])

    def test_max_value_from_the_values_file(self):
        p = copy.deepcopy(settings_prefab())
        p[5]['_N$string'] = p[5]['_string'] = '12'
        self.prefab.write_text(json.dumps(p), encoding='utf-8')
        (self.root / 'docs/english').mkdir(parents=True)
        (self.root / 'docs/english/label-values.json').write_text(json.dumps(
            {'labels': [{'path': '*/playLabel', 'max_value': 999999999999}]}), encoding='utf-8')
        rec = F.run(self.root)
        self.assertEqual(self.by(rec, 'changed', 'playLabel')['longest'], '999999999999')

    def test_overflow_none_is_not_frozen_to_its_auto_size_unless_a_room_is_given(self):
        # EsmesPulpPress HomeView gold "0": NONE, box = the width of "0". Freezing it would squeeze 99999 to nothing.
        p = copy.deepcopy(settings_prefab())
        p[5].update({'_N$string': '0', '_string': '0', '_N$overflow': 0})
        p[4]['_contentSize']['width'] = 16.7
        self.prefab.write_text(json.dumps(p), encoding='utf-8')
        rec = F.run(self.root)
        self.assertEqual(self.objs()[5]['_N$overflow'], 0)
        self.assertEqual(self.by(rec, 'grows', 'playLabel')['saved_box'], 16.7)
        (self.root / 'docs/english').mkdir(parents=True, exist_ok=True)
        (self.root / 'docs/english/label-values.json').write_text(json.dumps(
            {'labels': [{'path': '*/playLabel', 'max_value': 9999999, 'room': 100}]}), encoding='utf-8')
        rec = F.run(self.root)
        self.assertEqual(self.objs()[5]['_N$overflow'], 2)
        self.assertEqual(self.objs()[4]['_contentSize']['width'], 100)
        self.assertLessEqual(self.by(rec, 'changed', 'playLabel')['shrunk_width'], 100)

    def test_plain_number_without_max_value_is_noted(self):
        p = copy.deepcopy(settings_prefab())
        p[5]['_N$string'] = p[5]['_string'] = 'x5'
        self.prefab.write_text(json.dumps(p), encoding='utf-8')
        rec = F.run(self.root, dry_run=True)
        self.assertEqual(rec['notes'], [])
        self.assertEqual(F.longest_value('x5', 'a:b', [])[1], 'max_value_missing')

    # ------------------------------------------------------------------------------------------- fonts / engines
    def test_3x_prefab_label_keys(self):
        p = self.root / 'assets/ui/Home.prefab'
        p.write_text(json.dumps(prefab3x(), indent=2), encoding='utf-8')
        rec = F.run(self.root, files=[p])
        lab = self.objs(p)[4]
        self.assertEqual(lab['_overflow'], 2)
        ch = self.by(rec, 'changed', 'coinText')
        self.assertLessEqual(ch['shrunk_width'], 110 - 2 * 2)      # bold and the 2 px outline are counted

    def test_bmfont_and_unreadable_ttf(self):
        fnt = self.root / 'assets/font/num.fnt'
        fnt.parent.mkdir(parents=True)
        fnt.write_text('info face="n" size=50\ncommon lineHeight=50\n' +
                       '\n'.join('char id=%d xadvance=40' % (48 + i) for i in range(10)), encoding='utf-8')
        (self.root / 'assets/font/num.fnt.meta').write_text(json.dumps({'uuid': 'fnt-1'}), encoding='utf-8')
        ttf = self.root / 'assets/font/bad.ttf'
        ttf.write_bytes(b'not a font')
        (self.root / 'assets/font/bad.ttf.meta').write_text(json.dumps({'uuid': 'ttf-1'}), encoding='utf-8')
        fonts = F.Fonts(self.root)
        fn, method = fonts.width_fn('fnt-1')
        self.assertEqual(method, 'bmfont')
        self.assertAlmostEqual(fn('100', 25), 60.0)
        fn, method = fonts.width_fn('ttf-1')
        self.assertEqual(method, 'ttf-unreadable-table')
        self.assertGreater(fn('PLAY', 30), F.table_width('PLAY', 30))

    # -------------------------------------------------------------------------------------- what the audit says
    def test_audit_text_fit_reports_the_old_way_and_not_the_new_way(self):
        sys.path.insert(0, str(AUDIT_DIR))
        try:
            import audit_text_fit as T
        except ImportError:
            self.skipTest('remake-core/scripts/audit_text_fit.py not next to this pack')
        _, exact = T.measure(T.Project(self.root), {'font_kind': 'system'}, 'MUSIC 100%', 24)
        if not exact:
            self.skipTest('no Pillow / system font here: audit_text_fit.py cannot measure (the fit test above still ran)')

        def dump(lab):
            d = {'tool': 'ui_dump', 'schema': 1, 'screen': 'setting', 'kind': 'popup', 'canvas_css': [0, 0, 400, 800],
                 'viewport': {'width': 400, 'height': 800}, 'settle': True, 'nodes': [
                     {'path': 'Canvas/SettingPanel/musicLabel', 'name': 'musicLabel', 'order': 5, 'opacity': 1,
                      'rect': [140 / 400., 300 / 800., 120 / 400., 40 / 800.],
                      'comps': {'label': {'string': lab['_N$string'], 'fontSize': 24, 'actualFontSize': 24, 'width': 120,
                                          'height': 40, 'overflow': lab['_N$overflow'], 'wrap': lab['_enableWrapText'],
                                          'font': '', 'font_kind': 'system', 'color': [255, 255, 255], 'h_align': 1}}}]}
            out = self.root / ('dumps-%d' % lab['_N$overflow'])
            out.mkdir(exist_ok=True)
            (out / '001-ui-dump-setting.json').write_text(json.dumps(d), encoding='utf-8')
            return T.audit(self.root, [out])

        old = dump(self.objs()[3])
        self.assertIn('text_cut', {f['kind'] for f in old['findings']}, old['findings'])
        F.run(self.root)
        new = dump(self.objs()[3])
        self.assertNotIn('text_cut', {f['kind'] for f in new['findings']}, new['findings'])
        self.assertNotIn('text_outside_plate', {f['kind'] for f in new['findings']})


class CommandLine(unittest.TestCase):
    def test_exit_codes(self):
        root = Path(tempfile.mkdtemp(prefix='fitcli_'))
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__()
        try:
            self.assertEqual(F.main(['--project', str(root)]), 2)
            (root / 'assets').mkdir()
            (root / 'assets/a.prefab').write_text(json.dumps(settings_prefab()), encoding='utf-8')
            self.assertEqual(F.main(['--project', str(root)]), 1)          # desc + timer are on the to-fix list
            rec = json.loads((root / 'docs/english/fit-labels.json').read_text(encoding='utf-8'))
            self.assertEqual(rec['tool'], 'fit_english_labels')
        finally:
            quiet.__exit__(None, None, None)
            shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
