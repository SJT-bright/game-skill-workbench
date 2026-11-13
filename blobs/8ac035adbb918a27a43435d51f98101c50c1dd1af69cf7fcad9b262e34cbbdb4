"""Planning fixtures only; no game, capture round or evidence mutation."""
import copy
import unittest
from art_change_plan import plan

class Planning(unittest.TestCase):
    def setUp(self):
        self.s={'current_round_version':'a'*64,'source_hash':'b'*64,'export_hash':'c'*64,'matrix_hash':'d'*64,'collector_hash':'e'*64,
                'changes':dict(source=False,export=False,matrix=False,collector=False),'changed_files':dict(source=[],export=[])}
        self.reports=[('full.json',{'rows':[{'check':'pixels','status':'需处理','detail':'a'},{'check':'layout','status':'需处理','detail':'b'}]})]
    def test_tool_only_never_builds_or_captures_and_lists_all_failures(self):
        r=plan(self.s,self.reports,['richness']);self.assertFalse(r['build']['required']);self.assertFalse(r['capture']['required'])
        self.assertTrue(r['analyze']['required']);self.assertEqual(len(r['all_reported_blockers']),2);self.assertFalse(r['evidence_acceptance'])
    def test_report_only_can_use_existing_evidence(self):
        rules={'checker.py':'f'*64}
        r=plan(self.s,[('pass',{'rows':[]})],rule_hashes_before=rules,rule_hashes_after=rules)
        self.assertTrue(r['analyze']['required'],'an empty unbound report cannot stand for completed analysis');self.assertFalse(r['capture']['required'])
    def test_missing_rule_identity_does_not_claim_analysis_is_current(self):
        r=plan(self.s,[('pass',{'rows':[]})]);self.assertTrue(r['analyze']['required'])
    def test_missing_baseline_or_reports_cannot_claim_initial_full_check(self):
        s=copy.deepcopy(self.s);s['current_round_version']=None
        r=plan(s);self.assertTrue(r['capture']['required']);self.assertIsNone(r['analyze']['required'])
    def test_stale_export_requires_one_build_and_no_capture_yet(self):
        self.s['changes']['source']=True;self.s['changed_files']['source']=['assets/UI.js']
        r=plan(self.s,self.reports);self.assertTrue(r['build']['required']);self.assertIsNone(r['capture']['required'])
    def test_changed_export_does_not_blindly_trigger_second_build(self):
        self.s['changes']['source']=self.s['changes']['export']=True
        r=plan(self.s,self.reports);self.assertIsNone(r['build']['required']);self.assertIsNone(r['capture']['required'])
        rules={'checker.py':'f'*64}
        r=plan(self.s,[('pass',{'rows':[]})],rule_hashes_before=rules,rule_hashes_after=rules)
        self.assertTrue(r['analyze']['required'],'source/export edits invalidate related analyses even when tools did not change')
    def test_matrix_or_collector_change_is_not_a_reason_to_rebuild(self):
        for key in ('matrix','collector'):
            s=copy.deepcopy(self.s);s['changes'][key]=True
            r=plan(s,self.reports);self.assertFalse(r['build']['required']);self.assertIsNone(r['capture']['required'])
    def impact(self):
        self.s['changes']['source']=self.s['changes']['export']=True
        self.s['changed_files']={'source':['assets/UI.js'],'export':['src/bundle.js']}
        return {'before':dict(version='a'*64,**{k:'f'*64 for k in ('source_hash','export_hash','matrix_hash','collector_hash')}),
                'after':{k:self.s[k] for k in ('source_hash','export_hash','matrix_hash','collector_hash')},
                'files':[dict(domain=dom,path=name,before_sha256='1'*64,after_sha256='2'*64,scope='local',cases=['popup'],basis='exact reviewed method/asset diff') for dom,name in [('source','assets/UI.js'),('export','src/bundle.js')]]}
    def test_complete_impact_is_still_a_plan_not_authority(self):
        r=plan(self.s,self.reports,impact=self.impact(),case_ids=['home','popup'])
        self.assertEqual(r['capture']['candidate_affected_cases'],['popup']);self.assertFalse(r['evidence_acceptance'])
        self.assertTrue(any('impact declaration alone is not authority' in x for x in r['planning_blockers']))
    def test_unknown_shared_or_missing_file_mapping_remains_blocked(self):
        m=self.impact();m['files'][0]['scope']='shared';m['files'].pop()
        r=plan(self.s,self.reports,impact=m,case_ids=['home','popup'])
        self.assertTrue(any('shared or unknown' in x for x in r['planning_blockers']));self.assertNotIn('candidate_unaffected_cases',r['capture'])
    def test_status_error_never_means_no_work(self):
        r=plan({'error':'missing snapshot'},self.reports);self.assertIsNone(r['build']['required']);self.assertTrue(r['planning_blockers'])

if __name__=='__main__':unittest.main()
