"""First-piece wiring regressions; synthetic fixtures, never ART receipt evidence."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import art_preflight as preflight


def node(path, rect, **comps):
    return dict(path=path, name=path.rsplit('/', 1)[-1], order=1,
                opacity=1, rect=rect, comps=comps)


class FirstPiece(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root/'project'
        (self.project/'assets/font').mkdir(parents=True)
        self.dumps = self.root/'dumps'
        self.dumps.mkdir()
        self.out = self.root/'out'
        self.out.mkdir()

    def dump(self, name='sample', kind='page', purpose='page', nodes=None):
        data = dict(tool='ui_dump', schema=1, producer='chrome_touch.dump_ui',
                    screen=name, kind=kind, purpose=purpose,
                    page=dict(width=400, height=800, dpr=1),
                    viewport=dict(width=400, height=800), canvas_css=[0, 0, 400, 800],
                    nodes=nodes or [], settle=dict(labels=0, layouts=0, moved=0))
        path = self.dumps/('ui-dump-'+name+'.json')
        path.write_text(json.dumps(data))
        return dict(data, _file=str(path))

    def layout(self, docs, **kwargs):
        return preflight._layout_preflight(self.project, docs, self.out, **kwargs)

    def home(self):
        return self.dump('home', 'home', 'home', [
            node('Canvas/Play', [.3, .7, .4, .08], button=dict(interactable=True))])

    def test_partial_popup_does_not_require_whole_game_or_claim_layout_pass(self):
        popup = self.dump('reward', 'popup', 'reward', [
            node('Canvas/Popup', [.1, .2, .8, .5], sprite=dict(frame='panel'))])
        result = self.layout([popup], board='localize')
        self.assertEqual(result['status'], 'not_run')
        self.assertIsNone(result['passed'])
        self.assertFalse(result['geometry_checked'])
        self.assertTrue(result['extraction']['passed'])
        self.assertIn('gameplay', result['remaining'])
        self.assertFalse((self.out/'ui_coverage.json').exists())

    def test_declared_home_as_generic_page_is_rejected_before_full_capture(self):
        home = self.dump('home', 'page', 'home', [
            node('Canvas/Play', [.3, .7, .4, .08], button=dict(interactable=True))])
        result = self.layout([home], board='localize')
        self.assertFalse(result['passed'])
        self.assertIn('declared home', result['extraction']['errors'][0]['error'])

    def test_home_without_live_buttons_is_an_adapter_failure(self):
        result = self.layout([self.dump('home', 'home', 'home')])
        self.assertFalse(result['passed'])
        self.assertFalse(result['extraction']['passed'])

    def test_bad_popup_extraction_is_not_hidden_by_partial_coverage(self):
        result = self.layout([self.dump('reward', 'popup', 'reward')])
        self.assertFalse(result['passed'])
        self.assertIn('no popup found', result['extraction']['errors'][0]['error'])

    def test_linked_home_pages_outside_first_piece_are_explicitly_remaining(self):
        (self.project/'docs').mkdir()
        (self.project/'docs/ui-layout-overrides.json').write_text(json.dumps(
            dict(home_entry_pages=['settings'])))
        result = self.layout([self.home()])
        self.assertEqual(result['status'], 'not_run')
        self.assertIsNone(result['passed'])
        self.assertIn('settings', result['remaining'][0])

    def test_complete_representatives_use_formal_cli_board_and_rules(self):
        docs = [self.home(), self.dump('run', 'gameplay', 'gameplay', [
            node('Canvas/Pause', [.9, .02, .07, .04], button=dict(interactable=True))])]
        result = self.layout(docs, board='localize')
        self.assertTrue(result['geometry_checked'])
        self.assertEqual(result['coverage']['board'], 'localize')
        self.assertEqual(result['coverage']['provenance'], 'runtime_dump')
        self.assertFalse(result['passed'])  # missing existing required HOME entries
        messages = str(result['coverage']['results'])
        self.assertIn('desktop-shortcut', messages)
        self.assertEqual(result['coverage']['max_ui'], .20)
        self.assertEqual(result['coverage']['min_pad'], 8)

    def test_layout_checker_error_cannot_pass(self):
        docs = [self.home(), self.dump('run', 'gameplay', 'gameplay')]
        with mock.patch.object(preflight.subprocess, 'run', return_value=
                               subprocess.CompletedProcess([], 2, '', 'broken checker')):
            result = self.layout(docs, board='localize')
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['passed'])
        self.assertFalse(result['geometry_checked'])

    def text_overflow(self):
        # Existing text-fit bitmap rule, without a system-font approximation.
        font = '\n'.join(['info face="Digits" size=100', 'common lineHeight=100',
                           'page id=0 file="num.png"'] + [
            'char id=%d x=0 y=0 width=80 height=100 xoffset=0 yoffset=0 xadvance=106 page=0 chnl=15' % (48+i)
            for i in range(10)])
        (self.project/'assets/font/num.fnt').write_text(font)
        return self.dump('reward', nodes=[
            node('Canvas/LetterLayer/ui/award/propItem/bg', [123/400, 425/800, 66/400, 66/800],
                 sprite=dict(frame='propbg1')),
            node('Canvas/LetterLayer/ui/award/propItem/num', [109/400, 470/800, 72/400, 18/800],
                 label=dict(string='10000', fontSize=32, actualFontSize=32, width=165, height=40,
                            overflow=2, font='num', font_kind='bitmap', spacingX=-2, color=[255, 255, 255]))
            | dict(order=2)])

    def test_real_text_checker_catches_value_outside_plate_in_first_piece(self):
        data = self.text_overflow()
        result = preflight._text_preflight(self.project, [Path(data['_file'])], self.out)
        self.assertFalse(result['passed'])
        self.assertEqual(result['checked'], 1)
        self.assertIn('text_outside_plate', {f['kind'] for f in result['findings']})
        self.assertTrue((self.out/'text-plan.md').is_file())

    def test_text_checker_exception_cannot_pass(self):
        import audit_text_fit
        with mock.patch.object(audit_text_fit, 'audit', side_effect=RuntimeError('numpy child failed')):
            result = preflight._text_preflight(self.project, [], self.out)
        self.assertFalse(result['passed'])
        self.assertEqual(result['status'], 'error')

    def test_production_entry_runs_text_and_layout_without_receipt(self):
        import art_production
        data = self.text_overflow()
        real_run = subprocess.run
        def pages(cmd, **kwargs):
            # Only replace the pixel-page command. numpy capability probes and
            # audit_text_fit's numpy child must execute with their real interpreter.
            if not any(Path(str(arg)).name == 'audit_page_richness.py' for arg in cmd):
                return real_run(cmd, **kwargs)
            Path(cmd[cmd.index('--out')+1]).write_text(json.dumps(dict(
                checked=1, setup=[], pages=[dict(problems=[])], missing=['gameplay'])))
            return subprocess.CompletedProcess(cmd, 1, '', '')
        with mock.patch.object(art_production, 'audit', return_value=
                               dict(passed=True, declared=False, assets=[])), \
             mock.patch.object(preflight.subprocess, 'run', side_effect=pages), \
             contextlib.redirect_stdout(io.StringIO()):
            code = preflight.run(self.project, self.dumps, self.root/'entry', board='localize')
        result = json.loads((self.root/'entry/production-preflight.json').read_text())
        self.assertEqual(code, 1)
        self.assertFalse(result['text']['passed'])
        self.assertIsNone(result['layout']['passed'])
        self.assertFalse(result['runtime_verified'])
        self.assertFalse(result['receipt_written'])
        self.assertFalse((self.project/'.tiktok-kit/art-receipt.json').exists())
        self.assertEqual(json.loads(Path(data['_file']).read_text())['kind'], 'page')


if __name__ == '__main__':
    unittest.main()
