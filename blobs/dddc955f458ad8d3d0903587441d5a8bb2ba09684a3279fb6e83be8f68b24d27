"""Offline catalog checks; importing the scheduler never executes a runtime."""
import unittest

import runtime_incremental as incremental


class SelectedUnitCatalogTests(unittest.TestCase):
    def test_ad_catalog_preserves_every_declared_state_and_dynamic_directory(self):
        adapter = {'ad_entries': [
            {'id': 'skin', 'states': [{'name': 'unowned'}, {'name': 'owned'}]},
            {'id': 'homegift', 'states': [{'name': 'ready'}]},
        ], 'resume_play': {'start': [], 'ad': {'tap': 'level/reward'}}}
        self.assertEqual(incremental.unit_ids('ad_outcome', {}, adapter),
                         ['skin/unowned', 'skin/owned', 'homegift/ready', 'resume_play.ad', '@discovered'])

    def test_nonexistent_resume_ad_does_not_create_an_execution_unit(self):
        for resume in ({'n/a': 'no level'}, {'start': [], 'ad': {'none': 'no level ad'}}, {}):
            self.assertEqual(incremental.unit_ids('ad_outcome', {}, {'resume_play': resume}), ['@discovered'])

    def test_save_independence_requires_an_explicit_requires_array_on_every_step(self):
        block = {'steps': [{'name': 'skin', 'requires': []}, {'name': 'homegift', 'requires': ['skin']}]}
        self.assertEqual(incremental.unit_ids('save_restart', {}, {'save_restart': block}),
                         ['@kinds', 'step/skin', 'step/homegift'])
        del block['steps'][1]['requires']
        self.assertEqual(incremental.unit_ids('save_restart', {}, {'save_restart': block}), ['@suite'])

    def test_prechecked_routes_keep_the_original_suite_identity(self):
        for name in ('ad_outcome', 'save_restart'):
            self.assertEqual(incremental.unit_ids(name, {}, {}, prechecked=True), ['@suite'])


if __name__ == '__main__':
    unittest.main()
