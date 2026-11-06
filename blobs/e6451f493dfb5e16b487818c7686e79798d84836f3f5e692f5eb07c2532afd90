"""Input preflight must stop unproven batches without running pixels or changing receipts."""
import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

import art_check
import art_input_check
from art_capture_batch import bootstrap
from art_round_check import run
import test_art_check_inputs as fixtures


class InputPreflightTests(unittest.TestCase):
    setUp = fixtures.ArtInputTests.setUp
    tearDown = fixtures.ArtInputTests.tearDown
    write_manifest = fixtures.ArtInputTests.write_manifest

    def execute(self, board='localize', build=None):
        out = self.root / 'preflight'
        receipt = self.project / '.tiktok-kit/art-receipt.json'
        receipt.parent.mkdir(exist_ok=True)
        receipt.write_text('existing receipt must remain unchanged')
        before = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        args = ['art_check.py', '--project', str(self.project), '--dumps', str(self.dumps),
                '--out', str(out), '--inputs-only', '--board', board]
        if build:
            args += ['--build', str(build)]
        with patch.object(sys, 'argv', args), \
             patch.object(art_check, 'run', side_effect=AssertionError('pixel tool started')), \
             patch('art_production.audit', side_effect=AssertionError('production analysis started')), \
             contextlib.redirect_stdout(io.StringIO()):
            code = art_check.main()
        after = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        result = json.loads((out / 'input-preflight.json').read_text())
        self.assertEqual(result['visual_checks_run'], 0)
        self.assertIsNone(result['visual_passed'])
        self.assertFalse(result['receipt_written'])
        self.assertFalse((out / 'art-check.json').exists())
        return code, result

    def test_complete_coverage_is_not_visual_approval(self):
        code, result = self.execute(board='remake')
        self.assertEqual(code, 0)
        self.assertTrue(result['ready'])
        self.assertEqual(result['dump_count'], 4)

    def test_english_web_requires_actual_export_identity(self):
        code, result = self.execute()
        self.assertEqual(code, 1)
        self.assertTrue(any('--build' in e for e in result['errors']))

    def test_legacy_names_do_not_stamp_old_pngs_as_current(self):
        build = self.root / 'build'
        build.mkdir()
        (build / 'index.html').write_text('<html><head></head></html>')
        matrix = self.project / 'docs/art/capture-plan.json'
        for f in self.dumps.glob('*ui-dump-*.json'):
            data = json.loads(f.read_text())
            data['capture_name'] = f.stem
            f.write_text(json.dumps(data))
        bootstrap(self.dumps, matrix)
        policy = json.loads(matrix.read_text())
        for row in policy['cases']:
            row.update(dpr=1, recipe='actual arrival', environment='test',
                       witness=[{'path': 'Canvas/Title'}])
        matrix.write_text(json.dumps(policy))
        self.assertIn('id', run('start', self.project, build))
        code, result = self.execute(build=build)
        self.assertEqual(code, 1)
        self.assertFalse(result['capture_round'].get('ready'))
        self.assertTrue(result['capture_round'].get('error'))
        self.assertEqual(result['dump_count'], 4)

    def test_unrecognised_capture_name_does_not_silently_disappear(self):
        (self.dumps / 'extra-ui-dump.json').write_text('{}')
        code, result = self.execute(board='remake')
        self.assertEqual(code, 1)
        self.assertTrue(any('extra-ui-dump.json' in e for e in result['errors']))

    def test_multiple_directories_are_counted_not_auto_discarded(self):
        other = self.dumps / 'earlier'
        other.mkdir()
        f = self.dumps / 'home-ui-dump-0.json'
        d = json.loads(f.read_text())
        d['screenshot'] = str(self.dumps / d['screenshot'])
        (other / f.name).write_text(json.dumps(d))
        code, result = self.execute(board='remake')
        self.assertEqual(code, 0)
        self.assertEqual(result['dump_count'], 5)
        self.assertEqual(result['capture_directories'], {'.': 4, 'earlier': 1})

    def test_full_entry_with_native_build_cannot_skip_web_provenance(self):
        native = self.root / 'Native'
        native.mkdir()
        (native / 'game.js').write_text('// resource build, not a Web capture origin')
        for f in self.dumps.glob('*ui-dump-*.json'):
            data = json.loads(f.read_text())
            data.update(tool='ui_dump', producer='ego_page.dump_ui', schema=1)
            f.write_text(json.dumps(data))
        out = self.root / 'full'
        args = ['art_check.py', '--project', str(self.project), '--dumps', str(self.dumps),
                '--out', str(out), '--board', 'localize', '--build', str(native)]
        with patch.object(sys, 'argv', args), \
             patch.object(art_check, 'base_generated_rows', return_value=([], {})), \
             patch.object(art_check, 'run', side_effect=AssertionError('pixel analysis started')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(art_check.main(), 1)
        result = json.loads((out / 'art-check.json').read_text())
        self.assertEqual(result['status'], 'blocked_inputs')
        self.assertTrue(any('--capture-build' in e for e in result['input_errors']))

    def test_explicit_capture_build_does_not_fall_back_from_wrong_directory(self):
        web = self.root / 'web'
        web.mkdir()
        (web / 'index.html').write_text('<head></head>')
        inventory = {'records': []}
        with patch('art_round_check.run', side_effect=AssertionError('wrong export accepted')):
            result = art_input_check.verify_capture(self.project, self.dumps, web, 'localize',
                                                    inventory, self.root / 'missing', require_web=True)
        self.assertFalse(result['ready'])

    def test_separate_web_identity_keeps_native_resource_argument(self):
        native, web = self.root / 'Native', self.root / 'web'
        native.mkdir()
        web.mkdir()
        (web / 'index.html').write_text('<head></head>')
        with patch('art_round_check.run', return_value={'ready': True}) as verify:
            result = art_input_check.verify_capture(self.project, self.dumps, native, 'localize',
                                                   {'records': []}, web)
        verify.assert_called_once_with('verify', self.project, web, self.dumps)
        self.assertTrue(result['ready'])


if __name__ == '__main__':
    unittest.main()
