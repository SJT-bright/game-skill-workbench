#!/usr/bin/env python3
"""Regression tests for home-layout placement of top resource controls."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_ui_coverage as audit  # noqa: E402


class HomeResourceBarTests(unittest.TestCase):
    def test_power_and_key_plus_controls_are_top_hud(self):
        problems = []
        buttons = [
            {'name': 'Canvas/UI/MenuLayer/bar/power/icon', 'rect': [65, 45, 50, 25]},
            {'name': 'Canvas/UI/MenuLayer/bar/key/icon', 'rect': [190, 45, 50, 25]},
            {'name': 'Canvas/UI/MenuLayer/btn_shop', 'rect': [30,260,60,45]},
            {'name': 'Canvas/UI/MenuLayer/btn_skins', 'rect': [280,260,60,45]},
        ]
        audit.home_places('home_short', buttons, (375, 667), problems)
        self.assertEqual(problems, [])

    def test_feature_entrances_on_both_sides_are_allowed(self):
        problems=[]
        audit.home_places('home', [{'name':'btn_shop','rect':[30,260,60,45]},
                                   {'name':'btn_skins','rect':[280,260,60,45]}], (375,667), problems)
        self.assertEqual(problems,[])

    def test_missing_one_side_is_rejected(self):
        problems=[]
        audit.home_places('home',[{'name':'btn_shop','rect':[30,260,60,45]}],(375,667),problems)
        self.assertIn('each side',' '.join(problems))

    def test_more_than_five_below_play_is_rejected(self):
        buttons=[{'name':'btn_shop','rect':[30,260,60,45]}, {'name':'btn_skins','rect':[280,260,60,45]}]
        buttons += [{'name':'feature_'+str(i),'rect':[15+i*57,500,45,45]} for i in range(6)]
        problems=[];audit.home_places('home',buttons,(375,667),problems)
        self.assertIn('at most 5',' '.join(problems))


if __name__ == '__main__':
    unittest.main(verbosity=2)
