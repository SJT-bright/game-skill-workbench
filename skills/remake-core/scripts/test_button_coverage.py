#!/usr/bin/env python3
"""Self-tests for audit_button_coverage.py (INPUT-05, user 2026-10-22): the button list comes from the game's dumps,
every button must be tapped and the screen must change after the tap. Synthetic chrome_touch runs built from the
mock Cocos scenes; a complete run passes, a missed button and a dead button fail."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NODE = shutil.which('node')
sys.path.insert(0, str(HERE))
from test_ui_layout_and_copy import mock_dump  # noqa: E402

SCENES = [('good_home', 'home'), ('good_result', 'result_win'), ('good_result', 'result_fail'),
          ('good_result', 'result_win_repeat'), ('good_result', 'result_fail_repeat'), ('settings', 'settings'),
          ('settings_sound', 'settings_sound'), ('play', 'other')]


def picture(path, seed):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (375, 812), (150, 210, 250))
    ImageDraw.Draw(im).rectangle([20 + (seed * 37) % 300, 40 + (seed * 53) % 700, 80 + (seed * 37) % 300, 100 + (seed * 53) % 700],
                                 fill=((seed * 70) % 255, (seed * 130) % 255, (seed * 190) % 255))
    im.save(path)


def build_run(root, skip_button=None, dead_button=None, offset=False, reentry_bug=False):
    run = root / 'docs/test/run-iphone15'
    run.mkdir(parents=True)
    steps, seed = [], 1
    for n, (scene, purpose) in enumerate(SCENES):
        i = len(steps)
        f = mock_dump(run, 3, ('offset_' if offset and purpose == 'home' else '') + scene)
        d = json.loads(f.read_text())
        f.unlink()
        screen = '%s_%d' % (scene, n)
        d.update(screen=screen, purpose=purpose, kind={'good_home': 'home', 'play': 'gameplay'}.get(scene, 'popup'))
        if reentry_bug and purpose == 'result_win_repeat':     # 指尖麻将 v55: second open re-sorted the mask on top
            for x in d['nodes']:
                if x['comps'].get('block_input'):
                    x['order'] = max(y['order'] for y in d['nodes']) + 1
        (run / ('%03d-ui-dump-%s.json' % (i, screen))).write_text(json.dumps(d))
        picture(run / ('%03d-ui-%s.png' % (i, screen)), seed); seed += 1
        steps.append({'label': 'ui-' + screen, 'action': {'type': 'dump_ui', 'screen': screen, 'kind': d['kind'], 'purpose': purpose}})
        nodes = [x for x in d['nodes'] if 'button' in x['comps']]
        top = max((x['order'] for x in d['nodes'] if x['comps'].get('block_input')), default=-1)
        for b in nodes:
            if b['order'] < top or b['name'] == skip_button:
                continue
            r = b.get('screen') or b['rect']                  # tap where the button is drawn
            i = len(steps)
            steps.append({'label': 'tap', 'action': {'type': 'tap', 'x': (r[0] + r[2] / 2) * 375, 'y': (r[1] + r[3] / 2) * 812}})
            if b['name'] == dead_button or (offset and purpose == 'home'):   # the game still hit-tests the layout position
                shutil.copy(sorted(run.glob('%03d-*.png' % (i - 1)))[0], run / ('%03d-tap.png' % i))
            else:
                picture(run / ('%03d-tap.png' % i), seed); seed += 1
    (run / 'report.json').write_text(json.dumps({'device': 'iphone_15', 'steps': steps}))
    return run


@unittest.skipUnless(NODE, 'node not installed')
class ButtonCoverageTests(unittest.TestCase):
    def project(self, **kw):
        root = Path(tempfile.mkdtemp(prefix='buttons-'))
        self.addCleanup(shutil.rmtree, root, True)
        (root / 'assets').mkdir()
        build_run(root, **kw)
        return root

    def audit(self, root):
        out = root / 'r.json'
        r = subprocess.run([sys.executable, '-B', str(HERE / 'audit_button_coverage.py'), '--project', str(root), '--out', str(out),
                            '--md', str(root / 'list.md')], capture_output=True, text=True)
        return r.returncode, json.loads(out.read_text()), (root / 'list.md').read_text()

    def test_every_button_tapped_passes_and_lists_them(self):
        code, r, md = self.audit(self.project())
        self.assertEqual(code, 0, r['problems'])
        self.assertGreaterEqual(r['buttons'], 15)
        self.assertEqual(r['devices'], ['iphone_15'])
        self.assertIn('BtnSettings', md)

    def test_missed_button_fails(self):
        code, r, md = self.audit(self.project(skip_button='BtnRetry'))
        self.assertEqual(code, 1)
        self.assertIn('never tapped', ' '.join(r['problems']))
        self.assertIn('没点过', md)

    def test_dead_button_fails(self):
        code, r, md = self.audit(self.project(dead_button='BtnSkins'))
        self.assertEqual(code, 1)
        self.assertIn('点了没反应', ' '.join(r['problems']))

    def test_camera_offset_is_caught(self):
        # user 2026-10-22: camera offset -> buttons look fine but the tap (where the player sees them) does nothing
        code, r, md = self.audit(self.project(offset=True))
        self.assertEqual(code, 1)
        text = ' '.join(r['problems'])
        self.assertIn('camera_offset', text)
        self.assertIn('点了没反应', text)

    def test_skip_needs_a_reason(self):
        root = self.project(skip_button='BtnRevisit')
        (root / 'docs/test/button-skip.json').write_text(json.dumps([{'screen': 'good_home_0', 'path': 'Canvas/BtnRevisit',
                                                                      'reason': 'opens the TikTok profile; explanation popup checked'}]))
        self.assertEqual(self.audit(root)[0], 0)
        (root / 'docs/test/button-skip.json').write_text(json.dumps([{'screen': 'good_home_0', 'path': 'Canvas/BtnRevisit', 'reason': ''}]))
        self.assertEqual(self.audit(root)[0], 1)

    def test_buttons_under_a_popup_mask_are_not_required(self):
        code, r, md = self.audit(self.project())
        under = [x for x in r['rows'] if x['screen'].startswith('settings') and x['path'].startswith('Canvas/Btn') and
                 not x['path'].startswith('Canvas/Panel')]
        self.assertEqual(under, [])

    def test_reentry_mask_over_own_buttons_fails(self):
        # INPUT-05 re-open, 指尖麻将 v55: result page opened a second time, its mask now above Claim/Bonus -> taps swallowed
        code, r, md = self.audit(self.project(reentry_bug=True))
        self.assertEqual(code, 1)
        text = ' '.join(r['problems'])
        self.assertIn('INPUT-05 re-open', text)
        self.assertIn('Canvas/Panel/BtnDouble', text)

    def test_missing_reentry_dump_fails(self):
        root = self.project()
        rep = root / 'docs/test/run-iphone15/report.json'
        data = json.loads(rep.read_text())
        data['steps'] = [s for s in data['steps'] if s['action'].get('purpose') != 'result_win_repeat']
        rep.write_text(json.dumps(data))
        code, r, md = self.audit(root)
        self.assertEqual(code, 1)
        self.assertIn('result_win_repeat', ' '.join(r['problems']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
