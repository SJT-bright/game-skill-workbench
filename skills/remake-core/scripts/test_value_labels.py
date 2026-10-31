#!/usr/bin/env python3
"""Regression: level / score / currency values typed in one font label with their word (user 2026-10-30).

Saul's example was a result line "LEVEL 1 • +10 PEARLS" in white TTF on a translucent strip. font_number only looked at
labels that are digits alone, and docs/text/runtime-text.json waived font_text, so the mixed line passed every check.
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_check  # noqa: E402
import audit_page_richness as audit  # noqa: E402

DUMP = {'screen': 'result_win_iphone15', 'canvas_css': [0, 0, 393, 852], '_file': '/tmp/value-label/000-ui-dump-result.json'}


def label(path, value, font_kind='ttf', outline=True):
    lab = {'string': value, 'fontSize': 30, 'actualFontSize': 30, 'height': 40, 'font_kind': font_kind,
           'system_font': False, 'font': 'Fredoka-Bold.ttf' if font_kind == 'ttf' else 'pearl_digits.fnt',
           'color': [255, 255, 255]}
    if outline:
        lab['outline'] = {'color': [20, 40, 80], 'width': 2}
    return {'path': path, 'name': path.rsplit('/', 1)[-1], 'rect': [0.1, 0.4, 0.8, 0.05], 'comps': {'label': lab}}


def codes(nodes, runtime=()):
    previous = audit.RUNTIME_TEXT
    try:
        audit.RUNTIME_TEXT = list(runtime)
        return [p.split(':', 1)[0] for p in audit.text_problems(DUMP, nodes, [], None)]
    finally:
        audit.RUNTIME_TEXT = previous


class ValueLabelTests(unittest.TestCase):
    def test_mixed_result_line_listed_as_runtime_text_is_caught(self):
        n = label('Canvas/Result/RewardLine', 'LEVEL 1 • +10 PEARLS')
        self.assertIn('font_value_label', codes([n], runtime=['Canvas/Result/RewardLine']))

    def test_hud_level_and_coin_labels_are_caught(self):
        for value in ('LEVEL 1', 'Coins 120', '+10 PEARLS', '40 EGGS', 'BEST 1200', '3/5 STARS', 'x2 COINS',
                      'Lv.3', 'Score: 300', 'Level 12 / 70', 'Stage 3 of 10'):
            with self.subTest(value=value):
                self.assertIn('font_value_label', codes([label('Canvas/Hud/Value', value)], runtime=['Canvas/Hud/Value']))

    def test_lines_from_rejected_screenshots_are_caught(self):
        # Mosslight Ferry 10-21, Meadow Match 10-22 / 10-23 / 10-26, StarPop 10-26: all typed, all sent back
        for value in ('POOL 3  /  The side pocket', '0 DEW  ·  0 HINT TOKENS', '5 / 72 lights  ·  3 / 24 pools',
                      'RANK 9469  ·  0 POINTS', '50 COINS', '+50 COINS', '18 / 18 harvested', 'INVENTORY  0',
                      'Chapter 2 / 13-24'):
            with self.subTest(value=value):
                self.assertIn('font_value_label', codes([label('Canvas/Home/Line', value)], runtime=['Canvas/Home/Line']))
        for value in ('3 / 5', 'Reach 200 points / Clear 3 rows', 'Tap / Drag', 'Watch a full ad to receive 1 HAMMER.'):
            with self.subTest(value=value):
                self.assertNotIn('font_value_label', codes([label('Canvas/Home/Line', value)], runtime=['Canvas/Home/Line']))

    def test_richtext_value_line_is_caught(self):
        n = {'path': 'Canvas/Result/Rich', 'name': 'Rich', 'rect': [0.1, 0.4, 0.8, 0.05],
             'comps': {'richtext': {'string': '<color=#ffffff>LEVEL</color> 2 · <b>+20</b> COINS'}}}
        self.assertIn('font_value_label', codes([n]))

    def test_bitmap_digits_sentences_names_and_pure_numbers_are_not_this_rule(self):
        self.assertNotIn('font_value_label', codes([label('Canvas/Hud/Coins', 'Coins 120', font_kind='bitmap')]))
        for value in ('Reach 200 points', 'Merge 5 512 tiles', 'Ends in 02:30', 'CozyWaffle85', 'v1.0', '+10',
                      'Level Complete!', 'Clear 3 rows to win the round'):
            with self.subTest(value=value):
                self.assertNotIn('font_value_label', codes([label('Canvas/Hint/Text', value)], runtime=['Canvas/Hint/Text']))

    def test_pure_number_still_reports_font_number(self):
        self.assertIn('font_number', codes([label('Canvas/Hud/Coins', '120')]))

    def test_flat_colour_box_of_any_colour_behind_a_value_is_reported(self):
        coins = label('Canvas/Hud/CoinBar/Value', '120', font_kind='bitmap')
        coins['rect'] = [0.62, 0.05, 0.12, 0.04]
        beige = {'path': 'Canvas/Hud/CoinBar', 'name': 'CoinBar', 'rect': [0.55, 0.04, 0.3, 0.06],
                 'comps': {'graphics': {'fillColor': [240, 228, 200, 255], 'lineWidth': 0}}}
        blue = {'path': 'Canvas/Hud/CoinBar', 'name': 'CoinBar', 'rect': [0.55, 0.04, 0.3, 0.06],
                'comps': {'sprite': {'frame': 'default_sprite_splash', 'frame_size': [2, 2], 'color': [40, 90, 200]}}}
        for plate in (beige, blue):
            with self.subTest(plate=plate['comps']):
                self.assertTrue(any(p.startswith('flat_value_plate:') for p in audit.flat_value_plate_problems([plate, coins])))

    def test_generated_plate_picture_faint_tint_and_full_screen_backdrop_are_fine(self):
        coins = label('Canvas/Hud/CoinBar/Value', 'LEVEL 3', font_kind='bitmap')
        coins['rect'] = [0.62, 0.05, 0.12, 0.04]
        picture = {'path': 'Canvas/Hud/CoinBar', 'name': 'CoinBar', 'rect': [0.55, 0.04, 0.3, 0.06],
                   'comps': {'sprite': {'frame': 'plate_shell_pearl', 'frame_size': [600, 120], 'color': [255, 255, 255]}}}
        tint = {'path': 'Canvas/Hud/Tint', 'name': 'Tint', 'rect': [0.55, 0.04, 0.3, 0.06],
                'comps': {'graphics': {'fillColor': [0, 0, 0, 60]}}}
        backdrop = {'path': 'Canvas/Bg', 'name': 'Bg', 'rect': [0, 0, 1, 1],
                    'comps': {'sprite': {'frame': 'default_sprite_splash', 'frame_size': [2, 2], 'color': [30, 30, 60]}}}
        self.assertEqual(audit.flat_value_plate_problems([picture, tint, backdrop, coins]), [])

    def test_version_credits_and_original_notes_are_dev_info(self):
        for value in ('Fruit Escape • v1.3.0', 'Version 1.0.0', 'v1.0.0', 'CREDITS', 'Original art by the source game',
                      'Made with GPT', 'Fonts license: SIL OFL', 'Original game audio is preserved.'):
            with self.subTest(value=value):
                self.assertIn('dev_info_text', codes([label('Canvas/Settings/Info', value)]))
        # CREDITS as a space game's currency in the HUD / store is not the banned Credits page
        for path in ('Game/Canvas/GameplayHUD/Credits/Label', 'Game/Canvas/Modal-store/UpgradeCredits/Label'):
            with self.subTest(path=path):
                self.assertNotIn('dev_info_text', codes([label(path, 'CREDITS')]))
        self.assertNotIn('dev_info_text', codes([label('Canvas/Ad/Text', 'Watch a complete video to receive the original game reward')]))
        # edition notes and test leftovers (冲吧柯基 10-24, Meadow Match 10-23 / 10-26)
        for value in ('CORGI RUSH • English Edition', 'SIMULATED · Computer rivals', 'TEST REWARD', 'Test Ad · Web Preview',
                      '模拟广告'):
            with self.subTest(value=value):
                self.assertIn('dev_info_text', codes([label('Canvas/Settings/Info', value)]))
        for value in ('Test your luck', '智力测试'):
            with self.subTest(value=value):
                self.assertNotIn('dev_info_text', codes([label('Canvas/Home/Line', value)]))
        for value in ('v11 / sdk-missing', 'V9', 'V25 INPUT READY'):
            with self.subTest(value=value):
                self.assertIn('dev_info_text', codes([label('Canvas/Debug/Tag', value)]))
        for value in ('280 CREDITS', 'LEVEL 2', 'Version', 'Lv9', 'LV 3', 'x2', 'VS'):
            with self.subTest(value=value):
                self.assertNotIn('dev_info_text', codes([label('Canvas/Hud/Credits', value)]))

    def test_recorded_frames_next_to_dumps_are_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp) / 'home-taps' / 'frames'
            frames.mkdir(parents=True)
            (frames / '00001_0000040ms.jpg').write_bytes(b'')
            (Path(tmp) / 'loose.jpg').write_bytes(b'')
            self.assertEqual(art_check.recorded_frame_dirs(tmp), [frames])

    def test_art_check_counts_it_as_fixed_text_still_typed(self):
        findings = audit.text_problems(DUMP, [label('Canvas/Result/RewardLine', 'LEVEL 1 • +10 PEARLS')], [], None)
        report = {'pages': [{'screen': 'result_win_iphone15', 'problems': findings}]}
        caught = art_check.fixed_text_inventory_findings(report)
        self.assertTrue(any('font_value_label' in c for c in caught), caught)
        self.assertIn('font_value_label', art_check.ONE_PIECE_KINDS)


if __name__ == '__main__':
    unittest.main()
