"""Offline continuation tests. Every artifact and callback is an isolated fake."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import delivery_continuation as continuation


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.input = self.root / 'failed-input.json'
        self.plan_path = self.root / 'plan.json'
        self.input.write_text('{"dependency": "*", "receipt": null}')
        self.original_failure = {
            'stdout': 'original gate output\r\n原始输出\n',
            'stderr': 'scope_required: precise dependency missing\n', 'exit_code': 2,
        }
        self.task = continuation.continuation_task(
            stage='writer', original_failure=self.original_failure,
            approved_run_ids=['ads.normal'], next_action='map_skin_consumer_to_skin_png')
        self.full_suite = Mock(side_effect=AssertionError('The whole suite must never be called'))

    def observe(self):
        return {'input': self.input.read_text(),
                'plan': self.plan_path.read_text() if self.plan_path.exists() else None}

    def repair(self, task):
        self.assertEqual(task['resume_at'], 'writer')
        self.assertEqual(task['approved_run_ids'], ('ads.normal',))
        self.input.write_text('{"dependency": "skin.png", "receipt": "bound-sha"}')

    def replan(self, task, *, run_ids=('ads.normal',), mode='scoped', startup=False):
        plan = {
            'schema': continuation.PLAN_SCHEMA, 'mode': mode,
            'actions': {'ads': {cid: {'action': 'run', 'reason': 'skin consumer changed'}
                                for cid in run_ids}}, 'startup_run': startup,
        }
        raw = json.dumps(plan, sort_keys=True).encode()
        self.plan_path.write_bytes(raw)
        return {
            'plan': plan, 'plan_path': str(self.plan_path),
            # Fake gate result; parent gate integration tests call real preflight.
            'verification': {'schema': continuation.PLAN_SCHEMA, 'mode': mode,
                             'allowed': list(run_ids), 'startup_run': startup,
                             'plan_sha256': hashlib.sha256(raw).hexdigest()},
        }

    def run_workflow(self, **changes):
        resume = changes.pop('resume', Mock(return_value={'status': 'passed'}))
        options = {
            'repair_action': 'repair_skin_dependency',
            'actions': {'repair_skin_dependency': self.repair},
            'observe': self.observe, 'replan': self.replan, 'resume': resume,
        }
        options.update(changes)
        return continuation.repair_and_resume(self.task, **options), resume

    def test_missing_plan_repair_replans_and_resumes_only_authorized_nodes(self):
        def unchanged_repair(task):
            # The exact correction is plan regeneration by the registered gate callback.
            return {'status': 'inputs_ready', 'why': 'precise existing dependency is already valid'}

        self.input.write_text('{"dependency": "skin.png", "receipt": "bound-sha"}')
        result, resume = self.run_workflow(actions={'repair_skin_dependency': unchanged_repair})
        self.assertEqual(result['status'], 'resumed')
        self.assertFalse(result['task_terminal'])
        self.assertEqual(result['resumed_run_ids'], ['ads.normal'])
        self.assertEqual(result['resume_at'], 'writer')
        self.assertEqual(result['original_failure'], self.original_failure)
        plan = resume.call_args.args[0]
        self.assertEqual([cid for group in plan['actions'].values() for cid, row in group.items()
                          if row['action'] == 'run'], ['ads.normal'])
        resume.assert_called_once()
        self.full_suite.assert_not_called()

    def test_wildcard_dependency_repair_and_receipt_recovery_each_resume_exact_step(self):
        for kind in ('wildcard_dependency', 'missing_receipt'):
            with self.subTest(kind=kind):
                self.input.write_text(json.dumps({'failed': kind}))
                result, resume = self.run_workflow()
                self.assertEqual(result['status'], 'resumed')
                self.assertNotEqual(result['before_sha256'], result['after_sha256'])
                self.assertEqual(result['repair_action'], 'repair_skin_dependency')
                self.assertEqual((result['repair_calls'], result['replan_calls'], result['resume_calls']), (1, 1, 1))
                resume.assert_called_once()
                self.full_suite.assert_not_called()

    def test_initial_broad_concrete_authorization_can_be_narrowed(self):
        self.task['approved_run_ids'] = ['ads.normal', 'ads.cancel', 'runtime.save_restart/profile']
        result, resume = self.run_workflow(actions={'repair_skin_dependency': lambda task: self.input.write_text('fixed')})
        self.assertEqual(result['status'], 'resumed')
        self.assertEqual(result['resumed_run_ids'], ['ads.normal'])
        resume.assert_called_once()

    def test_unchanged_inputs_and_plan_do_not_retry_original_step(self):
        self.replan(self.task)
        repair = Mock(return_value=None)
        result, resume = self.run_workflow(actions={'repair_skin_dependency': repair})
        self.assertEqual(result['status'], 'repair_required')
        self.assertIn('没有内容变化', result['why'])
        self.assertFalse(result['task_terminal'])
        self.assertEqual(result['resume_calls'], 0)
        repair.assert_called_once()
        resume.assert_not_called()

    def test_unregistered_command_is_never_executed(self):
        handler = Mock()
        result, resume = self.run_workflow(repair_action='sh -c arbitrary', actions={'known': handler})
        self.assertEqual(result['status'], 'needs_agent_action')
        self.assertEqual(result['next_action'], 'map_skin_consumer_to_skin_png')
        self.assertEqual(result['repair_action'], 'sh -c arbitrary')
        handler.assert_not_called()
        resume.assert_not_called()

    def test_semantic_diagnosis_returns_concrete_next_action_without_replan(self):
        replan = Mock()
        action = Mock(return_value={'status': 'diagnosis_required',
                                    'why': 'No proven consumer for the changed bundle',
                                    'next_action': 'inspect_the_skin_panel_consumer_and_record_exact_inputs'})
        result, resume = self.run_workflow(actions={'repair_skin_dependency': action}, replan=replan)
        self.assertEqual(result['status'], 'needs_agent_action')
        self.assertFalse(result['task_terminal'])
        self.assertEqual(result['next_action'], 'inspect_the_skin_panel_consumer_and_record_exact_inputs')
        replan.assert_not_called()
        resume.assert_not_called()

    def test_repair_cannot_mutate_original_authorization(self):
        def expand(task):
            task['approved_run_ids'] += ('ads.cancel',)

        result, resume = self.run_workflow(actions={'repair_skin_dependency': expand})
        self.assertEqual(result['status'], 'repair_required')
        self.assertEqual(result['approved_run_ids'], ['ads.normal'])
        self.assertEqual(result['original_failure'], self.original_failure)
        resume.assert_not_called()

    def test_approved_ids_cannot_expand_after_replan(self):
        result, resume = self.run_workflow(
            replan=lambda task: self.replan(task, run_ids=('ads.normal', 'ads.cancel')))
        self.assertIn('扩大原授权', result['why'])
        resume.assert_not_called()

    def test_full_mode_cannot_be_promoted_by_repair(self):
        result, resume = self.run_workflow(replan=lambda task: self.replan(task, mode='full'))
        self.assertIn('提升为 full', result['why'])
        self.assertFalse(result['task_terminal'])
        resume.assert_not_called()

    def test_reuse_only_cannot_be_promoted_to_scoped(self):
        self.task = continuation.continuation_task(
            stage='writer', original_failure='receipt missing', approved_run_ids=[], mode='reuse-only')
        result, resume = self.run_workflow(
            actions={'repair_skin_dependency': lambda task: self.input.write_text('fixed')},
            replan=lambda task: self.replan(task, run_ids=()))
        self.assertIn('纯沿用授权', result['why'])
        resume.assert_not_called()

    def test_unapproved_startup_is_not_hidden_outside_allowed_list(self):
        result, resume = self.run_workflow(replan=lambda task: self.replan(task, startup=True))
        self.assertIn(continuation.STARTUP, result['why'])
        resume.assert_not_called()

    def test_missing_verification_or_changed_plan_never_resume(self):
        for problem in ('missing_verification', 'changed_file', 'mismatched_allowed', 'fake_schema'):
            with self.subTest(problem=problem):
                def replan(task):
                    planned = self.replan(task)
                    if problem == 'missing_verification':
                        planned.pop('verification')
                    elif problem == 'changed_file':
                        self.plan_path.write_text('{}')
                    elif problem == 'mismatched_allowed':
                        planned['verification']['allowed'] = ['ads.cancel']
                    elif problem == 'fake_schema':
                        planned['verification']['schema'] = 'fake-verified-true'
                    return planned

                result, resume = self.run_workflow(replan=replan)
                self.assertEqual(result['status'], 'repair_required')
                self.assertFalse(result['task_terminal'])
                resume.assert_not_called()

    def test_failed_replan_does_not_fallback_or_retry(self):
        replan = Mock(side_effect=ValueError('new precise dependency still missing'))
        result, resume = self.run_workflow(replan=replan)
        self.assertEqual(result['status'], 'repair_required')
        self.assertIn('precise dependency still missing', result['why'])
        self.assertEqual(result['replan_calls'], 1)
        replan.assert_called_once()
        resume.assert_not_called()
        self.full_suite.assert_not_called()

    def test_resume_failure_does_not_claim_recovery(self):
        for value in (2, False, {'status': 'failed', 'error': 'writer refused'}, {'exit_code': 3},
                      {'status': 'scope_required', 'blocked': True, 'problems': ['precise scope missing']},
                      {'passed': False}, {'blocked': True}, {'status': 'not_run'},
                      {'status': 'environment_incomplete'}):
            with self.subTest(value=value):
                self.input.write_text('still broken')
                result, resume = self.run_workflow(resume=Mock(return_value=value))
                self.assertEqual(result['status'], 'repair_required')
                self.assertFalse(result['task_terminal'])
                self.assertEqual(result['original_failure'], self.original_failure)
                if isinstance(value, dict):
                    self.assertEqual(result['resume_result'], value)
                resume.assert_called_once()

    def test_legacy_helpers_keep_original_exit_and_error_output(self):
        self.assertFalse(continuation.failure('exact error', stage='writer')['task_terminal'])

        @continuation.continuing_cli('writer')
        def fail():
            print('original stderr', file=__import__('sys').stderr)
            return 7

        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            self.assertEqual(fail(), 7)
        lines = stream.getvalue().splitlines()
        self.assertEqual(lines[0], 'original stderr')
        self.assertEqual(json.loads(lines[1])['resume_at'], 'writer')


if __name__ == '__main__':
    unittest.main()
