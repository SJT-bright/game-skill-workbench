"""Offline checks for real unit selection, original assertions and evidence extraction."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
import runtime_incremental
from runtime_split_migration import extract_unit


class SuiteExecutionTests(unittest.TestCase):
    def run_suite(self, name, adapter, selection, fault=None):
        with tempfile.TemporaryDirectory(prefix='runtime-split-unit-') as temp:
            root = Path(temp)
            modules = {
                'lib.mjs': """
export const C=globalThis.CFG, A=C.adapter;
export const url=q=>'http://isolated.invalid/?'+q;
export function evidence(name,data){globalThis.observed.report=JSON.parse(JSON.stringify(data));return name;}
export async function keepFrames(){}
export async function suite(body){
 const out={cases:[],warnings:[],evidence:{},add(id,passed,detail){this.cases.push({id,passed,detail});},
 warn(text){this.warnings.push(text);},save(){}};
 const page={evaluate:async()=>0,goto:async()=>{globalThis.observed.restarts++;if(C.fault==='lost')globalThis.observed.value=0;}};
 await body({out,page});globalThis.observed.out=out;
}
""",
                'gates.mjs': """
export const MIN_FPS=5;
export const waitHome=async()=>({ok:true,fps:60});
export async function openGame(){globalThis.observed.value=0;globalThis.observed.values={};globalThis.observed.opens++;}
export const evalJs=async()=>null;
export const nodeCentre=async()=>null;
export const shot=async(_page,path)=>path;
export async function click(){
 const m=globalThis.observed;m.clicks.push(m.mode);
 if(m.mode==='complete'&&globalThis.CFG.fault!=='no_reward'||m.mode==='cancel'&&globalThis.CFG.fault==='cancel_reward')m.value++;
}
export const sleep=async ms=>{globalThis.observed.time+=ms;};
""",
                'phone.mjs': """
export const sleep=async ms=>{globalThis.observed.time+=ms;};
export async function steps(_page,actions){
 const m=globalThis.observed;m.actions.push(...actions.map(a=>a.tag));m.value++;
 for(const a of actions)m.values[a.tag]=(m.values[a.tag]||0)+1;
 return {ok:true,log:actions};
}
export const js=async(_page,code)=>code.startsWith('field:')?(globalThis.observed.values[code.slice(6)]||0):globalThis.observed.value;
export const snap=async()=>({m:{},scene:'home'});
export const buttonsOf=()=>[];
export const point=async()=>({x:40,y:40});
export const priorAdEntries=async()=>[];
export const hostIdx=async()=>0;
export const hostSince=async()=>[{kind:'ad-show'},{kind:'ad-result'},{kind:'lifecycle',data:'show'}];
export const setAd=async(_page,mode)=>{globalThis.observed.mode=mode;};
export const dismissModal=async()=>null;
export const pickContinue=()=>null;
export const tapReact=async()=>({kind:'ad'});
export const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const truthy=Boolean;
""",
                'layout_rules.mjs': """
export const adEntriesProblems=()=>[];
export const snapDiff=()=>({add:[],gone:[],moved:[],text:[],sprite:[]});
export const dropPress=diff=>diff;
""",
                'revive_return.mjs': """
export const reviveContractProblem=()=>null;
export const checkReviveReturn=async()=>({ok:true});
"""
            }
            for filename, source in modules.items():
                (root / filename).write_text(source)
            suite = root / 'suite.mjs'
            suite.write_bytes((HERE / 'runtime_regression/suites' / (name + '.mjs')).read_bytes())
            config = {'lib': (root / 'lib.mjs').as_uri(), 'adapter': adapter, 'selection': selection,
                      'policy': 'new', 'prior': {}, 'evidenceDir': str(root), 'fault': fault}
            script = ('globalThis.CFG=' + json.dumps(config) + ';'
            'globalThis.observed={time:0,value:0,values:{},opens:0,restarts:0,actions:[],clicks:[]};'
                      'Date.now=()=>globalThis.observed.time;'
                      'await import(' + json.dumps(suite.as_uri()) + ');'
                      'console.log(JSON.stringify(globalThis.observed));')
            proc = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True,
                                  text=True, timeout=8)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)

    def skin_adapter(self):
        return {
            'ad_entries': [
                {'id': 'unrelated', 'button': 'Canvas/Other', 'states': [{'name': 'idle', 'actions': [{'tag': 'other'}]}]},
                {'id': 'skin', 'button': 'Canvas/Skin', 'states': [{'name': 'unowned', 'actions': [{'tag': 'skin'}]}]}
            ],
            'ad_outcome': {'entries': {'skin': {'reward_js': 'return reward;'},
                                       'unrelated': {'reward_js': 'return reward;'}}}
        }

    def save_adapter(self):
        return {'save_restart': {'steps': [
            {'name': 'other', 'kind': 'claim', 'requires': [], 'actions': [{'tag': 'other'}], 'read_js': 'return value;'},
            {'name': 'skin', 'kind': 'buy', 'requires': [], 'actions': [{'tag': 'skin'}], 'read_js': 'return value;'}
        ]}}

    def test_skin_outcome_executes_both_original_results_only_for_selected_entry(self):
        result = self.run_suite('ad_outcome', self.skin_adapter(), ['skin/unowned'])
        self.assertEqual(result['actions'], ['skin'])
        self.assertEqual(result['clicks'], ['cancel', 'complete'])
        self.assertEqual([row['id'] for row in result['out']['cases']],
                         ['skin/unowned/cancel', 'skin/unowned/complete'])
        self.assertTrue(result['out']['units']['skin/unowned']['passed'])

    def test_cancel_reward_fault_is_still_rejected(self):
        result = self.run_suite('ad_outcome', self.skin_adapter(), ['skin/unowned'], 'cancel_reward')
        self.assertFalse(result['out']['units']['skin/unowned']['passed'])
        self.assertFalse(result['out']['cases'][0]['passed'])

    def test_missing_complete_reward_is_still_rejected(self):
        result = self.run_suite('ad_outcome', self.skin_adapter(), ['skin/unowned'], 'no_reward')
        self.assertFalse(result['out']['units']['skin/unowned']['passed'])
        self.assertFalse(result['out']['cases'][1]['passed'])

    def test_save_skin_executes_only_skin_and_real_restart_assertion(self):
        result = self.run_suite('save_restart', self.save_adapter(), ['step/skin'])
        self.assertEqual(result['actions'], ['skin'])
        self.assertEqual(result['restarts'], 1)
        self.assertTrue(result['out']['units']['step/skin']['passed'])

    def test_declared_save_prerequisite_is_executed(self):
        adapter = self.save_adapter()
        adapter['save_restart']['steps'][1]['requires'] = ['other']
        result = self.run_suite('save_restart', adapter, ['step/skin'])
        self.assertEqual(result['actions'], ['other', 'skin'])
        self.assertEqual(result['restarts'], 1)

    def test_lost_skin_save_is_still_rejected(self):
        result = self.run_suite('save_restart', self.save_adapter(), ['step/skin'], 'lost')
        self.assertFalse(result['out']['units']['step/skin']['passed'])

    def test_cyclic_save_prerequisite_is_rejected_before_actions(self):
        adapter = self.save_adapter()
        adapter['save_restart']['steps'][0]['requires'] = ['skin']
        adapter['save_restart']['steps'][1]['requires'] = ['other']
        result = self.run_suite('save_restart', adapter, ['step/skin'])
        self.assertEqual(result['actions'], [])
        self.assertFalse(result['out']['cases'][0]['passed'])

    def test_legacy_save_adapter_keeps_cumulative_compatibility(self):
        adapter = self.save_adapter()
        for step in adapter['save_restart']['steps']:
            del step['requires']
            step['read_js'] = 'field:' + step['name']
        result = self.run_suite('save_restart', adapter, ['@suite'])
        self.assertEqual(result['actions'], ['other', 'skin'])
        self.assertEqual(result['restarts'], 1)
        self.assertEqual(result['out']['cases'][0]['id'], 'restart')
        self.assertTrue(result['out']['cases'][0]['passed'])

    def test_empty_selection_never_means_all(self):
        for suite, adapter in [('ad_outcome', self.skin_adapter()), ('save_restart', self.save_adapter())]:
            result = self.run_suite(suite, adapter, [])
            self.assertEqual(result['actions'], [])
            self.assertFalse(result['out']['cases'][0]['passed'])

    def test_enumeration_matches_actual_duplicate_resume_catalogue(self):
        adapter = self.skin_adapter()
        adapter['resume_play'] = {'ad': {'tap': 'Canvas/Skin'}, 'start': []}
        result = self.run_suite('ad_outcome', adapter, ['skin/unowned'])
        ids = runtime_incremental.unit_ids('ad_outcome',
            {'script': HERE / 'runtime_regression/suites/ad_outcome.mjs'}, adapter)
        self.assertEqual(set(ids) - {'@discovered'}, {entry['id'] for entry in result['report']['entries']})

    def test_unknown_selection_never_starts_unrelated_steps(self):
        for suite, adapter in [('ad_outcome', self.skin_adapter()), ('save_restart', self.save_adapter())]:
            result = self.run_suite(suite, adapter, ['unknown'])
            self.assertEqual(result['actions'], [])
            self.assertFalse(result['out']['cases'][0]['passed'])


class EnumerationTests(unittest.TestCase):
    def test_exact_outcome_and_save_ids(self):
        adapter = SuiteExecutionTests().skin_adapter()
        ids = runtime_incremental.unit_ids('ad_outcome', {}, adapter)
        self.assertEqual(ids, ['unrelated/idle', 'skin/unowned', '@discovered'])
        ids = runtime_incremental.unit_ids('save_restart', {}, SuiteExecutionTests().save_adapter())
        self.assertEqual(ids, ['@kinds', 'step/other', 'step/skin'])

    def test_legacy_save_is_atomic_until_dependencies_are_explicit(self):
        adapter = SuiteExecutionTests().save_adapter()
        del adapter['save_restart']['steps'][0]['requires']
        self.assertEqual(runtime_incremental.unit_ids('save_restart', {}, adapter), ['@suite'])

    def test_original_ad_assertion_body_is_retained_verbatim(self):
        before = (HERE / 'fixtures/runtime-unit-splits/ad_outcome.before.mjs').read_text()
        body = before[before.index('    const spec ='):before.index('\n  done();', before.index('    const spec ='))]
        self.assertIn(body, (HERE / 'runtime_regression/suites/ad_outcome.mjs').read_text())


class MigrationTests(unittest.TestCase):
    def parent(self, root, suite, report, cases, passed=False):
        path = root / 'report.json'
        path.write_text(json.dumps(report))
        return {'check_id': 'runtime.' + suite + '/@suite', 'key': 'original-key',
                'executed_at': 'original-time', 'passed': passed, 'seconds': 12.5,
                'binding': {'check_id': 'runtime.' + suite + '/@suite', 'tool_sha256': 'original-tool'},
                'roots': {'package': {'game.js': 'original-game'}},
                'files': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}],
                'result': {'suite': suite, 'passed': passed, 'cases': cases, 'evidence': {'report': str(path)}}}

    def test_passed_entry_can_be_extracted_from_failed_aggregate_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self.parent(Path(temp), 'ad_outcome', {
                'suite': 'ad_outcome', 'entries': [{'id': 'gift/ready', 'from': 'ad_entries'}],
                'cases': [{'id': 'gift/ready', 'cancel_result': 'pass', 'complete_result': 'pass'}]},
                [{'id': 'gift/ready/cancel', 'passed': True}, {'id': 'gift/ready/complete', 'passed': True}])
            old = copy.deepcopy(record)
            result = extract_unit(record, 'ad_outcome', 'gift/ready')
            self.assertTrue(result['passed'])
            self.assertFalse(result['inheritance']['source_passed'])
            self.assertEqual(result['inheritance']['executed_at'], 'original-time')
            self.assertEqual(result['inheritance']['source_binding'], record['binding'])
            self.assertEqual(record, old)

    def test_failed_entry_cannot_be_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self.parent(Path(temp), 'ad_outcome', {
                'suite': 'ad_outcome', 'entries': [{'id': 'skin/unowned', 'from': 'ad_entries'}],
                'cases': [{'id': 'skin/unowned', 'cancel_result': 'fail', 'complete_result': 'pass'}]},
                [{'id': 'skin/unowned/cancel', 'passed': False}, {'id': 'skin/unowned/complete', 'passed': True}])
            with self.assertRaises(ValueError):
                extract_unit(record, 'ad_outcome', 'skin/unowned')

    def test_earnings_without_restart_cannot_be_migrated(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self.parent(Path(temp), 'save_restart', {'suite': 'save_restart', 'result': 'fail',
                'steps': [{'name': 'other', 'before': 0, 'after': 1}]}, [{'id': 'restart', 'passed': False}])
            with self.assertRaises(ValueError):
                extract_unit(record, 'save_restart', 'step/other')

    def test_prior_successful_save_step_keeps_its_original_restart_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self.parent(Path(temp), 'save_restart', {'suite': 'save_restart', 'result': 'pass',
                'after_png': 'original.png', 'steps': [{'name': 'other', 'before': 0, 'after': 1, 'after_restart': 1}]},
                [{'id': 'restart', 'passed': True}], passed=True)
            result = extract_unit(record, 'save_restart', 'step/other')
            self.assertEqual(result['cases'][0]['detail']['after_restart'], 1)
            self.assertEqual(result['seconds'], 12.5)

    def test_tampered_frozen_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self.parent(Path(temp), 'save_restart', {'suite': 'save_restart', 'kinds': {'missing': []}}, [])
            Path(record['files'][0]['path']).write_text('{}')
            with self.assertRaises(ValueError):
                extract_unit(record, 'save_restart', '@kinds')


if __name__ == '__main__':
    unittest.main()
