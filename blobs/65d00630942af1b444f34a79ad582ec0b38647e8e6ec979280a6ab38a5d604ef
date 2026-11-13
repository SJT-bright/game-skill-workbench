"""Exact release-pair compatibility. SKILL_ART_COMPAT_BASELINE enables real old-producer proofs."""
import ast
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from PIL import Image, ImageDraw
import art_production as link
BASELINE = os.environ.get('SKILL_ART_COMPAT_BASELINE')


class DefaultRuleCompat(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'docs/art/source'
        shutil.copytree(link.ART.parent / 'examples/fixed-caption', self.source)
        (self.root / 'assets').mkdir()
        self.compat = json.loads((link.HERE / 'art-default-rules-compat.json').read_text())

    def tearDown(self): self.temp.cleanup()

    def produce(self, kind='fixed_button', skill=None, bands=False):
        art = Path(skill) / 'remake-art/scripts' if skill else link.ART
        output = self.root / 'assets/output.png'
        if kind == 'fixed_button':
            cmd = [str(art / 'compose_fixed_button.py'), str(self.source / 'recipe.json'), str(output)]
        else:
            sheet = self.source / 'sheet.png'
            image = Image.new('RGBA', (120, 240)); draw = ImageDraw.Draw(image)
            draw.rectangle((10, 10, 100, 40 if bands else 65), fill='red')
            draw.rectangle((10, 60 if bands else 95, 100, 150 if bands else 145), fill='blue')
            draw.rectangle((10, 175, 100, 229), fill='green'); image.save(sheet)
            cmd = [str(art / 'cut_sheet_frame.py'), str(sheet), '--grid', '3', '1', '--cell', '2', '1', '--out', str(output)]
            if bands: cmd += ['--rows-from-bands', '--source-sha256', link.sha(sheet)]
        result = subprocess.run([sys.executable, '-B', *cmd, '--project', str(self.root), '--asset-id', 'fixture', '--cases', 'home'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / link.MANIFEST
        data = json.loads(path.read_text())
        data['cases'] = [dict(id='home', owner='Canvas/Button', inside=[0, 0, 1, 1], children=['Canvas/Button/Text'], screen='home', viewport_width=393, expected_width=393, expected_height=852)]
        path.write_text(json.dumps(data)); return data

    def test_release_pair_hashes_are_exact(self):
        for relative, pair in self.compat['files'].items():
            self.assertEqual(link.sha(link.SKILLS / relative), pair['after_sha256'])
        self.assertEqual(link.rule_hashes('fixed_button')['remake-core/scripts/art_production.py'], self.compat['files']['remake-core/scripts/art_production.py']['before_sha256'])

    def test_default_sheet_and_fixed_button_remain_pixel_checked(self):
        for kind in ('fixed_button', 'sheet_frame'):
            with self.subTest(kind=kind):
                path = self.root / link.MANIFEST
                if path.exists(): path.unlink()
                self.produce(kind)
                self.assertTrue(link.audit(self.root)['passed'])
                self.assertIsNotNone(link.fingerprint(self.root))

    def test_new_band_mode_uses_actual_current_rules(self):
        data = self.produce('sheet_frame', bands=True)
        for relative, pair in self.compat['files'].items():
            self.assertEqual(data['production_assets'][0]['rules'][relative], pair['after_sha256'])
        self.assertTrue(link.audit(self.root)['passed'])
        data['production_assets'][0]['parameters']['rows_from_bands'] = False
        (self.root / link.MANIFEST).write_text(json.dumps(data))
        self.assertFalse(link.audit(self.root)['passed'])

    def test_non_boolean_mode_rejected_before_production_and_replay(self):
        data = self.produce('sheet_frame')
        for value in ('false', 'true', 0, 1, None, [], {}):
            with self.subTest(value=value):
                bad = copy.deepcopy(data['production_assets'][0]); bad['parameters']['rows_from_bands'] = value
                with self.assertRaisesRegex(ValueError, 'must be a boolean'): link.replay(self.root, bad)
                with self.assertRaisesRegex(ValueError, 'must be a boolean'):
                    link.prepare(self.root, 'fixture', ['home'], 'sheet_frame', self.root / 'assets/output.png', sheet=self.source / 'sheet.png', parameters=bad['parameters'])

    def test_unknown_rule_change_does_not_keep_old_fingerprint(self):
        self.produce('sheet_frame'); before = link.fingerprint(self.root); original = link.sha
        for relative in [*self.compat['files'], 'remake-core/scripts/art_usage_budget.py', 'remake-core/scripts/tiktok_finalize_steps/images.py']:
            with self.subTest(rule=relative):
                changed = link.SKILLS / relative
                with mock.patch.object(link, 'sha', side_effect=lambda p: 'f' * 64 if Path(p) == changed else original(p)):
                    self.assertNotEqual(link.fingerprint(self.root), before)
                    result = link.audit(self.root)
                    self.assertTrue(result['passed'])
                    rules = result['assets'][0]['measurements']['production_rules']
                    self.assertTrue(rules['changed'])
                    self.assertEqual(rules['current'][relative], 'f' * 64)
                    self.assertEqual(rules['verification'], 'current-rule-replay-and-exact-output-comparison')

    def test_fixed_producer_and_trim_stay_exact_dependencies(self):
        self.produce(); before = link.fingerprint(self.root); original = link.sha
        for name in ('compose_fixed_button.py', 'trim_visible.py'):
            changed = link.ART / name
            with mock.patch.object(link, 'sha', side_effect=lambda p: 'f' * 64 if Path(p) == changed else original(p)):
                self.assertNotEqual(link.fingerprint(self.root), before)
                result = link.audit(self.root)
                self.assertTrue(result['passed'])
                rules = result['assets'][0]['measurements']['production_rules']
                self.assertTrue(rules['changed'])
                self.assertEqual(rules['current'][changed.relative_to(link.SKILLS).as_posix()], 'f' * 64)

    def test_missing_or_malformed_mapping_cannot_reuse_old_fingerprint(self):
        self.produce(); before = link.fingerprint(self.root); original = Path.read_text
        for content in ('{}', '{broken', json.dumps(dict(self.compat, files={}))) :
            with mock.patch.object(Path, 'read_text', lambda p, *a, **kw: content if p.name == 'art-default-rules-compat.json' else original(p, *a, **kw)):
                self.assertNotEqual(link.fingerprint(self.root), before)
                result = link.audit(self.root)
                self.assertTrue(result['passed'])
                self.assertTrue(result['assets'][0]['measurements']['production_rules']['changed'])

    def test_pixels_cannot_be_forged_with_output_hash(self):
        data = self.produce(); output = self.root / 'assets/output.png'
        Image.new('RGBA', (136, 45), 'red').save(output)
        data['production_assets'][0]['output']['sha256'] = link.sha(output)
        (self.root / link.MANIFEST).write_text(json.dumps(data))
        result = link.audit(self.root)
        self.assertFalse(result['passed']); self.assertIn('replayed pixels', result['assets'][0]['error'])

    @unittest.skipUnless(BASELINE, 'requires formal 11.17.11 tree')
    def test_real_formal_output_rechecked_without_rewriting_old_evidence(self):
        base = Path(BASELINE)
        for relative, pair in self.compat['files'].items(): self.assertEqual(link.sha(base / relative), pair['before_sha256'])
        for kind in ('fixed_button', 'sheet_frame'):
            with self.subTest(kind=kind):
                manifest = self.root / link.MANIFEST
                if manifest.exists(): manifest.unlink()
                self.produce(kind, skill=base)
                before = (manifest.read_bytes(), (self.root / 'assets/output.png').read_bytes())
                code = 'import sys,json;sys.path.insert(0,sys.argv[1]);import art_production;print(json.dumps(art_production.fingerprint(sys.argv[2])))'
                proc = subprocess.run([sys.executable, '-B', '-c', code, str(base / 'remake-core/scripts'), str(self.root)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                record = json.loads(manifest.read_text())['production_assets'][0]
                actual = link.fingerprint(self.root)
                historical = json.loads(proc.stdout)
                if record['rules'] == link.rule_hashes(kind, record.get('parameters')):
                    self.assertEqual(actual, historical)
                else:
                    self.assertNotEqual(actual, historical, 'changed dependencies cannot reuse the old fingerprint')
                self.assertTrue(link.audit(self.root)['passed'])
                self.assertEqual(before, (manifest.read_bytes(), (self.root / 'assets/output.png').read_bytes()))

    @unittest.skipUnless(BASELINE, 'requires formal 11.17.11 tree')
    def test_default_algorithm_ast_matches_formal_branch(self):
        base = Path(BASELINE)
        def functions(path): return {n.name: n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
        old = functions(base / 'remake-art/scripts/cut_sheet_frame.py'); new = functions(link.ART / 'cut_sheet_frame.py')
        for name in ('digest', 'seam', 'fixed_frame'): self.assertEqual(ast.dump(old[name]), ast.dump(new[name]))
        extract = copy.deepcopy(new['extract'])
        self.assertEqual(extract.args.args[-1].arg, 'rows_from_bands')
        self.assertEqual(ast.dump(extract.args.defaults[-1]), 'Constant(value=False)')
        extract.args.args.pop(); extract.args.defaults.pop()
        branches = [n for n in extract.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'rows_from_bands']
        self.assertEqual(len(branches), 1)
        at = extract.body.index(branches[0]); extract.body[at:at + 1] = branches[0].orelse
        self.assertEqual(ast.dump(old['extract']), ast.dump(extract))
        # Producer input/output and pixel-comparison functions remain exact.
        # replay() now intentionally re-evaluates changed tools; its actual RGBA
        # result is covered above instead of falsely requiring historical code identity.
        old = functions(base / 'remake-core/scripts/art_production.py'); new = functions(link.HERE / 'art_production.py')
        for name in ('sha', 'local', 'file_record', 'declaration_bytes', 'read_manifest',
                     'load_producer', 'valid_id', 'check_conflicts', 'verify_file', 'inspect'):
            self.assertEqual(ast.dump(old[name]), ast.dump(new[name]), name)

if __name__ == '__main__': unittest.main()
