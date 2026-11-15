"""Production entry-point controls; synthetic pixels are not art or runtime acceptance."""
import copy
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

from PIL import Image

SKILLS = Path(os.environ.get('ENFORCEMENT_TEST_SKILLS', Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0, str(SKILLS / 'remake-core/scripts'))
sys.path.insert(0, str(SKILLS / 'remake-art/scripts'))
import art_usage_budget as U
import art_records as R
import bind_art as B

USAGE = {'unit': 'css_px', 'density': 2, 'cases': [
    {'id': 'wide', 'css_size': [150, 24]}, {'id': 'narrow', 'css_size': [100, 16]}]}
IDS = ['wide', 'narrow']


class UsagePipeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'assets/ui').mkdir(parents=True)
        (self.root / '.tiktok-kit').mkdir()
        self.policy('required')
        self.image = self.root / 'assets/ui/word.png'
        Image.new('RGBA', (320, 64), (220, 160, 110, 255)).save(self.image)

    def tearDown(self):
        self.temp.cleanup()

    def policy(self, value):
        (self.root / '.tiktok-kit/policy.json').write_text(json.dumps({'production_inputs': value}))

    def asset(self):
        return {'name': 'word', 'kind': 'badge', 'w': 320, 'h': 64, 'has_text': True, 'text': 'LEVEL',
                'alpha': True, 'usage': copy.deepcopy(USAGE), 'expected_cases': IDS[:]}

    def prompt_cli(self, asset):
        art = self.root / 'art.json'; art.write_text(json.dumps({'module': 'fixture', 'assets': [asset]}))
        style = self.root / 'style.json'; style.write_text(json.dumps({'board': 'localize', 'project': str(self.root),
            'style_sentence': 'Original fixture colours', 'references': [], 'palette': {
                'light': '#FFF1DC', 'outline': '#7A183C', 'line': '#9C506A',
                'main': '#B67595', 'secondary': '#73B9CF', 'accent': '#E48AAB'}}))
        out = self.root / 'prompts.json'
        result = subprocess.run([sys.executable, '-B', str(SKILLS / 'ad-boost/scripts/art/make_prompts.py'),
            '--art', str(art), '--style', str(style), '--out', str(out), '--board', 'localize', '--project', str(self.root)],
            capture_output=True, text=True, env=dict(os.environ, AD_BOOST_SKILLS_DIR=str(SKILLS)))
        return result, out

    def test_new_project_refuses_missing_usage_before_prompt_is_written(self):
        a = self.asset(); a.pop('usage'); a.pop('expected_cases')
        r, out = self.prompt_cli(a)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn('production inputs required', r.stderr + r.stdout)
        self.assertFalse(out.exists())

    def test_same_declared_cases_reach_prompt_and_smallest_css_requirement(self):
        r, out = self.prompt_cli(self.asset())
        self.assertEqual(r.returncode, 0, r.stderr)
        row = json.loads(out.read_text())['prompts'][0]
        self.assertEqual(row['usage'], USAGE)
        self.assertEqual(row['expected_cases'], IDS)
        self.assertEqual(row['usage_summary']['minimum_css_size'], [100.0, 16.0])
        self.assertIn('narrow: 100 x 16 CSS px', row['prompt'])
        self.assertEqual(row['text_pair']['need'], 4.5)
        self.assertIsNone(row['usage_summary']['visual_passed'])

    def test_missing_case_and_invalid_policy_refuse(self):
        a = self.asset(); a['usage']['cases'].pop()
        with self.assertRaisesRegex(ValueError, 'every expected case'):
            U.asset_usage(a, self.root)
        self.policy('guess')
        with self.assertRaisesRegex(ValueError, 'required or legacy'):
            U.asset_usage({'name': 'no usage'}, self.root)

    def test_legacy_calls_remain_compatible_and_no_density_gate_added(self):
        self.policy('legacy')
        self.assertIsNone(U.asset_usage({'name': 'old'}, self.root))
        a = self.asset(); a['usage']['density'] = 10
        record = U.asset_usage(a, self.root)
        result = U.validate_output(record['usage'], (80, 16), project=self.root)
        self.assertFalse(result['blocking'])
        self.assertFalse(result['auto_regenerate'])

    def test_direct_registration_requires_and_preserves_usage(self):
        with self.assertRaisesRegex(ValueError, 'production inputs required'):
            R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels')
        rows = R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels', usage=USAGE, expected_cases=IDS)
        self.assertEqual(rows[-1]['usage'], USAGE)
        binding = {'image': 'assets/ui/word.png', 'node': 'Any/Word'}
        inherited = B.binding_usage(self.root, binding)
        self.assertEqual(inherited['usage'], USAGE)
        self.assertEqual(inherited['expected_cases'], IDS)
        self.assertFalse(inherited['source_measurements']['blocking'])

    def test_formal_static_binding_consumes_registered_usage_before_writing(self):
        meta = {'ver': '2.3.7', 'uuid': 'fixture-texture', 'type': 'sprite', 'subMetas': {
            'word': {'ver': '1.0.6', 'uuid': 'fixture-frame', 'trimX': 0, 'trimY': 0,
                     'width': 320, 'height': 64, 'rawWidth': 320, 'rawHeight': 64}}}
        Path(str(self.image) + '.meta').write_text(json.dumps(meta))
        prefab = self.root / 'assets/Page.prefab'
        prefab.write_text(json.dumps([
            {'__type__': 'cc.Prefab', 'data': {'__id__': 1}},
            {'__type__': 'cc.Node', '_name': 'Page', '_children': [{'__id__': 2}], '_components': [],
             '_contentSize': {'width': 720, 'height': 1280}},
            {'__type__': 'cc.Node', '_name': 'Word', '_parent': {'__id__': 1}, '_children': [],
             '_components': [{'__id__': 3}], '_contentSize': {'width': 200, 'height': 80}},
            {'__type__': 'cc.Sprite', 'node': {'__id__': 2}, '_spriteFrame': {'__uuid__': 'fixture-frame'},
             '_type': 0, '_sizeMode': 0, '_isTrimmedMode': True}]))
        mapping = self.root / 'bind.json'; mapping.write_text(json.dumps({'bindings': [{
            'prefab': 'assets/Page.prefab', 'node': 'Page/Word', 'image': 'assets/ui/word.png'}]}))
        before = prefab.read_bytes()
        with self.assertRaisesRegex(B.BindError, 'production inputs required'):
            B.run_bind(self.root, mapping, None, False)
        self.assertEqual(prefab.read_bytes(), before)
        R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels', usage=USAGE, expected_cases=IDS)
        rows = B.run_bind(self.root, mapping, None, False)
        self.assertEqual(rows[0]['usage_record']['usage'], USAGE)
        self.assertEqual(rows[0]['new_size'], [200, 40])

    def test_binding_missing_or_contradicting_budget_refuses_without_modifying_image(self):
        before = self.image.read_bytes()
        with self.assertRaisesRegex(B.BindError, 'production inputs required'):
            B.binding_usage(self.root, {'image': 'assets/ui/word.png'})
        R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels', usage=USAGE, expected_cases=IDS)
        wrong = copy.deepcopy(USAGE); wrong['cases'][0]['css_size'] = [200, 24]
        with self.assertRaisesRegex(B.BindError, 'contradicts'):
            B.binding_usage(self.root, {'image': 'assets/ui/word.png', 'usage': wrong, 'expected_cases': IDS})
        self.assertEqual(self.image.read_bytes(), before)

    def test_strict_uses_actual_css_budget_and_derive_keeps_source_relationship(self):
        R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels', usage=USAGE, expected_cases=IDS)
        old_sha = R.sha(self.image.read_bytes())
        Image.new('RGBA', (80, 16), (220, 160, 111, 255)).save(self.image)
        R.record_derived(self.root, [self.image], origin=old_sha)
        inherited = B.binding_usage(self.root, {'image': 'assets/ui/word.png'})
        self.assertEqual(inherited['usage'], USAGE)
        (self.root / 'docs/art').mkdir(parents=True, exist_ok=True)
        (self.root / 'docs/art/clarity-policy.json').write_text(json.dumps({'preset': 'strict'}))
        with self.assertRaisesRegex(B.BindError, 'explicit strict'):
            B.binding_usage(self.root, {'image': 'assets/ui/word.png'})

    def test_registration_cli_consumes_inline_budget(self):
        r = subprocess.run([sys.executable, '-B', str(SKILLS / 'remake-core/scripts/art_records.py'), 'generated',
            '--project', str(self.root), '--tool', 'fixture tool', '--prompt', 'fixture pixels',
            '--usage-json', json.dumps(USAGE), '--expected-cases', *IDS, '--', str(self.image)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(R.valid_generated(self.root)[0][R.sha(self.image.read_bytes())]['usage'], USAGE)

    def test_manual_generation_postprocess_record_and_binding_share_declaration(self):
        # Synthetic colour rectangle is a transport fixture, never accepted art.
        asset = self.asset(); asset.update(kind='object', has_text=False, text='', alpha=False)
        gen = self.root / 'gen'; (gen / 'raw').mkdir(parents=True)
        shutil.copy2(self.image, gen / 'raw/word.png')
        prompts = self.root / 'manual-prompts.json'
        prompts.write_text(json.dumps({'name_guard': {'project': str(self.root)}, 'prompts': [
            dict(asset, prompt='synthetic transport fixture', refs=[])]}))
        (self.root / 'project.json').write_text(json.dumps({'engine': 'cocos-creator-js', 'version': '2.4.15'}))
        art = self.root / 'manual-art.json'; art.write_text(json.dumps({'module': 'fixture', 'assets': [asset]}))
        env = dict(os.environ, AD_BOOST_SKILLS_DIR=str(SKILLS))
        commands = [
            ['record_manual.py', '--prompts', str(prompts), '--out', str(gen), '--tool', 'fixture transport', '--source-dir', str(self.image.parent)],
            ['postprocess.py', '--art', str(art), '--gen', str(gen), '--project', str(self.root), '--dest', str(self.image.parent)],
            ['skill_link.py', 'record', '--project', str(self.root), '--gen', str(gen)]]
        for command in commands:
            result = subprocess.run([sys.executable, '-B', str(SKILLS / 'ad-boost/scripts/art' / command[0]), *command[1:]],
                                    capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rec = json.loads((gen / 'gen_log.json').read_text())['records']['word']
        self.assertEqual(rec['usage'], USAGE)
        self.assertEqual(rec['post']['usage']['cases'][1]['id'], 'narrow')
        self.assertEqual(B.binding_usage(self.root, {'image': 'assets/ui/word.png'})['usage'], USAGE)

    def test_postprocess_catches_changed_usage_before_copy(self):
        gen = self.root / 'gen'; (gen / 'raw').mkdir(parents=True)
        raw = gen / 'raw/word.png'; shutil.copy2(self.image, raw)
        asset = self.asset(); asset.update(kind='object', has_text=False, text='', alpha=False)
        changed = copy.deepcopy(USAGE); changed['cases'][1]['css_size'] = [90, 16]
        art = self.root / 'art.json'; art.write_text(json.dumps({'module': 'fixture', 'assets': [dict(asset, usage=changed)]}))
        (gen / 'gen_log.json').write_text(json.dumps({'records': {'word': dict(asset, raw=str(raw), sha256=R.sha(raw.read_bytes()))}}))
        dest = self.root / 'assets/not-copied'
        result = subprocess.run([sys.executable, '-B', str(SKILLS / 'ad-boost/scripts/art/postprocess.py'),
            '--art', str(art), '--gen', str(gen), '--dest', str(dest)], capture_output=True, text=True,
            env=dict(os.environ, AD_BOOST_SKILLS_DIR=str(SKILLS)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('usage changed since generation', result.stdout + result.stderr)
        self.assertFalse((dest / 'word.png').exists())
        raw_before = raw.read_bytes()
        repaired = subprocess.run([sys.executable, '-B', str(SKILLS / 'ad-boost/scripts/art/postprocess.py'),
            '--art', str(art), '--gen', str(gen), '--dest', str(dest), '--update-usage'], capture_output=True, text=True,
            env=dict(os.environ, AD_BOOST_SKILLS_DIR=str(SKILLS)))
        self.assertEqual(repaired.returncode, 0, repaired.stdout + repaired.stderr)
        rec = json.loads((gen / 'gen_log.json').read_text())['records']['word']
        self.assertEqual(rec['usage'], changed)
        self.assertEqual(rec['generation_usage']['usage'], USAGE)
        self.assertEqual(raw.read_bytes(), raw_before)
        self.assertIsNone(rec['usage_change']['visual_passed'])

    def test_source_is_resampled_at_each_real_declared_css_size(self):
        sys.path.insert(0, str(SKILLS / 'ad-boost/scripts/art'))
        import postprocess as P
        from PIL import ImageDraw
        im = Image.new('RGBA', (320, 64), (85, 45, 60, 255))
        ImageDraw.Draw(im).rectangle((80, 20, 240, 44), fill=(255, 250, 230, 255))
        report = P.usage_text_contrast(im, self.asset())
        self.assertEqual([r['render_css'] for r in report['cases']], [[120, 24], [80, 16]])
        self.assertEqual([r['measurement']['need'] for r in report['cases']], [3, 4.5])
        self.assertFalse(report['runtime_verified'])
        self.assertIsNone(report['visual_passed'])

    def test_source_that_passes_large_text_is_rejected_for_small_use_before_copy(self):
        sys.path.insert(0, str(SKILLS / 'ad-boost/scripts/art'))
        import postprocess as P
        from PIL import ImageDraw
        im = Image.new('RGBA', (320, 64), (145, 145, 145, 255))
        ImageDraw.Draw(im).rectangle((80, 20, 240, 44), fill=(255, 255, 255, 255))
        self.assertEqual(P.text_contrast(im, self.asset())['need'], 3)
        with self.assertRaisesRegex(ValueError, 'planned CSS use narrow'):
            P.usage_text_contrast(im, self.asset())

    def test_existing_record_consumer_catches_manual_bypass_without_pixels(self):
        directory = self.root / 'docs/art'; directory.mkdir(parents=True)
        path = directory / 'generated.json'
        digest = R.sha(self.image.read_bytes())
        path.write_text(json.dumps({'images': [{'file': 'assets/ui/word.png', 'sha256': digest,
            'tool': 'handwritten ledger', 'prompt': 'record without actual usage'}]}))
        assets = {'images': {'assets/ui/word.png': digest}, 'embedded': {}, 'audio': {}}
        shipped = {'files': {'assets/ui/word.png': ['fixture shipped consumer']}}
        bad = R.check_generated(self.root, board='localize', assets=assets, ship=shipped)
        self.assertFalse(bad['ok'])
        self.assertEqual(bad['usage_errors'][0]['file'], 'assets/ui/word.png')
        self.assertIn('production inputs required', bad['usage_errors'][0]['error'])
        # A declared unused image does not become a new all-assets gate.
        unused = R.check_generated(self.root, board='localize', assets=assets, ship={'files': {}})
        self.assertTrue(unused['ok'])
        self.policy('legacy')
        legacy = R.check_generated(self.root, board='localize', assets=assets, ship=shipped)
        self.assertNotEqual(legacy['ok'], False)
        self.policy('required')
        R.record_generated(self.root, [self.image], 'fixture tool', prompt='fixture pixels', usage=USAGE, expected_cases=IDS)
        good = R.check_generated(self.root, board='localize', assets=assets, ship=shipped)
        self.assertTrue(good['ok'], good['message'])
        self.assertEqual(good['usage_errors'], [])

    def test_existing_record_consumer_rejects_unregistered_new_shipped_image(self):
        digest = R.sha(self.image.read_bytes())
        assets = {'images': {'assets/ui/word.png': digest}, 'embedded': {}, 'audio': {}}
        out = R.check_generated(self.root, board='localize', assets=assets,
                                ship={'files': {'assets/ui/word.png': ['fixture shipped consumer']}})
        self.assertFalse(out['ok'])
        self.assertEqual(len(out['unrecorded']), 1)
        self.assertNotIn('英化游戏只提示', out['message'])

    def test_generation_exception_does_not_silently_waive_usage(self):
        directory=self.root/'docs/art';directory.mkdir(parents=True)
        row={'file':'assets/ui/word.png','why':'Explicit maintenance synthetic-source exception'}
        path=directory/'script-drawn-allow.json';path.write_text(json.dumps({'allow':[row]}))
        digest=R.sha(self.image.read_bytes())
        kwargs={'board':'localize','assets':{'images':{'assets/ui/word.png':digest},'embedded':{},'audio':{}},
                'ship':{'files':{'assets/ui/word.png':['fixture consumer']}}}
        bad=R.check_generated(self.root,**kwargs)
        self.assertFalse(bad['ok']);self.assertEqual(len(bad['usage_errors']),1)
        row.update(usage=USAGE,expected_cases=IDS);path.write_text(json.dumps({'allow':[row]}))
        self.assertTrue(R.check_generated(self.root,**kwargs)['ok'])


if __name__ == '__main__':
    unittest.main()
