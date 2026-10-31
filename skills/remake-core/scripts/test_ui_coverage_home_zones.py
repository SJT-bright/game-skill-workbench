#!/usr/bin/env python3
"""Remake home zoning (user 2026-10-28): settings on the currency row, only Revisit + Add to Home below PLAY,
check-in beside the hero. Old layouts fail for their own reason; the new zoning passes; English keeps the old rule."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_ui_coverage as audit  # noqa: E402

SIZE = [390, 844]
PLAY = {'name': 'play', 'kind': 'gameplay', 'size': SIZE, 'elements': [{'name': 'pause', 'rect': [330, 14, 44, 44]}]}


def home(buttons, name='home_9x19'):
    return {'name': name, 'kind': 'page', 'role': 'home', 'size': SIZE, 'buttons': buttons}


TOP = [{'name': 'Canvas/Home/TopBar/CoinsPlus', 'rect': [150, 52, 40, 40]}]
PLAY_BTN = [{'name': 'Canvas/Home/BtnPlay', 'rect': [85, 640, 220, 64], 'primary': True, 'label': 'text'}]
SIDES = [{'name': 'Canvas/Home/BtnCheckIn', 'rect': [16, 400, 54, 54]},
         {'name': 'Canvas/Home/BtnGift', 'rect': [16, 470, 54, 54]},
         {'name': 'Canvas/Home/BtnMap', 'rect': [320, 400, 54, 54]},
         {'name': 'Canvas/Home/BtnSkins', 'rect': [320, 470, 54, 54]}]
BOTTOM = [{'name': 'Canvas/Home/BtnProfileRevisit', 'rect': [120, 760, 54, 54]},
          {'name': 'Canvas/Home/BtnAddToHome', 'rect': [216, 760, 54, 54]}]
SETTINGS_TOP = [{'name': 'Canvas/Home/BtnSettings', 'rect': [14, 50, 44, 44]}]
NEW = SETTINGS_TOP + TOP + PLAY_BTN + SIDES + BOTTOM

# old layouts from D1 acceptance
SETTINGS_BELOW_CAPSULE = [{'name': 'Canvas/Home/BtnSettings', 'rect': [326, 104, 44, 44]}] + TOP + PLAY_BTN + SIDES + BOTTOM
CHECKIN_BOTTOM = SETTINGS_TOP + TOP + PLAY_BTN + SIDES[1:] + BOTTOM + [
    {'name': 'Canvas/Home/BtnCheckIn', 'rect': [24, 760, 54, 54]}]
FOUR_BOTTOM = SETTINGS_TOP + TOP + PLAY_BTN + [SIDES[0], SIDES[2]] + BOTTOM + [
    {'name': 'Canvas/Home/BtnGift', 'rect': [24, 760, 54, 54]}, {'name': 'Canvas/Home/BtnSkins', 'rect': [312, 760, 54, 54]}]
ONE_SIDE = SETTINGS_TOP + TOP + PLAY_BTN + SIDES[:2] + BOTTOM


def run(buttons, *extra, project=None):
    with tempfile.TemporaryDirectory(prefix='home-zones-') as temp:
        f = Path(temp) / 'ui-layout.json'
        f.write_text(json.dumps({'screens': [PLAY, home(buttons)]}))
        cmd = [sys.executable, '-B', str(HERE / 'audit_ui_coverage.py'), str(f), '--rules-selftest', *extra]
        if project:
            cmd += ['--project', str(project)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


class RemakeHomeZones(unittest.TestCase):
    def test_new_zoning_passes(self):
        code, out = run(NEW, '--board', 'remake')
        self.assertEqual(code, 0, out)

    def test_settings_below_capsule_fails(self):
        code, out = run(SETTINGS_BELOW_CAPSULE, '--board', 'remake')
        self.assertEqual(code, 1, out)
        self.assertIn('home_zone_settings_row', out)
        self.assertNotIn('home_zone_below_play', out)

    def test_settings_without_resource_bar_button_uses_capsule_row(self):
        no_bar = [b for b in NEW if b not in TOP]
        self.assertEqual(run(no_bar, '--board', 'remake')[0], 0)
        low = [dict(b, rect=[14, 110, 44, 44]) if 'Settings' in b['name'] else b for b in no_bar]
        code, out = run(low, '--board', 'remake')
        self.assertEqual(code, 1)
        self.assertIn('home_zone_settings_row', out)

    def test_settings_top_right_fails(self):
        right = [dict(b, rect=[330, 50, 44, 44]) if 'Settings' in b['name'] else b for b in NEW]
        code, out = run(right, '--board', 'remake')
        self.assertEqual(code, 1)
        self.assertIn('top-left', out)

    def test_checkin_in_bottom_row_fails(self):
        code, out = run(CHECKIN_BOTTOM, '--board', 'remake')
        self.assertEqual(code, 1, out)
        self.assertIn('home_zone_checkin_bottom', out)

    def test_four_bottom_items_fail(self):
        code, out = run(FOUR_BOTTOM, '--board', 'remake')
        self.assertEqual(code, 1, out)
        self.assertEqual(out.count('home_zone_below_play'), 2, out)

    def test_both_sides_still_required(self):
        code, out = run(ONE_SIDE, '--board', 'remake')
        self.assertEqual(code, 1)
        self.assertIn('each side of the hero', out)

    def test_english_keeps_old_rule(self):
        for layout in (SETTINGS_BELOW_CAPSULE, CHECKIN_BOTTOM, FOUR_BOTTOM):
            code, out = run(layout, '--board', 'localize')
            self.assertEqual(code, 0, out)
            self.assertNotIn('home_zone_', out)

    def test_board_from_project(self):
        with tempfile.TemporaryDirectory(prefix='home-proj-') as temp:
            proj = Path(temp)
            (proj / 'assets').mkdir()
            self.assertEqual(run(FOUR_BOTTOM, project=proj)[0], 1)          # no docs/board.txt: strictest (remake)
            (proj / 'docs').mkdir()
            (proj / 'docs' / 'board.txt').write_text('localize\n')
            self.assertEqual(run(FOUR_BOTTOM, project=proj)[0], 0)
            (proj / 'docs' / 'board.txt').write_text('remake\n')
            self.assertEqual(run(FOUR_BOTTOM, project=proj)[0], 1)

    def test_spaced_platform_names_are_recognised(self):
        # 农场水渠 real names: "Action-ADD TO HOME SCREEN" is the shortcut, not a stray feature
        spaced = [dict(b, name='Canvas/Home/Action-ADD TO HOME SCREEN') if 'AddToHome' in b['name'] else b for b in NEW]
        self.assertEqual(run(spaced, '--board', 'remake')[0], 0)

    def test_function_reports_ids(self):
        problems = []
        audit.home_zones_remake('h', [b for b in CHECKIN_BOTTOM if not b.get('primary')], SIZE, problems, 672 / 844)
        self.assertTrue(problems and all(p.split(':')[0].startswith('home_zone_') for p in problems), problems)


if __name__ == '__main__':
    unittest.main()
