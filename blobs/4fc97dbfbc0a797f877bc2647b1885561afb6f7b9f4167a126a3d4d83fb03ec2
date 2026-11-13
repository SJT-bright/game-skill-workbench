"""Regression controls for pixel-analysis reuse, never a proof of game acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from art_analysis_cache import PageCache, tool_snapshot
import audit_glyph_core as glyph
from test_glyph_core import write_font, label_node, page

HERE = Path(__file__).resolve().parent


class AnalysisCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.outer = Path(self.temp.name).resolve()
        self.root = self.outer / 'project'
        (self.root / 'assets').mkdir(parents=True)
        (self.root / 'docs/test').mkdir(parents=True)
        self.dump = self.root / 'docs/test/test-ui-dump-home.json'
        self.shot = self.root / 'docs/test/home.png'
        self.document = {'tool': 'ui_dump', 'producer': 'chrome_touch.dump_ui', 'schema': 1,
                         'screen': 'home-small', 'purpose': 'home', 'kind': 'home',
                         'nodes': [], 'screenshot': 'home.png', '_file': str(self.dump)}
        self.dump.write_text(json.dumps(self.document))
        Image.new('RGB', (40,80), (235,133,75)).save(self.shot)

    def tearDown(self):
        self.temp.cleanup()

    def key(self):
        return PageCache(self.root).key(self.document, self.shot)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def store(self, value):
        cache = PageCache(self.root)
        key = cache.key(self.document, self.shot)
        self.assertIsNotNone(key)
        self.assertIsNone(cache.get(key))
        cache.put(key, value)
        cache.finish()
        return key, cache.root / (key + '.json')

    def test_owning_outputs_do_not_self_invalidate_but_unknown_inputs_stay_bound(self):
        (self.root/'docs/art').mkdir(parents=True)
        before = self.key()
        output = self.write('docs/art/first_piece-ad-pages.json', json.dumps({
            'tool': 'art_production_preflight', 'passed': False, 'input_binding': {}}))
        self.assertEqual(before, self.key())
        output.write_text(json.dumps({'tool': 'art_production_preflight', 'passed': True}))
        self.assertEqual(before, self.key())
        unknown = self.write('docs/art/new-policy.json', '{"actual_input":true}')
        self.assertNotEqual(before, self.key())
        unknown.unlink()
        self.document['render_report'] = str(output)
        self.dump.write_text(json.dumps(self.document))
        explicit = self.key()
        output.write_text(json.dumps({'tool': 'art_production_preflight', 'passed': False}))
        self.assertNotEqual(explicit, self.key())  # Explicit raw references remain dependencies.

    def test_nonproduction_test_files_do_not_change_checker_fingerprint(self):
        tools = self.outer/'tools'
        tools.mkdir()
        checker = tools/'audit_pixels.py'
        checker.write_text('actual checker v1')
        before = tool_snapshot(tools)
        (tools/'test_unrelated.py').write_text('unrelated test')
        (tools/'fixture_example.json').write_text('{}')
        self.assertEqual(before, tool_snapshot(tools))
        checker.write_text('actual checker v2')
        self.assertNotEqual(before, tool_snapshot(tools))

    def test_repeat_hits_and_retains_failures(self):
        failure = [['known_overlap: letters overlap the icon'], {'visible': 3}]
        key, _ = self.store(failure)
        reader = PageCache(self.root)
        self.assertEqual(reader.key(self.document, self.shot), key)
        self.assertEqual(reader.get(key), failure)
        self.assertEqual(reader.report()['reused'], 1)
        reader.finish()

    def test_original_exemption_and_board_inputs_invalidate(self):
        for relative, first, second in [
                ('docs/english/pre-english-images.json', '{"images":{"abc":{}}}', '{"images":{}}'),
                ('docs/board.txt', 'localize', 'remake'),
                ('.tiktok-kit/finalize-source.json', '{"board":"localize"}', '{"board":"remake"}')]:
            with self.subTest(path=relative):
                path = self.write(relative, first)
                before = self.key()
                self.assertIsNotNone(before)
                path.write_text(second)
                self.assertNotEqual(before, self.key())
                path.unlink()

    def test_source_font_code_and_bad_policy_json_invalidate(self):
        for relative in ('assets/ui.ts', 'assets/font.fnt', 'docs/art/button-set.json'):
            with self.subTest(path=relative):
                path = self.write(relative, '{}')
                before = self.key()
                path.write_text('{bad json or changed source')
                self.assertNotEqual(before, self.key())
                path.unlink()

    def test_external_font_page_disables_cache_and_preserves_actual_glyph_defect(self):
        fonts = self.root / 'assets/fonts'
        external = self.root / 'font-pages'
        fonts.mkdir(); external.mkdir()
        write_font(external, 'digits', 96, 90)
        declaration = (external / 'digits.fnt').read_text().replace(
            'file="digits.png"', 'file="../../font-pages/digits.png"')
        (fonts / 'digits.fnt').write_text(declaration)
        node = label_node('Canvas/topbar/coinCount', '120', 'digits', 30, 30)
        document = page([node])
        before = glyph.glyph_core_problems(document, [node], glyph.font_ink_ratios(self.root, Image), None)
        self.assertEqual(before, [])
        cache = PageCache(self.root)
        self.assertIsNone(cache.key(self.document, self.shot))
        self.assertIn('bitmap page', cache.reason)
        # Only the external PNG changes; the copied production .fnt stays identical.
        write_font(external, 'digits', 96, 40)
        after = glyph.glyph_core_problems(document, [node], glyph.font_ink_ratios(self.root, Image), None)
        self.assertTrue(any(x.startswith('small_glyph_core:') for x in after), after)
        self.assertIsNone(PageCache(self.root).key(self.document, self.shot))

    def test_screenshot_and_raw_dump_changes_invalidate(self):
        before = self.key()
        Image.new('RGB', (40,80), (0,0,0)).save(self.shot)
        after = self.key()
        self.assertNotEqual(before, after)
        self.dump.write_text(self.dump.read_text() + '\n')
        self.assertNotEqual(after, self.key())

    def test_recursive_attachment_changes_invalidate(self):
        extra = self.root / 'docs/test/extra.png'
        Image.new('RGBA', (10,10), 'white').save(extra)
        nested = self.write('docs/test/evidence.json', '{"image":"extra.png"}')
        self.document['render_report'] = 'evidence.json'
        self.dump.write_text(json.dumps(self.document))
        before = self.key()
        self.assertIsNotNone(before)
        Image.new('RGBA', (10,10), 'black').save(extra)
        self.assertNotEqual(before, self.key())
        old = self.key()
        nested.write_text('{"image":"extra.png","observed":false}')
        self.assertNotEqual(old, self.key())
        nested.write_text('{bad')
        self.assertIsNone(self.key())

    def test_broken_or_tampered_cache_is_a_miss(self):
        key, record = self.store([[], {'visible': 3}])
        valid = json.loads(record.read_text())
        integrity_field = 'seal' if 'seal' in valid else 'sha256'
        broken_integrity = dict(valid, **{integrity_field: '0'*64})
        for bad in ('{broken', json.dumps(broken_integrity),
                    json.dumps(dict(valid, value=[[], {'visible': 99}]))):
            with self.subTest(bad=bad):
                record.write_text(bad)
                self.assertIsNone(PageCache(self.root).get(key))

    def test_finish_rejects_source_change_during_analysis(self):
        cache = PageCache(self.root)
        key = cache.key(self.document, self.shot)
        cache.put(key, [[], {}])
        self.write('assets/new-code.ts', 'changed')
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            cache.finish()
        self.assertFalse((cache.root / (key + '.json')).exists())

    def test_finish_rejects_capture_or_attachment_change_during_analysis(self):
        attachment = self.write('docs/test/evidence.json', '{"observed":true}')
        self.document['render_report'] = 'evidence.json'
        self.dump.write_text(json.dumps(self.document))
        for changed in (self.dump, self.shot, attachment):
            with self.subTest(path=changed.name):
                original = changed.read_bytes()
                cache = PageCache(self.root)
                key = cache.key(self.document, self.shot)
                self.assertIsNotNone(key)
                cache.put(key, [[], {}])
                changed.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'evidence changed'):
                    cache.finish()
                self.assertFalse((cache.root / (key + '.json')).exists())
                changed.write_bytes(original)

    def test_missing_evidence_and_loading_frames_never_reuse(self):
        before = self.key()
        self.assertIsNotNone(before)
        self.shot.unlink()
        self.assertIsNone(self.key())
        Image.new('RGB', (40,80), 'white').save(self.shot)
        for field in ({'purpose': 'loading'}, {'purpose': 'loading_retry'}, {'official_loading': True}):
            with self.subTest(field=field):
                document = dict(self.document, **field)
                self.assertIsNone(PageCache(self.root).key(document, self.shot))
        self.write('docs/art/official-loading.json', json.dumps({'frames': [
            {'dump': self.dump.relative_to(self.root).as_posix()}]}))
        self.assertIsNone(self.key())

    def test_empty_production_preflight_is_not_run(self):
        out = self.outer / 'preflight'
        proc = subprocess.run([sys.executable, '-B', str(HERE / 'art_check.py'),
                               '--project', str(self.root), '--production-only', '--out', str(out)],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads((out / 'production-preflight.json').read_text())
        self.assertFalse(result['passed'])
        self.assertEqual(result['status'], 'not_run')
        self.assertFalse(result['receipt_written'])
        self.assertFalse((self.root / '.tiktok-kit/art-receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
