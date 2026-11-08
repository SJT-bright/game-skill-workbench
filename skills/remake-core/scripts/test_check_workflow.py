import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_ledger as C
import check_workflow as W

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'game';self.p.mkdir();(self.p/'assets').mkdir()
        self.tool=Path(self.tmp.name)/'validate.py'
        self.tool.write_text('import json,sys\nfrom pathlib import Path\np=Path(sys.argv[1]);o=Path(sys.argv[2]);o.parent.mkdir(parents=True,exist_ok=True)\nn=int(p.read_text());o.write_text(json.dumps({"passed":0<=n<=10,"value":n}))\ncount=p.parent.parent/(p.name+".calls");count.write_text(str(int(count.read_text())+1 if count.exists() else 1))\nsys.exit(0 if 0<=n<=10 else 1)\n')
        self.doc={'schema':W.SCHEMA,'route':'source','roots':{'source':'${PROJECT}/assets'},'nodes':[]}
        for id,domain in [('text','text'),('audio','audio')]:
            (self.p/'assets'/id).write_text('5')
            self.doc['nodes'].append(dict(id=id,label=id,domain=domain,phase=2,basis='separate real input files',
                inputs={'source':[id]},command=['${PYTHON}',str(self.tool),'${PROJECT}/assets/'+id,'${PROJECT}/docs/checks/'+id+'.json'],
                tool_files=[str(self.tool)],verdict={'file':'${PROJECT}/docs/checks/'+id+'.json','pointer':'/passed','equals':True}))
        # Execution counters are external diagnostic output, not game input.
        self.doc['roots']['source']='${PROJECT}/assets'
        self.l=C.Ledger(self.p)
    def tearDown(self):self.l.close();self.tmp.cleanup()
    def run_node(self,id):
        result=W.run_node(self.l,self.doc,self.p,id)
        (self.p/'assets'/(id+'.calls')).unlink(missing_ok=True)
        return result
    def test_same_input_no_second_process(self):
        # Counter must not be inside dependencies; use the process call count instead.
        real=W.subprocess.run
        with patch.object(W.subprocess,'run',wraps=real) as call:
            self.run_node('text');self.run_node('text');self.assertEqual(call.call_count,1)
    def test_local_bad_edit_only_text_then_fix(self):
        self.run_node('text');self.run_node('audio');(self.p/'assets/text').write_text('99')
        self.assertTrue(W.prepare(self.l,self.doc,self.p)[1]['action']=='reuse')
        result,_=self.run_node('text');self.assertFalse(result['passed'])
        (self.p/'assets/text').write_text('6');result,_=self.run_node('text');self.assertTrue(result['passed'])
        self.assertEqual(W.prepare(self.l,self.doc,self.p)[1]['action'],'reuse')
    def test_unknown_added_input_blocks(self):
        self.run_node('text');(self.p/'assets/new-module').write_text('new')
        with self.assertRaises(C.NeedsScope):self.run_node('text')
    def test_stale_verdict_never_passes(self):
        self.tool.write_text('pass\n');out=self.p/'docs/checks/text.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text('{"passed":true}')
        result,_=W.run_node(self.l,self.doc,self.p,'text');self.assertFalse(result['passed'])
    def test_portable_original_evidence_and_no_rerun(self):
        self.run_node('text');folder=Path(self.tmp.name)/'bundle';self.l.export(folder)
        new=Path(self.tmp.name)/'received';(new/'assets').mkdir(parents=True)
        for id in ['text','audio']:(new/'assets'/id).write_text('5')
        other=C.Ledger(new)
        try:
            other.import_bundle(folder)
            with patch.object(W.subprocess,'run',side_effect=AssertionError('must not execute')):
                result,proof=W.run_node(other,self.doc,new,'text')
            self.assertTrue(result['passed']);self.assertTrue(proof['reused']);self.assertTrue((new/'docs/checks/text.json').is_file())
        finally:other.close()

if __name__=='__main__':unittest.main()
