"""Offline real-ledger and source-bound controls for reviewed release updates.

These fixtures execute the actual Python contracts and JavaScript probe with
explicit synthetic observations; they do not run a game, browser or device.
"""
from contextlib import redirect_stderr
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import audit_runtime_resources as resources
import bundle_module_inputs as modules
import check_ledger as ledger
import preview_audio_startup as audio
import regression_baseline as baseline
import test_bundle_module_inputs as module_fixtures
import test_regression_baseline as baseline_fixtures


class ModuleArchiveControls(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='reviewed-module-history-')
        self.addCleanup(self.folder.cleanup)
        self.archive = Path(self.folder.name)
        self.old = {module_fixtures.PATH: module_fixtures.bundle()}
        self.new = {module_fixtures.PATH: module_fixtures.bundle(skin='9')}
        self.roots = module_fixtures.roots(self.old)
        self.scope = module_fixtures.scope('Skin')

    def expand(self):
        with patch.dict(os.environ, {'ENGLISH_CHECK_MODULE_ARCHIVE': str(self.archive)}), \
                modules.module_sources(self.new):
            return modules.with_module_inputs(self.roots, scope=self.scope)

    def test_original_hashed_js_recovers_intermediate_module_inputs_without_execution(self):
        raw = self.old[module_fixtures.PATH]
        (self.archive / (ledger.sha(raw) + '.js')).write_bytes(raw)
        expected = modules.expand_module_roots(self.roots, self.old)
        self.assertEqual(self.expand(), expected)

    def test_wrong_historical_bytes_are_refused(self):
        raw = self.old[module_fixtures.PATH]
        (self.archive / (ledger.sha(raw) + '.js')).write_bytes(b'not the original JS')
        with self.assertRaisesRegex(modules.ModuleInputError, '原始字节校验失败'):
            self.expand()

    def test_missing_historical_bytes_do_not_reuse_stored_module_metadata(self):
        with self.assertRaises(modules.ModuleInputError):
            self.expand()


class NewCheckRepairControls(unittest.TestCase):
    def setUp(self):
        self.f = baseline_fixtures.BaselineRecoveryTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        retry = patch.dict(os.environ, {'CHECK_RETRY_REASON': 'explicit offline fixture environment retry'})
        retry.start()
        self.addCleanup(retry.stop)
        f = self.f
        f.record('ads.two')
        self.declaration = {'reason': 'new independent offline consumer', 'basis': 'fixture one.png'}
        f.config['baseline_recovery'] = {'new_checks': {'ads.one': self.declaration}}
        f.write_scope()
        first = f.identity()
        self.prior_plan = f.project / 'original-plan.json'
        self.save_plan({'schema': 'cocos-regression-scope.v1', 'project': str(f.project),
            'baseline': first, 'actions': {'ads': {row['check_id']: row for row in f.groups()['ads']}}})

    def save_plan(self, value):
        self.prior_plan.write_text(json.dumps(value))

    def request(self, failed, *, environment=None):
        f = self.f
        request = {'correction_basis': 'exact one.png consumer corrected',
                   'prior_plan': {'path': str(self.prior_plan), 'sha256': baseline.digest(self.prior_plan)},
                   'source_key': ledger.sha(failed['binding'])}
        if environment is not None:
            request['environment_retry'] = environment
        f.config['baseline_recovery']['check_repairs'] = {'ads.one': request}
        f.write_scope()
        return request

    def correct_input(self):
        self.f.current['one.png'] = b'corrected fixture one'
        self.f.current_roots = {'package': baseline.package_manifest(self.f.current)}

    def test_real_failed_new_check_resumes_only_after_its_actual_input_changes(self):
        failed = self.f.record('ads.one', self.f.current_roots, passed=False)
        self.request(failed)
        self.correct_input()
        recovered = self.f.identity()['sources']['ads.one']
        self.assertEqual(recovered['kind'], 'new_check_repair')
        self.assertFalse(recovered['old_pass_claimed'])
        self.assertFalse(recovered['prior_observation']['passed'])
        self.assertEqual(self.f.groups()['ads'][0]['action'], 'run')
        self.assertEqual(self.f.groups()['ads'][1]['action'], 'reuse')

    def test_same_input_business_failure_cannot_be_reset_to_new(self):
        failed = self.f.record('ads.one', self.f.current_roots, passed=False)
        self.request(failed)
        with self.assertRaisesRegex(ledger.NeedsScope, '实际依赖没有修正'):
            self.f.identity()

    def test_mutated_prior_plan_is_not_accepted(self):
        failed = self.f.record('ads.one', self.f.current_roots, passed=False)
        self.request(failed)
        self.correct_input()
        self.prior_plan.write_text(self.prior_plan.read_text() + ' ')
        with self.assertRaisesRegex(ledger.NeedsScope, '原核准计划字节'):
            self.f.identity()

    def test_prior_plan_from_another_project_is_refused(self):
        failed = self.f.record('ads.one', self.f.current_roots, passed=False)
        plan = json.loads(self.prior_plan.read_text())
        plan['project'] += '-foreign'
        self.save_plan(plan)
        self.request(failed)
        self.correct_input()
        with self.assertRaisesRegex(ledger.NeedsScope, '本工程本基线'):
            self.f.identity()

    def environment_failure(self, cases):
        message = 'Ego session stopped; resolve the recorded error/control state before continuing'
        raw = self.f.project / 'environment-error.json'
        observed = {'cases': cases, 'fatal': 'Error: ' + message}
        raw.write_text(json.dumps(observed))
        row = self.f.groups()['ads'][0]
        with redirect_stderr(io.StringIO()):
            self.f.store.execute(row, lambda: {'passed': False, 'fatal': observed['fatal'],
                'cases': cases, 'raw_files': [str(raw)]}, lambda result: result['passed'])
        failed = self.f.store.previous('ads.one')[0]
        self.request(failed, environment={'resolved_reason': 'offline fixture runner restored',
            'raw_report': {'path': str(raw), 'sha256': baseline.digest(raw)}})
        return failed

    def test_zero_case_environment_retry_keeps_error_and_still_requires_execution(self):
        failed = self.environment_failure([])
        source = self.f.identity()['sources']['ads.one']
        self.assertEqual(source['kind'], 'new_check_environment_retry')
        self.assertEqual(source['prior_binding'], failed['binding'])
        self.assertFalse(source['old_pass_claimed'])
        self.assertIn('session stopped', source['prior_error'])
        self.assertNotEqual(self.f.groups()['ads'][0]['action'], 'reuse')

    def test_executed_product_case_cannot_be_relabelled_environment_retry(self):
        self.environment_failure([{'id': 'business-failure', 'passed': False}])
        with self.assertRaisesRegex(ledger.NeedsScope, '零用例环境中断'):
            self.f.identity()


class ProfileControls(unittest.TestCase):
    def test_registry_keeps_each_exact_source_version_and_rejects_other_hashes(self):
        registry = Path(__file__).resolve().parents[2] / 'cocos-game-to-english/scripts/reviewed_resource_profiles.json'
        if not registry.is_file():
            self.skipTest('English-only resource registry; validated in the English release tree')
        profiles = json.loads(registry.read_text())
        names = [name for name in profiles if name.startswith('rubber-monster-en2-local-ui')]
        self.assertGreaterEqual(len(names), 2)
        seen = set()
        for name in names:
            profile = profiles[name]
            hashes = profile['source_sha256']
            seen.add(hashes['assets/main/index.js'])
            with patch.object(resources, '_reviewed_profiles', return_value=profiles):
                self.assertEqual(resources._matching_reviewed_profiles({}, hashes), [profile])
                foreign = dict(hashes, **{'assets/main/index.js': '0' * 64})
                self.assertEqual(resources._matching_reviewed_profiles({}, foreign), [])
        self.assertEqual(len(seen), len(names))


PROBE_DRIVER = r'''
const assert=require('node:assert/strict');
const code=JSON.parse(process.argv[1]);
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function run(names){
 let ticks=0,taps=[];
 const track={intent:true,volume:1,paused:true,currentTime:0,src:'fixture-bg.ogg'};
 function node(name){return {name,activeInHierarchy:true,opacity:255,children:[],getComponent(){return {enabled:true,interactable:true}},getBoundingBoxToWorld(){return {x:10,y:10,width:40,height:30}}};}
 const children=names.map(name=>node(name));
 const scene={activeInHierarchy:true,opacity:255,children,getComponent(){return null}};
 const canvas={width:390,height:844};
 const window={__audioStartupSnapshot:()=>({environment:'browser_native_host',tracks:[{...track}]}),
  cc:{Button:function(){},director:{getScene:()=>scene},game:{canvas},view:{getVisibleSize:()=>({}),getViewportRect:()=>({x:0,y:0}),getScaleX:()=>1,getScaleY:()=>1}}};
 const Element={prototype:{getBoundingClientRect(){return {left:0,top:0,right:390,bottom:844,width:390,height:844}}}};
 const p={evaluate:async fn=>fn(),cdp:async(kind,value)=>{taps.push(value.type);if(value.type==='touchEnd'){track.paused=false;track.currentTime=1;}}};
 class Clock extends Date{static now(){ticks+=3000;return ticks;}}
 const trace=await new AsyncFunction('p','window','Element','Date','setTimeout',code+'\nreturn collectPreviewAudio(p);')(p,window,Element,Clock,fn=>fn());
 return {trace,taps};
}
(async()=>{
 const preferred=await run(['OpenSettings','Start']);assert.equal(preferred.trace.action.node,'Start');assert.equal(preferred.trace.action.kind,'ordinary_play_touch');
 const settings=await run(['SettingsButton']);assert.equal(settings.trace.action.node,'SettingsButton');assert.equal(settings.trace.action.kind,'ordinary_settings_touch');assert.deepEqual(settings.taps,['touchStart','touchEnd']);
 const mute=await run(['Music','MusicToggle']);assert.equal(mute.trace.action,null);assert.deepEqual(mute.taps,[]);
 console.log(JSON.stringify({passed:true,cases:3,boundary:'Actual probe JS with synthetic Cocos observations; no browser/audio/device proof'}));
})().catch(e=>{console.error(e);process.exitCode=1});
'''


class OrdinaryAudioInputControls(unittest.TestCase):
    def test_settings_fallback_never_replaces_available_play_or_toggles_music(self):
        result = subprocess.run(['node', '-e', PROBE_DRIVER, json.dumps(audio.EGO_PROBE_JS)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['passed'])


if __name__ == '__main__':
    unittest.main()
