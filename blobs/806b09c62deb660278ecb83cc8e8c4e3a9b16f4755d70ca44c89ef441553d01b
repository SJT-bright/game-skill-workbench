#!/usr/bin/env python3
"""P20 (问题普查 20261104 T20): the check tools themselves. Each case is a real survey failure, run in seconds:

  help_*        --help printed usage instead of crashing (probe_cocos2_touch_coordinates.cjs: "Unexpected end of JSON
                input", 11-03; check_button_group.py opened "--help" as a file)
  noinput_*     no input is "not_run" (exit 2), never exit 0 / a pass (check_button_group.py printed [] exit 0)
  nopil_*       a missing Pillow is a not_run line, --help still works (was a Traceback)
  same_name     a text under the 2nd of two same-name plates gets that plate as container (这也太牛了: 178 false
                overflow blocks, 11-04)
  zero_items    0 dumps / 0 sprites is not_run, not pass (蛋壳特工队 3.8.8: 0 items checked and not blocked)
  one_board     art_check / design_check / audit_glyph_core read the board only through feature_policy.board_of;
                an English game recorded in .tiktok-kit/policy.json is localize for all of them

Run: python3 test_check_guard.py   (set J1_TREE=<unpacked skill tree> to run the same cases on another tree)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TREE = Path(os.environ.get('J1_TREE') or Path(__file__).resolve().parents[3])
CORE = TREE / 'remake-core' / 'scripts'
ART = TREE / 'remake-art' / 'scripts'
NODE = shutil.which('node')


def run(cmd, stdin='', env=None):
    p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=60, env=env)
    return p.returncode, p.stdout + p.stderr


def no_pil(script, *args):
    """Run a script as if Pillow were not installed (sys.modules['PIL'] = None makes every PIL import fail)."""
    code = ('import runpy,sys;sys.modules["PIL"]=None;sys.argv=%r;sys.path.insert(0,%r);'
            'runpy.run_path(%r,run_name="__main__")' % ([str(script)] + list(args), str(Path(script).parent), str(script)))
    return run([sys.executable, '-B', '-c', code])


def last_json(text):
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    try:
        return json.loads(text)
    except ValueError:
        return {}


@unittest.skipUnless(NODE, 'node not installed')
class NodeProbes(unittest.TestCase):
    PROBES = ['probe_cocos2_touch_coordinates.cjs', 'probe_cocos3_touch_coordinates.cjs', 'scan_runtime_resources.cjs',
              'scan_input_ownership.cjs', 'parse_package_requires.cjs', 'probe_native_bootstrap.cjs',
              'probe_cocos2_reward_storage.cjs']

    def test_help(self):
        for name in self.PROBES:
            code, out = run([NODE, str(CORE / name), '--help'])
            self.assertEqual(code, 0, '%s --help: %s' % (name, out[-300:]))
            self.assertIn('Usage', out, name)

    def test_noinput_is_not_run(self):
        for name in ('probe_cocos2_touch_coordinates.cjs', 'probe_cocos3_touch_coordinates.cjs', 'scan_runtime_resources.cjs',
                     'scan_input_ownership.cjs'):
            code, out = run([NODE, str(CORE / name)], stdin='')
            self.assertEqual(code, 2, '%s empty stdin: %s' % (name, out[-300:]))
            self.assertEqual(last_json(out).get('status'), 'not_run', name)


class PythonEntries(unittest.TestCase):
    def test_button_group_help_and_noinput(self):
        code, out = run([sys.executable, '-B', str(ART / 'check_button_group.py'), '--help'])
        self.assertEqual(code, 0, out[-300:])
        self.assertNotIn('Traceback', out)
        code, out = run([sys.executable, '-B', str(ART / 'check_button_group.py')])
        self.assertEqual(code, 2, 'no capture must be not_run, got: ' + out[-200:])
        self.assertEqual(last_json(out).get('status'), 'not_run')

    def test_nopil_help_and_not_run(self):
        for script in (CORE / 'audit_atlas_slices.py', CORE / 'check_text_backplates.py', ART / 'cut_sheet_frame.py',
                       ART / 'compose_fixed_button.py', ART / 'check_collection_preview.py'):
            code, out = no_pil(script, '--help')
            self.assertEqual(code, 0, '%s --help without Pillow: %s' % (script.name, out[-300:]))
            self.assertNotIn('Traceback', out, script.name)
            code, out = no_pil(script, 'x')
            self.assertEqual(code, 2, '%s without Pillow: %s' % (script.name, out[-300:]))
            self.assertEqual(last_json(out).get('status'), 'not_run', script.name)


def node(path, nid, ancestors, rect, comps):
    return {'path': path, 'id': nid, 'ancestor_ids': ancestors, 'name': path.rsplit('/', 1)[-1], 'rect': rect,
            'opacity': 1, 'comps': comps}


class Identity(unittest.TestCase):
    def test_same_name_container(self):
        # 这也太牛了 r36: the wave count "hhnum" sits on the 2nd "bg" plate; the 1st "bg" is a small round badge.
        nodes = [node('Canvas', 'c', [], [0, 0, 400, 800], {}),
                 node('Canvas/Top', 't', ['c'], [0, 0, 400, 120], {}),
                 node('Canvas/Top/bg', 'b1', ['t', 'c'], [10, 10, 40, 40], {'sprite': {'frame': 'badge'}}),
                 node('Canvas/Top/bg', 'b2', ['t', 'c'], [10, 60, 160, 40], {'sprite': {'frame': 'plate'}}),
                 node('Canvas/Top/bg/hhnum', 'n', ['b2', 't', 'c'], [20, 65, 120, 30],
                      {'label': {'string': 'WAVE 12/40', 'fontSize': 24}})]
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / 'home-ui-dump-390x844.json'
            dump.write_text(json.dumps({'tool': 'ui_dump', 'screen': 'home', 'canvas_css': [400, 800], 'nodes': nodes}))
            sys.path.insert(0, str(CORE))
            try:
                import importlib
                acq = importlib.import_module('audit_copy_quality')
                rows, _ = acq.runtime_strings([dump])
            finally:
                sys.path.remove(str(CORE))
                sys.modules.pop('audit_copy_quality', None)
        row = next(r for r in rows if r['text'].startswith('WAVE'))
        self.assertEqual(row['container'], [10, 60, 160, 40], 'container must be the plate the text is under (b2)')


class ZeroItems(unittest.TestCase):
    def project(self, tmp, engine='3.8.8'):
        p = Path(tmp) / 'p'
        (p / 'assets').mkdir(parents=True)
        (p / 'docs' / 'test').mkdir(parents=True)
        (p / 'package.json').write_text(json.dumps({'creator': {'version': engine}}))
        return p

    def test_copy_quality_no_text_is_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            code, out = run([sys.executable, '-B', str(CORE / 'audit_copy_quality.py'), '--project', str(p),
                             '--out', str(Path(tmp) / 'c.json')])
            self.assertEqual(code, 2, out[-300:])
            self.assertEqual(json.loads((Path(tmp) / 'c.json').read_text())['status'], 'not_run')

    def test_clarity_3x_zero_sprites_is_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(tmp)
            code, out = run([sys.executable, '-B', str(CORE / 'audit_image_clarity.py'), '--project', str(p),
                             '--out', str(Path(tmp) / 'cl.json')])
            self.assertEqual(code, 2, out[-300:])
            rep = json.loads((Path(tmp) / 'cl.json').read_text())
            self.assertEqual((rep['status'], rep['engine']['major']), ('not_run', 3))


class OneBoard(unittest.TestCase):
    def test_board_read_only_through_feature_policy(self):
        for name in ('art_check.py', 'design_check.py', 'audit_glyph_core.py'):
            text = (CORE / name).read_text(encoding='utf-8')
            self.assertNotIn("'board.txt'", text, '%s reads docs/board.txt itself' % name)
            self.assertIn('feature_policy.board_of', text, name)

    def test_tiktok_kit_board_is_localize(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'p'
            (p / '.tiktok-kit').mkdir(parents=True)
            (p / '.tiktok-kit' / 'policy.json').write_text('{"board": "localize"}')
            sys.path.insert(0, str(CORE))
            try:
                import feature_policy
                self.assertEqual(feature_policy.board_of(p), ('localize', '.tiktok-kit/policy.json'))
                self.assertEqual(feature_policy.applies('remake_art_style', 'localize', p), 'not_applicable')
                (p / 'docs').mkdir()
                (p / 'docs' / 'art-style.txt').write_text('remake')
                self.assertEqual(feature_policy.applies('remake_art_style', 'localize', p), 'block')
                self.assertEqual(feature_policy.applies('small_value_font', None), 'block')
            finally:
                sys.path.remove(str(CORE))
                sys.modules.pop('feature_policy', None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
