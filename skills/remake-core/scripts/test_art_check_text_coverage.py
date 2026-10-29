#!/usr/bin/env python3
"""Regression tests for the Weekly League typed-text miss and incomplete art rounds."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art_check  # noqa: E402
import audit_page_richness as audit  # noqa: E402


class ArtCheckCoverageTests(unittest.TestCase):
    def test_legacy_league_labels_are_detected_as_fixed_words_and_numbers(self):
        strings = [
            ('League title', 'WEEKLY LEAGUE'),
            ('League subtitle', 'SIMULATED · Computer rivals'),
            ('League rank', 'RANK 9469 · 0 POINTS'),
            ('League row rank', '9468'),
            ('League player', 'You'),
            ('League footer', 'Bronze · Ends Monday'),
        ]
        nodes = []
        for index, (name, value) in enumerate(strings):
            nodes.append({
                'path': 'GameRoot/' + name,
                'name': name,
                'rect': [0.1, 0.1 + index * 0.08, 0.8, 0.06],
                'comps': {'label': {'string': value, 'fontSize': 32, 'actualFontSize': 32,
                                    'height': 40, 'font_kind': 'ttf', 'system_font': False,
                                    'color': [65, 75, 50]}},
            })
        findings = audit.text_problems({'screen': 'league_iphone15', 'canvas_css': [0, 0, 393, 852],
                                        '_file': '/tmp/legacy-league/000-ui-dump-league.json'},
                                       nodes, [], None)
        page_report = {'pages': [{'screen': 'league_iphone15', 'problems': findings}]}
        caught = art_check.fixed_text_inventory_findings(page_report)
        self.assertTrue(any('font_text' in item and 'WEEKLY LEAGUE' in item for item in caught), caught)
        self.assertTrue(any('font_number' in item and '9468' in item for item in caught), caught)
        self.assertGreaterEqual(len(caught), 6, caught)

    def test_dynamic_rival_name_can_be_allowlisted_without_waiving_fixed_labels(self):
        previous = audit.RUNTIME_TEXT
        try:
            audit.RUNTIME_TEXT = ['*League rival name *']
            n = {'path': 'GameRoot/League rival name 0', 'name': 'Rival', 'rect': [0.1, 0.1, 0.5, 0.06],
                 'comps': {'label': {'string': 'CozyWaffle85', 'fontSize': 32, 'height': 40,
                                     'font_kind': 'ttf', 'system_font': False}}}
            findings = audit.text_problems({'screen': 'league_iphone15', 'canvas_css': [0, 0, 393, 852],
                                            '_file': '/tmp/current-league/000-ui-dump-league.json'}, [n], [], None)
            self.assertFalse(any(x.startswith('font_text:') for x in findings), findings)
        finally:
            audit.RUNTIME_TEXT = previous

    def test_league_counts_bitmap_rank_groups_but_not_digits_in_rival_names(self):
        nodes = [{'path': 'Canvas/GameRoot/League rival name 0', 'name': 'League rival name 0',
                  'rect': [0.2, 0.3, 0.4, 0.05],
                  'comps': {'label': {'string': 'CozyWaffle85'}}}]
        groups = ['League rank digits', 'League points digits'] + \
                 [f'League row {kind} {i}' for i in range(5) for kind in ('rank', 'score')]
        for group in groups:
            nodes.append({'path': 'Canvas/GameRoot/' + group + '/Digit 9', 'name': 'Digit 9',
                          'rect': [0.1, 0.2, 0.02, 0.03],
                          'comps': {'sprite': {'frame': 'v7_digit_9'}}})
        self.assertEqual(audit.league_number_count(nodes), 12)

    def test_league_nickname_digits_alone_do_not_pass_the_rank_score_requirement(self):
        names = []
        for i in range(5):
            names.append({'path': f'Canvas/GameRoot/League rival name {i}', 'name': f'League rival name {i}',
                          'rect': [0.2, 0.2, 0.4, 0.05],
                          'comps': {'label': {'string': f'CozyFarmer{i}85'}}})
        self.assertEqual(audit.league_number_count(names), 0)

    def test_one_viewport_or_missing_screen_fails_the_full_matrix(self):
        screens = [{'id': 'home'}, {'id': 'league'}]
        viewports = [{'name': 'iphone_15', 'width': 393, 'height': 852},
                     {'name': 'iphone_se', 'width': 375, 'height': 667}]
        one_dump = {('league', 393, 852)}
        gaps = art_check.screen_viewport_gaps(screens, viewports, one_dump)
        self.assertEqual(len(gaps), 3)
        self.assertIn(('league', 375, 667), gaps)
        self.assertIn(('home', 393, 852), gaps)

    def test_complete_exact_screen_and_viewport_matrix_passes(self):
        screens = [{'id': 'home'}, {'id': 'league'}]
        viewports = [{'name': 'iphone_15', 'width': 393, 'height': 852},
                     {'name': 'iphone_se', 'width': 375, 'height': 667}]
        observed = {(screen['id'], viewport['width'], viewport['height'])
                    for screen in screens for viewport in viewports}
        self.assertEqual(art_check.screen_viewport_gaps(screens, viewports, observed), [])


if __name__ == '__main__':
    unittest.main()
