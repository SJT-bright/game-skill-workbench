"""Formal remake entry checks; no browser, HTTP server or snapshot is started.

Successful UI callbacks are synthetic tool fixtures, never visual approval.
The real shared gate is exercised for six-family acceptance/refusal decisions.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ad_nodes_gate
import ad_standard_scope
import serve_preview


class OriginalFlowReached(Exception):
    """Stop at the original service/snapshot boundary, before any real effect."""


class FormalTrialEntry(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='ad-trial-entry-')
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name)
        (self.project / 'docs').mkdir()
        (self.project / 'docs/board.txt').write_text('remake')
        self.export = self.project / 'build/web'
        self.export.mkdir(parents=True)
        (self.export / 'index.html').write_text('<html>synthetic entry fixture</html>')
        self.slots = types.SimpleNamespace(sweep=Mock())
        self.snapshot = Mock(side_effect=OriginalFlowReached('snapshot'))
        self.server = Mock(side_effect=OriginalFlowReached('server'))
        self.browser = Mock()
        for patcher in (patch.dict(sys.modules, {'browser_slots': self.slots}),
                        patch.object(serve_preview, 'make_snapshot', self.snapshot),
                        patch.object(serve_preview, 'ThreadingHTTPServer', self.server),
                        patch.object(serve_preview, 'browser_request', self.browser)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.stderr = io.StringIO()
        capture = contextlib.redirect_stderr(self.stderr)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def args(self, *extra, project=True):
        return ['--directory', str(self.export), '--no-browser',
                *(['--project', str(self.project)] if project else []), *extra]

    def assert_no_effects(self):
        self.slots.sweep.assert_not_called()
        self.snapshot.assert_not_called()
        self.server.assert_not_called()
        self.browser.assert_not_called()

    def real_contract(self):
        spec = importlib.util.spec_from_file_location('ad_trial_gate_fixture', HERE / 'test_ad_nodes_gate.py')
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        fixture = fixtures.SharedGate()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.project = fixture.project
        (self.project / 'docs/board.txt').write_text('remake')
        self.export = self.project / 'build/web'
        (self.export / 'index.html').write_text('<html>synthetic six-family entry fixture</html>')
        def check(project, *, stage):
            return fixture.gate.check_project(project, stage=stage,
                                              art_stage_check=fixture.synthetic_ui_callback)
        return fixture, check

    def test_all_formal_flags_refuse_before_any_snapshot_service_or_browser_effect(self):
        for flags in (('--keep', '--snapshot'), ('--open',), ('--idle-minutes', '0')):
            with self.subTest(flags=flags), \
                    patch.object(ad_standard_scope, 'requirement', return_value={'required': True}) as scope, \
                    patch.object(ad_nodes_gate, 'check_project', return_value={
                        'passed': False, 'problems': ['missing standard family: trial']}) as gate:
                with self.assertRaises(SystemExit) as error:
                    serve_preview.main(self.args(*flags))
                self.assertEqual(error.exception.code, 1)
                scope.assert_called_once_with(self.project.resolve(), 'new')
                gate.assert_called_once_with(self.project.resolve(), stage='trial')
                self.assert_no_effects()
        self.assertIn('missing standard family: trial', self.stderr.getvalue())

    def test_missing_project_refuses_before_scope_or_side_effects(self):
        with patch.object(ad_standard_scope, 'requirement') as scope, \
                patch.object(ad_nodes_gate, 'check_project') as gate:
            with self.assertRaises(SystemExit) as error:
                serve_preview.main(self.args('--open', project=False))
            self.assertEqual(error.exception.code, 1)
            scope.assert_not_called()
            gate.assert_not_called()
            self.assert_no_effects()

    def test_internal_services_do_not_invoke_production_gate(self):
        with patch.object(ad_standard_scope, 'requirement') as scope, \
                patch.object(ad_nodes_gate, 'check_project') as gate:
            with self.assertRaises(OriginalFlowReached):
                serve_preview.main(self.args())
            scope.assert_not_called()
            gate.assert_not_called()
            self.server.assert_called_once()

    def test_owning_english_original_and_raw_paths_do_not_duplicate_gate(self):
        for kwargs, flags in (({'english_preview': True}, ('--open',)),
                              ({'chinese_original': True}, ('--open',)),
                              ({}, ('--raw', '--idle-minutes', '0'))):
            self.server.reset_mock()
            with self.subTest(kwargs=kwargs, flags=flags), \
                    patch.object(ad_standard_scope, 'requirement') as scope, \
                    patch.object(ad_nodes_gate, 'check_project') as gate:
                with self.assertRaises(OriginalFlowReached):
                    serve_preview.main(self.args(*flags), **kwargs)
                scope.assert_not_called()
                gate.assert_not_called()
                self.server.assert_called_once()

    def test_verified_maintenance_scope_preserves_original_flow(self):
        with patch.object(ad_standard_scope, 'requirement', return_value={'required': False}), \
                patch.object(ad_nodes_gate, 'check_project') as gate:
            with self.assertRaises(OriginalFlowReached):
                serve_preview.main(self.args('--open'))
            gate.assert_not_called()
            self.server.assert_called_once()

    def test_real_missing_standard_refuses_before_formal_side_effects(self):
        fixture, checker = self.real_contract()
        fixture.manifest['nodes'] = [node for node in fixture.manifest['nodes'] if node['kind'] != 'trial']
        fixture.persist()
        with patch.object(ad_nodes_gate, 'check_project', side_effect=checker):
            with self.assertRaises(SystemExit) as error:
                serve_preview.main(self.args('--keep', '--snapshot'))
            self.assertEqual(error.exception.code, 1)
            self.assert_no_effects()
        self.assertIn('trial', self.stderr.getvalue())

    def test_real_six_standard_with_synthetic_ui_callback_can_enter_original_snapshot_flow(self):
        fixture, checker = self.real_contract()
        with patch.object(ad_nodes_gate, 'check_project', side_effect=checker) as gate:
            with self.assertRaises(OriginalFlowReached):
                serve_preview.main(self.args('--keep', '--snapshot'))
            gate.assert_called_once_with(self.project.resolve(), stage='trial')
            self.snapshot.assert_called_once()
            self.server.assert_not_called()
            self.browser.assert_not_called()

    def test_unavailable_or_incomplete_gate_fails_closed(self):
        for outcome in (RuntimeError('missing same-bundle gate'), {'passed': True, 'problems': ['UI not current']}):
            with self.subTest(outcome=outcome), \
                    patch.object(ad_standard_scope, 'requirement', return_value={'required': True}), \
                    patch.object(ad_nodes_gate, 'check_project', **(
                        {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome})):
                with self.assertRaises(SystemExit) as error:
                    serve_preview.main(self.args('--open'))
                self.assertEqual(error.exception.code, 1)
                self.assert_no_effects()


if __name__ == '__main__':
    unittest.main()
