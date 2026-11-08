import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_ledger as C

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.l=C.Ledger(self.p);self.calls=[]
        self.inputs={'package':{'a.js':'a','b.png':'b'},'adapter':{'/ready':'r','/home':'h'}}
    def tearDown(self):self.l.close();self.tmp.cleanup()
    def scope(self,checks):
        f=self.p/'docs/checks/check-inputs.json';f.write_text(json.dumps({'schema':C.SCOPE_SCHEMA,'checks':checks}))
    def decl(self,items):return {'basis':'actual module consumers','inputs':items}
    def plan(self,id='runtime.audio',inputs=None):return self.l.prepare(id,inputs or self.inputs,{'engine':'2.x'},'tool',domain='audio')
    def perform(self,p):return self.l.execute(p,lambda:(self.calls.append(p['check_id']) or {'passed':True}),lambda r:r['passed'])
    def test_identical_input_runs_once_across_new_ledger(self):
        self.perform(self.plan());self.l.close();self.l=C.Ledger(self.p)
        r,m=self.perform(self.plan());self.assertTrue(m['reused']);self.assertEqual(len(self.calls),1)
    def test_changed_without_scope_stops_no_full_run(self):
        self.perform(self.plan());d={'package':{'a.js':'changed','b.png':'b'},'adapter':self.inputs['adapter']}
        with self.assertRaises(C.NeedsScope):self.perform(self.plan(inputs=d))
        self.assertEqual(len(self.calls),1)
    def test_unaffected_audio_survives_owned_image_change(self):
        self.scope({'runtime.audio':self.decl({'package':['a.js'],'adapter':['/ready']}),'art.home':self.decl({'package':['b.png'],'adapter':['/home']})})
        self.perform(self.plan());self.perform(self.plan('art.home'))
        d={'package':{'a.js':'a','b.png':'new'},'adapter':self.inputs['adapter']}
        self.assertEqual(self.plan(inputs=d)['action'],'reuse');self.assertEqual(self.plan('art.home',d)['action'],'run')
    def test_unowned_new_file_is_not_silently_ignored(self):
        self.scope({'runtime.audio':self.decl({'package':['a.js','b.png'],'adapter':['*']})});self.perform(self.plan())
        d={'package':dict(self.inputs['package'],**{'c.js':'c'}),'adapter':self.inputs['adapter']}
        self.assertEqual(self.plan(inputs=d)['action'],'needs_scope')
    def test_new_glob_member_invalidates_only_consumer(self):
        self.scope({'runtime.audio':self.decl({'package':['*.js'],'adapter':['*']}),'art.home':self.decl({'package':['*.png']})});self.perform(self.plan());self.perform(self.plan('art.home'))
        d={'package':dict(self.inputs['package'],**{'c.png':'c'}),'adapter':self.inputs['adapter']}
        self.assertEqual(self.plan(inputs=d)['action'],'reuse');self.assertEqual(self.plan('art.home',d)['action'],'run')
    def test_shared_input_invalidates_all_consumers(self):
        self.scope({x:self.decl({'package':['a.js','b.png'],'adapter':['*']}) for x in ['runtime.audio','art.home']})
        for x in ['runtime.audio','art.home']:self.perform(self.plan(x))
        d={'package':{'a.js':'new','b.png':'b'},'adapter':self.inputs['adapter']}
        for x in ['runtime.audio','art.home']:self.assertEqual(self.plan(x,d)['action'],'run')
    def test_evidence_copied_and_tamper_detected(self):
        e=self.p/'shot.png';e.write_bytes(b'original')
        r,m=self.l.execute(self.plan(),lambda:{'passed':True,'evidence':str(e)},lambda r:r['passed'])
        e.unlink();self.assertEqual(self.plan()['action'],'reuse')
        Path(r['evidence']).write_bytes(b'bad');self.assertEqual(self.plan()['action'],'evidence_missing')
    def test_failure_not_repeated_without_input_fix(self):
        self.l.execute(self.plan(),lambda:{'passed':False},lambda r:r['passed'])
        self.assertEqual(self.plan()['action'],'blocked_failed')
        with patch.dict('os.environ',{'CHECK_RETRY_REASON':'real browser was restored'}):self.assertEqual(self.plan()['action'],'run')
    def test_concurrent_claim_cannot_start_duplicate(self):
        plan=self.plan();token,_=self.l._claim(plan)
        other=C.Ledger(self.p)
        try:
            with self.assertRaises(C.AlreadyRunning):other._claim(plan)
        finally:other.close()
    def test_midrun_input_change_never_passes(self):
        with self.assertRaises(C.NeedsScope):self.l.execute(self.plan(),lambda:{'passed':True},lambda r:r['passed'],verify_inputs=lambda:{})
        self.assertFalse(self.l.previous('runtime.audio')[0]['passed'])
    def test_rule_change_rechecks_only_this_node(self):
        self.perform(self.plan());p=self.l.prepare('runtime.audio',self.inputs,{'engine':'2.x'},'newtool',domain='audio')
        self.assertEqual(p['action'],'run')
    def test_failed_claim_released(self):
        def bad():raise ValueError('fault')
        with self.assertRaises(ValueError):self.l.execute(self.plan(),bad,lambda r:True)
        self.assertEqual(self.l.db.execute('SELECT COUNT(*) FROM active').fetchone()[0],0)
    def test_json_parent_owns_new_child_without_invalidating_sibling(self):
        self.scope({cid:self.decl({'adapter':['/states/'+str(i)]})
                    for i,cid in enumerate(['art.home','art.settings'])})
        original={'adapter':C.json_manifest({'states':[{'name':'home'},{'name':'settings'}]})}
        for cid in ('art.home','art.settings'):self.perform(self.plan(cid,original))
        changed={'adapter':C.json_manifest({'states':[{'name':'home','actions':[{'js':'move'}]},{'name':'settings'}]})}
        self.assertEqual(self.plan('art.home',changed)['action'],'run')
        self.assertEqual(self.plan('art.settings',changed)['action'],'reuse')
        unknown={'adapter':C.json_manifest({'states':[{'name':'home'},{'name':'settings'},{'name':'new'}]})}
        self.assertEqual(self.plan('art.settings',unknown)['action'],'needs_scope')

if __name__=='__main__':unittest.main()
