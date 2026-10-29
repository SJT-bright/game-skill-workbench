#!/usr/bin/env python3
"""Adversarial contract calibration; synthetic fixtures are not game evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import button_state_check as check


def fixture(root):
    root = Path(root)
    source = root / 'business.json'
    source.write_text('{"price":10,"reward":1}')
    evidence = root / 'raw-input.json'
    evidence.write_text('{"synthetic":true,"no_actual_game_run":true}')
    refs = [check.file_ref(root, source)]
    control = {'id': 'shop.buy', 'page': 'shop', 'states': {
        'locked': {'when': {'lt': [{'path': 'before.store.coins'}, 10]}, 'expect': {
            'kind': 'blocked', 'message': {'template': 'Need {n} more coins.', 'values': {
                'n': {'sub': [10, {'path': 'before.store.coins'}]}}}, 'unchanged': ['store']}},
        'ready': {'when': {'ge': [{'path': 'before.store.coins'}, 10]}, 'expect': {
            'kind': 'effect', 'after': {'store.coins': {'sub': [{'path': 'before.store.coins'}, 10]},
                                      'store.items': {'add': [{'path': 'before.store.items'}, 1]}}}}
    }}
    rows = []
    for state, before, after in [('locked', {'coins': 4, 'items': 0}, {'coins': 4, 'items': 0}),
                                 ('ready', {'coins': 10, 'items': 0}, {'coins': 0, 'items': 1})]:
        rows.append({'id': 'shop.buy::' + state, 'page': 'shop', 'control': 'shop.buy', 'state': state,
                     'status': 'tested', 'layer': 'browser_touch', 'input': {'performed': True},
                     'visible_controls': ['shop.buy'], 'before': {'store': before}, 'after': {'store': after},
                     'feedback': {'before_id': 'old', 'after_id': 'new', 'text': 'Need 6 more coins.'},
                     'evidence': [check.file_ref(root, evidence)]})
    return {'schema': 'button-state-plan.v1', 'business_sources': refs, 'business_domains': ['store'], 'input_lifecycle': {'applicable': False, 'reason': 'Synthetic shop business-contract fixture has no production pointer owner; interruption calibration is tested separately.'}, 'controls': [control]}, {
        'schema': 'button-state-run.v1', 'business_sources': refs, 'cases': rows}


def save_fixture_report(root):
    plan, run = fixture(root)
    p, r, out = [Path(root) / name for name in ('button-plan.json', 'button-run.json', 'button-report.json')]
    p.write_text(json.dumps(plan)); r.write_text(json.dumps(run))
    report = check.make_report(root, p, r)
    out.write_text(json.dumps(report))
    return check.file_ref(root, out)


class ButtonStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='button-contract-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan, self.run = fixture(self.root)

    def verdict(self):
        return check.validate(self.plan, self.run, self.root)

    def test_normal_disabled_and_ready_controls_pass(self):
        result = self.verdict()
        self.assertTrue(result['passed'], result)
        self.assertEqual((result['required'], result['observed']), (2, 2))

    def test_unrelated_new_notice_fails(self):
        self.run['cases'][0]['feedback']['text'] = 'Something went wrong'
        self.assertFalse(self.verdict()['passed'])

    def test_wrong_deficit_fails(self):
        self.run['cases'][0]['feedback']['text'] = 'Need 5 more coins.'
        self.assertFalse(self.verdict()['passed'])

    def test_no_fresh_notice_fails(self):
        self.run['cases'][0]['feedback']['after_id'] = 'old'
        self.assertFalse(self.verdict()['passed'])

    def test_missing_state_fails(self):
        self.run['cases'].pop()
        self.assertFalse(self.verdict()['passed'])

    def test_omitted_visible_button_fails(self):
        self.run['cases'][0]['visible_controls'] = []
        self.assertFalse(self.verdict()['passed'])

    def test_unplanned_visible_button_fails(self):
        self.run['cases'][0]['visible_controls'].append('shop.other')
        self.assertFalse(self.verdict()['passed'])

    def test_empty_cases_and_empty_plan_fail(self):
        self.run['cases'] = []
        self.assertFalse(self.verdict()['passed'])
        self.plan['controls'] = []
        self.assertFalse(self.verdict()['passed'])

    def test_untested_na_and_prose_status_fail(self):
        for status in ('untested', 'n/a', 'pass', 'All disabled states checked'):
            self.run['cases'][0]['status'] = status
            self.assertFalse(self.verdict()['passed'], status)

    def test_wrong_state_facts_fail(self):
        self.run['cases'][0]['before']['store']['coins'] = 20
        self.assertFalse(self.verdict()['passed'])

    def test_resource_mutation_while_blocked_fails(self):
        self.run['cases'][0]['after']['store']['coins'] = 0
        self.assertFalse(self.verdict()['passed'])

    def test_spend_without_reward_fails(self):
        self.run['cases'][1]['after']['store']['items'] = 0
        self.assertFalse(self.verdict()['passed'])

    def test_duplicate_case_fails(self):
        self.run['cases'].append(copy.deepcopy(self.run['cases'][0]))
        self.assertFalse(self.verdict()['passed'])

    def test_conditional_extra_control_uses_business_visibility(self):
        self.plan['excluded_controls'] = [{'id': 'shop.exchange', 'page': 'shop',
            'why': 'Separate exchange workflow is outside the purchase repair scope',
            'visible_when': {'lt': [{'path': 'before.store.coins'}, 10]}}]
        self.run['cases'][0]['visible_controls'].append('shop.exchange')
        self.assertTrue(self.verdict()['passed'], self.verdict())

    def test_unexpected_effect_resource_mutation_fails(self):
        self.run['cases'][1]['before']['store']['gems'] = 9
        self.run['cases'][1]['after']['store']['gems'] = 0
        self.assertFalse(self.verdict()['passed'])

    def test_expected_value_cannot_read_its_own_after(self):
        self.plan['controls'][0]['states']['ready']['expect']['after']['store.coins'] = {'path': 'after.store.coins'}
        self.run['cases'][1]['after']['store']['coins'] = 10
        self.assertFalse(self.verdict()['passed'])

    def test_malformed_case_returns_failure_instead_of_traceback(self):
        self.run['cases'] = [17]
        self.assertFalse(self.verdict()['passed'])

    def test_presentation_field_cannot_be_oracle(self):
        self.plan['controls'][0]['states']['locked']['expect']['message'] = {
            'template': '{x}', 'values': {'x': {'path': 'before.button.reason'}}}
        self.run['cases'][0]['before']['button'] = {'reason': 'Need 6 more coins.'}
        self.assertFalse(self.verdict()['passed'])

    def test_changed_evidence_and_source_fail(self):
        (self.root / 'raw-input.json').write_text('modified')
        self.assertFalse(self.verdict()['passed'])
        self.plan, self.run = fixture(self.root)
        (self.root / 'business.json').write_text('{"price":99}')
        self.assertFalse(self.verdict()['passed'])

    def test_current_report_rechecks_raw_run_not_pass_flag(self):
        ref = save_fixture_report(self.root)
        self.assertTrue(check.current_report(self.root, ref))
        run_path = self.root / 'button-run.json'
        data = json.loads(run_path.read_text()); data['cases'].pop(); run_path.write_text(json.dumps(data))
        report_path = self.root / ref['path']; report = json.loads(report_path.read_text())
        report['inputs']['run'] = check.file_ref(self.root, run_path)
        report_path.write_text(json.dumps(report))
        self.assertFalse(check.current_report(self.root, check.file_ref(self.root, report_path)))


class InputLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='input-lifecycle-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan, self.run = fixture(self.root)
        self.plan['controls'][0]['states'] = {'ready': self.plan['controls'][0]['states']['ready']}
        self.run['cases'] = [self.run['cases'][1]]
        self.run['cases'][0]['input']['after_interruption'] = True
        sequences = {
            'missing_terminal': [('start','old'),('hide',None),('show',None),('start','new'),('end','new')],
            'late_terminal': [('start','old'),('hide',None),('show',None),('end','old'),('start','new'),('end','new')],
            'cancel': [('start','old'),('cancel','old'),('end','old'),('start','new'),('end','new')],
            'disable_reenable': [('start','old'),('disable',None),('enable',None),('end','old'),('start','new'),('end','new')],
        }
        self.trace = {'schema':'input-lifecycle-run.v1','business_sources':self.plan['business_sources'],
                      'layer':'isolated_production','scenarios':{k:[{'type':t,'finger':f,'commits':int(i==len(v)-1)} for i,(t,f) in enumerate(v)] for k,v in sequences.items()}}
        self.plan['input_lifecycle'] = {'applicable':True,'groups':[{'id':'shared','controls':['shop.buy'],
            'trace':{},'recovery_cases':['shop.buy::ready']}]}
        self.write_trace()

    def verdict(self):
        return check.validate(self.plan,self.run,self.root)

    def write_trace(self):
        p=self.root/'lifecycle.json';p.write_text(json.dumps(self.trace))
        self.plan['input_lifecycle']['groups'][0]['trace']=check.file_ref(self.root,p)

    def test_lifecycle_passes(self):
        self.assertTrue(self.verdict()['passed'],self.verdict())

    def test_missing_declaration_rejected(self):
        del self.plan['input_lifecycle'];self.assertFalse(self.verdict()['passed'])

    def test_missing_scenario_rejected(self):
        del self.trace['scenarios']['missing_terminal'];self.write_trace();self.assertFalse(self.verdict()['passed'])

    def test_late_commit_and_stuck_input_rejected(self):
        for scenario,index,value in [('late_terminal',3,1),('missing_terminal',4,0)]:
            old=self.trace['scenarios'][scenario][index]['commits'];self.trace['scenarios'][scenario][index]['commits']=value
            self.write_trace();self.assertFalse(self.verdict()['passed']);self.trace['scenarios'][scenario][index]['commits']=old

    def test_cancel_delivered_in_missing_terminal_is_rejected(self):
        self.trace['scenarios']['missing_terminal'].insert(1,{'type':'cancel','finger':'old','commits':0})
        self.write_trace();self.assertFalse(self.verdict()['passed'])

    def test_wrong_binding_and_modified_trace_rejected(self):
        self.trace['business_sources']=[];self.write_trace();self.assertFalse(self.verdict()['passed'])
        (self.root/'lifecycle.json').write_text('{}');self.assertFalse(self.verdict()['passed'])

    def test_no_gui_recovery_or_ordinary_tap_rejected(self):
        self.run['cases'][0]['input'].pop('after_interruption');self.assertFalse(self.verdict()['passed'])
        self.plan['input_lifecycle']['groups'][0]['recovery_cases']=[];self.assertFalse(self.verdict()['passed'])

    def test_undeclared_group_control_rejected(self):
        self.plan['input_lifecycle']['groups'][0]['controls']=[];self.assertFalse(self.verdict()['passed'])

    def test_current_report_rechecks_lifecycle_not_pass_flag(self):
        pp,rp,out=[self.root/n for n in ('plan.json','run.json','report.json')]
        pp.write_text(json.dumps(self.plan));rp.write_text(json.dumps(self.run))
        report=check.make_report(self.root,pp,rp);out.write_text(json.dumps(report))
        self.assertTrue(check.current_report(self.root,check.file_ref(self.root,out)))
        self.trace['scenarios']['missing_terminal'][-1]['commits']=0;self.write_trace()
        pp.write_text(json.dumps(self.plan))
        report['inputs']['plan']=check.file_ref(self.root,pp);report['passed']=True
        out.write_text(json.dumps(report))
        self.assertFalse(check.current_report(self.root,check.file_ref(self.root,out)))

    def test_obvious_touch_owner_cannot_opt_out(self):
        p=self.root/'owner.ts';p.write_text('TOUCH_START touchId getID')
        self.plan['business_sources']=[check.file_ref(self.root,p)];self.run['business_sources']=self.plan['business_sources']
        self.plan['input_lifecycle']={'applicable':False,'reason':'This deliberately misleading exclusion must not bypass the obvious production touch ownership.'}
        self.assertFalse(self.verdict()['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
