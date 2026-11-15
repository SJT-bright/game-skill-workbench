"""Synthetic scope/identity regressions, not runtime capture or ART evidence."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image
import art_preflight
import art_production
import audit_art_slots
import audit_page_richness

HERE = Path(__file__).resolve().parent


class Scope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root/'project'
        (self.project/'assets').mkdir(parents=True)
        (self.project/'docs/art').mkdir(parents=True)
        self.config = self.project/'docs/art/visual-slots.json'
        self.dumps = self.root/'dumps'
        self.dumps.mkdir()
        self.cases = [self.case('slot-a', 'alpha'), self.case('slot-b', 'beta')]
        self.write_cases()
        self.a = self.dump('actual-capture-one', 'alpha')
        self.b = self.dump('actual-capture-two', 'beta')

    def case(self, identifier, screen):
        return dict(id=identifier, screen=screen, viewport_width=100, viewport_height=200,
                    expected_width=100, expected_height=200, owner='Panel',
                    inside=[0, 0, 1, 1], children=['Panel/Icon'])

    def write_cases(self):
        self.config.write_text(json.dumps(dict(cases=self.cases)))

    def dump(self, name, screen, height=200):
        shot = self.dumps/(name+'.png')
        Image.new('RGB', (100, height), (80, 120, 180)).save(shot)
        doc = dict(tool='ui_dump', producer='ego_page.dump_ui', schema=1,
                   screen=screen, viewport=dict(width=100, height=height),
                   page=dict(width=100, height=height, dpr=1), kind='page', purpose='other',
                   canvas_css=[0, 0, 100, height], screenshot=shot.name,
                   art_capture_id='synthetic-not-proof-'+name,
                   nodes=[dict(path='Panel', name='Panel', screen=[0, 0, 1, 1],
                               rect=[0, 0, 1, 1], comps={}, opacity=1),
                          dict(path='Panel/Icon', name='Icon', screen=[.2, .2, .1, .1],
                               rect=[.2, .2, .1, .1], comps={}, opacity=1)])
        target = self.dumps/('capture-ui-dump-'+name+'.json')
        target.write_text(json.dumps(doc))
        return target

    def docs(self):
        return audit_page_richness.load([self.dumps])

    def slots(self, ids=None):
        docs = self.docs()
        return audit_art_slots.run(self.config, [Path(d['_file']) for d in docs],
                                   [audit_page_richness.screenshot_of(d) for d in docs], case_ids=ids)

    def test_subset_is_slot_id_and_unselected_case_remains(self):
        self.b.unlink()
        result = self.slots(['slot-a'])
        self.assertTrue(result['passed'])
        self.assertEqual(result['selected_cases'], ['slot-a'])
        self.assertEqual(result['remaining_cases'], ['slot-b'])
        self.assertIsNone(result['full_art_passed'])
        self.assertFalse(self.slots()['passed'])  # Original full behavior still checks beta.
        with self.assertRaisesRegex(ValueError, 'unknown'):
            self.slots(['actual-capture-one'])

    def test_unknown_empty_duplicate_and_blank_ids_fail(self):
        for ids in ([], ['unknown'], ['slot-a', 'slot-a'], [''], [' slot-a']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.slots(ids)

    def test_duplicate_manifest_ids_fail(self):
        self.cases.append(self.cases[0].copy())
        self.write_cases()
        with self.assertRaisesRegex(ValueError, 'duplicate declared'):
            self.slots(['slot-a'])

    def test_missing_height_rejected_only_in_explicit_scope(self):
        del self.cases[0]['viewport_height']
        self.write_cases()
        self.assertTrue(self.slots()['passed'])
        with self.assertRaisesRegex(ValueError, 'height'):
            self.slots(['slot-a'])

    def test_correct_height_selected_wrong_height_not_accepted(self):
        self.dump('same-screen-tall', 'alpha', 300)
        result = self.slots(['slot-a'])
        self.assertTrue(result['passed'])
        self.a.unlink()
        self.assertFalse(self.slots(['slot-a'])['passed'])

    def test_missing_and_ambiguous_selected_capture_fail(self):
        self.a.unlink()
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            audit_art_slots.first_piece_documents(self.config, self.docs(), ['slot-a'])
        self.a = self.dump('one', 'alpha')
        self.dump('two', 'alpha')
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            audit_art_slots.first_piece_documents(self.config, self.docs(), ['slot-a'])

    def test_two_slots_on_one_page_both_run(self):
        self.cases.append(self.case('slot-a2', 'alpha'))
        self.write_cases()
        docs, selected, remaining = audit_art_slots.first_piece_documents(
            self.config, self.docs(), ['slot-a', 'slot-a2'])
        self.assertEqual(len(docs), 1)
        result = self.slots(selected)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['cases']), 2)
        self.cases[2]['children'] = ['Panel/Missing']
        self.write_cases()
        self.assertFalse(self.slots(selected)['passed'])

    def test_dump_file_selection_is_exact_unique_and_in_loaded_set(self):
        docs = self.docs()
        result = audit_page_richness.selected_dump_files(docs, [self.a])
        self.assertEqual([Path(d['_file']) for d in result], [self.a])
        for paths in ([], [self.a, self.a], [self.root/'outside.json']):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                audit_page_richness.selected_dump_files(docs, paths)

    def test_real_pixel_selection_keeps_whole_page_findings_and_full_cache_reuse(self):
        reports = {}
        original = self.a.read_bytes()
        for name, extra in [('selected', ['--dump-file', str(self.a)]), ('full', [])]:
            output = self.root/(name+'.json')
            proc = subprocess.run([sys.executable, '-B', str(HERE/'audit_page_richness.py'),
                '--project', str(self.project), '--board', 'localize', '--dumps', str(self.dumps),
                '--out', str(output), *extra], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, proc.stderr)  # Real bad plain synthetic pages.
            reports[name] = json.loads(output.read_text())
        self.assertEqual(reports['selected']['checked'], 1)
        self.assertEqual(reports['full']['checked'], 2)
        selected_page = reports['selected']['pages'][0]
        self.assertTrue(any(p.startswith('flat_background:') for p in selected_page['problems']))
        full_page = next(p for p in reports['full']['pages'] if p['screen'] == 'alpha')
        self.assertEqual(selected_page, full_page)
        cache = json.loads((self.root/'full.cache.json').read_text())
        self.assertEqual((cache['reused'], cache['recomputed']), (1, 1))
        self.assertEqual(self.a.read_bytes(), original)

    def binding(self, board='localize'):
        return art_preflight.first_piece_input_binding(self.project, [self.a], ['slot-a'], board=board)

    def test_binding_is_read_only_stable_and_covers_source_slots_scope(self):
        before = self.binding()
        self.assertTrue(before['available'], before)
        self.assertEqual(before, self.binding())
        self.assertFalse((self.project/'.tiktok-kit').exists())
        self.assertNotEqual(before, self.binding(board='remake'))
        source = self.project/'assets/ui.js'
        source.write_text('node.width = 50;')
        self.assertNotEqual(before, self.binding())
        source.unlink()
        self.assertEqual(before, self.binding())
        self.cases[0]['inside'] = [.1, .1, .9, .9]
        self.write_cases()
        self.assertNotEqual(before, self.binding())

    def test_binding_only_selected_evidence_and_recursive_attachment(self):
        before = self.binding()
        self.b.write_text(self.b.read_text()+'\n')
        self.assertEqual(before, self.binding())
        attachment = self.dumps/'observation.json'
        attachment.write_text(json.dumps(dict(value=1)))
        doc = json.loads(self.a.read_text())
        doc['observation'] = attachment.name
        self.a.write_text(json.dumps(doc))
        with_attachment = self.binding()
        self.assertTrue(with_attachment['available'])
        attachment.write_text(json.dumps(dict(value=2)))
        self.assertNotEqual(with_attachment, self.binding())
        attachment.unlink()
        self.assertFalse(self.binding()['available'])

    def scoped_entry(self, *, production_failed=False, selected_page_problem=False, mutate_source=False):
        output = self.root/'entry'
        real_run = subprocess.run
        calls = []
        def pages(cmd, **kwargs):
            if not any(Path(str(arg)).name == 'audit_page_richness.py' for arg in cmd):
                return real_run(cmd, **kwargs)
            selected = [Path(cmd[i+1]) for i, value in enumerate(cmd) if value == '--dump-file']
            self.assertEqual(selected, [self.a])
            calls.append(selected)
            findings = ['a different real problem on selected page'] if selected_page_problem else []
            Path(cmd[cmd.index('--out')+1]).write_text(json.dumps(dict(
                checked=1, setup=[], pages=[dict(screen='alpha', problems=findings)], missing=['beta'])))
            if mutate_source:
                (self.project/'assets/ui.js').write_text('late write')
            return subprocess.CompletedProcess(cmd, 1 if findings else 0, '', '')
        production = dict(passed=not production_failed, declared=True,
                          assets=[dict(id='unselected-bad-asset', passed=not production_failed)])
        with mock.patch.object(art_production, 'audit', return_value=production) as prod, \
             mock.patch.object(art_preflight, '_text_preflight', return_value=dict(passed=True)), \
             mock.patch.object(art_preflight, '_layout_preflight', return_value=dict(passed=None, status='not_run')), \
             mock.patch.object(art_preflight.subprocess, 'run', side_effect=pages), \
             contextlib.redirect_stdout(io.StringIO()):
            code = art_preflight.run(self.project, self.dumps, output, board='localize', case_ids=['slot-a'])
        prod.assert_called_once_with(self.project, require_cases=True)
        self.assertEqual(len(calls), 1)
        self.assertFalse((self.project/'.tiktok-kit/art-receipt.json').exists())
        return code, json.loads((output/'production-preflight.json').read_text())

    def test_scoped_pipeline_excludes_other_pages_and_never_claims_full_pass(self):
        code, report = self.scoped_entry()
        self.assertEqual(code, 0)
        self.assertEqual(report['selected_cases'], ['slot-a'])
        self.assertEqual(report['remaining_cases'], ['slot-b'])
        self.assertIsNone(report['full_art_passed'])
        self.assertFalse(report['receipt_written'])
        self.assertEqual(report['input_binding'], self.binding())

    def test_selected_page_other_problem_still_fails(self):
        code, report = self.scoped_entry(selected_page_problem=True)
        self.assertEqual(code, 1)
        self.assertTrue(report['pages']['findings'])

    def test_unselected_bad_production_asset_still_fails(self):
        code, report = self.scoped_entry(production_failed=True)
        self.assertEqual(code, 1)
        self.assertFalse(report['production']['passed'])

    def test_midcheck_source_change_invalidates_binding(self):
        code, report = self.scoped_entry(mutate_source=True)
        self.assertEqual(code, 1)
        self.assertFalse(report['input_binding']['available'])
        self.assertIn('changed during', report['error'])

    def test_cli_rejects_scope_outside_production_or_without_dumps(self):
        for options in ([], ['--production-only']):
            command = [sys.executable, '-B', str(HERE/'art_check.py'), '--project', str(self.project),
                       '--first-piece-case', 'slot-a', *options]
            proc = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn('requires --production-only and explicit --dumps', proc.stderr)


if __name__ == '__main__':
    unittest.main()
