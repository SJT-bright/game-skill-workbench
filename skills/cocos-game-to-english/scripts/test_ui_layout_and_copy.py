#!/usr/bin/env python3
"""Self-tests: runtime UI dump -> layout (no hand-typed layout) and English copy quality.

Uses test_ui_dump_mock.js (a fake Cocos 2.x/3.x scene in Node) because no engine runs here; on a real game the
first dump of a page is checked by eye. Each check is calibrated: a known-bad case fails, a fixed case passes.
"""
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NODE = shutil.which('node')


def py(tool, *args):
    r = subprocess.run([sys.executable, '-B', str(HERE / tool), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def mock_dump(folder, api, scene):
    out = subprocess.run([NODE, str(HERE / 'test_ui_dump_mock.js'), str(api), scene], capture_output=True, text=True, check=True)
    f = Path(folder) / ('000-ui-dump-%s.json' % scene)
    f.write_text(out.stdout)
    return f


@unittest.skipUnless(NODE, 'node not installed')
class RuntimeLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='layout-test-'))
        self.dumps = self.tmp / 'dumps'
        self.dumps.mkdir()
        for scene in ('menu', 'play', 'pause'):
            mock_dump(self.dumps, 3, scene)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def extract(self, *extra):
        out = self.tmp / 'ui-layout.json'
        if out.exists():
            out.unlink()
        code, text = py('extract_ui_layout.py', self.dumps, '--out', out, *extra)
        return code, (json.loads(out.read_text()) if code == 0 else text)

    def test_dump_reads_same_positions_in_2x_and_3x(self):
        for scene in ('play', 'pause', 'menu'):
            d3 = json.loads(mock_dump(self.tmp, 3, scene).read_text())
            d2 = json.loads(mock_dump(self.tmp, 2, scene).read_text())
            self.assertEqual([n['rect'] for n in d3['nodes']], [n['rect'] for n in d2['nodes']])
            self.assertNotIn('Canvas/Hidden', [n['path'] for n in d3['nodes']])   # inactive node never read

    def test_dump_reports_graphic_card_surfaces_and_image_only_claim_button(self):
        for api in (2, 3):
            d = json.loads(mock_dump(self.tmp, api, 'checkin').read_text())
            cards = [n for n in d['nodes'] if n['name'] == 'CardSurface']
            self.assertEqual(len(cards), 7)
            self.assertTrue(all('graphics' in n['comps'] for n in cards))
            claim = next(n for n in d['nodes'] if n['name'] == 'btn_claim')
            self.assertIn('button', claim['comps'])
            self.assertEqual(claim['comps']['sprite']['frame'], 'btn_claim')
            self.assertFalse(any('label' in n['comps'] and n['comps']['label']['string'].lower() == 'claim'
                                 for n in d['nodes']))

    def test_enable_bold_and_is_bold_both_dumped(self):
        for api in (2, 3):
            dump = json.loads(mock_dump(self.tmp, api, 'bold_api').read_text())
            labels = {n['name']: n['comps']['label']['bold'] for n in dump['nodes'] if 'label' in n['comps']}
            self.assertTrue(labels['EnableBold'])
            self.assertTrue(labels['IsBold'])
            self.assertFalse(labels['Plain'])

    def test_old_enable_bold_omission_is_reproduced(self):
        probe = self.tmp / 'old-bold-probe'
        probe.mkdir()
        shutil.copy2(HERE / 'test_ui_dump_mock.js', probe / 'test_ui_dump_mock.js')
        source = (HERE / 'ui_dump.js').read_text()
        old = source.replace('lab.enableBold === true || lab.isBold === true', 'lab.isBold === true')
        self.assertNotEqual(old, source)
        (probe / 'ui_dump.js').write_text(old)
        raw = subprocess.run([NODE, str(probe / 'test_ui_dump_mock.js'), '2', 'bold_api'], capture_output=True, text=True, check=True)
        labels = {n['name']: n['comps']['label']['bold'] for n in json.loads(raw.stdout)['nodes'] if 'label' in n['comps']}
        self.assertFalse(labels['EnableBold'])
        self.assertTrue(labels['IsBold'])

    def test_layout_is_picked_from_the_game(self):
        code, layout = self.extract()
        self.assertEqual(code, 0, layout)
        s = {x['name']: x for x in layout['screens']}
        play = [e['name'] for e in s['play_9x19']['elements']]
        self.assertEqual(play, ['Canvas/TopBar', 'Canvas/BtnPause', 'Canvas/TipBubble'])   # board tiles skipped
        self.assertTrue(s['play_9x19']['elements'][2].get('temporary'))
        home = {b['name']: b for b in s['home_9x19']['buttons']}
        self.assertTrue(home['Canvas/BtnPlay'].get('primary'))
        self.assertEqual(home['Canvas/BtnShop']['label'], 'small')
        pause = s['pause_9x19']
        self.assertEqual(pause['safe'], [135.0, 512.0, 480.0, 620.0])                        # from 9-slice borders
        self.assertEqual([d['name'] for d in pause['decorations']], ['Canvas/PausePopup/Panel/CornerTL'])
        self.assertEqual(len(pause['contents']), 3)

    def test_result_kind_is_accepted_and_extracted_as_popup_geometry(self):
        f = self.dumps / '000-ui-dump-pause.json'
        d = json.loads(f.read_text())
        d['kind'] = 'result'
        f.write_text(json.dumps(d))
        code, layout = self.extract()
        self.assertEqual(code, 0, layout)
        result = next(s for s in layout['screens'] if s['name'] == 'pause_9x19')
        self.assertEqual(result['kind'], 'popup')
        self.assertGreater(len(result['contents']), 0)

    def test_popup_can_use_a_named_graphics_panel_surface(self):
        f = self.dumps / '000-ui-dump-pause.json'
        d = json.loads(f.read_text())
        panel = next(n for n in d['nodes'] if n['path'] == 'Canvas/PausePopup/Panel')
        panel['name'] = 'PanelSurface'
        panel['path'] = 'Canvas/PausePopup/PanelSurface'
        panel['comps'] = {'graphics': {'lineWidth': 7}}
        f.write_text(json.dumps(d))
        code, layout = self.extract()
        self.assertEqual(code, 0, layout)
        popup = next(s for s in layout['screens'] if s['name'] == 'pause_9x19')
        self.assertEqual(popup['kind'], 'popup')
        self.assertAlmostEqual(popup['panel'][2], 560.0, delta=2.0)

    def test_audit_measures_real_positions(self):
        code, layout = self.extract()
        code, out = py('audit_ui_coverage.py', self.tmp / 'ui-layout.json')
        self.assertEqual(code, 1)                      # the mock title really crosses the inner border
        self.assertIn('Title crosses the inner border', out)

    def test_hand_typed_or_edited_layout_rejected(self):
        self.extract()
        layout = json.loads((self.tmp / 'ui-layout.json').read_text())
        layout['screens'][1]['contents'][0]['rect'][1] = 530
        (self.tmp / 'edited.json').write_text(json.dumps(layout))
        self.assertEqual(py('audit_ui_coverage.py', self.tmp / 'edited.json')[0], 2)
        (self.tmp / 'manual.json').write_text(json.dumps({'screens': layout['screens']}))
        code, out = py('audit_ui_coverage.py', self.tmp / 'manual.json')
        self.assertEqual(code, 2)
        self.assertIn('hand-typed', out)

    def test_changed_dump_rejected(self):
        self.extract()
        f = self.dumps / '000-ui-dump-play.json'
        f.write_text(f.read_text().replace('"1,250"', '"9,999"'))
        self.assertEqual(py('audit_ui_coverage.py', self.tmp / 'ui-layout.json')[0], 2)

    def test_overrides_only_tag(self):
        bad = self.tmp / 'bad-overrides.json'
        bad.write_text(json.dumps({'tags': {'Canvas/BtnPlay': {'rect': [0, 0, 10, 10]}}}))
        self.assertEqual(self.extract('--overrides', bad)[0], 2)
        good = self.tmp / 'overrides.json'
        good.write_text(json.dumps({'tags': {'Canvas/BtnPlay': {'primary': False}, 'Canvas/TipBubble': {'role': 'ignore'}}}))
        code, layout = self.extract('--overrides', good)
        self.assertEqual(code, 0)
        s = {x['name']: x for x in layout['screens']}
        self.assertNotIn('primary', {b['name']: b for b in s['home_9x19']['buttons']}['Canvas/BtnPlay'])
        self.assertNotIn('Canvas/TipBubble', [e['name'] for e in s['play_9x19']['elements']])
        self.assertIn(py('audit_ui_coverage.py', self.tmp / 'ui-layout.json')[0], (0, 1))   # provenance with overrides accepted

    def test_failed_dump_stops_extraction(self):
        (self.dumps / '009-ui-dump-broken.json').write_text(json.dumps({'tool': 'ui_dump', 'error': 'no running scene yet'}))
        code, out = self.extract()
        self.assertEqual(code, 2)
        self.assertIn('do not type the layout by hand', out)


class CopyQualityTests(unittest.TestCase):
    def project(self, code_lines, table=None, glossary=None, dumps=()):
        root = Path(tempfile.mkdtemp(prefix='copy-test-'))
        (root / 'assets').mkdir()
        (root / 'assets' / 'Ui.ts').write_text('\n'.join('this.l%d.string = %s;' % (i, json.dumps(s)) for i, s in enumerate(code_lines)))
        if table is not None or glossary is not None:
            (root / 'docs/copy').mkdir(parents=True)
        if table is not None:
            (root / 'docs/copy/copy-table.csv').write_text('zh,en\n' + '\n'.join('%s,%s' % r for r in table) + '\n', encoding='utf-8')
        if glossary is not None:
            (root / 'docs/copy/glossary.json').write_text(json.dumps(glossary))
        for scene in dumps:
            (root / 'docs/test').mkdir(parents=True, exist_ok=True)
            mock_dump(root / 'docs/test', 3, scene)
        return root

    def run_audit(self, root, *extra):
        out = root / 'report.json'
        if out.exists():
            out.unlink()
        code, _ = py('audit_copy_quality.py', '--project', root, '--out', out, *extra)
        return code, json.loads(out.read_text()) if out.exists() else None

    def test_bad_copy_blocks(self):
        root = self.project(['Recieve', 'Tap the the tile', 'Not enough coins，watch an ad'], table=[('获得{0}金币', 'Got coins')])
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        self.assertEqual({c['kind'] for c in r['checks']}, {'spelling', 'repeated_word', 'fullwidth_punctuation', 'placeholder'})

    def test_clean_copy_passes_and_chinglish_is_only_listed(self):
        root = self.project(['Level Complete!', 'Not enough coins. Watch an ad?', 'Receive'],
                            table=[('获得{0}金币', 'Got {0} coins')])
        code, r = self.run_audit(root)
        self.assertEqual(code, 0, r['checks'])
        self.assertIn('chinglish', {x['kind'] for x in r['review']})

    def test_glossary_allows_names_and_bans_variants(self):
        root = self.project(['Monkeyzo Dash', 'Gold: 100'])
        self.assertEqual(self.run_audit(root)[0], 1)                       # unknown name is a spelling hit
        root = self.project(['Monkeyzo Dash', 'Gold: 100'], glossary={'allow': ['Monkeyzo'], 'terms': {'Coins': ['Gold']}})
        code, r = self.run_audit(root)
        self.assertEqual([c['kind'] for c in r['checks']], ['glossary'])

    def test_mixed_names_are_listed(self):
        root = self.project(['Energy is full', 'Stamina +5', 'Claim', 'Collect'])
        kinds = [x['message'] for x in self.run_audit(root)[1]['review'] if x['kind'] == 'terminology']
        self.assertEqual(len(kinds), 2)

    @unittest.skipUnless(NODE, 'node not installed')
    def test_runtime_text_that_does_not_fit_blocks(self):
        root = self.project(['PLAY'], dumps=['copy'])
        code, r = self.run_audit(root, '--require-runtime', '--sheet', root / 'sheet.md')
        self.assertEqual(code, 1)
        self.assertEqual([c['kind'] for c in r['checks']], ['overflow'])
        kinds = {x['kind'] for x in r['review']}
        self.assertTrue({'maybe_cut', 'button_case'} <= kinds, kinds)
        self.assertIn('Claim Reward Now', (root / 'sheet.md').read_text())

    def test_no_runtime_text_blocks_when_required(self):
        root = self.project(['PLAY'])
        code, r = self.run_audit(root, '--require-runtime')
        self.assertEqual((code, r['checks'][0]['kind']), (1, 'no_runtime_text'))


@unittest.skipUnless(NODE, 'node not installed')
class PageRichnessTests(unittest.TestCase):
    """User 2026-10-21 negative examples must fail; full pages must pass."""
    @staticmethod
    def screenshot(path, flat, dump=None, busy=False):
        """Stand-in for the screenshot chrome_touch takes with each dump: a flat light-blue page (the user's
        2026-10-21 screenshots) or a simple sky picture (gradient, clouds, hills)."""
        from PIL import Image, ImageDraw
        im = Image.new('RGB', (375, 812), (146, 214, 250))
        d = ImageDraw.Draw(im)
        if not flat:
            for y in range(812):
                d.line([(0, y), (375, y)], fill=(120 + y // 8, 190 + y // 20, 250 - y // 10))
            for x, y in ((60, 120), (250, 200), (150, 330), (300, 460)):
                d.ellipse([x - 50, y - 22, x + 50, y + 22], fill=(255, 255, 255))
            d.ellipse([-80, 640, 260, 900], fill=(110, 190, 100))
            d.ellipse([160, 680, 480, 940], fill=(90, 170, 90))
        for y in range(520, 571):                                   # a glossy button plate (gradient, not flat)
            d.line([(110, y), (265, y)], fill=(250, 110 + (y - 520) * 2, 60))
        if not flat:
            import random
            rnd = random.Random(7)                                  # painted texture: nothing in a real picture is one flat colour
            px = im.load()
            for yy in range(0, 812):
                for xx in range(0, 375):
                    c = px[xx, yy]; n = rnd.randint(-14, 14)
                    px[xx, yy] = (max(0, min(255, c[0] + n)), max(0, min(255, c[1] + n)), max(0, min(255, c[2] - n)))
        if busy:          # user 2026-10-23 (Metro Switch home): a painted plaza full of small high-contrast things
            import random
            rnd = random.Random(11)
            for _ in range(2600):
                x, y, r = rnd.randint(0, 375), rnd.randint(0, 812), rnd.randint(2, 6)
                d.rectangle([x - r, y - r, x + r, y + r], fill=rnd.choice([(20, 30, 60), (250, 250, 240), (200, 40, 40), (30, 120, 60)]))
        if dump:          # the picture words / bitmap digits themselves: light fills, a different colour per text item
            palette = [(255, 214, 70), (255, 150, 190), (130, 220, 255), (170, 240, 120), (255, 170, 80), (210, 170, 255)]
            for n in dump.get('nodes', []):
                frame = str(n['comps'].get('sprite', {}).get('frame', ''))
                if not (n['comps'].get('label') or frame.startswith('txt_')) or n.get('opacity', 1) <= 0.05:
                    continue
                r = n.get('screen') or n['rect']
                col = palette[sum(map(ord, n['name'])) % len(palette)]
                x0, x1 = 375 * (r[0] + r[2] * 0.15), 375 * (r[0] + r[2] * 0.85)
                y0, y1 = 812 * (r[1] + r[3] * 0.25), 812 * (r[1] + r[3] * 0.75)
                for k, y in enumerate(range(int(y0), int(y1))):
                    d.line([(x0, y), (x1, y)], fill=col if k % 3 else tuple(max(0, c - 40) for c in col))
                # The good fixture represents game-style outlined picture text.
                # Keep its outline in the rendered pixels so the contrast check
                # evaluates the fill/outline/background relationship.
                d.rectangle([int(x0), int(y0), int(x1), int(y1)], outline=(58, 42, 35), width=2)
        im.save(path)

    def project(self, scenes, league_add=False, flat=()):
        root = Path(tempfile.mkdtemp(prefix='rich-test-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets').mkdir()
        (root / 'docs/test').mkdir(parents=True)
        for i, (scene, purpose) in enumerate(scenes):
            f = mock_dump(root / 'docs/test', 3, scene)
            d = json.loads(f.read_text())
            d['purpose'] = purpose
            d['screen'] = '%s_%d' % (scene, i)
            f.unlink()
            name = '%03d-ui-dump-%s-%d.json' % (i, scene, i)
            d['screenshot'] = name.replace('-ui-dump-', '-ui-').replace('.json', '.png')
            (root / 'docs/test' / name).write_text(json.dumps(d))
            self.screenshot(root / 'docs/test' / d['screenshot'], flat=scene in flat or purpose in flat, dump=d)
        (root / 'docs/art').mkdir(parents=True, exist_ok=True)       # user 2026-10-22: one button set in the game style
        (root / 'docs/art/button-set.json').write_text(json.dumps({'style': 'glossy candy capsules with a gold rim',
                                                                  'frames': ['btn_*', 'icon_*', 'node*']}))
        (root / 'docs/art/screens.json').write_text(json.dumps({'runtime_verified': True, 'screens': [      # user 2026-10-24: actual state IDs and captures
            {'id': '%s_%d' % (sc, i), 'name': '%s_%d' % (sc, i), 'purpose': pu, 'open': 'test fixture'} for i, (sc, pu) in enumerate(scenes)]}))
        (root / 'docs/text').mkdir(parents=True, exist_ok=True)
        (root / 'docs/text/runtime-text.json').write_text(json.dumps({'labels': [
            {'path': 'Canvas/Panel/Row*/Name', 'why': 'league rival names are generated at run time'}]}))
        if any(purpose == 'checkin' for _, purpose in scenes):
            (root / 'docs/features.json').write_text(json.dumps({'daily_checkin': True}))
        if league_add:
            (root / 'docs/league').mkdir(parents=True)
            (root / 'docs/league/decision.json').write_text(json.dumps({'decision': 'add'}))
        return root

    def run_audit(self, root):
        out = root / 'rich.json'
        code, text = py('audit_page_richness.py', '--project', root, '--out', out)
        return code, json.loads(out.read_text())

    def problems(self, report, purpose):
        return ' '.join(p for row in report['pages'] if row['purpose'] == purpose for p in row['problems'])

    def test_negative_examples_fail(self):
        code, r = self.run_audit(self.project([('bad_home', 'home'), ('bad_result', 'result_win'),
                                               ('bad_result', 'result_fail'), ('empty_league', 'league')], league_add=True))
        self.assertEqual(code, 1)
        home = self.problems(r, 'home')
        self.assertIn('bare_button', home)
        self.assertIn('system_font', home)
        win = self.problems(r, 'result_win')
        for kind in ('monotonous', 'result_page', 'result_double'):
            self.assertIn(kind, win)
        self.assertIn('empty_panel', self.problems(r, 'league'))

    FULL = [('good_home', 'home'), ('good_result', 'result_win'), ('good_result', 'result_fail'),
            ('settings', 'settings'), ('settings_sound', 'settings_sound'), ('play', 'other')]

    def test_missing_backdrop_is_rejected(self):
        root = self.project(self.FULL)
        for file in (root/'docs/test').glob('*-ui-dump-*.json'):
            dump=json.loads(file.read_text())
            dump['nodes']=[n for n in dump['nodes'] if not any(w in (n.get('name','')+' '+str(n.get('comps',{}).get('sprite',{}).get('frame',''))).lower() for w in ('background','backdrop'))]
            file.write_text(json.dumps(dump))
        code, report = self.run_audit(root)
        self.assertEqual(code,1)
        self.assertIn('plain_backdrop',self.problems(report,'home'))

    def test_full_pages_pass(self):
        code, r = self.run_audit(self.project(self.FULL, league_add=False))
        self.assertEqual(code, 0, json.dumps([p for p in r['pages'] if p['problems']], indent=1))
        self.assertEqual(r['checked'], 6)                       # gameplay is measured too (background only)

    def test_flat_background_fails_even_when_the_scene_looks_full(self):
        # user 2026-10-21: light-blue result page and light-blue gameplay sky with nothing on them
        code, r = self.run_audit(self.project(self.FULL, league_add=False, flat=('good_result', 'play')))
        self.assertEqual(code, 1)
        flat = [p['purpose'] for p in r['pages'] if any(x.startswith('flat_background') for x in p['problems'])]
        self.assertEqual(sorted(flat), ['other', 'result_fail', 'result_win'])

    def test_buttons_over_40_percent_and_small_title_fail(self):
        # user 2026-10-21: the home page needs a big title and cover art; function buttons <= 40% of the screen (2026-10-23)
        scenes = [('button_home', 'home')] + self.FULL[1:]
        code, r = self.run_audit(self.project(scenes, league_add=True))
        self.assertEqual(code, 1)
        home = self.problems(r, 'home')
        self.assertIn('buttons_too_big', home)
        self.assertIn('big title', home)
        self.assertIn('cover art', home)
        good = next(p for p in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] if p['purpose'] == 'home')
        self.assertLess(good['stats']['button_share'], 0.40)

    def test_round_two_mistakes_fail(self):
        # user 2026-10-21, second art round: level select with 3 blank cards, a blue placeholder square, a home page
        # with dark thick PLAY text, four text buttons, text sticking out of its plate and a big empty middle
        scenes = [('round2_home', 'home'), ('round2_map', 'map')] + self.FULL[1:]
        root = self.project(scenes, league_add=True)
        from PIL import Image, ImageDraw
        shot = next((root / 'docs/test').glob('*-ui-round2_map-*.png'))
        im = Image.open(shot).convert('RGB'); ImageDraw.Draw(im).rectangle([120, 300, 255, 420], fill=(78, 134, 220)); im.save(shot)
        # A flat sky patch alone is valid art. Model the actual independent placeholder
        # surface corresponding to these blue pixels, as the production audit now requires.
        dump_file = next((root / 'docs/test').glob('*-ui-dump-round2_map-*.json'))
        dump = json.loads(dump_file.read_text())
        dump['nodes'].append({'name': 'BluePlaceholder', 'path': 'Canvas/BluePlaceholder',
            'rect': [120 / 375, 300 / 812, 135 / 375, 120 / 812], 'opacity': 1,
            'comps': {'sprite': {'frame': 'flat_blue_placeholder'}}})
        dump_file.write_text(json.dumps(dump))
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        home, level = self.problems(r, 'home'), self.problems(r, 'map')
        for kind in ('dark_text', 'text_buttons', 'text_outside', 'empty_area'):
            self.assertIn(kind, home)
        for kind in ('blank_card', 'map_page', 'solid_block', 'placeholder'):
            self.assertIn(kind, level)

    def test_plain_popup_needs_an_illustration(self):
        # user 2026-10-23: flat pale "Home screen reward" panel with text and three buttons only
        code, r = self.run_audit(self.project(self.FULL + [('plain_popup', 'reward')], league_add=True))
        self.assertEqual(code, 1)
        self.assertIn('plain_popup', self.problems(r, 'reward'))
        code, r = self.run_audit(self.project(self.FULL + [('reward_popup', 'reward')], league_add=True))
        self.assertNotIn('plain_popup', self.problems(r, 'reward'))
        self.assertNotIn('plain_popup', self.problems(r, 'result_win'))

    def test_checkin_popup_needs_seven_cards_and_a_big_day7(self):
        code, r = self.run_audit(self.project(self.FULL + [('checkin', 'checkin')], league_add=False))
        self.assertEqual(code, 0, json.dumps([p for p in r['pages'] if p['problems']], indent=1))
        code, r = self.run_audit(self.project(self.FULL + [('checkin_small7', 'checkin')], league_add=False))
        self.assertIn('day-7 card must be the big one', self.problems(r, 'checkin'))

    def test_calm_and_busy_backgrounds_are_measured_without_numpy(self):
        import audit_page_richness as apr
        from PIL import Image, ImageDraw
        root = Path(tempfile.mkdtemp(prefix='background-density-')); self.addCleanup(shutil.rmtree, root, True)
        shot = root / 'background.png'
        dump = {'_file': str(root / 'dump.json'), 'screenshot': shot.name}
        calm = Image.new('RGB', (188, 376))
        draw = ImageDraw.Draw(calm)
        for y in range(376):
            draw.line((0, y, 187, y), fill=(100 + y // 8, 195 + y // 16, 230))
        draw.ellipse((0, 245, 75, 330), fill=(130, 205, 150))
        calm.save(shot)
        problems, share = apr.busy_background(dump, [])
        self.assertEqual(problems, [])
        self.assertIsNotNone(share)
        self.assertLess(share, apr.MAX_BUSY)
        noisy = Image.new('RGB', (188, 376)); draw = ImageDraw.Draw(noisy)
        for y in range(0, 376, 2):
            for x in range(0, 188, 2):
                value = 245 if (x // 2 + y // 2) % 2 else 25
                draw.rectangle((x, y, x + 1, y + 1), fill=(value, value, value))
        noisy.save(shot)
        problems, share = apr.busy_background(dump, [])
        self.assertTrue(any(p.startswith('busy_background:') for p in problems), problems)
        self.assertGreater(share, apr.MAX_BUSY)

    def test_plain_low_contrast_text_fails(self):
        # user 2026-10-22: thin system-font words on generated art; white RETRY on a cream panel
        root = self.project(self.FULL + [('plain_text_result', 'other')], league_add=True)
        from PIL import Image
        shot = next((root / 'docs/test').glob('*-ui-plain_text_result-*.png'))
        Image.new('RGB', (375, 812), (244, 238, 222)).save(shot)                     # cream panel behind the text
        code, r = self.run_audit(root)
        plain = self.problems(r, 'other')
        self.assertIn('low_contrast: "RETRY"', plain)
        self.assertNotIn('low_contrast: "NEW BEST!"', plain)                           # dark text on cream is readable,
        self.assertTrue(any(k + ': "NEW BEST!"' in plain for k in ('dark_green_text', 'dark_bold_text')))  # but banned
        self.assertIn('plain_text: "RETRY"', plain)
        self.assertIn('font_text: "NEW BEST!"', plain)
        self.assertIn('system_font', plain)

    def test_semantic_picture_text_frame_is_measured_for_contrast(self):
        # A fixed title can be a Sprite after its Label is disabled; the txt_ frame name keeps it in the text audit.
        import audit_page_richness as apr
        from PIL import Image, ImageDraw
        root = Path(tempfile.mkdtemp(prefix='picture-text-')); self.addCleanup(shutil.rmtree, root, True)
        shot = root / 'capture-ui-daily.png'
        image = Image.new('RGB', (375, 812), (250, 245, 232))
        ImageDraw.Draw(image).rectangle([80, 244, 295, 341], fill=(244, 238, 220))
        image.save(shot)
        rect = [80 / 375, 244 / 812, 216 / 375, 98 / 812]
        title = {'path': 'Canvas/Panel/daily_rewards/GeneratedArt', 'name': 'GeneratedArt', 'rect': rect,
                 'screen': rect, 'opacity': 1, 'comps': {'sprite': {'frame': 'txt_daily_rewards'}}}
        dump = {'_file': str(root / 'manual-ui-dump-daily.json'), 'screenshot': shot.name,
                'canvas_css': [0, 0, 375, 812]}
        problems = ' '.join(apr.text_problems(dump, [title], [], Image))
        self.assertIn('low_contrast: picture text "daily rewards"', problems)

    def test_countdown_caption_and_utility_button_do_not_create_false_positives(self):
        # A timer hint below an action and a Close/Claim pair have different roles from feature captions.
        import audit_page_richness as apr
        close = {'path': 'Canvas/Panel/btn_close', 'name': 'btn_close', 'rect': [0.43, 0.8, 0.14, 0.04],
                 'comps': {'button': {'interactable': True}, 'sprite': {'frame': 'btn_close'}}}
        claim = {'path': 'Canvas/Panel/btn_claim', 'name': 'btn_claim', 'rect': [0.3, 0.55, 0.4, 0.07],
                 'comps': {'button': {'interactable': True}, 'sprite': {'frame': 'btn_claim'}}}
        hint = {'path': 'Canvas/Panel/NextReward/GeneratedArt', 'name': 'GeneratedArt', 'rect': [0.27, 0.64, 0.23, 0.04],
                'comps': {'sprite': {'frame': 'txt_next_reward'}}}
        timer = {'path': 'Canvas/Panel/Countdown', 'name': 'Countdown', 'rect': [0.55, 0.64, 0.22, 0.04],
                 'comps': {'label': {'string': '00:00:00'}}}
        nodes = [close, claim, hint, timer]
        self.assertFalse(any('action_caption' in p for p in apr.overlap_problems(nodes, [close, claim], [])))
        self.assertEqual(apr.caption_style_problems({}, nodes, [close, claim], None), [])

        next_level = {'path': 'Canvas/Panel/NextLevel/GeneratedArt', 'name': 'GeneratedArt', 'rect': [0.38, 0.63, 0.24, 0.04],
                      'comps': {'sprite': {'frame': 'txt_next_level'}}}
        nodes = [claim, next_level]
        self.assertTrue(any('action_caption' in p for p in apr.overlap_problems(nodes, [claim], [])),
                        'a real "Next Level" action caption must still be caught')

    def test_countdown_outside_capsule_is_a_sibling_and_keeps_clearance(self):
        # A timer visually below an energy capsule must not remain a capsule descendant or intersect its rim.
        import audit_page_richness as apr
        capsule = {'path': 'Canvas/header_power', 'name': 'header_power', 'rect': [0.1, 0.1, 0.3, 0.1],
                   'comps': {'sprite': {'frame': 'energy_capsule'}}}
        amount = {'path': 'Canvas/header_power/num', 'name': 'num', 'rect': [0.15, 0.12, 0.12, 0.04],
                  'comps': {'label': {'string': '9/10'}}}
        timer_inside = {'path': 'Canvas/header_power/timer', 'name': 'timer', 'rect': [0.17, 0.185, 0.16, 0.04],
                        'comps': {'label': {'string': '01:44'}}}
        problems = apr.overlap_problems([capsule, amount, timer_inside], [], [])
        self.assertTrue(any('text_outside' in problem and '01:44' in problem for problem in problems), problems)

        timer_below = {'path': 'Canvas/energy_timer', 'name': 'energy_timer', 'rect': [0.17, 0.212, 0.16, 0.04],
                       'comps': {'label': {'string': '01:44'}}}
        problems = apr.overlap_problems([capsule, amount, timer_below], [], [])
        self.assertFalse(any('text_outside' in problem or 'overlap_text' in problem for problem in problems), problems)

    def test_bitmap_font_low_contrast_is_measured_from_rendered_pixels(self):
        # User 2026-10-24: Label.color is white for BMFont even when the glyph atlas blends into the card.
        from PIL import Image, ImageDraw
        from audit_page_richness import picture_text_contrast
        image = Image.new('RGB', (120, 80), (255, 246, 222))
        draw = ImageDraw.Draw(image)
        draw.rectangle([42, 24, 77, 56], fill=(244, 226, 191))
        self.assertIsNotNone(picture_text_contrast(image, [0.33, 0.25, 0.34, 0.5], 3.0))
        draw.rectangle([40, 22, 79, 58], outline=(74, 49, 31), width=4)
        self.assertIsNone(picture_text_contrast(image, [0.33, 0.25, 0.34, 0.5], 3.0))

    def test_bitmap_font_uses_the_surface_directly_behind_a_glyph(self):
        # Nearby card background must not replace the darker number well as the contrast reference.
        from PIL import Image, ImageDraw
        from audit_page_richness import picture_text_contrast
        image = Image.new('RGB', (120, 80), (254, 246, 224))
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 30, 119, 50], fill=(57, 123, 94))
        draw.line([(58, 34), (58, 46)], fill=(104, 67, 35), width=6)
        draw.line([(58, 34), (58, 46)], fill=(249, 241, 216), width=2)
        self.assertIsNone(picture_text_contrast(image, [0.25, 0.375, 0.5, 0.25], 4.5))

    def test_hidden_value_surface_covered_by_panel_is_rejected(self):
        from PIL import Image
        from audit_page_richness import check, hidden_value_surface_problems, text_surface
        panel = {'name': 'PanelSurface', 'path': 'Canvas/Panel/PanelSurface', 'order': 2, 'depth': 3,
                 'rect': [0, 0, 1, 1], 'comps': {'graphics': {'lineWidth': 7}}}
        well = {'name': 'CountdownWell', 'path': 'Canvas/Panel/CountdownWell', 'order': 1, 'depth': 3,
                'rect': [0.55, 0.6, 0.3, 0.1], 'comps': {'graphics': {'lineWidth': 2}}}
        label = {'name': 'NextClaim', 'path': 'Canvas/Panel/NextClaim', 'order': 3, 'depth': 3,
                 'rect': [0.57, 0.62, 0.26, 0.05], 'comps': {'label': {'string': '00:00:00'}}}
        broken = [well, panel, label]
        self.assertTrue(any('hidden_surface:' in item for item in hidden_value_surface_problems(broken)))
        self.assertEqual(text_surface(label, broken), panel['rect'])

        visible = [dict(panel, order=0), dict(well, order=1), dict(label, order=2)]
        self.assertEqual(hidden_value_surface_problems(visible), [])
        self.assertEqual(text_surface(visible[-1], visible), well['rect'])

        d = {'kind': 'popup', 'purpose': 'checkin', 'page': {'width': 375, 'height': 812},
             'nodes': broken, '_file': '/tmp/hidden-value-surface-probe.json'}
        problems, _ = check(d, Image)
        self.assertTrue(any(item.startswith('hidden_surface:') for item in problems), problems)

    def test_flat_button_measures_rendered_plate_not_wide_hitbox(self):
        from PIL import Image, ImageDraw
        from audit_page_richness import flat_button_problems
        button = {'name': 'btn_claim', 'path': 'Canvas/Panel/btn_claim', 'rect': [0.1, 0.1, 0.8, 0.3],
                  'screen': [0.1, 0.1, 0.8, 0.3], 'comps': {'button': {'interactable': True}}}
        plate = {'name': 'GeneratedArt', 'path': 'Canvas/Panel/btn_claim/GeneratedArt', 'rect': [0.365, 0.1, 0.27, 0.3],
                 'screen': [0.365, 0.1, 0.27, 0.3], 'comps': {'sprite': {'frame': 'btn_claim'}}}
        image = Image.new('RGB', (200, 100), (245, 240, 224))
        draw = ImageDraw.Draw(image)
        for y in range(10, 40):
            draw.line((73, y, 127, y), fill=(245, 90 + y * 3, 20))
        self.assertEqual(flat_button_problems([button], [button, plate], image), [])  # the hit area is mostly panel colour
        draw.rectangle((73, 10, 127, 39), fill=(210, 120, 18))
        self.assertTrue(any('flat_button:' in item for item in flat_button_problems([button], [button, plate], image)))

    def test_panel_whitespace_is_not_a_placeholder_but_a_matching_surface_is(self):
        from audit_page_richness import panel_fill_block
        panel = {'name': 'PanelSurface', 'path': 'Canvas/Panel/PanelSurface', 'rect': [0.07, 0.2, 0.86, 0.6],
                 'comps': {'graphics': {'lineWidth': 7}}}
        block = [0.1, 0.6, 0.35, 0.11]
        backdrop = {'name': 'BG', 'path': 'Canvas/BG', 'rect': [0, 0, 1, 1], 'comps': {'sprite': {'frame': 'bg'}}}
        self.assertTrue(panel_fill_block(block, [panel, backdrop]))
        placeholder = {'name': 'Placeholder', 'path': 'Canvas/Panel/Placeholder', 'rect': block,
                       'comps': {'graphics': {'lineWidth': 0}}}
        self.assertFalse(panel_fill_block(block, [panel, backdrop, placeholder]))

    def test_checkin_requires_visible_content_inside_each_day_card(self):
        from audit_page_richness import check
        with tempfile.TemporaryDirectory(prefix='checkin-inner-content-') as tmp:
            f = mock_dump(tmp, 3, 'checkin')
            d = json.loads(f.read_text())
            d['_file'] = str(f)
            d['kind'], d['purpose'] = 'popup', 'checkin'
            d['nodes'] = [n for n in d['nodes'] if not n['path'].startswith('Canvas/Panel/Day3/Icon') and
                          not n['path'].startswith('Canvas/Panel/Day3/Amount')]
            problems, _ = check(d)
            self.assertTrue(any('day 3 card has no visible reward content' in item for item in problems), problems)

    def test_light_bitmap_digits_on_dark_well_are_not_mistaken_for_dark_text(self):
        # User 2026-10-24: sample the dark-green value well, not the cream card around it.
        from PIL import Image, ImageDraw
        from audit_page_richness import picture_text_dark
        image = Image.new('RGB', (120, 80), (250, 240, 218))
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 20, 90, 60), fill=(18, 94, 64))
        draw.line((60, 27, 60, 53), fill=(93, 56, 36), width=7)
        draw.line((60, 27, 60, 53), fill=(255, 216, 116), width=3)
        text = [40 / 120, 21 / 80, 40 / 120, 38 / 80]
        surface = [0.25, 0.25, 0.5, 0.5]
        self.assertTrue(picture_text_dark(image, text))       # old outer-card sample falsely counted the dark well as glyphs
        self.assertEqual(picture_text_dark(image, text, surface), '')
        draw.rectangle((30, 20, 90, 60), fill=(18, 94, 64))
        draw.line((60, 27, 60, 53), fill=(25, 25, 25), width=7)
        self.assertTrue(picture_text_dark(image, text, surface))

    def test_translucent_fullscreen_modal_keeps_its_underlay_backdrop(self):
        from audit_page_richness import check
        d = {'kind': 'popup', 'purpose': 'checkin', 'page': {'width': 375, 'height': 812}, 'nodes': [
            {'path': 'Canvas/BG', 'name': 'BG', 'order': 0, 'depth': 1, 'rect': [0, 0, 1, 1], 'comps': {'sprite': {'frame': 'bg_main'}}},
            {'path': 'Canvas/QueueDialog', 'name': 'QueueDialog', 'order': 1, 'depth': 1, 'rect': [-0.2, -0.1, 1.4, 1.2], 'comps': {'block_input': True}},
            {'path': 'Canvas/QueueDialog/Backdrop', 'name': 'Backdrop', 'order': 2, 'depth': 2, 'rect': [-0.2, -0.1, 1.4, 1.2], 'comps': {'graphics': {'lineWidth': 2}}},
            {'path': 'Canvas/QueueDialog/Panel/PanelArt', 'name': 'PanelArt', 'order': 3, 'depth': 3, 'rect': [0.1, 0.1, 0.8, 0.8], 'comps': {'sprite': {'frame': 'panel_tall', 'sliced': True}}},
        ]}
        d['_file'] = '/tmp/checkin-modal-probe.json'
        problems, _ = check(d)
        self.assertFalse(any(p.startswith('plain_backdrop:') for p in problems), problems)
        self.assertFalse(any(p.startswith('empty_panel:') for p in problems), problems)

    def test_bitmap_font_samples_the_enclosing_surface_not_the_outer_backdrop(self):
        # A low-contrast glyph nearly fills its local plate; the unrelated dark scene behind that plate must not make it pass.
        from PIL import Image, ImageDraw
        from audit_page_richness import picture_text_contrast, text_surface
        image = Image.new('RGB', (160, 90), (18, 48, 38))
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 20, 130, 70), fill=(238, 226, 198))
        draw.line((60, 35, 60, 58), fill=(222, 207, 173), width=8)
        label = {'name': 'Amount', 'path': 'Canvas/Dialog/Well/Amount', 'order': 3,
                 'rect': [0.2, 25 / 90, 0.6, 40 / 90], 'comps': {'label': {'string': '1'}}}
        surface = {'name': 'Surface', 'path': 'Canvas/Dialog/Well/Surface', 'order': 2,
                   'rect': [30 / 160, 20 / 90, 100 / 160, 50 / 90], 'comps': {'graphics': {'lineWidth': 2}}}
        backdrop = {'name': 'Backdrop', 'path': 'Canvas/Backdrop', 'order': 1,
                    'rect': [0, 0, 1, 1], 'comps': {'sprite': {'frame': 'background'}}}
        # The outer-ring-only measurement passes against the dark backdrop; the local surface measurement catches the real defect.
        self.assertIsNone(picture_text_contrast(image, label['rect'], 4.5))
        self.assertEqual(text_surface(label, [backdrop, surface, label]), surface['rect'])
        self.assertIsNotNone(picture_text_contrast(image, label['rect'], 4.5, text_surface(label, [backdrop, surface, label])))

    def test_modal_occlusion_requires_a_full_screen_input_blocker(self):
        from audit_page_richness import fully_occluded, modal_masks
        underlay = {'name': 'OldButton', 'order': 4, 'rect': [0.35, 0.4, 0.3, 0.2], 'comps': {'button': {}}}
        blocker = {'name': 'Dialog', 'order': 6, 'rect': [-0.1, -0.1, 1.2, 1.2], 'comps': {'block_input': True}}
        shade_only = {'name': 'Shade', 'order': 5, 'rect': [0, 0, 1, 1], 'opacity': 0.5, 'comps': {}}
        masks = modal_masks([underlay, shade_only, blocker])
        self.assertEqual(masks, [blocker])
        self.assertTrue(fully_occluded(underlay, masks))
        partly_visible = dict(underlay, rect=[-0.2, 0.4, 0.3, 0.2])
        self.assertTrue(fully_occluded(partly_visible, masks))  # every actually visible pixel is covered
        partial_mask = dict(blocker, rect=[0.5,0,0.5,1])
        self.assertFalse(fully_occluded(underlay, [partial_mask]))

    def test_font_text_dark_teal_and_typed_arrows_fail(self):
        # user 2026-10-22: Collection page with "COINS 47 PEARLS 17" / "Price · 250 coins" in a dark-teal font and
        # "<" ">" typed on flat rounded boxes; every fixed word must be picture text, every button from one set
        root = self.project(self.FULL + [('teal_shop', 'skins')], league_add=True)
        from PIL import Image, ImageDraw
        dump = next((root / 'docs/test').glob('*-ui-dump-teal_shop-*.json'))
        shot = next((root / 'docs/test').glob('*-ui-teal_shop-*.png'))
        im = Image.open(shot).convert('RGB'); draw = ImageDraw.Draw(im)
        for n in json.loads(dump.read_text())['nodes']:
            if n['name'] in ('BtnPrev', 'BtnNext'):
                r = n['rect']
                draw.rounded_rectangle([r[0] * 375, r[1] * 812, (r[0] + r[2]) * 375, (r[1] + r[3]) * 812], 12, fill=(122, 184, 180))
        im.save(shot)
        code, r = self.run_audit(root)
        bad = self.problems(r, 'skins')
        for kind in ('font_text: "COINS 47', 'font_text: "Price', 'font_text: "Buttercup Mini"', 'dark_green_text', 'text_arrow',
                     'flat_button: Canvas/BtnPrev', 'off_style_button: Canvas/BtnNext'):
            self.assertIn(kind, bad)
        self.assertNotIn('Canvas/Panel/BtnUnlock', bad)              # the picture-text Unlock button in the set is fine
        self.assertNotIn('SunnyFox', ' '.join(p for row in r['pages'] for p in row['problems']))   # declared run-time names
        (root / 'docs/art/button-set.json').unlink()
        self.assertIn('button_set', json.dumps(self.run_audit(root)[1], ensure_ascii=False))

    def test_all_text_is_one_piece_generated_picture_text(self):
        # user 2026-10-23 (both boards, strongly emphasised): the "Scissors Master" home - typed title and subtitle, PLAY typed
        # on a flat plate, LEVELS/SKINS/Add to Home/Revisit words laid on tiles, coin "0" and level "0/9" in a font
        code, r = self.run_audit(self.project([('typed_home', 'home')] + self.FULL[1:], league_add=True))
        self.assertEqual(code, 1)
        home = self.problems(r, 'home')
        for kind in ('typed_title: "Scissors Master"', 'typed_title: "Cut the paper', 'spliced_button: Canvas/BtnPlay lays the word "PLAY"',
                     'spliced_button: Canvas/BtnLevels', 'spliced_button: Canvas/BtnShortcut', 'font_number: "0"', 'font_number: "0/9"'):
            self.assertIn(kind, home)
        # the good pages: buttons are btn_<words> pictures, numbers use generated bitmap digits, the title is a logo picture
        good = ' '.join(p for row in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] for p in row['problems'])
        for kind in ('spliced_button', 'font_number', 'typed_title'):
            self.assertNotIn(kind, good)

    def test_squashed_words_and_canvas_text_fail(self):
        # user 2026-10-23: words.png cells 570x345 forced into 234x49 buttons (DETAILS 2.89x, SKINS 1.80x) with
        # SizeMode.CUSTOM, and a RasterText.ts drawing the dynamic words with Canvas fonts
        root = self.project([('squashed', 'skins')] + self.FULL, league_add=True)
        (root / 'assets/scripts').mkdir(parents=True)
        (root / 'assets/scripts/RasterText.ts').write_text('export function draw(ctx, s) {\n  ctx.font = "bold 40px Arial";\n'
                                                            '  ctx.fillText(s, 0, 0);\n}\n')
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        bad = self.problems(r, 'skins')
        for kind in ('squashed_text: Canvas/BtnDetails/Word (frame "words") is a word picture 570x345 drawn at 468x98 - squashed flat 2.89x',
                     'squashed_text: Canvas/SkinsTitle', 'squashed_picture: Canvas/Mascot', 'canvas_text: Canvas/CoinsRaster',
                     'spliced_button: Canvas/BtnDetails lays the word "words"'):
            self.assertIn(kind, bad)
        for fine in ('Canvas/MapTitle', 'Canvas/ProgressFill'):            # uniform scale; a bar may stretch
            self.assertNotIn(fine, bad)
        self.assertIn('canvas_font_code: assets/scripts/RasterText.ts', ' '.join(r['setup']))
        (root / 'docs/text/runtime-text.json').write_text(json.dumps({'labels': [], 'canvas_text_files': [
            {'file': 'assets/scripts/RasterText.ts', 'why': 'player nickname typed at run time'}]}))
        self.assertNotIn('canvas_font_code', ' '.join(self.run_audit(root)[1]['setup']))
        good = ' '.join(p for row in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] for p in row['problems'])
        for kind in ('squashed_', 'canvas_text', 'uniform_text_colour'):
            self.assertNotIn(kind, good)

    def test_low_res_runtime_frames_fail(self):
        # user 2026-10-23: the final review (ART-04) found frames below 2x their node size after the user had approved the
        # art; the same runtime check runs in every art round (backgrounds 1.5x)
        root = self.project([('blurry', 'gameplay')] + self.FULL, league_add=True)
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        bad = self.problems(r, 'gameplay')
        self.assertIn('low_res: Canvas/Robot (frame "gameplay:10") picture 140x126 is drawn at 82.5x90 = 1.40x - needs >= 2x (165x180 px)', bad)
        self.assertIn('low_res: Canvas/GameBg (frame "bg_spa")', bad)
        self.assertIn('= 1.47x - needs >= 1.5x', bad)
        self.assertIn('low_res: Canvas/OldShelf', bad)
        self.assertNotIn('low_res: Canvas/Tray', bad)
        (root / 'docs/art').mkdir(parents=True, exist_ok=True)
        (root / 'docs/art/clarity-exempt.json').write_text(json.dumps({'frames': [{'frame': 'orig_*', 'why': 'original shelf kept (localize)'},
                                                                                   {'frame': 'gameplay:*', 'why': ''}]}))
        bad = self.problems(self.run_audit(root)[1], 'gameplay')
        self.assertNotIn('Canvas/OldShelf', bad)
        self.assertIn('Canvas/Robot', bad, 'an exemption needs a why')
        good = ' '.join(p for row in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] for p in row['problems'])
        self.assertNotIn('low_res', good)

    def test_clipping_is_caught(self):
        # user 2026-10-23: the energy "20" drawn over the lightning icon, a coin pile hanging off the left end of the WATCH AD
        # button, "WATCH AD · DOUBLE COINS" as a small caption under it, buttons on top of each other (穿模)
        code, r = self.run_audit(self.project([('clipping', 'reward')] + self.FULL, league_add=True))
        self.assertEqual(code, 1)
        bad = self.problems(r, 'reward')
        for kind in ('overlap_text_picture: "20" (Canvas/EnergyBar/EnergyCount) is drawn over the picture Canvas/EnergyBar/EnergyIcon',
                     'clip_out: Canvas/BtnWatchAd/CoinPile sticks out of Canvas/BtnWatchAd', 'action_caption: "WATCH AD DOUBLE COINS"',
                     'overlap_buttons: Canvas/BtnHome and Canvas/BtnShop'):
            self.assertIn(kind, bad)
        good = ' '.join(p for row in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] for p in row['problems'])
        for kind in ('overlap_', 'clip_out', 'action_caption'):
            self.assertNotIn(kind, good)

    @staticmethod
    def paint_checker(root, scene, node_path, cell=10):
        """The fake-transparency checkerboard an image generator bakes into card art (user 2026-10-23: green squares in
        every Daily Rewards card)."""
        from PIL import Image, ImageDraw
        f = next((root / 'docs/test').glob('*-ui-dump-%s-*.json' % scene))
        d = json.loads(f.read_text())
        r = next(n['rect'] for n in d['nodes'] if n['path'] == node_path)
        shot = f.parent / d['screenshot']
        im = Image.open(shot).convert('RGB')
        dr = ImageDraw.Draw(im)
        x0, y0, x1, y1 = int(r[0] * 375), int(r[1] * 812), int((r[0] + r[2]) * 375), int((r[1] + r[3]) * 812)
        for y in range(y0, y1, cell):
            for x in range(x0, x1, cell):
                light = ((x - x0) // cell + (y - y0) // cell) % 2
                dr.rectangle([x, y, min(x1, x + cell) - 1, min(y1, y + cell) - 1], fill=(176, 226, 160) if light else (120, 190, 110))
        im.save(shot)

    def test_digits_over_each_other_and_checkerboard_fail(self):
        # user 2026-10-23 Daily Rewards popup: 3-digit rewards printed as "10" over "100", the day-7 car sticking far out of
        # its card, the generator's checkerboard "transparency" inside the cards, a .fnt whose digits overlap
        root = self.project([('daily_overlap', 'reward')] + self.FULL, league_add=True)
        self.paint_checker(root, 'daily_overlap', 'Canvas/Panel/Day1')
        (root / 'assets/fonts').mkdir(parents=True)
        (root / 'assets/fonts/num_gold.fnt').write_text('info face="num_gold" size=64\ncommon lineHeight=64 base=52\n'
                                                        'char id=48 x=0 y=0 width=44 height=60 xoffset=0 yoffset=0 xadvance=26\n'
                                                        'char id=49 x=44 y=0 width=30 height=60 xoffset=0 yoffset=0 xadvance=32\n')
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        bad = self.problems(r, 'reward')
        for kind in ('glyph_overlap: the digit pictures under Canvas/Panel/Day1/Reward are drawn over each other',
                     'double_number: "150" (Canvas/Panel/Day2/Amount) and "15" (Canvas/Panel/Day2/Amount/Copy)',
                     'negative_spacing: "200" (Canvas/Panel/Day3/Amount) has spacingX -14',
                     'clip_out: Canvas/Panel/Car sticks out of Canvas/Panel/Day7',
                     'checker_fill: a checkerboard pattern'):
            self.assertIn(kind, bad)
        self.assertIn('Canvas/Panel/Day1', bad.split('checker_fill', 1)[1][:400])
        setup = ' '.join(r['setup'])
        self.assertIn('font_advance: assets/fonts/num_gold.fnt - glyph 0 (width 44, xadvance 26, gap -18; need >= 7)', setup)
        self.assertNotIn('glyph 1', setup)
        good = ' '.join(p for row in self.run_audit(self.project(self.FULL, league_add=False))[1]['pages'] for p in row['problems'])
        for kind in ('glyph_overlap', 'double_number', 'negative_spacing', 'checker_fill', 'clip_out'):
            self.assertNotIn(kind, good)

    def test_all_text_one_colour_fails(self):
        # user 2026-10-23: Hazel's Shelf Scramble home (title, PLAY, 100 and 3 all teal) and the "Your Progress" popup
        # (every word the same orange-yellow with a brown outline)
        import audit_page_richness as apr
        from PIL import Image, ImageDraw
        root = Path(tempfile.mkdtemp(prefix='colour-')); self.addCleanup(shutil.rmtree, root, True)
        lab = lambda s, col: {'label': {'string': s, 'font': 'Fredoka-Bold', 'font_kind': 'ttf', 'fontSize': 40, 'height': 60, 'color': col}}
        teal = [{'path': 'Canvas/' + n, 'name': n, 'rect': [0.1, y, 0.5, 0.05], 'comps': lab(s, [40, 190, 190])}
                for n, s, y in (('Title', "Hazel's Shelf", 0.1), ('Play', 'PLAY', 0.6), ('Coins', '100', 0.02), ('Lives', '3', 0.02))]
        self.assertIn('uniform_text_colour: all 4 text items', ' '.join(apr.colour_problems({}, teal, None)))
        varied = [dict(n, comps=lab(text, col)) for n, text, col in zip(teal, ('a', 'b', 'c', 'd'),
                  ([255, 214, 70], [255, 255, 255], [255, 150, 190], [130, 220, 255]))]
        self.assertEqual(apr.colour_problems({}, varied, None), [])
        # picture text measured on the screenshot: all words the same orange-yellow fill with a brown outline
        shot = root / 'p-ui-1.png'
        im = Image.new('RGB', (375, 812), (150, 150, 150)); dr = ImageDraw.Draw(im)
        boxes = [('Title', 0.15), ('Stars', 0.35), ('Levels', 0.5), ('BtnOk', 0.7)]
        for _, y in boxes:
            for k, yy in enumerate(range(int(812 * y) + 8, int(812 * y) + 32)):
                dr.line([(80, yy), (290, yy)], fill=(110, 60, 20) if k % 4 == 0 else (250, 190, 60))
        im.save(shot)
        d = {'_file': str(root / 'p-ui-dump-1.json'), 'screenshot': shot.name}
        pics = [{'path': 'Canvas/Panel/' + n, 'name': n, 'rect': [0.2, y, 0.6, 40 / 812], 'comps': {'sprite': {'frame': 'txt_' + n.lower()}}}
                for n, y in boxes]
        self.assertIn('uniform_text_colour: all 4 text items are the same colour (hue ~30', ' '.join(apr.colour_problems(d, pics, Image)))

    def test_dense_text_may_be_thin_and_bitmap_digits_pass(self):
        import audit_page_richness as apr
        from PIL import Image
        root = Path(tempfile.mkdtemp(prefix='dense-')); self.addCleanup(shutil.rmtree, root, True)
        shot = root / 'x-ui-1.png'; Image.new('RGB', (375, 812), (250, 240, 220)).save(shot)
        d = {'_file': str(root / 'x-ui-dump-1.json'), 'screenshot': shot.name, 'canvas_css': [0, 0, 375, 812]}
        thin = {'font': 'Nunito-Regular', 'font_kind': 'ttf', 'system_font': False, 'fontSize': 28, 'height': 60, 'color': [120, 80, 40]}
        nodes = [{'path': 'Canvas/Help/Rules', 'name': 'Rules', 'rect': [0.1, 0.3, 0.8, 0.2],
                  'comps': {'label': dict(thin, string='Drag two matching tiles together to merge them into a bigger one.')}},
                 {'path': 'Canvas/Help/Tip', 'name': 'Tip', 'rect': [0.1, 0.6, 0.5, 0.05], 'comps': {'label': dict(thin, string='Merge now')}},
                 {'path': 'Canvas/Top/Coins', 'name': 'Coins', 'rect': [0.1, 0.05, 0.2, 0.04],
                  'comps': {'label': {'string': '1,250', 'font': 'num_candy', 'font_kind': 'bitmap', 'fontSize': 30, 'height': 40,
                                      'color': [255, 255, 255]}}},
                 {'path': 'Canvas/Top/Energy', 'name': 'Energy', 'rect': [0.5, 0.05, 0.2, 0.04],
                  'comps': {'label': {'string': '5/5', 'font': 'Fredoka-Bold', 'fontSize': 30, 'height': 40, 'bold': True,
                                      'color': [255, 255, 255]}}},
                 {'path': 'Canvas/Top/Old', 'name': 'Old', 'rect': [0.75, 0.05, 0.2, 0.04],
                  'comps': {'label': {'string': '12', 'font': 'digits_gold.fnt', 'fontSize': 30, 'height': 40, 'color': [255, 255, 255]}}}]
        out = ' | '.join(apr.text_problems(d, nodes, [], Image))
        self.assertNotIn('plain_text: "Drag two', out)            # rules / notices over 40 characters may be a thinner font
        self.assertIn('plain_text: "Merge now"', out)             # short words may not
        self.assertNotIn('"1,250"', out)                          # generated digit pictures as a bitmap font
        self.assertIn('font_number: "5/5"', out)                  # a TTF number
        self.assertNotIn('"12"', out)                             # an older dump without font_kind: judged by the .fnt name

    def test_dark_bold_text_is_banned_any_hue(self):
        # user 2026-10-23 (permanent): dark-teal "COINS 785 / LEVEL 1" HUD over the sky, dark-teal "HOME SCREEN OPEN ·
        # PROFILE RETURN OPEN / MISSIONS 2/3 RESOLVED" on a cream panel; any dark bold text, label colour or picture pixels
        sys.path.insert(0, str(HERE))
        import audit_page_richness as apr
        from PIL import Image, ImageDraw
        tmp = Path(tempfile.mkdtemp(prefix='dark-bold-'))
        self.addCleanup(shutil.rmtree, tmp, True)
        im = Image.new('RGB', (375, 812), (150, 205, 245))                       # sky
        draw = ImageDraw.Draw(im)
        draw.rectangle([40, 300, 335, 420], fill=(246, 238, 220))                 # cream panel
        draw.rectangle([60, 330, 300, 380], fill=(30, 70, 72))                    # dark-teal "picture text" glyphs
        draw.rectangle([20, 40, 160, 80], fill=(255, 255, 255)); draw.rectangle([20, 40, 160, 46], fill=(60, 40, 20))
        im.save(tmp / 'g-ui-hud-1.png')
        d = {'_file': str(tmp / 'g-ui-dump-hud-1.json'), 'screenshot': 'g-ui-hud-1.png', 'canvas_css': [0, 0, 375, 812]}

        def lab(name, words, rgb, rect, **kw):
            return {'path': 'Canvas/' + name, 'name': name, 'rect': rect, 'opacity': 1,
                    'comps': {'label': dict({'string': words, 'color': list(rgb), 'fontSize': 30, 'height': 40, 'bold': True}, **kw)}}
        nodes = [lab('Coins', 'COINS 785', (88, 60, 40), [0.05, 0.12, 0.3, 0.05]),           # dark brown bold: any hue
                 lab('Level', 'LEVEL 1', (45, 52, 70), [0.4, 0.12, 0.3, 0.05], bold=False, outline={'width': 2}),  # slate
                 lab('Best', 'BEST 120', (255, 246, 214), [0.05, 0.2, 0.3, 0.05], outline={'width': 3, 'color': [90, 50, 20]}),
                 {'path': 'Canvas/Panel/Status', 'name': 'Status', 'rect': [60 / 375, 330 / 812, 240 / 375, 50 / 812], 'opacity': 1,
                  'comps': {'sprite': {'frame': 'txt_HOME_SCREEN_OPEN'}}},
                 {'path': 'Canvas/Hud/Coin', 'name': 'Coin', 'rect': [20 / 375, 40 / 812, 140 / 375, 40 / 812], 'opacity': 1,
                  'comps': {'sprite': {'frame': 'txt_COINS'}}}]
        out = ' | '.join(apr.text_problems(d, nodes, [], Image))
        self.assertIn('dark_bold_text: "COINS 785"', out)
        self.assertIn('dark_bold_text: "LEVEL 1"', out)
        self.assertNotIn('"BEST 120" is dark', out)                    # light fill with a dark outline is the right way
        self.assertIn('dark_picture_text: "HOME SCREEN OPEN"', out)    # picture text measured on the pixels
        self.assertNotIn('dark_picture_text: "COINS"', out)            # white glyphs with a thin dark edge are fine
        from audit_dev_text import PAT
        for words in ('HOME SCREEN OPEN · PROFILE RETURN OPEN', 'MISSIONS 2/3 RESOLVED'):
            self.assertTrue(PAT.search(words), words)
        self.assertFalse(PAT.search('Open the shop'))

    def test_mixed_caption_styles_fail(self):
        # user 2026-10-23: LEVELS / SOUVENIRS picture text on different ribbons, SETTINGS typed, HOME SCREEN +2 and
        # PROFILE REVISIT +2 typed on cloud plates - five buttons, four caption styles
        root = self.project(self.FULL + [('mixed_captions', 'other'), ('ribbon_captions', 'skins')], league_add=True)
        code, r = self.run_audit(root)
        bad = self.problems(r, 'other')
        self.assertIn('mixed_caption_style', bad)
        for way in ('picture text: BtnLevels/BtnSouvenirs', 'font label: BtnSettings', 'on plate "caption_cloud"'):
            self.assertIn(way, bad)
        from PIL import Image, ImageDraw
        dump = next((root / 'docs/test').glob('*-ui-dump-ribbon_captions-*.json'))
        shot = next((root / 'docs/test').glob('*-ui-ribbon_captions-*.png'))

        def paint(mixed):        # the caption ribbons as they look on the screen: same plate, letters in one or two colours
            im = Image.open(shot).convert('RGB'); draw = ImageDraw.Draw(im)
            for n in json.loads(dump.read_text())['nodes']:
                q = n['rect']; box = [q[0] * 375, q[1] * 812, (q[0] + q[2]) * 375, (q[1] + q[3]) * 812]
                if n['name'].startswith('CapPlate'):
                    draw.rectangle(box, fill=(150, 80, 60))
                elif n['name'].startswith('Cap'):
                    ink = (90, 210, 200) if mixed and n['name'] in ('Cap1', 'Cap3') else (250, 250, 240)
                    draw.rectangle(box, fill=(150, 80, 60))
                    for k in range(int(box[0]) + 4, int(box[2]) - 4, 6):
                        draw.rectangle([k, box[1] + 6, k + 3, box[3] - 6], fill=ink)
            im.save(shot)
        paint(False)
        self.assertNotIn('mixed_caption_style', self.problems(self.run_audit(root)[1], 'skins'))   # one plate, one colour: fine
        paint(True)                                          # same way but different colours still fails
        self.assertIn('different colours', self.problems(self.run_audit(root)[1], 'skins'))

    def test_developer_wording_on_screen_fails(self):
        root = self.project(self.FULL, league_add=False)
        f = next((root / 'docs/test').glob('*-ui-dump-settings-*.json'))
        f.write_text(f.read_text().replace('"txt_How_to_Play"', '"txt_LOCAL_PREVIEW"'))
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        self.assertIn('dev_text', self.problems(r, 'settings'))

    def test_missing_screenshot_fails(self):
        root = self.project(self.FULL, league_add=False)
        next((root / 'docs/test').glob('*-ui-play-*.png')).unlink()
        code, r = self.run_audit(root)
        self.assertEqual(code, 1)
        self.assertIn('no_screenshot', ' '.join(p for row in r['pages'] for p in row['problems']))

    def test_settings_pages_need_their_rows(self):
        code, r = self.run_audit(self.project([(s, 'settings_sound' if p == 'settings' else 'settings' if p == 'settings_sound' else p)
                                               for s, p in self.FULL], league_add=True))
        self.assertEqual(code, 1)
        self.assertIn('settings_general', self.problems(r, 'settings'))
        self.assertIn('settings_sound', self.problems(r, 'settings_sound'))

    def test_required_pages(self):
        code, r = self.run_audit(self.project([('good_home', 'home'), ('good_result', 'result_win')], league_add=True))
        self.assertEqual(code, 1)
        self.assertEqual(r['missing'], ['result_fail', 'settings', 'settings_sound', 'league'])


@unittest.skipUnless(NODE, 'node not installed')
class ArtCheckTests(unittest.TestCase):
    """art_check.py: the art line's own check right after each art round (user 2026-10-21)."""
    def run_check(self, scenes, flat=(), bar=False, extra_screens=(), board=None, runtime_verified=True, screen_alias=False):
        helper = PageRichnessTests()
        helper.addCleanup = self.addCleanup
        root = helper.project(scenes, league_add=False, flat=flat)
        screens_path = root / 'docs/art/screens.json'
        screens_json = json.loads(screens_path.read_text())
        screens_json['runtime_verified'] = runtime_verified
        # Synthetic fixtures must meet the same two-viewport matrix contract as the
        # auditor. These resized test images are not game/runtime acceptance evidence.
        screens_json['required_viewports'] = [dict(name='test_short', width=375, height=812), dict(name='test_tall', width=390, height=844)]
        from PIL import Image
        for source in list((root / 'docs/test').glob('*-ui-dump-*.json')):
            dump = json.loads(source.read_text())
            dump['viewport'] = dict(width=375, height=812)
            dump['page'] = dict(width=375, height=812, dpr=1)
            dump['canvas_css'] = [0, 0, 375, 812]
            source.write_text(json.dumps(dump))
            second = dict(dump)
            second['viewport'] = dict(width=390, height=844)
            second['page'] = dict(width=390, height=844, dpr=1)
            second['canvas_css'] = [0, 0, 390, 844]
            second['screenshot'] = 'second-' + dump['screenshot']
            with Image.open(root / 'docs/test' / dump['screenshot']) as shot:
                shot.resize((390, 844)).save(root / 'docs/test' / second['screenshot'])
            (source.parent / ('second-' + source.name)).write_text(json.dumps(second))
        screens_path.write_text(json.dumps(screens_json))
        if screen_alias:
            first_dump = next((root / 'docs/test').glob('*-ui-dump-*.json'))
            identity = json.loads(first_dump.read_text())['screen']
            for candidate in (root / 'docs/test').glob('*-ui-dump-*.json'):
                dump = json.loads(candidate.read_text())
                if dump['screen'] == identity:
                    dump['screen'] = dump['purpose']
                    candidate.write_text(json.dumps(dump))
        if extra_screens:    # pages/popups listed in docs/art/screens.json but never dumped
            sj = json.loads(screens_path.read_text())
            sj['screens'] += [{'id': n, 'name': n, 'purpose': n, 'open': 'tap the gift'} for n in extra_screens]
            screens_path.write_text(json.dumps(sj))
        if bar:      # user 2026-10-22: top resource bar declared; an endless game (no map)
            (root / 'docs/top-bar.json').write_text(json.dumps({'schema': 'top_bar.v1', 'theme': 'ocean', 'resources': [
                {'kind': 'currency', 'name': 'Pearls', 'icon': 'pearl', 'node': 'TopBar/Pearls', 'count': 'TopBar/Pearls/Count'},
                {'kind': 'progress', 'name': 'Best', 'icon': 'flag', 'node': 'TopBar/Level', 'count': 'TopBar/Level/Count'}]}))
            (root / 'docs/levels').mkdir(parents=True)
            (root / 'docs/levels/level_plan.json').write_text(json.dumps({'schema': 'level_plan.v1', 'mode': 'endless', 'why': 'one run'}))
        # Build genuine synthetic PNG + Cocos source metadata for every captured
        # frame; these validate source coverage, not a real game's artwork.
        import hashlib
        from PIL import ImageDraw
        (root / 'project.json').write_text('{}')
        texture_root = root / 'assets' / 'fixture-textures'
        texture_root.mkdir(parents=True, exist_ok=True)
        frames = set()
        for captured in (root / 'docs/test').glob('*-ui-dump-*.json'):
            for node in json.loads(captured.read_text()).get('nodes', []):
                frame = node.get('comps', {}).get('sprite', {}).get('frame')
                if isinstance(frame, str) and frame and not frame.startswith('background_'):
                    frames.add(frame)
        for frame in frames:
            name = hashlib.sha256(frame.encode()).hexdigest() + '.png'
            image = Image.new('RGBA', (64,64), (0,0,0,0))
            ImageDraw.Draw(image).rounded_rectangle((8,8,55,55), radius=12, fill=(80,150,220,255))
            image.save(texture_root / name)
            (texture_root / (name + '.meta')).write_text(json.dumps({'subMetas': {frame: {}}}))
        out = Path(tempfile.mkdtemp(prefix='artcheck-out-')) / 'r'
        self.addCleanup(shutil.rmtree, out.parent, True)
        code, text = py('art_check.py', '--project', root, '--out', out, *(['--board', board] if board else []))
        return code, json.loads((out / 'art-check.json').read_text()), text

    def test_good_pages_pass(self):
        scenes = [('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, bar=True)
        bad = [x for x in r['rows'] if x['status'] == '需处理']
        self.assertEqual(code, 0, json.dumps(bad, ensure_ascii=False, indent=1))
        self.assertIn('看图清单', text)
        rows = {x['check']: x['status'] for x in r['rows']}
        self.assertEqual(rows['关卡地图'], '通过')
        self.assertEqual(rows['字不压扁拉伸、字色有变化'], '通过')
        self.assertEqual(rows['实际页面状态与截图（docs/art/screens.json）'], '通过')
        self.assertEqual(rows['位置穿模（字和图不互相压、数字不叠印、不伸出按钮/胶囊/卡片、主功能字在按钮上、没有假透明格子）'], '通过')
        self.assertEqual(rows['穿模审查图（给 Codex 看）'], '提示')            # zoomed crops of buttons/capsules/numbers made
        self.assertIn('穿模审查图', text)
        self.assertEqual(rows['顶部资源栏'], '提示')          # "goes up after a win" is checked in the test stage
        self.assertEqual(rows['文字一次成图（标题logo、整张按钮、图片数字）'], '通过')
        self.assertEqual(rows['同组按钮同一种风格（按钮和下面的字做法、底板、颜色一致）'], '通过')

    def test_mixed_button_captions_block_the_art_round(self):
        # user 2026-10-23: five feature buttons, four caption styles - caught by the art line itself, before any person looks
        scenes = [s for s in PageRichnessTests.FULL if s[1] != 'league'] + [('mixed_captions', 'other')]
        code, r, text = self.run_check(scenes, bar=True)
        self.assertEqual(code, 1)
        row = next(x for x in r['rows'] if x['check'].startswith('同组按钮同一种风格'))
        self.assertEqual(row['status'], '需处理')
        self.assertIn('mixed_caption_style', row['detail'])

    def test_missing_top_bar_blocks_the_art_round(self):
        code, r, text = self.run_check([s for s in PageRichnessTests.FULL if s[1] != 'league'])
        self.assertEqual(code, 1)
        rows = {x['check']: x['status'] for x in r['rows']}
        self.assertEqual(rows['顶部资源栏'], '需处理')
        self.assertEqual(rows['关卡地图'], '需处理')

    def test_round_two_pages_fail(self):
        scenes = [('round2_home', 'home'), ('round2_map', 'map')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, flat=('play',))
        self.assertEqual(code, 1)
        row = next(x for x in r['rows'] if x['check'] == '页面内容与背景')
        self.assertEqual(row['status'], '需处理')
        one = next(x for x in r['rows'] if x['check'] == '文字一次成图（标题logo、整张按钮、图片数字）')
        self.assertEqual(one['status'], '需处理')                  # PLAY typed on its plate (user 2026-10-23)
        self.assertIn('spliced_button', one['detail'] if 'detail' in one else json.dumps(one, ensure_ascii=False))

    def test_squashed_words_and_unlisted_screens_block(self):
        # user 2026-10-23: squashed DETAILS words, Canvas-drawn text; every clickable page/popup restyled and dumped together
        scenes = [('squashed', 'skins'), ('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, bar=True)
        self.assertEqual(code, 1)
        rows = {x['check']: x for x in r['rows']}
        self.assertEqual(rows['字不压扁拉伸、字色有变化']['status'], '需处理')
        self.assertIn('squashed_text', rows['字不压扁拉伸、字色有变化']['detail'])
        self.assertIn('canvas_text', rows['文字一次成图（标题logo、整张按钮、图片数字）']['detail'])
        missing_code, missing_report, _ = self.run_check(scenes,bar=True,extra_screens=('progress_popup',))
        self.assertEqual(missing_code,1)
        self.assertEqual(missing_report['rows'][0]['status'],'缺采集')
        self.assertIn('progress_popup',json.dumps(missing_report,ensure_ascii=False))
        self.assertIn('压扁', text)

    def test_screen_inventory_must_be_runtime_verified_and_exactly_named(self):
        scenes = [('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        for kwargs, expected in (({'runtime_verified': False}, '运行核对'), ({'screen_alias': True}, '缺采集')):
            code, report, _ = self.run_check(scenes, bar=True, **kwargs)
            self.assertEqual(code, 1)
            row = report['rows'][0]
            self.assertEqual(row['status'], '缺采集')
            self.assertIn(expected, row['detail'])

    def test_clipping_blocks_the_art_round(self):
        scenes = [('clipping', 'reward'), ('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, bar=True)
        self.assertEqual(code, 1)
        row = next(x for x in r['rows'] if x['check'].startswith('位置穿模'))
        self.assertEqual(row['status'], '需处理')
        for kind in ('overlap_text_picture', 'clip_out', 'action_caption'):
            self.assertIn(kind, row['detail'])
        sheets = next(x for x in r['rows'] if x['check'] == '穿模审查图（给 Codex 看）')
        self.assertEqual(sheets['status'], '提示')

    def test_overlapping_digits_block_the_art_round(self):
        scenes = [('daily_overlap', 'reward'), ('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, bar=True)
        self.assertEqual(code, 1)
        row = next(x for x in r['rows'] if x['check'].startswith('位置穿模'))
        self.assertEqual(row['status'], '需处理')
        for kind in ('glyph_overlap', 'double_number', 'negative_spacing'):
            self.assertIn(kind, row['detail'])
        self.assertIn('数字', text)

    def test_clock_spacing_is_measured_after_phone_scaling(self):
        # Regression from the Bus Queue HUD: source .fnt xadvance passed, but the 01:46 bitmap glyphs
        # rendered with less than 2.5 CSS px between them and looked merged on the phone.
        from PIL import Image
        from audit_page_richness import clock_glyph_clearance_problems
        root = Path(tempfile.mkdtemp(prefix='clock-clearance-'))
        self.addCleanup(shutil.rmtree, root, True)
        fonts = root / 'assets/fonts'; fonts.mkdir(parents=True)
        metric_lines = [
            'info face="Timer" size=128 bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=2,2',
            'common lineHeight=160 base=130 scaleW=512 scaleH=512 pages=1 packed=0',
            'page id=0 file="timer.png"', 'chars count=5',
        ]
        for code in (48, 49, 52, 54, 58):
            metric_lines.append('char id=%d x=0 y=0 width=100 height=110 xoffset=0 yoffset=0 xadvance=116 page=0 chnl=15' % code)
        (fonts / 'Timer.fnt').write_text('\n'.join(metric_lines) + '\n')
        dumps = root / 'dumps'; dumps.mkdir()
        dump_file = dumps / 'timer-ui-dump-home.json'; dump_file.write_text('{}')
        Image.new('RGB', (390, 844), (100, 180, 230)).save(dumps / 'timer-ui-home.png')
        for viewport, canvas_height, scale in ((390, 844, 0.442), (375, 812, 0.425)):
            node = {'path': 'Canvas/UI/MenuLayer/energy_timer', 'name': 'energy_timer',
                    'rect': [0.2, 0.1, 87.59 * scale / viewport, 0.03],
                    'screen': [0.2, 0.1, 87.59 * scale / viewport, 0.03],
                    'comps': {'label': {'string': '01:46', 'font': 'Timer', 'font_kind': 'bitmap',
                                        'fontSize': 35, 'actualFontSize': 35, 'width': 87.59, 'spacingX': 0}}}
            dump = {'_file': str(dump_file), 'screenshot': 'timer-ui-home.png',
                    'canvas_css': [0, 0, viewport, canvas_height], 'nodes': [node]}
            before = clock_glyph_clearance_problems(dump, root)
            self.assertTrue(any('font_advance_rendered' in issue and 'CSS px' in issue for issue in before), before)
            node['comps']['label']['spacingX'] = 2
            after = clock_glyph_clearance_problems(dump, root)
            self.assertFalse(after, after)

    def test_low_res_blocks_from_the_first_round_on_both_boards(self):
        # user 2026-10-23: the final review's ART-04 (runtime frames < 2x node size, background < 1.5x) is the same check as
        # the art self-check after every art round - also the first localize round in the original style
        scenes = [('blurry', 'gameplay'), ('good_home+bar', 'home')] + [s for s in PageRichnessTests.FULL[1:] if s[1] != 'league']
        code, r, text = self.run_check(scenes, bar=True, board='localize')
        self.assertEqual(r['art_style'], 'original')
        self.assertEqual(code, 1)
        row = next(x for x in r['rows'] if x['check'].startswith('清晰度（ART-04'))
        self.assertEqual(row['status'], '需处理')
        self.assertIn('Canvas/Robot', row['detail'])
        # The second viewport can be the worse ratio; preserve the actual low-resolution invariant.
        ratios = [float(value) for value in re.findall(r'(\d+(?:\.\d+)?)x', row['detail'])]
        self.assertTrue(any(value < 2 for value in ratios), row['detail'])

    def test_nothing_dumped_is_not_skipped(self):
        code, r, text = self.run_check([])
        self.assertEqual(code, 1)
        self.assertEqual(r['rows'][0]['status'], '缺采集')


class AssetSheetTests(unittest.TestCase):
    def test_dark_art_on_transparent_background_stays_visible(self):
        from PIL import Image, ImageDraw
        tmp = Path(tempfile.mkdtemp(prefix='sheet-alpha-'))
        im = Image.new('RGBA', (200, 80), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle([20, 20, 180, 60], fill=(30, 30, 30, 255))
        (tmp / 'art').mkdir()
        im.save(tmp / 'art' / 'btn.png')
        code, out = py('make_contact_sheet.py', tmp / 'art', '--out', tmp / 'sheets')
        self.assertEqual(code, 0, out)
        sheet = Image.open(tmp / 'sheets' / 'sheet_01.jpg').convert('RGB')
        corner = sheet.getpixel((12, 12))                      # transparent area of the thumbnail
        self.assertGreater(sum(corner), 300)                   # grey checkerboard, not black


if __name__ == '__main__':
    unittest.main(verbosity=2)
