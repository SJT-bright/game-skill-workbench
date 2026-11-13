#!/usr/bin/env python3
"""Synthetic routing, producer reuse and writer side-effect boundary tests."""
from contextlib import ExitStack, nullcontext, redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1] / 'cocos-game-check/package-check/scripts'
sys.path[:0] = [str(HERE), str(PKG)]
import make_tiktok_zip as M
import build_checked_zip as B
import writer_proofs as P
import audit_runtime_coverage as coverage_tool


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='single-writer-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.project = self.home / 'project'
        self.native = self.project / 'native'
        self.web = self.project / 'web'
        for root in (self.project / 'assets', self.native, self.web):
            root.mkdir(parents=True)
            (root / 'main.js').write_text('const fixture = 1;')
        self.app = 'fixture-app'
        (self.native / 'game.js').write_text('require("./main.js");')
        (self.native / 'game.json').write_text('{"subpackages": []}')
        (self.native / 'project.config.json').write_text(json.dumps({'appid': self.app}))
        self.manifest = self.project / 'resources.json'
        self.manifest.write_text('{}')
        self.out = self.home / 'out.zip'
        self.kw = dict(native=self.native, app_id=self.app, out=self.out, project=self.project,
                       web=self.web, resource_manifest=self.manifest, keep_old_packages=True)


class SingleWriter(Fixture):
    def mock_engine(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.calls = []
        def ready(name, value):
            def observed(*args, **kwargs):
                self.calls.append(name)
                return value
            return observed
        files = {p.relative_to(self.native).as_posix(): p.read_bytes() for p in self.native.rglob('*') if p.is_file()}
        sizes = {name: len(data) for name, data in files.items()}
        info = {'appId': self.app, 'main': sum(sizes.values()), 'total': sum(sizes.values()),
                'normal': {}, 'independent': {}, 'package_gates': {'blocks': [], 'warnings': [], 'gates': []}}
        finalized = {'policy': 'new', 'board': 'remake', 'kind': 'finalize-native'}
        proofs = {'checks': [], 'refs': {}}
        replacements = [
            (M, 'finalize_for_writer', ready('prepared', (finalized, {'writer': True}, []))),
            (M, 'native_problems', ready('native', ([], sizes, info))),
            (M, 'english_new_image_problems', ready('english_images', [])),
            (M, 'resolve_rework', lambda *args: (None, 'fixture')),
            (M, 'writer_regressions', ready('regressions', {'blocked': False, 'problems': [],
                'warnings': [], 'rewarded_ad_regression': {'status': 'not_applicable'}, 'runtime_regression': {'passed': True}})),
            (M, 'regression_receipt', lambda *args: {'schema': 'fixture-complete'}),
            (M, 'finalize_report', lambda *args: {'policy': 'new', 'table_markdown': 'fixture'}),
            (M, 'adapter_step', lambda *args: None),
            (P, 'resolve_web', lambda *args: self.web),
            (P, 'consume', ready('producer_proofs', proofs)),
            (P, 'unchanged', lambda *args: None),
        ]
        for owner, name, function in replacements:
            stack.enter_context(patch.object(owner, name, side_effect=function))
        patches = {
            'audit_packed_assets.audit': ready('packed_assets', {'passed': True, 'errors': []}),
            'package_obligations.verify': ready('obligations', {'passed': True}),
            'package_obligations.publication_guard': lambda *args: nullcontext(),
            'audit_native_resource_paths.audit': ready('resource_paths', {'status': 'pass', 'errors': []}),
            'audit_interaction_audio.audit': ready('interaction_audio', {'passed': True}),
            'audit_final_storage.audit_final_storage': ready('storage', {'passed': True}),
            'known_issue_checkpoints.consume_for_writer': ready('checkpoints', {'status': 'summary', 'unmapped': ['fixture']}),
            'project_qa.review_policy': lambda *args: None,
            'check_package.verify_regression_scope': ready('scope', {'plan_sha256': 'fixture'}),
            'check_package.tools_in_use': lambda: {},
            'delivery_folder.tidy': lambda *args, **kwargs: {'fixture': True},
            'upload_size_gate.enforce_tiktok_host': lambda *args: None,
        }
        for name, function in patches.items():
            stack.enter_context(patch(name, side_effect=function))
        self.startup = stack.enter_context(patch('audit_final_package_startup.audit_final_startup',
            side_effect=ready('startup', {'checks': []})))
        stack.enter_context(patch.object(M.vnz, 'finalize_problem', return_value=None))
        def verify(archive, app_id):
            with zipfile.ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
                actual = {n: hashlib.sha256(zipped.read(n)).hexdigest() for n in zipped.namelist()}
            return {'file_sha256': actual, 'sha256': P.file_sha(archive), 'archive_bytes': Path(archive).stat().st_size,
                    'files': len(actual), 'main_bytes': sum(sizes.values()), 'uncompressed_total_bytes': sum(sizes.values())}
        stack.enter_context(patch.object(M.vnz, 'verify', side_effect=verify))
        stack.enter_context(patch.object(M.vnz, 'make_receipt', return_value={'schema': 2, 'fixture': True}))
        stack.enter_context(patch.object(M.subprocess, 'run', side_effect=AssertionError('writer must not execute a subprocess')))
        return stack

    def test_legacy_build_routes_all_parameters_once(self):
        values = dict(self.kw, interaction_audio_trace='audio', startup_contract='startup', loading_recovery_runtime='retry',
            ad_regression='ads', board='localize', keep_webp_exception='reason', rework_of='old', report='report',
            build_tag='version', review='review', coverage='coverage', writer_evidence='proof',
            native_resource_paths_runtime='path-proof', webp_codec_reports=['codec'])
        with patch.object(M, 'write_package', return_value={'sentinel': True}) as backend:
            self.assertEqual(B.build(**values), {'sentinel': True})
        self.assertEqual(backend.call_count, 1)
        self.assertEqual(backend.call_args.kwargs, values)

    def test_two_cli_names_and_app_id_alias_share_parser_backend(self):
        output = {'finalize': {'policy': 'new', 'table_markdown': ''}, 'delivery_folder': {}}
        for cli in (M.main, B.main):
            for flag in ('--app-id', '--expected-app-id'):
                argv = ['--native', str(self.native), flag, self.app, '--out', str(self.out),
                        '--project', str(self.project), '--resource-manifest', str(self.manifest),
                        '--interaction-audio-trace', 'a', '--writer-evidence', 'p', '--web', str(self.web)]
                with self.subTest(cli=cli.__module__, flag=flag), patch.object(M, 'write_package', return_value=output) as backend, \
                        patch('delivery_folder.describe', return_value=[]), redirect_stdout(io.StringIO()):
                    self.assertEqual(cli(argv), 0)
                    self.assertEqual(backend.call_count, 1)
                    self.assertEqual(backend.call_args.kwargs['app_id'], self.app)
                    self.assertEqual(backend.call_args.kwargs['interaction_audio_trace'], Path('a'))
                    self.assertEqual(backend.call_args.kwargs['writer_evidence'], Path('p'))

    def test_failure_does_not_fallback_or_retry(self):
        with patch.object(M, 'write_package', side_effect=ValueError('exact failed node')) as backend:
            with self.assertRaisesRegex(ValueError, 'exact failed node'):
                B.build(**self.kw)
        self.assertEqual(backend.call_count, 1)

    def test_same_engine_preserves_all_duties_and_deterministic_bytes(self):
        self.mock_engine()
        before = P.tree(self.native, None)
        first = M.write_package(**dict(self.kw, interaction_audio_trace=self.home / 'trace'))
        expected_calls = ['prepared', 'native', 'packed_assets', 'obligations', 'english_images', 'resource_paths',
                          'interaction_audio', 'producer_proofs', 'checkpoints', 'storage', 'scope', 'startup', 'regressions']
        self.assertEqual(self.calls, expected_calls)
        self.assertTrue(self.startup.call_args.kwargs['reuse_only'])
        self.assertEqual(before, P.tree(self.native, None))
        self.calls.clear()
        second_out = self.home / 'other.zip'
        B.build(**dict(self.kw, out=second_out, interaction_audio_trace=self.home / 'trace'))
        self.assertEqual(self.out.read_bytes(), second_out.read_bytes())
        self.assertEqual(first['known_issue_coverage']['unmapped'], ['fixture'])

    def test_one_writer_invocation_reuses_startup_audit_but_next_call_is_fresh(self):
        self.mock_engine()
        import audit_upload_startup as startup
        original_preflight = M.native_problems.side_effect
        original_verify = M.vnz.verify.side_effect
        payload = {p.relative_to(self.native).as_posix(): p.read_bytes()
                   for p in self.native.rglob('*') if p.is_file()}
        def preflight(*args, **kwargs):
            startup.audit_files(payload)
            return original_preflight(*args, **kwargs)
        def final_archive(archive, app_id):
            with zipfile.ZipFile(archive) as zipped:
                startup.audit_files({name: zipped.read(name) for name in zipped.namelist()})
            return original_verify(archive, app_id)
        M.native_problems.side_effect = preflight
        M.vnz.verify.side_effect = final_archive
        with patch.dict(os.environ):
            os.environ.pop('NODE_OPTIONS', None)
            os.environ.pop('NODE_PATH', None)
            with patch.object(startup, '_audit_files_uncached', return_value={'passed': True, 'errors': [], 'warnings': []}) as evaluator:
                M.write_package(**self.kw)
                self.assertEqual(evaluator.call_count, 1)
                M.write_package(**dict(self.kw, out=self.home / 'next.zip'))
                self.assertEqual(evaluator.call_count, 2)
        self.assertIsNone(startup._AUDIT_INVOCATION.get())

    def test_substantive_negative_stops_without_archive(self):
        self.mock_engine()
        for target, reason in [('writer_proofs.consume', 'reward-storage: stale'),
                               ('audit_native_resource_paths.audit', 'relocation proof stale'),
                               ('audit_final_storage.audit_final_storage', 'storage proof failed')]:
            with self.subTest(target=target), patch(target, side_effect=ValueError(reason)):
                with self.assertRaisesRegex(ValueError, reason):
                    B.build(**self.kw)
                self.assertFalse(self.out.exists())

    def test_prepared_guard_never_finalizes_missing_or_valid_native(self):
        import tiktok_finalize as F
        before = P.tree(self.native, None)
        record = {'policy': 'new', 'kind': 'finalize-native', 'blocks': [], 'warnings': []}
        with patch('ad_standard_scope.requirement', return_value={'required': False}), \
                patch.object(F, 'decide_policy', return_value={'policy': 'new'}), \
                patch.object(F.T, 'load_manifest', return_value={}), \
                patch.object(F, 'read_source_record', return_value={'board': 'localize'}), \
                patch.object(F, 'check_source_record', return_value=[]), \
                patch.object(F, 'finalize_native', side_effect=AssertionError('implicit prepare')), \
                patch.object(F, 'prepared_native_result', return_value=None) as prepared:
            result, _, problems = M.finalize_for_writer(self.native, self.project, 'localize', self.app)
            self.assertIsNone(result)
            self.assertIn('K_native_preparation_required', problems[0])
            prepared.return_value = record
            result, context, problems = M.finalize_for_writer(self.native, self.project, 'localize', self.app)
            self.assertFalse(problems)
            self.assertIs(context['finalize_record'], result)
            self.assertTrue(prepared.call_args.kwargs['options']['prepared_png_only'])
        self.assertEqual(before, P.tree(self.native, None))

    def test_registered_qa_is_consumed_and_never_invoked_by_writer(self):
        self.mock_engine()
        with patch('project_qa.review_policy', return_value={'writer_path': 'registered.py'}), \
                patch.object(P, 'consume_project_qa', return_value={'refs': {}, 'original_at': 'original'}) as consume, \
                patch('project_qa.invoke', side_effect=AssertionError('writer invoked project producer')):
            result = M.write_package(**self.kw)
        self.assertEqual(consume.call_count, 1)
        self.assertEqual(result['project_qa_proof']['original_at'], 'original')

    def test_codec_evidence_is_current_and_keeps_its_hashed_raw_trace(self):
        (self.native / 'texture.webp').write_bytes(b'fixture texture')
        self.mock_engine()
        import check_known_issues as known
        binding = {'source_sha256': known.snapshot(self.project)[2], 'native_tree_sha256': known.tree_sha(self.native),
                   'web_tree_sha256': known.tree_sha(self.web), 'build_tag': 'original'}
        raw = self.home / 'codec.raw'; raw.write_text('synthetic actual decoder trace')
        runtime = self.home / 'codec.runtime.json'
        runtime.write_text(json.dumps({'binding': binding, 'native_codec_verified': True, 'codec_evidence_refs': [0],
                                      'raw_evidence': [{'path': raw.name, 'sha256': P.file_sha(raw)}]}))
        report = self.home / 'codec.report.json'
        report.write_text(json.dumps({'tool': 'audit_native_texture_codec', 'passed': True, 'failed': 0, 'checked': 1,
                                      'binding': binding, 'runtime_file': runtime.name}))
        result = M.write_package(**dict(self.kw, webp_codec_reports=[report]))
        self.assertIn(str(raw), result['writer_producer_proofs']['refs'])
        raw.write_text('changed decoder observation')
        with self.assertRaisesRegex(ValueError, 'raw evidence.*changed'):
            M.write_package(**dict(self.kw, out=self.home / 'codec-bad.zip', webp_codec_reports=[report]))
        self.assertFalse((self.home / 'codec-bad.zip').exists())


class RegressionReads(Fixture):
    def test_reuse_only_summary_has_empty_execution_selection(self):
        import check_package as checks
        import ad_incremental as ads
        import runtime_incremental as runtime
        reusable = [{'check_id': 'fixture', 'why': 'existing original evidence', 'action': 'reuse'}]
        seen = []
        def ad_run(*args, **kwargs):
            if kwargs.get('plan_only'):
                return reusable
            seen.append(('ads', kwargs['cases']))
            return {'passed': True, 'complete': True}
        def runtime_run(*args, **kwargs):
            if kwargs.get('plan_only'):
                return reusable
            seen.append(('runtime', kwargs['suites']))
            return {'passed': True, 'complete': True}
        with patch.object(checks, 'regression_context', return_value=(self.project, 'adapter', 'remake', 'new')), \
                patch.object(checks, 'verify_regression_scope', return_value={}), \
                patch.object(checks, 'input_gate'), patch('regression_scope_gate.needs_ad_suite', return_value=True), \
                patch.object(ads, 'run', side_effect=ad_run), patch.object(runtime, 'run', side_effect=runtime_run), \
                patch.object(checks, 'regression_coverage_problem', return_value=None), \
                patch.object(checks, 'regression_record', return_value={'complete': True}), \
                patch('ad_regression._run_uncached', side_effect=AssertionError('browser')), \
                patch('runtime_regression._run_uncached', side_effect=AssertionError('browser')):
            result = M.writer_regressions(self.native, 'adapter', 'new', 'remake', project=self.project)
            self.assertFalse(result['blocked'], result)
            self.assertEqual(seen, [('ads', []), ('runtime', [])])
            reusable[0]['action'] = 'run'
            seen.clear()
            result = M.writer_regressions(self.native, 'adapter', 'new', 'remake', project=self.project)
            self.assertTrue(result['blocked'])
            self.assertIn('fixture', result['problems'][0])
            self.assertEqual(seen, [])


class ProducerProofs(Fixture):
    def coverage(self):
        path = self.project / 'docs/test/runtime-coverage.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        roots = P.paths(self.project, self.native, self.web)
        artifacts, sites = coverage_tool.inventory({name: roots[name] for name in ('source', 'native', 'web')})
        self.assertEqual(sites, {})
        path.write_text(json.dumps({'schema': 'runtime_coverage.v1', 'artifacts': artifacts, 'sites': {}, 'domains': {}}))
        return path

    def test_real_na_producer_once_then_consumers_never_execute(self):
        self.coverage()
        first = P.prepare(self.project, self.native, self.web)
        keys = {row['id']: row['key'] for row in first['checks']}
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('unexpected VM/command')):
            second = P.prepare(self.project, self.native, self.web)
            current = P.consume(self.project, self.native, self.web)
        self.assertTrue(all(row['action'] == 'reused' for row in second['checks']))
        self.assertEqual(keys, {row['id']: row['key'] for row in current['checks']})
        self.assertTrue(all(Path(row['raw']).is_file() for row in current['checks']))

    def test_missing_stale_or_changed_raw_never_runs_vm(self):
        self.coverage()
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('unexpected VM/command')):
            with self.assertRaisesRegex(ValueError, 'missing evidence'):
                P.consume(self.project, self.native, self.web)
        first = P.prepare(self.project, self.native, self.web)
        raw = Path(first['checks'][0]['raw'])
        original = raw.read_bytes()
        raw.write_text('{}')
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('unexpected VM/command')):
            with self.assertRaisesRegex(ValueError, 'raw producer output'):
                P.consume(self.project, self.native, self.web)
        raw.write_bytes(original)
        (self.native / 'new.js').write_text('const newlyDiscovered = 1;')
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('unexpected VM/command')):
            with self.assertRaisesRegex(ValueError, 'reward-storage.*stale'):
                P.consume(self.project, self.native, self.web)

    def test_coverage_only_change_keeps_reward_proof_and_original_time(self):
        coverage = self.coverage()
        first = P.prepare(self.project, self.native, self.web)
        reward = first['checks'][0]
        document = json.loads(coverage.read_bytes())
        document['note'] = 'Coverage bookkeeping correction; executable artifacts are unchanged.'
        coverage.write_text(json.dumps(document))
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('unrelated reward probe repeated')):
            second = P.prepare(self.project, self.native, self.web)
        self.assertEqual(second['checks'][0]['key'], reward['key'])
        self.assertEqual(second['checks'][0]['original_at'], reward['original_at'])
        self.assertEqual(second['checks'][0]['action'], 'reused')
        self.assertEqual(second['checks'][1]['action'], 'rerun')

    def test_clock_and_seed_are_controlled_only_for_explicit_producer(self):
        script = """const vm=require('vm'),clock=require(process.argv[1]);
const live=clock({});if(live.Date!==Date||live.Math!==Math)throw Error('defaults changed');
const env={COCOS_REWARD_PROBE_NOW_MS:'1761955200000',COCOS_REWARD_PROBE_SEED:'7'};
const run=()=>vm.runInNewContext('[Date.now(),new Date().getTime(),new Date(0).getTime(),Math.random(),Math.random()]',clock(env));
const first=run(),second=run();if(JSON.stringify(first)!==JSON.stringify(second)||first[0]!==1761955200000||first[1]!==first[0]||first[2]!==0)throw Error('clock not isolated');
console.log(JSON.stringify({passed:true,first,second,timezone:process.env.TZ}));"""
        result = subprocess.run(['node', '-e', script, str(HERE / 'reward_probe_clock.cjs')],
                                env=dict(os.environ, TZ='UTC'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['passed'])

    def test_actual_vm_loaders_receive_the_explicit_fixed_clock(self):
        script = r"""const fs=require('fs'),vm=require('vm'),path=require('path');
const root=process.argv[1],epoch=1761955200000;process.env.COCOS_REWARD_PROBE_NOW_MS=String(epoch);process.env.COCOS_REWARD_PROBE_SEED='7';
let observed=0;
function verify(c){if(c.Date.now()!==epoch||new c.Date().getTime()!==epoch)throw Error('unbound VM Date');observed++;}
const fakefs={readFileSync:()=> '46:[function(e,t,n){},{}],47:'};
const rewardRequire=n=> n.includes('check_guard')?null:n==='node:fs'?fakefs:n==='node:vm'?{runInNewContext:(s,c)=>{verify(c);if(observed===2)throw Error('CLOCK_CAPTURED');}}:n==='./reward_probe_clock.cjs'?require(path.join(root,n)):require(n);
try{vm.runInNewContext(fs.readFileSync(path.join(root,'probe_cocos2_reward_storage.cjs'),'utf8'),{require:rewardRequire,__dirname:root,module:{exports:{}},process:{argv:['node','fixture','/native','/web','/web/main.js']}});throw Error('probe did not stop')}catch(e){if(e.message!=='CLOCK_CAPTURED')throw e;}
const moduleStub={exports:{}};
const papercutRequire=n=> n==='vm'?{createContext:c=>{verify(c);throw Error('CLOCK_CAPTURED');}}:n==='./reward_probe_clock.cjs'?require(path.join(root,n)):require(n);
vm.runInNewContext(fs.readFileSync(path.join(root,'papercut_production_loader.cjs'),'utf8'),{require:papercutRequire,module:moduleStub});
try{moduleStub.exports('/native',{});throw Error('loader did not stop')}catch(e){if(e.message!=='CLOCK_CAPTURED')throw e;}
if(observed!==3)throw Error('missing VM injection');console.log(JSON.stringify({passed:true,observed}));"""
        result = subprocess.run(['node', '-e', script, str(HERE)], capture_output=True, text=True,
                                env=dict(os.environ, TZ='UTC'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['observed'], 3)

    def test_applicable_proof_is_bound_and_concurrent_prepare_runs_once(self):
        self.coverage()
        report = {'tool': 'run_reward_storage_probe', 'passed': True, 'applicable': True, 'status': 'passed',
                  'execution': {'passed': True, 'checks': ['controlled synthetic producer']}}
        original = subprocess.CompletedProcess([], 0, json.dumps(report), '')
        with patch.object(P.subprocess, 'run', return_value=original) as producer:
            with ThreadPoolExecutor(max_workers=2) as threads:
                results = list(threads.map(lambda _: P.prepare(self.project, self.native, self.web), range(2)))
        self.assertEqual(producer.call_count, 1)
        keys = [next(row['key'] for row in result['checks'] if row['id'] == 'reward-storage') for result in results]
        self.assertEqual(keys[0], keys[1])
        env = producer.call_args.kwargs['env']
        self.assertEqual(env['TZ'], 'UTC')
        self.assertEqual(int(env['COCOS_REWARD_PROBE_NOW_MS']), P.OPTIONS['clock_ms'])
        self.assertNotIn('NODE_OPTIONS', env)
        self.assertNotIn('NODE_PATH', env)
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('consumer VM')):
            consumed = P.consume(self.project, self.native, self.web)
        self.assertTrue(consumed['checks'][0]['report']['applicable'])

    def test_single_reward_cli_check_does_not_need_coverage_or_source_layer(self):
        (self.project / 'assets/main.js').unlink()
        (self.project / 'assets').rmdir()
        P.prepare(self.project, self.native, self.web, kind='reward-storage')
        output = io.StringIO()
        actual_binding = P.binding
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('check executed producer')), \
                patch.object(P, 'binding', wraps=actual_binding) as observed, redirect_stdout(output):
            code = P.main(['check', '--kind', 'reward-storage', '--project', str(self.project),
                           '--native', str(self.native), '--web', str(self.web)])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual([row['id'] for row in json.loads(output.getvalue())['checks']], ['reward-storage'])
        self.assertEqual([call.args[0] for call in observed.call_args_list], ['reward-storage'])
        self.assertFalse((self.project / 'docs/test/runtime-coverage.json').exists())

    def test_single_coverage_cli_check_does_not_need_reward_proof_or_node(self):
        self.coverage()
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('coverage executed VM')):
            P.prepare(self.project, self.native, self.web, kind='runtime-coverage')
        output = io.StringIO()
        with patch.object(P.subprocess, 'run', side_effect=AssertionError('check executed producer')), \
                patch.object(P.shutil, 'which', return_value=None), redirect_stdout(output):
            code = P.main(['check', '--kind', 'runtime-coverage', '--project', str(self.project),
                           '--native', str(self.native), '--web', str(self.web)])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual([row['id'] for row in json.loads(output.getvalue())['checks']], ['runtime-coverage'])
        with self.assertRaisesRegex(ValueError, 'reward-storage: missing producer proof'):
            P.consume(self.project, self.native, self.web)


class ProjectQaProofs(Fixture):
    def write_proof(self, checks):
        expected = {'required_checks': ['review_audit', 'writer_coverage']}
        report = {'tool': 'project_qa_writer_evidence', 'passed': True, 'error': None, 'checks': checks}
        execution = {'returncode': 0, 'command': ['synthetic QA producer'], 'stdout': json.dumps(report), 'stderr': ''}
        raw = self.home / 'qa.raw.json'; raw.write_text(json.dumps(execution))
        proof = self.home / 'qa.proof.json'
        proof.write_text(json.dumps({'schema': P.SCHEMA, 'kind': 'project-qa', 'binding': expected,
            'key': P.digest(expected), 'execution': execution, 'execution_sha256': P.digest(execution),
            'raw': {'path': raw.name, 'sha256': P.file_sha(raw)}, 'executed_at': 'original', 'seconds': 1}))
        return proof, expected

    def test_qa_explicit_failure_or_incomplete_dominates_pass(self):
        negatives = [{'status': 'incomplete', 'passed': True, 'complete': False},
                     {'status': 'passed', 'passed': True, 'complete': False},
                     {'status': 'failed', 'passed': True}, {'status': 'passed', 'passed': False},
                     {'status': 'passed', 'passed': True, 'failed': 1},
                     {'status': 'passed', 'passed': True, 'errors': ['actual failure']},
                     {'status': 'passed', 'passed': True, 'planned_not_run': ['missing case']}]
        for result in negatives:
            with self.subTest(result=result):
                proof, expected = self.write_proof([{'id': 'review_audit', 'result': {'status': 'passed'}},
                                                    {'id': 'writer_coverage', 'result': result}])
                with self.assertRaisesRegex(ValueError, 'does not establish'):
                    P.read_proof(proof, 'project-qa', expected)

    def test_qa_missing_or_duplicate_required_writer_coverage_is_rejected(self):
        audit = {'id': 'review_audit', 'result': {'status': 'passed'}}
        coverage = {'id': 'writer_coverage', 'result': {'status': 'passed', 'complete': True}}
        for rows in ([audit], [audit, audit], [audit, coverage, coverage]):
            with self.subTest(rows=rows):
                proof, expected = self.write_proof(rows)
                with self.assertRaisesRegex(ValueError, 'does not establish'):
                    P.read_proof(proof, 'project-qa', expected)
        proof, expected = self.write_proof([audit, coverage])
        self.assertEqual(P.read_proof(proof, 'project-qa', expected)['original_at'], 'original')

    def test_incomplete_qa_producer_preserves_failure_and_does_not_repeat_it(self):
        index = self.project / P.DEFAULT
        index.parent.mkdir(parents=True)
        index.write_text(json.dumps({'schema': P.SCHEMA, 'project': str(self.project), 'proofs': {}}))
        args = SimpleNamespace(project=self.project, native=self.native, web=self.web, review=self.home / 'review.json')
        expected = {'required_checks': ['review_audit', 'writer_coverage']}
        incomplete = {'status': 'incomplete', 'passed': True, 'complete': False}
        def result(profile, function, *args, **kwargs):
            return incomplete if function == 'legacy_coverage' else {'status': 'passed'}
        with patch.object(P, 'qa_binding', return_value=expected), \
                patch('project_qa.adjusted_args', return_value=args), patch('project_qa.invoke', side_effect=result) as invoke:
            with self.assertRaisesRegex(ValueError, 'stale or failed'):
                P.prepare_project_qa(args, {}, {'writer_path': 'registered fixture'})
            self.assertEqual(invoke.call_count, 2)
            invoke.reset_mock()
            with self.assertRaisesRegex(ValueError, 'stale or failed'):
                P.prepare_project_qa(args, {}, {'writer_path': 'registered fixture'})
            invoke.assert_not_called()
        raw = next((index.parent / 'writer-producer-proofs').glob('project-qa-*.raw.json'))
        execution = json.loads(raw.read_bytes())
        report = json.loads(execution['stdout'])
        self.assertEqual(execution['returncode'], 1)
        self.assertFalse(report['passed'])
        self.assertEqual(report['checks'][1]['result'], incomplete)
        self.assertNotIn('project-qa', json.loads(index.read_bytes())['proofs'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
