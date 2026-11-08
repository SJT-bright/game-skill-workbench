"""Preparation reuse against real source/Native steps, including changed-dependency failures."""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import preparation_cache as C
import tiktok_finalize as F
import tiktok_finalize_steps as T
from test_tiktok_finalize import APP, build24, manifest, project24
from tiktok_finalize_steps import frame_scan, reward_order_scan, save_read_scan


class PreparationReuse(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='prepare-cache-test-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = project24(self.tmp / 'project')
        F.P.write_marker(self.project, 'localize', manifest().version, reason='fixture')
        (self.project / 'assets/Game.js').write_text('const price = 10;\n')
        self.names = ('frame_scan', 'reward_order_scan', 'save_read_scan')

    def source(self, names=None, **kw):
        return F.finalize_source(self.project, 'localize', steps=names or self.names, **kw)

    def test_source_no_change_and_single_image_do_not_repeat_code_scan(self):
        with mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as frame, \
                mock.patch.object(reward_order_scan, 'apply', wraps=reward_order_scan.apply) as reward, \
                mock.patch.object(save_read_scan, 'apply', wraps=save_read_scan.apply) as save:
            first = self.source()
            second = self.source()
            (self.project / 'assets/button.png').write_bytes(b'pixel-content-v2')
            third = self.source()
        self.assertFalse(first['blocks'])
        self.assertEqual((frame.call_count, reward.call_count, save.call_count), (1, 1, 1))
        for record in (second, third):
            self.assertTrue(all(s['preparation']['reused'] for s in record['steps']))
            self.assertEqual([s['preparation']['executed_at'] for s in record['steps']],
                             [s['preparation']['executed_at'] for s in first['steps']])
        self.assertEqual(F.check_source_record(self.project), [])

    def test_new_changed_deleted_code_and_level_table_invalidate_only_consumers(self):
        self.source()
        level = self.project / 'docs/levels/level_plan.json'
        level.parent.mkdir(parents=True)
        level.write_text('{"levels": []}')
        plan = F.source_preparation_plan(self.project)
        self.assertEqual(plan['execute'], ['save_read_scan'])
        self.source()
        code = self.project / 'assets/new.js'
        code.write_text('const n = 1;')
        self.assertEqual(F.source_preparation_plan(self.project)['execute'], list(self.names))
        self.source()
        code.write_text('const n = 2;')
        self.assertEqual(F.source_preparation_plan(self.project)['execute'], list(self.names))
        self.source()
        code.unlink()
        # Content addressing may find the original exact state; this is legitimate reuse.
        self.assertEqual(F.source_preparation_plan(self.project)['execute'], [])

    def test_real_failure_is_not_cached_and_is_not_washed_into_pass(self):
        (self.project / 'assets/Game.js').write_text('cc.Class({\nupdate(dt) { this.node.x += 5; }\n});\n')
        with mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as scan:
            first = F.finalize_source(self.project, 'remake', steps=('frame_scan',))
            second = F.finalize_source(self.project, 'remake', steps=('frame_scan',))
        self.assertEqual(scan.call_count, 2)
        self.assertEqual(first['blocks'], second['blocks'])
        self.assertIn('K_frame_dt', [b['id'] for b in second['blocks']])
        self.assertFalse(list((self.project / C.HOME / 'source-frame_scan').glob('*.json')))

    def test_source_and_sync_share_real_evidence(self):
        # Install sync's standard parts first; otherwise its intentional code edits
        # correctly invalidate a previous scan of the pre-install code.
        F.finalize_sync(self.project, 'localize')
        self.source()
        with mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as scan:
            record = F.finalize_sync(self.project, 'localize')
        self.assertEqual(scan.call_count, 0)
        result = next(s for s in record['steps'] if s['step'] == 'frame_scan')
        self.assertTrue(result['preparation']['reused'])

    def test_source_external_configuration_and_rule_changes_invalidate(self):
        ad = self.tmp / 'ad-config.json'
        ad.write_text(json.dumps({'appId': APP}))
        options = {'ad_config': str(ad)}
        self.source(('settings',), options=options)
        self.assertEqual(F.check_source_record(self.project), [])
        before = (self.project / F.SOURCE_RECORD).read_bytes()
        ad.write_text(json.dumps({'appId': APP, 'changed': True}))
        self.assertTrue(F.check_source_record(self.project))
        self.assertEqual((self.project / F.SOURCE_RECORD).read_bytes(), before)
        changed_manifest = manifest(lambda d: d.update(testRuleVersion='changed'))
        self.assertTrue(F.check_source_record(self.project, manifest=changed_manifest))

    def test_source_cannot_reuse_mutation_when_output_changes(self):
        record = self.source(('settings',))
        self.assertFalse(record['blocks'])
        second = self.source(('settings',))
        self.assertTrue(second['steps'][0]['preparation']['reused'])
        settings = self.project / 'settings/bytedance.json'
        settings.write_text('{"appid":"wrong"}')
        third = self.source(('settings',))
        self.assertFalse(third['steps'][0]['preparation']['reused'])
        self.assertEqual(json.loads(settings.read_text())['appid'], APP)

    def test_corrupted_result_unknown_step_and_legacy_are_not_reused(self):
        record = self.source(('frame_scan',))
        cache = Path(record['steps'][0]['preparation']['evidence'])
        damaged = json.loads(cache.read_text())
        damaged['result']['warnings'].append({'id': 'fabricated'})
        cache.write_text(json.dumps(damaged))
        with mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as scan:
            record = self.source(('frame_scan',))
            self.source(('frame_scan',), policy='legacy')
            self.source(('frame_scan',), policy='legacy')
        self.assertEqual(scan.call_count, 3)
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=manifest())
        call = mock.Mock(return_value={'blocks': [], 'state': 'kit_current'})
        session = C.Session(ctx)
        session.apply('unregistered', call)
        session.apply('unregistered', call)
        self.assertEqual(call.call_count, 2)

    def test_read_only_step_changing_its_inputs_is_not_passed(self):
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=manifest())
        def unstable():
            (self.project / 'assets/late.js').write_text('const n = 1;')
            return {'blocks': [], 'state': 'kit_current'}
        result = C.Session(ctx).apply('frame_scan', unstable)
        self.assertEqual(result['blocks'][0]['id'], 'K_preparation_input_changed')

    def test_mutator_external_change_is_not_bound_as_success(self):
        from tiktok_finalize_steps import settings
        ad = self.tmp / 'ad.json'
        ad.write_text(json.dumps({'appId': APP}))
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=manifest(),
                    options={'ad_config': str(ad)})
        def mutate_external():
            result = settings.apply(ctx)
            ad.write_text(json.dumps({'appId': APP, 'external_revision': 2}))
            return result
        result = C.Session(ctx).apply('settings', mutate_external)
        self.assertIn('K_preparation_input_changed', [r['id'] for r in result['blocks']])
        call = mock.Mock(wraps=lambda: settings.apply(ctx))
        again = C.Session(ctx).apply('settings', call)
        self.assertEqual(call.call_count, 1)
        self.assertFalse(again['blocks'])

    def test_rule_mutation_within_same_session_is_rejected(self):
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=manifest())
        version = ['v1']
        def change_rule():
            version[0] = 'v2'
            return {'state': 'kit_current', 'blocks': []}
        with mock.patch.object(C, 'tool_inputs', side_effect=lambda *a: {'rule': version[0]}):
            session = C.Session(ctx)
            first = session.apply('frame_scan', change_rule)
            call = mock.Mock(return_value={'state': 'kit_current', 'blocks': []})
            session.apply('frame_scan', call)
        self.assertEqual(call.call_count, 1)
        self.assertIn('K_preparation_input_changed', [r['id'] for r in first['blocks']])

    def test_generated_tool_bytecode_does_not_change_rule_identity(self):
        kit = self.tmp / 'kit'
        shutil.copytree(T.KIT_DIR, kit, ignore=shutil.ignore_patterns('__pycache__'))
        m = T.Manifest(manifest().data, kit)
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=m)
        def import_side_effect():
            result = frame_scan.apply(ctx)
            generated = kit / 'tools/__pycache__/imported.cpython-315.pyc'
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_bytes(b'generated bytecode')
            return result
        result = C.Session(ctx).apply('frame_scan', import_side_effect)
        self.assertFalse(result['blocks'])
        call = mock.Mock(wraps=lambda: frame_scan.apply(ctx))
        again = C.Session(ctx).apply('frame_scan', call)
        self.assertEqual(call.call_count, 0)
        self.assertTrue(again['preparation']['reused'])
        (kit / 'tools/check_kit_project.py').write_text('# actual rule change\n')
        C.Session(ctx).apply('frame_scan', call)
        self.assertEqual(call.call_count, 1)

    def test_same_key_threads_execute_once(self):
        ctx = T.Ctx('source', self.project, project=self.project, engine=2, policy='new', manifest=manifest())
        barrier, calls = threading.Barrier(2), []
        def worker():
            barrier.wait(timeout=5)
            def execute():
                calls.append(1)
                time.sleep(0.1)
                return frame_scan.apply(ctx)
            return C.Session(ctx).apply('frame_scan', execute)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sorted(r['preparation']['reused'] for r in results), [False, True])

    def test_same_key_processes_execute_once(self):
        code = '''import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import preparation_cache as C
import tiktok_finalize_steps as T
from tiktok_finalize_steps import frame_scan
p=Path(sys.argv[2]); gate=Path(sys.argv[3]); count=Path(sys.argv[4])
while not gate.exists(): time.sleep(.01)
ctx=T.Ctx('source',p,project=p,engine=2,policy='new',manifest=T.load_manifest())
def run():
    with count.open('a') as f:f.write('executed\\n')
    time.sleep(.15)
    return frame_scan.apply(ctx)
out=C.Session(ctx).apply('frame_scan',run)
assert not out['blocks'],out
'''
        gate, count = self.tmp / 'start', self.tmp / 'executions'
        args = [sys.executable, '-B', '-c', code, str(Path(C.__file__).parent), str(self.project), str(gate), str(count)]
        workers = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        try:
            gate.touch()
            for worker in workers:
                _, error = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, error.decode())
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.terminate()
                    worker.wait(timeout=5)
        self.assertEqual(count.read_text().splitlines(), ['executed'])

    def test_symlink_directory_prevents_cache_hit(self):
        record = self.source(('frame_scan',))
        self.assertFalse(record['blocks'])
        outside = self.tmp / 'outside'
        outside.mkdir()
        (outside / 'entry.js').write_text('const x = 1;')
        (self.project / 'assets/link').symlink_to(outside, target_is_directory=True)
        with mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as scan:
            self.source(('frame_scan',))
        self.assertEqual(scan.call_count, 1)

    def test_input_changed_while_reading_cache_hit_runs_real_scan(self):
        self.source(('frame_scan',))
        reader, once = C.read_record, []
        def edit_after_read(path, binding):
            row = reader(path, binding)
            if row and not once:
                once.append(1)
                (self.project / 'assets/late.js').write_text('cc.Class({\nupdate(dt) { this.node.x += 5; }\n});\n')
            return row
        with mock.patch.object(C, 'read_record', side_effect=edit_after_read), \
                mock.patch.object(frame_scan, 'apply', wraps=frame_scan.apply) as call:
            result = self.source(('frame_scan',))
        self.assertEqual(call.call_count, 1)
        self.assertTrue(any('K_W_frame_dt' in str(i) for i in result['steps'][0]['info']))

    def native(self, native, **kwargs):
        return F.finalize_native(native, self.project, 'localize', APP, **kwargs)

    def test_native_exact_prepared_candidate_reused_and_changed_file_reexecuted(self):
        native = build24(self.tmp / 'native')
        steps = ('startup', 'touch', 'storage', 'login', 'appid', 'structure')
        record = self.native(native, steps=steps)
        self.assertFalse(record['blocks'], record['blocks'])
        with mock.patch.object(F, '_run_steps', wraps=F._run_steps) as run:
            again = self.native(native, steps=steps)
        self.assertEqual(run.call_count, 0)
        self.assertTrue(again['preparation']['reused'])
        self.assertTrue(all(not step['changed'] for step in again['steps']))
        self.assertEqual(F.check_finalize_record(again, T.Ctx('native', native).files()), [])
        (native / 'new-data.json').write_text('{"new":1}')
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=steps))
        with mock.patch.object(F, '_run_steps', wraps=F._run_steps) as run:
            updated = self.native(native, steps=steps)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(updated['blocks'])

    def test_native_conditions_and_extra_junk_invalidate(self):
        native = build24(self.tmp / 'native')
        steps = ('appid',)
        record = self.native(native, steps=steps)
        self.assertFalse(record['blocks'])
        self.assertIsNotNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=steps))
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', 'other', steps=steps))
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=steps, policy='new'))
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=steps,
                                                 options={'any_new_condition': True}))
        (native / '.DS_Store').write_bytes(b'junk')
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=steps))

    def test_native_failed_appid_never_cached(self):
        native = build24(self.tmp / 'native')
        with mock.patch.object(F, '_run_steps', wraps=F._run_steps) as run:
            first = F.finalize_native(native, self.project, 'localize', 'invalid', steps=('appid',))
            again = F.finalize_native(native, self.project, 'localize', 'invalid', steps=('appid',))
        self.assertEqual(run.call_count, 2)
        self.assertTrue(first['blocks'])
        self.assertEqual(first['blocks'], again['blocks'])
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', 'invalid', steps=('appid',)))

    def test_native_unreported_write_is_not_endorsed(self):
        from tiktok_finalize_steps import structure
        native = build24(self.tmp / 'native')
        actual = structure.apply
        def external_mutation(ctx):
            result = actual(ctx)
            (native / 'late-debug.js').write_text('window.__qa = true;')
            return result
        with mock.patch.object(structure, 'apply', side_effect=external_mutation):
            first = self.native(native, steps=('structure',))
        self.assertIn('K_preparation_input_changed', [b['id'] for b in first['blocks']])
        again = self.native(native, steps=('structure',))
        self.assertIn('L4_debug_code', [b['id'] for b in again['blocks']])
        self.assertFalse(again.get('preparation', {}).get('reused'))

    def test_prepared_api_is_read_only_and_conditions_normalize_empty_webp(self):
        native = build24(self.tmp / 'native')
        self.native(native, steps=('appid',))
        before = C.tree(self.project / '.tiktok-kit', prune=False)
        result = F.prepared_native_result(native, self.project, 'localize', APP, steps=('appid',),
                                         options={'keep_webp_exception': '', 'png_cache_read_only': True})
        self.assertIsNotNone(result)
        self.assertEqual(before, C.tree(self.project / '.tiktok-kit', prune=False))

    def test_full_native_proof_can_satisfy_writer_but_not_reverse(self):
        native = build24(self.tmp / 'native')
        self.native(native, steps=('appid',))
        with mock.patch.object(F, '_run_steps', wraps=F._run_steps) as call:
            result = self.native(native, steps=('appid',), options={'prepared_png_only': True})
        self.assertEqual(call.call_count, 0)
        self.assertTrue(result['preparation']['requested_prepared_png_only'])
        shutil.rmtree(self.project / C.HOME)
        self.native(native, steps=('appid',), options={'prepared_png_only': True})
        self.assertIsNone(F.prepared_native_result(native, self.project, 'localize', APP, steps=('appid',)))


if __name__ == '__main__':
    unittest.main()
