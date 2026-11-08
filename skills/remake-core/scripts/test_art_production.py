"""Production linkage refusal and compatibility tests; algorithm fixtures, not game screenshots."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import art_receipt as receipt
from PIL import Image, ImageDraw
import art_production as link


class ProductionLink(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'docs/art/source'
        shutil.copytree(link.ART.parent / 'examples/fixed-caption', self.source)
        (self.root / 'assets').mkdir()
        self.output = self.root / 'assets/claim.png'
        self.spec = self.source / 'recipe.json'
        self.ids = ['claim-small', 'claim-tall']

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return self.root / link.MANIFEST

    def save(self, data):
        self.manifest().write_text(json.dumps(data))

    def command(self, *extra, expected=0):
        p = subprocess.run([sys.executable, '-B', str(link.ART / 'compose_fixed_button.py'),
                            str(self.spec), str(self.output), *map(str, extra)], capture_output=True, text=True)
        self.assertEqual(p.returncode, expected, p.stderr)
        return p

    def produce(self):
        return self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids)

    def cases(self):
        data = json.loads(self.manifest().read_text())
        data['cases'] = [dict(id=name, owner='Canvas/Claim', inside=[0,0,1,1], children=['Canvas/Claim/Text'],
                              screen=name, viewport_width=393, expected_width=393, expected_height=852)
                         for name in self.ids]
        self.save(data)

    def write_budget(self, size=(60, 20), ids=None):
        path = self.source/'usage.json'
        path.write_text(json.dumps(dict(unit='css_px', density=2,
            cases=[dict(id=i, css_size=size) for i in (ids or self.ids)])))
        return path

    def test_usage_budget_rejects_before_replacing_output(self):
        budget = self.write_budget()
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids,
                     '--usage-budget', budget)
        old = self.output.read_bytes(), self.manifest().read_bytes()
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids,
                     '--final-size', 68, 22, expected=1)
        self.assertEqual(old, (self.output.read_bytes(), self.manifest().read_bytes()))
        self.assertTrue(link.audit(self.root, require_cases=False)['passed'])

    def test_usage_budget_is_retained_and_all_cases_are_required(self):
        budget = self.write_budget()
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids,
                     '--usage-budget', budget)
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', self.ids[0])
        row = json.loads(self.manifest().read_text())['production_assets'][0]
        self.assertEqual(row['expected_cases'], self.ids)
        self.assertIn('usage_budget', row)
        self.write_budget(ids=[self.ids[0]])
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', self.ids[0],
                     '--usage-budget', budget, expected=1)

    def test_budget_file_change_invalidates_receipt_binding(self):
        budget = self.write_budget()
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids,
                     '--usage-budget', budget)
        self.cases()
        self.assertIsNotNone(link.fingerprint(self.root))
        budget.write_text(budget.read_text() + ' ')
        with self.assertRaises(ValueError):
            link.fingerprint(self.root)

    def test_normal_and_case_coverage(self):
        p = self.produce()
        self.assertFalse(json.loads(p.stdout)['production']['runtime_verified'])
        self.assertTrue(link.audit(self.root, require_cases=False)['passed'])
        self.assertFalse(link.audit(self.root)['passed'])
        self.cases()
        self.assertTrue(link.audit(self.root)['passed'])
        # Other artwork is outside this declared producer, not falsely marked verified.
        Image.new('RGBA', (15,15), 'red').save(self.root / 'assets/character.png')
        self.assertEqual(len(link.audit(self.root)['assets']), 1)

    def test_legacy_command_unchanged(self):
        self.command()
        self.assertFalse(self.manifest().exists())
        self.assertFalse(link.audit(self.root)['declared'])

    def test_fail_does_not_replace_previous_output_or_mark_success(self):
        self.produce()
        image_before = self.output.read_bytes()
        record_before = self.manifest().read_bytes()
        data = json.loads(self.spec.read_text()); data['safe_box'] = [0,0,10,10]
        self.spec.write_text(json.dumps(data))
        p = subprocess.run([sys.executable, '-B', str(link.ART/'compose_fixed_button.py'), str(self.spec),
                            str(self.output), '--project',str(self.root),'--asset-id','claim','--cases',*self.ids],capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.output.read_bytes(), image_before)
        self.assertEqual(self.manifest().read_bytes(), record_before)
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])

    def test_changed_output_rejected_even_if_hash_rewritten(self):
        self.produce()
        Image.new('RGBA', (136,45), 'red').save(self.output)
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])
        data = json.loads(self.manifest().read_text())
        data['production_assets'][0]['output']['sha256'] = link.sha(self.output)
        data['production_assets'][0]['passed'] = True
        self.save(data)
        result = link.audit(self.root, require_cases=False)
        self.assertFalse(result['passed'])
        self.assertIn('replayed pixels', result['assets'][0]['error'])

    def test_changed_source_and_rule_rejected(self):
        self.produce()
        data = json.loads(self.manifest().read_text())
        data['production_assets'][0]['rules'] = {}
        self.save(data)
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])
        self.produce()
        source = self.source/'claim.png'
        source.write_bytes(source.read_bytes() + b'extra')
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])

    def test_rerun_keeps_other_cases_and_existing_usage(self):
        self.produce(); self.cases()
        before = json.loads(self.manifest().read_text())
        before['other_metadata'] = {'keep': True}
        self.save(before)
        self.command('--project', self.root, '--asset-id','claim','--cases','claim-small')
        after = json.loads(self.manifest().read_text())
        self.assertEqual(after['cases'], before['cases'])
        self.assertEqual(after['other_metadata'], before['other_metadata'])
        self.assertEqual(after['production_assets'][0]['expected_cases'],self.ids)

    def test_id_output_conflicts_and_missing_flags(self):
        self.produce()
        with self.assertRaises(ValueError):
            link.prepare(self.root,'other',self.ids,'fixed_button',self.output,spec=self.spec)
        with self.assertRaises(ValueError):
            link.prepare(self.root,'claim',self.ids,'fixed_button',self.root/'assets/other.png',spec=self.spec)
        self.command('--project',self.root,expected=2)

    def test_empty_duplicate_and_malformed_declarations(self):
        self.produce(); self.cases()
        valid=json.loads(self.manifest().read_text())
        for mutate in [lambda x:x.update(production_assets=[]),
                       lambda x:x['production_assets'].append(copy.deepcopy(x['production_assets'][0])),
                       lambda x:x['cases'].append(copy.deepcopy(x['cases'][0])),
                       lambda x:x['production_assets'][0].update(expected_cases=[]),
                       lambda x:x['cases'][0].update(inside=None,children=[]),
                       lambda x:x.update(production_assets=[None])]:
            data=copy.deepcopy(valid);mutate(data);self.save(data)
            self.assertFalse(link.audit(self.root)['passed'])

    def test_outside_or_symlink_inputs_refused(self):
        with self.assertRaises(ValueError):
            link.prepare(self.root,'claim',self.ids,'fixed_button',self.root.parent/'bad.png',spec=self.spec)
        alias = self.root/'source-alias';alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            link.prepare(self.root,'claim',self.ids,'fixed_button',self.output,spec=alias/'recipe.json')
        data=json.loads(self.spec.read_text());data['base']['file']='../../../../outside.png'
        self.spec.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            link.prepare(self.root,'claim',self.ids,'fixed_button',self.output,spec=self.spec)

    def test_crop_uses_same_separator_and_exact_pixels(self):
        sheet = self.source/'sheet.png'
        im=Image.new('RGBA',(100,60),(0,0,0,0));draw=ImageDraw.Draw(im)
        draw.rectangle((10,10,35,45),fill='red');draw.rectangle((65,10,90,45),fill='blue');im.save(sheet)
        output=self.root/'assets/frame.png'
        p=subprocess.run([sys.executable,'-B',str(link.ART/'cut_sheet_frame.py'),str(sheet),'--grid','1','2',
                          '--cell','1','1','--out',str(output),'--project',str(self.root),'--asset-id','frame',
                          '--cases','frame-small'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(link.audit(self.root, require_cases=False)['passed'])
        data=json.loads(self.manifest().read_text())
        # Repointing to the other source cell, even with matching output hash, is detectable.
        data['production_assets'][0]['parameters']['cell']=[1,2];self.save(data)
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])
        data['production_assets'][0]['parameters']['cell']=[1,1]
        data['production_assets'][0]['parameters']['fixed_rect']=[11,10,30,40];self.save(data)
        result=link.audit(self.root,require_cases=False)
        self.assertFalse(result['passed'])
        self.assertIn('loses',result['assets'][0]['error'])


    def test_uneven_sheet_mode_is_replayed_and_bound(self):
        sheet = self.source / 'uneven.png'
        im = Image.new('RGBA', (120, 240))
        draw = ImageDraw.Draw(im)
        draw.rectangle((10, 10, 100, 40), fill='red')
        draw.rectangle((10, 60, 100, 150), fill='blue')
        draw.rectangle((10, 175, 100, 229), fill='green')
        im.save(sheet)
        output = self.root / 'assets/uneven.png'
        command = [sys.executable, '-B', str(link.ART / 'cut_sheet_frame.py'), str(sheet),
                   '--grid', '3', '1', '--cell', '2', '1', '--out', str(output),
                   '--project', str(self.root), '--asset-id', 'uneven', '--cases', 'uneven-small',
                   '--rows-from-bands', '--source-sha256', hashlib.sha256(sheet.read_bytes()).hexdigest()]
        proc = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(link.audit(self.root, require_cases=False)['passed'])
        data = json.loads(self.manifest().read_text())
        data['production_assets'][0]['parameters']['rows_from_bands'] = False
        self.save(data)
        self.assertFalse(link.audit(self.root, require_cases=False)['passed'])

    def receipt_check(self):
        return receipt.check(self.root, board='remake', policy='new')

    def passed_receipt(self):
        return receipt.write(self.root, 'pass', {'status': 'pass', 'checked': 1, 'failed': 0})

    def assert_receipt_stale(self):
        result = self.receipt_check()
        self.assertEqual(result['state'], 'production_binding_stale', result)
        self.assertEqual(result['level'], 'block', result)

    def test_receipt_binds_production_without_pixel_replay(self):
        self.produce(); self.cases()
        with mock.patch.object(link, 'inspect', side_effect=AssertionError('no pixel replay')):
            binding = link.fingerprint(self.root)
            rec = self.passed_receipt()
            self.assertEqual(rec['production_binding'], binding)
            self.assertEqual(self.receipt_check()['state'], 'match_pass')
        # Production binding never replaces the English runtime value/capture gates.
        checked = receipt.check(self.root, board='localize', policy='new')
        self.assertEqual(checked['state'], 'value_evidence_stale')

    def test_receipt_rejects_each_recipe_case_source_and_rule_drift(self):
        self.produce(); self.cases(); self.passed_receipt()
        original_spec = self.spec.read_bytes()
        original_manifest = self.manifest().read_bytes()
        source = self.source / 'claim.png'
        original_source = source.read_bytes()
        for path, original in [(self.spec, original_spec), (source, original_source)]:
            with self.subTest(file=path.name):
                path.write_bytes(original + b' ')
                self.assert_receipt_stale()
                path.write_bytes(original)
        data = json.loads(original_manifest)
        data['cases'][0]['inside'] = [0.1, 0.1, 0.8, 0.8]
        self.save(data); self.assert_receipt_stale()
        self.manifest().write_bytes(original_manifest)
        # Raw bytes bind even a rewrite with equivalent JSON.
        self.manifest().write_bytes(original_manifest + b'\n')
        self.assert_receipt_stale()
        self.manifest().write_bytes(original_manifest)
        with mock.patch.object(link, 'rule_hashes', return_value={'changed-rule.py': 'new'}):
            self.assert_receipt_stale()
        self.assertEqual(self.receipt_check()['state'], 'match_pass')

    def test_receipt_rejects_deleted_declaration_and_output(self):
        self.produce(); self.cases(); self.passed_receipt()
        original = self.manifest().read_bytes()
        data = json.loads(original); del data['production_assets']
        self.save(data); self.assert_receipt_stale()
        self.manifest().unlink(); self.assert_receipt_stale()
        self.manifest().write_bytes(original)
        self.output.unlink(); self.assert_receipt_stale()

    def test_legacy_receipt_must_recheck_after_adding_production(self):
        self.command()
        old = self.passed_receipt()
        self.assertNotIn('production_binding', old)
        self.assertEqual(self.receipt_check()['state'], 'match_pass')
        self.produce(); self.cases()
        self.assert_receipt_stale()
        self.passed_receipt()
        self.assertEqual(self.receipt_check()['state'], 'match_pass')

    def test_legacy_without_production_keeps_original_receipt_semantics(self):
        self.command()
        self.manifest().parent.mkdir(parents=True, exist_ok=True)
        self.save({'cases': []})
        self.assertIsNone(link.fingerprint(self.root))
        rec = self.passed_receipt()
        self.assertNotIn('production_binding', rec)
        self.assertEqual(self.receipt_check()['state'], 'match_pass')
        self.save({'cases': [], 'unrelated': 'legacy'})
        self.assertEqual(self.receipt_check()['state'], 'match_pass')

    def test_invalid_production_cannot_write_pass_but_can_record_failure(self):
        self.produce(); self.cases(); self.passed_receipt()
        original_receipt = receipt.receipt_path(self.root).read_bytes()
        self.save({'cases': [], 'production_assets': []})
        with self.assertRaises(ValueError):
            self.passed_receipt()
        self.assertEqual(receipt.receipt_path(self.root).read_bytes(), original_receipt)
        rec = receipt.write(self.root, 'fail', {'status': 'fail'})
        self.assertIn('production_binding_error', rec)
        self.assert_receipt_stale()

    def test_fingerprint_invalid_record_types_fail_closed(self):
        self.produce(); self.cases()
        valid = json.loads(self.manifest().read_text())
        for mutate in [lambda x: x['production_assets'][0].update(output=[]),
                       lambda x: x['production_assets'][0].update(inputs=[]),
                       lambda x: x['production_assets'][0].update(kind='unknown'),
                       lambda x: x['production_assets'][0].update(expected_cases=[]),
                       lambda x: x['cases'].clear()]:
            data = copy.deepcopy(valid); mutate(data); self.save(data)
            with self.assertRaises(ValueError):
                link.fingerprint(self.root)

    def art_directory_symlink(self):
        art = self.root / 'docs/art'
        target = self.root / 'legacy-art'
        art.rename(target)
        art.symlink_to(target, target_is_directory=True)

    def test_legacy_symlink_art_directory_without_manifest_stays_neutral(self):
        self.command()
        self.art_directory_symlink()
        self.assertFalse(self.manifest().exists())
        self.assertIsNone(link.fingerprint(self.root))
        result = link.audit(self.root)
        self.assertTrue(result['passed'])
        self.assertFalse(result['declared'])
        self.passed_receipt()
        self.assertEqual(self.receipt_check()['state'], 'match_pass')

    def test_legacy_symlink_art_directory_with_only_cases_stays_neutral(self):
        self.command()
        self.save({'cases': []})
        self.art_directory_symlink()
        self.assertIsNone(link.fingerprint(self.root))
        self.assertTrue(link.audit(self.root)['passed'])
        self.assertFalse(link.audit(self.root)['declared'])
        self.passed_receipt()
        self.assertEqual(self.receipt_check()['state'], 'match_pass')

    def test_declared_symlink_and_deleted_bound_declaration_still_refused(self):
        self.produce(); self.cases(); self.passed_receipt()
        self.art_directory_symlink()
        with self.assertRaisesRegex(ValueError, 'symlink'):
            link.fingerprint(self.root)
        result = link.audit(self.root)
        self.assertFalse(result['passed'])
        self.assertTrue(result['declared'])
        self.assert_receipt_stale()
        self.save({'cases': []})
        self.assertIsNone(link.fingerprint(self.root))
        self.assertTrue(link.audit(self.root)['passed'])
        self.assert_receipt_stale()
        self.manifest().unlink()
        self.assertIsNone(link.fingerprint(self.root))
        self.assert_receipt_stale()

    def test_source_carry_cannot_mask_registered_output_change(self):
        self.produce(); self.cases(); self.passed_receipt()
        before = self.receipt_check()
        with Image.open(self.output) as original:
            original.resize((68, 22)).save(self.output)
        receipt.carry(self.root, 'test-source-resize', before)
        self.assert_receipt_stale()
        self.assertFalse(link.audit(self.root)['passed'])

    def source_resize_fixture(self, max_side=68):
        from tiktok_finalize_steps import images
        self.produce(); self.cases()
        with Image.open(self.output) as actual:
            w, h = actual.size
        texture = '12345678-1234-1234-1234-123456789012'
        frame = '12345678-1234-1234-1234-123456789013'
        meta = {'ver': '2.3.5', 'uuid': texture, 'type': 'sprite', 'width': w, 'height': h,
                'platformSettings': {}, 'subMetas': {'claim': {'ver': '1.0.4', 'uuid': frame,
                'rawTextureUuid': texture, 'trimX': 0, 'trimY': 0, 'offsetX': 0, 'offsetY': 0,
                'width': w, 'height': h, 'rawWidth': w, 'rawHeight': h, 'borderTop': 0,
                'borderBottom': 0, 'borderLeft': 0, 'borderRight': 0, 'subMetas': {}}}}
        self.output.with_suffix('.png.meta').write_text(json.dumps(meta))
        kit = self.root / '.tiktok-kit'; kit.mkdir(exist_ok=True)
        (kit / 'image-overrides.json').write_text(json.dumps({'images': {'assets/claim.png': {'max_side': max_side}}}))
        return images

    def test_actual_source_resize_adoption_and_regeneration_keep_final_size(self):
        images = self.source_resize_fixture()
        self.passed_receipt()
        old_receipt = receipt.receipt_path(self.root).read_bytes()
        before = link.audit(self.root)
        self.assertFalse(before['passed'])
        self.assertEqual(before['assets'][0]['pending_source_resize']['size'], [68, 22])
        self.assertIn('--final-size 68 22', before['assets'][0]['error'])
        applied = images.apply({'project': self.root, 'policy': 'new'})
        self.assertFalse(applied['blocks'], applied)
        self.assertTrue(applied['changed'])
        self.assertFalse(link.audit(self.root)['passed'])
        process = subprocess.run([sys.executable, '-B', str(Path(link.__file__)), '--project', str(self.root),
                                  '--adopt-source-resize', 'claim'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertTrue(result['recapture_required'])
        self.assertFalse(result['receipt_refreshed'])
        self.assertEqual(receipt.receipt_path(self.root).read_bytes(), old_receipt)
        self.assert_receipt_stale()
        self.assertTrue(link.audit(self.root)['passed'])
        adopted_bytes = self.output.read_bytes()
        self.produce()
        with Image.open(self.output) as actual:
            self.assertEqual(actual.size, (68, 22))
        self.assertTrue(link.audit(self.root)['passed'])
        self.assertEqual(images.plan({'project': self.root, 'policy': 'new'})['actions'], [])
        # The producer is allowed a different PNG encoding, but not different RGBA.
        with Image.open(self.output) as actual:
            import io
            with Image.open(io.BytesIO(adopted_bytes)) as adopted:
                self.assertEqual(actual.convert('RGBA').tobytes(), adopted.convert('RGBA').tobytes())

    def test_explicit_final_size_resolves_plan_without_running_source(self):
        self.source_resize_fixture()
        self.assertFalse(link.audit(self.root)['passed'])
        self.command('--project', self.root, '--asset-id', 'claim', '--cases', *self.ids, '--final-size', '68', '22')
        self.assertTrue(link.audit(self.root)['passed'])
        self.produce()
        with Image.open(self.output) as actual:
            self.assertEqual(actual.size, (68, 22))

    def test_adoption_rejects_pixel_change_distortion_enlarge_crop_and_loss(self):
        self.produce(); self.cases()
        original_manifest = self.manifest().read_bytes()
        with Image.open(self.output) as image:
            original = image.convert('RGBA')
        try:
            corrupt = original.resize((68, 22), Image.Resampling.LANCZOS)
            corrupt.putpixel((10, 10), (255, 0, 0, 255))
            bad_images = [corrupt, original.resize((68, 12), Image.Resampling.LANCZOS),
                          original.resize((272, 90), Image.Resampling.LANCZOS), original.crop((0, 0, 68, 22))]
            for bad in bad_images:
                with self.subTest(size=bad.size):
                    bad.save(self.output)
                    with self.assertRaises(ValueError):
                        link.adopt_source_resize(self.root, 'claim')
                    self.assertEqual(self.manifest().read_bytes(), original_manifest)
                    bad.close()
            original.convert('RGB').save(self.output, format='JPEG', quality=70)
            with self.assertRaises(ValueError):
                link.adopt_source_resize(self.root, 'claim')
            self.assertEqual(self.manifest().read_bytes(), original_manifest)
        finally:
            original.close()

    def test_lossless_reencoding_adopts_only_equal_rgba(self):
        self.produce(); self.cases(); self.passed_receipt()
        before = self.output.read_bytes()
        with Image.open(self.output) as image:
            image.save(self.output, compress_level=0)
        self.assertNotEqual(self.output.read_bytes(), before)
        result = link.adopt_source_resize(self.root, 'claim')
        self.assertTrue(result['recapture_required'])
        self.assertTrue(link.audit(self.root)['passed'])
        self.assert_receipt_stale()
        record = json.loads(self.manifest().read_text())['production_assets'][0]
        self.assertFalse(record.get('derivations'))

    def test_sheet_regeneration_preserves_size_and_checks_full_cut_first(self):
        sheet = self.source / 'one-sheet.png'
        source = Image.new('RGBA', (100, 60), (0, 0, 0, 0))
        ImageDraw.Draw(source).rectangle((10, 10, 35, 45), fill='red')
        source.save(sheet)
        output = self.root / 'assets/cut.png'
        command = [sys.executable, '-B', str(link.ART / 'cut_sheet_frame.py'), str(sheet),
                   '--grid', '1', '1', '--cell', '1', '1', '--out', str(output),
                   '--project', str(self.root), '--asset-id', 'cut', '--cases', 'cut-small']
        for extra in [['--final-size', '13', '18'], []]:
            proc = subprocess.run(command + extra, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with Image.open(output) as actual:
                self.assertEqual(actual.size, (13, 18))
            self.assertTrue(link.audit(self.root, require_cases=False)['passed'])
        before = output.read_bytes(), self.manifest().read_bytes()
        proc = subprocess.run(command + ['--fixed-rect', '11', '10', '35', '45'], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual((output.read_bytes(), self.manifest().read_bytes()), before)

    def test_resize_prediction_respects_legacy_and_unknown_metadata(self):
        self.produce(); self.cases()
        report = link.audit(self.root)
        self.assertTrue(report['passed'])
        self.assertEqual(report['assets'][0]['source_resize_plan']['state'], 'unresolved')
        self.source_resize_fixture()
        with mock.patch.object(receipt, 'strictness', return_value=(False, 'localize', 'legacy')):
            report = link.audit(self.root)
            self.assertTrue(report['passed'])
            self.assertEqual(report['assets'][0]['source_resize_plan']['state'], 'legacy_no_source_resize')



if __name__ == '__main__':
    unittest.main()
