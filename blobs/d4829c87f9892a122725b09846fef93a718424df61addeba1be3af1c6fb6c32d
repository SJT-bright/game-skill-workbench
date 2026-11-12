import copy
import unittest

from ad_ui_stage_check import evaluate_plan


class AdUIStageCheck(unittest.TestCase):
    def setUp(self):
        self.plan = {
            'schema': 'art_iteration_plan.v1', 'advisory_only': True,
            'first_piece': {'current': True, 'passed': True, 'capture_verified': True,
                            'selected_cases': ['trial_narrow', 'trial_tall']},
            'visual_to_capture': {'trial_narrow': 'trial_375', 'trial_tall': 'trial_390'},
            'capture_plan': {'cases': [{'id': 'trial_375', 'action': 'fresh'},
                                       {'id': 'trial_390', 'action': 'reuse'},
                                       {'id': 'unrelated_shop', 'action': 'recapture'}]},
            'issues': [], 'remaining_visual_cases': ['unrelated_shop'],
        }
        self.required = ['trial_narrow', 'trial_tall']

    def test_current_owning_checks_allow_only_required_cases(self):
        problems, checked = evaluate_plan(self.plan, self.required)
        self.assertEqual(problems, [])
        self.assertEqual(checked, self.required)
        self.assertEqual(self.plan['capture_plan']['cases'][-1]['action'], 'recapture')

    def test_bare_passed_does_not_replace_real_checker(self):
        problems, checked = evaluate_plan({'passed': True}, self.required)
        self.assertTrue(problems)
        self.assertEqual(checked, [])

    def test_one_selected_size_does_not_approve_the_other(self):
        self.plan['first_piece']['selected_cases'] = ['trial_narrow']
        problems, checked = evaluate_plan(self.plan, self.required)
        self.assertTrue(problems)
        self.assertEqual(checked, [])

    def test_each_actual_check_boundary_is_required(self):
        for key in ('current', 'passed', 'capture_verified'):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan['first_piece'][key] = False
                self.assertTrue(evaluate_plan(plan, self.required)[0])

    def test_visual_and_capture_namespaces_are_mapped(self):
        self.plan['visual_to_capture']['trial_tall'] = 'trial_tall'
        self.assertTrue(evaluate_plan(self.plan, self.required)[0])

    def test_stale_capture_refuses_even_when_first_piece_says_pass(self):
        self.plan['capture_plan']['cases'][1]['action'] = 'recapture'
        self.assertTrue(evaluate_plan(self.plan, self.required)[0])

    def test_owning_checker_findings_are_not_erased(self):
        self.plan['issues'] = [{'layer': 'visual', 'code': 'text_outside_plate'}]
        self.assertTrue(evaluate_plan(self.plan, self.required)[0])

    def test_missing_collector_is_not_visual_approval(self):
        self.plan['capture_plan'] = {'error': 'collector evidence not verified'}
        self.assertTrue(evaluate_plan(self.plan, self.required)[0])


if __name__ == '__main__':
    unittest.main()
